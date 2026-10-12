"""Account handlers: transactional OTP verification and opaque session rotation."""
from collections import deque
from contextlib import closing
from datetime import timedelta, timezone
import hashlib
import hmac
import math
import re
import secrets
from threading import RLock
from uuid import uuid4
from argon2 import PasswordHasher, Type
from argon2.exceptions import VerificationError, InvalidHashError
from server.configuration import skeleton as cfg
from server.src.cloud_protection import json_bytes
from server.src.crypto_keys import b64u, decode_b64u
from server.src.database import transaction
from server.src.smtp_mail import validate_email
from server.src.types import ApiError, AuthContext, HandlerResult


def _success(data):
    return HandlerResult(200, {'v':1,'ok':True,'data':data})


def _schema(body, fields):
    if not isinstance(body,dict) or type(body.get('v')) is not int:
        raise ApiError('INVALID_REQUEST',400)
    if body['v'] != 1: raise ApiError('UNSUPPORTED_VERSION',400)
    if set(body) != {'v',*fields}: raise ApiError('INVALID_REQUEST',400)


def _password(value):
    if not isinstance(value,str) or len(value) < 8: raise ApiError('INVALID_REQUEST',400)
    return value


def _hasher():
    return PasswordHasher(time_cost=3,memory_cost=65536,parallelism=1,salt_len=16,type=Type.ID)


def _now(deps):
    return deps.utc_now().astimezone(timezone.utc).replace(tzinfo=None)


