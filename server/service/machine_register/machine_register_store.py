"""Ghi máy mới và chủ sở hữu trong transaction của luồng đăng ký."""

from uuid import uuid4


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

