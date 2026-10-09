"""Read weight from the HX711 load cell amplifier.

WHAT THIS FILE IS
    The lowest layer of the scale. It speaks the HX711's bit protocol on
    two GPIO pins and turns the raw counts into grams. Anything that
    needs a weight goes through loadcell/cup_detection.py, which sits on
    top of this.

THE WIRING
    SCK = GPIO 4   clock, driven by us
    DT  = GPIO 18  data, driven by the chip

    Both devices are created when this module is imported, so importing
    it claims those two pins for the process.

HOW ONE READING WORKS
    1.  The HX711 pulls DT low when a new sample is ready. It converts at
        about 10 samples a second, so a sample appears roughly every
        100ms (~87ms measured on this machine).
    2.  read_hx711() waits for that, then clocks 24 bits out on SCK, most
        significant bit first, plus one extra pulse to select the gain
        for the next reading.
    3.  The 24-bit value is signed, so anything with the top bit set is
        shifted down into a negative number.
    4.  read_weight_smooth() converts counts to grams using the saved
        calibration, gram = (raw - OFFSET) / SCALE, and takes a median
        over a sliding window to reject single-sample spikes.

    DATA_READY_TIMEOUT_SECONDS must cover a whole conversion period. It
    was once ~10ms, shorter than any HX711 sample interval, so reads
    returned None about 85% of the time and cup detection failed at
    random.

CALIBRATION
    OFFSET and SCALE come from configuration/calib_loadcell.json and must
    be loaded with load_calibration() before any absolute weight means
    anything. Use loadcell/tare.py to re-zero an empty scale.
"""

from gpiozero import OutputDevice, DigitalInputDevice
from time import monotonic, perf_counter_ns, sleep
import collections
import statistics
import json
import os

from configuration.configuration import *
from configuration.machine import LOADCELL_DT_PIN, LOADCELL_SCK_PIN

# --- CẤU HÌNH PIN ---
# Hai chân được mở ở ĐÚNG MỘT CHỖ: hàm này. test_gui/hardware.py trả chân
# lại cho tiến trình khác giữa các job rồi mở lại, và bản sao cấu hình chân
# của nó từng quên mất trở kéo lên -> âm thầm khôi phục lỗi "dây đứt đọc ra
# -399.4 g". Ai cần mở lại chân thì gọi open_pins(), đừng tự tạo thiết bị.
SCK = None
DT = None


def open_pins():
    """Mở (hoặc mở lại) GPIO 4 và 18 với đúng cấu hình. An toàn khi gọi lại."""
    global SCK, DT

    if SCK is None:
        SCK = OutputDevice(LOADCELL_SCK_PIN)
        SCK.off()

    if DT is None:
        # pull_up=False (mặc định) để .value GIỮ NGUYÊN quy ước "1 = chân ở
        # mức HIGH". KHÔNG truyền pull_up=True: gpiozero khi đó đặt
        # _active_state = False và ĐẢO luôn .value, làm hỏng cả vòng chờ
        # lẫn phép đọc từng bit. Trở kéo ép riêng ở dòng dưới, mức phần cứng.
        DT = DigitalInputDevice(LOADCELL_DT_PIN)

        # Kéo LÊN, không kéo xuống. DOUT của HX711 nghỉ ở mức HIGH và chỉ
        # xuống LOW khi có mẫu mới, nên LOW là tín hiệu "sẵn sàng dữ liệu".
        # Với trở kéo XUỐNG (mặc định gpiozero), sợi DT đứt bị ghim ở LOW ->
        # read_hx711() tưởng chip mời đọc, clock ra 24 bit 0, trả raw = 0,
        # và (0 - OFFSET)/SCALE = -399.4 g: một con số SAI trông hợp lệ.
        # Với trở kéo LÊN, dây đứt bị ghim ở HIGH = "chưa có mẫu" -> hết
        # timeout -> None -> rơi đúng nhánh báo lỗi phần cứng đã có sẵn.
        # Chip đang nối thì DOUT là ngõ ra CMOS đẩy-kéo, trở ~50kΩ vô hại.
        DT.pin.pull = "up"

    return SCK, DT


