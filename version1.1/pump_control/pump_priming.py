"python3 -m pump_control.pump_priming"
import sys
import collections
from time import sleep
from gpiozero import PWMLED

# Cân dùng CHUNG driver ở loadcell/loadcell.py, KHÔNG chép lại.
# File này từng giữ bản sao riêng của read_hx711()/tare()/load_calibration()/
# read_weight_smooth() cùng OutputDevice(4), DigitalInputDevice(18) của nó.
# Bản sao đó thiếu mọi lớp bảo vệ đã thêm vào driver chính -- trở kéo lên,
# canh giờ xung, phát hiện lệch nhịp, chặn giá trị vô lý -- nên nó vẫn đọc
# sai đúng kiểu cũ trong khi driver chính đã lành. Nó còn giành hai chân
# GPIO 4/18 ngay lúc import, nên chạy file này lúc service đang chạy sẽ
# chết vì 'GPIO busy'.
from loadcell.loadcell import (
    WINDOW_SIZE,
    load_calibration,
    read_weight_smooth,
    tare,
)

# =====================================================================
# 1. CẤU HÌNH PHẦN CỨNG (Đồng bộ theo hệ thống)
# =====================================================================
# Sơ đồ chân GPIO của 10 bơm — dùng chung ở configuration/machine.py,
# KHÔNG chép lại, đúng như driver cân ở phần import phía trên.
from configuration.machine import PUMP_GPIO

# Định lượng mồi nước (15ml tương đương 5g)
PRIMING_DELTA_GRAM = 8.0  
STABILIZATION_TIME = 1.0  # Thời gian chờ nước ổn định (giây)

# =====================================================================
# 3. TIẾN TRÌNH MỒI NƯỚC ĐỘNG THEO PHƯƠNG PHÁP DELTA
# =====================================================================
def run_pump_priming():
    print("=" * 60)
    print("      QUY TRÌNH MỒI NƯỚC ĐẦU NGÀY TỰ ĐỘNG (LOADCELL)")
    print("=" * 60)
    
    # Khởi tạo và tải thông số cân
    try:
        load_calibration()
        print("[OK] Đã tải thông số cấu hình Loadcell thành công.")
    except Exception as e:
        print(f"[X] LỖI: {e}")
        sys.exit(1)

    print("\n👉 Đã nhận lệnh mồi nước. Bắt đầu chạy tự động...")
    print("Đang tiến hành trừ bì (Tare)...", end=" ", flush=True)
    tare(30)
    print("Xong!\n")

    # Khởi tạo cửa sổ lọc nhiễu cho cân
    window = collections.deque(maxlen=WINDOW_SIZE)
    
    # Điền trước dữ liệu mồi cho cân ổn định
    for _ in range(WINDOW_SIZE):
        read_weight_smooth(window)
        sleep(0.02)

    # Vòng lặp quét mồi tuần tự từ Bơm 1 đến Bơm 10
    for pump_num in sorted(PUMP_GPIO.keys()):
        gpio_pin = PUMP_GPIO[pump_num]
        
        # Đọc trọng lượng nền hiện tại trong ly trước khi bơm chạy
        base_weight = read_weight_smooth(window)
        while base_weight is None:
            base_weight = read_weight_smooth(window)
        
        # Thiết lập mục tiêu tịnh tiến động (Delta lý tưởng = Trọng lượng gốc + 15g)
        target_weight = base_weight + PRIMING_DELTA_GRAM
        
        print(f"▶️ [BƠM #{pump_num}] Bắt đầu mồi nước...")
        print(f"   - Trọng lượng ly hiện tại: {base_weight:.2f} g")
        print(f"   - Trọng lượng mục tiêu cần đạt: {target_weight:.2f} g")
        
        # Khởi tạo kích hoạt chân GPIO điều khiển motor bơm
        pwm = PWMLED(gpio_pin, frequency=1000)
        pwm.value = 1.0  # Bật bơm hoạt động hết công suất
        
        try:
            while True:
                current_weight = read_weight_smooth(window)
                if current_weight is not None:
                    # Tính toán lượng nước thực tế mà vòi hiện tại đã xả vào ly
                    pumped_delta = current_weight - base_weight
                    if pumped_delta < 0:
                        pumped_delta = 0.0
                        
                    print(f"\r   -> Đang bơm... Lượng nước tăng thêm: {pumped_delta:5.1f} ml / {PRIMING_DELTA_GRAM} ml", end="", flush=True)
                    
                    # Điều kiện ngắt: Nếu cân đo đạt hoặc vượt khối lượng mục tiêu delta
                    if current_weight >= target_weight:
                        break
                sleep(0.02)
                
            # Tắt bơm ngay lập tức khi đạt đích
            pwm.off()
            print(f"\n   [OK] Bơm #{pump_num} đã điền đầy ống.")
            
            # Giai đoạn chờ nước ổn định dao động theo yêu cầu của bạn
            print(f"   ⏳ Tạm dừng {STABILIZATION_TIME}s để dòng nước ổn định bề mặt...")
            sleep(STABILIZATION_TIME)
            
        except KeyboardInterrupt:
            pwm.off()
            print(f"\n[!] Quy trình mồi nước bị dừng khẩn cấp bởi người dùng tại Bơm #{pump_num}!")
            sys.exit(0)
        except Exception as e:
            pwm.off()
            print(f"\n[X] LỖI khi vận hành Bơm #{pump_num}: {e}")
            sys.exit(1)

    print("\n" + "=" * 60)
    print(" 🎉 HOÀN THÀNH: Tất cả đường ống đã được điền đầy nước!")
    print(" Máy đã sẵn sàng pha chế chính xác theo công thức.")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    run_pump_priming()
