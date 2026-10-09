"""Test tái hiện DBG-06: pause()/resume() của ButtonWatcher không đếm người mượn.

VÌ SAO CÓ FILE NÀY
    Hai bên cùng "mượn" chip nút 0x20 bằng một cờ Event duy nhất:
      - run_flow.run_one_order() gọi watcher.pause() trước khi mở runner;
      - test_gui.hardware.start() gọi pause_active()/resume_active() quanh
        MỌI job test.
    Bên nào trả trước sẽ xoá cờ của bên kia. Job test kết thúc giữa lúc một
    đơn đang pha thì watcher đọc lại chip song song với panel.py trong
    process_runner -- đúng lỗi "hai reader trên một bus I2C" mà
    button_watch.py nói đã làm mất đơn.

    Test KHÔNG chạy thread watcher (không mở I2C): chỉ thao tác cờ, đúng
    đường mà hai bên gọi. Test này FAIL khi lỗi còn -- đó là bằng chứng.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from panel_control import button_watch  # noqa: E402


def test_job_ket_thuc_khong_duoc_mo_lai_chip_khi_don_con_dang_pha(monkeypatch):
    watcher = button_watch.ButtonWatcher()
    # Giả lập watcher đang chạy mà không start thread thật.
    monkeypatch.setattr(button_watch, "_active", watcher)

    # 1. Job test (vd. prime-all, cân) bắt đầu: mượn chip.
    borrowed = button_watch.pause_active()
    assert borrowed

    # 2. Trong lúc job chạy, chế độ test bị tắt (soak/người ghi mode.json)
    #    và run_flow nhận đơn: run_one_order() cũng pause().
    watcher.pause()

    # 3. Job test xong trước khi đơn xong: finally của hardware.start()
    #    gọi resume_active().
    button_watch.resume_active()

    # Đơn vẫn đang pha -> watcher PHẢI còn tạm dừng.
    assert watcher._paused.is_set(), (
        "Job test trả chip đã xoá luôn lần pause() của đơn đang pha: "
        "watcher đọc 0x20 song song với panel.py trong process_runner."
    )
