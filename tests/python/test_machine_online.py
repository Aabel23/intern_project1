"""Online của máy suy từ long-poll và lệnh đã lấy (HTTP thật, SQLite tạm, đồng hồ giả).

Chạy: python -m unittest tests.python.test_machine_online -v
Đồng hồ giả chỉ thay time.time() của machine_transport (giờ ghi "đã thấy" và giờ lấy lệnh);
chờ long-poll và chờ kết quả của send() vẫn dùng thời gian thật, đã rút ngắn bằng patch.
"""

import ast
import json
import tempfile
import threading
import types
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from server import main
from server.config import config
from server.database.connection import get_connection
from server.database.machine.init_db import init_db
from server.lib.http import http_rate_limit as rate_limit
from server.lib.machine import machine_transport as relay
from server.lib.security.user_session import create_session
from server.service.machine_link import machine_link_process

KEY = "online-key"
SEEN = 15
COMMAND = 20
MACHINE_DIR = Path(__file__).resolve().parents[2] / "version1.1" / "machine"
# Lệnh máy hiện có đều xong trong vài giây, nên "lệnh đã lấy < COMMAND_TIMEOUT" thay được heartbeat theo lệnh.
SHORT_COMMANDS = {"nhan_menu", "cap_nhat_menu", "nhan_kho", "nap_kho"}


