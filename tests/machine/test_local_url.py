import unittest
from unittest.mock import patch
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'version1.1'))

from machine.config.env import get_server_url


class LocalUrlTests(unittest.TestCase):
    def test_http_is_lan_only_and_https_remains_available(self):
        for url in ('http://192.168.1.10:8080', 'http://127.0.0.1:8080', 'https://example.invalid'):
            with self.subTest(url=url), patch('machine.config.env.read_env', return_value=url):
                self.assertEqual(get_server_url(), url)
        for url in ('http://8.8.8.8', 'http://example.invalid', 'http://192.168.1.10/path'):
            with self.subTest(url=url), patch('machine.config.env.read_env', return_value=url):
                with self.assertRaises(ValueError):
                    get_server_url()
