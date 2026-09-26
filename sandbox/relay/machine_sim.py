"""Laptop chạy vòng lặp thật của machine/main.py (heartbeat, nhận lệnh, trả kết quả)
với database máy giả, để app thấy máy online và đọc/sửa menu, kho.

Database giả là một file SQLite tạm, tạo mới mỗi lần chạy và xóa khi dừng; đường
dẫn in ra lúc khởi động, mở bằng sqlite3 để xem hoặc sửa số liệu khi máy đang chạy.

Chạy từ thư mục gốc androidv0.1 (server đang chạy, máy đã đăng ký bằng key trong env):
    python sandbox/relay/machine_sim.py                  # dùng machine/config/machine.env
    python sandbox/relay/machine_sim.py --env may_thu.env
"""

import argparse
import importlib.util
import os
import sqlite3
import sys
import tempfile
import threading
import types
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MACHINE_DIR = ROOT / "machine"

# Hai bảng tối giản theo tên cột của database máy thật (MySQL).
SCHEMA = """
CREATE TABLE drink (
    drink_id INTEGER PRIMARY KEY,
    drink_name TEXT NOT NULL,
    price REAL NOT NULL,
    category TEXT NOT NULL,
    available INTEGER NOT NULL,
    in_stock INTEGER NOT NULL
);
CREATE TABLE ingredient (
    ingredient_id INTEGER PRIMARY KEY,
    ingredient_name TEXT NOT NULL,
    amount REAL NOT NULL,
    max_gram REAL,
    pump_no INTEGER,
    in_stock INTEGER NOT NULL
);
INSERT INTO drink VALUES
    (1, 'Cà phê sữa', 25000, 'Cà phê', 1, 1),
    (2, 'Trà đào', 30000, 'Trà', 1, 1),
    (3, 'Matcha latte', 35000, 'Trà', 0, 1);
INSERT INTO ingredient VALUES
    (1, 'Sữa tươi', 1200, 2000, 1, 1),
    (2, 'Đào ngâm', 0, 1500, 2, 0),
    (3, 'Cà phê hạt', 800, 1000, NULL, 1);
"""
# Máy thật dùng mức này khi max_gram chưa khai báo (NULL).
DEFAULT_MAX_GRAM = 10000.0

DB = None
LOCK = threading.Lock()


def open_database():
    """Tạo file SQLite tạm với dữ liệu mẫu; trả đường dẫn để in ra và xóa khi dừng."""
    global DB
    fd, path = tempfile.mkstemp(prefix="machine_sim_", suffix=".db")
    os.close(fd)
    DB = sqlite3.connect(path, check_same_thread=False)
    DB.row_factory = sqlite3.Row
    DB.executescript(SCHEMA)
    return path


def query(sql, params=()):
    with LOCK:
        return DB.execute(sql, params).fetchall()


def get_menu():
    rows = query("SELECT * FROM drink ORDER BY drink_id")
    return {"drinks": [
        {"drinkId": row["drink_id"], "name": row["drink_name"], "price": row["price"],
         "category": row["category"], "available": bool(row["available"]),
         "inStock": bool(row["in_stock"])}
        for row in rows
    ]}


def update_drink(column):
    def update(drink_id, value):
        with LOCK, DB:
            changed = DB.execute(f"UPDATE drink SET {column}=? WHERE drink_id=?",
                                 (value, drink_id)).rowcount
        if not changed:
            raise ValueError(f"Không có món id {drink_id}.")
    return update


def get_ingredients():
    # Cùng dạng database.admin_functions.ingredients.get_ingredients() của máy thật.
    rows = query("SELECT * FROM ingredient ORDER BY ingredient_id")
    return {"ingredients": [
        {"id": row["ingredient_id"], "name": row["ingredient_name"],
         "amount": row["amount"], "in_stock": bool(row["in_stock"])}
        for row in rows
    ]}


