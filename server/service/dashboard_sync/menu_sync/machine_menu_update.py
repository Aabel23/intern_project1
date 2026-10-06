"""Cập nhật menu: JSON app → (kết quả máy hoặc lỗi, HTTP status)."""

from server.lib.machine.machine_access import check_access
from server.lib.machine.machine_transport import send

# Cấu hình riêng: quyền thao tác, số món tối đa và giới hạn giá.
QUYEN_MENU = {"owner", "manager"}
MAX_CHANGES = 200
MAX_PRICE = 99999999.99


# Nhóm 1: kiểm từng giá trị cơ bản trong gói tin.
def is_number(value):
    # Bool là lớp con của int trong Python, nhưng không được dùng làm số ở đây.
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_menu_version(value):
    # Phiên bản CRC32: số nguyên không dấu 32 bit.
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value < 2**32


def is_drink_id(value):
    # ID món phải là số nguyên dương.
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def is_price(value):
    return is_number(value) and 0 <= value <= MAX_PRICE


def is_available(value):
    # Trạng thái món chỉ nhận true/false, không nhận 0/1.
    return isinstance(value, bool)


# Nhóm 2: kiểm một món, sau đó kiểm toàn bộ danh sách thay đổi.
# Chỉ hai cột này được sửa; mỗi cột gắn với hàm kiểm giá trị tương ứng.
EDITABLE = {"available": is_available, "price": is_price}


def is_change(change):
    # Một dòng: {drink_id, available?, price?}, phải có ít nhất một trường sửa.
    if not isinstance(change, dict) or not is_drink_id(change.get("drink_id")):
        return False
    fields = {key: value for key, value in change.items() if key != "drink_id"}
    # Từ chối trường lạ; tất cả giá trị phải hợp lệ.
    return bool(fields) and all(key in EDITABLE and EDITABLE[key](value) for key, value in fields.items())


def is_changes(thay_doi):
    # Danh sách 1..MAX_CHANGES dòng; một dòng sai thì cả gói bị từ chối.
    return isinstance(thay_doi, list) and 1 <= len(thay_doi) <= MAX_CHANGES and all(map(is_change, thay_doi))


# Nhóm 3: luồng chính được machine_menu_main gọi khi URL cập nhật menu khớp.
def cap_nhat_menu(data):
    # Bước 1: kiểm phiên và quyền máy; lỗi thì dừng trước khi kiểm nội dung.
    machine_id, error = check_access(data, QUYEN_MENU)
    if error:
        return error

    # Bước 2: kiểm phiên bản và danh sách thay đổi bằng các hàm phía trên.
    menu_version, thay_doi = data.get("menu_version"), data.get("thay_doi")
    if not is_menu_version(menu_version) or not is_changes(thay_doi):
        return {"loi": "Gói thay đổi menu không hợp lệ"}, 400
    # Token chỉ dùng tại server; máy nhận phiên bản và các món cần sửa.
    command_data = {"menu_version": menu_version, "thay_doi": thay_doi}

    # Bước 3: đưa lệnh vào hộp thư chung, chờ máy và trả nguyên kết quả.
    # Máy kiểm xung đột phiên bản và thực hiện cập nhật trong transaction.
    return send(machine_id, "cap_nhat_menu", command_data)