def _rfc3339(value):
    return value.replace(tzinfo=timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z')


def _email_lock(deps,email):
    with deps.state.guard:
        return deps.state.email_locks.setdefault(email,RLock())


def _events(deps,bucket,key,now,window):
    events = deps.state.rate_events.setdefault((bucket,key),deque())
    while events and events[0] <= now-window: events.popleft()
    return events


def _send_gate(deps,email,ip):
    now = deps.monotonic()
    with deps.state.guard:
        email_events = _events(deps,'otp_email',email,now,cfg.SEND_WINDOW_SECONDS)
        ip_events = _events(deps,'otp_ip',ip,now,cfg.SEND_WINDOW_SECONDS)
        waits = [deps.state.cooldown_until.get(email,0)-now]
        for events,limit in ((email_events,cfg.EMAIL_SEND_LIMIT),(ip_events,cfg.IP_SEND_LIMIT)):
            if len(events) >= limit: waits.append(events[0]+cfg.SEND_WINDOW_SECONDS-now)
        wait = max(waits)
        if wait > 0: raise ApiError('RATE_LIMITED',429,max(1,math.ceil(wait)))
        email_events.append(now)
        ip_events.append(now)
        deps.state.cooldown_until[email] = now + cfg.OTP_COOLDOWN_SECONDS


def _check_email_result(deps,email):
    with deps.state.guard:
        retry = max(0,math.ceil(deps.state.cooldown_until[email]-deps.monotonic()))
    return _success({'message':'CHECK_EMAIL','retry_after_seconds':retry})


def _allow_recipient(deps,email):
    if deps.settings.app_env == 'test' and email not in deps.settings.test_recipient_allowlist:
        raise ApiError('TEST_RECIPIENT_NOT_ALLOWED',403)


def _clear_expired_lock(cursor,user,now):
    until = user['registration_locked_until']
    if until is not None and now >= until:
        cursor.execute('UPDATE users SET registration_attempts=0,registration_locked_until=NULL WHERE id=%s',(user['id'],))
        user['registration_attempts'] = 0
        user['registration_locked_until'] = None


def _otp_hash(deps,email,generation,otp):
    return hmac.new(deps.settings.otp_hash_secret,json_bytes([email,'register',generation,otp]),hashlib.sha256).digest()


def _send(email,context,deps,password=None):
    with _email_lock(deps,email):
        _allow_recipient(deps,email)
        _send_gate(deps,email,context.ip)
        now = _now(deps)
        generation_id = None
        otp = None
        with transaction(deps.connect) as connection, closing(connection.cursor(dictionary=True)) as cursor:
            cursor.execute('SELECT * FROM users WHERE email=%s FOR UPDATE',(email,))
            user = cursor.fetchone()
            if user is None and password is not None:
                user = {'id':str(uuid4()),'email':email,'verified_at':None,'registration_attempts':0,'registration_locked_until':None}
                cursor.execute('INSERT INTO users(id,email,password_hash) VALUES(%s,%s,%s)',(user['id'],email,_hasher().hash(password)))
            elif user is not None and user['verified_at'] is None:
                _clear_expired_lock(cursor,user,now)
                if password is not None:
                    cursor.execute('UPDATE users SET password_hash=%s WHERE id=%s',(_hasher().hash(password),user['id']))
            if user is not None and user['verified_at'] is None:
                cursor.execute('SELECT COALESCE(MAX(generation),0) AS latest FROM otp_generations WHERE email=%s AND purpose=%s',(email,'register'))
                generation = cursor.fetchone()['latest'] + 1
                generation_id = str(uuid4())
                otp = f'{secrets.randbelow(1000000):06d}'
                cursor.execute('INSERT INTO otp_generations(id,email,purpose,hash,expires_at,generation,status) VALUES(%s,%s,%s,%s,%s,%s,%s)',
                               (generation_id,email,'register',_otp_hash(deps,email,generation,otp),now+timedelta(seconds=cfg.OTP_SECONDS),generation,'sending'))
        if user is None: return _check_email_result(deps,email)
        try:
            if user['verified_at'] is not None:
                deps.mail.send_registration_notice(email)
            else:
                deps.mail.send_registration_otp_mail(email,otp)
        except ApiError:
            if generation_id is not None:
                with transaction(deps.connect) as connection, closing(connection.cursor()) as cursor:
                    cursor.execute('UPDATE otp_generations SET status=%s WHERE id=%s',('failed',generation_id))
            raise
        if generation_id is not None:
            with transaction(deps.connect) as connection, closing(connection.cursor()) as cursor:
                cursor.execute('UPDATE otp_generations SET status=%s,consumed_at=%s WHERE email=%s AND purpose=%s AND status=%s',('consumed',_now(deps),email,'register','active'))
                cursor.execute('UPDATE otp_generations SET status=%s WHERE id=%s',('active',generation_id))
        return _check_email_result(deps,email)


def register_account(body,context,*,deps):
    _schema(body,{'email','password'})
    return _send(validate_email(body['email']),context,deps,_password(body['password']))


def send_registration_otp(body,context,*,deps):
    _schema(body,{'email'})
    return _send(validate_email(body['email']),context,deps)


def verify_registration_otp(body,context,*,deps):
    _schema(body,{'email','otp'})
    email = validate_email(body['email'])
    if not isinstance(body['otp'],str) or not re.fullmatch(r'[0-9]{6}',body['otp']):
        raise ApiError('INVALID_REQUEST',400)
    error = None
    with _email_lock(deps,email):
        now = _now(deps)
        with transaction(deps.connect) as connection, closing(connection.cursor(dictionary=True)) as cursor:
            cursor.execute('SELECT * FROM users WHERE email=%s FOR UPDATE',(email,))
            user = cursor.fetchone()
            if user is None or user['verified_at'] is not None:
                error = ApiError('OTP_INVALID',409)
            else:
                _clear_expired_lock(cursor,user,now)
                until = user['registration_locked_until']
                if until is not None and now < until:
                    error = ApiError('OTP_LOCKED',429,max(1,math.ceil((until-now).total_seconds())))
                else:
                    cursor.execute('SELECT * FROM otp_generations WHERE email=%s AND purpose=%s AND status=%s ORDER BY generation DESC LIMIT 1 FOR UPDATE',(email,'register','active'))
                    generation = cursor.fetchone()
                    if generation is None:
                        error = ApiError('OTP_INVALID',409)
                    elif now >= generation['expires_at']:
                        error = ApiError('OTP_EXPIRED',410)
                    elif not hmac.compare_digest(bytes(generation['hash']),_otp_hash(deps,email,generation['generation'],body['otp'])):
                        attempts = user['registration_attempts'] + 1
                        until = now+timedelta(seconds=cfg.OTP_LOCK_SECONDS) if attempts >= cfg.OTP_MAX_ATTEMPTS else None
                        cursor.execute('UPDATE users SET registration_attempts=%s,registration_locked_until=%s WHERE id=%s',(attempts,until,user['id']))
                        error = ApiError('OTP_LOCKED',429,cfg.OTP_LOCK_SECONDS) if until else ApiError('OTP_INVALID',409)
                    else:
                        cursor.execute('UPDATE users SET verified_at=%s,registration_attempts=0,registration_locked_until=NULL WHERE id=%s',(now,user['id']))
                        cursor.execute('UPDATE otp_generations SET status=%s,consumed_at=%s WHERE id=%s',('consumed',now,generation['id']))
    # Persist wrong-attempt counters before reporting the business error.
    if error: raise error
    return _success({'verified':True})


def _token_hash(token,code):
    try:
        if len(decode_b64u(token)) != 32: raise ValueError()
    except (ValueError,TypeError):
        raise ApiError(code,401 if code == 'SESSION_EXPIRED' else 400) from None
    return hashlib.sha256(token.encode('ascii')).digest()


def _issue(cursor,user,now,session_id=None):
    access,refresh = b64u(secrets.token_bytes(32)),b64u(secrets.token_bytes(32))
    access_expires = now+timedelta(seconds=cfg.ACCESS_SECONDS)
    refresh_expires = now+timedelta(seconds=cfg.REFRESH_SECONDS)
    refresh_hash = _token_hash(refresh,'SESSION_EXPIRED')
    if session_id is None:
        session_id = str(uuid4())
        cursor.execute('INSERT INTO sessions(id,user_id,refresh_hash,refresh_expires_at) VALUES(%s,%s,%s,%s)',(session_id,user['id'],refresh_hash,refresh_expires))
    else:
        cursor.execute('UPDATE sessions SET refresh_hash=%s,refresh_expires_at=%s WHERE id=%s',(refresh_hash,refresh_expires,session_id))
    cursor.execute('INSERT INTO access_tokens(hash,session_id,expires_at) VALUES(%s,%s,%s)',(_token_hash(access,'SESSION_EXPIRED'),session_id,access_expires))
    return _success({'access_token':access,'access_expires_at':_rfc3339(access_expires),
                     'refresh_token':refresh,'refresh_expires_at':_rfc3339(refresh_expires),
                     'user':{'id':user['id'],'email':user['email']}})


def login(body,context,*,deps):
    _schema(body,{'email','password'})
    email,password = validate_email(body['email']),_password(body['password'])
    with deps.state.guard:
        events = _events(deps,'login_ip',context.ip,deps.monotonic(),cfg.LOGIN_WINDOW_SECONDS)
        if len(events) >= cfg.LOGIN_FAILURE_LIMIT:
            raise ApiError('RATE_LIMITED',429,max(1,math.ceil(events[0]+cfg.LOGIN_WINDOW_SECONDS-deps.monotonic())))
    with transaction(deps.connect) as connection, closing(connection.cursor(dictionary=True)) as cursor:
        cursor.execute('SELECT * FROM users WHERE email=%s',(email,))
        user = cursor.fetchone()
        valid = False
        if user is not None and user['verified_at'] is not None:
            try: valid = _hasher().verify(user['password_hash'],password)
            except (VerificationError,InvalidHashError): pass
        if valid: return _issue(cursor,user,_now(deps))
    with deps.state.guard:
        _events(deps,'login_ip',context.ip,deps.monotonic(),cfg.LOGIN_WINDOW_SECONDS).append(deps.monotonic())
    raise ApiError('AUTH_FAILED',401)


def refresh_session(body,context,*,deps):
    _schema(body,{'refresh_token'})
    token_hash = _token_hash(body['refresh_token'],'SESSION_EXPIRED')
    with transaction(deps.connect) as connection, closing(connection.cursor(dictionary=True)) as cursor:
        cursor.execute('SELECT * FROM sessions WHERE refresh_hash=%s FOR UPDATE',(token_hash,))
        session = cursor.fetchone()
        now = _now(deps)
        if session is None or session['revoked_at'] is not None or now >= session['refresh_expires_at']:
            raise ApiError('SESSION_EXPIRED',401)
        cursor.execute('SELECT id,email FROM users WHERE id=%s',(session['user_id'],))
        user = cursor.fetchone()
        return _issue(cursor,user,now,session['id'])


def logout(body,context,*,deps):
    _schema(body,{'refresh_token'})
    token_hash = _token_hash(body['refresh_token'],'INVALID_REQUEST')
    with transaction(deps.connect) as connection, closing(connection.cursor(dictionary=True)) as cursor:
        cursor.execute('SELECT id FROM sessions WHERE refresh_hash=%s FOR UPDATE',(token_hash,))
        session = cursor.fetchone()
        if session is not None:
            cursor.execute('UPDATE sessions SET revoked_at=%s WHERE id=%s',(_now(deps),session['id']))
    return _success({'logged_out':True})


def authenticate_access(token,*,deps):
    token_hash = _token_hash(token,'SESSION_EXPIRED')
    with transaction(deps.connect) as connection, closing(connection.cursor(dictionary=True)) as cursor:
        cursor.execute('SELECT a.expires_at,s.id AS session_id,s.user_id,s.revoked_at FROM access_tokens a JOIN sessions s ON s.id=a.session_id WHERE a.hash=%s',(token_hash,))
        row = cursor.fetchone()
        if row is None or row['revoked_at'] is not None or _now(deps) >= row['expires_at']:
            raise ApiError('SESSION_EXPIRED',401)
        return AuthContext(row['user_id'],row['session_id'])
