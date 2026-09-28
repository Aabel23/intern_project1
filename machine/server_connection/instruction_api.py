"""Các hàm giao tiếp HTTP giữa machine và server."""

import json
import urllib.request

from config.env import get_product_key, get_server_url
from config.routing import GET_COMMAND_PATH, POST_RESULT_PATH


def post_json(path, data):
    # Mọi request của máy đều kèm product key để server biết máy nào đang gọi.
    body = json.dumps({**data, "product_key": get_product_key()}).encode("utf-8")
    request = urllib.request.Request(
        get_server_url() + path,
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def poll_command():
    # Hỏi server lệnh tiếp theo trong hộp thư của máy này.
    return post_json(GET_COMMAND_PATH, {})["lenh"]


def send_result(lenh_id, ket_qua):
    # Đóng gói kết quả để server chuyển lại cho app.
    post_json(POST_RESULT_PATH, {"id": lenh_id, "ket_qua": ket_qua})

