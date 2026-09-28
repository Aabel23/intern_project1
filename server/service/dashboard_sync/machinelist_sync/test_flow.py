"""Chạy: python -m unittest server.service.dashboard_sync.machinelist_sync.test_flow"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from server.database.connection import get_connection
from server.database.machine.init_db import init_db
from server.service.machine_register.machine_register_flow import receive_register
from server.service.machine_share.share_flow import accept_invite, create_invite
from server.service.user_login.session import create_session
from . import machinelist_flow as flow


class MachineListTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        override = patch('server.database.connection.DB_PATH', Path(directory.name) / 'test.db')
        override.start()
        self.addCleanup(override.stop)
        init_db()
        self.owner = self.make_user('owner')
        self.staff = self.make_user('staff')
        self.machine_id = receive_register({
            'machine_name': 'FlexMix-01', 'product_key': 'key', 'token': self.owner,
        })['machine_id']
        invite = create_invite({'token': self.owner, 'machine_id': self.machine_id})
        accept_invite({'token': self.staff, 'code': invite['code']})

    @staticmethod
    def make_user(username):
        with get_connection() as conn:
            user_id = conn.execute(
                "INSERT INTO users (full_name, username, password, email) VALUES (?, ?, 'x', ?)",
                (username, username, f'{username}@test.local'),
            ).lastrowid
        return create_session(user_id)

    def call(self, route, data):
        """Gọi flow, kiểm status khớp valid (200/400) như app đang nhận, trả thân kết quả."""
        result, status = route(data)
        self.assertEqual(status, 200 if result['valid'] else 400)
        return result

    def rename(self, data):
        return self.call(flow.rename_machine, data)

    def remove(self, data):
        return self.call(flow.remove_machine, data)

    def machines(self, token):
        return {m['machine_id']: m for m in self.call(flow.list_my_machines, {'token': token})['machines']}

    def test_only_owner_renames(self):
        self.assertFalse(self.rename({
            'token': self.staff, 'machine_id': self.machine_id, 'name': 'FlexMix-Moi',
        })['valid'])
        self.assertFalse(self.rename({
            'token': self.owner, 'machine_id': self.machine_id, 'name': '   ',
        })['valid'])
        result = self.rename({'token': self.owner, 'machine_id': self.machine_id, 'name': ' FlexMix-Moi '})
        self.assertTrue(result['valid'])
        self.assertEqual(self.machines(self.staff)[self.machine_id]['name'], 'FlexMix-Moi')

    def test_staff_removes_only_own_access(self):
        result = self.remove({'token': self.staff, 'machine_id': self.machine_id})
        self.assertEqual((result['valid'], result['deleted']), (True, False))
        self.assertEqual(self.machines(self.staff), {})
        self.assertIn(self.machine_id, self.machines(self.owner))
        # Không còn quyền thì không gỡ được nữa.
        self.assertFalse(self.remove({'token': self.staff, 'machine_id': self.machine_id})['valid'])

    def test_owner_deletes_machine_and_tag_can_register_again(self):
        result = self.remove({'token': self.owner, 'machine_id': self.machine_id})
        self.assertEqual((result['valid'], result['deleted']), (True, True))
        self.assertEqual(self.machines(self.owner), {})
        self.assertEqual(self.machines(self.staff), {})
        # Tem QR cũ đăng ký lại được, người đăng ký thành chủ mới.
        again = receive_register({'machine_name': 'FlexMix-01', 'product_key': 'key', 'token': self.staff})
        self.assertTrue(again['created'])
        self.assertEqual(self.machines(self.staff)[again['machine_id']]['role'], 'owner')

    def test_requires_login(self):
        self.assertTrue(self.call(flow.list_my_machines, {})['login_required'])
        self.assertTrue(self.rename({'machine_id': self.machine_id, 'name': 'x'})['login_required'])
        self.assertTrue(self.remove({'machine_id': self.machine_id})['login_required'])


if __name__ == '__main__':
    unittest.main()
