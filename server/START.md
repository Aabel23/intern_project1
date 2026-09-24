# Khởi động server

Từ thư mục `androidv0.1`, chạy một lệnh:

```sh
python -m server.main
```

Host và port đọc từ `server/config/config.py`, hiện là `0.0.0.0:8000`.
App dùng `http://<IP máy chạy server>:8000`; `0.0.0.0` là địa chỉ lắng nghe.
Tắt tiến trình API cũ đang dùng port 8000 trước khi chạy, không chạy thêm các
entry point dịch vụ trên cùng port. Ctrl+C dừng server.

Một server phục vụ đồng thời:

- Đăng ký tài khoản, gửi OTP, xác minh OTP.
- Đăng nhập, xác minh đăng nhập và đăng xuất (xóa token trên server).
- Đăng ký máy qua Bluetooth/QR và xác minh đăng ký máy.
- Chia sẻ máy cho nhân viên, xem và thu hồi nhân viên (`service/machine_share/README.md`).
- Heartbeat, xem online, nhận lệnh và trả kết quả của machine; máy xưng danh bằng
  product key, app gửi lệnh phải kèm token của chủ/nhân viên (`RELAY_FLOW.html`).

Mỗi request có thread riêng, nên app chờ kết quả không chặn machine hỏi lệnh.
Phiên OTP/đăng nhập hết hạn được dọn định kỳ. Khởi động lại làm mất các phiên
và lệnh đang giữ trong RAM; các bản ghi SQLite vẫn còn.

`server/main.py` chỉ nối dịch vụ; các entry point riêng vẫn dùng được.
Các module dùng chung một tiến trình và database, không phải cách ly tiến trình.
Lỗi import hoặc lỗi cả tiến trình vẫn ảnh hưởng server chung.

Database users và cấu hình SMTP dùng như luồng đăng ký hiện tại; entry point
chỉ gọi hàm khởi tạo bảng machines hiện có, không tự tạo lại tài khoản/SMTP.

```sh
python -m unittest server.test_main -v
```