open_pins()

# --- BIẾN TOÀN CỤC ---
OFFSET = 0
SCALE = 1.0
WINDOW_SIZE = 8

# --- CẤU HÌNH BỘ LỌC SPIKE ---
# Một chu kỳ chuyển đổi của HX711 là ~100ms ở 10 SPS, ~12.5ms ở 80 SPS.
# 0.25s đủ dư cho cả hai tốc độ mà vẫn phát hiện được chip mất kết nối.
DATA_READY_TIMEOUT_SECONDS = 0.25

# Biên độ raw lớn nhất còn coi là phép cân thật (~5700 g với calib hiện
# tại). Vượt qua là hỏng đường tín hiệu, không phải vật nặng.
MAX_PLAUSIBLE_RAW = 4_000_000

# --- CHỐNG CHIP NGỦ GIỮA KHUNG ---
# Datasheet HX711: giữ PD_SCK ở mức CAO quá 60us = lệnh power-down. Chip
# ngủ, reset, rồi lái DOUT lên HIGH -> mọi bit còn lại của khung đọc ra 1.
# Python bit-bang không cam kết được điều đó: chỉ cần Linux cướp CPU giữa
# SCK.on() và SCK.off() là vô tình phát ra đúng lệnh ngủ.
#
# Đo trên máy này (đã tính cả xung 25):
#     rảnh : median 27.6us  p99 44.1us  max 44.9us  -> 0.00% vượt 55us
#     tải  : median 25.2us  p99 119.3us max 257.7us -> 2.56% vượt 55us
# Phân bố tách đôi sạch: khung tốt <= ~45us, khung bị treo >= ~70us, không
# có gì ở giữa. Nên mọi ngưỡng trong 45..70us cho kết quả y hệt nhau; chọn
# 55us để có biên an toàn dưới mốc 60us mà vẫn không loại nhầm khung nào.
MAX_SCK_HIGH_NS = 55_000

# --- ƯU TIÊN REALTIME CHO ĐOẠN TỚI HẠN ---
# Đây là chỗ trị NGUYÊN NHÂN chứ không phải triệu chứng: mọi kiểu hỏng đo
# được đều bắt nguồn từ việc Linux đá tiến trình ra giữa 25 xung clock.
# Nâng luồng lên SCHED_FIFO trong đúng đoạn phát xung sẽ chặn việc đó.
#
# CHỈ bao đoạn phát xung, KHÔNG đặt realtime cho cả service: main.py còn
# chạy HTTP server và vài luồng nền, để tất cả ở realtime là rủi ro treo
# máy. Đoạn này chỉ ~0.3ms trong mỗi chu kỳ 87ms (~0.4% thời gian), và
# kernel còn chặn thêm bằng sched_rt_runtime_us = 950000 (95%).
#
# Cần CAP_SYS_NICE, cấp bằng AmbientCapabilities trong unit systemd. Nếu
# không có quyền thì im lặng chạy tiếp ở mức ưu tiên thường: mất lớp bảo
# vệ này thôi, các lớp kia vẫn còn. Thử MỘT lần rồi nhớ kết quả, tránh
# gọi syscall lỗi ~10 lần mỗi giây.
REALTIME_PRIORITY = 10
_realtime_available = None


def _enter_realtime():
    """Nâng luồng đang gọi lên SCHED_FIFO. False nếu không được phép."""
    global _realtime_available

    if _realtime_available is False:
        return False

    try:
        os.sched_setscheduler(
            0, os.SCHED_FIFO, os.sched_param(REALTIME_PRIORITY)
        )
    except (OSError, AttributeError):
        _realtime_available = False
        return False

    _realtime_available = True
    return True


def _leave_realtime():
    """Trả luồng về mức ưu tiên thường. Không bao giờ được ném lỗi."""
    try:
        os.sched_setscheduler(0, os.SCHED_OTHER, os.sched_param(0))
    except (OSError, AttributeError):
        pass


