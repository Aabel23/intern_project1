"""Factory-registered machines, owner claim, release and the Operator CLI (contracts v2 D1/D2)."""
import argparse
from contextlib import closing
from datetime import timezone
import hashlib
import hmac
import re
import secrets
import sys
from uuid import UUID, uuid4
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from server.configuration import skeleton as cfg
from server.src.cloud_protection import json_bytes, verify_machine_signature
from server.src.crypto_keys import b64u, decode_b64u
from server.src.database import run_transaction
from server.src.types import ApiError, HandlerResult

P256_ORDER = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
SERIAL_PATTERN = re.compile(r'[0-9a-f]{16}')


def _success(data):
    return HandlerResult(200, {'v':1,'ok':True,'data':data})


def _schema(body, fields):
    if not isinstance(body,dict) or type(body.get('v')) is not int:
        raise ApiError('INVALID_REQUEST',400)
    if body['v'] != 1: raise ApiError('UNSUPPORTED_VERSION',400)
    if set(body) != {'v',*fields}: raise ApiError('INVALID_REQUEST',400)


def _uuid4(value):
    try:
        parsed = UUID(value)
    except (ValueError,TypeError,AttributeError):
        raise ApiError('INVALID_REQUEST',400) from None
    if parsed.version != 4 or str(parsed) != value: raise ApiError('INVALID_REQUEST',400)
    return value


def _serial(value):
    if not isinstance(value,str) or not SERIAL_PATTERN.fullmatch(value): raise ApiError('INVALID_REQUEST',400)
    return value


def key_id_for(public_key: bytes) -> str:
    return 'mk_' + b64u(hashlib.sha256(public_key).digest())[:22]


def sign_raw(private_key, message: bytes) -> bytes:
    """Deterministic P-256 signature as raw r||s with low-s, the only form verifiers accept."""
    r, s = decode_dss_signature(private_key.sign(message, ec.ECDSA(hashes.SHA256(), deterministic_signing=True)))
    if s > P256_ORDER // 2: s = P256_ORDER - s
    return r.to_bytes(32,'big') + s.to_bytes(32,'big')


def _now_ms(deps):
    return int(deps.utc_now().timestamp()*1000)


def _now(deps):
    return deps.utc_now().astimezone(timezone.utc).replace(tzinfo=None)


def _audit(cursor, device_id, action, actor, now):
    cursor.execute('INSERT INTO device_audit(device_id,action,actor,at) VALUES(%s,%s,%s,%s)',(device_id,action,actor,now))


def device_by_key_id(deps, key_id):
    """Machine envelope lookup; the key, never the serial, identifies the machine."""
    def work(connection):
        with closing(connection.cursor(dictionary=True)) as cursor:
            cursor.execute('SELECT id,serial,name,public_key,key_id,owner_user_id FROM devices WHERE key_id=%s',(key_id,))
            return cursor.fetchone()
    return run_transaction(deps.connect, work)


def owner_of(deps, machine_id):
    def work(connection):
        with closing(connection.cursor(dictionary=True)) as cursor:
            cursor.execute('SELECT owner_user_id FROM devices WHERE id=%s',(machine_id,))
            row = cursor.fetchone()
            return None if row is None else row['owner_user_id']
    return run_transaction(deps.connect, work)


# ---------------------------------------------------------------- machine routes

def machine_hello(body, context, *, deps):
    _schema(body,set())
    device = context.machine
    return _success({'server_time_ms':_now_ms(deps),'machine_id':device['id'],'owned':device['owner_user_id'] is not None})


# ---------------------------------------------------------------- app routes

def list_user_machines(body, context, *, deps):
    _schema(body,set())
    def work(connection):
        with closing(connection.cursor(dictionary=True)) as cursor:
            cursor.execute('SELECT id,serial,name FROM devices WHERE owner_user_id=%s ORDER BY name,serial',(context.auth.user_id,))
            return cursor.fetchall()
    rows = run_transaction(deps.connect, work)
    relay = deps.state.relay
    machines = []
    for row in rows:
        seen = relay.last_seen_ms(row['id']) if relay else None
        machines.append({'id':row['id'],'serial':row['serial'],'name':row['name'],'role':'owner',
                         'online':bool(relay and relay.is_online(row['id'])),'last_seen_at':seen})
    return _success({'machines':machines,'server_seen_at':_now_ms(deps)})


