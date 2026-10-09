"""Trừ bì một cái ly rồi hiện khối lượng nước rót vào, theo thời gian thực.

CHẠY KHI ĐÃ DỪNG SERVICE — nó cần GPIO 4 và 18:

    sudo systemctl stop flexmix-backend
    ./.venv/bin/python -m loadcell.tare
    sudo systemctl start flexmix-backend

Dòng `import` bên dưới mở luôn hai chân đó (loadcell/loadcell.py gọi
open_pins() ở cấp module), nên chạy lúc máy đang bán sẽ báo chân bận.

FILE NÀY TỪNG KHÔNG CHẠY ĐƯỢC LẦN NÀO
    Ba dấu vết còn lại từ lúc nó được chép ra từ một script khác: docstring
    ghi tên file khác ("app_rot_nuoc.py"), dòng import lấy từ PACKAGE
    `loadcell` thay vì module `loadcell.loadcell` -- mà __init__.py rỗng
    nên không có tên nào ở đó -- và CALIBLOADCELL_FILE được dùng ở hàm main
    mà không hề được import. Sửa dòng import xong vẫn còn NameError.

    Cả ba đã sửa 2026-09-16.
"""

import time
import collections
from time import sleep

# Từ MODULE loadcell.loadcell, không phải package loadcell: loadcell/
# __init__.py rỗng, nên `from loadcell import ...` không tìm thấy gì.
from loadcell.loadcell import (
    load_calibration,
    tare,
    read_weight_smooth,
    WINDOW_SIZE,
)

# ── NGƯỠNG PHÁT HIỆN LY ───────────────────────────────────────────────────────
CUP_DETECT_GRAM  = 10.0
SUSTAINED_TIME   = 1.0   # giây
IDLE_NOISE_FLOOR = 5.0   # gram

# ══════════════════════════════════════════════════════════════════════════════
# FLOW PHÁT HIỆN LY
# ══════════════════════════════════════════════════════════════════════════════

def wait_for_cup():
    # [1] In ra "Dat ly len can"
    print("\n1. Dat ly len can...")
    
    window = collections.deque(maxlen=WINDOW_SIZE)
    sustained_start = None

    while True:
        gram = read_weight_smooth(window)
        if gram is None:
            sleep(0.05)
            continue

        # Lọc nhiễu vặt (gió, nước đọng)
        if abs(gram) < IDLE_NOISE_FLOOR:
            gram = 0.0

        if gram <= CUP_DETECT_GRAM:
            sustained_start = None
        else:
            if sustained_start is None:
                sustained_start = time.monotonic()

            elapsed = time.monotonic() - sustained_start
            if elapsed >= SUSTAINED_TIME:
                return gram

        sleep(0.05)

# ══════════════════════════════════════════════════════════════════════════════
# CHƯƠNG TRÌNH CHÍNH
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    try:
        print("=" * 50)
        print("  HE THONG CAN LY — KHOI DONG")
        print("=" * 50)
        
        # Không truyền đường dẫn: load_calibration() đã lấy mặc định là
        # CALIBLOADCELL_FILE, và hằng đó đi qua runtime_path() nên tự trỏ
        # sang /var/lib/flexmix/ khi máy đã migrate. Bản cũ truyền tay một
        # tên chưa hề được import -- NameError ngay dòng này.
        load_calibration()

        # BƯỚC 1 & BƯỚC 2: Yêu cầu đặt ly và xác nhận
        wait_for_cup()
        input("2. Phat hien dat ly len can - nhan enter de confirm")

        # BƯỚC 3: Thực hiện trừ bì ly
        print("3. Dang tru bi ly...", end=" ", flush=True)
        tare(30)
        print("xong!")

        # Xả bộ đệm cũ để cân không bị âm nháy loạn
        window = collections.deque(maxlen=WINDOW_SIZE)
        for _ in range(WINDOW_SIZE * 2):
            read_weight_smooth(window)

        # ── SẴN SÀNG RÓT NƯỚC ─────────────────────────────────────────────────
        print("\n" + "=" * 50)
        print("  [OK] SAN SANG ROT NUOC")
        print("=" * 50 + "\n")

        print("  Do khoi luong nuoc real-time (Ctrl+C de dung)...\n")
        
        while True:
            gram = read_weight_smooth(window)
            if gram is not None:
                display = 0.0 if abs(gram) < 1.0 else gram
                bar     = "█" * min(int(display / 5), 40)
                print(f"\r  {display:7.2f} g  [{bar:<40}]", end="", flush=True)
            sleep(0.05)

    except KeyboardInterrupt:
        print("\n\nDa dung chuong trinh. Tam biet!")