def ingredients_payload():
    # Cùng dạng database.admin_functions.ingredients.ingredients_payload() của máy thật (các trường app dùng).
    rows = query("SELECT * FROM ingredient ORDER BY ingredient_id")
    return {"ingredients": [
        {"ingredient_id": row["ingredient_id"], "name": row["ingredient_name"],
         "amount": row["amount"],
         "max_gram": row["max_gram"] if row["max_gram"] is not None else DEFAULT_MAX_GRAM,
         "max_set": row["max_gram"] is not None, "pump_no": row["pump_no"],
         "in_stock": bool(row["in_stock"])}
        for row in rows
    ]}


def update_inventory(mode):
    def update(ingredient_id, gram):
        with LOCK, DB:
            row = DB.execute("SELECT amount FROM ingredient WHERE ingredient_id=?",
                             (ingredient_id,)).fetchone()
            if row is None:
                raise ValueError(f"Không có nguyên liệu id {ingredient_id}.")
            amount = {"set": 0, "add": row["amount"], "subtract": row["amount"]}[mode]
            amount += -float(gram) if mode == "subtract" else float(gram)
            if amount < 0:
                raise ValueError("Không đủ nguyên liệu.")
            DB.execute("UPDATE ingredient SET amount=?, in_stock=? WHERE ingredient_id=?",
                       (amount, int(amount > 0), ingredient_id))
        return Decimal(str(amount))
    return update


def refill(target, value):
    # Cùng dạng database.admin_functions.ingredients.refill() của máy thật.
    with LOCK, DB:
        rows = DB.execute("SELECT ingredient_id, max_gram FROM ingredient" +
                          ("" if target == "all" else " WHERE ingredient_id=?"),
                          () if target == "all" else (int(target),)).fetchall()
        if not rows:
            raise ValueError(f"Không có nguyên liệu id {target}.")
        for row in rows:
            full = row["max_gram"] if row["max_gram"] is not None else DEFAULT_MAX_GRAM
            amount = full if value == "full" else float(value)
            DB.execute("UPDATE ingredient SET amount=?, in_stock=? WHERE ingredient_id=?",
                       (amount, int(amount > 0), row["ingredient_id"]))
    return {"count": len(rows)}


def install_fake_database():
    """Thay các module database của máy thật (MySQL) bằng hàm đọc SQLite tạm."""
    drinks = types.ModuleType("database.admin_functions.drinks")
    drinks.get_menu = get_menu
    drinks.set_drink_available = update_drink("available")
    drinks.set_drink_price = update_drink("price")
    ingredients = types.ModuleType("database.admin_functions.ingredients")
    ingredients.get_ingredients = get_ingredients
    ingredients.ingredients_payload = ingredients_payload
    ingredients.refill = refill
    inventory = types.ModuleType("database.inventory_service")
    inventory.publish_store_menu = lambda: ""
    inventory.set_inventory = update_inventory("set")
    inventory.add_inventory = update_inventory("add")
    inventory.subtract_inventory = update_inventory("subtract")
    sys.modules.update({
        "database": types.ModuleType("database"),
        "database.admin_functions": types.ModuleType("database.admin_functions"),
        "database.admin_functions.drinks": drinks,
        "database.admin_functions.ingredients": ingredients,
        "database.inventory_service": inventory,
    })


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Máy FlexMix giả nối server qua relay.")
    parser.add_argument("--env", help="file machine.env khác (tên, product key, server)")
    args = parser.parse_args()
    if args.env:
        os.environ["FLEXMIX_MACHINE_ENV"] = str(Path(args.env).resolve())

    # machine/main.py import theo kiểu chạy trong thư mục machine (config, server_connection).
    sys.path.insert(0, str(MACHINE_DIR))
    db_path = open_database()
    install_fake_database()
    spec = importlib.util.spec_from_file_location("machine_main", MACHINE_DIR / "main.py")
    machine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(machine)
    from config.machine_config import get_machine_name, get_server_url
    try:
        try:
            print(f"Máy giả {get_machine_name()} nối {get_server_url()}, Ctrl+C để dừng.", flush=True)
        except ValueError as error:
            sys.exit(str(error))
        print(f"Database tạm: {db_path}", flush=True)
        machine.run()
    except KeyboardInterrupt:
        print("Đã dừng máy giả.", flush=True)
    finally:
        DB.close()
        os.remove(db_path)


if __name__ == "__main__":
    main()
