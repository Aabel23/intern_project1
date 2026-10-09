"""
test_pump_accuracy.py
======================
Test do chinh xac cua bom bang cach bom theo thoi gian (calib san co trong
pump_ml.py) roi can lai bang loadcell (HX711) de xem thuc te ra bao nhieu gram.

QUY TRINH MOI LAN BOM:
    1. Bom X ml (quy doi ra thoi gian theo calib pump_gram)
    2. Cho 2s cho nuoc on dinh (het rung, het bot)
    3. Doc can (median cua vai mau)
    4. In ra: thoi gian bom (s) + khoi luong can duoc (g)
    5. Tru bi (zero lai can, gom ca ly + nuoc dang co) -> san sang cho lan ke

    Ly co dung tich lon (~500ml) nen dung 1 ly cho ca N lan, khong doi ly giua
    cac lan. Sau moi lan tru bi thi can bao ve tu 0 -> gram doc duoc CHINH LA
    gram cua rieng lan bom do (khong cong don).

CACH CHAY (tu thu muc version1.0/):
    python3 -m pump_control.pump_test

    Chuong trinh se hoi lenh theo dinh dang:  <so_bom> <ml> <so_lan>
    Vi du go vao:  1 30 15
        -> Bom #1, moi lan 30ml, lap lai 15 lan
    Go 'q' de thoat.

KET QUA:
    In ra bang: Lan | Thoi gian bom (s) | Khoi luong can (g) | Sai so vs muc tieu (g)
    Cuoi cung in trung binh + do lech chuan de tien dien vao file Excel
    test_dinh_luong_bom.xlsx (cot 30ml (s) / 50ml (s) trong sheet "Test bom").
"""

import sys
import collections
import statistics
from time import sleep

from pump_control.pump_ml import pump_gram, PUMP_GPIO, _load_pump_calib
from loadcell.loadcell import (
    load_calibration,
    read_weight_smooth,
    tare,
    WINDOW_SIZE,
)

# --- CAU HINH ---
SETTLE_TIME_SECONDS = 2.0     # cho nuoc on dinh truoc khi can
READ_SAMPLES = 10             # so mau doc lien tiep de lay median khi can ket qua
TARE_SAMPLES = 30             # so mau khi tru bi


def read_stable_weight(window, samples=READ_SAMPLES):
    """Doc vai mau lien tiep, tra ve median. Bo qua mau None (chip khong tra loi)."""
    vals = []
    tries = 0
    max_tries = samples * 5  # de phong read_weight_smooth tra None vai lan
    while len(vals) < samples and tries < max_tries:
        w = read_weight_smooth(window)
        if w is not None:
            vals.append(w)
        tries += 1
    if not vals:
        return None
    return statistics.median(vals)


def tare_scale(window):
    """Tru bi: doc raw truc tiep (khong qua window loc) roi set OFFSET moi.

    Dung ham tare() co san trong loadcell.py, sau do xoa window cu vi cac
    mau cu duoc tinh theo OFFSET cu, khong con hop le voi OFFSET moi.
    """
    tare(TARE_SAMPLES)
    window.clear()


