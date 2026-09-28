"""Đóng gói menu để gửi app.

Cấu trúc gói (trước khi nén):
{
    "type": "menu_sync",
    "v": 1,                          # phiên bản cấu trúc gói
    "menu_version": 123456789,       # CRC32 của dữ liệu món, đổi món thì đổi số
    "generated_at": "2026-09-28T17:30:00",
    "fields": ["drink_id", "drink_name", ...],
    "drinks": [[1001, "Peach Tea", ...], ...]   # mỗi món là 1 mảng theo thứ tự fields
}

Gói gửi đi = base64(zlib(JSON gọn, UTF-8)) để đi được trong kết quả JSON của relay.
"""

# Thư viện chuẩn
import base64
import json
import zlib
from datetime import datetime

# Trong module menu_sync
from .machine_menu_store import FIELDS

PACKET_TYPE = "menu_sync"
PACKET_VERSION = 1


def menu_version_of(drinks):
    return zlib.crc32(_to_json(drinks))


def build_packet(drinks):
    return {
        "type": PACKET_TYPE,
        "v": PACKET_VERSION,
        "menu_version": menu_version_of(drinks),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "fields": list(FIELDS),
        "drinks": drinks,
    }


def encode_packet(packet):
    return base64.b64encode(zlib.compress(_to_json(packet), level=9)).decode("ascii")


def reply_with_menu(status, drinks):
    """Kết quả trả app kèm nguyên gói: status "ok" hoặc "conflict"."""
    packet = build_packet(drinks)
    return {"status": status, "menu_version": packet["menu_version"], "packet": encode_packet(packet)}


def _to_json(data):
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
