"""Nhận lệnh từ server rồi chọn hàm dữ liệu cần chạy."""

import gzip
import hashlib
import json
import time
import threading
import urllib.error

from server_connection import heartbeat, instruction_api

# Đọc menu và cập nhật món uống từ tầng database.
from database.admin_functions.drinks import (
    get_menu,
    set_drink_available,
    set_drink_price,
)

# Nguyên liệu: đọc gọn, dữ liệu kho đầy đủ (max_gram, pump_no...) và nạp kho.
from database.admin_functions.ingredients import (
    get_ingredients,
    ingredients_payload,
    refill,
)

# Cập nhật kho bằng các hàm sẵn có trong database.
from database.inventory_service import (
    set_inventory as set_ingredient_amount,
    add_inventory as add_ingredient_amount,
    subtract_inventory as subtract_ingredient_amount,
)


def handle_command(lenh):
    # Server chỉ giao lệnh trong hộp thư của máy xưng đúng product key.
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

    # Nạp kho từ app (/machine/refill): target = id nguyên liệu hoặc "all", value = "full" hoặc số gram.
    if ten == "nap_kho":
        return refill(thamso.get("target"), thamso.get("value"))

    return {"loi": "Lenh khong hop le"}


# Lệnh đồng bộ dashboard: tên lệnh -> hàm đọc database.
LENH_DONG_BO = {
    "dong_bo_nguyen_lieu": ingredients_payload,
}


def pack_sync(lenh):
    # ETag là hash của dữ liệu; trùng ETag app đang giữ thì gửi gói rỗng (không đổi).
    du_lieu = LENH_DONG_BO[lenh["ten"]]()
    raw = json.dumps(du_lieu, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    etag = '"' + hashlib.sha256(raw).hexdigest()[:32] + '"'
    if etag == lenh.get("etag"):
        return etag, b""
    return etag, gzip.compress(raw, mtime=0)


def run():
    # Heartbeat chạy riêng để vẫn báo máy đang hoạt động khi xử lý lệnh lâu.
    threading.Thread(target=heartbeat.run_heartbeat, daemon=True).start()

    while True:
        # Nhận lệnh từ server.
        try:
            lenh = instruction_api.poll_command()
        except (urllib.error.URLError, OSError, ValueError) as error:
            print("Khong ket noi duoc server:", error, flush=True)
            time.sleep(1)
            continue
        if lenh is None:
            time.sleep(1)
            continue

        # Phân tích lệnh và chạy hàm dữ liệu.
        print("Machine nhan lenh:", lenh, flush=True)
        try:
            if lenh.get("ten") in LENH_DONG_BO:
                ket_qua = pack_sync(lenh)
            else:
                ket_qua = handle_command(lenh)
        except Exception as error:
            # Lỗi tham số hay lỗi database đều trả về app, không làm dừng vòng lặp của máy.
            ket_qua = {"loi": str(error)}

        # Gửi kết quả về server để trả cho app.
        try:
            if isinstance(ket_qua, tuple):
                instruction_api.send_sync(lenh["id"], *ket_qua)
            else:
                instruction_api.send_result(lenh["id"], ket_qua)
        except (urllib.error.URLError, OSError) as error:
            print("Khong gui duoc ket qua:", error, flush=True)


if __name__ == "__main__":
    run()