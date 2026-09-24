# Pairing trên Raspberry Pi

Chạy từ thư mục gốc `androidv0.1` trên Raspberry Pi OS:

```sh
sudo apt install bluez python3-dbus python3-gi
sudo systemctl start bluetooth
python3 -m machine.pairing.bluetooth_pairing
```

Máy lấy `MACHINE_NAME` trong `machine/config/machine.env` làm tên Bluetooth và gửi `PRODUCT_KEY` trong cùng file (xem `machine/README.md`).
BlueZ đăng ký SPP UUID `00001101-0000-1000-8000-00805f9b34fb`, channel 1,
yêu cầu bond trước khi nhận kết nối. Agent chấp nhận bond bằng NoInputNoOutput.
Máy cho phép quét tìm trong 120 giây; chạy lại để mở lại cửa sổ quét.
Hết thời gian discoverable không ngắt kết nối đang có hoặc chặn thiết bị đã biết địa chỉ.

App quét `FlexMix-`, cho người dùng chọn máy, bond rồi kết nối RFCOMM.
Mỗi gói là một dòng JSON UTF-8 kết thúc bằng `\n`:

1. App gửi `{"type":"identify"}`.
2. Máy trả `{"type":"ready","ok":true}`; `pair_bluetooth()` trả `True`.
3. Máy gọi `send_bluetooth()` gửi
   `{"type":"pairing","machine_name":"FlexMix-01","product_key":"..."}`.
4. App đọc đủ gói rồi gửi `{"type":"ack","ok":true}`.
5. `send_bluetooth()` trả `True`, máy đóng kết nối. Dịch vụ tiếp tục chờ app.

App phải đọc từng dòng vì hai gói từ máy có thể đến chung một lần đọc.
Timeout gửi/nhận là 30 giây; gói nhận tối đa 4096 byte.
`pair_bluetooth()` xác nhận app sẵn sàng; BlueZ xử lý bond trước đó.
Không gửi ID máy vì server cấp ID chính thức sau đăng ký; khi chạy relay, máy xưng danh bằng product key.

Luồng chính nằm trong `bluetooth_pairing.py`, các callback bắt buộc của BlueZ
nằm trong `bluez_server.py`. Module này chạy riêng, chưa nối vào `machine/main.py`
hoặc đăng ký server.

## Thử bằng app Android

1. Chạy module trên Pi rồi mở app, vào tab Máy → Bluetooth.
2. Cấp quyền Bluetooth (Android cũ cần quyền vị trí và bật vị trí nếu hệ thống yêu cầu).
3. Chờ quét 15 giây, chọn máy `FlexMix-...` trong danh sách vừa tìm thấy.
4. Đồng ý ghép đôi khi Android hỏi. App nhận `ready`, đọc gói `pairing`, gửi ACK.
5. App hiển thị tên máy và product key; Pi in `Pairing hoàn tất: True`.

Sau khi nhận gói, app gửi `/app/dang-ky-may` kèm token; người pair đầu tiên thành chủ máy.
Quay lại sẽ hủy quét/kết nối đang chờ. Nếu Pi hết cửa sổ quét 120 giây,
khởi động lại module pairing trên Pi rồi bấm Quét lại trên app.

```sh
python -m unittest machine.pairing.test_bluetooth_pairing -v
```

Test dùng socket thật trong máy tính để kiểm tra giao thức, không cần BlueZ.
Bond, tên Bluetooth và kết nối SPP vẫn cần kiểm tra trên Raspberry Pi và Android thật.
