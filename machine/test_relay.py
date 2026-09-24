"""Chạy: python -m unittest machine.test_relay

Chạy vòng lặp thật của machine/main.py với server thật (SQLite tạm) và
database máy giả trong RAM, kiểm tra heartbeat + nhận lệnh + trả kết quả.
"""

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
from urllib.request import Request, urlopen

MACHINE_DIR = Path(__file__).resolve().parent
MENU = {"drinks": [{"drinkId": 1, "name": "Cà phê", "price": 20000, "available": True}]}


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
    return {
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

    def test_machine_serves_app_commands(self):
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


if __name__ == "__main__":
    unittest.main()
