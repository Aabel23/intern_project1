"""Chạy: python -m unittest machine.test_relay

Chạy vòng lặp thật của machine/main.py với server thật (SQLite tạm) và
database máy giả trong RAM, kiểm tra heartbeat + nhận lệnh + trả kết quả.
"""

import base64
import gzip
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

MACHINE_DIR = Path(__file__).resolve().parent
INGREDIENTS = {"ingredients": [{"ingredient_id": 1, "name": "Sữa", "amount": 500, "max_gram": 1000,
                                "max_set": True, "pump_no": 1, "in_stock": True}]}


def fake_database(calls):
    """Thay tầng database MySQL của máy bằng module giả ghi lại lời gọi."""
    ingredients = types.ModuleType("database.admin_functions.ingredients")
    ingredients.get_ingredients = lambda: {"ingredients": []}
    ingredients.ingredients_payload = lambda: INGREDIENTS

    def refill(target, value):
        calls.append(("refill", target, value))
        return {"ingredient_id": target, "amount": 1000, "in_stock": True}
    ingredients.refill = refill
    inventory = types.ModuleType("database.inventory_service")
    inventory.publish_store_menu = lambda: calls.append(("publish",)) or ""

    def fail(*_):
        raise RuntimeError("MySQL mất kết nối")
    inventory.set_inventory = inventory.add_inventory = inventory.subtract_inventory = fail
    return {
        "database": types.ModuleType("database"),
        "database.admin_functions": types.ModuleType("database.admin_functions"),
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
                 if name.split(".")[0] in ("config", "server_connection", "menu_sync")}
        self.addCleanup(sys.modules.update, saved)
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
        from menu_sync import menu_sync_database
        patch.object(menu_sync_database, "DB_PATH", menu_db).start()
        self.addCleanup(lambda: [sys.modules.pop(n, None) for n in list(sys.modules)
                                 if n.split(".")[0] in ("config", "server_connection", "menu_sync")])

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
        self.check_menu_tab()
        # Lỗi database trả về app, vòng lặp của máy vẫn chạy tiếp.
        self.assertEqual(send("them_nguyen_lieu", {"ingredient_id": 1, "gram": 5}),
                         {"loi": "MySQL mất kết nối"})
        # Lệnh ngoài bảng QUYEN_LENH hoặc tham số sai kiểu bị server chặn, không xuống máy.
        for ten, thamso in (("lenh_la", {}), (None, {}), ("xem_nguyen_lieu", [1])):
            with self.assertRaises(HTTPError) as caught:
                self.post("/app/gui-lenh", {"token": self.token, "machine_id": self.machine_id,
                                            "ten": ten, "thamso": thamso})
            caught.exception.close()
            self.assertIn(caught.exception.code, (400, 403))
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
        self.assertEqual(self.sync("nhan_menu")[0], 403)

        # Nạp kho qua /machine/refill: {machine_id, target, value}.
        self.calls.clear()
        self.assertEqual(self.refill(1, "full"),
                         (200, {"ingredient_id": 1, "amount": 1000, "in_stock": True}))
        self.assertEqual(self.refill("all", "full")[0], 200)
        self.assertEqual(self.refill(2, 750)[0], 200)
        self.assertEqual([c for c in self.calls if c[0] == "refill"],
                         [("refill", 1, "full"), ("refill", "all", "full"), ("refill", 2, 750)])
        self.assertEqual(self.calls.count(("publish",)), 3)
        # Gói sai bị server chặn, không xuống máy.
        for target, value in (("all", 500), (0, "full"), (1, -5), (1, "nhieu"), (True, "full")):
            self.assertEqual(self.refill(target, value)[0], 400)
        self.assertEqual(len(self.calls), 6)

    def menu(self, path, data):
        request = Request(self.url + path, headers={"Content-Type": "application/json"},
                          data=json.dumps({"token": self.token, "machine_id": self.machine_id, **data}).encode())
        try:
            with urlopen(request, timeout=30) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            with error:
                return error.code, json.loads(error.read())

    def check_menu_tab(self):
        unpack = lambda reply: json.loads(zlib.decompress(base64.b64decode(reply["packet"])))
        # Lần đầu (menu_version 0) nhận nguyên gói; món đã xóa mềm không có trong gói.
        status, reply = self.menu("/app/nhan-menu", {"menu_version": 0})
        self.assertEqual((status, reply["status"]), (200, "ok"))
        packet = unpack(reply)
        self.assertEqual((packet["type"], packet["v"], packet["menu_version"]), ("menu_sync", 1, reply["menu_version"]))
        drinks = [dict(zip(packet["fields"], row)) for row in packet["drinks"]]
        self.assertEqual([d["drink_name"] for d in drinks], ["Cà phê", "Trà đào"])
        version = reply["menu_version"]
        # Đã có bản mới nhất thì máy không gửi lại gói.
        self.assertEqual(self.menu("/app/nhan-menu", {"menu_version": version}),
                         (200, {"status": "up_to_date", "menu_version": version}))

        # Gửi thay đổi dựa trên bản đang giữ: máy ghi rồi trả menu mới.
        status, reply = self.menu("/app/gui-menu", {"menu_version": version, "thay_doi": [
            {"drink_id": 1001, "available": False}, {"drink_id": 1002, "price": 35000}]})
        self.assertEqual((status, reply["status"]), (200, "ok"))
        drinks = {row[0]: dict(zip(packet["fields"], row)) for row in unpack(reply)["drinks"]}
        self.assertEqual((drinks[1001]["available"], drinks[1002]["price"]), (0, 35000))
        self.assertNotEqual(reply["menu_version"], version)
        # Gửi lại trên bản cũ thì máy không ghi, trả conflict kèm menu mới nhất.
        status, stale = self.menu("/app/gui-menu", {"menu_version": version, "thay_doi": [
            {"drink_id": 1001, "available": True}]})
        self.assertEqual((status, stale["status"], stale["menu_version"]), (200, "conflict", reply["menu_version"]))
        # Món không có trên máy: máy báo lỗi, không ghi gì.
        status, error = self.menu("/app/gui-menu", {"menu_version": reply["menu_version"], "thay_doi": [
            {"drink_id": 1002, "price": 1}, {"drink_id": 1003, "price": 1}]})
        self.assertEqual(status, 502)
        self.assertIn("loi", error)
        self.assertEqual(self.menu("/app/nhan-menu", {"menu_version": reply["menu_version"]})[1]["status"],
                         "up_to_date")
        # Gói sai bị server chặn, không xuống máy.
        for bad in ({"menu_version": -1}, {"menu_version": "x"}):
            self.assertEqual(self.menu("/app/nhan-menu", bad)[0], 400)
        for thay_doi in ([], [{"drink_id": 1001}], [{"drink_id": 1001, "drink_name": "x"}],
                         [{"drink_id": 1001, "price": -1}], [{"drink_id": 1001, "available": 1}],
                         [{"drink_id": True, "price": 1}], {"drink_id": 1001}):
            self.assertEqual(self.menu("/app/gui-menu", {"menu_version": 0, "thay_doi": thay_doi})[0], 400)

    def refill(self, target, value):
        request = Request(self.url + "/machine/refill", headers={"Content-Type": "application/json"},
                          data=json.dumps({"token": self.token, "machine_id": self.machine_id,
                                           "target": target, "value": value}).encode())
        try:
            with urlopen(request, timeout=30) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            with error:
                return error.code, json.loads(error.read())


if __name__ == "__main__":
    unittest.main()
