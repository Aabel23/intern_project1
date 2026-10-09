"""Chạy ba phần của máy, mỗi phần trong một thread riêng.

VÌ SAO MỘT THREAD CHẾT PHẢI KÉO CẢ TIẾN TRÌNH THEO
    Trước đây _run() bắt lỗi, in ra rồi để thread đó chết lặng lẽ. Tiến
    trình vẫn sống vì hai thread kia còn chạy, nên `Restart=always` trong
    flexmix-backend.service KHÔNG kích hoạt -- systemd chỉ dựng lại một
    tiến trình đã thoát.

    Hỏng kiểu đó là kiểu tệ nhất máy này có thể gặp: run_flow chết thì màn
    hình bán hàng vẫn nhận đơn, vẫn in nhãn, vẫn thu tiền -- mà không ly
    nào được pha, và không ai biết cho tới lúc khách hỏi.

    Nên bất kỳ thread nào kết thúc, vì lỗi hay vì tự return, đều kết thúc
    cả tiến trình. Ba phần này đều là vòng lặp vô hạn: không phần nào
    "chạy xong" một cách bình thường, nên thread nào dừng cũng là bất
    thường.

VÌ SAO os._exit() CHỨ KHÔNG PHẢI sys.exit()
    sys.exit() trong thread chỉ ném SystemExit và kết thúc đúng thread đó
    -- tức là đúng cái không đủ. os._exit() kết thúc tiến trình ngay.

    Nó bỏ qua các handler atexit và không flush buffer, nên stdout/stderr
    được flush bằng tay ngay trước đó. Phần cứng không cần dọn ở đây:
    run_flow tự đưa bơm và bảng nút về trạng thái nghỉ lúc khởi động, nên
    lần chạy kế tiếp bắt đầu từ trạng thái sạch dù lần này chết thế nào --
    kể cả mất điện, thứ mà không handler nào chạy được.
"""

import os
import sys
import threading
import traceback

from configuration import machine
from order import run_flow
from store_gui import serve as store_serve
from store_gui import sync_menu

SYNC_INTERVAL_MINUTES = machine.MENU_SYNC_INTERVAL_MINUTES

# Mã thoát báo cho systemd biết đây là kết thúc bất thường. Bất kỳ giá trị
# khác 0 nào cũng được với Restart=always; 1 để `systemctl status` hiện
# "status=1/FAILURE" thay vì "SUCCESS" cho một tiến trình chết vì lỗi.
EXIT_CODE_THREAD_DIED = 1


def _run(name, target, argv):
    """Chạy một phần. Thread này kết thúc = cả tiến trình kết thúc."""
    try:
        target(argv)
        reason = "tự kết thúc"
    except Exception:
        # In cả traceback, không chỉ str(error): trên máy chạy thật đây là
        # thứ duy nhất nói được hỏng ở đâu, và journalctl giữ lại nó.
        traceback.print_exc()
        reason = "dừng vì lỗi"

    print(f"[{name}] {reason} — thoát để systemd khởi động lại.", flush=True)
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(EXIT_CODE_THREAD_DIED)


def main():
    services = [
        ("store_gui", store_serve.main, []),
        ("sync_menu", sync_menu.main, ["--interval", str(SYNC_INTERVAL_MINUTES)]),
        ("run_flow", run_flow.main, []),
    ]

    threads = [
        threading.Thread(target=_run, args=(name, target, argv),
                         name=name, daemon=True)
        for name, target, argv in services
    ]
    for thread in threads:
        thread.start()

    try:
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        print("\nĐã dừng.", flush=True)


if __name__ == "__main__":
    main()