class FakeClock:
    def __init__(self):
        self.now = 1_000_000.0

    def time(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class MachineOnlineTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        patch("server.database.connection.DB_PATH", Path(directory.name) / "test.db").start()
        self.clock = FakeClock()
        patch.object(relay, "time", types.SimpleNamespace(time=self.clock.time)).start()
        patch.object(relay, "POLL_WAIT_SECONDS", 0.2).start()
        patch.object(relay, "MACHINE_SEEN_TIMEOUT_SECONDS", SEEN).start()
        patch.object(relay, "COMMAND_TIMEOUT_SECONDS", COMMAND).start()
        patch.object(rate_limit, "MAX_REQUESTS", 10 ** 9).start()
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
        self.token, self.machine_id = self.owner_machine("owner", KEY)

    # ---------- tiện ích ----------

    def owner_machine(self, username, key):
        with get_connection() as conn:
            user_id = conn.execute(
                "INSERT INTO users (full_name, username, password, email) VALUES (?, ?, 'x', ?)",
                (username, username, f"{username}@t.local"),
            ).lastrowid
        token = create_session(user_id)
        _, machine = self.request("/app/user/machine/register", {
            "machine_name": "FlexMix-Online", "product_key": key, "token": token,
        })
        return token, machine["machine_id"]

    def request(self, path, data=None):
        body = None if data is None else json.dumps(data).encode()
        url = f"http://127.0.0.1:{self.server.server_port}{path}"
        try:
            response = urlopen(Request(url, data=body, headers={"Content-Type": "application/json"}), timeout=10)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.loads(response.read())

    def online(self, machine_id=None):
        return self.request(f"/app/machine/status/get?machine_id={machine_id or self.machine_id}")[1]["online"]

    def poll(self, key=KEY):
        return self.request("/machine/command/poll", {"product_key": key})[1]["lenh"]

    def take(self, key=KEY):
        for _ in range(50):
            lenh = self.poll(key)
            if lenh is not None:
                return lenh
        self.fail("Máy không nhận được lệnh")

    def ask_app(self):
        return self.request("/app/machine/ingredient/get", {"token": self.token, "machine_id": self.machine_id,
                                                            "version": 0})

    def wait_queued(self):
        for _ in range(100):
            with relay.KHOA:
                if relay.HOP_THU.get(self.machine_id):
                    return
            threading.Event().wait(0.02)
        self.fail("App chưa xếp lệnh vào hộp thư")

    # ---------- cấu hình ----------

    def test_poll_wait_shorter_than_seen_window(self):
        # Máy đang treo một poll luôn online nhờ lần ghi lúc mở poll: không cần đếm poll đang mở.
        self.assertLess(config.POLL_WAIT_SECONDS, config.MACHINE_SEEN_TIMEOUT_SECONDS)
        self.assertLessEqual(config.MACHINE_SEEN_TIMEOUT_SECONDS, config.COMMAND_TIMEOUT_SECONDS)

    def test_machine_commands_are_known_short_commands(self):
        commands = set()
        for path in MACHINE_DIR.glob("*/machine_*_request.py"):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "COMMANDS" for t in node.targets):
                    commands |= {key.value for key in node.value.keys}
        self.assertEqual(commands, SHORT_COMMANDS,
                         "Lệnh máy mới: đo thời lượng; dài hơn COMMAND_TIMEOUT_SECONDS thì cần heartbeat theo lệnh "
                         "(docs/heartbeat-vs-long-poll.md mục 6) trước khi thêm vào SHORT_COMMANDS")

    # ---------- máy rảnh ----------

    def test_heartbeat_route_is_gone(self):
        # Route heartbeat đã bỏ: gọi với key đúng cũng không làm máy online hay ghi "đã thấy".
        self.assertEqual(self.request("/machine/heartbeat/send", {"product_key": KEY})[0], 404)
        status, reply = self.request(f"/app/machine/status/get?machine_id={self.machine_id}")
        self.assertEqual((status, reply["online"], reply["last_seen"]), (200, False, None))

    def test_poll_marks_online_until_seen_window_ends(self):
        self.assertFalse(self.online())
        self.poll()
        self.clock.advance(SEEN - 1)
        self.assertTrue(self.online())
        self.clock.advance(2)
        self.assertFalse(self.online())

    def test_result_marks_online(self):
        self.request("/machine/result/send", {"product_key": KEY, "id": 999999, "ket_qua": {}})
        self.assertTrue(self.online())

    def test_online_counts_from_poll_start_not_poll_end(self):
        # Máy mở poll rồi chết: đồng hồ trôi qua cửa sổ trong lúc server còn giữ poll (take() đang chờ).
        real_take = machine_link_process.take

        def take_while_clock_runs(machine_id):
            self.clock.advance(SEEN + 1)
            return real_take(machine_id)

        with patch.object(machine_link_process, "take", take_while_clock_runs):
            self.assertIsNone(self.poll())
        self.assertFalse(self.online())

    # ---------- máy bận ----------

    def test_queued_untaken_command_does_not_keep_machine_online(self):
        self.poll()
        with patch.object(relay, "COMMAND_TIMEOUT_SECONDS", 1), ThreadPoolExecutor(max_workers=1) as pool:
            app = pool.submit(self.ask_app)
            self.wait_queued()
            # Lệnh đã nằm trong DANG_CHO/HOP_THU nhưng máy chưa lấy: không tính là bận.
            self.clock.advance(SEEN + 1)
            self.assertFalse(self.online())
            self.assertEqual(app.result(timeout=5), (502, {"loi": "Máy không phản hồi, lệnh đã được hủy"}))

    def test_busy_machine_stays_online_while_running_taken_command(self):
        with ThreadPoolExecutor(max_workers=1) as pool:
            self.poll()
            app = pool.submit(self.ask_app)
            lenh = self.take()
            # Quá cửa sổ poll nhưng máy đang làm lệnh đã lấy: vẫn online.
            self.clock.advance(SEEN + 1)
            self.assertTrue(self.online())
            self.request("/machine/result/send", {"product_key": KEY, "id": lenh["id"], "ket_qua": {"ok": 1}})
            self.assertEqual(app.result(timeout=5), (200, {"ok": 1}))
        self.assertNotIn(self.machine_id, relay.DANG_LAM)

    def test_result_before_take_leaves_no_busy_entry(self):
        self.poll()
        with patch.object(relay, "COMMAND_TIMEOUT_SECONDS", 1), ThreadPoolExecutor(max_workers=1) as pool:
            app = pool.submit(self.ask_app)
            self.wait_queued()
            with relay.KHOA:
                lenh_id = relay.HOP_THU[self.machine_id][0]["id"]
            # Kết quả đến trước khi máy lấy lệnh: send() xong sớm, nhưng lệnh vẫn nằm trong hộp thư.
            self.request("/machine/result/send", {"product_key": KEY, "id": lenh_id, "ket_qua": {"som": 1}})
            app.result(timeout=5)
            # Lần poll sau lấy lệnh cũ còn sót; lệnh đó không còn ai chờ nên không được ghi là máy đang bận.
            self.poll()
        self.assertNotIn(self.machine_id, relay.DANG_LAM)

    def test_taken_command_older_than_command_timeout_is_not_busy(self):
        with ThreadPoolExecutor(max_workers=1) as pool:
            self.poll()
            app = pool.submit(self.ask_app)
            lenh = self.take()
            self.clock.advance(COMMAND + 1)
            self.assertFalse(self.online())
            self.request("/machine/result/send", {"product_key": KEY, "id": lenh["id"], "ket_qua": {"ok": 1}})
            self.assertEqual(app.result(timeout=5), (200, {"ok": 1}))

    def test_hung_command_loop_goes_offline_and_next_command_fails_fast(self):
        with patch.object(relay, "COMMAND_TIMEOUT_SECONDS", 1), ThreadPoolExecutor(max_workers=1) as pool:
            self.poll()
            app = pool.submit(self.ask_app)
            self.take()
            # Máy lấy lệnh rồi treo: không poll, không trả kết quả; send() hết giờ thật sau 1 giây.
            self.assertEqual(app.result(timeout=5),
                             (502, {"loi": "Máy chưa trả kết quả, hãy tải lại để kiểm tra"}))
        self.assertNotIn(self.machine_id, relay.DANG_LAM)
        self.clock.advance(SEEN + 1)
        self.assertFalse(self.online())
        self.assertEqual(self.ask_app(), (503, {"loi": "Máy đang offline"}))

    def test_other_machine_result_does_not_end_busy_state(self):
        _, other_id = self.owner_machine("other", "other-key")
        with ThreadPoolExecutor(max_workers=1) as pool:
            self.poll()
            app = pool.submit(self.ask_app)
            lenh = self.take()
            self.request("/machine/result/send", {"product_key": "other-key", "id": lenh["id"], "ket_qua": {"gia": 1}})
            self.clock.advance(SEEN + 1)
            # Kết quả giả của máy khác không gỡ trạng thái bận của máy này.
            self.assertTrue(self.online())
            self.assertFalse(self.online(other_id))
            self.request("/machine/result/send", {"product_key": KEY, "id": lenh["id"], "ket_qua": {"that": 1}})
            self.assertEqual(app.result(timeout=5), (200, {"that": 1}))

    # ---------- song song ----------

    def test_parallel_polls_and_sends_do_not_deadlock(self):
        stop = threading.Event()

        def machine():
            while not stop.is_set():
                lenh = self.poll()
                if lenh is not None:
                    self.request("/machine/result/send", {"product_key": KEY, "id": lenh["id"],
                                                          "ket_qua": {"id": lenh["id"]}})

        self.poll()
        machines = [threading.Thread(target=machine, daemon=True) for _ in range(2)]
        for thread in machines:
            thread.start()
        try:
            with ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(lambda _: self.ask_app()[0], range(40)))
        finally:
            stop.set()
            for thread in machines:
                thread.join(timeout=5)
        self.assertEqual(results, [200] * 40)
        self.assertNotIn(self.machine_id, relay.DANG_LAM)
        self.assertEqual(relay.HOP_THU.get(self.machine_id, []), [])


if __name__ == "__main__":
    unittest.main()
