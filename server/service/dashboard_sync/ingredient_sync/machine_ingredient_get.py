"""Lấy kho: JSON app → (kết quả máy hoặc lỗi, HTTP status)."""

from server.lib.machine.machine_access import check_access
from server.lib.machine.machine_transport import send

QUYEN_KHO = {"owner", "manager"}


def is_version(value):
    # CRC32: số nguyên 0..2^32-1; app chưa có danh sách kho gửi 0.
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value < 2**32


def nhan_kho(data):
    # Bước 1: kiểm phiên và quyền máy; lỗi thì dừng.
    machine_id, error = check_access(data, QUYEN_KHO)
    if error:
        return error

    # Bước 2: kiểm phiên bản kho app đang giữ.
    version = data.get("version", 0)
    if not is_version(version):
        return {"loi": "version không hợp lệ"}, 400

    # Bước 3: giao lệnh và chờ máy; trả nguyên kết quả hoặc lỗi transport.
    return send(machine_id, "nhan_kho", {"version": version})
