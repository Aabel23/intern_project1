"""Test tái hiện DBG-03: watchdog CMA khởi động lại trình duyệt mãi mãi.

VÌ SAO CÓ FILE NÀY
    Ngưỡng CMA_LOW_KB (120 MB) chọn cho Chromium, nơi CmaFree "nằm phẳng
    ~300 MB rồi rơi". Kiosk giờ là Firefox; sáng 2026-10-06 CmaFree đứng yên
    ở 113-119 MB và journal ghi 40 lần "signalled 1 browser process(es)
    early" từ 10:49 tới 11:50 -- cứ ~95 s (cooldown 90 s + 2 lần đọc 5 s)
    một lần. Khởi động lại không làm CmaFree hồi lên, nên _check_cma không
    có điểm dừng: khách chỉ còn chưa tới 95 s để gọi món trước khi trang
    bị nạp lại, giỏ hàng mất, mốc test-mode của trang bị đặt lại.

    Test giả lập đồng hồ và /proc, không đụng trình duyệt thật. FAIL khi lỗi
    còn -- đó là bằng chứng.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from store_gui import kiosk_watchdog as kw  # noqa: E402


def test_cma_thap_khong_hoi_sau_restart_khong_duoc_restart_lien_tuc(monkeypatch):
    clock = {"now": 1000.0}
    restarts = []

    monkeypatch.setattr(kw.time, "monotonic", lambda: clock["now"])
    # CmaFree đứng yên dưới ngưỡng, như log 2026-10-06 (114 MB).
    monkeypatch.setattr(kw, "read_cma_free_kb", lambda: 114 * 1024)
    monkeypatch.setattr(kw, "kiosk_browser_pids", lambda: [4242])
    monkeypatch.setattr(kw, "drink_in_progress", lambda: False)
    monkeypatch.setattr(kw, "restart_kiosk_browser",
                        lambda: restarts.append(clock["now"]) or 1)
    monkeypatch.setattr(kw, "_last_request", clock["now"])
    monkeypatch.setattr(kw, "_quiet_until", 0.0)
    monkeypatch.setattr(kw, "_cma_strikes", 0)

    # Mười phút, mỗi nhịp CHECK_SECONDS; trang vẫn poll đều (có traffic).
    for _ in range(int(600 / kw.CHECK_SECONDS)):
        clock["now"] += kw.CHECK_SECONDS
        kw.note_request()
        kw._tick()

    # Restart lần đầu là hợp lý; restart lại khi lần trước không làm CMA
    # hồi thì chỉ phá trang của khách.
    assert len(restarts) <= 1, (
        f"watchdog restart trình duyệt {len(restarts)} lần trong 10 phút "
        f"dù CmaFree không đổi: {restarts}"
    )
