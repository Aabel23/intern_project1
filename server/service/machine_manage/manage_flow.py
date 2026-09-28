"""Luồng quản lý máy: xỏ kiểm tra (manage_verify) với ghi database (machine_write).

    rename_machine: đăng nhập → mã máy → tên 1-150 ký tự → phải là chủ → đổi tên
    remove_machine: đăng nhập → mã máy → khóa ghi → chủ thì xóa máy,
                    nhân viên thì chỉ bỏ quyền của mình, người lạ thì từ chối

Mỗi hàm nhận body JSON đã parse, trả (kết quả, HTTP status); đọc/ghi HTTP nằm ở
manage_api.py. Thân kết quả giữ dạng {"valid", "message", ...} app đang đọc.

Chạy riêng module (token lấy từ server đầy đủ, vì dùng chung database):
    python -m server.service.machine_manage.manage_flow --port 8000
"""

# Server chung: database, chạy riêng module
from server.database.connection import get_connection
from server.database.machine import machine_write
from server.lib.module_server import run_standalone

# Trong module machine_manage
from .manage_verify import check_request, clean_name, invalid, role_of


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


if __name__ == "__main__":
    run_standalone((f"{__package__}.manage_api",), "Quản lý máy")
