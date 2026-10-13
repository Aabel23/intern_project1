import os
import base64
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from server.configuration.skeleton import load_local_environment, load_settings


class LocalEnvironmentTests(unittest.TestCase):
    @patch('server.configuration.skeleton.Path.is_file', return_value=True)
    @patch('server.configuration.skeleton.Path.read_text')
    def test_loads_config_without_overriding_process_environment(self, read, exists):
        read.return_value = '# local config\n\nDB_HOST=127.0.0.1\nDB_PASSWORD=a=b\n'
        with patch.dict(os.environ, {'DB_HOST': 'external-host'}, clear=True):
            load_local_environment()
            self.assertEqual(os.environ['DB_HOST'], 'external-host')
            self.assertEqual(os.environ['DB_PASSWORD'], 'a=b')

    @patch('server.configuration.skeleton.Path.is_file', return_value=False)
    def test_env_file_is_optional(self, exists):
        with patch.dict(os.environ, {}, clear=True):
            load_local_environment()
            self.assertEqual(dict(os.environ), {})

    @patch('server.configuration.skeleton.Path.is_file', return_value=True)
    @patch('server.configuration.skeleton.Path.read_text', return_value='invalid config with secret')
    def test_invalid_line_does_not_expose_its_value(self, read, exists):
        with self.assertRaisesRegex(ValueError, '^CONFIG_INVALID$'):
            load_local_environment()

    def test_lan_http_requires_private_bind_and_keeps_inner_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            for name in ('hpke', 'sign', 'trust'):
                path = Path(directory) / name
                path.write_bytes(b'test-only')
                path.chmod(0o600)
            env = {
                'DB_HOST': '127.0.0.1', 'DB_NAME': 'test_only',
                'DB_USER': 'test_only', 'DB_PASSWORD': 'test_only',
                'SMTP_USER': 'sender@example.invalid',
                'SMTP_FROM': 'sender@example.invalid',
                'SMTP_APP_PASSWORD': 'test_only',
                'OTP_HASH_SECRET': base64.urlsafe_b64encode(b'x' * 32).decode().rstrip('='),
                'APP_ENV': 'production', 'SERVER_TRANSPORT': 'http',
                'SERVER_BIND_HOST': '192.168.1.10',
                'SERVER_HPKE_KEY_FILE': str(Path(directory) / 'hpke'),
                'SERVER_SIGNING_KEY_FILE': str(Path(directory) / 'sign'),
                'SERVER_TRUST_FILE': str(Path(directory) / 'trust'),
            }
            with patch.dict(os.environ, env, clear=True):
                settings = load_settings()
                self.assertEqual(settings.server_transport, 'http')
                self.assertEqual((settings.tls_cert_file, settings.tls_key_file), ('', ''))
                self.assertEqual(settings.server_bind_port, 8080)
            for host in ('0.0.0.0', '8.8.8.8'):
                with self.subTest(host=host), patch.dict(os.environ, {**env, 'SERVER_BIND_HOST': host}, clear=True):
                    with self.assertRaisesRegex(ValueError, '^CONFIG_INVALID$'):
                        load_settings()
