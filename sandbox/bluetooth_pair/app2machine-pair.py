"""Laptop Windows đóng vai máy FlexMix để app Android pair Bluetooth thật.

Chạy từ thư mục gốc androidv0.1:
    python sandbox/bluetooth_pair/app2machine-pair.py

Máy giả dùng lại nguyên handle_connection() của machine/pairing nên trả lời
y hệt Raspberry Pi; sandbox chỉ thêm phần in từng gói tin ra terminal.
Trên app bật "Hiện mọi thiết bị Bluetooth" vì tên laptop không bắt đầu bằng FlexMix-.
"""

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from machine.pairing.bluetooth_pairing import handle_connection
from sandbox.bluetooth_pair.win_bluetooth import serve

SPP_UUID = "00001101-0000-1000-8000-00805f9b34fb"


def main():
    # Terminal Windows mặc định cp1252, không in được tiếng Việt.
    sys.stdout.reconfigure(encoding="utf-8")
    serve(SPP_UUID, "FlexMix Pairing", handle_connection, peer="APP", me="MÁY")


if __name__ == "__main__":
    main()
