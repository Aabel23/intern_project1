#!/bin/sh
# Chạy bởi Openbox khi X khởi động (~/.config/openbox/autostart).
# Ẩn con trỏ chuột, tắt màn hình chờ/khóa, chờ backend sẵn sàng rồi mở
# Chromium ở chế độ kiosk toàn màn hình, không có cách nào thoát ra bằng
# chuột/cảm ứng.

# Không tắt màn hình, không blank, không lock (bắt buộc cho màn hình LCD
# cảm ứng luôn bật).
xset s off
xset s noblank
xset -dpms

# Ẩn con trỏ chuột khi không di chuyển (đỡ vướng trên màn cảm ứng).
unclutter -idle 0.5 -root &

# ĐỘ PHÂN GIẢI MÀN HÌNH
#
# Áp lại lựa chọn đã lưu trong trang admin (Màn hình). Phải làm ở ĐÂY chứ
# không phải trong flexmix-backend.service: service đó khởi động TRƯỚC X,
# nên xrandr gọi từ backend sẽ không có màn hình nào để nói chuyện.
#
# Chưa chọn gì thì lệnh này không làm gì cả, và nó KHÔNG BAO GIỜ làm hỏng
# khởi động: apply_saved() nuốt mọi lỗi rồi trả về, vì một cửa hàng không
# mở được màn hình chỉ vì một dòng cấu hình độ phân giải thì tệ hơn nhiều
# so với việc chạy ở chế độ mặc định của panel.
#
# Vì sao đáng bận tâm: GPU của Pi ghép lại từng khung hình khi khách vuốt
# menu, và chi phí đó gần như tỉ lệ thuận với số điểm ảnh. Đo 09/09/2026
# trên chính máy này: 1920x1200 vuốt bị khựng, 1280x800 thì mượt, trang
# web không đổi một dòng.
# `cd` trong subshell là bắt buộc: Openbox chạy autostart từ thư mục
# home, và `python3 -m configuration.…` chỉ tìm thấy gói khi thư mục
# project nằm trên sys.path. Thiếu nó thì lệnh dưới báo
# ModuleNotFoundError mỗi lần khởi động — im lặng, vì nó chỉ đi vào
# journal. Subshell để phần còn lại của script vẫn ở thư mục cũ.
(cd /home/flexxource/hungvu/version1.0 \
 && ./.venv/bin/python3 -m configuration.display_mode --apply-saved) 2>&1 \
    | logger -t kiosk-display

# Đợi store_gui/serve.py (cổng 8080) lên hẳn rồi mới mở trình duyệt,
# tránh màn "Không thể kết nối" thoáng qua rồi phải người đứng đó bấm lại.
URL="http://localhost:8080/store_gui/drinks-pos.html"
until curl -s -o /dev/null "$URL"; do
    sleep 1
done

# TRÌNH DUYỆT: FIREFOX, KHÔNG PHẢI CHROMIUM
#
#   Chromium trên máy này rút cạn toàn bộ 320 MB CMA của Pi — vùng nhớ
#   liền khối mà tầng đồ hoạ cấp buffer từ đó — rồi tự giết renderer khi
#   không cấp nổi một tile 1920×320. Đo ngày 1/9/2026: 99 lần crash trong
#   29 giờ, lần nào cũng cách nhau ĐÚNG 1040 giây, cả ngày lẫn đêm, không
#   khách, không đơn.
#
#   Đã loại trừ: hết RAM, snap tự cập nhật, /dev/shm, file descriptor,
#   trang web rò rỉ (một trang chỉ có một dòng chữ cũng rút cạn y hệt),
#   phần cứng GPU, overlay sai model, và cả `--disable-gpu` (crash vẫn
#   tới đúng giờ với chữ ký y nguyên).
#
#   Firefox trên CÙNG máy, CÙNG trang, CÙNG màn hình: chạy 83 phút với
#   CmaFree dao động 147–207 MB và TỰ HỒI LẠI. Chromium chỉ đi xuống;
#   Firefox cấp rồi trả. Đó là khác biệt về chất, không phải về lượng.
#
# CỜ CỦA FIREFOX ÍT HƠN CHROMIUM RẤT NHIỀU
#   Chromium nhận --incognito, --disable-pinch,
#   --overscroll-history-navigation=0, --noerrdialogs... Firefox chỉ có
#   --kiosk và --private-window. Mọi thứ còn lại nằm trong preferences:
#   xem deploy/kiosk/firefox-kiosk-user.js và bước 8 của README. THIẾU
#   file đó thì khách vuốt cạnh màn hình là lùi trang được.
#
# --kiosk        : toàn màn hình, không thanh địa chỉ, không nút đóng
# --private-window: không giữ lịch sử của khách trước (như --incognito)
#
# Log đi qua `logger` thay vì đổ vào ~/.xsession-errors — file đó từng bị
# lỗi GPU của Chromium bơm lên 5,9 GB. journald tự giới hạn dung lượng.
# Xem bằng:  journalctl -t kiosk-browser -f
while true; do
    firefox \
        --kiosk \
        --private-window \
        "$URL" 2>&1 | logger -t kiosk-browser
    # Nếu trình duyệt bị đóng (crash, hoặc bị bên ngoài kill) thì tự mở
    # lại ngay, để không bao giờ lộ ra desktop trống.
    #
    # Lưu ý: vòng này CHỈ chạy khi trình duyệt THOÁT. Nếu chỉ tab chết mà
    # tiến trình còn sống thì nó không kích hoạt —
    # store_gui/kiosk_watchdog.py lo trường hợp đó.
    sleep 1
done
