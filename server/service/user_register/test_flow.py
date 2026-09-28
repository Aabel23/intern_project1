"""Chạy: python -m unittest server.service.user_register.test_flow"""
import http.client
import json
import sqlite3
import tempfile
from pathlib import Path
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from .otp import otp_flow as flow
from server import main as server_main
from server.lib import rate_limit
from .user_register import registration_flow
from server.database import connection


class RegistrationFlowTest(unittest.TestCase):
    def setUp(self):
        registration_flow.REGISTRATIONS.clear()
        flow.SESSIONS.clear()
        flow.EMAIL_LIMITS.clear()
        self.data = {"request_id": "a" * 32, "full_name": "Test",
                     "username": "test", "email": "test@example.com", "password": "password123"}
        for target, value in [("send_otp", None), ("generate_code", "012345")]:
            mock = patch.object(flow, target, return_value=value)
            setattr(self, target, mock.start())
            self.addCleanup(mock.stop)
        self.verify_user = patch.object(registration_flow, "verify_user", return_value=None).start()
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        patch.object(connection, "DB_PATH", Path(folder.name) / "test.db").start()
        with connection.get_connection() as db:
            db.execute("""CREATE TABLE users (
                id INTEGER PRIMARY KEY, full_name TEXT, username TEXT UNIQUE,
                password TEXT, email TEXT UNIQUE, role TEXT, store_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )""")
        self.clock = patch.object(flow.time, "monotonic", return_value=1000).start()
        self.addCleanup(patch.stopall)

    def start(self):
        result = registration_flow.receive_register(self.data)
        self.assertTrue(result["valid"], result)
        return result["registration_id"]

    def test_retry_keeps_session_and_sends_once(self):
        key = self.start()
        self.assertEqual(self.start(), key)
        self.send_otp.assert_called_once()
        self.assertNotIn("password", registration_flow.REGISTRATIONS[key]["user_data"])
        self.assertNotEqual(registration_flow.REGISTRATIONS[key]["user_data"]["password_hash"], self.data["password"])
        changed = dict(self.data, username="changed")
        self.assertFalse(registration_flow.receive_register(changed)["valid"])

    def test_wrong_attempts_do_not_remove_cooldown(self):
        key = self.start()
        for _ in range(5):
            result = registration_flow.confirm_otp({"registration_id": key, "code": "999999"})
            self.assertFalse(result["valid"])
        self.assertIn("5", result["message"])
        self.assertEqual(flow.resend_otp({"registration_id": key})["retry_after"], 60)
        self.assertFalse(registration_flow.confirm_otp({"registration_id": key, "code": "012345"})["valid"])

    def test_parallel_verify_is_idempotent_and_resend_is_blocked(self):
        key = self.start()
        with patch("builtins.print") as output:
            with ThreadPoolExecutor(2) as pool:
                results = list(pool.map(lambda _: registration_flow.confirm_otp(
                    {"registration_id": key, "code": "012345"}), range(2)))
        self.assertTrue(all(result["valid"] for result in results))
        output.assert_called_once()  # Chỉ một lần chuyển trạng thái.
        self.assertIsNone(flow.SESSIONS[key]["otp_hash"])
        self.assertTrue(registration_flow.REGISTRATIONS[key]["data_valid"])
        self.assertTrue(registration_flow.REGISTRATIONS[key]["otp_verified"])
        with connection.get_connection() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM users").fetchone()[0], 1)
            stored = db.execute("SELECT password FROM users").fetchone()[0]
        self.assertEqual(stored, registration_flow.REGISTRATIONS[key]["user_data"]["password_hash"])
        self.assertEqual(registration_flow.receive_register(self.data)["account_created"], True)
        self.assertFalse(flow.resend_otp({"registration_id": key})["valid"])

    def test_new_session_cannot_replace_old_payload(self):
        first = self.start()
        self.clock.return_value = 1061
        other = dict(self.data, request_id="b" * 32, username="other")
        second = registration_flow.receive_register(other)["registration_id"]
        self.assertNotEqual(first, second)
        self.assertEqual(registration_flow.REGISTRATIONS[first]["user_data"]["username"], "test")
        self.assertEqual(registration_flow.REGISTRATIONS[second]["user_data"]["username"], "other")

    def test_failed_resend_preserves_old_code_and_cooldown(self):
        key = self.start()
        self.clock.return_value = 1061
        self.send_otp.return_value = "SMTP failed"
        self.assertFalse(flow.resend_otp({"registration_id": key})["valid"])
        self.assertEqual(flow.resend_otp({"registration_id": key})["retry_after"], 60)
        self.assertTrue(registration_flow.confirm_otp({"registration_id": key, "code": "012345"})["valid"])

    def test_slow_send_does_not_hold_lock_or_allow_second_send(self):
        started = threading.Event()
        finish = threading.Event()
        def slow_send(*args):
            started.set()
            if not finish.wait(3):
                raise TimeoutError("test timeout")
        self.send_otp.side_effect = slow_send
        with ThreadPoolExecutor(1) as pool:
            task = pool.submit(registration_flow.receive_register, self.data)
            try:
                self.assertTrue(started.wait(2))
                result = registration_flow.receive_register(self.data)
                self.assertFalse(result["valid"])
                self.assertEqual(result["retry_after"], 3)
                flow.cleanup()
            finally:
                finish.set()
            self.assertTrue(task.result()["valid"])
        self.send_otp.assert_called_once()

    def test_email_limit_survives_new_sessions(self):
        for index in range(5):
            self.clock.return_value = 1000 + index * 61
            data = dict(self.data, request_id=f"{index:032x}")
            self.assertTrue(registration_flow.receive_register(data)["valid"])
        self.clock.return_value = 1400
        self.assertFalse(registration_flow.receive_register(dict(self.data, request_id="f" * 32))["valid"])
        self.assertEqual(self.send_otp.call_count, 5)

    def test_expiry_capacity_and_invalid_input(self):
        self.assertFalse(registration_flow.receive_register({})["valid"])
        self.assertFalse(registration_flow.confirm_otp({"registration_id": [], "code": "123456"})["valid"])
        key = self.start()
        with patch.object(flow, "MAX_SESSIONS", 1):
            self.assertFalse(registration_flow.receive_register(dict(self.data, request_id="b" * 32))["valid"])
        self.clock.return_value = 1901
        flow.cleanup()
        self.assertFalse(registration_flow.confirm_otp({"registration_id": key, "code": "012345"})["valid"])
        self.assertFalse(flow.SESSIONS)
        self.clock.return_value = 4601
        flow.cleanup()
        self.assertFalse(flow.EMAIL_LIMITS)

    def test_database_failure_can_retry_without_second_otp(self):
        key = self.start()
        with patch.object(registration_flow, "register_user", side_effect=sqlite3.OperationalError("busy")):
            with self.assertRaises(sqlite3.OperationalError):
                registration_flow.confirm_otp({"registration_id": key, "code": "012345"})
        self.assertFalse(registration_flow.REGISTRATIONS[key]["account_created"])
        self.assertTrue(registration_flow.confirm_otp({"registration_id": key, "code": "012345"})["account_created"])

    def test_wrong_code_cannot_create_user(self):
        key = self.start()
        self.assertFalse(registration_flow.confirm_otp({"registration_id": key, "code": "999999"})["valid"])
        with connection.get_connection() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM users").fetchone()[0], 0)
        self.assertFalse(registration_flow.REGISTRATIONS[key]["otp_verified"])

    def test_http_flow_and_rate_limit(self):
        IP_REQUESTS = rate_limit.IP_REQUESTS
        IP_REQUESTS.clear()
        server = server_main.Server(("127.0.0.1", 0), server_main.Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        def post(path, data):
            client = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
            try:
                client.request("POST", path, json.dumps(data), {"Content-Type": "application/json"})
                response = client.getresponse()
                return response.status, json.loads(response.read())
            finally:
                client.close()
        try:
            from server.config.routing import APP_REGISTER_USER, APP_VERIFY_OTP
            with patch.object(server_main.Handler, "log_message"):
                status, result = post(APP_REGISTER_USER, self.data)
                self.assertEqual(status, 200)
                status, result = post(APP_VERIFY_OTP, {"registration_id": result["registration_id"], "code": "012345"})
                self.assertEqual(status, 200)
                self.assertTrue(result["account_created"])
                self.assertEqual(post("/unknown", {})[0], 404)
                IP_REQUESTS["127.0.0.1"] = [1060, 30]
                self.assertEqual(post(APP_REGISTER_USER, self.data)[0], 429)
        finally:
            server.shutdown()
            server.server_close()
            worker.join(3)
            IP_REQUESTS.clear()

    def test_real_validation_and_duplicate_database_constraint(self):
        from .user_register.user_verify import verify_user
        self.verify_user.side_effect = verify_user
        self.assertFalse(registration_flow.receive_register(dict(self.data, password="short"))["valid"])
        # Quá giới hạn đăng nhập thì không cho tạo (tài khoản sẽ không đăng nhập được).
        for field, value in (("username", "u" * 151), ("password", "p" * 1025), ("full_name", "n" * 151)):
            self.assertFalse(verify_user(dict(self.data, **{field: value})) is None, field)
        key = self.start()
        self.assertTrue(registration_flow.confirm_otp({"registration_id": key, "code": "012345"})["valid"])
        duplicate = dict(self.data, request_id="b" * 32)
        self.assertFalse(registration_flow.receive_register(duplicate)["valid"])

    def test_invalid_registration_does_not_send(self):
        self.verify_user.return_value = "invalid"
        self.assertFalse(registration_flow.receive_register(self.data)["valid"])
        self.send_otp.assert_not_called()


if __name__ == "__main__":
    unittest.main()
