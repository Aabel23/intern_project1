"""Chạy: python -m unittest tests.python.test_machine_list"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from server.database.connection import get_connection
from server.database.machine.init_db import init_db
from server.lib.security.user_session import create_session, user_from_request
from server.service.dashboard_sync.machinelist_sync.machine_list_get import list_my_machines
from server.service.dashboard_sync.machinelist_sync.machine_list_rename import rename_machine
from server.service.dashboard_sync.machinelist_sync.machine_list_remove import remove_machine


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
        self.machine_id = 'fm_test'
        owner_id = user_from_request({'token': self.owner})
        staff_id = user_from_request({'token': self.staff})
        with get_connection() as conn:
            conn.execute("INSERT INTO machines (machine_id, name) VALUES (?, ?)",
                         (self.machine_id, 'FlexMix-01'))
            conn.executemany("INSERT INTO machine_managers (machine_id, user_id, role) VALUES (?, ?, ?)",
                             [(self.machine_id, owner_id, 'owner'), (self.machine_id, staff_id, 'manager')])

    @staticmethod
    def make_user(username):
        with get_connection() as conn:
            user_id = conn.execute(
                "INSERT INTO users (full_name, username, password, email) VALUES (?, ?, 'x', ?)",
                (username, username, f'{username}@test.local'),
            ).lastrowid
        return create_session(user_id)

    def call(self, route, data):
        """Gọi flow, trả thân kết quả."""
        return route(data)

    def rename(self, data):
        return self.call(rename_machine, data)

    def remove(self, data):
        return self.call(remove_machine, data)

    def machines(self, token):
        return {m['machine_id']: m for m in self.call(list_my_machines, {'token': token})['machines']}

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

    def test_owner_deletes_machine_and_manager_records(self):
        result = self.remove({'token': self.owner, 'machine_id': self.machine_id})
        self.assertEqual((result['valid'], result['deleted']), (True, True))
        self.assertEqual(self.machines(self.owner), {})
        self.assertEqual(self.machines(self.staff), {})
        with get_connection() as conn:
            self.assertIsNone(conn.execute("SELECT 1 FROM machines WHERE machine_id=?", (self.machine_id,)).fetchone())
            self.assertIsNone(conn.execute("SELECT 1 FROM machine_managers WHERE machine_id=?", (self.machine_id,)).fetchone())

    def test_requires_login(self):
        self.assertTrue(self.call(list_my_machines, {})['login_required'])
        self.assertTrue(self.rename({'machine_id': self.machine_id, 'name': 'x'})['login_required'])
        self.assertTrue(self.remove({'machine_id': self.machine_id})['login_required'])

    def test_invalid_input_and_outsider_cannot_change_machine(self):
        outsider = self.make_user('outsider')
        self.assertEqual(self.machines(outsider), {})
        for action in (self.rename, self.remove):
            for machine_id in (None, '', True, 'x' * 101):
                with self.subTest(action=action.__name__, machine_id=machine_id):
                    self.assertEqual(action({'token': self.owner, 'machine_id': machine_id, 'name': 'x'}),
                                     {'valid': False, 'message': 'Thiếu mã máy hợp lệ'})
            self.assertFalse(action({'token': outsider, 'machine_id': self.machine_id, 'name': 'x'})['valid'])
        for name in (None, True, '', '   ', 'x' * 151):
            with self.subTest(name=name):
                self.assertEqual(self.rename({'token': self.owner, 'machine_id': self.machine_id, 'name': name}),
                                 {'valid': False, 'message': 'Tên máy phải có 1-150 ký tự'})
        self.assertEqual(self.machines(self.owner)[self.machine_id]['name'], 'FlexMix-01')
        result = self.rename({'token': self.owner, 'machine_id': self.machine_id, 'name': ' ' + 'x' * 150 + ' '})
        self.assertEqual(result, {'valid': True, 'name': 'x' * 150, 'message': 'Đã đổi tên máy'})


if __name__ == '__main__':
    unittest.main()
