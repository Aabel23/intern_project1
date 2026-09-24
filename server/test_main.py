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
        # Máy xưng danh bằng product key, server tự tra machine_id đã cấp.
        status, _ = self.request('/machine/heartbeat', {'product_key': 'test-key'})
        self.assertEqual(status, 200)
        status, result = self.request(f"/machine/trang-thai?machine_id={machine['machine_id']}")
        self.assertTrue(result['online'])
        self.assertEqual(self.request('/missing', {})[0], 404)

    def make_owner_machine(self, username='owner', key='relay-key'):
        with get_connection() as conn:
            user_id = conn.execute(
                "INSERT INTO users (full_name, username, password, email) VALUES (?, ?, 'x', ?)",
                (username, username, f'{username}@test.local'),
            ).lastrowid
        token = create_session(user_id)
        _, machine = self.request('/app/dang-ky-may', {
            'machine_name': 'FlexMix-Relay', 'product_key': key, 'token': token,
        })
        return token, machine['machine_id']

    def test_waiting_app_does_not_block_machine(self):
        from server import server as relay
        token, machine_id = self.make_owner_machine()
        self.request('/machine/heartbeat', {'product_key': 'relay-key'})
        with ThreadPoolExecutor(max_workers=1) as pool:
            app = pool.submit(self.request, '/app/gui-lenh', {
                'token': token, 'machine_id': machine_id, 'ten': 'xem_menu', 'thamso': {},
            })
            # App đang chờ kết quả trong khi máy vẫn hỏi lệnh được.
            command = None
            for _ in range(100):
                status, data = self.request('/machine/hoi-lenh', {'product_key': 'relay-key'})
                command = data['lenh']
                if command is not None:
                    break
                threading.Event().wait(0.02)
            self.assertEqual(command['ten'], 'xem_menu')
            self.assertNotIn('token', command)
            self.request('/machine/tra-ket-qua', {
                'product_key': 'relay-key', 'id': command['id'], 'ket_qua': {'ok': True},
            })
            self.assertEqual(app.result(timeout=3), (200, {'ok': True}))
        self.assertEqual(relay.HOP_THU.get(machine_id), [])

    def test_relay_checks_login_owner_and_product_key(self):
        from server import server as relay
        token, machine_id = self.make_owner_machine()
        other, other_machine = self.make_owner_machine('other', 'other-key')
        status, data = self.request('/app/gui-lenh', {'machine_id': machine_id, 'ten': 'xem_menu'})
        self.assertEqual(status, 401)
        self.assertTrue(data['login_required'])
        status, _ = self.request('/app/gui-lenh', {
            'token': other, 'machine_id': machine_id, 'ten': 'xem_menu',
        })
        self.assertEqual(status, 403)
        self.assertEqual(self.request('/machine/heartbeat', {'product_key': 'sai-key'})[0], 403)
        self.assertEqual(self.request('/machine/hoi-lenh', {})[0], 403)
        # Máy chưa heartbeat thì báo offline ngay, không để app chờ.
        status, data = self.request('/app/gui-lenh', {
            'token': token, 'machine_id': machine_id, 'ten': 'xem_menu',
        })
        self.assertEqual(data, {'loi': 'Máy đang offline'})
        # Máy khác không lấy được hay trả kết quả cho lệnh không thuộc về nó.
        self.request('/machine/heartbeat', {'product_key': 'relay-key'})
        with ThreadPoolExecutor(max_workers=1) as pool:
            app = pool.submit(self.request, '/app/gui-lenh', {
                'token': token, 'machine_id': machine_id, 'ten': 'xem_menu',
            })
            for _ in range(100):
                with relay.KHOA:
                    pending = list(relay.HOP_THU.get(machine_id, []))
                if pending:
                    break
                threading.Event().wait(0.02)
            _, data = self.request('/machine/hoi-lenh', {'product_key': 'other-key'})
            self.assertIsNone(data['lenh'])
            self.request('/machine/tra-ket-qua', {
                'product_key': 'other-key', 'id': pending[0]['id'], 'ket_qua': {'gia': True},
            })
            _, data = self.request('/machine/hoi-lenh', {'product_key': 'relay-key'})
            self.request('/machine/tra-ket-qua', {
                'product_key': 'relay-key', 'id': data['lenh']['id'], 'ket_qua': {'that': True},
            })
            self.assertEqual(app.result(timeout=3), (200, {'that': True}))

    def test_cleanup_callbacks(self):
        with patch.object(main, 'cleanup_registration') as registration:
            with patch.object(main, 'cleanup_login') as login:
                self.server.service_actions()
                registration.assert_called()
                login.assert_called()


if __name__ == '__main__':
    unittest.main()
