"""Chạy: python -m unittest tests.python.test_machine_menu_image

Luồng ảnh món /app/machine/image/get qua server thật (SQLite tạm), máy giả hỏi lệnh
bằng HTTP: kiểm gói app, lệnh nhan_anh không mang token, kết quả máy về nguyên vẹn.
"""

import base64
import json
import tempfile
import threading
import unittest
import zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from server import main
from server.database.connection import get_connection
from server.database.machine.init_db import init_db
from server.lib.http import http_rate_limit as rate_limit
from server.lib.security.user_session import create_session

KEY = "image-key"


class MachineMenuImageTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        patch("server.database.connection.DB_PATH", Path(directory.name) / "test.db").start()
        # Long-poll ngắn để máy giả hỏi lại nhanh khi hộp thư rỗng.
        patch("server.lib.machine.machine_transport.POLL_WAIT_SECONDS", 0.3).start()
        self.addCleanup(patch.stopall)
        init_db()
        rate_limit.IP_REQUESTS.clear()
        self.server = main.create_server(("127.0.0.1", 0))
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.addCleanup(rate_limit.IP_REQUESTS.clear)

        with get_connection() as conn:
            user_id = conn.execute(
                "INSERT INTO users (full_name, username, password, email)"
                " VALUES ('o', 'owner', 'x', 'owner@test.local')"
            ).lastrowid
        self.token = create_session(user_id)
        _, machine = self.request("/app/user/machine/register", {
            "machine_name": "FlexMix-Image", "product_key": KEY, "token": self.token,
        })
        self.machine_id = machine["machine_id"]
        self.request("/machine/command/poll", {"product_key": KEY})

    def request(self, path, data):
        url = f"http://127.0.0.1:{self.server.server_port}{path}"
        request = Request(url, data=json.dumps(data).encode(), headers={"Content-Type": "application/json"})
        try:
            response = urlopen(request, timeout=10)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.loads(response.read())

    def ask(self, anh):
        return self.request("/app/machine/image/get", {"token": self.token, "machine_id": self.machine_id, "anh": anh})

    def answer_once(self, make_result):
        """Máy giả: hỏi lệnh tới khi có, trả kết quả do make_result(lệnh) dựng."""
        for _ in range(100):
            command = self.request("/machine/command/poll", {"product_key": KEY})[1]["lenh"]
            if command is not None:
                self.request("/machine/result/send", {"product_key": KEY, "id": command["id"],
                                                      "ket_qua": make_result(command)})
                return command
            threading.Event().wait(0.02)
        self.fail("máy giả không nhận được lệnh")

    def test_image_command_round_trip(self):
        # Ảnh ~700 KB: sau base64 vẫn vừa giới hạn 1 MB của /machine/result/send.
        raw = bytes(range(256)) * 2800
        crc = zlib.crc32(raw)
        result = {"status": "ok", "con_lai": [1003], "anh": [
            {"drink_id": 1001, "image_hash": crc, "mime": "image/webp", "data": base64.b64encode(raw).decode()},
            {"drink_id": 1002, "loi": "không có ảnh"},
        ]}
        wanted = [{"drink_id": 1001, "image_hash": 5}, {"drink_id": 1002, "image_hash": 6},
                  {"drink_id": 1003, "image_hash": 7}]
        with ThreadPoolExecutor(max_workers=1) as pool:
            app = pool.submit(self.ask, wanted)
            command = self.answer_once(lambda _: result)
            status, reply = app.result(timeout=10)

        # Lệnh xuống máy chỉ có danh sách ảnh, không mang token hay đường dẫn.
        self.assertEqual((command["instruction"], command["data"]), ("nhan_anh", {"anh": wanted}))
        self.assertNotIn("token", json.dumps(command))
        # Server trả nguyên kết quả máy; hash thật có thể khác hash app đã xin.
        self.assertEqual(status, 200)
        self.assertEqual(reply, result)
        self.assertEqual(zlib.crc32(base64.b64decode(reply["anh"][0]["data"])), crc)

    def test_invalid_requests_never_reach_machine(self):
        from server.lib.machine import machine_transport as relay
        bad_lists = [
            None, [], "1001", [1001],
            [{"drink_id": 1001}],
            [{"drink_id": 0, "image_hash": 1}],
            [{"drink_id": True, "image_hash": 1}],
            [{"drink_id": 1001, "image_hash": 0}],
            [{"drink_id": 1001, "image_hash": 2**32}],
            [{"drink_id": 1001, "image_hash": "1"}],
            [{"drink_id": 1001, "image_hash": 1, "path": "../../etc/passwd"}],
            [{"drink_id": 1001, "image_hash": 1}, {"drink_id": 1001, "image_hash": 2}],
            [{"drink_id": i, "image_hash": 1} for i in range(1, 22)],
        ]
        for anh in bad_lists:
            with self.subTest(anh=anh):
                status, reply = self.ask(anh)
                self.assertEqual(status, 400)
                self.assertIn("loi", reply)
        self.assertEqual(relay.HOP_THU.get(self.machine_id, []), [])

    def test_requires_login_and_machine_access(self):
        status, reply = self.request("/app/machine/image/get", {
            "token": "sai", "machine_id": self.machine_id, "anh": [{"drink_id": 1, "image_hash": 1}],
        })
        self.assertEqual(status, 401)
        self.assertTrue(reply["login_required"])


if __name__ == "__main__":
    unittest.main()
