"""Luồng tab Kho trên máy: verify → database → trả kết quả.

    nhan_kho: version trùng → up_to_date, khác → danh sách kho kèm version mới
    nap_kho:  kiểm target/value → nạp → dựng lại menu màn bán hàng → trả kết quả nạp

version là CRC32 của danh sách kho, cùng cách với menu_version của tab Menu.
"""

# Thư viện chuẩn
import json
import zlib

# Trong module ingredient_sync
from .ingredient_sync_database import read_ingredients, refill_ingredient, republish_store_menu
from .ingredient_sync_verify import check_refill, check_version


def version_of(ingredients):
    raw = json.dumps(ingredients, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return zlib.crc32(raw.encode("utf-8"))


def nhan_kho(data):
    version = check_version(data)
    ingredients = read_ingredients()
    current = version_of(ingredients)
    if version == current:
        return {"status": "up_to_date", "version": current}
    return {"status": "ok", "version": current, "ingredients": ingredients}


def nap_kho(data):
    target, value = check_refill(data)
    result = refill_ingredient(target, value)
    # Màn bán hàng đọc menu-data.js, không đọc MySQL: nạp xong phải dựng lại ngay.
    # Lỗi dựng menu không làm hỏng lệnh (database đã ghi), chỉ báo kèm "warning".
    warning = republish_store_menu()
    if warning:
        result = {**result, "warning": warning}
    return result
