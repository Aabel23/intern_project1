"""Biến môi trường của machine.

Giá trị riêng của từng máy (tên, địa chỉ server) nằm trong machine.env cạnh file này
và không commit. Danh tính (khóa ký, mã niêm phong S) không nằm ở đây mà nằm trong
thư mục trạng thái do `python -m machine.config.provision` tạo ở xưởng.

    MACHINE_NAME=FlexMix-02
    SERVER_URL=http://192.168.1.10:8080  # LAN; khi mở Internet dùng https://...
    SERVER_TRUST_FILE=/etc/flexmix/server-trust.json   # tùy chọn; mặc định config/server-trust.json
    STATE_DIR=/var/lib/flexmix                         # tùy chọn

Đặt biến môi trường FLEXMIX_MACHINE_ENV để dùng file ở chỗ khác
(ví dụ /etc/flexmix/machine.env trên Raspberry Pi).
"""

import os
import ipaddress
from pathlib import Path
from urllib.parse import urlsplit

ENV_PATH = Path(os.environ.get("FLEXMIX_MACHINE_ENV") or Path(__file__).with_name("machine.env"))
SOFTWARE_VERSION = "1.1"


def read_env(name, default=None):
    """Đọc một khóa trong machine.env khi cần, không nạp bí mật lúc import."""
    if ENV_PATH.is_file():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition("=")
            if separator and key.strip() == name:
                value = value.split("#", 1)[0].strip().strip('"\'')
                if value:
                    return value
    if default is not None:
        return default
    raise ValueError(f"Thiếu {name} trong {ENV_PATH}")


def get_machine_name():
    return read_env("MACHINE_NAME")


def get_server_url():
    url = read_env("SERVER_URL").rstrip("/")
    if url.startswith("https://"):
        return url
    parsed = urlsplit(url)
    if (not parsed.hostname or parsed.username or parsed.password or parsed.query
            or parsed.fragment or parsed.path):
        raise ValueError("SERVER_URL không hợp lệ")
    if parsed.scheme != "http":
        raise ValueError("SERVER_URL phải là HTTPS hoặc HTTP nội bộ")
    try:
        address = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        raise ValueError("HTTP chỉ dùng địa chỉ IP nội bộ") from None
    if address.version != 4 or not (address.is_loopback or any(address in subnet for subnet in (
            ipaddress.ip_network('10.0.0.0/8'), ipaddress.ip_network('172.16.0.0/12'),
            ipaddress.ip_network('192.168.0.0/16')))):
        raise ValueError("HTTP chỉ dùng địa chỉ IP nội bộ")
    return url


def get_server_trust_path():
    # Mặc định là file provision_keys.py ghi cạnh env.py.
    return Path(read_env("SERVER_TRUST_FILE", str(Path(__file__).with_name("server-trust.json"))))


def get_state_dir():
    return Path(os.environ.get("FLEXMIX_STATE_DIR") or read_env("STATE_DIR", "/var/lib/flexmix"))
