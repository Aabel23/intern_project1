"""Laptop đóng vai app nhân viên để thử luồng share máy khi chỉ có một điện thoại.

Điện thoại (chủ máy) bấm Chia sẻ rồi gửi mã qua Bluetooth (hoặc hiện QR), sandbox
nhận mã, đăng nhập bằng tài khoản thứ hai rồi gọi đúng các API app nhân viên gọi,
in mọi gói tin Bluetooth lẫn HTTP ra terminal.

Chạy từ thư mục gốc androidv0.1 (server đang chạy):
    python sandbox/bluetooth_pair/app2app_pair.py            # nhận mã qua Bluetooth
    python sandbox/bluetooth_pair/app2app_pair.py --adb      # chụp QR trên điện thoại qua adb
    python sandbox/bluetooth_pair/app2app_pair.py --camera   # quét bằng webcam laptop
    python sandbox/bluetooth_pair/app2app_pair.py --image anh.png
    python sandbox/bluetooth_pair/app2app_pair.py --text '{"type":"share","code":"..."}'

Cần: pip install opencv-python-headless khi đọc QR, adb khi dùng --adb.
"""

import argparse
import getpass
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from machine.pairing.bluetooth_pairing import pack_message, receive_message
from sandbox.bluetooth_pair.win_bluetooth import serve
from server.config.config import (
    INVITE_CODE_MAX_LENGTH,
    INVITE_CODE_MIN_LENGTH,
    SERVER_PORT,
)
from server.config.routing import (
    APP_ACCEPT_SHARE,
    APP_LOGIN,
    APP_MY_MACHINES,
    APP_VERIFY_LOGIN,
)

# Trùng SHARE_UUID trong BluetoothPairing.kt của app.
SHARE_UUID = "e53b1694-9a6d-41e7-8b4a-00e228b8164e"

# Không in bí mật ra terminal, chỉ in vài ký tự đầu để đối chiếu.
SECRET_FIELDS = {"password", "token"}


def mask(data):
    if not isinstance(data, dict):
        return data
    return {
        key: (f"{value[:6]}…({len(value)} ký tự)" if key in SECRET_FIELDS and isinstance(value, str) else value)
        for key, value in data.items()
    }


def log(direction, path, data):
    stamp = time.strftime("%H:%M:%S")
    print(f"[{stamp}] {direction} {path}", flush=True)
    print(json.dumps(mask(data), ensure_ascii=False, indent=2), flush=True)


