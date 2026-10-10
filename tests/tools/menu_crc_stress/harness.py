"""Dựng server thật + vòng lặp machine/main.py thật cho stress CRC menu.

Kỹ thuật giống tests/python/test_machine_relay.py (setUp) nhưng dùng version1.1/machine,
patch bật/tắt thủ công để dùng lại được ngoài unittest.
Chạy thử: python -m tests.tools.menu_crc_stress.harness
"""

import importlib.util
import json
import os
import sqlite3
import sys
import tempfile
import threading
import time
import types
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

REPO = Path(__file__).resolve().parents[3]
MACHINE_DIR = REPO / "version1.1" / "machine"
MACHINE_PACKAGES = ("config", "server_connection", "menu_sync", "ingredient_sync")
DRINK_SCHEMA = ("CREATE TABLE drink (drink_id INTEGER PRIMARY KEY, drink_name TEXT, image TEXT,"
                " price NUMERIC, available INTEGER, in_stock INTEGER, deleted_at TEXT,"
                " glass_id INTEGER, drink_type_id INTEGER, garnish TEXT, featured INTEGER)")


def _drink(drink_id, name, price, glass, kind, garnish, deleted_at=None):
    return {"drink_id": drink_id, "drink_name": name, "image": f"recipe/image/{name}.webp",
            "price": price, "available": 1, "in_stock": 1, "deleted_at": deleted_at,
            "glass_id": glass, "drink_type_id": kind, "garnish": garnish, "featured": 0}


# 5 món theo version1.1/database/database.sql + 1006 đã xóa mềm (không được lọt vào gói).
SEED_DRINKS = [
    _drink(1001, "Peach Tea", 30000, 3001, 5001, "Ống hút to, lát đào"),
    _drink(1002, "Milk Tea", 35000, 3001, 5001, "Ống hút to, nắp dập"),
    _drink(1003, "Milk Coffee", 29000, 3002, 5001, "Ống hút nhỏ"),
    _drink(1004, "Strawberry Soda", 32000, 3003, 5003, "Lát chanh, lá bạc hà"),
    _drink(1005, "Chocolate Milk", 33000, 3001, 5004, "Kem tươi, bột cacao"),
    _drink(1006, "Món đã xóa", 1, None, None, None, "2026-01-01"),
]


def fake_database():
    """Thay tầng database MySQL của máy bằng module giả (stress chỉ đụng menu)."""
    ingredients = types.ModuleType("database.admin_functions.ingredients")
    ingredients.ingredients_payload = lambda: {"ingredients": []}
    ingredients.refill = lambda target, value: {"ingredient_id": target, "amount": value, "in_stock": True}
    inventory = types.ModuleType("database.inventory_service")
    inventory.publish_store_menu = lambda: ""
    return {
        "database": types.ModuleType("database"),
        "database.admin_functions": types.ModuleType("database.admin_functions"),
        "database.admin_functions.ingredients": ingredients,
        "database.inventory_service": inventory,
    }


class _Stop(BaseException):
    """Ném trong luồng máy để thoát main.run() khi harness dừng."""


def machine_modules():
    return [name for name in list(sys.modules) if name.split(".")[0] in MACHINE_PACKAGES]


