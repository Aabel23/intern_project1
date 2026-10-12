from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import os
import unittest
from unittest.mock import patch
from server.configuration import routing
from server.src import account
from server.src.database import open_connection, transaction
from server.src.http import dispatch_request
from server.src.types import ApiError, Dependencies, RequestContext, create_runtime_state
from test_smtp import settings


class MailSpy:
    def __init__(self): self.sent=[]; self.fail=False
    def send_registration_otp_mail(self,email,otp):
        if self.fail: raise ApiError('MAIL_UNAVAILABLE',502)
        self.sent.append(('otp',email,otp))
    def send_registration_notice(self,email):
        if self.fail: raise ApiError('MAIL_UNAVAILABLE',502)
        self.sent.append(('notice',email,None))


class AccountUnitTests(unittest.TestCase):
    def setUp(self):
        self.clock=[datetime(2026,10,12,tzinfo=timezone.utc),10.0]
        def forbidden(): raise AssertionError('DB must not be touched before schema validation')
        self.deps=Dependencies(settings(),forbidden,lambda:self.clock[0],lambda:self.clock[1],MailSpy(),None,create_runtime_state(settings()))
        self.context=RequestContext('127.0.0.1')

    def test_invalid_extra_field_and_version(self):
        for body,code in (({'v':1,'email':'a@example.invalid','extra':1},'INVALID_REQUEST'),
                          ({'v':2,'email':'a@example.invalid'},'UNSUPPORTED_VERSION'),
                          ({'v':True,'email':'a@example.invalid'},'INVALID_REQUEST')):
            result=dispatch_request(routing.USER_OTP_SEND,body,self.context,deps=self.deps)
            self.assertEqual(result.payload['error']['code'],code)
            self.assertEqual(result.status,400)

    def test_cooldown_and_email_window(self):
        account._send_gate(self.deps,'a@example.invalid',self.context.ip)
        self.clock[1]+=59.9
        with self.assertRaises(ApiError) as raised: account._send_gate(self.deps,'a@example.invalid',self.context.ip)
        self.assertEqual(raised.exception.retry_after_seconds,1)
        for _ in range(4):
            self.clock[1]+=60
            account._send_gate(self.deps,'a@example.invalid',self.context.ip)
        self.clock[1]+=60
        with self.assertRaises(ApiError) as raised: account._send_gate(self.deps,'a@example.invalid',self.context.ip)
        self.assertEqual(raised.exception.code,'RATE_LIMITED')
        self.clock[1]=3610
        account._send_gate(self.deps,'a@example.invalid',self.context.ip)

    def test_unknown_resend_no_insert_or_mail(self):
        class Cursor:
            def execute(self,sql,params):
                self.assert_select=sql.startswith('SELECT')
                if not self.assert_select: raise AssertionError('unknown resend wrote DB')
            def fetchone(self): return None
            def close(self): pass
        class Connection:
            def cursor(self,**kw): return Cursor()
            def commit(self): pass
            def rollback(self): pass
            def close(self): pass
        deps=replace(self.deps,connect=Connection)
        result=account.send_registration_otp({'v':1,'email':' Unknown@Example.invalid '},self.context,deps=deps)
        self.assertEqual(result.payload['data'],{'message':'CHECK_EMAIL','retry_after_seconds':60})
        self.assertEqual(deps.mail.sent,[])
        with self.assertRaises(ApiError) as raised: account.send_registration_otp({'v':1,'email':'unknown@example.invalid'},self.context,deps=deps)
        self.assertEqual(raised.exception.code,'RATE_LIMITED')

    def test_db_failure_is_sanitized(self):
        import mysql.connector
        def fail(): raise mysql.connector.DatabaseError('TEST_ONLY_PRIVATE_DETAIL')
        deps=replace(self.deps,connect=fail)
        result=dispatch_request(routing.USER_OTP_SEND,{'v':1,'email':'a@example.invalid'},self.context,deps=deps)
        self.assertEqual(result.status,503)
        self.assertEqual(result.payload,{'v':1,'ok':False,'error':{'code':'SERVICE_UNAVAILABLE'}})


