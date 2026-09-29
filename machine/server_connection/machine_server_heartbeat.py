"""Báo định kỳ cho server biết machine vẫn đang chạy."""

import json
import time
import urllib.error
import urllib.request

from config.env import get_product_key, get_server_url
from config.routing import HEARTBEAT_INTERVAL_SECONDS, MACHINE_HEARTBEAT_SEND


def send_heartbeat():
    # Máy xưng danh bằng product key; server tự tra machine_id và ghi thời điểm nhận.
    data = {"product_key": get_product_key()}
    body = json.dumps(data).encode("utf-8")
    request = urllib.request.Request(
        get_server_url() + MACHINE_HEARTBEAT_SEND,
        data=body,
        headers={"Content-Type": "application/json"},
    )
    response = urllib.request.urlopen(request, timeout=5)
    response.close()


def run_heartbeat():
    while True:
        try:
            send_heartbeat()
        except (urllib.error.URLError, OSError, ValueError) as error:
            print("Khong gui duoc heartbeat:", error, flush=True)
        time.sleep(HEARTBEAT_INTERVAL_SECONDS)
