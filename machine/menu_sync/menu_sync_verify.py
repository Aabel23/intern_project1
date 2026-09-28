"""Kiểm tra lệnh menu server chuyển xuống trước khi đụng database.

Server đã kiểm quyền người dùng; máy chỉ kiểm lệnh có đúng dạng không và món có
trên máy không. Sai thì raise ValueError, vòng lặp máy trả {"loi": ...} cho app.
"""

# Cột app được sửa, kèm kiểu hợp lệ.
EDITABLE = {"available": (bool,), "price": (int, float)}


def check_menu_version(thamso):
    menu_version = thamso.get("menu_version") if isinstance(thamso, dict) else None
    if not isinstance(menu_version, int) or isinstance(menu_version, bool) or menu_version < 0:
        raise ValueError("menu_version không hợp lệ")
    return menu_version


def check_changes(thamso, known_ids):
    """Trả list (drink_id, {cột: giá trị đã chuẩn hóa}) sẵn sàng ghi."""
    thay_doi = thamso.get("thay_doi")
    if not isinstance(thay_doi, list) or not thay_doi:
        raise ValueError("Thiếu thay_doi")
    checked = []
    for change in thay_doi:
        if not isinstance(change, dict) or change.get("drink_id") not in known_ids:
            raise ValueError(f"Không có món {change.get('drink_id') if isinstance(change, dict) else change}")
        fields = {}
        for key, value in change.items():
            if key == "drink_id":
                continue
            if key not in EDITABLE or not isinstance(value, EDITABLE[key]) or (
                    key == "price" and isinstance(value, bool)):
                raise ValueError(f"Cột {key} không sửa được hoặc sai kiểu")
            if key == "price" and value < 0:
                raise ValueError("Giá món không được âm")
            fields[key] = int(value) if key == "available" else value
        if not fields:
            raise ValueError(f"Món {change['drink_id']} không có cột nào để sửa")
        checked.append((change["drink_id"], fields))
    return checked