@unittest.skipUnless(os.environ.get('TEST_DB_NAME'),'TEST_DB_* isolated MySQL fixture required')
class AccountMySQLTests(unittest.TestCase):
    def setUp(self):
        name=os.environ['TEST_DB_NAME']
        if not name.endswith('_test'): self.skipTest('fixture DB name must end _test')
        self.config=settings(db_host=os.environ['TEST_DB_HOST'],db_port=int(os.environ['TEST_DB_PORT']),
                             db_name=name,db_user=os.environ['TEST_DB_USER'],db_password=os.environ['TEST_DB_PASSWORD'])
        self.clock=[datetime(2026,10,12,tzinfo=timezone.utc),100.0]
        self.mail=MailSpy()
        self.deps=Dependencies(self.config,lambda:open_connection(self.config),lambda:self.clock[0],lambda:self.clock[1],self.mail,None,create_runtime_state(self.config))
        self.context=RequestContext('127.0.0.1')
        with transaction(self.deps.connect) as connection,closing(connection.cursor()) as cursor:
            for table in ('access_tokens','sessions','otp_generations','users'): cursor.execute('DELETE FROM '+table)
        self.email='recipient@example.invalid'
        self.password='TEST_ONLY_PASSWORD'

    def advance(self,seconds):
        self.clock[0]+=timedelta(seconds=seconds);self.clock[1]+=seconds

    def call(self,path,**body):
        return dispatch_request(path,{'v':1,**body},self.context,deps=self.deps)

    def register(self):
        return self.call(routing.USER_ACCOUNT_REGISTER,email=self.email,password=self.password)

    def otp(self):
        return self.mail.sent[-1][2]

    def verify(self,otp=None):
        return self.call(routing.USER_OTP_VERIFY,email=self.email,otp=otp or self.otp())

    def verified_login(self):
        self.assertEqual(self.register().status,200)
        self.assertEqual(self.verify().status,200)
        result=self.call(routing.USER_SESSION_LOGIN,email=self.email,password=self.password)
        self.assertEqual(result.status,200)
        return result.payload['data']

    def query(self,sql,params=()):
        with transaction(self.deps.connect) as connection,closing(connection.cursor(dictionary=True)) as cursor:
            cursor.execute(sql,params)
            return cursor.fetchall()

    def test_new_duplicate_verified_neutral_and_notice(self):
        first=self.register();self.verify();before=self.query('SELECT password_hash FROM users')[0]
        self.advance(60)
        second=self.call(routing.USER_ACCOUNT_REGISTER,email=self.email,password='TEST_ONLY_CHANGED')
        self.assertEqual(first,second)
        self.assertEqual(self.mail.sent[-1],('notice',self.email,None))
        self.assertEqual(before,self.query('SELECT password_hash FROM users')[0])

    def test_unverified_overwrite_persists_on_smtp_failure_and_old_active_survives(self):
        self.register();old_otp=self.otp();before=self.query('SELECT password_hash FROM users')[0]
        self.advance(60);self.mail.fail=True
        failed=self.call(routing.USER_ACCOUNT_REGISTER,email=self.email,password='TEST_ONLY_NEW_PASSWORD')
        self.assertEqual(failed.status,502)
        after=self.query('SELECT password_hash,verified_at FROM users')[0]
        self.assertNotEqual(before['password_hash'],after['password_hash']);self.assertIsNone(after['verified_at'])
        self.assertTrue(account._hasher().verify(after['password_hash'],'TEST_ONLY_NEW_PASSWORD'))
        generations=self.query('SELECT status FROM otp_generations ORDER BY generation')
        self.assertEqual([x['status'] for x in generations],['active','failed'])
        self.assertEqual(self.verify(old_otp).status,200)

    def test_smtp_fail_new_verified_and_resend_same_public_error(self):
        self.mail.fail=True
        new=self.register()
        self.assertEqual(self.query('SELECT status FROM otp_generations')[0]['status'],'failed')
        self.advance(60);self.mail.fail=False;self.register();self.verify();self.advance(60);self.mail.fail=True
        verified=self.register();self.advance(60)
        resend=self.call(routing.USER_OTP_SEND,email=self.email)
        self.assertEqual(new,verified);self.assertEqual(new,resend)
        self.assertEqual(new.payload,{'v':1,'ok':False,'error':{'code':'MAIL_UNAVAILABLE'}})

    def test_resend_invalidates_previous_generation_not_counter(self):
        with patch('server.src.account.secrets.randbelow',side_effect=[123456,654321]):
            self.register();old=self.otp();self.verify('000000');self.advance(60)
            self.call(routing.USER_OTP_SEND,email=self.email)
            self.assertEqual(self.query('SELECT registration_attempts FROM users')[0]['registration_attempts'],1)
            self.assertEqual(self.verify(old).payload['error']['code'],'OTP_INVALID')
            self.assertEqual(self.verify().status,200)
            self.assertEqual(self.verify().payload['error']['code'],'OTP_INVALID')

    def test_wrong_expired_and_fifth_lock_persists_restart(self):
        self.register();wrong='000000' if self.otp()!='000000' else '000001'
        for _ in range(4): self.assertEqual(self.verify(wrong).payload['error']['code'],'OTP_INVALID')
        fifth=self.verify(wrong)
        self.assertEqual(fifth.payload['error'],{'code':'OTP_LOCKED','retry_after_seconds':900})
        self.deps=replace(self.deps,state=create_runtime_state(self.config))
        self.advance(899.9)
        self.assertEqual(self.verify().payload['error'],{'code':'OTP_LOCKED','retry_after_seconds':1})
        self.advance(0.1)
        self.assertEqual(self.verify().payload['error']['code'],'OTP_EXPIRED')
        self.assertEqual(self.query('SELECT registration_attempts,registration_locked_until FROM users')[0],{'registration_attempts':0,'registration_locked_until':None})

    def test_lock_resend_register_dont_reset_and_expiry_wrong_starts_one(self):
        self.register();wrong='000000' if self.otp()!='000000' else '000001'
        for _ in range(5): self.verify(wrong)
        self.advance(60);self.call(routing.USER_OTP_SEND,email=self.email)
        self.advance(60);self.register()
        self.assertEqual(self.query('SELECT registration_attempts FROM users')[0]['registration_attempts'],5)
        self.advance(780)
        self.call(routing.USER_OTP_SEND,email=self.email)
        wrong='000000' if self.otp()!='000000' else '000001'
        self.assertEqual(self.verify(wrong).payload['error']['code'],'OTP_INVALID')
        self.assertEqual(self.query('SELECT registration_attempts FROM users')[0]['registration_attempts'],1)

    def test_lock_exact_boundary_active_code_can_verify(self):
        self.register();wrong='000000' if self.otp()!='000000' else '000001'
        for _ in range(5): self.verify(wrong)
        self.advance(850);self.call(routing.USER_OTP_SEND,email=self.email)
        self.advance(50)
        self.assertEqual(self.verify().status,200)

    def test_concurrent_verify_only_one_consumes(self):
        self.register();code=self.otp()
        with ThreadPoolExecutor(2) as pool:
            results=list(pool.map(lambda _:self.verify(code),range(2)))
        self.assertEqual(sorted(x.status for x in results),[200,409])

    def test_concurrent_fifth_wrong_does_not_exceed_five(self):
        self.register();wrong='000000' if self.otp()!='000000' else '000001'
        for _ in range(4): self.verify(wrong)
        with ThreadPoolExecutor(2) as pool: results=list(pool.map(lambda _:self.verify(wrong),range(2)))
        self.assertTrue(all(x.payload['error']['code']=='OTP_LOCKED' for x in results))
        self.assertEqual(self.query('SELECT registration_attempts FROM users')[0]['registration_attempts'],5)

    def test_login_unverified_wrong_unknown_same_auth_failed(self):
        self.register()
        for email,password in ((self.email,self.password),('unknown@example.invalid',self.password)):
            self.assertEqual(self.call(routing.USER_SESSION_LOGIN,email=email,password=password).payload['error']['code'],'AUTH_FAILED')
        self.verify()
        self.assertEqual(self.call(routing.USER_SESSION_LOGIN,email=self.email,password='TEST_ONLY_WRONG').payload['error']['code'],'AUTH_FAILED')

    def test_access_exact_expiry_refresh_rotation_logout(self):
        data=self.verified_login();token=data['access_token'];refresh=data['refresh_token']
        account.authenticate_access(token,deps=self.deps)
        self.advance(3599.999999);account.authenticate_access(token,deps=self.deps)
        self.advance(.000001)
        with self.assertRaises(ApiError): account.authenticate_access(token,deps=self.deps)
        rotated=self.call(routing.USER_SESSION_REFRESH,refresh_token=refresh).payload['data']
        self.assertEqual(self.call(routing.USER_SESSION_REFRESH,refresh_token=refresh).status,401)
        account.authenticate_access(rotated['access_token'],deps=self.deps)
        self.assertEqual(self.call(routing.USER_SESSION_LOGOUT,refresh_token=rotated['refresh_token']).status,200)
        with self.assertRaises(ApiError): account.authenticate_access(rotated['access_token'],deps=self.deps)
        self.assertEqual(self.call(routing.USER_SESSION_REFRESH,refresh_token=rotated['refresh_token']).status,401)
        self.assertEqual(self.call(routing.USER_SESSION_LOGOUT,refresh_token=rotated['refresh_token']).status,200)

    def test_refresh_exact_idle_expiry_and_logout_anonymous(self):
        data=self.verified_login();self.advance(2592000)
        self.assertEqual(self.call(routing.USER_SESSION_REFRESH,refresh_token=data['refresh_token']).status,401)
        self.assertEqual(self.call(routing.USER_SESSION_LOGOUT,refresh_token=data['refresh_token']).status,200)
        self.assertEqual(self.call(routing.USER_SESSION_LOGOUT,refresh_token='A'*43).status,200)

    def test_concurrent_refresh_one_winner_replay_preserves_new_session(self):
        data=self.verified_login()
        with ThreadPoolExecutor(2) as pool: results=list(pool.map(lambda _:self.call(routing.USER_SESSION_REFRESH,refresh_token=data['refresh_token']),range(2)))
        self.assertEqual(sorted(x.status for x in results),[200,401])
        winner=next(x.payload['data'] for x in results if x.status==200)
        account.authenticate_access(winner['access_token'],deps=self.deps)
        self.assertEqual(self.call(routing.USER_SESSION_REFRESH,refresh_token=winner['refresh_token']).status,200)

    def test_unknown_and_otp_expiry_exact(self):
        result=self.call(routing.USER_OTP_SEND,email='unknown@example.invalid')
        self.assertEqual(result.status,200);self.assertEqual(self.mail.sent,[])
        self.assertEqual(self.query('SELECT id FROM users'),[])
        self.assertEqual(self.verify('123456').payload['error']['code'],'OTP_INVALID')
        self.register();self.advance(600)
        self.assertEqual(self.verify().payload['error']['code'],'OTP_EXPIRED')


if __name__=='__main__': unittest.main()
