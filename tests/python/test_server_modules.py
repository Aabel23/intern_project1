"""Kiểm tra route trùng và khởi tạo module không làm mất dữ liệu."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from server.database.connection import get_connection
from server.lib.module_server import ModuleServer
from server.main import create_server


class ModuleSetupTest(unittest.TestCase):
    def test_duplicate_routes_fail_before_setup(self):
        for method in ("GET", "POST"):
            calls = []
            fields = {"ROUTES": {}, "GET_ROUTES": ()}
            fields["ROUTES" if method == "POST" else "GET_ROUTES"] = {"/same": None}
            modules = [SimpleNamespace(__name__=name, setup=lambda: calls.append(True), **fields)
                       for name in ("first", "second")]
            with self.subTest(method=method), self.assertRaisesRegex(ValueError, method + " /same"):
                ModuleServer(("127.0.0.1", 0), modules)
            self.assertEqual(calls, [])

    def test_restarting_server_preserves_existing_invites(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("server.database.connection.DB_PATH", Path(directory) / "test.db"):
                with create_server(("127.0.0.1", 0)):
                    with get_connection() as conn:
                        conn.execute("INSERT INTO users (id, full_name, username, password, email)"
                                     " VALUES (1, 'owner', 'owner', 'hash', 'owner@test.local')")
                        conn.execute("INSERT INTO machines (machine_id, name) VALUES ('fm_test', 'Test')")
                        conn.execute("INSERT INTO machine_invites (code_hash, machine_id, created_by, expires_at)"
                                     " VALUES ('saved', 'fm_test', 1, 9999999999)")
                for _ in range(2):
                    with create_server(("127.0.0.1", 0)):
                        with get_connection() as conn:
                            self.assertEqual(conn.execute("SELECT code_hash FROM machine_invites").fetchone()[0], "saved")


if __name__ == "__main__":
    unittest.main()
