from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import http.client
import ssl
import socket
import time
import threading
from pathlib import Path
import tempfile
import unittest
from uuid import uuid4
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, x25519
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pyhpke import KEMKey, KEMKeyPair
from server.configuration import routing, skeleton as cfg
from server.src.cloud_protection import bootstrap_time, close_response, json_bytes, open_request, suite, verify_machine_signature
from server.src.crypto_keys import ServerKeys, b64u, decode_b64u, load_server_keys
from server.src.http import create_app
from server.src.types import ApiError, Dependencies, HandlerResult, RequestContext, create_runtime_state
from test_smtp import settings

ROOT = Path(__file__).resolve().parents[1] / 'fixtures' / 'crypto'


class CloudTests(unittest.TestCase):
    def setUp(self):
        self.clock = [datetime(2026,10,12,tzinfo=timezone.utc),100.0]
        self.keys = ServerKeys(x25519.X25519PrivateKey.generate(),ec.generate_private_key(ec.SECP256R1()),{})
        self.deps = Dependencies(settings(),None,lambda:self.clock[0],lambda:self.clock[1],None,self.keys,create_runtime_state(settings()))
        self.context = RequestContext('127.0.0.1')

    def envelope(self,body=None,stamp=None,path=routing.USER_SESSION_BOOTSTRAP):
        sid = str(uuid4())
        stamp = int(self.clock[0].timestamp()*1000) if stamp is None else stamp
        env = dict(pv=1,route=path,method='POST',receiver='server',kid='server-hpke-1',send_id=sid,
                   sent_at_ms=stamp,machine_key_id=None,enc='',ct='',sig=None)
        aad = json_bytes([1,path,'POST','server','server-hpke-1',sid,stamp,None])
        enc,sender = suite().create_sender_context(KEMKey.from_pyca_cryptography_key(self.keys.hpke_private.public_key()),info=b'flexmix-cloud-v1')
        env['enc'] = b64u(enc)
        env['ct'] = b64u(sender.seal(json_bytes({'auth':None,'body':body or {'v':1}}),aad))
        return env,sender

    def test_official_rfc9180_ciphertexts_and_exports(self):
        vector = json.loads((ROOT/'rfc9180-base.json').read_text())['vector']
        hpke = suite()
        recipient = hpke.kem.deserialize_private_key(bytes.fromhex(vector['skRm']))
        ephemeral = KEMKeyPair(hpke.kem.deserialize_private_key(bytes.fromhex(vector['skEm'])),hpke.kem.deserialize_public_key(bytes.fromhex(vector['pkEm'])))
        enc,sender = hpke.create_sender_context(hpke.kem.deserialize_public_key(bytes.fromhex(vector['pkRm'])),info=bytes.fromhex(vector['info']),eks=ephemeral)
        self.assertEqual(enc.hex(),vector['enc'])
        receiver = hpke.create_recipient_context(enc,recipient,info=bytes.fromhex(vector['info']))
        for item in vector['encryptions']:
            plain,aad,cipher = (bytes.fromhex(item[k]) for k in ('pt','aad','ct'))
            self.assertEqual(sender.seal(plain,aad),cipher)
            self.assertEqual(receiver.open(cipher,aad),plain)
        for item in vector['exports']:
            context = bytes.fromhex(item['exporter_context'])
            expected = bytes.fromhex(item['exported_value'])
            self.assertEqual(sender.export(context,item['L']),expected)
            self.assertEqual(receiver.export(context,item['L']),expected)

    def test_response_bound_to_context_status_route_and_nonce(self):
        env,sender = self.envelope()
        opened = open_request(env['route'],env,self.context,deps=self.deps)
        result = HandlerResult(200,{'v':1,'ok':True,'data':{'server_time_ms':123}})
        response = close_response(opened,result)
        aad = json_bytes(['flexmix-response-v1',env['send_id'],200,env['route']])
        key = sender.export(b'flexmix-response-v1',16)
        cipher,nonce = decode_b64u(response['ct']),decode_b64u(response['nonce'])
        self.assertEqual(json.loads(AESGCM(key).decrypt(nonce,cipher,aad)),result.payload)
        _,other = self.envelope()
        for test_key,test_nonce,test_cipher,test_aad in (
            (other.export(b'flexmix-response-v1',16),nonce,cipher,aad),
            (key,bytes([nonce[0]^1])+nonce[1:],cipher,aad),
            (key,nonce,cipher[:-1]+bytes([cipher[-1]^1]),aad),
            (key,nonce,cipher,json_bytes(['flexmix-response-v1',env['send_id'],401,env['route']]))):
            with self.assertRaises(InvalidTag): AESGCM(test_key).decrypt(test_nonce,test_cipher,test_aad)

    def test_tamper_header_enc_cipher_and_replay(self):
        for field,value in (('route',routing.USER_SESSION_LOGIN),('method','GET'),('receiver','other'),('kid','bad'),
                            ('send_id',str(uuid4())),('sent_at_ms',1),('machine_key_id','bad'),('sig','bad'),('enc',b64u(b'Z'*32)),('ct',b64u(b'Z'*32))):
            with self.subTest(field=field):
                env,_ = self.envelope()
                env[field]=value
                with self.assertRaises(ApiError): open_request(routing.USER_SESSION_BOOTSTRAP,env,self.context,deps=self.deps)
        env,_ = self.envelope()
        open_request(env['route'],env,self.context,deps=self.deps)
        with self.assertRaises(ApiError): open_request(env['route'],env,self.context,deps=self.deps)

    def test_bootstrap_wall_zero_and_wrong_route(self):
        env,_ = self.envelope(stamp=0)
        opened = open_request(env['route'],env,self.context,deps=self.deps)
        result = bootstrap_time(opened.body,self.context,deps=self.deps)
        server_time = result.payload['data']['server_time_ms']
        receipt = 500.0
        stamp = server_time + int((501.0-receipt)*1000) # client wall time is never consulted
        env,_ = self.envelope(body={'v':1,'email':'u@example.invalid','password':'long-password'},stamp=stamp,path=routing.USER_ACCOUNT_REGISTER)
        open_request(env['route'],env,self.context,deps=self.deps)
        env,_ = self.envelope(stamp=0,path=routing.USER_SESSION_LOGIN)
        with self.assertRaises(ApiError): open_request(env['route'],env,self.context,deps=self.deps)

    def test_machine_raw_low_s_signature(self):
        key = self.keys.signing_private
        message = b'TEST ONLY message'
        r,s = decode_dss_signature(key.sign(message,ec.ECDSA(hashes.SHA256())))
        order = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
        s=min(s,order-s)
        public = key.public_key().public_bytes(serialization.Encoding.X962,serialization.PublicFormat.UncompressedPoint)
        signature = r.to_bytes(32,'big')+s.to_bytes(32,'big')
        verify_machine_signature(public,message,signature)
        for raw in (b'\0'*64,signature[:-1],r.to_bytes(32,'big')+(order-s).to_bytes(32,'big')):
            with self.assertRaises(ApiError): verify_machine_signature(public,message,raw)
        with self.assertRaises(ApiError): verify_machine_signature(public,message+b'x',signature)

    def test_key_pins_match_and_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)
            for name,key in (('hpke',self.keys.hpke_private),('sign',self.keys.signing_private)):
                item=path/name
                item.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
                item.chmod(0o600)
            pins={'v':1,'hpke':{'kid':'server-hpke-1','public_key':b64u(self.keys.hpke_private.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw))},
                  'signing':{'kid':'server-sign-1','public_key':b64u(self.keys.signing_private.public_key().public_bytes(serialization.Encoding.X962,serialization.PublicFormat.UncompressedPoint))}}
            (path/'trust').write_text(json.dumps(pins))
            config=replace(settings(),server_hpke_key_file=str(path/'hpke'),server_signing_key_file=str(path/'sign'),server_trust_file=str(path/'trust'))
            load_server_keys(config)
            pins['hpke']['public_key']=b64u(b'Z'*32)
            (path/'trust').write_text(json.dumps(pins))
            with self.assertRaisesRegex(ValueError,'CONFIG_INVALID'): load_server_keys(config)
            (path/'hpke').chmod(0o644)
            with self.assertRaisesRegex(ValueError,'CONFIG_INVALID'): load_server_keys(config)

    def test_public_fixture_response(self):
        fixture=json.loads((ROOT/'python-kotlin-account.json').read_text())
        keys=replace(self.keys,hpke_private=x25519.X25519PrivateKey.from_private_bytes(bytes.fromhex(fixture['test_only_skRm'])))
        deps=replace(self.deps,keys=keys)
        opened=open_request(fixture['request']['route'],fixture['request'],self.context,deps=deps)
        self.assertEqual(opened.response_key.hex(),fixture['response_key'])
        response=fixture['response']
        aad=json_bytes(['flexmix-response-v1',response['send_id'],response['status'],opened.route])
        self.assertEqual(json.loads(AESGCM(opened.response_key).decrypt(decode_b64u(response['nonce']),decode_b64u(response['ct']),aad)),fixture['response_plaintext'])


    def test_https_encrypted_bootstrap_and_errors_ip_from_socket(self):
        # Explicit local test CA trust; no CERT_NONE/hostname bypass.
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)
            key=ec.generate_private_key(ec.SECP256R1())
            subject=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'localhost')])
            now=datetime.now(timezone.utc)
            cert=(x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
                  .public_key(key.public_key()).serial_number(x509.random_serial_number())
                  .not_valid_before(now-timedelta(minutes=1)).not_valid_after(now+timedelta(hours=1))
                  .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost')]),critical=False)
                  .sign(key,hashes.SHA256()))
            (path/'cert').write_bytes(cert.public_bytes(serialization.Encoding.PEM))
            (path/'key').write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
            (path/'key').chmod(0o600)
            config=replace(self.deps.settings,server_bind_port=0,tls_cert_file=str(path/'cert'),tls_key_file=str(path/'key'))
            deps=replace(self.deps,settings=config)
            server=create_app(deps)
            worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
            tls=ssl.create_default_context(cafile=str(path/'cert'))
            stalled = None
            def send(method,route,raw,headers=None):
                conn=http.client.HTTPSConnection('localhost',server.server_port,context=tls,timeout=5)
                try:
                    conn.request(method,route,raw,headers or {})
                    response=conn.getresponse()
                    return response.status,json.loads(response.read())
                finally: conn.close()
            try:
                # Regression P1: a TCP peer sends no TLS bytes while a real client works.
                stalled=socket.create_connection(('127.0.0.1',server.server_port),timeout=5)
                deadline=time.monotonic()+2
                while True:
                    acquired=deps.state.http_slots.acquire(blocking=False)
                    if acquired: deps.state.http_slots.release()
                    if deps.state.http_slots._value == cfg.MAX_HTTP_REQUESTS-1: break
                    if time.monotonic()>=deadline: self.fail('stalled TLS peer did not enter bounded worker')
                    time.sleep(.01)
                env,sender=self.envelope(stamp=0)
                status,response=send('POST',env['route'],json_bytes(env),{'X-Forwarded-For':'198.51.100.77'})
                self.assertEqual(status,200);self.assertNotIn('data',response)
                aad=json_bytes(['flexmix-response-v1',env['send_id'],status,env['route']])
                result=json.loads(AESGCM(sender.export(b'flexmix-response-v1',16)).decrypt(decode_b64u(response['nonce']),decode_b64u(response['ct']),aad))
                self.assertEqual(result['data']['server_time_ms'],int(self.clock[0].timestamp()*1000))
                self.assertIn(('bootstrap_ip','127.0.0.1'),deps.state.rate_events)
                self.assertNotIn(('bootstrap_ip','198.51.100.77'),deps.state.rate_events)
                self.assertEqual(send('GET',env['route'],None),(405,{'pv':1,'error':{'code':'INVALID_ENVELOPE'}}))
                with self.assertLogs('server.src.http', level='INFO') as logs:
                    self.assertEqual(send('POST','/unknown?token=PRIVATE_TEST_VALUE',b'{}'),(404,{'pv':1,'error':{'code':'INVALID_ENVELOPE'}}))
                self.assertTrue(any('HTTP POST <unknown-route> -> 404' in line for line in logs.output))
                self.assertFalse(any('PRIVATE_TEST_VALUE' in line for line in logs.output))
                self.assertEqual(send('POST',env['route'],b'x'*65537),(400,{'pv':1,'error':{'code':'INVALID_ENVELOPE'}}))
                # Regression P2: valid JSON syntax with excessive nesting remains a 400.
                nested=b'['*5000+b'0'+b']'*5000
                self.assertLess(len(nested),65536)
                self.assertEqual(send('POST',env['route'],nested),(400,{'pv':1,'error':{'code':'INVALID_ENVELOPE'}}))
                self.assertEqual(send('POST',env['route'],json_bytes({'v':1})),(400,{'pv':1,'error':{'code':'INVALID_ENVELOPE'}}))
                env,sender=self.envelope(body={'v':1,'extra':True})
                status,response=send('POST',env['route'],json_bytes(env))
                self.assertEqual(status,400);self.assertIn('ct',response)
                aad=json_bytes(['flexmix-response-v1',env['send_id'],status,env['route']])
                result=json.loads(AESGCM(sender.export(b'flexmix-response-v1',16)).decrypt(decode_b64u(response['nonce']),decode_b64u(response['ct']),aad))
                self.assertEqual(result,{'v':1,'ok':False,'error':{'code':'INVALID_REQUEST'}})
            finally:
                if stalled is not None: stalled.close()
                server.shutdown();server.server_close();worker.join(2)

    def test_replay_capacity_clock_and_bootstrap_rate_boundaries(self):
        from unittest.mock import patch
        with patch('server.src.cloud_protection.cfg.REPLAY_CACHE_LIMIT',1):
            env,_=self.envelope();open_request(env['route'],env,self.context,deps=self.deps)
            next_env,_=self.envelope()
            with self.assertRaises(ApiError) as raised: open_request(next_env['route'],next_env,self.context,deps=self.deps)
            self.assertEqual(raised.exception.code,'RATE_LIMITED')
            self.clock[1]+=600
            open_request(next_env['route'],next_env,self.context,deps=self.deps)
        for _ in range(20): bootstrap_time({'v':1},self.context,deps=self.deps)
        with self.assertRaises(ApiError) as raised: bootstrap_time({'v':1},self.context,deps=self.deps)
        self.assertEqual(raised.exception.retry_after_seconds,60)
        self.clock[1]+=60;bootstrap_time({'v':1},self.context,deps=self.deps)
        now_ms=int(self.clock[0].timestamp()*1000)
        env,_=self.envelope(stamp=now_ms-300000);open_request(env['route'],env,self.context,deps=self.deps)
        env,_=self.envelope(stamp=now_ms-300001)
        with self.assertRaises(ApiError): open_request(env['route'],env,self.context,deps=self.deps)


if __name__=='__main__': unittest.main()
