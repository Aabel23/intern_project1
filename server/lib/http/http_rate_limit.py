"""Giới hạn 30 request/phút/IP cho các API chưa cần token (dò mật khẩu, spam OTP).

API máy/chia sẻ đã đòi token hợp lệ nên không dùng, cả quán chung một IP vẫn không bị chặn.
"""

import threading
import time

IP_REQUESTS = {}
IP_LOCK = threading.Lock()
MAX_REQUESTS = 30
WINDOW_SECONDS = 60
MAX_IPS = 1000


def too_many_requests(ip):
    now = time.monotonic()
    with IP_LOCK:
        for key, record in list(IP_REQUESTS.items()):
            if now >= record[0]:
                del IP_REQUESTS[key]
        if ip not in IP_REQUESTS and len(IP_REQUESTS) >= MAX_IPS:
            return True
        record = IP_REQUESTS.setdefault(ip, [now + WINDOW_SECONDS, 0])
        record[1] += 1
        return record[1] > MAX_REQUESTS
