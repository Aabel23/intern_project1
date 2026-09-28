"""Kiểm tra lệnh menu server chuyển xuống trước khi đụng database.

Server đã kiểm quyền người dùng; máy chỉ kiểm lệnh có đúng dạng không và món có
trên máy không. Sai thì raise ValueError, vòng lặp máy trả {"loi": ...} cho app.
"""


def is_price(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0


def is_available(value):
    return isinstance(value, bool)


# Cột app được sửa → hàm kiểm giá trị.
EDITABLE = {"available": is_available, "price": is_price}


def check_menu_version(data):
    menu_version = data.get("menu_version")
    if not isinstance(menu_version, int) or isinstance(menu_version, bool) or menu_version < 0:
        raise ValueError("menu_version không hợp lệ")
    return menu_version


def check_change(change, known_ids):
    """Một dòng thay_doi → (drink_id, {cột: giá trị ghi vào database})."""
    if not isinstance(change, dict) or change.get("drink_id") not in known_ids:
        raise ValueError(f"Không có món {change}")
    fields = {key: value for key, value in change.items() if key != "drink_id"}
    if not fields:
        raise ValueError(f"Món {change['drink_id']} không có cột nào để sửa")
    if not all(key in EDITABLE and EDITABLE[key](value) for key, value in fields.items()):
        raise ValueError(f"Món {change['drink_id']}: cột không sửa được hoặc giá trị sai")
    # SQLite lưu available dạng 0/1.
    if "available" in fields:
        fields["available"] = int(fields["available"])
    return change["drink_id"], fields


def check_changes(data, known_ids):
    """Kiểm hết mọi dòng thay_doi; trả list (drink_id, fields) sẵn sàng ghi."""
    thay_doi = data.get("thay_doi")
    if not isinstance(thay_doi, list) or not thay_doi:
        raise ValueError("Thiếu thay_doi")
    return [check_change(change, known_ids) for change in thay_doi]
