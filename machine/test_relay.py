"""Chạy: python -m unittest machine.test_relay

Chạy vòng lặp thật của machine/main.py với server thật (SQLite tạm) và
database máy giả trong RAM, kiểm tra heartbeat + nhận lệnh + trả kết quả.
"""

import gzip
import importlib.util
import json
import os
import sys
import tempfile
import threading
import types
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

MACHINE_DIR = Path(__file__).resolve().parent
MENU = {"drinks": [{"drinkId": 1, "name": "Cà phê", "price": 20000, "available": True}]}
INGREDIENTS = {"ingredients": [{"ingredient_id": 1, "name": "Sữa", "amount": 500, "max_gram": 1000,
                                "max_set": True, "pump_no": 1, "in_stock": True}]}


def fake_database(calls):
    """Thay tầng database MySQL của máy bằng module giả ghi lại lời gọi."""
    drinks = types.ModuleType("database.admin_functions.drinks")
    drinks.get_menu = lambda: MENU
    drinks.set_drink_available = lambda drink_id, available: calls.append(("available", drink_id, available))
    drinks.set_drink_price = lambda drink_id, price: calls.append(("price", drink_id, price))
    ingredients = types.ModuleType("database.admin_functions.ingredients")
    ingredients.get_ingredients = lambda: {"ingredients": []}
    inventory = types.ModuleType("database.inventory_service")

    def fail(*_):
        raise RuntimeError("MySQL mất kết nối")
    inventory.set_inventory = inventory.add_inventory = inventory.subtract_inventory = fail
    serve = types.ModuleType("admin_gui.serve")
    serve.ingredients_payload = lambda: INGREDIENTS
    return {
        "admin_gui": types.ModuleType("admin_gui"),
        "admin_gui.serve": serve,
        "database": types.ModuleType("database"),
        "database.admin_functions": types.ModuleType("database.admin_functions"),
        "database.admin_functions.drinks": drinks,
        "database.admin_functions.ingredients": ingredients,
        "database.inventory_service": inventory,
    }


class MachineRelayTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        patch("server.database.connection.DB_PATH", Path(folder.name) / "test.db").start()
        self.addCleanup(patch.stopall)
        from server import main as server_main
        from server.database.connection import get_connection
        from server.database.machine.init_db import init_db
        from server.service.user_login.session import create_session
        init_db()
        self.server = server_main.Server(("127.0.0.1", 0), server_main.Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        with get_connection() as conn:
            user_id = conn.execute(
                "INSERT INTO users (full_name, username, password, email) VALUES ('o','o','x','o@t.local')"
            ).lastrowid
        self.token = create_session(user_id)
        self.machine_id = self.post("/app/dang-ky-may", {
            "machine_name": "FlexMix-Test", "product_key": "fm_test_key", "token": self.token,
        })["machine_id"]

        # machine.env tạm, giống file thật trên Pi.
        env = Path(folder.name) / "machine.env"
        env.write_text(
            f"MACHINE_NAME=FlexMix-Test\nPRODUCT_KEY=fm_test_key\nSERVER_URL={self.url}\n",
            encoding="utf-8",
        )
        patch.dict(os.environ, {"FLEXMIX_MACHINE_ENV": str(env)}).start()
        self.calls = []
        # machine/main.py import theo kiểu chạy trong thư mục machine (config, server_connection).
        patch.object(sys, "path", [str(MACHINE_DIR), *sys.path]).start()
        saved = {name: sys.modules.pop(name) for name in list(sys.modules)
                 if name.split(".")[0] in ("config", "server_connection")}
        self.addCleanup(sys.modules.update, saved)
        patch.dict(sys.modules, fake_database(self.calls)).start()
        spec = importlib.util.spec_from_file_location("machine_main_under_test", MACHINE_DIR / "main.py")
        self.machine = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.machine)
        self.addCleanup(lambda: [sys.modules.pop(n, None) for n in list(sys.modules)
                                 if n.split(".")[0] in ("config", "server_connection")])

    def post(self, path, data):
        request = Request(self.url + path, data=json.dumps(data).encode(),
                          headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read())

    def sync(self, lenh, etag=None):
        """Gọi /app/dong-bo; trả (status, etag, dữ liệu đã giải nén hoặc lỗi JSON)."""
        headers = {"Content-Type": "application/json"}
        if etag:
            headers["If-None-Match"] = etag
        request = Request(self.url + "/app/dong-bo", headers=headers, data=json.dumps({
            "token": self.token, "machine_id": self.machine_id, "lenh": lenh,
        }).encode())
        try:
            with urlopen(request, timeout=30) as response:
                body = response.read()
                if response.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
                return response.status, response.headers.get("ETag"), json.loads(body)
        except HTTPError as error:
            with error:
                body = error.read()
            return error.code, error.headers.get("ETag"), json.loads(body) if body else None

    def test_machine_serves_app_commands(self):
        # Máy chưa chạy (chưa heartbeat) thì server báo offline ngay.
        self.assertEqual(self.sync("dong_bo_nguyen_lieu")[0], 503)
        threading.Thread(target=self.machine.run, daemon=True).start()
        for _ in range(100):
            with urlopen(f"{self.url}/machine/trang-thai?machine_id={self.machine_id}") as response:
                if json.loads(response.read())["online"]:
                    break
            threading.Event().wait(0.05)
        else:
            self.fail("Máy không heartbeat được bằng product key")

        send = lambda ten, thamso=None: self.post("/app/gui-lenh", {
            "token": self.token, "machine_id": self.machine_id, "ten": ten, "thamso": thamso or {},
        })
        self.assertEqual(send("xem_menu"), MENU)
        self.assertEqual(send("doi_trang_thai_mon", {"drink_id": 1, "available": False}), {"ok": True})
        self.assertEqual(self.calls, [("available", 1, False)])
        # Lỗi database trả về app, vòng lặp của máy vẫn chạy tiếp.
        self.assertEqual(send("them_nguyen_lieu", {"ingredient_id": 1, "gram": 5}),
                         {"loi": "MySQL mất kết nối"})
        self.assertEqual(send("lenh_la"), {"loi": "Lenh khong hop le"})
        self.assertEqual(send("xem_nguyen_lieu"), {"ingredients": []})

        # Đồng bộ kho: lần đầu nhận dữ liệu nén + ETag, gửi lại ETag đó thì nhận 304.
        status, etag, data = self.sync("dong_bo_nguyen_lieu")
        self.assertEqual((status, data), (200, INGREDIENTS))
        self.assertTrue(etag)
        self.assertEqual(self.sync("dong_bo_nguyen_lieu", etag), (304, etag, None))
        # Dữ liệu trên máy đổi thì ETag cũ không còn khớp.
        INGREDIENTS["ingredients"][0]["amount"] = 400
        self.addCleanup(INGREDIENTS["ingredients"][0].update, amount=500)
        status, etag_moi, data = self.sync("dong_bo_nguyen_lieu", etag)
        self.assertEqual((status, data["ingredients"][0]["amount"]), (200, 400))
        self.assertNotEqual(etag_moi, etag)
        # Máy đọc dữ liệu lỗi thì app nhận lỗi, vòng lặp của máy vẫn chạy.
        INGREDIENTS["loi_thu"] = object()
        self.addCleanup(INGREDIENTS.pop, "loi_thu")
        status, _, data = self.sync("dong_bo_nguyen_lieu")
        self.assertEqual(status, 502)
        self.assertIn("loi", data)
        # Lệnh ngoài bảng quyền bị server chặn, không xuống máy.
        self.assertEqual(self.sync("xem_menu")[0], 403)


if __name__ == "__main__":
    unittest.main()
