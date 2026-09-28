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
from server.lib import rate_limit
from server.service.user_login.session import create_session


class StartpointTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        override = patch('server.database.connection.DB_PATH', Path(directory.name) / 'test.db')
        override.start()
        self.addCleanup(override.stop)
        init_db()
        # Long-poll ngắn để máy hỏi lệnh khi hộp thư rỗng không làm chậm test.
        wait = patch('server.service.machine_relay.relay_queue.POLL_WAIT_SECONDS', 0.3)
        wait.start()
        self.addCleanup(wait.stop)
        rate_limit.IP_REQUESTS.clear()
        self.server = main.Server(('127.0.0.1', 0), main.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        rate_limit.IP_REQUESTS.clear()

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
        from server.service.machine_relay import relay_queue as relay
        token, machine_id = self.make_owner_machine()
        self.request('/machine/heartbeat', {'product_key': 'relay-key'})
        with ThreadPoolExecutor(max_workers=1) as pool:
            app = pool.submit(self.request, '/app/nhan-kho', {
                'token': token, 'machine_id': machine_id, 'version': 0,
            })
            # App đang chờ kết quả trong khi máy vẫn hỏi lệnh được.
            command = None
            for _ in range(100):
                status, data = self.request('/machine/hoi-lenh', {'product_key': 'relay-key'})
                command = data['lenh']
                if command is not None:
                    break
                threading.Event().wait(0.02)
            self.assertEqual((command['instruction'], command['data']), ('nhan_kho', {'version': 0}))
            self.assertNotIn('token', command)
            self.request('/machine/tra-ket-qua', {
                'product_key': 'relay-key', 'id': command['id'], 'ket_qua': {'ok': True},
            })
            self.assertEqual(app.result(timeout=3), (200, {'ok': True}))
        self.assertEqual(relay.HOP_THU.get(machine_id), [])

    def test_long_poll_returns_as_soon_as_command_arrives(self):
        import time
        token, machine_id = self.make_owner_machine()
        self.request('/machine/heartbeat', {'product_key': 'relay-key'})
        with patch('server.service.machine_relay.relay_queue.POLL_WAIT_SECONDS', 4), ThreadPoolExecutor(max_workers=1) as pool:
            started = time.monotonic()
            poll = pool.submit(self.request, '/machine/hoi-lenh', {'product_key': 'relay-key'})
            threading.Event().wait(0.3)
            with ThreadPoolExecutor(max_workers=1) as app_pool:
                app = app_pool.submit(self.request, '/app/nhan-kho', {
                    'token': token, 'machine_id': machine_id, 'version': 0,
                })
                _, data = poll.result(timeout=5)
                # Máy nhận lệnh ngay khi app gửi, không chờ hết thời gian long-poll.
                self.assertLess(time.monotonic() - started, 2)
                self.assertEqual(data['lenh']['instruction'], 'nhan_kho')
                self.request('/machine/tra-ket-qua', {
                    'product_key': 'relay-key', 'id': data['lenh']['id'], 'ket_qua': {'ok': 1},
                })
                self.assertEqual(app.result(timeout=3), (200, {'ok': 1}))

    def test_relay_checks_login_owner_and_product_key(self):
        from server.service.machine_relay import relay_queue as relay
        token, machine_id = self.make_owner_machine()
        other, other_machine = self.make_owner_machine('other', 'other-key')
        status, data = self.request('/app/nhan-kho', {'machine_id': machine_id, 'version': 0})
        self.assertEqual(status, 401)
        self.assertTrue(data['login_required'])
        status, _ = self.request('/app/nhan-kho', {
            'token': other, 'machine_id': machine_id, 'version': 0,
        })
        self.assertEqual(status, 403)
        self.assertEqual(self.request('/machine/heartbeat', {'product_key': 'sai-key'})[0], 403)
        self.assertEqual(self.request('/machine/hoi-lenh', {})[0], 403)
        # Máy chưa heartbeat thì báo offline ngay, không để app chờ.
        status, data = self.request('/app/nhan-kho', {
            'token': token, 'machine_id': machine_id, 'version': 0,
        })
        self.assertEqual((status, data), (503, {'loi': 'Máy đang offline'}))
        # Máy khác không lấy được hay trả kết quả cho lệnh không thuộc về nó.
        self.request('/machine/heartbeat', {'product_key': 'relay-key'})
        with ThreadPoolExecutor(max_workers=1) as pool:
            app = pool.submit(self.request, '/app/nhan-kho', {
                'token': token, 'machine_id': machine_id, 'version': 0,
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
        # Mỗi module tự khai tick(); server chỉ gọi các tick đó định kỳ.
        from server.service.user_login import login_api
        from server.service.user_register.user_register import user_register_api
        with patch.object(user_register_api, 'tick') as registration:
            with patch.object(login_api, 'tick') as login:
                self.server.service_actions()
                registration.assert_called()
                login.assert_called()


if __name__ == '__main__':
    unittest.main()
