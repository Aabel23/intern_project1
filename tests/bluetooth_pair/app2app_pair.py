"""Laptop đóng vai app thứ hai để thử luồng share máy khi chỉ có một điện thoại.

Nhân viên (mặc định): điện thoại là chủ máy, bấm Chia sẻ rồi gửi mã qua Bluetooth
(hoặc hiện QR); laptop nhận mã, đăng nhập tài khoản thứ hai, gọi /app/machine/share/accept.
Chủ máy (--send): điện thoại là nhân viên, mở "Nhận chia sẻ qua Bluetooth";
laptop đăng nhập tài khoản chủ, tạo mã mời rồi gửi qua Bluetooth tới điện thoại.
Mọi gói tin Bluetooth lẫn HTTP đều in ra terminal.

Chạy từ thư mục gốc androidv0.1 (server đang chạy):
    python tests/bluetooth_pair/app2app_pair.py            # nhận mã qua Bluetooth
    python tests/bluetooth_pair/app2app_pair.py --adb      # chụp QR trên điện thoại qua adb
    python tests/bluetooth_pair/app2app_pair.py --camera   # quét bằng webcam laptop
    python tests/bluetooth_pair/app2app_pair.py --image anh.png
    python tests/bluetooth_pair/app2app_pair.py --text '{"type":"share","code":"..."}'
    python tests/bluetooth_pair/app2app_pair.py --send --phone AA:BB:CC:DD:EE:FF --machine-id fm_...

Mật khẩu hỏi trên terminal; chạy tự động thì đặt biến môi trường SANDBOX_PASSWORD.
Cần: pip install opencv-python-headless khi đọc QR, adb khi dùng --adb.
"""

import argparse
import getpass
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from machine.pairing.machine_bluetooth_pair import pack_message, receive_message
from tests.bluetooth_pair.win_bluetooth import LoggedConnection, connect_service, serve
from server.config.config import SERVER_PORT
from server.config.routing import APP_ACCEPT_SHARE, APP_CREATE_SHARE, APP_LOGIN, APP_MY_MACHINES, APP_VERIFY_LOGIN

INVITE_CODE_MIN_LENGTH = 20
INVITE_CODE_MAX_LENGTH = 100

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
        with urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        # Server trả lỗi nghiệp vụ (400/401/403) kèm JSON, vẫn in như response thường.
        with error:
            result = json.loads(error.read().decode("utf-8"))
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
    if not (args.text or args.image):
        try:
            input("\nTrên điện thoại: tab Máy → menu máy → Chia sẻ để hiện QR, rồi bấm Enter… ")
        except EOFError:
            # Chạy tự động không có bàn phím: QR đã hiện sẵn trên điện thoại.
            print()
    raw = read_qr(args)
    if not raw:
        sys.exit("Không thấy QR. Để QR hiện rõ trên màn hình rồi chạy lại.")
    print(f"\nNội dung QR: {raw}", flush=True)
    try:
        return json.loads(raw)
    except ValueError:
        sys.exit("QR không phải JSON; có thể đang quét nhầm QR khác.")


def share_from_bluetooth(timeout=None):
    print("\nTrên điện thoại: tab Máy → menu máy → Chia sẻ → Gửi qua Bluetooth,",
          "chọn laptop này trong danh sách.", flush=True)
    data = serve(SHARE_UUID, "FlexMix Share", receive_share,
                 peer="CHỦ MÁY", me="APP2", once=True, timeout=timeout)
    if data is None:
        sys.exit("Đã dừng trước khi nhận được mã.")
    return data


def share_to_phone(server, token, machine_id, phone):
    """Giống sendShare trong BluetoothPairing.kt: identify -> ready, gửi share -> nhận ACK."""
    invite = post(server, APP_CREATE_SHARE, {"machine_id": machine_id, "token": token})
    if invite.get("valid") is not True:
        sys.exit("Không tạo được mã mời.")
    try:
        sock = connect_service(phone, SHARE_UUID)
    except OSError as error:
        sys.exit(f"{error}. Điện thoại cần mở màn hình Nhận chia sẻ qua Bluetooth trước.")
    print(f"\n=== Đã kết nối điện thoại {phone} ===", flush=True)
    with LoggedConnection(sock, "NHÂN VIÊN", "CHỦ MÁY") as connection:
        connection.settimeout(30)
        with connection.makefile("rb") as reader:
            connection.sendall(pack_message({"type": "identify"}))
            if receive_message(reader) != {"type": "ready", "ok": True}:
                sys.exit("Điện thoại chưa sẵn sàng nhận mã.")
            connection.sendall(pack_message({"type": "share", "code": invite["code"]}))
            ack = receive_message(reader)
    return ack.get("type") == "ack" and ack.get("ok") is True


def main():
    # Terminal Windows mặc định cp1252, không in được tiếng Việt.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Giả lập app thứ hai trong luồng chia sẻ máy.")
    parser.add_argument("--server", default=f"http://127.0.0.1:{SERVER_PORT}")
    parser.add_argument("--username", help="tài khoản trên laptop, khác tài khoản trên điện thoại")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--adb", action="store_true", help="chụp QR trên điện thoại qua adb")
    source.add_argument("--camera", action="store_true", help="quét QR bằng webcam")
    source.add_argument("--image", help="đọc QR từ file ảnh")
    source.add_argument("--text", help="dán thẳng nội dung QR")
    source.add_argument("--send", action="store_true", help="laptop là chủ máy, gửi mã tới điện thoại")
    parser.add_argument("--phone", help="địa chỉ Bluetooth điện thoại nhận (với --send)")
    parser.add_argument("--machine-id", help="máy cần chia sẻ (với --send)")
    parser.add_argument("--timeout", type=float, help="số giây chờ điện thoại gửi mã rồi dừng")
    args = parser.parse_args()
    if args.send and not (args.phone and args.machine_id):
        parser.error("--send cần --phone và --machine-id")

    username = args.username or input("Tài khoản trên laptop: ").strip()
    password = os.environ.get("SANDBOX_PASSWORD") or getpass.getpass("Mật khẩu: ")
    token = login(args.server, username, password)

    if args.send:
        ok = share_to_phone(args.server, token, args.machine_id, args.phone)
        print("\n=== Điện thoại xác nhận nhận mã:", ok, "===", flush=True)
        sys.exit(0 if ok else 1)

    use_qr = args.adb or args.camera or args.image or args.text
    code = parse_share(share_from_qr(args) if use_qr else share_from_bluetooth(args.timeout))

    result = post(args.server, APP_ACCEPT_SHARE, {"code": code, "token": token})
    if result.get("valid") is not True:
        sys.exit("Nhận chia sẻ thất bại.")
    # App nhân viên tải lại danh sách máy sau khi nhận; in ra để thấy vai trò mới.
    post(args.server, APP_MY_MACHINES, {"token": token})
    print("\n=== Nhận chia sẻ thành công ===", flush=True)


if __name__ == "__main__":
    main()
