"""Hàm kiểm tra và hàm chức năng của tab Menu; không đọc/ghi HTTP.

Kiểm tra: người gửi có quyền với máy không, gói app gửi có đúng dạng không.
Chức năng: chuyển lệnh xuống máy qua hộp thư relay dùng chung và chờ kết quả.
"""

# Server chung: database máy, hàm kiểm tra
from server.database.machine.machine_read import can_manage, is_owner
from server.lib.checks import is_machine_id

# Module khác: phiên đăng nhập, bảng quyền, hộp thư lệnh của máy
from server.service.dashboard_sync.sync_rules import QUYEN_MENU
from server.service.machine_relay import relay_queue as relay
from server.service.user_login.session import NOT_LOGGED_IN, user_from_request

# Cột app được sửa, kèm kiểu hợp lệ; máy cũng chỉ ghi đúng các cột này.
EDITABLE = {"available": (bool,), "price": (int, float)}
MAX_CHANGES = 200
MAX_PRICE = 99999999.99


# ---------- kiểm tra ----------

def is_menu_version(value):
    # CRC32: số nguyên 0..2^32-1; app chưa có menu gửi 0.
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value < 2**32


def is_change(change):
    """Một dòng thay_doi: {drink_id, available?, price?}, ít nhất một cột được sửa."""
    if not isinstance(change, dict):
        return False
    drink_id = change.get("drink_id")
    if not isinstance(drink_id, int) or isinstance(drink_id, bool) or drink_id <= 0:
        return False
    fields = set(change) - {"drink_id"}
    if not fields or not fields <= set(EDITABLE):
        return False
    for key in fields:
        value = change[key]
        if not isinstance(value, EDITABLE[key]) or (key == "price" and isinstance(value, bool)):
            return False
        if key == "price" and not 0 <= value <= MAX_PRICE:
            return False
    return True


def is_changes(thay_doi):
    return (isinstance(thay_doi, list) and 1 <= len(thay_doi) <= MAX_CHANGES
            and all(map(is_change, thay_doi)))


def check_access(data):
    """Trả (machine_id, None) nếu được đụng menu máy này, sai thì (None, (lỗi, status))."""
    user_id = user_from_request(data)
    if user_id is None:
        return None, ({"loi": NOT_LOGGED_IN["message"], "login_required": True}, 401)
    machine_id = data.get("machine_id")
    if not is_machine_id(machine_id) or not can_manage(machine_id, user_id):
        return None, ({"loi": "Bạn không quản lý máy này"}, 403)
    vai_tro = "owner" if is_owner(machine_id, user_id) else "manager"
    if vai_tro not in QUYEN_MENU:
        return None, ({"loi": "Không đủ quyền với menu"}, 403)
    return machine_id, None


# ---------- chức năng ----------

def send_to_machine(machine_id, ten, thamso):
    """Bỏ lệnh vào hộp thư chung của máy và chờ máy long-poll lấy, trả (kết quả, status).

    Hộp thư nằm ở machine_relay/relay_queue.py vì máy chỉ hỏi lệnh ở một chỗ (/machine/hoi-lenh)
    cho mọi loại lệnh; module này chỉ dùng, không giữ hộp thư riêng.
    """
    if not relay.is_online(machine_id):
        return {"loi": "Máy đang offline"}, 503
    lenh = {"id": next(relay.DEM_LENH), "ten": ten, "thamso": thamso}
    ket_qua = relay.gui_va_cho(machine_id, lenh)
    if not isinstance(ket_qua, dict) or not ("loi" in ket_qua or "status" in ket_qua):
        ket_qua = {"loi": "Máy trả kết quả không đúng loại lệnh"}
    return ket_qua, 502 if "loi" in ket_qua else 200
