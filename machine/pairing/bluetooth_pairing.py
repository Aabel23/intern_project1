"""Ghép đôi và gửi dữ liệu Bluetooth trên máy Linux dùng BlueZ."""

import json
from machine.config.machine_config import MACHINE_NAME, PRODUCT_KEY


def receive_message(reader):
    # Một dòng là một gói JSON, tối đa 4096 byte.
    body = reader.readline(4097)
    if len(body) > 4096 or not body.endswith(b"\n"):
        raise ValueError("Gói Bluetooth quá lớn hoặc chưa đầy đủ")
    text = body.decode("utf-8")
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("Gói Bluetooth phải là JSON object")
    return data


def pair_bluetooth(connection, reader):
    """Xác nhận app sẵn sàng; BlueZ đã xử lý bond trước khi gọi hàm này."""
    data = receive_message(reader)
    if data.get("type") != "identify":
        connection.sendall(pack_message({"ok": False}))
        return False
    connection.sendall(pack_message({"type": "ready", "ok": True}))
    return True


def pack_message(message):
    """Chuyển dictionary thành một gói JSON dạng bytes."""
    json_text = json.dumps(message, ensure_ascii=False, separators=(",", ":"))
    return (json_text + "\n").encode("utf-8")


def send_bluetooth(connection, reader, message):
    """Gửi trên kết nối hiện tại và chờ app xác nhận đã nhận đủ gói."""
    packet = pack_message(message)
    connection.sendall(packet)
    answer = receive_message(reader)
    return answer.get("type") == "ack" and answer.get("ok") is True


def handle_connection(connection):
    # Đóng kết nối cả khi lỗi; không chờ app gửi dữ liệu vô hạn.
    with connection:
        connection.settimeout(30)
        with connection.makefile("rb") as reader:
            paired = pair_bluetooth(connection, reader)
            if not paired:
                return False

            message = {
                "type": "pairing",
                "machine_name": MACHINE_NAME,
                "product_key": PRODUCT_KEY,
            }
            return send_bluetooth(connection, reader, message)


def main():
    # Chỉ cần BlueZ khi chạy trên Pi, test JSON không cần thư viện này.
    from machine.pairing.bluez_server import run_server
    run_server(MACHINE_NAME, handle_connection)


if __name__ == "__main__":
    main()