def post(server, path, body):
    """POST JSON giống MachineApi của app, in cả request lẫn response."""
    log("APP2 -> SERVER", path, body)
    request = Request(
        server + path,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
    except URLError as error:
        sys.exit(f"Không gọi được server {server}: {error}")
    log("SERVER -> APP2", path, result)
    return result


def login(server, username, password):
    # Cùng hai bước với auth_page: gửi tài khoản rồi hỏi kết quả xác minh.
    request_id = uuid.uuid4().hex
    sent = post(server, APP_LOGIN, {
        "request_id": request_id, "username": username, "password": password,
    })
    if sent.get("valid") is not True:
        sys.exit("Đăng nhập thất bại.")
    for _ in range(10):
        result = post(server, APP_VERIFY_LOGIN, {
            "request_id": request_id, "login_id": sent["login_id"],
        })
        if result.get("retry_after"):
            time.sleep(result["retry_after"])
            continue
        if result.get("valid") is True and isinstance(result.get("token"), str):
            return result["token"]
        break
    sys.exit("Đăng nhập thất bại.")


def decode_image(image):
    import cv2
    text, _, _ = cv2.QRCodeDetector().detectAndDecode(image)
    return text or None


def qr_from_adb():
    """Chụp màn hình điện thoại đang hiện QR chia sẻ qua cáp USB."""
    import cv2
    import numpy
    try:
        png = subprocess.run(["adb", "exec-out", "screencap", "-p"],
                             capture_output=True, check=True, timeout=15).stdout
    except (OSError, subprocess.SubprocessError) as error:
        sys.exit(f"Không chụp được màn hình điện thoại qua adb: {error}")
    image = cv2.imdecode(numpy.frombuffer(png, numpy.uint8), cv2.IMREAD_COLOR)
    if image is None:
        sys.exit("adb không trả ảnh màn hình; kiểm tra điện thoại đã cắm và cho phép gỡ lỗi USB.")
    return decode_image(image)


def qr_from_camera():
    import cv2
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        sys.exit("Không mở được webcam.")
    print("Đưa màn hình điện thoại vào webcam… (tối đa 60 giây)", flush=True)
    try:
        deadline = time.time() + 60
        while time.time() < deadline:
            ok, frame = camera.read()
            if ok and (text := decode_image(frame)):
                return text
    finally:
        camera.release()
    return None


def read_qr(args):
    if args.text:
        return args.text
    if args.image:
        import cv2
        image = cv2.imread(args.image)
        if image is None:
            sys.exit(f"Không đọc được ảnh {args.image}")
        return decode_image(image)
    return qr_from_camera() if args.camera else qr_from_adb()


def receive_share(connection):
    """Giống listenShare trong BluetoothPairing.kt: identify -> ready, nhận share, ACK."""
    with connection:
        connection.settimeout(30)
        with connection.makefile("rb") as reader:
            if receive_message(reader).get("type") != "identify":
                raise ValueError("Thiết bị gửi không phải app FlexMix")
            connection.sendall(pack_message({"type": "ready", "ok": True}))
            data = receive_message(reader)
            ok = data.get("type") == "share"
            connection.sendall(pack_message({"type": "ack", "ok": ok}))
            if not ok:
                raise ValueError("Gói nhận được không phải mã chia sẻ")
            # Chờ bên gửi đọc xong ACK và đóng trước, tránh mất ACK khi đóng sớm.
            try:
                reader.read(1)
            except OSError:
                pass
            return data


def parse_share(data):
    """Cùng quy tắc với parseMachineQr trong app cho gói loại share."""
    code = data.get("code") if isinstance(data, dict) else None
    if not isinstance(code, str) or data.get("type") != "share" \
            or not INVITE_CODE_MIN_LENGTH <= len(code) <= INVITE_CODE_MAX_LENGTH:
        sys.exit("Đây không phải mã chia sẻ máy hợp lệ.")
    return code


def share_from_qr(args):
    input("\nTrên điện thoại: tab Máy → menu máy → Chia sẻ để hiện QR, rồi bấm Enter… ")
    raw = read_qr(args)
    if not raw:
        sys.exit("Không thấy QR. Để QR hiện rõ trên màn hình rồi chạy lại.")
    print(f"\nNội dung QR: {raw}", flush=True)
    try:
        return json.loads(raw)
    except ValueError:
        sys.exit("QR không phải JSON; có thể đang quét nhầm QR khác.")


def share_from_bluetooth():
    print("\nTrên điện thoại: tab Máy → menu máy → Chia sẻ → Gửi qua Bluetooth,",
          "chọn laptop này trong danh sách.", flush=True)
    data = serve(SHARE_UUID, "FlexMix Share", receive_share,
                 peer="CHỦ MÁY", me="APP2", once=True)
    if data is None:
        sys.exit("Đã dừng trước khi nhận được mã.")
    return data


def main():
    # Terminal Windows mặc định cp1252, không in được tiếng Việt.
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Giả lập app nhân viên nhận chia sẻ máy.")
    parser.add_argument("--server", default=f"http://127.0.0.1:{SERVER_PORT}")
    parser.add_argument("--username", help="tài khoản thứ hai, khác tài khoản chủ máy")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--adb", action="store_true", help="chụp QR trên điện thoại qua adb")
    source.add_argument("--camera", action="store_true", help="quét QR bằng webcam")
    source.add_argument("--image", help="đọc QR từ file ảnh")
    source.add_argument("--text", help="dán thẳng nội dung QR")
    args = parser.parse_args()

    username = args.username or input("Tài khoản app thứ hai: ").strip()
    password = getpass.getpass("Mật khẩu: ")
    token = login(args.server, username, password)

    use_qr = args.adb or args.camera or args.image or args.text
    code = parse_share(share_from_qr(args) if use_qr else share_from_bluetooth())

    result = post(args.server, APP_ACCEPT_SHARE, {"code": code, "token": token})
    if result.get("valid") is not True:
        sys.exit("Nhận chia sẻ thất bại.")
    # App nhân viên tải lại danh sách máy sau khi nhận; in ra để thấy vai trò mới.
    post(args.server, APP_MY_MACHINES, {"token": token})
    print("\n=== Nhận chia sẻ thành công ===", flush=True)


if __name__ == "__main__":
    main()
