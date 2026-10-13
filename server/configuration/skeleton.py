"""Planner defaults and fail-closed environment configuration."""
import base64
import ipaddress
import os
from pathlib import Path
import stat
from server.src.types import Settings

OTP_SECONDS = 600
OTP_COOLDOWN_SECONDS = 60
OTP_MAX_ATTEMPTS = 5
OTP_LOCK_SECONDS = 900
EMAIL_SEND_LIMIT = 5
IP_SEND_LIMIT = 20
SEND_WINDOW_SECONDS = 3600
LOGIN_FAILURE_LIMIT = 10
LOGIN_WINDOW_SECONDS = 600
ACCESS_SECONDS = 3600
REFRESH_SECONDS = 2592000
SESSION_ABSOLUTE_SECONDS = 7776000
REFRESH_REUSE_GRACE_SECONDS = 30
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 256
ARGON2_CONCURRENCY = 4
CLAIM_SECONDS = 120
RELAY_SECONDS = 15
POLL_SECONDS = 20
MACHINE_HTTP_SECONDS = 25
APP_RELAY_HTTP_SECONDS = 20
ONLINE_GRACE_SECONDS = 30
TERMINAL_RELAY_SECONDS = 60
HTTP_MAX_BYTES = 65536
PLAINTEXT_MAX_BYTES = 16384
MAX_HTTP_REQUESTS = 256
MAX_POLL_REQUESTS = 160
MAX_RELAY_REQUESTS = 48
RELAY_DATA_MAX_BYTES = 12288
MACHINE_RESULT_CACHE = 32
HTTP_READ_SECONDS = 30
REPLAY_CACHE_LIMIT = 10000
REPLAY_CACHE_SECONDS = 600
BOOTSTRAP_LIMIT = 20
BOOTSTRAP_WINDOW_SECONDS = 60
CLOCK_SKEW_SECONDS = 300
TEST_RECIPIENTS = ('nguyenhoanganh15112005@gmail.com', '23200002@student.hcmus.edu.vn')


def load_local_environment() -> None:
    path = Path(__file__).with_name('.env')
    if not path.is_file():
        return
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        name, separator, value = line.partition('=')
        name = name.strip()
        if not separator or not name.isidentifier():
            raise ValueError('CONFIG_INVALID')
        os.environ.setdefault(name, value.strip())


def load_settings() -> Settings:
    try:
        def required(name):
            value = os.environ[name]
            if not value:
                raise ValueError()
            return value

        def port(name, default):
            value = int(os.environ.get(name, default))
            if not 1 <= value <= 65535:
                raise ValueError()
            return value

        def file(name, private=False):
            value = required(name)
            path = Path(value)
            if not path.is_absolute() or not path.is_file():
                raise ValueError()
            if private and os.name != 'nt' and stat.S_IMODE(path.stat().st_mode) != 0o600:
                raise ValueError()
            with path.open('rb') as stream:
                stream.read(1)
            return value

        smtp_user, smtp_from = required('SMTP_USER'), required('SMTP_FROM')
        if smtp_user != smtp_from or any(c in smtp_user for c in '\r\n'):
            raise ValueError()
        encoded = required('OTP_HASH_SECRET')
        secret = base64.urlsafe_b64decode(encoded + '=' * (-len(encoded) % 4))
        if len(secret) != 32 or base64.urlsafe_b64encode(secret).decode().rstrip('=') != encoded:
            raise ValueError()
        app_env = required('APP_ENV')
        if app_env not in ('test', 'production'):
            raise ValueError()
        allowlist = ()
        if app_env == 'test':
            allowlist = tuple(x.strip().lower() for x in required('TEST_RECIPIENT_ALLOWLIST').split(','))
            if len(allowlist) != 2 or set(allowlist) != set(TEST_RECIPIENTS):
                raise ValueError()
        elif 'TEST_RECIPIENT_ALLOWLIST' in os.environ:
            raise ValueError()
        transport = os.environ.get('SERVER_TRANSPORT', 'https')
        if transport not in ('http', 'https'):
            raise ValueError()
        bind_host = os.environ.get('SERVER_BIND_HOST', '127.0.0.1')
        if transport == 'http':
            address = ipaddress.ip_address(bind_host)
            if address.version != 4 or not (address.is_loopback or any(address in subnet for subnet in (
                    ipaddress.ip_network('10.0.0.0/8'), ipaddress.ip_network('172.16.0.0/12'),
                    ipaddress.ip_network('192.168.0.0/16')))):
                raise ValueError()
        return Settings(
            required('DB_HOST'), port('DB_PORT', '3306'), required('DB_NAME'),
            required('DB_USER'), required('DB_PASSWORD'), smtp_user, smtp_from,
            required('SMTP_APP_PASSWORD'), secret,
            bind_host, port('SERVER_BIND_PORT', '8080' if transport == 'http' else '8443'),
            file('TLS_CERT_FILE') if transport == 'https' else '',
            file('TLS_KEY_FILE', True) if transport == 'https' else '',
            file('SERVER_HPKE_KEY_FILE', True), file('SERVER_SIGNING_KEY_FILE', True),
            file('SERVER_TRUST_FILE'), app_env, allowlist, transport,
        )
    except (KeyError, ValueError, OSError):
        raise ValueError('CONFIG_INVALID') from None


def load_db_settings() -> Settings:
    """Operator CLI only needs the database; other server secrets stay unread."""
    try:
        value = int(os.environ.get('DB_PORT', '3306'))
        names = ('DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD')
        if not 1 <= value <= 65535 or not all(os.environ.get(n) for n in names):
            raise ValueError()
        return Settings(os.environ['DB_HOST'], value, os.environ['DB_NAME'], os.environ['DB_USER'],
                        os.environ['DB_PASSWORD'], '', '', '', b'', '', 0, '', '', '', '', '', 'production', ())
    except ValueError:
        raise ValueError('CONFIG_INVALID') from None
