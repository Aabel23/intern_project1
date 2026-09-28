"""Kịch bản tấn công vào server thật (HTTP thật, SQLite tạm).

Chạy: python -m unittest server.test_security -v
Mỗi test khẳng định hành vi AN TOÀN. Lỗ hổng đã ghi trong log/SECURITY_NOTES.md nhưng
chưa sửa được đánh dấu @unittest.expectedFailure (kèm mã SEC-xx): lượt chạy vẫn đạt.
Khi ai đó sửa lỗ hổng, test báo "unexpected success" -> bỏ decorator và cập nhật ghi chú.
"""

import secrets
import json
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPConnection, RemoteDisconnected
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from server import main
from server.database.connection import get_connection
from server.database.machine.init_db import init_db
from server.lib import rate_limit
from server.database.user.user_add import hash_password
from server.service.user_login import login_flow
from server.lib.session import create_session


class SecurityScenarioTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        for target, value in (("server.database.connection.DB_PATH", Path(directory.name) / "t.db"),
                              ("server.service.machine_link.link_queue.POLL_WAIT_SECONDS", 0.3)):
            p = patch(target, value)
            p.start()
            self.addCleanup(p.stop)
        init_db()
        rate_limit.IP_REQUESTS.clear()
        login_flow.LOGIN_STATES.clear()
        self.server = main.Server(("127.0.0.1", 0), main.Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.addCleanup(rate_limit.IP_REQUESTS.clear)
        self.addCleanup(login_flow.LOGIN_STATES.clear)

    # ---------- tiện ích ----------

    def post(self, path, data=None, raw=None, headers=None):
        body = raw if raw is not None else json.dumps(data).encode()
        request = Request(f"http://127.0.0.1:{self.server.server_port}{path}", data=body,
                          headers={"Content-Type": "application/json", **(headers or {})})
        try:
            with urlopen(request, timeout=10) as response:
                return response.status, response.read()
        except HTTPError as error:
            with error:
                return error.code, error.read()

    def user(self, name, password="matkhau-dung-123"):
        with get_connection() as conn:
            user_id = conn.execute(
                "INSERT INTO users (full_name, username, password, email) VALUES (?, ?, ?, ?)",
                (name, name, hash_password(password), f"{name}@t.local")).lastrowid
        return user_id, create_session(user_id)

    def machine(self, token, key="fm_tem_may_that"):
        status, body = self.post("/app/dang-ky-may", {"machine_name": "FlexMix-A", "product_key": key,
                                                      "token": token})
        self.assertEqual(status, 200)
        return json.loads(body)["machine_id"]

    def login(self, username, password):
        request_id = secrets.token_hex(16)
        status, body = self.post("/app/dang-nhap", {"request_id": request_id, "username": username,
                                                    "password": password})
        data = json.loads(body)
        if status != 200:
            return status, data
        status, body = self.post("/app/xac-minh-dang-nhap", {"request_id": request_id,
                                                             "login_id": data["login_id"]})
        return status, json.loads(body)

    # ---------- đã an toàn (giữ để không bị hồi quy) ----------

    def test_other_account_cannot_command_or_sync_machine(self):
        _, owner = self.user("chu")
        _, stranger = self.user("la")
        machine_id = self.machine(owner)
        for path, extra in (("/app/nhan-kho", {"version": 0}), ("/app/nhan-menu", {}),
                            ("/app/nap-kho", {"target": "all", "value": "full"}),
                            ("/app/nhan-vien-may", {}), ("/app/tao-ma-chia-se", {}),
                            ("/app/doi-ten-may", {"name": "x"}), ("/app/go-may", {})):
            status, body = self.post(path, {"token": stranger, "machine_id": machine_id, **extra})
            self.assertIn(status, (400, 403), path)
        with get_connection() as conn:
            self.assertEqual(conn.execute("SELECT name FROM machines").fetchone()["name"], "FlexMix-A")

    def test_staff_cannot_escalate_to_owner_actions(self):
        _, owner = self.user("chu")
        staff_id, staff = self.user("nv")
        machine_id = self.machine(owner)
        with get_connection() as conn:
            conn.execute("INSERT INTO machine_managers (machine_id, user_id, role) VALUES (?, ?, 'manager')",
                         (machine_id, staff_id))
        owner_id = self.user("x")[0] - 2
        for path, extra in (("/app/tao-ma-chia-se", {}), ("/app/doi-ten-may", {"name": "hack"}),
                            ("/app/nhan-vien-may", {}), ("/app/thu-hoi-quyen", {"user_id": owner_id})):
            status, _ = self.post(path, {"token": staff, "machine_id": machine_id, **extra})
            self.assertEqual(status, 400, path)
        # Nhân viên "gỡ máy" chỉ bỏ quyền của mình, máy và chủ vẫn còn.
        self.post("/app/go-may", {"token": staff, "machine_id": machine_id})
        with get_connection() as conn:
            self.assertEqual(conn.execute("SELECT role FROM machine_managers").fetchall()[0]["role"], "owner")
            self.assertEqual(conn.execute("SELECT COUNT(*) c FROM machines").fetchone()["c"], 1)

    def test_second_user_with_sticker_cannot_steal_registered_machine(self):
        _, owner = self.user("chu")
        _, thief = self.user("trom")
        self.machine(owner)
        status, body = self.post("/app/dang-ky-may", {"machine_name": "FlexMix-A", "product_key": "fm_tem_may_that",
                                                      "token": thief})
        self.assertEqual(status, 400)

    def test_invite_code_single_use_and_logout_kills_token(self):
        _, owner = self.user("chu")
        _, a = self.user("a")
        _, b = self.user("b")
        machine_id = self.machine(owner)
        code = json.loads(self.post("/app/tao-ma-chia-se", {"token": owner, "machine_id": machine_id})[1])["code"]
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda t: self.post("/app/nhan-chia-se", {"token": t, "code": code})[0], (a, b)))
        self.assertEqual(sorted(results), [200, 400])
        self.post("/app/dang-xuat", {"token": a})
        self.assertEqual(self.post("/app/may-cua-toi", {"token": a})[0], 400)

    def test_wrong_password_and_unknown_user_look_the_same(self):
        self.user("co_that")
        s1, d1 = self.login("co_that", "sai-mat-khau-123")
        rate_limit.IP_REQUESTS.clear()
        s2, d2 = self.login("khong_ton_tai", "sai-mat-khau-123")
        self.assertEqual((s1, d1["message"]), (s2, d2["message"]))

    def test_password_brute_force_is_rate_limited(self):
        self.user("nan_nhan")
        statuses = [self.post("/app/dang-nhap", {"request_id": f"{i:032x}", "username": "nan_nhan",
                                                 "password": f"doan-{i:04d}-xx"})[0] for i in range(35)]
        self.assertIn(429, statuses)

    def test_machine_cannot_answer_for_another_machine(self):
        _, owner = self.user("chu")
        machine_id = self.machine(owner)
        _, other_owner = self.user("chu2")
        self.machine(other_owner, key="fm_may_khac")
        self.post("/machine/heartbeat", {"product_key": "fm_tem_may_that"})
        with ThreadPoolExecutor(1) as pool:
            app = pool.submit(self.post, "/app/nhan-kho", {"token": owner, "machine_id": machine_id,
                                                           "version": 0})
            time.sleep(0.3)
            for lenh_id in range(1, 50):
                self.post("/machine/tra-ket-qua", {"product_key": "fm_may_khac", "id": lenh_id,
                                                  "ket_qua": {"drinks": "gia"}})
            status, body = self.post("/machine/hoi-lenh", {"product_key": "fm_tem_may_that"})
            lenh = json.loads(body)["lenh"]
            self.post("/machine/tra-ket-qua", {"product_key": "fm_tem_may_that", "id": lenh["id"],
                                              "ket_qua": {"drinks": []}})
            self.assertEqual(json.loads(app.result(15)[1]), {"drinks": []})

    # ---------- lỗ hổng đã ghi, chưa sửa (xem log/SECURITY_NOTES.md) ----------

    @unittest.expectedFailure
    def test_SEC02_sticker_key_holder_cannot_hijack_owner_commands(self):
        """SEC-02: ai chụp được tem QR (product key) giả được máy và lấy lệnh của chủ."""
        _, owner = self.user("chu")
        machine_id = self.machine(owner)
        # Kẻ tấn công chỉ có key trên tem: heartbeat + hỏi lệnh như máy thật.
        self.post("/machine/heartbeat", {"product_key": "fm_tem_may_that"})
        with ThreadPoolExecutor(1) as pool:
            pool.submit(self.post, "/app/nap-kho", {"token": owner, "machine_id": machine_id,
                                                    "target": 1, "value": 1})
            time.sleep(0.3)
            lenh = json.loads(self.post("/machine/hoi-lenh", {"product_key": "fm_tem_may_that"})[1])["lenh"]
            if lenh:
                self.post("/machine/tra-ket-qua", {"product_key": "fm_tem_may_that", "id": lenh["id"],
                                                  "ket_qua": {"ok": True}})
        self.assertIsNone(lenh, "Kẻ giữ product key nhận được lệnh của chủ máy")

    @unittest.expectedFailure
    def test_SEC03_full_ip_table_does_not_lock_out_new_clients(self):
        """SEC-03: đủ 1000 IP trong bảng giới hạn thì mọi IP mới bị 429 khi đăng nhập/đăng ký."""
        self.user("khach")
        now = time.monotonic()
        for i in range(1000):
            rate_limit.IP_REQUESTS[f"10.0.{i // 250}.{i % 250}"] = [now + 60, 1]
        status, _ = self.login("khach", "matkhau-dung-123")
        self.assertEqual(status, 200)

    @unittest.expectedFailure
    def test_SEC04_login_state_flood_does_not_block_real_login(self):
        """SEC-04: lấp đầy 1000 phiên đăng nhập chờ (không cần mật khẩu đúng) thì người thật bị "Server đang bận"."""
        self.user("khach")
        now = time.monotonic()
        for i in range(login_flow.MAX_LOGIN_STATES):
            login_flow.LOGIN_STATES[f"rac{i}"] = {"request_id": f"{i:032x}", "fingerprint": "",
                                                  "status": "verified", "result": {}, "expires_at": now + 60}
        status, data = self.login("khach", "matkhau-dung-123")
        self.assertEqual(status, 200, data)

    @unittest.expectedFailure
    def test_SEC05_registration_does_not_reveal_existing_email(self):
        """SEC-05: đăng ký trả "Email đã tồn tại" -> dò được email nào có tài khoản."""
        self.user("co_that")
        from server.service.user_register.user_register_verify import verify_user
        base = {"full_name": "X", "username": "moi_hoan_toan", "password": "12345678", "request_id": "b" * 32}
        taken = verify_user({**base, "email": "co_that@t.local"})
        free = verify_user({**base, "email": "chua_co@t.local"})
        self.assertEqual(taken, free)

    def test_SEC06_gzip_route_is_gone(self):
        """SEC-06 (đã hết): đường gói gzip máy→app (/machine/tra-dong-bo) đã bỏ, kết quả chỉ còn JSON qua tra-ket-qua."""
        self.assertEqual(self.post("/machine/tra-dong-bo", {"product_key": "x"})[0], 404)

    def test_nested_json_gets_an_error_response(self):
        """JSON lồng sâu (RecursionError khi parse) vẫn nhận 400, server không rớt kết nối."""
        conn = HTTPConnection("127.0.0.1", self.server.server_port, timeout=10)
        body = b"[" * 4000
        conn.request("POST", "/app/dang-nhap", body=body, headers={"Content-Type": "application/json"})
        try:
            status = conn.getresponse().status
        except (RemoteDisconnected, ConnectionResetError):
            status = None
        finally:
            conn.close()
        self.assertEqual(status, 400)

    @unittest.expectedFailure
    def test_SEC14_usernames_differing_only_in_case_cannot_coexist(self):
        """SEC-14: kiểm tra trùng không phân biệt hoa/thường nhưng cột UNIQUE thì có; đăng ký song song lọt cả hai."""
        from server.database.user.user_add import add_user_with_hash
        add_user_with_hash("A", "An", "x", "an1@t.local")
        with self.assertRaises(ValueError):
            add_user_with_hash("B", "an", "x", "an2@t.local")

    @unittest.expectedFailure
    def test_SEC08_machine_status_requires_login(self):
        """SEC-08: /machine/trang-thai không cần token, ai biết machine_id đều xem được online/last_seen."""
        _, owner = self.user("chu")
        machine_id = self.machine(owner)
        self.post("/machine/heartbeat", {"product_key": "fm_tem_may_that"})
        with urlopen(f"http://127.0.0.1:{self.server.server_port}/machine/trang-thai?machine_id={machine_id}") as r:
            data = json.loads(r.read())
        self.assertIsNone(data.get("last_seen"))


if __name__ == "__main__":
    unittest.main()