def remove_machine(body, context, *, deps):
    _schema(body,{'machine_id'})
    machine_id = _uuid4(body['machine_id'])
    def work(connection):
        with closing(connection.cursor(dictionary=True)) as cursor:
            cursor.execute('SELECT owner_user_id FROM devices WHERE id=%s FOR UPDATE',(machine_id,))
            row = cursor.fetchone()
            if row is None or row['owner_user_id'] != context.auth.user_id: return ApiError('FORBIDDEN',403)
            cursor.execute('UPDATE devices SET owner_user_id=NULL WHERE id=%s',(machine_id,))
            _audit(cursor,machine_id,'owner_release','user:'+context.auth.user_id,_now(deps))
            return None
    error = run_transaction(deps.connect, work)
    if error: raise error
    return _success({'removed':True})


def challenge_bytes(challenge):
    return json_bytes(['flexmix-claim-v1',challenge['claim_id'],challenge['machine_id'],challenge['user_id'],
                       challenge['purpose'],challenge['nonce'],challenge['expires_at']])


def accept_bytes(challenge, local_session_binding):
    return json_bytes(['flexmix-claim-accept-v1',b64u(challenge_bytes(challenge)),local_session_binding])


def activate_machine(body, context, *, deps):
    if not isinstance(body,dict) or body.get('step') not in ('begin','complete'):
        raise ApiError('INVALID_REQUEST',400)
    if body['step'] == 'begin':
        _schema(body,{'step','serial'})
        return _begin_claim(_serial(body['serial']),context,deps)
    _schema(body,{'step','claim_id','machine_proof','local_session_binding'})
    try:
        proof = decode_b64u(body['machine_proof'])
    except ValueError:
        raise ApiError('INVALID_REQUEST',400) from None
    if len(proof) != 64: raise ApiError('INVALID_REQUEST',400)
    return _complete_claim(_uuid4(body['claim_id']),proof,_uuid4(body['local_session_binding']),context,deps)


def _begin_claim(serial, context, deps):
    user_id = context.auth.user_id
    def work(connection):
        with closing(connection.cursor(dictionary=True)) as cursor:
            cursor.execute('SELECT id,owner_user_id FROM devices WHERE serial=%s',(serial,))
            device = cursor.fetchone()
            if device is None: return ApiError('MACHINE_UNTRUSTED',401)
            if device['owner_user_id'] is not None: return ApiError('ALREADY_OWNED',409)
            claim_id, nonce = str(uuid4()), secrets.token_bytes(32)
            expires = _now_ms(deps) + cfg.CLAIM_SECONDS*1000
            cursor.execute('INSERT INTO claim_challenges(id,device_id,user_id,nonce,expires_at_ms) VALUES(%s,%s,%s,%s,%s)',
                           (claim_id,device['id'],user_id,nonce,expires))
            return {'claim_id':claim_id,'machine_id':device['id'],'user_id':user_id,'purpose':'claim_owner',
                    'nonce':b64u(nonce),'expires_at':expires}
    challenge = run_transaction(deps.connect, work)
    if isinstance(challenge,ApiError): raise challenge
    signature = sign_raw(deps.keys.signing_private, challenge_bytes(challenge))
    return _success({'claim_id':challenge['claim_id'],'machine_id':challenge['machine_id'],'challenge':challenge,
                     'server_challenge_signature':b64u(signature)})


def _complete_claim(claim_id, proof, binding, context, deps):
    user_id = context.auth.user_id
    def work(connection):
        with closing(connection.cursor(dictionary=True)) as cursor:
            # Lock order claim -> device everywhere to keep deadlocks rare.
            cursor.execute('SELECT * FROM claim_challenges WHERE id=%s FOR UPDATE',(claim_id,))
            claim = cursor.fetchone()
            if claim is None or claim['user_id'] != user_id: return ApiError('CLAIM_ACCOUNT_MISMATCH',403)
            cursor.execute('SELECT * FROM devices WHERE id=%s FOR UPDATE',(claim['device_id'],))
            device = cursor.fetchone()
            machine = {'id':device['id'],'serial':device['serial'],'name':device['name'],'role':'owner'}
            # A retry after a lost response returns the committed result, even past expiry.
            if claim['consumed_at'] is not None:
                if device['owner_user_id'] == user_id and claim['local_session_binding'] == binding:
                    return {'machine':machine}
                return ApiError('ALREADY_OWNED',409)
            if _now_ms(deps) >= claim['expires_at_ms']: return ApiError('CLAIM_EXPIRED',410)
            challenge = {'claim_id':claim_id,'machine_id':device['id'],'user_id':user_id,'purpose':'claim_owner',
                         'nonce':b64u(bytes(claim['nonce'])),'expires_at':claim['expires_at_ms']}
            try:
                verify_machine_signature(bytes(device['public_key']),accept_bytes(challenge,binding),proof)
            except ApiError:
                return ApiError('CLAIM_PROOF_INVALID',401)
            cursor.execute('UPDATE devices SET owner_user_id=%s WHERE id=%s AND owner_user_id IS NULL',(user_id,device['id']))
            if cursor.rowcount != 1: return ApiError('ALREADY_OWNED',409)
            now = _now(deps)
            cursor.execute('UPDATE claim_challenges SET consumed_at=%s,local_session_binding=%s WHERE id=%s',(now,binding,claim_id))
            _audit(cursor,device['id'],'owner_claim','user:'+user_id,now)
            return {'machine':machine}
    result = run_transaction(deps.connect, work)
    if isinstance(result,ApiError): raise result
    return _success(result)


