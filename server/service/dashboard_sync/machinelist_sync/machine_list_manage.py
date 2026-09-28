"""Luồng tab Máy: kiểm tra yêu cầu, quyền và cập nhật dữ liệu máy.

    list_my_machines: đăng nhập → các máy người này là chủ hoặc nhân viên
    machine_status:   máy có heartbeat trong 15 giây gần nhất không (Online/Offline)
    rename_machine:   đăng nhập → mã máy → tên 1-150 ký tự → phải là chủ → đổi tên
    remove_machine:   đăng nhập → mã máy → khóa ghi → chủ thì xóa máy,
                      nhân viên thì chỉ bỏ quyền của mình, người lạ thì từ chối

Dữ liệu tab này là của server (bảng machines, giờ heartbeat trong RAM), không
hỏi xuống máy nên máy offline vẫn dùng được. Hàm route nhận body JSON đã parse,
trả thân {"valid", "message", ...}; api gắn status theo valid (200/400).
"""

from server.database.connection import get_connection
from server.database.machine import machine_read
from server.database.machine.machine_write import remove_manager
from server.lib.checks import is_machine_id
from server.lib.http_json import invalid
from server.lib.machine_transport import is_online, last_seen_of
from server.lib.session import check_login

from .machine_list_store import list_by_user, rename_machine as save_name, delete_machine


NAME_MAX_LENGTH = 150


def check_request(data):
    """Trả (user_id, machine_id, None) nếu đã đăng nhập và mã máy đúng dạng, sai thì (None, None, lỗi)."""
    user_id, error = check_login(data)
    if error:
        return None, None, error
    machine_id = data.get("machine_id")
    if not is_machine_id(machine_id):
        return None, None, invalid("Thiếu mã máy hợp lệ")
    return user_id, machine_id, None


def clean_name(name):
    """Tên đã bỏ khoảng trắng hai đầu; None nếu rỗng hoặc dài quá NAME_MAX_LENGTH."""
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > NAME_MAX_LENGTH:
        return None
    return name.strip()


def role_of(conn, machine_id, user_id):
    """"owner", "manager" hoặc None; đọc trong conn của flow để cùng transaction với lệnh ghi."""
    if machine_read.is_owner(machine_id, user_id, conn):
        return "owner"
    if machine_read.can_manage(machine_id, user_id, conn):
        return "manager"
    return None


def list_my_machines(data):
    """Các máy tài khoản đang là chủ (owner) hoặc được giao quản lý (manager)."""
    user_id, error = check_login(data)
    if error:
        return error
    return {"valid": True, "machines": list_by_user(user_id)}


def machine_status(machine_id):
    """Không cần token: chỉ báo máy còn liên lạc với server, như trước."""
    return {"machine_id": machine_id, "online": is_online(machine_id), "last_seen": last_seen_of(machine_id)}


def rename_machine(data):
    """Chủ máy đổi tên hiển thị; tên do người dùng nhập trên app."""
    user_id, machine_id, error = check_request(data)
    if error:
        return error
    name = clean_name(data.get("name"))
    if name is None:
        return invalid("Tên máy phải có 1-150 ký tự")
    with get_connection() as conn:
        if role_of(conn, machine_id, user_id) != "owner":
            return invalid("Chỉ chủ máy mới đổi tên được")
        save_name(conn, machine_id, name)
    return {"valid": True, "name": name, "message": "Đã đổi tên máy"}


def remove_machine(data):
    """Chủ gỡ máy: xóa máy cùng quyền của mọi nhân viên, tem QR đăng ký lại được.
    Nhân viên gỡ máy: chỉ bỏ quyền quản lý của chính mình."""
    user_id, machine_id, error = check_request(data)
    if error:
        return error
    with get_connection() as conn:
        # Khóa ghi trước khi đọc vai trò, để vai trò không đổi giữa lúc đọc và lúc xóa.
        conn.execute("BEGIN IMMEDIATE")
        role = role_of(conn, machine_id, user_id)
        if role == "owner":
            delete_machine(conn, machine_id)
            return {"valid": True, "deleted": True, "message": "Đã gỡ máy khỏi quán"}
        if role is None:
            return invalid("Bạn không quản lý máy này")
        remove_manager(conn, machine_id, user_id)
    return {"valid": True, "deleted": False, "message": "Đã bỏ quản lý máy"}