def run_test(pump_number: int, ml_target: float, num_runs: int):
    if pump_number not in PUMP_GPIO:
        print(f"Loi: Bom #{pump_number} khong ton tai trong PUMP_GPIO.")
        return

    pump_calib = _load_pump_calib()
    if f"pump_{pump_number}" not in pump_calib:
        print(f"Loi: Bom #{pump_number} chua duoc calib. Chay calib_pump.py truoc.")
        return

    print("Dang tai calib loadcell...")
    load_calibration()
    print("OK.\n")

    print(f"Test Bom #{pump_number}  |  {ml_target:.1f}ml / lan  |  {num_runs} lan")
    print("Gia dinh: 1ml nuoc ~= 1g. Dat ly RONG len can.\n")

    window = collections.deque(maxlen=WINDOW_SIZE)

    input("Dat ly rong len can, nhan Enter de tru bi lan dau...")
    print("Dang tru bi ly rong...", end=" ", flush=True)
    tare_scale(window)
    print("xong.\n")

    results = []  # list of (duration_s, weight_g)

    for i in range(1, num_runs + 1):
        print(f"--- Lan {i}/{num_runs} ---")

        duration = pump_gram(pump_number, ml_target, verbose=True)

        print(f"  Cho {SETTLE_TIME_SECONDS:.1f}s cho nuoc on dinh...", end=" ", flush=True)
        sleep(SETTLE_TIME_SECONDS)
        print("xong.")

        weight = read_stable_weight(window)
        if weight is None:
            print("  CANH BAO: khong doc duoc can (loadcell khong phan hoi).")
            weight = float("nan")
        else:
            if abs(weight) < 0.1:
                weight = 0.0

        error = weight - ml_target if weight == weight else float("nan")  # nan check
        print(f"  => Thoi gian bom: {duration:.3f}s   Can duoc: {weight:.2f}g   "
              f"Sai so: {error:+.2f}g\n")

        results.append((duration, weight))

        # Tru bi (gom ca ly + nuoc hien co) de chuan bi cho lan ke tiep
        print("  Dang tru bi cho lan ke tiep...", end=" ", flush=True)
        tare_scale(window)
        print("xong.\n")

    # --- TONG KET ---
    durations = [d for d, w in results]
    weights = [w for d, w in results if w == w]  # loai nan

    print("=" * 60)
    print(f"KET QUA BOM #{pump_number} - {ml_target:.1f}ml x {num_runs} lan")
    print("=" * 60)
    print(f"{'Lan':>4} | {'Thoi gian (s)':>14} | {'Can duoc (g)':>13} | {'Sai so (g)':>10}")
    print("-" * 60)
    for i, (d, w) in enumerate(results, start=1):
        err_str = f"{(w - ml_target):+.2f}" if w == w else "  N/A"
        w_str = f"{w:.2f}" if w == w else "N/A"
        print(f"{i:>4} | {d:>14.3f} | {w_str:>13} | {err_str:>10}")
    print("-" * 60)

    if durations:
        print(f"Trung binh thoi gian bom : {statistics.mean(durations):.3f} s")
    if weights:
        print(f"Trung binh can duoc      : {statistics.mean(weights):.2f} g")
        if len(weights) > 1:
            print(f"Do lech chuan (stdev)    : {statistics.stdev(weights):.2f} g")
        print(f"Sai so trung binh vs {ml_target:.0f}ml : "
              f"{statistics.mean(weights) - ml_target:+.2f} g")
    if len(weights) < len(results):
        print(f"CANH BAO: {len(results) - len(weights)}/{len(results)} lan doc can bi loi (N/A).")

    print("\n  Nhap lenh theo dinh dang:  <so_bom> <ml> <so_lan>")
    print("  Vi du:  1 30 15      -> Bom #1, 30ml/lan, 15 lan")
    print("  Nhap 'q' de thoat.\n") 

def main(): 
    print("=" * 50)
    print("  TEST DO CHINH XAC BOM (loadcell)")
    print("=" * 50)
    print("\n  Nhap lenh theo dinh dang:  <so_bom> <ml> <so_lan>")
    print("  Vi du:  1 30 15      -> Bom #1, 30ml/lan, 15 lan")
    print("  Nhap 'q' de thoat.\n")

    while True:
        raw = input("  Lenh > ").strip().lower()
        if raw == "q":
            break

        tokens = raw.split()
        if len(tokens) != 3:
            print("  Sai dinh dang. Vi du: 1 30 15")
            continue

        try:
            pump_number = int(tokens[0])
            ml_target = float(tokens[1])
            num_runs = int(tokens[2])
        except ValueError:
            print(f"  Gia tri khong hop le: {tokens}")
            continue

        if num_runs <= 0:
            print("  Loi: so lan phai > 0.")
            continue
        if ml_target <= 0:
            print("  Loi: ml phai > 0.")
            continue

        try:
            run_test(pump_number, ml_target, num_runs)
        except KeyboardInterrupt:
            print("\n\nDa dung lan test nay boi nguoi dung.\n")
        except Exception as e:
            print(f"\n  LOI: {e}\n")


if __name__ == "__main__":
    main()
    