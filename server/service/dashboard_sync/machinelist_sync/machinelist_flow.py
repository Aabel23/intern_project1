"""Luồng tab Máy: xỏ kiểm tra (machinelist_verify) với database máy của server.

    list_my_machines: đăng nhập → các máy người này là chủ hoặc nhân viên
    machine_status:   máy có heartbeat trong 15 giây gần nhất không (Online/Offline)
    rename_machine:   đăng nhập → mã máy → tên 1-150 ký tự → phải là chủ → đổi tên
    remove_machine:   đăng nhập → mã máy → khóa ghi → chủ thì xóa máy,
                      nhân viên thì chỉ bỏ quyền của mình, người lạ thì từ chối

Dữ liệu tab này là của server (bảng machines, giờ heartbeat trong RAM), không
hỏi xuống máy nên máy offline vẫn dùng được. Hàm route nhận body JSON đã parse,
trả thân {"valid", "message", ...}; api gắn status theo valid (200/400).
"""

# Server chung: database, dạng lỗi, phiên đăng nhập
from server.database.connection import get_connection
from server.database.machine import machine_read, machine_write
from server.lib.http_json import invalid
from server.lib.session import check_login

# Module khác: giờ heartbeat của máy
from server.service.machine_link.link_queue import is_online, last_seen_of

# Trong module machinelist_sync
from .machinelist_verify import check_request, clean_name, role_of


def list_my_machines(data):
    """Các máy tài khoản đang là chủ (owner) hoặc được giao quản lý (manager)."""
    user_id, error = check_login(data)
    if error:
        return error
    return {"valid": True, "machines": machine_read.list_by_user(user_id)}


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
        machine_write.rename_machine(conn, machine_id, name)
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
            machine_write.delete_machine(conn, machine_id)
            return {"valid": True, "deleted": True, "message": "Đã gỡ máy khỏi quán"}
        if role is None:
            return invalid("Bạn không quản lý máy này")
        machine_write.remove_manager(conn, machine_id, user_id)
    return {"valid": True, "deleted": False, "message": "Đã bỏ quản lý máy"}
