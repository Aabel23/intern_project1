"""Luồng tab Máy: xỏ kiểm tra (machinelist_verify) với database máy của server.

    list_my_machines: đăng nhập → các máy người này là chủ hoặc nhân viên
    rename_machine:   đăng nhập → mã máy → tên 1-150 ký tự → phải là chủ → đổi tên
    remove_machine:   đăng nhập → mã máy → khóa ghi → chủ thì xóa máy,
                      nhân viên thì chỉ bỏ quyền của mình, người lạ thì từ chối

Dữ liệu tab này là của server (bảng machines), không hỏi xuống máy nên máy
offline vẫn dùng được. Mỗi hàm nhận body JSON đã parse, trả (kết quả, HTTP
status); đọc/ghi HTTP nằm ở machinelist_api.py. Thân kết quả giữ dạng
{"valid", "message", ...} app đang đọc.
"""

# Server chung: database
from server.database.connection import get_connection
from server.database.machine import machine_read, machine_write

# Trong module machinelist_sync
from .machinelist_verify import check_login, check_request, clean_name, invalid, role_of


def list_my_machines(data):
    """Các máy tài khoản đang là chủ (owner) hoặc được giao quản lý (manager)."""
    user_id, error = check_login(data)
    if error:
        return error, 400
    return {"valid": True, "machines": machine_read.list_by_user(user_id)}, 200


def rename_machine(data):
    """Chủ máy đổi tên hiển thị; tên do người dùng nhập trên app."""
    user_id, machine_id, error = check_request(data)
    if error:
        return error, 400
    name = clean_name(data.get("name"))
    if name is None:
        return invalid("Tên máy phải có 1-150 ký tự"), 400
    with get_connection() as conn:
        if role_of(conn, machine_id, user_id) != "owner":
            return invalid("Chỉ chủ máy mới đổi tên được"), 400
        machine_write.rename_machine(conn, machine_id, name)
    return {"valid": True, "name": name, "message": "Đã đổi tên máy"}, 200


def remove_machine(data):
    """Chủ gỡ máy: xóa máy cùng quyền của mọi nhân viên, tem QR đăng ký lại được.
    Nhân viên gỡ máy: chỉ bỏ quyền quản lý của chính mình."""
    user_id, machine_id, error = check_request(data)
    if error:
        return error, 400
    with get_connection() as conn:
        # Khóa ghi trước khi đọc vai trò, để vai trò không đổi giữa lúc đọc và lúc xóa.
        conn.execute("BEGIN IMMEDIATE")
        role = role_of(conn, machine_id, user_id)
        if role == "owner":
            machine_write.delete_machine(conn, machine_id)
            return {"valid": True, "deleted": True, "message": "Đã gỡ máy khỏi quán"}, 200
        if role is None:
            return invalid("Bạn không quản lý máy này"), 400
        machine_write.remove_manager(conn, machine_id, user_id)
    return {"valid": True, "deleted": False, "message": "Đã bỏ quản lý máy"}, 200
