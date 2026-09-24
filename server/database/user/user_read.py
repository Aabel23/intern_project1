"""Các hàm đọc dữ liệu từ bảng users."""

from ..connection import get_connection

# Chỉ các cột được phép trả về khi xem thông tin người dùng.
# Không đưa mật khẩu vào danh sách này.
PUBLIC_COLUMNS = (
    "id",
    "full_name",
    "username",
    "email",
    "role",
    "store_id",
    "created_at",
    "updated_at",
)


def get_by_id(user_id: int):
    """Tìm một người dùng theo ID."""
    columns = ", ".join(PUBLIC_COLUMNS)
    sql = f"SELECT {columns} FROM users WHERE id = ?"

    # Dấu ? nhận giá trị riêng, tránh ghép ID trực tiếp vào câu SQL.
    with get_connection() as conn:
        row = conn.execute(sql, (user_id,)).fetchone()

    if row is None:
        return None
    return dict(row)


def get_by_username(username: str):
    """Tìm một người dùng theo tên đăng nhập."""
    columns = ", ".join(PUBLIC_COLUMNS)
    sql = f"SELECT {columns} FROM users WHERE username = ?"

    with get_connection() as conn:
        row = conn.execute(sql, (username,)).fetchone()

    if row is None:
        return None
    return dict(row)


def get_by_email(email):
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    return dict(row) if row else None


def get_credentials(username: str):
    """Đọc mật khẩu đã băm để kiểm tra đăng nhập; không trả ra app."""
    sql = "SELECT id, username, password FROM users WHERE username = ?"

    with get_connection() as conn:
        row = conn.execute(sql, (username,)).fetchone()

    if row is None:
        return None
    return dict(row)


def list_users(
    store_id=None,
    role=None,
    limit: int = 100,
    offset: int = 0,
):
    """Liệt kê user, có thể lọc theo cửa hàng và/hoặc chức vụ."""
    columns = ", ".join(PUBLIC_COLUMNS)
    sql = f"SELECT {columns} FROM users WHERE 1 = 1"
    params = []

    # Chỉ thêm điều kiện khi người gọi truyền giá trị cần lọc.
    if store_id is not None:
        sql += " AND store_id = ?"
        params.append(store_id)
    if role is not None:
        sql += " AND role = ?"
        params.append(role)

    # Sắp xếp và giới hạn số dòng trả về.
    sql += " ORDER BY id LIMIT ? OFFSET ?"
    params.append(limit)
    params.append(offset)

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()

    # Chuyển từng dòng SQLite thành dict để phần khác dễ dùng.
    users = []
    for row in rows:
        users.append(dict(row))
    return users
