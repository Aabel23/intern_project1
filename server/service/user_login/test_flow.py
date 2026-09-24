"""Chạy: python -m unittest server.service.user_login.test_flow"""

import hashlib
import http.client
import json
import os
import threading
import unittest
from unittest.mock import patch

from . import login_flow, login_verify
from .login_api import LoginHandler, LoginServer, ROUTES


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
        server = LoginServer(("127.0.0.1", 0), LoginHandler)
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

    def test_server_also_exposes_registration_routes(self):
        self.assertIn("/app/dang-ky-nguoi-dung", ROUTES)
        self.assertIn("/app/gui-ma-otp", ROUTES)
        self.assertIn("/app/xac-minh-otp", ROUTES)


if __name__ == "__main__":
    unittest.main()
