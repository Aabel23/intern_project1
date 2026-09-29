"""Chủ máy đổi tên: JSON app → {valid, name, message} hoặc lỗi."""

from server.database.connection import get_connection
from server.database.machine.machine_read import is_owner
from server.lib.http.http_json import invalid
from server.lib.security.user_session import check_login
from server.lib.validation.identifier_validate import is_machine_id

NAME_MAX_LENGTH = 150


def clean_name(name):
    """Bỏ khoảng trắng hai đầu; None nếu tên rỗng hoặc quá 150 ký tự."""
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > NAME_MAX_LENGTH:
        return None
    return name.strip()


def rename_machine(data):
    # Bước 1: kiểm phiên rồi kiểm mã máy.
    user_id, error = check_login(data)
    if error:
        return error
    machine_id = data.get("machine_id")
    if not is_machine_id(machine_id):
        return invalid("Thiếu mã máy hợp lệ")

    # Bước 2: làm sạch và kiểm tên trước khi kiểm quyền chủ.
    name = clean_name(data.get("name"))
    if name is None:
        return invalid("Tên máy phải có 1-150 ký tự")

    # Bước 3: kiểm quyền và ghi tên qua cùng kết nối database.
    with get_connection() as conn:
        if not is_owner(machine_id, user_id, conn):
            return invalid("Chỉ chủ máy mới đổi tên được")
        conn.execute("UPDATE machines SET name=? WHERE machine_id=?", (name, machine_id))
    return {"valid": True, "name": name, "message": "Đã đổi tên máy"}
