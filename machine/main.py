"""Nhận lệnh từ server rồi chọn hàm dữ liệu cần chạy."""

import time
import threading
import urllib.error

from config.machine_config import MACHINE_ID
from server_connection import heartbeat, instruction_api

# Đọc menu và cập nhật món uống từ tầng database.
from database.admin_functions.drinks import (
    get_menu,
    set_drink_available,
    set_drink_price,
)

# Đọc nguyên liệu theo cấu trúc gọn cho machine.
from database.admin_functions.ingredients import get_ingredients

# Cập nhật kho bằng các hàm sẵn có trong database.
from database.inventory_service import (
    set_inventory as set_ingredient_amount,
    add_inventory as add_ingredient_amount,
    subtract_inventory as subtract_ingredient_amount,
)


def handle_command(lenh):
    # Kiểm tra lệnh có gửi đúng cho máy này không.
    if lenh.get("machine_id") != MACHINE_ID:
        return {"loi": "Machine ID khong dung"}

    ten = lenh.get("ten")
    thamso = lenh.get("thamso", {})

    # Đọc dữ liệu.
    if ten == "xem_menu":
        return get_menu()
    if ten == "xem_nguyen_lieu":
        return get_ingredients()

    # Cập nhật món uống.
    if ten == "doi_trang_thai_mon":
        set_drink_available(thamso["drink_id"], thamso["available"])
        return {"ok": True}
    if ten == "doi_gia_mon":
        set_drink_price(thamso["drink_id"], thamso["price"])
        return {"ok": True}

    # Cập nhật kho nguyên liệu.
    if ten == "dat_luong_nguyen_lieu":
        amount = set_ingredient_amount(thamso["ingredient_id"], thamso["gram"])
        return {"amount": float(amount)}
    if ten == "them_nguyen_lieu":
        amount = add_ingredient_amount(thamso["ingredient_id"], thamso["gram"])
        return {"amount": float(amount)}
    if ten == "tru_nguyen_lieu":
        amount = subtract_ingredient_amount(thamso["ingredient_id"], thamso["gram"])
        return {"amount": float(amount)}

    return {"loi": "Lenh khong hop le"}


def run():
    # Heartbeat chạy riêng để vẫn báo máy đang hoạt động khi xử lý lệnh lâu.
    threading.Thread(target=heartbeat.run_heartbeat, daemon=True).start()

    while True:
        # Nhận lệnh từ server.
        try:
            lenh = instruction_api.poll_command()
        except (urllib.error.URLError, OSError) as error:
            print("Khong ket noi duoc server:", error, flush=True)
            time.sleep(1)
            continue
        if lenh is None:
            time.sleep(1)
            continue

        # Phân tích lệnh và chạy hàm dữ liệu.
        print("Machine nhan lenh:", lenh, flush=True)
        try:
            ket_qua = handle_command(lenh)
        except (KeyError, TypeError, ValueError) as error:
            ket_qua = {"loi": str(error)}

        # Gửi kết quả về server để trả cho app.
        try:
            instruction_api.send_result(lenh["id"], ket_qua)
        except (urllib.error.URLError, OSError) as error:
            print("Khong gui duoc ket qua:", error, flush=True)


if __name__ == "__main__":
    run()