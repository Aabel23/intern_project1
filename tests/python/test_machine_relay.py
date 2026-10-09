"""Chạy: python -m unittest tests.python.test_machine_relay

Chạy vòng lặp thật của machine/main.py với server thật (SQLite tạm) và
database máy giả, kiểm tra heartbeat + nhận lệnh + trả kết quả cho tab Menu và Kho.
"""

import base64
import importlib.util
import json
import os
import sqlite3
import sys
import tempfile
import threading
import types
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

MACHINE_DIR = Path(__file__).resolve().parents[2] / "machine"
MACHINE_PACKAGES = ("config", "server_connection", "menu_sync", "ingredient_sync")
INGREDIENTS = {"ingredients": [{"ingredient_id": 1, "name": "Sữa", "amount": 500, "max_gram": 1000,
                                "max_set": True, "pump_no": 1, "in_stock": True}]}


def fake_database(calls):
    """Thay tầng database MySQL của máy (version1.0) bằng module giả ghi lại lời gọi."""
    ingredients = types.ModuleType("database.admin_functions.ingredients")
    ingredients.ingredients_payload = lambda: INGREDIENTS

    def refill(target, value):
        calls.append(("refill", target, value))
        return {"ingredient_id": target, "amount": 1000, "in_stock": True}
    ingredients.refill = refill
    inventory = types.ModuleType("database.inventory_service")
    inventory.publish_store_menu = lambda: calls.append(("publish",)) or ""
    return {
        "database": types.ModuleType("database"),
        "database.admin_functions": types.ModuleType("database.admin_functions"),
        "database.admin_functions.ingredients": ingredients,
        "database.inventory_service": inventory,
    }


def machine_modules():
    return [name for name in list(sys.modules) if name.split(".")[0] in MACHINE_PACKAGES]


class MachineRelayTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        patch("server.database.connection.DB_PATH", Path(folder.name) / "test.db").start()
        self.addCleanup(patch.stopall)
        from server import main as server_main
        from server.database.connection import get_connection
        from server.database.machine.init_db import init_db
        from server.lib.security.user_session import create_session
        init_db()
        self.server = server_main.create_server(("127.0.0.1", 0))
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        with get_connection() as conn:
            user_id = conn.execute(
                "INSERT INTO users (full_name, username, password, email) VALUES ('o','o','x','o@t.local')"
            ).lastrowid
        self.token = create_session(user_id)
        self.machine_id = self.post("/app/user/machine/register", {
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
        # machine/main.py import theo kiểu chạy trong thư mục machine (config, server_connection...).
        patch.object(sys, "path", [str(MACHINE_DIR), *sys.path]).start()
        saved = {name: sys.modules.pop(name) for name in machine_modules()}
        self.addCleanup(sys.modules.update, saved)
        self.addCleanup(lambda: [sys.modules.pop(name, None) for name in machine_modules()])
        patch.dict(sys.modules, fake_database(self.calls)).start()
        spec = importlib.util.spec_from_file_location("machine_main_under_test", MACHINE_DIR / "main.py")
        self.machine = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.machine)
        # Menu máy đọc SQLite; dùng bản tạm hai món thay cho machine/database/database.db.
        menu_db = Path(folder.name) / "machine.db"
        with sqlite3.connect(menu_db) as conn:
            conn.execute("CREATE TABLE drink (drink_id INTEGER PRIMARY KEY, drink_name TEXT, image TEXT,"
                         " price NUMERIC, available INTEGER, in_stock INTEGER, deleted_at TEXT,"
                         " glass_id INTEGER, drink_type_id INTEGER, garnish TEXT, featured INTEGER)")
            conn.executemany("INSERT INTO drink VALUES (?, ?, NULL, ?, 1, 1, ?, NULL, NULL, NULL, 0)",
                             [(1001, "Cà phê", 20000, None), (1002, "Trà đào", 30000, None),
                              (1003, "Món đã xóa", 1, "2026-01-01")])
        conn.close()
        from menu_sync import machine_menu_store
        patch.object(machine_menu_store, "DB_PATH", menu_db).start()

    def post(self, path, data):
        request = Request(self.url + path, data=json.dumps(data).encode(),
                          headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read())

    def call(self, path, data):
        """POST kèm token và machine_id của test; trả (status, JSON)."""
        request = Request(self.url + path, headers={"Content-Type": "application/json"},
                          data=json.dumps({"token": self.token, "machine_id": self.machine_id, **data}).encode())
        try:
            with urlopen(request, timeout=30) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            with error:
                return error.code, json.loads(error.read())

    def test_machine_serves_app_commands(self):
        # Máy chưa chạy (chưa heartbeat) thì server báo offline ngay.
        self.assertEqual(self.call("/app/machine/ingredient/get", {"version": 0})[0], 503)
        threading.Thread(target=self.machine.run, daemon=True).start()
        for _ in range(100):
            with urlopen(f"{self.url}/app/machine/status/get?machine_id={self.machine_id}") as response:
                if json.loads(response.read())["online"]:
                    break
            threading.Event().wait(0.05)
        else:
            self.fail("Máy không heartbeat được bằng product key")
        self.check_menu_tab()
        self.check_ingredient_tab()
        # Các route cũ đã bỏ.
        for path in ("/app/gui-lenh", "/app/dong-bo", "/machine/refill", "/machine/tra-dong-bo"):
            self.assertEqual(self.call(path, {})[0], 404)

    def check_menu_tab(self):
        unpack = lambda reply: json.loads(zlib.decompress(base64.b64decode(reply["packet"])))
        # Lần đầu (menu_version 0) nhận nguyên gói; món đã xóa mềm không có trong gói.
        status, reply = self.call("/app/machine/menu/get", {"menu_version": 0})
        self.assertEqual((status, reply["status"]), (200, "ok"))
        packet = unpack(reply)
        self.assertEqual((packet["type"], packet["v"], packet["menu_version"]), ("menu_sync", 1, reply["menu_version"]))
        drinks = [dict(zip(packet["fields"], row)) for row in packet["drinks"]]
        self.assertEqual([d["drink_name"] for d in drinks], ["Cà phê", "Trà đào"])
        version = reply["menu_version"]
        # Đã có bản mới nhất thì máy không gửi lại gói.
        self.assertEqual(self.call("/app/machine/menu/get", {"menu_version": version}),
                         (200, {"status": "up_to_date", "menu_version": version}))

        # Gửi thay đổi dựa trên bản đang giữ: máy ghi rồi trả menu mới.
        status, reply = self.call("/app/machine/menu/update", {"menu_version": version, "thay_doi": [
            {"drink_id": 1001, "available": False}, {"drink_id": 1002, "price": 35000}]})
        self.assertEqual((status, reply["status"]), (200, "ok"))
        drinks = {row[0]: dict(zip(packet["fields"], row)) for row in unpack(reply)["drinks"]}
        self.assertEqual((drinks[1001]["available"], drinks[1002]["price"]), (0, 35000))
        self.assertNotEqual(reply["menu_version"], version)
        # Gửi lại trên bản cũ thì máy không ghi, trả conflict kèm menu mới nhất.
        status, stale = self.call("/app/machine/menu/update", {"menu_version": version, "thay_doi": [
            {"drink_id": 1001, "available": True}]})
        self.assertEqual((status, stale["status"], stale["menu_version"]), (200, "conflict", reply["menu_version"]))
        # Món không có trên máy: máy báo lỗi, không ghi gì.
        status, error = self.call("/app/machine/menu/update", {"menu_version": reply["menu_version"], "thay_doi": [
            {"drink_id": 1002, "price": 1}, {"drink_id": 1003, "price": 1}]})
        self.assertEqual(status, 502)
        self.assertIn("loi", error)
        self.assertEqual(self.call("/app/machine/menu/get", {"menu_version": reply["menu_version"]})[1]["status"],
                         "up_to_date")
        # Gói sai bị server chặn, không xuống máy.
        for bad in ({"menu_version": -1}, {"menu_version": "x"}):
            self.assertEqual(self.call("/app/machine/menu/get", bad)[0], 400)
        for thay_doi in ([], [{"drink_id": 1001}], [{"drink_id": 1001, "drink_name": "x"}],
                         [{"drink_id": 1001, "price": -1}], [{"drink_id": 1001, "available": 1}],
                         [{"drink_id": True, "price": 1}], {"drink_id": 1001}):
            self.assertEqual(self.call("/app/machine/menu/update", {"menu_version": 0, "thay_doi": thay_doi})[0], 400)

    def check_ingredient_tab(self):
        # Lần đầu (version 0) nhận nguyên danh sách kho kèm version.
        status, reply = self.call("/app/machine/ingredient/get", {"version": 0})
        self.assertEqual((status, reply["status"], reply["ingredients"]), (200, "ok", INGREDIENTS["ingredients"]))
        version = reply["version"]
        # Đã có bản mới nhất thì máy không gửi lại danh sách.
        self.assertEqual(self.call("/app/machine/ingredient/get", {"version": version}),
                         (200, {"status": "up_to_date", "version": version}))
        # Kho trên máy đổi thì version cũ không còn khớp.
        INGREDIENTS["ingredients"][0]["amount"] = 400
        self.addCleanup(INGREDIENTS["ingredients"][0].update, amount=500)
        status, reply = self.call("/app/machine/ingredient/get", {"version": version})
        self.assertEqual((status, reply["ingredients"][0]["amount"]), (200, 400))
        self.assertNotEqual(reply["version"], version)
        # Máy đọc dữ liệu lỗi thì app nhận lỗi 502, vòng lặp của máy vẫn chạy.
        INGREDIENTS["ingredients"].append(object())
        self.addCleanup(INGREDIENTS["ingredients"].pop)
        status, error = self.call("/app/machine/ingredient/get", {"version": 0})
        self.assertEqual(status, 502)
        self.assertIn("loi", error)

        # Nạp kho: target = id hoặc "all", value = "full" hoặc số gram; nạp xong dựng lại menu bán hàng.
        self.calls.clear()
        self.assertEqual(self.call("/app/machine/ingredient/refill", {"target": 1, "value": "full"}),
                         (200, {"ingredient_id": 1, "amount": 1000, "in_stock": True}))
        self.assertEqual(self.call("/app/machine/ingredient/refill", {"target": "all", "value": "full"})[0], 200)
        self.assertEqual(self.call("/app/machine/ingredient/refill", {"target": 2, "value": 750})[0], 200)
        self.assertEqual(self.calls, [("refill", 1, "full"), ("publish",), ("refill", "all", "full"), ("publish",),
                                      ("refill", 2, 750), ("publish",)])
        # Gói sai bị server chặn, không xuống máy.
        for target, value in (("all", 500), (0, "full"), (1, -5), (1, "nhieu"), (True, "full"),
                              (None, "full"), (1, True), (1, None), (1, 100000000),
                              (1, float('nan')), (1, float('inf'))):
            self.assertEqual(self.call("/app/machine/ingredient/refill", {"target": target, "value": value})[0], 400)
        for bad in ({"version": -1}, {"version": "x"}, {"version": True}, {"version": 2**32},
                    {"version": None}, {"version": 1.5}):
            self.assertEqual(self.call("/app/machine/ingredient/get", bad)[0], 400)
        self.assertEqual(len(self.calls), 6)


if __name__ == "__main__":
    unittest.main()
