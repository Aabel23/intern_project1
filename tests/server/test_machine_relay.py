"""End-to-end over HTTPS + MySQL: factory registration, machine hello/poll/result, claim, relay (contracts v2)."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import ssl
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'version1.1'))

from argon2 import PasswordHasher
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, x25519
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.x509.oid import NameOID
from pyhpke import KEMKey

from machine.config import identity as machine_identity
from machine.main import Dispatcher
from machine.server_connection.cloud_protection import CloudError
from machine.server_connection.machine_server_request import ServerClient
from server.configuration import routing
from server.src import devices
from server.src.cloud_protection import json_bytes, suite, verify_machine_signature
from server.src.crypto_keys import ServerKeys, b64u, decode_b64u
from server.src.database import open_connection, transaction
from server.src.http import create_app
from server.src.relay import RelayHub
from server.src.types import Dependencies, create_runtime_state
from test_smtp import settings

TABLES = ('device_audit','claim_challenges','devices','refresh_tokens','access_tokens','sessions','otp_generations','users')


def make_cert(directory):
    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'localhost')])
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=1))
            .not_valid_after(now+timedelta(hours=1))
            .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost')]),critical=False).sign(key,hashes.SHA256()))
    (directory/'cert').write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    (directory/'key').write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
    (directory/'key').chmod(0o600)


class AppClient:
    """Mirrors the Flutter CloudClient envelope: HPKE base, auth inside, exporter response."""
    def __init__(self, base, keys, tls, now_ms):
        self.base, self.keys, self.tls, self.now_ms = base, keys, tls, now_ms
        self.token = None

    def post(self, route, body, timeout=25):
        sid = str(uuid4())
        stamp = self.now_ms()
        aad = json_bytes([1,route,'POST','server','server-hpke-1',sid,stamp,None])
        enc,sender = suite().create_sender_context(KEMKey.from_pyca_cryptography_key(self.keys.hpke_private.public_key()),info=b'flexmix-cloud-v1')
        auth = None if self.token is None else {'access_token':self.token}
        env = dict(pv=1,route=route,method='POST',receiver='server',kid='server-hpke-1',send_id=sid,sent_at_ms=stamp,
                   machine_key_id=None,enc=b64u(enc),ct=b64u(sender.seal(json_bytes({'auth':auth,'body':body}),aad)),sig=None)
        request = urllib.request.Request(self.base+route,data=json_bytes(env),headers={'Content-Type':'application/json'},method='POST')
        try:
            with urllib.request.urlopen(request,timeout=timeout,context=self.tls) as response: status,raw = response.status,response.read()
        except urllib.error.HTTPError as error: status,raw = error.code,error.read()
        outer = json.loads(raw)
        if 'error' in outer: return status,outer
        plain = AESGCM(sender.export(b'flexmix-response-v1',16)).decrypt(decode_b64u(outer['nonce']),decode_b64u(outer['ct']),
                                                                        json_bytes(['flexmix-response-v1',sid,status,route]))
        return status,json.loads(plain)


@unittest.skipUnless(os.environ.get('TEST_DB_NAME'),'TEST_DB_* isolated MySQL fixture required')
class MachineRelayTests(unittest.TestCase):
    def setUp(self):
        name = os.environ['TEST_DB_NAME']
        if not name.endswith('_test'): self.skipTest('fixture DB name must end _test')
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        make_cert(self.dir)
        config = settings(db_host=os.environ['TEST_DB_HOST'],db_port=int(os.environ['TEST_DB_PORT']),db_name=name,
                          db_user=os.environ['TEST_DB_USER'],db_password=os.environ['TEST_DB_PASSWORD'],
                          server_bind_port=0,tls_cert_file=str(self.dir/'cert'),tls_key_file=str(self.dir/'key'))
        self.keys = ServerKeys(x25519.X25519PrivateKey.generate(),ec.generate_private_key(ec.SECP256R1()),{})
        self.boot_ms = int(time.time()*1000)-1000
        state = create_runtime_state(config,self.boot_ms)
        state.relay = RelayHub(relay_seconds=2,poll_seconds=1,online_grace=1.5,terminal_seconds=5)
        self.deps = Dependencies(config,lambda:open_connection(config),lambda:datetime.now(timezone.utc),time.monotonic,None,self.keys,state)
        with transaction(self.deps.connect) as connection,closing(connection.cursor()) as cursor:
            for table in TABLES: cursor.execute('DELETE FROM '+table)
        self.server = create_app(self.deps)
        threading.Thread(target=self.server.serve_forever,daemon=True).start()
        self.base = f'https://localhost:{self.server.server_port}'
        self.tls = ssl.create_default_context(cafile=str(self.dir/'cert'))
        self.trust = {'v':1,'hpke':{'kid':'server-hpke-1','public_key':b64u(self.keys.hpke_private.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw))},
                      'signing':{'kid':'server-sign-1','public_key':b64u(self.keys.signing_private.public_key().public_bytes(serialization.Encoding.X962,serialization.PublicFormat.UncompressedPoint))}}
        # Factory station: the machine creates its identity, the Operator registers the public key.
        self.state_dir = self.dir/'machine'
        self.identity = machine_identity.provision(self.state_dir,'00000000abcdef01')
        self.registered = devices.register_device(self.deps.connect,self.identity.serial,'FlexMix-Test',self.identity.public_key,
                                                  now=datetime.now(timezone.utc).replace(tzinfo=None))
        self.machine = ServerClient(self.base,self.identity,self.trust,self.tls)

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.tmp.cleanup()

    def user(self, email):
        user_id = str(uuid4())
        with transaction(self.deps.connect) as connection,closing(connection.cursor()) as cursor:
            cursor.execute('INSERT INTO users(id,email,password_hash,verified_at) VALUES(%s,%s,%s,%s)',
                           (user_id,email,PasswordHasher().hash('TEST_ONLY_PASSWORD_LONG'),datetime(2026,1,1)))
        client = AppClient(self.base,self.keys,self.tls,lambda:int(time.time()*1000))
        status,body = client.post(routing.USER_SESSION_LOGIN,{'v':1,'email':email,'password':'TEST_ONLY_PASSWORD_LONG'})
        self.assertEqual(status,200,body)
        client.token = body['data']['access_token']
        client.user_id = user_id
        return client

    def claim(self, app):
        status,begin = app.post(routing.USER_MACHINE_ACTIVATE,{'v':1,'step':'begin','serial':self.identity.serial})
        self.assertEqual(status,200,begin)
        data = begin['data']
        challenge = data['challenge']
        # The machine checks the pinned server signature before signing, as in the BLE claim stage.
        verify_machine_signature(decode_b64u(self.trust['signing']['public_key']),devices.challenge_bytes(challenge),
                                 decode_b64u(data['server_challenge_signature']))
        binding = str(uuid4())
        proof = self.identity.sign(devices.accept_bytes(challenge,binding))
        return app.post(routing.USER_MACHINE_ACTIVATE,{'v':1,'step':'complete','claim_id':data['claim_id'],
                                                         'machine_proof':b64u(proof),'local_session_binding':binding})

    def poll_once(self, dispatcher):
        command = self.machine.poll_command()
        if command is not None:
            self.machine.send_result(command['request_id'],dispatcher.handle(command))
        return command

    def test_factory_register_is_idempotent_and_conflicts(self):
        again = devices.register_device(self.deps.connect,self.identity.serial,'FlexMix-Test',self.identity.public_key,now=datetime(2026,1,1))
        self.assertEqual(again['machine_id'],self.registered['machine_id'])
        other = ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(serialization.Encoding.X962,serialization.PublicFormat.UncompressedPoint)
        with self.assertRaises(Exception) as raised: devices.register_device(self.deps.connect,self.identity.serial,'X',other,now=datetime(2026,1,1))
        self.assertEqual(raised.exception.code,'KEY_CONFLICT')

    def test_hello_unknown_key_and_boot_floor(self):
        data = self.machine.hello()
        self.assertEqual(data['machine_id'],self.registered['machine_id']); self.assertFalse(data['owned'])
        stranger = machine_identity.provision(self.dir/'stranger','00000000abcdef02')
        with self.assertRaises(CloudError) as raised: ServerClient(self.base,stranger,self.trust,self.tls).hello()
        self.assertEqual(raised.exception.code,'UNKNOWN_KEY')
        # An envelope stamped before the server booted is refused even inside the skew window.
        self.machine.hello()
        self.machine._server_time = self.boot_ms-5000
        with self.assertRaises(CloudError) as raised: self.machine.poll_command()
        self.assertEqual(raised.exception.code,'INVALID_ENVELOPE')
        self.assertIsNone(self.machine._server_time)

    def test_claim_list_relay_status_and_release(self):
        app = self.user('owner@example.invalid')
        status,body = self.claim(app)
        self.assertEqual(status,200,body)
        self.assertEqual(body['data']['machine'],{'id':self.registered['machine_id'],'serial':self.identity.serial,'name':'FlexMix-Test','role':'owner'})
        # Offline until the machine polls.
        request = {'v':1,'request_id':str(uuid4()),'machine_id':self.registered['machine_id'],'instruction':'machine.status.read','data':{}}
        status,body = app.post(routing.MACHINE_COMMAND_SEND,request)
        self.assertEqual((status,body['error']['code']),(503,'MACHINE_OFFLINE'))
        dispatcher = Dispatcher({'machine.status.read':lambda data:{'serial':self.identity.serial,'software_version':'1.1','uptime_seconds':5,'read_sequence':1}})
        self.assertIsNone(self.poll_once(dispatcher))
        status,body = app.post(routing.USER_MACHINE_LIST,{'v':1})
        self.assertTrue(body['data']['machines'][0]['online'])
        with ThreadPoolExecutor(1) as pool:
            sent = pool.submit(app.post,routing.MACHINE_COMMAND_SEND,request)
            command = None
            while command is None: command = self.poll_once(dispatcher)
            status,body = sent.result()
        self.assertEqual(status,200,body)
        self.assertEqual(body['data']['source'],'machine')
        self.assertEqual(body['data']['result'],{'ok':True,'data':{'serial':self.identity.serial,'software_version':'1.1','uptime_seconds':5,'read_sequence':1}})
        # Same request_id again returns the cached terminal, not a second read.
        self.assertEqual(app.post(routing.MACHINE_COMMAND_SEND,request)[1],body)
        # Another account cannot use the machine; the owner can release it.
        stranger = self.user('stranger@example.invalid')
        self.assertEqual(stranger.post(routing.MACHINE_COMMAND_SEND,{**request,'request_id':str(uuid4())})[1]['error']['code'],'FORBIDDEN')
        self.assertEqual(stranger.post(routing.USER_MACHINE_REMOVE,{'v':1,'machine_id':self.registered['machine_id']})[0],403)
        self.assertEqual(app.post(routing.USER_MACHINE_REMOVE,{'v':1,'machine_id':self.registered['machine_id']})[0],200)
        self.assertEqual(app.post(routing.USER_MACHINE_LIST,{'v':1})[1]['data']['machines'],[])
        self.assertFalse(self.machine.hello()['owned'])

    def test_relay_timeout_and_retry_gone(self):
        app = self.user('owner@example.invalid')
        self.assertEqual(self.claim(app)[0],200)
        self.assertIsNone(self.machine.poll_command())
        request = {'v':1,'request_id':str(uuid4()),'machine_id':self.registered['machine_id'],'instruction':'machine.status.read','data':{}}
        status,body = app.post(routing.MACHINE_COMMAND_SEND,request)
        self.assertEqual((status,body['error']['code']),(504,'MACHINE_TIMEOUT'))
        status,body = app.post(routing.MACHINE_COMMAND_SEND,{**request,'request_id':str(uuid4()),'retry':True})
        self.assertEqual((status,body['error']['code']),(410,'REQUEST_GONE'))

    def test_qr_ticket_read_is_relayed_only_to_owner(self):
        owner = self.user('ticket-owner@example.invalid')
        stranger = self.user('ticket-stranger@example.invalid')
        self.assertEqual(self.claim(owner)[0], 200)
        ticket = {'serial': 21, 'drink_name': 'Trà đào', 'price_vnd': '35000.00',
                  'status': 'used', 'created_at': '2026-10-13T10:42:00',
                  'scanned_at': None, 'completed_at': '2026-10-13T10:45:00'}
        dispatcher = Dispatcher({'nhan_ve_qr': lambda data: {'tickets': [ticket], 'next_before_serial': None}})
        self.assertIsNone(self.poll_once(dispatcher))
        request = {'v': 1, 'request_id': str(uuid4()), 'machine_id': self.registered['machine_id'],
                   'instruction': 'nhan_ve_qr', 'data': {'before_serial': None, 'limit': 20}}
        denied = stranger.post(routing.MACHINE_COMMAND_SEND, request)
        self.assertEqual((denied[0], denied[1]['error']['code']), (403, 'FORBIDDEN'))
        with ThreadPoolExecutor(1) as pool:
            sent = pool.submit(owner.post, routing.MACHINE_COMMAND_SEND, request)
            command = None
            while command is None: command = self.poll_once(dispatcher)
            status, body = sent.result()
        self.assertEqual(status, 200, body)
        self.assertEqual(body['data']['result']['data'], {'tickets': [ticket], 'next_before_serial': None})
        self.assertNotIn('payload', body['data']['result']['data']['tickets'][0])

    def test_claim_race_single_owner_and_retry_returns_result(self):
        first,second = self.user('a@example.invalid'),self.user('b@example.invalid')
        with ThreadPoolExecutor(2) as pool: results = list(pool.map(self.claim,(first,second)))
        statuses = sorted(status for status,_ in results)
        self.assertIn(statuses,([200,409],))
        with transaction(self.deps.connect) as connection,closing(connection.cursor()) as cursor:
            cursor.execute('SELECT owner_user_id FROM devices'); owners = cursor.fetchall()
        self.assertEqual(len(owners),1)

    def test_claim_wrong_proof_and_mismatch(self):
        app,other = self.user('a@example.invalid'),self.user('b@example.invalid')
        status,begin = app.post(routing.USER_MACHINE_ACTIVATE,{'v':1,'step':'begin','serial':self.identity.serial})
        challenge = begin['data']['challenge']
        binding = str(uuid4())
        bad = machine_identity.provision(self.dir/'bad','00000000abcdef03').sign(devices.accept_bytes(challenge,binding))
        body = {'v':1,'step':'complete','claim_id':challenge['claim_id'],'machine_proof':b64u(bad),'local_session_binding':binding}
        self.assertEqual(app.post(routing.USER_MACHINE_ACTIVATE,body)[1]['error']['code'],'CLAIM_PROOF_INVALID')
        good = {**body,'machine_proof':b64u(self.identity.sign(devices.accept_bytes(challenge,binding)))}
        self.assertEqual(other.post(routing.USER_MACHINE_ACTIVATE,good)[1]['error']['code'],'CLAIM_ACCOUNT_MISMATCH')
        first = app.post(routing.USER_MACHINE_ACTIVATE,good)
        self.assertEqual(first[0],200)
        # Response lost after commit: the same claim returns the same machine.
        self.assertEqual(app.post(routing.USER_MACHINE_ACTIVATE,good),first)
        self.assertEqual(app.post(routing.USER_MACHINE_ACTIVATE,{'v':1,'step':'begin','serial':self.identity.serial})[1]['error']['code'],'ALREADY_OWNED')
        self.assertEqual(app.post(routing.USER_MACHINE_ACTIVATE,{'v':1,'step':'begin','serial':'ffffffffffffffff'})[1]['error']['code'],'MACHINE_UNTRUSTED')

    def test_newest_poll_wins(self):
        self.machine.hello()
        with ThreadPoolExecutor(1) as pool:
            old = pool.submit(self.machine.poll_command)
            time.sleep(.3)
            started = time.monotonic()
            self.machine.poll_command()
            self.assertIsNone(old.result(timeout=2))
        self.assertLess(time.monotonic()-started,2)

    def test_dispatcher_runs_each_request_once(self):
        calls = []
        dispatcher = Dispatcher({'nap_kho':lambda data:calls.append(data) or {'status':'ok'}})
        command = {'request_id':str(uuid4()),'instruction':'nap_kho','data':{'x':1},'remaining_ms':5000,'_received_monotonic':time.monotonic()}
        self.assertEqual(dispatcher.handle(command),dispatcher.handle(dict(command)))
        self.assertEqual(len(calls),1)
        self.assertEqual(Dispatcher({'f':lambda d:{'loi':'Sai'}}).handle({**command,'request_id':'1','instruction':'f'}),
                         {'ok':False,'error':{'code':'COMMAND_FAILED','message':'Sai'}})
        self.assertEqual(Dispatcher({}).handle({**command,'request_id':'2'})['error']['code'],'UNSUPPORTED_INSTRUCTION')
        self.assertEqual(Dispatcher({'nap_kho':lambda d:{}}).handle({**command,'request_id':'3','remaining_ms':0})['error']['code'],'COMMAND_EXPIRED')


if __name__ == '__main__': unittest.main()
