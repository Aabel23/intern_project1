"""Các hàm ghi bảng machines và machine_managers.

Luôn nhận conn: nơi gọi giữ giao dịch (BEGIN IMMEDIATE) để các bước đi cùng nhau.
"""


def remove_manager(conn, machine_id, user_id):
    # Chỉ xóa quyền manager, không xóa được chủ máy.
    conn.execute(
        "DELETE FROM machine_managers WHERE machine_id=? AND user_id=? AND role='manager'",
        (machine_id, user_id),
    )
