"""Chạy: python -m unittest server.service.user_login.test_flow"""

import hashlib
import http.client
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from . import login_flow, login_verify
from server.database.connection import get_connection
from server.database.machine.init_db import init_db
from server import main as server_main
from .login_api import ROUTES
from .session import create_session, end_session, user_from_request


def password_hash(password):
    salt = os.urandom(16)
    iterations = 2_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


class LoginFlowTest(unittest.TestCase):
    request_id = "a" * 32

    def setUp(self):
        login_flow.LOGIN_STATES.clear()

    def test_login_state_machine(self):
        credentials = {
            "id": 1,
            "username": "staff",
            "password": password_hash("password123"),
        }
        # Không ghi phiên vào database thật trong test.
        with patch.object(login_verify, "get_credentials", return_value=credentials),                 patch.object(login_verify, "create_session", return_value="token-test") as session:
            accepted = login_flow.receive_login(
                {
                    "request_id": self.request_id,
                    "username": "staff",
                    "password": "password123",
                }
            )
            result = login_flow.send_verification(
                {"request_id": self.request_id, "login_id": accepted["login_id"]}
            )

        self.assertTrue(accepted["valid"])
        self.assertTrue(result["valid"])
        self.assertEqual(result["token"], "token-test")
        session.assert_called_once_with(1)
        self.assertNotIn("password", login_flow.LOGIN_STATES[accepted["login_id"]])

    def test_wrong_password_uses_generic_error(self):
        credentials = {
            "id": 1,
            "username": "staff",
            "password": password_hash("password123"),
        }
        with patch.object(login_verify, "get_credentials", return_value=credentials):
            accepted = login_flow.receive_login(
                {
                    "request_id": self.request_id,
                    "username": "staff",
                    "password": "wrong",
                }
            )
            result = login_flow.send_verification(
                {"request_id": self.request_id, "login_id": accepted["login_id"]}
            )

        self.assertFalse(result["valid"])
        self.assertEqual(result["message"], login_verify.INVALID_LOGIN)

    def test_retry_reuses_login_id_and_request_id_must_match(self):
        data = {
            "request_id": self.request_id,
            "username": "staff",
            "password": "password123",
        }
        with patch.object(
            login_flow,
            "verify_login",
            return_value={"valid": True, "verified": True, "message": "OK"},
        ) as verify:
            first = login_flow.receive_login(data)
            retried = login_flow.receive_login(data)

        self.assertEqual(first["login_id"], retried["login_id"])
        verify.assert_called_once_with(data)
        mismatch = login_flow.send_verification(
            {"request_id": "b" * 32, "login_id": first["login_id"]}
        )
        self.assertFalse(mismatch["valid"])

    def test_http_api_receives_raw_json_and_returns_verification(self):
        server = server_main.Server(("127.0.0.1", 0), server_main.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with patch.object(
                login_flow,
                "verify_login",
                return_value={"valid": True, "verified": True, "message": "OK"},
            ):
                connection = http.client.HTTPConnection("127.0.0.1", server.server_port)
                connection.request(
                    "POST",
                    "/app/dang-nhap",
                    json.dumps(
                        {
                            "request_id": self.request_id,
                            "username": "staff",
                            "password": "password123",
                        }
                    ),
                    {"Content-Type": "application/json"},
                )
                accepted = json.loads(connection.getresponse().read())
                connection.request(
                    "POST",
                    "/app/xac-minh-dang-nhap",
                    json.dumps(
                        {
                            "request_id": self.request_id,
                            "login_id": accepted["login_id"],
                        }
                    ),
                    {"Content-Type": "application/json"},
                )
                verified = json.loads(connection.getresponse().read())
                connection.close()

            self.assertTrue(verified["valid"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_main_server_exposes_login_and_registration_routes(self):
        routes = {path for module in server_main.MODULES for path in getattr(module, "ROUTES", ())}
        for path in (*ROUTES, "/app/dang-ky-nguoi-dung", "/app/gui-ma-otp", "/app/xac-minh-otp"):
            self.assertIn(path, routes)



class SessionTest(unittest.TestCase):
    def test_logout_invalidates_token(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        with patch("server.database.connection.DB_PATH", Path(folder.name) / "test.db"):
            init_db()
            with get_connection() as conn:
                user_id = conn.execute(
                    "INSERT INTO users (full_name, username, password, email)"
                    " VALUES ('a', 'a', 'x', 'a@test.local')"
                ).lastrowid
            token = create_session(user_id)
            self.assertEqual(user_from_request({"token": token}), user_id)
            self.assertTrue(end_session({"token": token})["valid"])
            # Token cũ không dùng lại được sau khi đăng xuất.
            self.assertIsNone(user_from_request({"token": token}))

if __name__ == "__main__":
    unittest.main()