# Số xung tối đa phát thêm để kéo chip ra khỏi trạng thái kẹt giữa khung.
# Một khung là 25 xung nên 30 là dư; nhiều hơn chỉ tổ phát vào khung sau.
RESYNC_MAX_PULSES = 30

# Đếm để theo dõi sức khoẻ máy: hai con số này tăng nghĩa là máy đang quá
# tải khiến Python không giữ được nhịp clock, KHÔNG phải cân hỏng.
stretched_frames = 0
desynced_frames = 0

SPIKE_THRESHOLD_GRAM = 15.0   # Gram lệch tối đa so với median → nếu vượt quá = spike
MAX_CONSECUTIVE_REJECTS = 5   # Reject liên tiếp tối đa trước khi chấp nhận giá trị mới
_consecutive_rejects = 0


def read_hx711():
    """Return one raw 24-bit reading, or None if the chip stayed quiet.

    Blocks until the HX711 signals a new sample by pulling DT low, up to
    DATA_READY_TIMEOUT_SECONDS. None means the chip did not answer at
    all, which is a wiring or power problem rather than a light scale.
    """
    count = 0
    # HX711 kéo DT xuống thấp mỗi khi có mẫu mới: khoảng 100ms ở 10 SPS
    # (đo được ~87ms trên máy này). Phải chờ đủ một chu kỳ chuyển đổi,
    # nếu không hàm trả về None gần như mọi lần.
    deadline = monotonic() + DATA_READY_TIMEOUT_SECONDS
    while DT.value == 1:
        if monotonic() > deadline:
            return None
        sleep(0.0001)

    # Canh giờ TỪNG xung. Mốc lấy trước SCK.on() và sau SCK.off() nên
    # khoảng đo luôn BAO TRÙM thời gian chân thật sự ở mức cao -> không
    # bao giờ bỏ sót một lần vi phạm thật (đo được >= thật).
    global stretched_frames, desynced_frames
    stretched = False

    realtime = _enter_realtime()

    try:
        for _ in range(24):
            started = perf_counter_ns()
            SCK.on()
            count = count << 1
            SCK.off()
            if perf_counter_ns() - started > MAX_SCK_HIGH_NS:
                stretched = True
            if DT.value:
                count += 1

    # Xung thứ 25 chọn gain cho lần đọc sau. PHẢI canh giờ cả xung này:
    # nó nằm ngoài vòng lặp nên từng bị bỏ sót, mà một cú treo ở đây làm
    # hỏng khung KẾ TIẾP trong khi khung hiện tại vẫn báo timing sạch.
        started = perf_counter_ns()
        SCK.on()
        SCK.off()
        if perf_counter_ns() - started > MAX_SCK_HIGH_NS:
            stretched = True
    finally:
        # Trả ưu tiên NGAY khi hết đoạn tới hạn. Phần còn lại của hàm
        # (tái đồng bộ, kiểm tra giá trị) không cần realtime.
        if realtime:
            _leave_realtime()

    # Sau đủ 25 xung, HX711 bắt đầu chuyển đổi mới và ĐƯA DOUT LÊN CAO.
    # Nếu DOUT vẫn thấp thì chip chưa nhận đủ 25 xung -> nó đang đứng giữa
    # khung, lệch nhịp với ta, và giá trị vừa đọc là rác. Đo được: bắt
    # 29% số khung sai với chỉ 0.17% loại nhầm.
    #
    # Phải TÁI ĐỒNG BỘ, không chỉ bỏ khung: chip còn kẹt giữa khung thì
    # mọi lần đọc sau cũng lệch theo.
    if DT.value == 0:
        for _ in range(RESYNC_MAX_PULSES):
            SCK.on()
            SCK.off()
            if DT.value:
                break
        desynced_frames += 1
        return None

    if count & 0x800000:
        count -= 0x1000000

    # Bỏ khung SAU KHI đã phát đủ 25 xung, không thoát sớm giữa chừng:
    # thoát sớm sẽ để chip đứng ở giữa khung và lần đọc kế tiếp lệch nhịp
    # vĩnh viễn. Phát nốt cho đủ nhịp rồi mới vứt giá trị đi.
    if stretched:
        stretched_frames += 1
        return None

    # Chặn các mẫu không thể là phép cân thật. Trở kéo lên ở trên bắt được
    # dây đứt TRƯỚC khi đọc; đoạn này bắt dây chập chờn NGAY TRONG lúc
    # đang đánh 24 xung clock, khi đó không có timeout nào kích hoạt cả.
    #   0 hoặc -1  = DT ghim ở một mức suốt cả khung (đứt/chập dây tín hiệu)
    #   |x| > 4e6  = ADC bão hoà: cầu cân hở hoặc đấu ngược cực
    # Ngưỡng 4e6 tương đương ~5700 g, cách rất xa tầm hoạt động thật
    # (ly đầy ~580_000 count), nên không bao giờ cắt nhầm mẫu tốt.
    if count in (0, -1) or abs(count) > MAX_PLAUSIBLE_RAW:
        return None

    return count


