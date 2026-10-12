"""Trạm xưởng: tạo danh tính máy rồi in thông tin để Operator đăng ký và in QR niêm phong.

    python -m machine.config.provision --name FlexMix-02

Kết quả JSON: serial, public_key, key_id và lệnh Operator chạy trên server. Trường `qr`
chứa mã niêm phong S, chỉ đưa thẳng sang máy in tem, không lưu hay gửi đi nơi khác.
"""

import argparse
import json
import shlex

from machine.config.env import get_state_dir
from machine.config.identity import b64u, load_seal_code, provision, qr_payload


def main(argv=None):
    parser = argparse.ArgumentParser(description="Tạo danh tính máy ở xưởng (chạy lại an toàn).")
    parser.add_argument("--name", required=True)
    parser.add_argument("--state-dir")
    args = parser.parse_args(argv)
    state_dir = args.state_dir or get_state_dir()
    identity = provision(state_dir)
    public_key = b64u(identity.public_key)
    command = ["python3", "-m", "server.src.factory_register", "--serial", identity.serial,
               "--name", args.name, "--public-key", public_key]
    print(json.dumps({
        "serial": identity.serial,
        "public_key": public_key,
        "key_id": identity.key_id,
        "operator_command": " ".join(shlex.quote(part) for part in command),
        "qr": qr_payload(identity, load_seal_code(state_dir)),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
