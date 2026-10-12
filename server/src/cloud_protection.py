"""RFC9180 request envelopes and exporter-bound encrypted responses."""
from collections import deque
import json
import math
import secrets
from uuid import UUID
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pyhpke import CipherSuite, KEMId, KDFId, AEADId, KEMKey
from server.configuration import routing, skeleton as cfg
from server.src.crypto_keys import b64u, decode_b64u
from server.src.types import ApiError, Dependencies, HandlerResult, OpenedRequest, RequestContext


def json_bytes(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')


def parse_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError()
            result[key] = value
        return result
    def number(value):
        raise ValueError()
    result = json.loads(raw, object_pairs_hook=pairs, parse_constant=number)
    def safe(value):
        if type(value) is int and abs(value) > 9007199254740991:
            raise ValueError()
        if isinstance(value, dict):
            for item in value.values(): safe(item)
        elif isinstance(value, list):
            for item in value: safe(item)
    safe(result)
    return result


def suite():
    return CipherSuite.new(KEMId.DHKEM_X25519_HKDF_SHA256, KDFId.HKDF_SHA256, AEADId.AES128_GCM)


def account_routes():
    return {routing.USER_ACCOUNT_REGISTER, routing.USER_OTP_SEND, routing.USER_OTP_VERIFY,
            routing.USER_SESSION_LOGIN, routing.USER_SESSION_REFRESH,
            routing.USER_SESSION_LOGOUT, routing.USER_SESSION_BOOTSTRAP}


def user_routes():
    """App routes that require auth={access_token} inside the envelope."""
    return {routing.USER_MACHINE_LIST, routing.USER_MACHINE_ACTIVATE, routing.USER_MACHINE_REMOVE,
            routing.MACHINE_COMMAND_SEND}


def machine_routes():
    """Routes signed by a factory-registered machine key (contracts v2 D1)."""
    return {routing.MACHINE_HELLO_SEND, routing.MACHINE_COMMAND_POLL, routing.MACHINE_RESULT_SEND}


def all_routes():
    return account_routes() | user_routes() | machine_routes()


def machine_envelope_bytes(aad: bytes, enc: str, ct: str) -> bytes:
    return json_bytes(['flexmix-machine-envelope-v1', b64u(aad), enc, ct])


def verify_machine_signature(public_key: bytes, signed_bytes: bytes, signature: bytes) -> None:
    order = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
    try:
        if len(signature) != 64 or len(public_key) != 65 or public_key[0] != 4:
            raise ValueError()
        r, s = int.from_bytes(signature[:32], 'big'), int.from_bytes(signature[32:], 'big')
        if not 0 < r < order or not 0 < s <= order // 2:
            raise ValueError()
        key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), public_key)
        key.verify(encode_dss_signature(r,s), signed_bytes, ec.ECDSA(hashes.SHA256()))
    except (ValueError, InvalidSignature):
        raise ApiError('INVALID_ENVELOPE', 400) from None


