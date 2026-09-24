"""Các hàm giao tiếp HTTP giữa machine và server."""

import json
import urllib.request

from config.machine_config import (
    GET_COMMAND_PATH, 
    POST_RESULT_PATH, 
    SERVER_URL,
)


def poll_command():
    # Hỏi server rồi đọc gói lệnh trả về.
    response = urllib.request.urlopen(SERVER_URL + GET_COMMAND_PATH, timeout=10)
    body = response.read()
    response.close()

    text = body.decode("utf-8")
    data = json.loads(text)
    return data["lenh"]


def send_result(lenh_id, ket_qua):
    # Đóng gói kết quả để server chuyển lại cho app.
    data = {"id": lenh_id, "ket_qua": ket_qua}
    body = json.dumps(data).encode("utf-8")

    # Gửi kết quả cho server.
    request = urllib.request.Request(
        SERVER_URL + POST_RESULT_PATH,
        data=body,
        headers={"Content-Type": "application/json"},
    )
    response = urllib.request.urlopen(request, timeout=10)
    response.close()
