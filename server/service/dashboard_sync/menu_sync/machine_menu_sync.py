"""Luồng tab Menu: quyền → dạng gói → gửi lệnh cho máy → trả nguyên kết quả máy.

    nhan_menu: quyền → menu_version → máy trả up_to_date hoặc gói menu mới
    gui_menu:  quyền → menu_version + thay_doi → máy ghi rồi trả gói mới (hoặc conflict)

Mỗi hàm nhận body JSON đã parse, trả (kết quả, HTTP status); đọc/ghi HTTP nằm ở
machine_menu_request.py. Gói menu (base64 zlib) đi nguyên từ máy tới app, server không
giải nén, không lưu. Cấu trúc gói: machine/menu_sync/machine_menu_pack.py.
"""

# Tài nguyên chung: kiểm quyền và vận chuyển lệnh tới máy
from server.lib.machine_access import check_access
from server.lib.machine_transport import send

# Trong module menu_sync
from .machine_menu_validate import is_changes, is_menu_version

QUYEN_MENU = {"owner", "manager"}


def nhan_menu(data):
    # {token, machine_id, menu_version}
    machine_id, error = check_access(data, QUYEN_MENU)
    if error:
        return error
    menu_version = data.get("menu_version", 0)
    if not is_menu_version(menu_version):
        return {"loi": "menu_version không hợp lệ"}, 400
    return send(machine_id, "nhan_menu", {"menu_version": menu_version})


def gui_menu(data):
    # {token, machine_id, menu_version, thay_doi: [{drink_id, available?, price?}]}.
    # menu_version là bản app đang sửa; máy từ chối (conflict) nếu đã có bản mới hơn.
    machine_id, error = check_access(data, QUYEN_MENU)
    if error:
        return error
    menu_version, thay_doi = data.get("menu_version"), data.get("thay_doi")
    if not is_menu_version(menu_version) or not is_changes(thay_doi):
        return {"loi": "Gói thay đổi menu không hợp lệ"}, 400
    return send(machine_id, "gui_menu", {"menu_version": menu_version, "thay_doi": thay_doi})
