"""Cấu hình machine.

Giá trị riêng của từng máy (tên, product key, địa chỉ server) nằm trong
machine.env cạnh file này và không commit. Tạo file cho máy mới bằng:

    python -m machine.config.create_env --name FlexMix-02 --server http://IP:8000

Đặt biến môi trường FLEXMIX_MACHINE_ENV để dùng file ở chỗ khác
(ví dụ /etc/flexmix/machine.env trên Raspberry Pi).
"""

import os
from pathlib import Path

# Đường dẫn API mà machine sử dụng.
GET_COMMAND_PATH = "/machine/hoi-lenh"
POST_RESULT_PATH = "/machine/tra-ket-qua"
HEARTBEAT_PATH = "/machine/heartbeat"
HEARTBEAT_INTERVAL_SECONDS = 5

ENV_PATH = Path(os.environ.get("FLEXMIX_MACHINE_ENV") or Path(__file__).with_name("machine.env"))


def read_env(name):
    """Đọc một khóa trong machine.env khi cần, không nạp bí mật lúc import."""
    if not ENV_PATH.is_file():
        raise ValueError(
            f"Chưa có {ENV_PATH}. Tạo bằng: python -m machine.config.create_env"
            " --name <tên máy> --server <http://IP:port>"
        )
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator and key.strip() == name:
            value = value.strip().strip('"\'')
            if value:
                return value
    raise ValueError(f"Thiếu {name} trong {ENV_PATH}")


def get_machine_name():
    return read_env("MACHINE_NAME")


def get_product_key():
    # Máy xưng danh với server bằng key này; server tự tra ra machine_id đã cấp.
    return read_env("PRODUCT_KEY")


def get_server_url():
    return read_env("SERVER_URL").rstrip("/")
