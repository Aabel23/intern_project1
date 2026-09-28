"""Đọc/nạp kho qua tầng database của máy pha (MySQL, mã nguồn version1.0).

File duy nhất của tab Kho đụng database. Cần package database của version1.0 trên
PYTHONPATH (xem machine/README.md).
"""

# Tầng database của máy pha (version1.0)
from database.admin_functions.ingredients import ingredients_payload, refill
from database.inventory_service import publish_store_menu


def read_ingredients():
    """Danh sách nguyên liệu: ingredient_id, name, amount, max_gram, max_set, pump_no, in_stock..."""
    return ingredients_payload()["ingredients"]


def refill_ingredient(target, value):
    """Nạp kho bằng đúng hàm trang admin của máy dùng; trả kết quả của hàm đó."""
    return refill(target, value)


def republish_store_menu():
    """Dựng lại menu-data.js cho màn bán hàng; trả câu cảnh báo, rỗng nếu ổn."""
    return publish_store_menu()
