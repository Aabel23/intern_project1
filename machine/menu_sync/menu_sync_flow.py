"""Luồng tab Menu trên máy: xỏ verify → database → đóng gói.

    nhan_menu: menu_version trùng → up_to_date, khác → gói menu mới
    gui_menu:  menu_version khác bản trên máy → conflict + gói mới nhất, không ghi;
               khớp → kiểm từng thay đổi, ghi trong một transaction → gói mới
"""

# Trong module menu_sync: database → kiểm tra → đóng gói
from .menu_sync_database import connect, read_drinks, update_drink
from .menu_sync_verify import check_changes, check_menu_version
from .menu_sync_packet import menu_version_of, reply_with_menu


def nhan_menu(data):
    menu_version = check_menu_version(data)
    with connect() as conn:
        drinks = read_drinks(conn)
    current = menu_version_of(drinks)
    if menu_version == current:
        return {"status": "up_to_date", "menu_version": current}
    return reply_with_menu("ok", drinks)


def gui_menu(data):
    menu_version = check_menu_version(data)
    with connect() as conn:
        drinks = read_drinks(conn)
        if menu_version != menu_version_of(drinks):
            return reply_with_menu("conflict", drinks)
        # Kiểm hết trước rồi mới ghi: một dòng sai thì cả gói không được ghi.
        for drink_id, fields in check_changes(data, {row[0] for row in drinks}):
            update_drink(conn, drink_id, fields)
        drinks = read_drinks(conn)
    return reply_with_menu("ok", drinks)