def tare(samples=30):
    """Lấy mẫu để thiết lập điểm 0 (trừ bì)"""
    global OFFSET
    data = []
    while len(data) < samples:
        v = read_hx711()
        if v is not None:
            data.append(v)
    if data:
        OFFSET = sum(data) / len(data)
    return OFFSET


def load_calibration(calib_file=CALIBLOADCELL_FILE):
    """Tải OFFSET và SCALE từ file calib đã lưu sẵn"""
    global OFFSET, SCALE
    if not os.path.exists(calib_file):
        raise FileNotFoundError(
            f"Khong tim thay '{calib_file}'. Hay chay init_loadcell.py truoc."
        )
    with open(calib_file) as f:
        d = json.load(f)
    OFFSET = float(d["offset"])
    SCALE  = float(d["scale"])


def read_weight_smooth(window):
    """
    Đọc loadcell, lọc spike, trả về gram.

    Thuật toán:
        1. Đọc raw từ HX711
        2. Nếu window đã có >= 4 mẫu, tính median hiện tại:
           - Nếu raw mới lệch > SPIKE_THRESHOLD_GRAM → bỏ qua, trả về median
           - Nếu reject liên tiếp > MAX_CONSECUTIVE_REJECTS → chấp nhận
             (tránh kẹt khi cân thật sự thay đổi nhanh)
        3. Thêm raw vào window, trả về median (thay vì mean)
    """
    global _consecutive_rejects

    raw = read_hx711()
    if raw is None:
        return None

    if SCALE == 0:
        return 0.0

    # Spike gate
    if len(window) >= 4:
        current_median_raw = statistics.median(window)
        current_gram = (current_median_raw - OFFSET) / SCALE
        new_gram     = (raw - OFFSET) / SCALE
        delta        = abs(new_gram - current_gram)

        if delta > SPIKE_THRESHOLD_GRAM and _consecutive_rejects < MAX_CONSECUTIVE_REJECTS:
            _consecutive_rejects += 1
            return current_gram  # Giữ nguyên giá trị ổn định
        else:
            _consecutive_rejects = 0
    else:
        _consecutive_rejects = 0

    window.append(raw)
    return (statistics.median(window) - OFFSET) / SCALE


# --- CHƯƠNG TRÌNH CHÍNH (chỉ chạy khi gọi trực tiếp file này) ---
if __name__ == "__main__":
    try:
        print("Dang tai thong so calib...")
        load_calibration()
        print("OK.\n")

        input("👉 Dat LY TRONG len can, roi nhan Enter...")

        print("Dang tru bi ly...", end=" ", flush=True)
        tare(30)
        print("xong!\n")

        print("Rot nuoc vao ly. Nhan Ctrl+C de dung.\n")

        window = collections.deque(maxlen=WINDOW_SIZE)

        while True:
            weight = read_weight_smooth(window)
            if weight is not None:
                if abs(weight) < 0.1:
                    weight = 0.0
                print(f"\r  Nuoc: {weight:8.2f} g", end="", flush=True)
            sleep(0.05)

    except KeyboardInterrupt:
        print("\n\nDa dung.")