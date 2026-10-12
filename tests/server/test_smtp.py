import smtplib
import ssl
import unittest
from unittest.mock import MagicMock, patch
from server.configuration.skeleton import TEST_RECIPIENTS, load_settings
from server.src.smtp_mail import SMTPMail, validate_email
from server.src.types import ApiError, Settings


def settings(**changes):
    values = dict(db_host='localhost',db_port=3306,db_name='test_only',db_user='test_only',db_password='TEST_ONLY',
                  smtp_user='sender@example.invalid',smtp_from='sender@example.invalid',smtp_app_password='TEST_ONLY',
                  otp_hash_secret=b'T'*32,server_bind_host='127.0.0.1',server_bind_port=8443,
                  tls_cert_file='/test-only/cert',tls_key_file='/test-only/key',server_hpke_key_file='/test-only/hpke',
                  server_signing_key_file='/test-only/sign',server_trust_file='/test-only/trust',app_env='production',test_recipient_allowlist=())
    values.update(changes)
    return Settings(**values)


class SMTPTests(unittest.TestCase):
    def setUp(self):
        self.mail = SMTPMail(settings())

    @patch('server.src.smtp_mail.smtplib.SMTP')
    def test_one_to_tls_before_auth(self,factory):
        client = factory.return_value.__enter__.return_value
        client.send_message.return_value = {}
        self.mail.send_registration_otp_mail(' Recipient@Example.invalid ', '123456')
        factory.assert_called_once_with('smtp.gmail.com',587,timeout=10)
        calls = [call[0] for call in client.method_calls]
        self.assertEqual(calls,['ehlo','starttls','ehlo','login','send_message'])
        context = client.starttls.call_args.kwargs['context']
        self.assertEqual(context.verify_mode,ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)
        msg = client.send_message.call_args.args[0]
        self.assertEqual(msg.get_all('To'),['recipient@example.invalid'])
        self.assertIsNone(msg['Cc']); self.assertIsNone(msg['Bcc'])
        self.assertEqual(client.send_message.call_args.kwargs['to_addrs'],['recipient@example.invalid'])

    @patch('server.src.smtp_mail.smtplib.SMTP')
    def test_verified_notice_contains_no_otp(self,factory):
        client = factory.return_value.__enter__.return_value
        client.send_message.return_value = {}
        self.mail.send_registration_notice('recipient@example.invalid')
        text = client.send_message.call_args.args[0].get_content()
        self.assertIn('attempted to register',text)
        self.assertNotIn('verification code',text)

    @patch('server.src.smtp_mail.smtplib.SMTP')
    def test_auth_and_timeout_identical_public_error(self,factory):
        for cause,method,internal in ((smtplib.SMTPAuthenticationError(535,b'TEST_ONLY'),'login','MAIL_AUTH'),
                                      (TimeoutError(),'send_message','MAIL_SEND')):
            with self.subTest(method=method):
                client = MagicMock()
                factory.return_value.__enter__.return_value = client
                getattr(client,method).side_effect = cause
                with self.assertLogs('server.src.smtp_mail',level='ERROR') as records:
                    with self.assertRaises(ApiError) as raised:
                        self.mail.send_registration_notice('recipient@example.invalid')
                self.assertEqual((raised.exception.code,raised.exception.status),('MAIL_UNAVAILABLE',502))
                self.assertEqual(records.output,['ERROR:server.src.smtp_mail:'+internal])

    @patch('server.src.smtp_mail.smtplib.SMTP')
    def test_no_network_for_injection_or_test_nonrecipient(self,factory):
        for value in ('a@example.invalid\r\nBcc: other@example.invalid','a@example.invalid,b@example.invalid','Name <a@example.invalid>'):
            with self.assertRaises(ApiError): self.mail.send_registration_notice(value)
        mail = SMTPMail(settings(app_env='test',test_recipient_allowlist=TEST_RECIPIENTS))
        with self.assertRaises(ApiError) as raised: mail.send_registration_notice('other@example.invalid')
        self.assertEqual(raised.exception.code,'TEST_RECIPIENT_NOT_ALLOWED')
        factory.assert_not_called()

    def test_missing_env_and_secret_repr(self):
        with patch.dict('os.environ',{},clear=True), self.assertRaisesRegex(ValueError,'^CONFIG_INVALID$'):
            load_settings()
        self.assertNotIn('TEST_ONLY',repr(settings()))
        self.assertEqual(validate_email(' U@Example.invalid '),'u@example.invalid')


if __name__ == '__main__': unittest.main()
