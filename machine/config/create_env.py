"""Tạo machine.env cho một máy mới với product key ngẫu nhiên riêng của máy đó.

    python -m machine.config.create_env --name FlexMix-02 --server http://IP:8000

Không bao giờ ghi đè file đã có: key đã in lên tem QR và đăng ký với server,
đổi key là máy mất liên lạc. In tem bằng: python machine_qr.py --from-env
"""

import argparse
import secrets
import sys

from machine.config.machine_config import ENV_PATH


def build_env(name, server):
    name, server = name.strip(), server.strip().rstrip("/")
    if not name.startswith("FlexMix-") or len(name) > 150:
        raise ValueError("Tên máy phải bắt đầu bằng FlexMix- (app quét Bluetooth theo tên này).")
    if not server.startswith(("http://", "https://")):
        raise ValueError("Địa chỉ server phải có dạng http://IP:port.")
    key = "fm_" + secrets.token_hex(16)
    return f"MACHINE_NAME={name}\nPRODUCT_KEY={key}\nSERVER_URL={server}\n"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Tạo machine.env cho máy mới.")
    parser.add_argument("--name", required=True, help="tên Bluetooth, vd. FlexMix-02")
    parser.add_argument("--server", required=True, help="địa chỉ server, vd. http://192.168.1.10:8000")
    args = parser.parse_args()
    if ENV_PATH.exists():
        sys.exit(f"{ENV_PATH} đã có, không ghi đè product key của máy.")
    try:
        content = build_env(args.name, args.server)
    except ValueError as error:
        sys.exit(str(error))
    ENV_PATH.write_text(content, encoding="utf-8")
    print(f"Đã tạo {ENV_PATH}. In tem QR: python machine_qr.py --from-env")


if __name__ == "__main__":
    main()
