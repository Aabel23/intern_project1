"""Báo định kỳ cho server biết machine vẫn đang chạy."""

import json
import time
import urllib.error
import urllib.request

from config.machine_config import (
    HEARTBEAT_INTERVAL_SECONDS,
    HEARTBEAT_PATH,
    MACHINE_ID,
    SERVER_URL,
)


def send_heartbeat():
    # Gửi mã máy; server tự ghi lại thời điểm nhận được.
    data = {"machine_id": MACHINE_ID}
    body = json.dumps(data).encode("utf-8")
    request = urllib.request.Request(
        SERVER_URL + HEARTBEAT_PATH,
        data=body,
        headers={"Content-Type": "application/json"},
    )
    response = urllib.request.urlopen(request, timeout=5)
    response.close()


def run_heartbeat():
    while True:
        try:
            send_heartbeat()
        except (urllib.error.URLError, OSError) as error:
            print("Khong gui duoc heartbeat:", error, flush=True)
        time.sleep(HEARTBEAT_INTERVAL_SECONDS)
