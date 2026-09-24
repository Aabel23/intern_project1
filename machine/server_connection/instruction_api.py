"""Các hàm giao tiếp HTTP giữa machine và server."""

import json
import urllib.request

from config.machine_config import (
    GET_COMMAND_PATH,
    POST_RESULT_PATH,
    POST_SYNC_PATH,
    get_product_key,
    get_server_url,
)


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


def send_sync(lenh_id, etag, goi):
    # Gói đồng bộ là JSON đã nén gzip (rỗng nếu không đổi); thông tin lệnh đi trong header.
    request = urllib.request.Request(
        get_server_url() + POST_SYNC_PATH,
        data=goi,
        headers={
            "Content-Type": "application/octet-stream",
            "X-Product-Key": get_product_key(),
            "X-Lenh-Id": str(lenh_id),
            "ETag": etag,
        },
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        response.read()
