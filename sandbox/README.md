# Sandbox: thử app thật khi chỉ có một điện thoại và một laptop Windows

Laptop đóng vai những thứ còn thiếu (máy FlexMix, app thứ hai) và in mọi gói tin ra
terminal. Chạy từ thư mục gốc `androidv0.1`, server đang chạy (`python -m server.main`).

| Script | Laptop đóng vai | Ghi chú |
| --- | --- | --- |
| `bluetooth_pair/app2machine-pair.py [--env file]` | máy FlexMix chờ app pair Bluetooth | dùng nguyên `machine/pairing`; trên app bật "Hiện mọi thiết bị Bluetooth" |
| `relay/machine_sim.py [--env file]` | máy FlexMix online qua relay | chạy nguyên `machine/main.py`, database máy giả là SQLite tạm (tạo mới mỗi lần chạy, in đường dẫn, xóa khi dừng) |
| `bluetooth_pair/app2app_pair.py` | nhân viên nhận mã qua Bluetooth | thêm `--adb`/`--camera`/`--image`/`--text` để nhận qua QR |
| `bluetooth_pair/app2app_pair.py --send --phone <BT điện thoại> --machine-id <id>` | chủ máy gửi mã tới điện thoại | điện thoại mở "Nhận chia sẻ qua Bluetooth" trước |

`--env` trỏ tới file dạng `machine/config/machine.env` (tên, product key, server) để
giả một máy khác; mặc định dùng file của repo. `app2app_pair.py` hỏi mật khẩu trên
terminal, hoặc đọc biến môi trường `SANDBOX_PASSWORD` khi chạy tự động.

## Test tự động toàn bộ trên điện thoại

```sh
python sandbox/e2e/run_e2e.py              # build + cài app rồi test (~5 phút)
python sandbox/e2e/run_e2e.py --skip-build # dùng app đang cài
```

Cần: điện thoại cắm USB (gỡ lỗi USB), Bluetooth và Wi-Fi bật, cùng mạng với laptop,
`flutter` và `adb` trong PATH, `pip install opencv-python-headless`.
Script tự bật server nếu chưa chạy, tạo tài khoản và máy tạm (`e2e_…`, `FlexMix-E2E-…`),
điều khiển app qua `adb`, rồi xóa sạch dữ liệu tạm. Log và ảnh màn hình lúc lỗi nằm
trong `sandbox/e2e/logs/<thời điểm>/`.

Kịch bản: đăng nhập chủ → pair máy qua Bluetooth → máy online, đọc menu, bật món, xem kho →
chia sẻ qua Bluetooth → xem và thu hồi nhân viên → chia sẻ qua QR → đăng xuất (xóa phiên
trên server) → nhân viên nhận chia sẻ qua Bluetooth → phiên hết hạn thì về màn hình đăng nhập.
