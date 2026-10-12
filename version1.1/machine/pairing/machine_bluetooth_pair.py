"""Dịch vụ nhận máy qua BLE (hợp đồng v2): python -m machine.pairing.machine_bluetooth_pair

Chỉ quảng bá khi máy chưa có chủ theo lần hello gần nhất, hoặc trong 10 phút đầu sau khi
dịch vụ khởi động (cửa sổ claim, D2). Trạng thái online của phiên lấy từ cache mà vòng
`machine.main` ghi sau mỗi hello.
"""

import time

from machine.config.env import get_machine_name, get_server_trust_path, get_state_dir
from machine.config.identity import decode_b64u, load_identity, load_seal_code, load_server_trust, read_cache
from machine.pairing.claim_session import ClaimSession
from machine.pairing.wifi_setup import configure_wifi

CLAIM_WINDOW_SECONDS = 600


def main():
    state_dir = get_state_dir()
    identity = load_identity(state_dir)
    trust = load_server_trust(get_server_trust_path())
    signing_key = decode_b64u(trust["signing"]["public_key"])
    started = time.monotonic()

    def machine_info():
        cache = read_cache(state_dir)
        seen = cache.get("seen_at")
        return cache.get("machine_id"), isinstance(seen, (int, float)) and time.time() - seen < 60

    def new_session():
        # Mỗi kết nối đọc lại S từ đĩa; phiên xóa bản sao trong RAM khi đóng.
        return ClaimSession(identity, load_seal_code(state_dir), signing_key, configure_wifi, machine_info)

    def advertise():
        cache = read_cache(state_dir)
        return cache.get("owned") is not True or time.monotonic() - started < CLAIM_WINDOW_SECONDS

    from machine.pairing.gatt_server import run
    run(get_machine_name(), new_session, advertise)


if __name__ == "__main__":
    main()