# ---------------------------------------------------------------- Operator CLI

def register_device(connect, serial, name, public_key, *, rekey=False, now):
    """Idempotent on (serial, public_key); a different key needs an explicit, audited rekey."""
    serial = _serial(serial)
    if not isinstance(name,str) or not 1 <= len(name) <= 64 or any(ord(c) < 32 for c in name):
        raise ApiError('INVALID_REQUEST',400)
    if len(public_key) != 65 or public_key[0] != 4:
        raise ApiError('INVALID_REQUEST',400)
    ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(),public_key)
    key_id = key_id_for(public_key)
    def work(connection):
        with closing(connection.cursor(dictionary=True)) as cursor:
            cursor.execute('SELECT * FROM devices WHERE serial=%s FOR UPDATE',(serial,))
            device = cursor.fetchone()
            if device is None:
                device_id = str(uuid4())
                cursor.execute('INSERT INTO devices(id,serial,name,public_key,key_id,created_at) VALUES(%s,%s,%s,%s,%s,%s)',
                               (device_id,serial,name,public_key,key_id,now))
                _audit(cursor,device_id,'register','operator',now)
                return {'machine_id':device_id,'key_id':key_id,'created':True}
            if hmac.compare_digest(bytes(device['public_key']),public_key):
                return {'machine_id':device['id'],'key_id':key_id,'created':False}
            if not rekey: return ApiError('KEY_CONFLICT',409)
            cursor.execute('UPDATE devices SET public_key=%s,key_id=%s WHERE id=%s',(public_key,key_id,device['id']))
            _audit(cursor,device['id'],'rekey','operator',now)
            return {'machine_id':device['id'],'key_id':key_id,'created':False}
    result = run_transaction(connect, work)
    if isinstance(result,ApiError): raise result
    return result


def unbind_device(connect, serial, *, now):
    serial = _serial(serial)
    def work(connection):
        with closing(connection.cursor(dictionary=True)) as cursor:
            cursor.execute('SELECT id FROM devices WHERE serial=%s FOR UPDATE',(serial,))
            device = cursor.fetchone()
            if device is None: return ApiError('MACHINE_UNTRUSTED',404)
            cursor.execute('UPDATE devices SET owner_user_id=NULL WHERE id=%s',(device['id'],))
            _audit(cursor,device['id'],'owner_unbind','operator',now)
            return {'machine_id':device['id'],'unbound':True}
    result = run_transaction(connect, work)
    if isinstance(result,ApiError): raise result
    return result


def main(argv=None):
    import json
    from datetime import datetime
    from server.configuration.skeleton import load_db_settings
    from server.src.database import open_connection
    parser = argparse.ArgumentParser(prog='python -m server.src.devices', description='Operator: register, rekey or unbind a machine.')
    parser.add_argument('--serial', required=True)
    parser.add_argument('--name')
    parser.add_argument('--public-key')
    parser.add_argument('--rekey', action='store_true')
    parser.add_argument('--unbind', action='store_true')
    args = parser.parse_args(argv)
    settings = load_db_settings()
    connect = lambda: open_connection(settings)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        if args.unbind:
            result = unbind_device(connect, args.serial, now=now)
        else:
            if not args.name or not args.public_key: parser.error('--name and --public-key are required')
            result = register_device(connect, args.serial, args.name, decode_b64u(args.public_key), rekey=args.rekey, now=now)
    except (ApiError, ValueError) as error:
        print(json.dumps({'ok':False,'error':getattr(error,'code','INVALID_REQUEST')}))
        return 1
    print(json.dumps({'ok':True,**result}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
