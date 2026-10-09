"""
init_loadcell.py
=============
Chạy MỘT LẦN DUY NHẤT để hiệu chuẩn cân với quả cân mẫu 83.3g.
Kết quả lưu vào calib.json — các lần sau không cần chạy lại.

Cách dùng:
    python init_loadcell.py
"""

import json
# Cân dùng CHUNG driver ở loadcell/loadcell.py, KHÔNG chép lại.
# File này từng giữ bản sao riêng của read_hx711()/tare()/load_calibration()/
# read_weight_smooth() cùng OutputDevice(4), DigitalInputDevice(18) của nó.
# Bản sao đó thiếu mọi lớp bảo vệ đã thêm vào driver chính -- trở kéo lên,
# canh giờ xung, phát hiện lệch nhịp, chặn giá trị vô lý -- nên nó vẫn đọc
# sai đúng kiểu cũ trong khi driver chính đã lành. Nó còn giành hai chân
# GPIO 4/18 ngay lúc import, nên chạy file này lúc service đang chạy sẽ
# chết vì 'GPIO busy'.
#
# Ở ĐÂY CÒN QUAN TRỌNG HƠN MỌI NƠI KHÁC: file này SINH RA calib_loadcell.json.
# Một khung hỏng lọt vào lúc lấy mẫu sẽ ghi sai OFFSET/SCALE, và từ đó mọi
# phép cân của máy đều sai theo -- một lỗi thoáng qua bị đóng băng thành
# hằng số vĩnh viễn.
from loadcell.loadcell import read_hx711
from configuration.configuration import CALIBLOADCELL_FILE

# ── THAM SỐ ───────────────────────────────────────────────────────────────────
KNOWN_WEIGHT  = 83.3   # gram — quả cân mẫu
SAMPLES       = 50     # Càng nhiều mẫu càng chính xác


def _average(n: int) -> float:
    buf = []
    fails = 0
    while len(buf) < n:
        v = read_hx711()
        if v is not None:
            buf.append(v)
        else:
            fails += 1
            if fails > n * 3:
                raise RuntimeError("HX711 không phản hồi — kiểm tra kết nối.")
    return sum(buf) / len(buf)


def main():
    print("=" * 45)
    print("   HIỆU CHUẨN CÂN — CHẠY 1 LẦN DUY NHẤT")
    print("=" * 45)

    # BƯỚC 1 — Tare bàn cân trống
    print("\n[BƯỚC 1] Đảm bảo bàn cân TRỐNG hoàn toàn.")
    input("         → Nhấn Enter khi sẵn sàng... ")
    print(f"         Đang lấy {SAMPLES} mẫu offset...", end=" ", flush=True)
    offset = _average(SAMPLES)
    print(f"xong.  RAW offset = {offset:.1f}")

    # BƯỚC 2 — Đặt quả cân mẫu
    print(f"\n[BƯỚC 2] Đặt quả cân mẫu {KNOWN_WEIGHT}g lên bàn cân.")
    input("         → Nhấn Enter khi sẵn sàng... ")
    print(f"         Đang lấy {SAMPLES} mẫu với quả cân...", end=" ", flush=True)
    raw_with = _average(SAMPLES)
    print(f"xong.  RAW với cân = {raw_with:.1f}")

    # BƯỚC 3 — Tính SCALE
    scale = (raw_with - offset) / KNOWN_WEIGHT
    if abs(scale) < 1:
        print("\n❌ SCALE quá nhỏ — có thể cân không được kết nối đúng.")
        return

    # BƯỚC 4 — Kiểm tra nhanh
    check = (raw_with - offset) / scale
    print(f"\n✅ Kiểm tra: {check:.2f}g (kỳ vọng {KNOWN_WEIGHT}g) "
          f"— sai số {abs(check - KNOWN_WEIGHT):.2f}g")

    # BƯỚC 5 — Lưu file
    with open(CALIBLOADCELL_FILE, "w") as f:
        json.dump({"offset": offset, "scale": scale}, f, indent=2)

    print(f"\n💾 Đã lưu → {CALIBLOADCELL_FILE}")
    print(f"   OFFSET = {offset:.2f}")
    print(f"   SCALE  = {scale:.6f}")
    print("\n✅ Hiệu chuẩn hoàn tất.\n")


if __name__ == "__main__":
    main()
