"""Gmail STARTTLS transport with one validated recipient and sanitized errors."""
from email.message import EmailMessage
from email.utils import parseaddr
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
import logging
import re
import smtplib
import ssl
from server.src.types import ApiError, Settings


def validate_email(email):
    if not isinstance(email, str) or '\r' in email or '\n' in email:
        raise ApiError('INVALID_REQUEST', 400)
    email = email.strip().lower()
    name, parsed = parseaddr(email)
    if (not email or len(email) > 254 or name or parsed != email
            or not re.fullmatch(r'[^\s@<>,;:"()]+@[^\s@<>,;:"()]+\.[^\s@<>,;:"()]+', email)):
        raise ApiError('INVALID_REQUEST', 400)
    return email


# smtplib timeouts apply per socket step; this bounds the whole send.
SEND_TOTAL_SECONDS = 15


class SMTPMail:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix='smtp')

    def _send_registration_mail(self, email, subject, content):
        future = self._pool.submit(self._deliver, email, subject, content)
        try:
            return future.result(timeout=SEND_TOTAL_SECONDS)
        except FutureTimeout:
            logging.getLogger(__name__).error('MAIL_TIMEOUT')
            raise ApiError('MAIL_UNAVAILABLE', 502) from None

    def _deliver(self, email, subject, content):
        email = validate_email(email)
        settings = self.settings
        if settings.smtp_from != settings.smtp_user:
            raise ApiError('MAIL_UNAVAILABLE', 502)
        if settings.app_env == 'test' and email not in settings.test_recipient_allowlist:
            raise ApiError('TEST_RECIPIENT_NOT_ALLOWED', 403)
        message = EmailMessage()
        message['From'] = settings.smtp_from
        message['To'] = email
        message['Subject'] = subject
        message.set_content(content)
        try:
            with smtplib.SMTP('smtp.gmail.com', 587, timeout=10) as smtp:
                smtp.ehlo()
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
                smtp.login(settings.smtp_user, settings.smtp_app_password)
                refused = smtp.send_message(message, from_addr=settings.smtp_from, to_addrs=[email])
                if refused:
                    raise smtplib.SMTPRecipientsRefused(refused)
        except smtplib.SMTPAuthenticationError:
            logging.getLogger(__name__).error('MAIL_AUTH')
            raise ApiError('MAIL_UNAVAILABLE', 502) from None
        except (smtplib.SMTPException, OSError):
            logging.getLogger(__name__).error('MAIL_SEND')
            raise ApiError('MAIL_UNAVAILABLE', 502) from None

    def send_registration_otp_mail(self, email: str, otp: str) -> None:
        if not isinstance(otp, str) or not re.fullmatch(r'[0-9]{6}', otp):
            raise ApiError('INVALID_REQUEST', 400)
        self._send_registration_mail(email, 'FlexMix email verification',
                                     'Your verification code is ' + otp + '. It expires in 10 minutes.')

    def send_registration_notice(self, email: str) -> None:
        self._send_registration_mail(email, 'FlexMix registration notice',
                                     'Someone attempted to register using this email address. Your account was not changed.')
