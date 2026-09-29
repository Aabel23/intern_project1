"""Các hàm ghi bảng machines và machine_managers.

Luôn nhận conn: nơi gọi giữ giao dịch (BEGIN IMMEDIATE) để các bước đi cùng nhau.
"""

from uuid import uuid4


def remove_manager(conn, machine_id, user_id):
    # Chỉ xóa quyền manager, không xóa được chủ máy.
    conn.execute(
        "DELETE FROM machine_managers WHERE machine_id=? AND user_id=? AND role='manager'",
        (machine_id, user_id),
    )


def add_machine(conn, name, key_hash):
    """Thêm máy mới, trả machine_id server cấp."""
    machine_id = "fm_" + uuid4().hex
    conn.execute(
        "INSERT INTO machines (machine_id, name, product_key_hash) VALUES (?, ?, ?)",
        (machine_id, name, key_hash),
    )
    return machine_id


def set_owner(conn, machine_id, user_id):
    conn.execute(
        "INSERT INTO machine_managers (machine_id, user_id, role) VALUES (?, ?, 'owner')"
        " ON CONFLICT (machine_id, user_id) DO UPDATE SET role='owner'",
        (machine_id, user_id),
    )
