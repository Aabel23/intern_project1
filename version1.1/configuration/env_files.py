"""Nạp biến môi trường từ file, cho các lệnh chạy TAY.

VẤN ĐỀ NÓ GIẢI QUYẾT
    systemd truyền /etc/flexmix/qrproto.env vào tiến trình qua
    EnvironmentFile=, nên service luôn có đủ biến. Nhưng mọi lệnh chạy
    tay thì KHÔNG đi qua systemd:

        python3 -m database.main
        python3 -m pump_control.calib_pump
        python3 -m admin_gui.auth --list

    Trước đây chúng chỉ đọc được <dự án>/.env, nên máy nào gom hết cấu
    hình vào /etc là mất sạch công cụ dòng lệnh -- triệu chứng khó hiểu
    vì màn hình bán hàng vẫn chạy bình thường. Cách chữa từng được ghi
    trong tài liệu là gõ `set -a; . /etc/flexmix/qrproto.env; set +a`
    trước mỗi lệnh, một nghi thức ai cũng sẽ quên.

    File này bỏ nghi thức đó: cùng một file cấu hình phục vụ cả systemd
    lẫn người.

THỨ TỰ ƯU TIÊN
    1. Biến đã có sẵn trong môi trường  -- systemd, hoặc `export` tay
    2. <dự án>/.env                     -- máy phát triển
    3. /etc/flexmix/qrproto.env         -- máy chạy thật

    Chỉ điền tên CHƯA có, nên thứ tự trên là thứ tự thắng. Máy phát
    triển đặt .env thì .env thắng, vì người đặt nó ở đó là cố ý.

KHÔNG BAO GIỜ NÉM LỖI
    Thiếu file, không đủ quyền đọc, file hỏng cú pháp -- đều bỏ qua im
    lặng. Nơi cần biến sẽ tự báo lỗi với câu rõ ràng của nó
    (database/config.py nói thiếu BEVERAGE_DB_PASSWORD; qrproto/keys.py
    nói thiếu QRPROTO_KEY). Một lỗi "không đọc được file" ở đây chỉ che
    mất câu nói đúng vấn đề.
"""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent

# Máy phát triển. Trong .gitignore.
PROJECT_ENV_FILE = PROJECT_DIR / ".env"

# Máy chạy thật. deploy/install.sh tạo file này với đủ 7 biến, và
# flexmix-backend.service đọc nó qua EnvironmentFile=.
SYSTEM_ENV_FILE = Path("/etc/flexmix/qrproto.env")

_loaded = False


def _fill_from(path: Path) -> None:
    """Đọc KEY=value, chỉ điền tên chưa có trong môi trường."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, ValueError):
        # Không có file, hoặc không đủ quyền -- xem phần cuối docstring.
        return

    for line in text.splitlines():
        line = line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        name, _, value = line.partition("=")
        name = name.strip()
        value = value.strip().strip('"').strip("'")

        if name and name not in os.environ:
            os.environ[name] = value


def load_env_files() -> None:
    """Nạp cả hai file, theo thứ tự ưu tiên. An toàn khi gọi nhiều lần."""
    global _loaded

    if _loaded:
        return

    _fill_from(PROJECT_ENV_FILE)
    _fill_from(SYSTEM_ENV_FILE)
    _loaded = True


def sources() -> list[str]:
    """Những file thực sự đọc được — để lệnh chẩn đoán in ra."""
    return [str(p) for p in (PROJECT_ENV_FILE, SYSTEM_ENV_FILE)
            if os.access(p, os.R_OK)]
