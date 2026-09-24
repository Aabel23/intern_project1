"""Laptop chạy vòng lặp thật của machine/main.py (heartbeat, nhận lệnh, trả kết quả)
với database máy giả trong RAM, để app thấy máy online và đọc/sửa menu, kho.

Chạy từ thư mục gốc androidv0.1 (server đang chạy, máy đã đăng ký bằng key trong env):
    python sandbox/relay/machine_sim.py                  # dùng machine/config/machine.env
    python sandbox/relay/machine_sim.py --env may_thu.env
"""

import argparse
import importlib.util
import os
import sys
import threading
import types
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MACHINE_DIR = ROOT / "machine"

# Cùng dạng dữ liệu mà database máy thật (MySQL) trả cho app.
DRINKS = {
    1: {"drinkId": 1, "name": "Cà phê sữa", "price": 25000.0, "category": "Cà phê",
        "available": True, "inStock": True},
    2: {"drinkId": 2, "name": "Trà đào", "price": 30000.0, "category": "Trà",
        "available": True, "inStock": True},
    3: {"drinkId": 3, "name": "Matcha latte", "price": 35000.0, "category": "Trà",
        "available": False, "inStock": True},
}
INGREDIENTS = {
    1: {"id": 1, "name": "Sữa tươi", "amount": 1200.0, "in_stock": True, "max_gram": 2000.0, "pump_no": 1},
    2: {"id": 2, "name": "Đào ngâm", "amount": 0.0, "in_stock": False, "max_gram": 1500.0, "pump_no": 2},
    3: {"id": 3, "name": "Cà phê hạt", "amount": 800.0, "in_stock": True, "max_gram": 1000.0, "pump_no": None},
}
LOCK = threading.Lock()


def set_drink_available(drink_id, available):
    with LOCK:
        if drink_id not in DRINKS:
            raise ValueError(f"Không có món id {drink_id}.")
        DRINKS[drink_id]["available"] = bool(available)


def set_drink_price(drink_id, price):
    with LOCK:
        if drink_id not in DRINKS:
            raise ValueError(f"Không có món id {drink_id}.")
        DRINKS[drink_id]["price"] = round(float(price), 2)


def update_inventory(mode):
    def update(ingredient_id, gram):
        with LOCK:
            if ingredient_id not in INGREDIENTS:
                raise ValueError(f"Không có nguyên liệu id {ingredient_id}.")
            row = INGREDIENTS[ingredient_id]
            amount = {"set": 0, "add": row["amount"], "subtract": row["amount"]}[mode]
            amount += -float(gram) if mode == "subtract" else float(gram)
            if amount < 0:
                raise ValueError("Không đủ nguyên liệu.")
            row["amount"], row["in_stock"] = amount, amount > 0
            return Decimal(str(amount))
    return update


def ingredients_payload():
    # Cùng dạng admin_gui.serve.ingredients_payload() của máy thật (các trường app dùng).
    with LOCK:
        return {"ingredients": [
            {"ingredient_id": row["id"], "name": row["name"], "amount": row["amount"],
             "max_gram": row["max_gram"], "max_set": True, "pump_no": row["pump_no"],
             "in_stock": row["in_stock"]}
            for row in INGREDIENTS.values()
        ]}


def install_fake_database():
    """Thay các module database của máy thật (MySQL) bằng dữ liệu trong RAM."""
    drinks = types.ModuleType("database.admin_functions.drinks")
    drinks.get_menu = lambda: {"drinks": [dict(row) for row in DRINKS.values()]}
    drinks.set_drink_available = set_drink_available
    drinks.set_drink_price = set_drink_price
    ingredients = types.ModuleType("database.admin_functions.ingredients")
    ingredients.get_ingredients = lambda: {"ingredients": [dict(row) for row in INGREDIENTS.values()]}
    inventory = types.ModuleType("database.inventory_service")
    inventory.set_inventory = update_inventory("set")
    inventory.add_inventory = update_inventory("add")
    inventory.subtract_inventory = update_inventory("subtract")
    serve = types.ModuleType("admin_gui.serve")
    serve.ingredients_payload = ingredients_payload
    sys.modules.update({
        "admin_gui": types.ModuleType("admin_gui"),
        "admin_gui.serve": serve,
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
    install_fake_database()
    spec = importlib.util.spec_from_file_location("machine_main", MACHINE_DIR / "main.py")
    machine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(machine)
    from config.machine_config import get_machine_name, get_server_url
    try:
        print(f"Máy giả {get_machine_name()} nối {get_server_url()}, Ctrl+C để dừng.", flush=True)
    except ValueError as error:
        sys.exit(str(error))
    try:
        machine.run()
    except KeyboardInterrupt:
        print("Đã dừng máy giả.", flush=True)


if __name__ == "__main__":
    main()