def open_request(path: str, envelope: dict, context: RequestContext, *, deps: Dependencies) -> OpenedRequest:
    if path not in all_routes():
        raise ApiError('INVALID_ENVELOPE', 404)
    machine_route = path in machine_routes()
    device = None
    try:
        fields = {'pv','route','method','receiver','kid','send_id','sent_at_ms','machine_key_id','enc','ct','sig'}
        if not isinstance(envelope, dict) or set(envelope) != fields:
            raise ValueError()
        if type(envelope['pv']) is not int or envelope['pv'] != 1:
            raise ApiError('UNSUPPORTED_VERSION', 400)
        if envelope['kid'] != 'server-hpke-1':
            raise ApiError('UNKNOWN_KEY', 400)
        if envelope['route'] != path or envelope['method'] != 'POST' or envelope['receiver'] != 'server':
            raise ValueError()
        if machine_route:
            if not isinstance(envelope['machine_key_id'],str) or not isinstance(envelope['sig'],str) or len(envelope['machine_key_id']) > 32:
                raise ValueError()
        elif envelope['machine_key_id'] is not None or envelope['sig'] is not None:
            raise ValueError()
        sid = envelope['send_id']
        uid = UUID(sid)
        if uid.version != 4 or str(uid) != sid:
            raise ValueError()
        stamp = envelope['sent_at_ms']
        if type(stamp) is not int or not 0 <= stamp <= 9007199254740991:
            raise ValueError()
        enc, ciphertext = decode_b64u(envelope['enc']), decode_b64u(envelope['ct'])
        if len(enc) != 32 or len(ciphertext) < 16:
            raise ValueError()
        aad = json_bytes([1,path,'POST','server',envelope['kid'],sid,stamp,envelope['machine_key_id']])
        if machine_route:
            from server.src.devices import device_by_key_id
            device = device_by_key_id(deps, envelope['machine_key_id'])
            if device is None:
                raise ApiError('UNKNOWN_KEY', 400)
            # The outer signature is checked before spending work on HPKE.
            verify_machine_signature(bytes(device['public_key']), machine_envelope_bytes(aad, envelope['enc'], envelope['ct']),
                                     decode_b64u(envelope['sig']))
        hpke = suite().create_recipient_context(enc, KEMKey.from_pyca_cryptography_key(deps.keys.hpke_private), info=b'flexmix-cloud-v1')
        plaintext = hpke.open(ciphertext, aad)
        if len(plaintext) > cfg.PLAINTEXT_MAX_BYTES:
            raise ValueError()
        # Timestamp-zero exception is restricted to the read-only bootstrap schema.
        value = parse_json(plaintext)
        if not isinstance(value, dict) or set(value) != {'auth','body'} or not isinstance(value['body'],dict):
            raise ValueError()
        if stamp == 0:
            if path not in (routing.USER_SESSION_BOOTSTRAP, routing.MACHINE_HELLO_SEND) or value != {'auth':None,'body':{'v':1}} or type(value['body']['v']) is not int:
                raise ValueError()
        elif abs(int(deps.utc_now().timestamp()*1000)-stamp) > cfg.CLOCK_SKEW_SECONDS*1000:
            raise ValueError()
        elif stamp < deps.state.boot_wall_ms:
            # Boot floor (v2 D6): the RAM replay cache cannot vouch for anything sent before this process started.
            raise ValueError()
        if machine_route and value['auth'] is not None:
            raise ValueError()
        now = deps.monotonic()
        with deps.state.guard:
            replay = deps.state.replay_entries
            for key in list(replay):
                if replay[key] <= now: del replay[key]
            key = (envelope['kid'],sid)
            if key in replay: raise ValueError()
            if len(replay) >= cfg.REPLAY_CACHE_LIMIT:
                raise ApiError('RATE_LIMITED',429)
            replay[key] = now + cfg.REPLAY_CACHE_SECONDS
        return OpenedRequest(value['body'],value['auth'],path,sid,hpke.export(b'flexmix-response-v1',16),device)
    except ApiError as error:
        # A DB outage while looking up a machine key is not an envelope fault.
        raise error
    except Exception:
        raise ApiError('INVALID_ENVELOPE',400) from None


def close_response(opened: OpenedRequest, result: HandlerResult) -> dict:
    nonce = secrets.token_bytes(12)
    aad = json_bytes(['flexmix-response-v1',opened.send_id,result.status,opened.route])
    plaintext = json_bytes(result.payload)
    if len(plaintext) > cfg.PLAINTEXT_MAX_BYTES:
        raise ValueError('RESPONSE_TOO_LARGE')
    ciphertext = AESGCM(opened.response_key).encrypt(nonce,plaintext,aad)
    return {'pv':1,'send_id':opened.send_id,'status':result.status,'nonce':b64u(nonce),'ct':b64u(ciphertext)}


def bootstrap_time(body: dict, context: RequestContext, *, deps: Dependencies) -> HandlerResult:
    if not isinstance(body,dict) or set(body) != {'v'} or type(body['v']) is not int:
        raise ApiError('INVALID_REQUEST',400)
    if body['v'] != 1: raise ApiError('UNSUPPORTED_VERSION',400)
    now = deps.monotonic()
    with deps.state.guard:
        events = deps.state.rate_events.setdefault(('bootstrap_ip',context.ip),deque())
        while events and events[0] <= now-cfg.BOOTSTRAP_WINDOW_SECONDS: events.popleft()
        if len(events) >= cfg.BOOTSTRAP_LIMIT:
            raise ApiError('RATE_LIMITED',429,max(1,math.ceil(events[0]+cfg.BOOTSTRAP_WINDOW_SECONDS-now)))
        events.append(now)
    return HandlerResult(200,{'v':1,'ok':True,'data':{'server_time_ms':int(deps.utc_now().timestamp()*1000)}})
