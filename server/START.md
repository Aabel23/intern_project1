# Khởi động server

Từ `androidv0.1`:

```sh
python -m server.main
python -m server.main --port 8001
```

Mặc định host/port là `0.0.0.0:8000`; có thể đổi bằng `--host` và `--port`.
App kết nối tới `http://<IP máy chạy server>:8000`.

`server/main.py` import trực tiếp các module và đăng ký trong `MODULES`.
Mỗi lần khởi động đều chạy toàn bộ module. Route được khai báo tập trung trong
`server/config/routing.py`, chia nhóm bằng comment; mỗi module giữ bảng `ROUTES`
ánh xạ các route đó sang hàm xử lý của mình.

Server phát hiện route trùng trước khi mở cổng. Khởi động tạo các bảng dùng chung
nếu chưa có, giữ dữ liệu hiện có, rồi chạy hook `setup()` của từng module.
Module chia sẻ tự tạo bảng mã mời. SMTP đọc từ `server/config/.env` khi cần gửi OTP,
qua `service/user_register/otp/user_otp_send.py`.

Mỗi request có thread riêng để app chờ lệnh không chặn máy long-poll. Hộp thư
và heartbeat ở `lib/machine_transport.py`; dữ liệu đó, OTP và yêu cầu đăng nhập
đang chờ sẽ mất khi tiến trình dừng. Phiên token đã lưu trong SQLite vẫn còn.

Các module dùng chung một tiến trình và tài nguyên nền. Quy ước chi tiết:
[MODULE_PATTERN.md](../MODULE_PATTERN.md).

```sh
python -m unittest tests.python.test_server tests.python.test_server_modules
```
