"""Test tái hiện DBG-07: mã quét trong lúc chế độ test bị "phát lại" sau đó.

VÌ SAO CÓ FILE NÀY
    Vòng chính run_flow.main():
        wait_while_test_mode()               # chặn ở đây cả lúc test
        seen = wait_for_new_scan(raw, seen)  # seen = None sau đơn trước
    Khách quét mã khi máy đang ở chế độ test -> scanner vẫn ghi raw_qr.json
    (scanner không biết gì về chế độ test). Khi chế độ test tắt, `seen` vẫn
    là None nên mã cũ được coi là MỚI và máy mở đơn cho người có thể đã bỏ
    đi từ vài phút trước. Docstring button_watch nói ngược lại: "a
    customer's code is left unread ... They can scan again".

    Ghép đúng hai hàm main() gọi, không chạy main() (nó mở scanner, panel).
    Mọi file ở tmp_path; release_test_gpio bị thay để không chạm GPIO.
    FAIL khi lỗi còn -- đó là bằng chứng.
"""

import json
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from order import run_flow as rf  # noqa: E402
from panel_control import button_watch  # noqa: E402


def test_ma_quet_trong_che_do_test_khong_duoc_mo_don_sau_khi_tat(monkeypatch, tmp_path):
    mode_file = tmp_path / "mode.json"
    raw = tmp_path / "raw_qr.json"
    monkeypatch.setattr(button_watch, "MODE_FILE", mode_file)
    monkeypatch.setattr(rf, "release_test_gpio", lambda: None)
    monkeypatch.setattr(rf, "log_event", lambda *a, **k: None)
    monkeypatch.setattr(rf, "TEST_MODE_POLL_SECONDS", 0.01)
    monkeypatch.setattr(rf, "SCAN_POLL_SECONDS", 0.01)

    # Máy vào chế độ test (nút 15 / soak) ngay sau một đơn: seen = None.
    mode_file.write_text(json.dumps({"open": True, "id": "a"}))
    seen = None

    # Khách quét mã trong lúc đó; rồi chế độ test được tắt.
    def customer_then_close():
        raw.write_text(json.dumps({"qr_code": "STALE", "timestamp": "t1"}))
        mode_file.write_text(json.dumps({"open": False, "id": "b"}))

    threading.Timer(0.05, customer_then_close).start()
    rf.wait_while_test_mode()

    got = {}

    def take():
        got["scan"] = rf.wait_for_new_scan(raw, seen)

    worker = threading.Thread(target=take, daemon=True)
    worker.start()
    worker.join(timeout=0.5)

    assert got.get("scan") is None, (
        f"mã quét lúc máy đang test đã mở đơn sau khi tắt test: {got.get('scan')}"
    )
