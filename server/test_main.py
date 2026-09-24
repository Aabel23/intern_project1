"""Kiểm tra các dịch vụ chung cổng bằng HTTP thật, SQLite tạm."""

import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from server import main
from server.database.connection import get_connection
from server.database.machine.init_db import init_db
from server.service.user_login.session import create_session


class StartpointTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        override = patch('server.database.connection.DB_PATH', Path(directory.name) / 'test.db')
        override.start()
        self.addCleanup(override.stop)
        init_db()
        main.IP_REQUESTS.clear()
        self.server = main.Server(('127.0.0.1', 0), main.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        main.IP_REQUESTS.clear()

    def request(self, path, data=None):
        body = None if data is None else json.dumps(data).encode()
        url = f'http://127.0.0.1:{self.server.server_port}{path}'
        request = Request(url, data=body, headers={'Content-Type': 'application/json'})
        try:
            response = urlopen(request, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.loads(response.read())

    def test_services_share_one_port(self):
        for path in ('/app/dang-ky-nguoi-dung', '/app/gui-ma-otp', '/app/xac-minh-otp',
                     '/app/dang-nhap', '/app/xac-minh-dang-nhap'):
            status, data = self.request(path, {})
            self.assertEqual(status, 400)
            self.assertFalse(data['valid'])
        with get_connection() as conn:
            user_id = conn.execute(
                "INSERT INTO users (full_name, username, password, email)"
                " VALUES ('t', 't', 'x', 't@test.local')"
            ).lastrowid
        token = create_session(user_id)
        status, machine = self.request('/app/dang-ky-may', {
            'machine_name': 'FlexMix-Test', 'product_key': 'test-key', 'token': token,
        })
        self.assertEqual(status, 200)
        status, result = self.request('/app/xac-minh-dang-ky-may', {
            'machine_id': machine['machine_id'], 'product_key': 'test-key',
        })
        self.assertTrue(result['verified'])
        status, _ = self.request('/app/tao-ma-chia-se', {
            'token': token, 'machine_id': machine['machine_id'],
        })
        self.assertEqual(status, 200)
        status, mine = self.request('/app/may-cua-toi', {'token': token})
        self.assertEqual(mine['machines'][0]['role'], 'owner')
        self.request('/machine/heartbeat', {'machine_id': 'TEST'})
        status, result = self.request('/machine/trang-thai?machine_id=TEST')
        self.assertTrue(result['online'])
        self.assertEqual(self.request('/missing', {})[0], 404)

    def test_waiting_app_does_not_block_machine(self):
        from server import server as relay
        queued = threading.Event()
        original_put = relay.HOP_THU.put

        def put(command):
            original_put(command)
            queued.set()

        with patch.object(relay.HOP_THU, 'put', side_effect=put):
            with ThreadPoolExecutor(max_workers=1) as pool:
                app = pool.submit(self.request, '/app/gui-lenh', {
                    'machine_id': 'TEST', 'ten': 'xem_menu', 'thamso': {},
                })
                self.assertTrue(queued.wait(3))
                status, data = self.request('/machine/hoi-lenh')
                command = data['lenh']
                self.request('/machine/tra-ket-qua', {'id': command['id'], 'ket_qua': {'ok': True}})
                self.assertEqual(app.result(timeout=3), (200, {'ok': True}))

    def test_cleanup_callbacks(self):
        with patch.object(main, 'cleanup_registration') as registration:
            with patch.object(main, 'cleanup_login') as login:
                self.server.service_actions()
                registration.assert_called()
                login.assert_called()


if __name__ == '__main__':
    unittest.main()
