"""Laptop Windows đóng vai máy FlexMix để app Android pair Bluetooth thật.

Chạy từ thư mục gốc androidv0.1:
    python tests/bluetooth_pair/app2machine-pair.py                 # dùng machine/config/machine.env
    python tests/bluetooth_pair/app2machine-pair.py --env may_thu.env

Máy giả dùng lại nguyên handle_connection() của machine/pairing nên trả lời
y hệt Raspberry Pi; sandbox chỉ thêm phần in từng gói tin ra terminal.
Trên app bật "Hiện mọi thiết bị Bluetooth" vì tên laptop không bắt đầu bằng FlexMix-.
"""

import argparse
import os
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

SPP_UUID = "00001101-0000-1000-8000-00805f9b34fb"


def main():
    # Terminal Windows mặc định cp1252, không in được tiếng Việt.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Laptop giả làm máy FlexMix qua Bluetooth.")
    parser.add_argument("--env", help="file machine.env khác (tên, product key, server)")
    parser.add_argument("--once", action="store_true", help="dừng sau một lần pair thành công")
    args = parser.parse_args()
    if args.env:
        # Phải đặt trước khi import config.env vì đường dẫn đọc lúc import.
        os.environ["FLEXMIX_MACHINE_ENV"] = str(Path(args.env).resolve())

    from machine.config.env import get_machine_name, get_product_key
    from machine.pairing.machine_bluetooth_pair import handle_connection
    from tests.bluetooth_pair.win_bluetooth import serve

    try:
        print(f"Máy giả {get_machine_name()}, key {get_product_key()[:6]}…", flush=True)
    except ValueError as error:
        sys.exit(str(error))
    serve(SPP_UUID, "FlexMix Pairing", handle_connection, peer="APP", me="MÁY", once=args.once)


if __name__ == "__main__":
    main()
