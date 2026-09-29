"""Thêm người dùng mới vào bảng users."""

import sqlite3

from ..connection import get_connection
from server.lib.security.user_password import hash_password


def add_full_name(full_name):
    """Chuẩn bị họ tên để lưu."""
    full_name = full_name.strip()
    if not full_name:
        raise ValueError("Họ tên không được để trống")
    return full_name


def add_username(username):
    """Chuẩn bị tên đăng nhập để lưu."""
    username = username.strip()
    if not username:
        raise ValueError("Tên đăng nhập không được để trống")
    return username


def add_password(password):
    """Chuẩn bị mật khẩu để lưu (đã băm)."""
    return hash_password(password)


def add_email(email):
    """Chuẩn bị email để lưu."""
    email = email.strip()
    if not email:
        raise ValueError("Email không được để trống")
    return email


def add_role(role):
    """Chuẩn bị chức vụ để lưu."""
    role = role.strip()
    if not role:
        raise ValueError("Chức vụ không được để trống")
    return role


def add_store_id(store_id):
    """Giữ ID cửa hàng; None nghĩa là chưa gán cửa hàng."""
    return store_id


def add_id(cursor):
    """Lấy ID mà SQLite tự tạo sau khi thêm user."""
    return cursor.lastrowid


def add_user(full_name, username, password, email, role="staff", store_id=None):
    """Gọi các hàm con rồi thêm một người dùng vào bảng users."""
    password_hash = add_password(password)
    return add_user_with_hash(full_name, username, password_hash, email, role, store_id)


def add_user_with_hash(full_name, username, password_hash, email, role="staff", store_id=None):
    """Dùng nội bộ khi mật khẩu đã được server băm trước lúc chờ OTP."""
    full_name = add_full_name(full_name)
    username = add_username(username)
    email = add_email(email)
    role = add_role(role)
    store_id = add_store_id(store_id)

    # Các giá trị được ghi chung một lần để không tạo user thiếu cột.
    sql = """INSERT INTO users (full_name, username, password, email, role, store_id)
             VALUES (?, ?, ?, ?, ?, ?)"""
    values = (full_name, username, password_hash, email, role, store_id)

    with get_connection() as conn:
        try:
            cursor = conn.execute(sql, values)
        except sqlite3.IntegrityError as error:
            raise ValueError("Tên đăng nhập hoặc email đã tồn tại") from error

        # Đọc lại dòng vừa tạo; không chọn cột password.
        user_id = add_id(cursor)
        row = conn.execute(
            """SELECT id, full_name, username, email, role, store_id, created_at, updated_at
               FROM users WHERE id = ?""",
            (user_id,),
        ).fetchone()

    return dict(row)
