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
from server.lib.http import http_rate_limit as rate_limit
from server.lib.security.user_session import create_session


class StartpointTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        override = patch('server.database.connection.DB_PATH', Path(directory.name) / 'test.db')
        override.start()
        self.addCleanup(override.stop)
        init_db()
        # Long-poll ngắn để máy hỏi lệnh khi hộp thư rỗng không làm chậm test.
        wait = patch('server.lib.machine.machine_transport.POLL_WAIT_SECONDS', 0.3)
        wait.start()
        self.addCleanup(wait.stop)
        rate_limit.IP_REQUESTS.clear()
        self.server = main.create_server(('127.0.0.1', 0))
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
        for path in ('/app/user/account/register', '/app/user/otp/send', '/app/user/otp/verify',
                     '/app/user/session/login', '/app/user/session/verify'):
            status, data = self.request(path, {})
            self.assertEqual(status, 400)
            self.assertFalse(data['valid'])
        with get_connection() as conn:
            user_id = conn.execute(
                "INSERT INTO users (full_name, username, password, email)"
                " VALUES ('t', 't', 'x', 't@test.local')"
            ).lastrowid
        token = create_session(user_id)
        status, machine = self.request('/app/user/machine/register', {
            'machine_name': 'FlexMix-Test', 'product_key': 'test-key', 'token': token,
        })
        self.assertEqual(status, 200)
        status, _ = self.request('/app/machine/share/create', {
            'token': token, 'machine_id': machine['machine_id'],
        })
        self.assertEqual(status, 200)
        status, mine = self.request('/app/user/machine/list', {'token': token})
        self.assertEqual(mine['machines'][0]['role'], 'owner')
        # Máy xưng danh bằng product key, server tự tra machine_id đã cấp.
        status, _ = self.request('/machine/heartbeat/send', {'product_key': 'test-key'})
        self.assertEqual(status, 200)
        status, result = self.request(f"/app/machine/status/get?machine_id={machine['machine_id']}")
        self.assertTrue(result['online'])
        self.assertEqual(self.request('/missing', {})[0], 404)

    def make_owner_machine(self, username='owner', key='relay-key'):
        with get_connection() as conn:
            user_id = conn.execute(
                "INSERT INTO users (full_name, username, password, email) VALUES (?, ?, 'x', ?)",
                (username, username, f'{username}@test.local'),
            ).lastrowid
        token = create_session(user_id)
        _, machine = self.request('/app/user/machine/register', {
            'machine_name': 'FlexMix-Relay', 'product_key': key, 'token': token,
        })
        return token, machine['machine_id']

    def test_waiting_app_does_not_block_machine(self):
        from server.lib.machine import machine_transport as relay
        token, machine_id = self.make_owner_machine()
        self.request('/machine/heartbeat/send', {'product_key': 'relay-key'})
        with ThreadPoolExecutor(max_workers=1) as pool:
            app = pool.submit(self.request, '/app/machine/ingredient/get', {
                'token': token, 'machine_id': machine_id, 'version': 0,
            })
            # App đang chờ kết quả trong khi máy vẫn hỏi lệnh được.
            command = None
            for _ in range(100):
                status, data = self.request('/machine/command/poll', {'product_key': 'relay-key'})
                command = data['lenh']
                if command is not None:
                    break
                threading.Event().wait(0.02)
            self.assertEqual((command['instruction'], command['data']), ('nhan_kho', {'version': 0}))
            self.assertNotIn('token', command)
            self.request('/machine/result/send', {
                'product_key': 'relay-key', 'id': command['id'], 'ket_qua': {'ok': True},
            })
            self.assertEqual(app.result(timeout=3), (200, {'ok': True}))
        self.assertEqual(relay.HOP_THU.get(machine_id), [])

    def test_long_poll_returns_as_soon_as_command_arrives(self):
        import time
        token, machine_id = self.make_owner_machine()
        self.request('/machine/heartbeat/send', {'product_key': 'relay-key'})
        with patch('server.lib.machine.machine_transport.POLL_WAIT_SECONDS', 4), ThreadPoolExecutor(max_workers=1) as pool:
            started = time.monotonic()
            poll = pool.submit(self.request, '/machine/command/poll', {'product_key': 'relay-key'})
            threading.Event().wait(0.3)
            with ThreadPoolExecutor(max_workers=1) as app_pool:
                app = app_pool.submit(self.request, '/app/machine/ingredient/get', {
                    'token': token, 'machine_id': machine_id, 'version': 0,
                })
                _, data = poll.result(timeout=5)
                # Máy nhận lệnh ngay khi app gửi, không chờ hết thời gian long-poll.
                self.assertLess(time.monotonic() - started, 2)
                self.assertEqual(data['lenh']['instruction'], 'nhan_kho')
                self.request('/machine/result/send', {
                    'product_key': 'relay-key', 'id': data['lenh']['id'], 'ket_qua': {'ok': 1},
                })
                self.assertEqual(app.result(timeout=3), (200, {'ok': 1}))

    def test_relay_checks_login_owner_and_product_key(self):
        from server.lib.machine import machine_transport as relay
        token, machine_id = self.make_owner_machine()
        other, other_machine = self.make_owner_machine('other', 'other-key')
        status, data = self.request('/app/machine/ingredient/get', {'machine_id': machine_id, 'version': 0})
        self.assertEqual(status, 401)
        self.assertTrue(data['login_required'])
        status, _ = self.request('/app/machine/ingredient/get', {
            'token': other, 'machine_id': machine_id, 'version': 0,
        })
        self.assertEqual(status, 403)
        self.assertEqual(self.request('/machine/heartbeat/send', {'product_key': 'sai-key'})[0], 403)
        self.assertEqual(self.request('/machine/command/poll', {})[0], 403)
        # Máy chưa heartbeat thì báo offline ngay, không để app chờ.
        status, data = self.request('/app/machine/ingredient/get', {
            'token': token, 'machine_id': machine_id, 'version': 0,
        })
        self.assertEqual((status, data), (503, {'loi': 'Máy đang offline'}))
        # Máy khác không lấy được hay trả kết quả cho lệnh không thuộc về nó.
        self.request('/machine/heartbeat/send', {'product_key': 'relay-key'})
        with ThreadPoolExecutor(max_workers=1) as pool:
            app = pool.submit(self.request, '/app/machine/ingredient/get', {
                'token': token, 'machine_id': machine_id, 'version': 0,
            })
            for _ in range(100):
                with relay.KHOA:
                    pending = list(relay.HOP_THU.get(machine_id, []))
                if pending:
                    break
                threading.Event().wait(0.02)
            _, data = self.request('/machine/command/poll', {'product_key': 'other-key'})
            self.assertIsNone(data['lenh'])
            self.request('/machine/result/send', {
                'product_key': 'other-key', 'id': pending[0]['id'], 'ket_qua': {'gia': True},
            })
            _, data = self.request('/machine/command/poll', {'product_key': 'relay-key'})
            self.request('/machine/result/send', {
                'product_key': 'relay-key', 'id': data['lenh']['id'], 'ket_qua': {'that': True},
            })
            self.assertEqual(app.result(timeout=3), (200, {'that': True}))

    def test_timed_out_command_is_not_run_or_answered_later(self):
        token, machine_id = self.make_owner_machine()
        self.request('/machine/heartbeat/send', {'product_key': 'relay-key'})
        refill = {'token': token, 'machine_id': machine_id, 'target': 'all', 'value': 'full'}

        def take():
            for _ in range(20):
                lenh = self.request('/machine/command/poll', {'product_key': 'relay-key'})[1]['lenh']
                if lenh is not None:
                    return lenh
            self.fail('Máy không nhận được lệnh')

        with patch('server.lib.machine.machine_transport.COMMAND_TIMEOUT_SECONDS', 1):
            # Máy còn heartbeat nhưng chưa lấy lệnh: hết giờ thì hủy, online lại không nạp kho lần nữa.
            status, data = self.request('/app/machine/ingredient/refill', refill)
            self.assertEqual((status, data), (502, {'loi': 'Máy không phản hồi, lệnh đã được hủy'}))
            self.assertIsNone(self.request('/machine/command/poll', {'product_key': 'relay-key'})[1]['lenh'])
            # Máy lấy lệnh nhưng trả muộn: kết quả muộn không thành kết quả của lần hỏi sau.
            with ThreadPoolExecutor(max_workers=1) as pool:
                late = pool.submit(self.request, '/app/machine/ingredient/get', {
                    'token': token, 'machine_id': machine_id, 'version': 0,
                })
                old = take()
                self.assertEqual(late.result(timeout=3),
                                 (502, {'loi': 'Máy chưa trả kết quả, hãy tải lại để kiểm tra'}))
                retry = pool.submit(self.request, '/app/machine/ingredient/get', {
                    'token': token, 'machine_id': machine_id, 'version': 0,
                })
                new = take()
                self.request('/machine/result/send', {
                    'product_key': 'relay-key', 'id': old['id'], 'ket_qua': {'cu': True},
                })
                self.request('/machine/result/send', {
                    'product_key': 'relay-key', 'id': new['id'], 'ket_qua': {'moi': True},
                })
                self.assertEqual(retry.result(timeout=3), (200, {'moi': True}))

    def test_owner_removes_machine_and_same_tag_can_register_again(self):
        owner, machine_id = self.make_owner_machine(key="reusable-tag")
        other, _ = self.make_owner_machine("new-owner", "other-tag")
        status, removed = self.request('/app/user/machine/remove', {'token': owner, 'machine_id': machine_id})
        self.assertEqual(status, 200)
        self.assertTrue(removed['deleted'])
        status, registered = self.request('/app/user/machine/register', {
            'token': other, 'machine_name': 'FlexMix', 'product_key': 'reusable-tag',
        })
        self.assertEqual(status, 200)
        self.assertTrue(registered['created'])
        _, mine = self.request('/app/user/machine/list', {'token': other})
        self.assertIn((registered['machine_id'], 'owner'),
                      [(machine['machine_id'], machine['role']) for machine in mine['machines']])

    def test_cleanup_callbacks(self):
        # Mỗi module tự khai tick(); server chỉ gọi các tick đó định kỳ.
        from server.service.user_login import user_login_main
        from server.service.user_register import user_register_main
        with patch.object(user_register_main, 'tick') as registration:
            with patch.object(user_login_main, 'tick') as login:
                self.server.service_actions()
                registration.assert_called()
                login.assert_called()


if __name__ == '__main__':
    unittest.main()