class Harness:
    """Server + máy thật trên SQLite tạm; mọi lệnh menu đi bằng token MANAGER."""

    def __init__(self, workdir=None):
        self._tmp = None if workdir else tempfile.TemporaryDirectory(prefix="menu_crc_")
        self.workdir = Path(workdir) if workdir else Path(self._tmp.name)
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.machine_db = self.workdir / "machine.db"
        self.machine_id = self.manager_token = self.owner_token = None
        self.server = self.machine = None
        self._patches = []
        self._saved_modules = None
        self._started = False
        self._stop_event = threading.Event()
        self._machine_thread = None

    def _start_patch(self, p):
        p.start()
        self._patches.append(p)

    # ---------- dựng / dỡ ----------
    def start(self):
        if self._started:
            return self
        self._started = True
        self._stop_event.clear()
        try:
            self._start_server()
            self._create_accounts()
            self._start_machine()
            self._wait_online()
        except BaseException:
            self.stop()
            raise
        return self

    def _start_server(self):
        self._start_patch(patch("server.database.connection.DB_PATH", self.workdir / "server.db"))
        from server import main as server_main
        from server.database.machine.init_db import init_db
        from server.lib.http import http_rate_limit
        from server.lib.machine import machine_transport
        # Mọi request đến từ 127.0.0.1; vài trăm vòng (đăng ký, status...) sẽ vượt 30 request/phút/IP.
        # Nâng trần trong lúc harness chạy để rate limit không làm hỏng kết quả stress.
        self._start_patch(patch.object(http_rate_limit, "MAX_REQUESTS", 10 ** 9))
        http_rate_limit.IP_REQUESTS.clear()
        # Long-poll ngắn để stop() nhanh. Không để dưới 1s: main.poll() ngủ thêm 1s khi
        # server trả sớm hơn 1s, sẽ làm mỗi lệnh chậm thêm tới 1s.
        self._start_patch(patch.object(machine_transport, "POLL_WAIT_SECONDS", 1.5))
        init_db()
        self.server = server_main.create_server(("127.0.0.1", 0))
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def _create_accounts(self):
        from server.database.connection import get_connection
        from server.lib.security.user_session import create_session
        with get_connection() as conn:
            owner = conn.execute("INSERT INTO users (full_name, username, password, email)"
                                 " VALUES ('owner','owner','x','owner@t.local')").lastrowid
            manager = conn.execute("INSERT INTO users (full_name, username, password, email)"
                                   " VALUES ('manager','manager','x','manager@t.local')").lastrowid
        self.owner_token, self.manager_token = create_session(owner), create_session(manager)
        status, reply = self.post("/app/user/machine/register", {
            "machine_name": "FlexMix-Stress", "product_key": "fm_stress_key", "token": self.owner_token})
        if status != 200 or "machine_id" not in reply:
            raise RuntimeError(f"Đăng ký máy lỗi: {status} {reply}")
        self.machine_id = reply["machine_id"]
        # Cấp quyền manager bằng luồng chia sẻ thật: chủ tạo mã → người thứ hai nhận.
        status, invite = self.post("/app/machine/share/create",
                                   {"token": self.owner_token, "machine_id": self.machine_id})
        if not invite.get("code"):
            raise RuntimeError(f"Tạo mã chia sẻ lỗi: {status} {invite}")
        status, accepted = self.post("/app/machine/share/accept",
                                     {"token": self.manager_token, "code": invite["code"]})
        if not accepted.get("valid"):
            raise RuntimeError(f"Nhận mã chia sẻ lỗi: {status} {accepted}")
        _, listing = self.post("/app/user/machine/list", {"token": self.manager_token})
        roles = {m["machine_id"]: m["role"] for m in listing.get("machines", [])}
        if roles.get(self.machine_id) != "manager":
            raise RuntimeError(f"Tài khoản không ở quyền manager: {listing}")

    def _start_machine(self):
        env = self.workdir / "machine.env"
        env.write_text(f"MACHINE_NAME=FlexMix-Stress\nPRODUCT_KEY=fm_stress_key\nSERVER_URL={self.url}\n",
                       encoding="utf-8")
        self._start_patch(patch.dict(os.environ, {"FLEXMIX_MACHINE_ENV": str(env)}))
        # main.py import theo kiểu chạy trong thư mục máy (config, server_connection...).
        self._start_patch(patch.object(sys, "path", [str(MACHINE_DIR), *sys.path]))
        self._saved_modules = {name: sys.modules.pop(name) for name in machine_modules()}
        self._start_patch(patch.dict(sys.modules, fake_database()))
        spec = importlib.util.spec_from_file_location("machine_main_under_stress", MACHINE_DIR / "main.py")
        self.machine = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.machine)
        self.machine_db.unlink(missing_ok=True)
        with sqlite3.connect(self.machine_db) as conn:
            conn.execute(DRINK_SCHEMA)
            cols = list(SEED_DRINKS[0])
            conn.executemany(f"INSERT INTO drink ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                             [[d[c] for c in cols] for d in SEED_DRINKS])
        conn.close()
        from menu_sync import machine_menu_store
        self._start_patch(patch.object(machine_menu_store, "DB_PATH", self.machine_db))
        # main.run() là vòng while True không có cờ dừng: bọc poll() để ném _Stop khi
        # stop() bật cờ, rồi join luồng TRƯỚC khi gỡ patch (tránh luồng sót đụng DB máy thật).
        real_poll = self.machine.poll
        stop_event = self._stop_event

        def poll():
            if stop_event.is_set():
                raise _Stop
            return real_poll()

        self.machine.poll = poll

        def loop():
            try:
                self.machine.run()
            except _Stop:
                pass

        self._machine_thread = threading.Thread(target=loop, daemon=True, name="machine-loop")
        self._machine_thread.start()

    def _wait_online(self, timeout=15):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                with urlopen(f"{self.url}/app/machine/status/get?machine_id={self.machine_id}", timeout=5) as r:
                    if json.loads(r.read()).get("online"):
                        return
            except (HTTPError, OSError, ValueError):
                pass
            time.sleep(0.05)
        raise RuntimeError("Máy không online (chưa poll được) trong thời gian chờ")

    def stop(self):
        if not self._started:
            return
        self._started = False
        self._stop_event.set()
        if self._machine_thread is not None:
            # poll() đang chờ tối đa POLL_WAIT_SECONDS (+1s ngủ khi lỗi) rồi gặp cờ dừng.
            self._machine_thread.join(timeout=10)
            self._machine_thread = None
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        try:
            from server.lib.http import http_rate_limit
            http_rate_limit.IP_REQUESTS.clear()
        except ImportError:
            pass
        for p in reversed(self._patches):
            try:
                p.stop()
            except RuntimeError:
                pass
        self._patches.clear()
        if self._saved_modules is not None:
            for name in machine_modules():
                sys.modules.pop(name, None)
            sys.modules.update(self._saved_modules)
            self._saved_modules = None
        if self._tmp is not None:
            self._tmp.cleanup()

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()

    # ---------- gọi API ----------
    def post(self, path, data):
        """POST JSON; trả (status, JSON) cả khi 2xx lẫn HTTPError."""
        request = Request(self.url + path, data=json.dumps(data).encode(),
                          headers={"Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=30) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            with error:
                body = error.read()
            try:
                return error.code, json.loads(body)
            except ValueError:
                return error.code, {"raw": body.decode("utf-8", "replace")}

    def menu_get(self, menu_version):
        return self.post("/app/machine/menu/get", {"token": self.manager_token, "machine_id": self.machine_id,
                                                   "menu_version": menu_version})

    def menu_update(self, menu_version, changes):
        return self.post("/app/machine/menu/update", {"token": self.manager_token, "machine_id": self.machine_id,
                                                      "menu_version": menu_version, "thay_doi": changes})

    def db_execute(self, sql, params=()):
        """Ghi thẳng SQLite máy (giả nhân viên sửa trên máy, vd đổi tên món mà API không cho)."""
        conn = sqlite3.connect(self.machine_db)
        try:
            with conn:
                conn.execute(sql, params)
        finally:
            conn.close()


if __name__ == "__main__":
    with Harness() as h:
        status, reply = h.menu_get(0)
        print("status:", status, reply.get("status"))
        print("menu_version:", reply.get("menu_version"))
        print("packet length:", len(reply.get("packet", "")))
