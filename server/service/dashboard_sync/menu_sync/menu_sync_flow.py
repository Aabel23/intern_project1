"""Luồng tab Menu: xỏ kiểm tra (menu_sync_verify) với chuyển lệnh xuống máy.

    nhan_menu: quyền → menu_version → máy trả up_to_date hoặc gói menu mới
    gui_menu:  quyền → menu_version + thay_doi → máy ghi rồi trả gói mới (hoặc conflict)

Mỗi hàm nhận body JSON đã parse, trả (kết quả, HTTP status); đọc/ghi HTTP nằm ở
menu_sync_api.py. Gói menu (base64 zlib) đi nguyên từ máy tới app, server không
giải nén, không lưu. Cấu trúc gói: machine/menu_sync/menu_sync_packet.py.

Chạy riêng module (chỉ có route menu + relay để máy nhận lệnh):
    python -m server.service.dashboard_sync.menu_sync.menu_sync_flow --port 8000
"""

# Server chung: chạy riêng module
from server.lib.module_server import run_standalone

# Trong module menu_sync
from .menu_sync_verify import check_access, is_changes, is_menu_version, send_to_machine


def nhan_menu(data):
    # {token, machine_id, menu_version}
    machine_id, error = check_access(data)
    if error:
        return error
    menu_version = data.get("menu_version", 0)
    if not is_menu_version(menu_version):
        return {"loi": "menu_version không hợp lệ"}, 400
    return send_to_machine(machine_id, "nhan_menu", {"menu_version": menu_version})


def gui_menu(data):
    # {token, machine_id, menu_version, thay_doi: [{drink_id, available?, price?}]}.
    # menu_version là bản app đang sửa; máy từ chối (conflict) nếu đã có bản mới hơn.
    machine_id, error = check_access(data)
    if error:
        return error
    menu_version, thay_doi = data.get("menu_version"), data.get("thay_doi")
    if not is_menu_version(menu_version) or not is_changes(thay_doi):
        return {"loi": "Gói thay đổi menu không hợp lệ"}, 400
    return send_to_machine(machine_id, "gui_menu", {"menu_version": menu_version, "thay_doi": thay_doi})


if __name__ == "__main__":
    # Chỉ tab Menu và relay (máy cần heartbeat, hỏi lệnh, trả kết quả).
    run_standalone(
        (f"{__package__}.menu_sync_api", "server.service.machine_relay.relay_api"),
        "Menu sync",
    )
