import os
import unittest
from unittest.mock import patch

from server.configuration.skeleton import load_local_environment


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
