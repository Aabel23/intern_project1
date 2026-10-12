"""Nối Wi-Fi qua NetworkManager (Raspberry Pi OS Bookworm trở lên dùng NM mặc định).

Hồ sơ mới được ghi thẳng thành keyfile 0600 rồi `nmcli connection load`, nên mật khẩu không
bao giờ nằm trên dòng lệnh. Chỉ báo thành công khi `connection up` đạt ACTIVATED có IPv4
(association + DHCP; ipv4.may-fail=no), không dùng việc tới được server làm tín hiệu.
Thất bại thì xóa hồ sơ mới; hồ sơ cũ vẫn còn nên NM tự quay về mạng cũ.
"""

import os
from pathlib import Path
import subprocess
import uuid

CONNECT_TIMEOUT = 45
KEYFILE_DIR = Path("/etc/NetworkManager/system-connections")


def _nmcli(*args, timeout=15):
    return subprocess.run(["nmcli", *args], capture_output=True, text=True, timeout=timeout)


def _escape(value):
    """Giá trị GKeyFile: '\\' là ký tự thoát, khoảng trắng đầu dòng bị cắt nếu không thoát."""
    value = value.replace("\\", "\\\\")
    if value.startswith(" "):
        value = "\\s" + value[1:]
    return value


def keyfile_text(name, ssid, password, interface):
    sections = [("connection", [("id", name), ("uuid", str(uuid.uuid4())), ("type", "wifi"),
                                ("interface-name", interface), ("autoconnect", "true"),
                                ("autoconnect-priority", "10")]),
                ("wifi", [("mode", "infrastructure"), ("ssid", ssid)])]
    if password:
        sections.append(("wifi-security", [("key-mgmt", "wpa-psk"), ("psk", password)]))
    sections += [("ipv4", [("method", "auto"), ("may-fail", "false")]), ("ipv6", [("method", "auto")])]
    lines = []
    for section, items in sections:
        lines.append(f"[{section}]")
        lines += [f"{key}={_escape(value)}" for key, value in items]
        lines.append("")
    return "\n".join(lines)


def configure_wifi(ssid, password, interface="wlan0", runner=_nmcli, keyfile_dir=KEYFILE_DIR):
    if any(c in ssid + password for c in "\r\n"):
        return {"ok": False}
    name = "flexmix-" + uuid.uuid4().hex[:8]
    path = Path(keyfile_dir) / (name + ".nmconnection")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(keyfile_text(name, ssid, password, interface))
    try:
        if runner("connection", "load", str(path)).returncode != 0:
            raise RuntimeError("load")
        up = runner("--wait", str(CONNECT_TIMEOUT), "connection", "up", "id", name, timeout=CONNECT_TIMEOUT + 5)
        if up.returncode == 0:
            return {"ok": True}
    except (RuntimeError, subprocess.TimeoutExpired):
        pass
    runner("connection", "delete", "id", name)
    try:
        path.unlink()
    except OSError:
        pass
    return {"ok": False}
