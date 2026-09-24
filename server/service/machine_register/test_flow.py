"""Test HTTP thật và SQLite tạm, không sửa database đang dùng."""

import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from server.database.connection import get_connection
from server.database.machine.init_db import init_db
from server.service.machine_register.machine_register_flow import receive_register
from server.service.user_login.session import create_session
from http.server import ThreadingHTTPServer
from server.service.machine_register.machine_register_api import MachineRegisterHandler


class MachineRegisterTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        database = Path(self.directory.name) / 'test.db'
        override = patch('server.database.connection.DB_PATH', database)
        override.start()
        self.addCleanup(override.stop)
        init_db()
        self.token = self.make_user('owner')
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), MachineRegisterHandler)
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()
        self.addCleanup(self.stop_server)

    @staticmethod
    def make_user(username):
        with get_connection() as conn:
            user_id = conn.execute(
                "INSERT INTO users (full_name, username, password, email) VALUES (?, ?, 'x', ?)",
                (username, username, f'{username}@test.local'),
            ).lastrowid
        return create_session(user_id)

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.worker.join()

    def post(self, path, data):
        url = f'http://127.0.0.1:{self.server.server_port}{path}'
        request = Request(url, data=json.dumps(data).encode(), headers={'Content-Type': 'application/json'})
        try:
            response = urlopen(request, timeout=3)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.loads(response.read())

    def test_register_retry_and_verify(self):
        packet = {'type': 'pairing', 'machine_name': 'FlexMix-01', 'product_key': 'test-key',
                  'token': self.token}
        status, first = self.post('/app/dang-ky-may', packet)
        self.assertEqual(status, 200)
        self.assertTrue(first['created'])
        status, second = self.post('/app/dang-ky-may', packet)
        self.assertEqual(first['machine_id'], second['machine_id'])
        self.assertFalse(second['created'])
        status, verified = self.post('/app/xac-minh-dang-ky-may', {
            'machine_id': first['machine_id'], 'product_key': 'test-key',
        })
        self.assertTrue(verified['verified'])
        status, rejected = self.post('/app/xac-minh-dang-ky-may', {
            'machine_id': first['machine_id'], 'product_key': 'wrong-key',
        })
        self.assertEqual(status, 400)
        self.assertFalse(rejected['valid'])
        with get_connection() as conn:
            rows = conn.execute('SELECT * FROM machines').fetchall()
        self.assertEqual(len(rows), 1)
        self.assertNotEqual(rows[0]['product_key_hash'], 'test-key')
        with get_connection() as conn:
            owners = conn.execute("SELECT role FROM machine_managers").fetchall()
        self.assertEqual([row['role'] for row in owners], ['owner'])

    def test_owner_and_login_required(self):
        packet = {'machine_name': 'FlexMix-01', 'product_key': 'owned-key'}
        self.assertEqual(self.post('/app/dang-ky-may', packet)[0], 400)
        self.assertEqual(self.post('/app/dang-ky-may', {**packet, 'token': self.token})[0], 200)
        status, result = self.post('/app/dang-ky-may', {**packet, 'token': self.make_user('other')})
        self.assertEqual(status, 400)
        self.assertIn('chủ máy', result['message'])

    def test_invalid_data(self):
        for data in ([], {}, {'machine_name': 'FlexMix', 'product_key': 123}):
            status, result = self.post('/app/dang-ky-may', data)
            self.assertEqual(status, 400)
            self.assertFalse(result['valid'])

    def test_concurrent_requests_return_same_id(self):
        packet = {'machine_name': 'FlexMix-01', 'product_key': 'concurrent-key', 'token': self.token}
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(receive_register, [packet] * 4))
        self.assertEqual(len({result['machine_id'] for result in results}), 1)
        self.assertEqual(sum(result['created'] for result in results), 1)


if __name__ == '__main__':
    unittest.main()
