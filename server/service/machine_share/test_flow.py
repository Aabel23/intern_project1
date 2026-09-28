"""Chia sẻ máy bằng mã mời, dùng SQLite tạm."""

import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from server.database.connection import get_connection
from server.database.machine.init_db import init_db
from server.service.machine_register.machine_register_flow import receive_register
from server.lib.session import create_session
from server.lib.session import user_from_request
from server.service.dashboard_sync.machinelist_sync.machinelist_flow import list_my_machines
from .share_flow import accept_invite, create_invite, list_staff, revoke_staff


class MachineShareTest(unittest.TestCase):
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

    @staticmethod
    def make_user(username):
        with get_connection() as conn:
            user_id = conn.execute(
                "INSERT INTO users (full_name, username, password, email) VALUES (?, ?, 'x', ?)",
                (username, username, f'{username}@test.local'),
            ).lastrowid
        return create_session(user_id)

    def roles(self, token):
        machines = list_my_machines({'token': token})['machines']
        return {machine['machine_id']: machine['role'] for machine in machines}

    def test_owner_shares_once(self):
        invite = create_invite({'token': self.owner, 'machine_id': self.machine_id})
        self.assertTrue(invite['valid'])
        self.assertEqual(self.roles(self.staff), {})
        accepted = accept_invite({'token': self.staff, 'code': invite['code']})
        self.assertTrue(accepted['valid'])
        self.assertEqual(accepted['machine_name'], 'FlexMix-01')
        self.assertEqual(self.roles(self.staff), {self.machine_id: 'manager'})
        # Mã đã dùng thì người khác không dùng lại được.
        other = self.make_user('other')
        self.assertFalse(accept_invite({'token': other, 'code': invite['code']})['valid'])

    def test_only_owner_creates_invite(self):
        invite = create_invite({'token': self.owner, 'machine_id': self.machine_id})
        accept_invite({'token': self.staff, 'code': invite['code']})
        self.assertFalse(create_invite({'token': self.staff, 'machine_id': self.machine_id})['valid'])
        self.assertFalse(create_invite({'machine_id': self.machine_id})['valid'])

    def test_owner_keeps_role_and_invite_expires(self):
        invite = create_invite({'token': self.owner, 'machine_id': self.machine_id})
        accept_invite({'token': self.owner, 'code': invite['code']})
        self.assertEqual(self.roles(self.owner), {self.machine_id: 'owner'})
        invite = create_invite({'token': self.owner, 'machine_id': self.machine_id})
        later = time.time() + 600
        with patch('server.service.machine_share.share_flow.time.time', return_value=later):
            self.assertFalse(accept_invite({'token': self.staff, 'code': invite['code']})['valid'])


    def test_owner_lists_and_revokes_staff(self):
        invite = create_invite({'token': self.owner, 'machine_id': self.machine_id})
        accept_invite({'token': self.staff, 'code': invite['code']})
        result = list_staff({'token': self.owner, 'machine_id': self.machine_id})
        self.assertEqual([member['username'] for member in result['staff']], ['staff'])
        staff_id = result['staff'][0]['user_id']
        # Nhân viên không xem hay thu hồi được quyền, kể cả của chính mình.
        self.assertFalse(list_staff({'token': self.staff, 'machine_id': self.machine_id})['valid'])
        self.assertFalse(revoke_staff({
            'token': self.staff, 'machine_id': self.machine_id, 'user_id': staff_id,
        })['valid'])
        self.assertTrue(revoke_staff({
            'token': self.owner, 'machine_id': self.machine_id, 'user_id': staff_id,
        })['valid'])
        self.assertEqual(self.roles(self.staff), {})
        # Không thu hồi được quyền chủ máy.
        owner_id = user_from_request({'token': self.owner})
        revoke_staff({'token': self.owner, 'machine_id': self.machine_id, 'user_id': owner_id})
        self.assertEqual(self.roles(self.owner), {self.machine_id: 'owner'})

    def test_new_invite_replaces_unused_one(self):
        first = create_invite({'token': self.owner, 'machine_id': self.machine_id})
        second = create_invite({'token': self.owner, 'machine_id': self.machine_id})
        self.assertFalse(accept_invite({'token': self.staff, 'code': first['code']})['valid'])
        self.assertTrue(accept_invite({'token': self.staff, 'code': second['code']})['valid'])

if __name__ == '__main__':
    unittest.main()
