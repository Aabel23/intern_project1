"""Which addresses this machine can actually be reached on.

WHY THIS EXISTS
    Two copies of this lived in store_gui/serve.py and admin_gui/serve.py,
    and they had already drifted apart. Only the admin copy grew the third
    branch below -- asking the kernel directly -- so the store server could
    not see a Tailscale address at all:

        store_gui.local_addresses()   -> ['192.168.1.167']
        admin_gui.local_addresses()   -> ['192.168.1.167', '100.71.158.28']

    That difference is not cosmetic. store_gui/serve.py now decides which
    interfaces to BIND from these answers, so a copy that cannot see the
    tailnet is a copy that silently drops remote administration.

    Same failure shape as the pump wiring table -- see
    configuration/machine.py -- so it gets the same treatment: one home,
    and both callers import it.

WHY THREE WAYS OF ASKING
    None of them is sufficient alone.

        getaddrinfo(hostname)   often returns only 127.0.1.1, as it does on
                                this Pi.
        a UDP probe to 8.8.8.8  returns the address that reaches the
                                internet -- the Wi-Fi one. A Tailscale
                                interface never shows up this way, because
                                nothing routes to the public internet
                                through it.
        ip -4 -o addr show      asks the kernel for every interface, which
                                is the only one that finds tailscale0.

    They are tried in that order and merged, so a machine where `ip` is
    missing still gets an answer.

WHY IT IMPORTS NOTHING OF OURS
    No gpiozero, no database, no configuration. It answers a question about
    the operating system, and it is read while deciding how to open a
    socket -- before anything else in the process exists.
"""

from __future__ import annotations

import socket
import subprocess


# Tailscale hands out addresses from the CGNAT range 100.64.0.0/10. The
# prefix is matched as text rather than parsed: it is only ever used to
# tell "my own devices" from "the shop's Wi-Fi", and every tailnet address
# starts with 100.
TAILSCALE_PREFIX = "100."

IP_COMMAND_TIMEOUT_SECONDS = 3


def _from_hostname() -> list[str]:
    """Whatever the hostname resolves to. Often just 127.0.1.1."""
    found: list[str] = []

    try:
        for info in socket.getaddrinfo(socket.gethostname(), None,
                                       socket.AF_INET):
            address = info[4][0]

            if address not in found:
                found.append(address)
    except OSError:
        pass

    return found


def _from_route_probe() -> str | None:
    """The address that would be used to reach the internet.

    No packet is sent -- connect() on a UDP socket only fixes the route.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("8.8.8.8", 80))
            return probe.getsockname()[0]
    except OSError:
        return None


def _from_ip_command() -> list[str]:
    """Every IPv4 the kernel knows about, including tailscale0."""
    found: list[str] = []

    try:
        listing = subprocess.run(
            ["ip", "-4", "-o", "addr", "show"],
            capture_output=True, text=True,
            timeout=IP_COMMAND_TIMEOUT_SECONDS, check=False,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return found

    for line in listing.splitlines():
        parts = line.split()

        if "inet" in parts:
            address = parts[parts.index("inet") + 1].split("/")[0]

            if address not in found:
                found.append(address)

    return found


def all_addresses() -> list[str]:
    """Every IPv4 this machine holds, loopback included, no duplicates."""
    found: list[str] = []

    probe = _from_route_probe()

    if probe is not None:
        found.append(probe)

    for address in _from_hostname() + _from_ip_command():
        if address not in found:
            found.append(address)

    return found


def local_addresses() -> list[str]:
    """The addresses worth printing in a startup banner.

    Loopback is dropped: it is already shown as "localhost" and repeating
    it as a number tells nobody anything new.
    """
    return [a for a in all_addresses() if not a.startswith("127.")]


def tailscale_address() -> str | None:
    """This machine's Tailscale address, or None if it is not on a tailnet.

    None is a perfectly ordinary answer -- a machine with no Tailscale
    installed, or one where tailscaled has not finished starting yet.
    Callers decide what to do about it; this does not complain.
    """
    for address in all_addresses():
        if address.startswith(TAILSCALE_PREFIX):
            return address

    return None


# Địa chỉ loopback. Kiosk, màn pha chế và màn test đều tới server qua nó
# (deploy/kiosk mở http://localhost:8080/...), nên đây là thứ làm máy chạy
# được kể cả khi không có mạng nào.
LOOPBACK_HOST = "127.0.0.1"


def bind_hosts(explicit: str | None = None,
               loopback_only: bool = False) -> list[str]:
    """Các địa chỉ nên nghe. Loopback luôn; tailnet nếu có; LAN thì không.

    VÌ SAO KHÔNG BAO GIỜ CÓ LAN
        Những server dùng hàm này đều phát file từ đĩa và gắn API quản trị
        hoặc API điều khiển phần cứng. "Vào được" nghĩa là "thử đọc được
        cấu hình của máy", hoặc "chạy được bơm". Wi-Fi mà khách đang ngồi
        là đúng cái mạng điều đó không được phép đúng.

    VÌ SAO SUY RA CHỨ KHÔNG CẤU HÌNH
        Một setting trong /etc là setting máy sau không có. Danh sách được
        suy ra từ chính máy mỗi lần khởi động, nên máy mới clone về là đúng
        ngay: không Tailscale thì chỉ loopback, có tailnet thì tự thêm.

    VÌ SAO Ở ĐÂY CHỨ KHÔNG Ở store_gui/serve.py
        Ba server dùng nó -- store_gui, admin_gui, test_gui. Bản đầu chỉ
        sửa store_gui, nên hai cái kia vẫn bind 0.0.0.0 khi chạy độc lập:
        admin_gui phơi toàn bộ API quản trị ra LAN, test_gui phơi
        /api/prime và /api/pump/hold, những endpoint KHÔNG cần đăng nhập.
        main.py không mở hai cổng đó nên máy bán hàng an toàn, nhưng tài
        liệu bảo người phát triển chạy chúng bằng tay.

    `explicit` đè lên tất cả -- kể cả "0.0.0.0", lối thoát cho máy phát
    triển thật sự muốn được gọi qua LAN. Máy bán hàng không nên truyền.
    """
    if explicit:
        return [explicit]

    hosts = [LOOPBACK_HOST]

    if loopback_only:
        return hosts

    tailnet = tailscale_address()

    if tailnet is not None:
        hosts.append(tailnet)

    return hosts
