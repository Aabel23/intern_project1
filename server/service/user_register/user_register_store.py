"""Ghi tài khoản vào database, sau khi user_register_process đã kiểm tra đủ hai cờ."""

# Server chung: database tài khoản
from server.database.user.user_add import add_user_with_hash


def register_user(data):
    """Chỉ nhận dữ liệu nội bộ đã xác minh, không nhận trực tiếp JSON từ app."""
    return add_user_with_hash(
        data["full_name"], data["username"], data["password_hash"], data["email"]
    )
