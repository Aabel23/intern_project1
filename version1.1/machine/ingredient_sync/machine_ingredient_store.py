"""Đọc/nạp kho qua tầng database của máy pha (MySQL, database/services/inventory.py).

File duy nhất của tab Kho đụng database. Cần thư mục gốc version1.1 trên
PYTHONPATH (xem machine/README.md).
"""

# Tầng database của máy pha
from database.services.inventory import list_ingredients, publish_store_menu, refill


def read_ingredients():
    """Danh sách nguyên liệu: ingredient_id, name, amount, max_gram, max_set, pump_no, in_stock..."""
    return list_ingredients()


def refill_ingredient(target, value):
    """Nạp kho: target = id hoặc "all", value = "full" hoặc số gram; trả kết quả nạp."""
    return refill(target, value)


def republish_store_menu():
    """Dựng lại menu-data.js cho màn bán hàng; trả câu cảnh báo, rỗng nếu ổn."""
    return publish_store_menu()
