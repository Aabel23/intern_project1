# Cấu hình gửi email OTP

Tài khoản gửi mail và mật khẩu không nằm trong mã nguồn mà trong `server/config/.env`
(đã có trong `.gitignore`, không chia sẻ file này):

```
SERVICE_EMAIL=<gmail dùng để gửi OTP>
SMTP_PASSWORD=<App Password 16 ký tự>
```

1. Tạo Gmail App Password cho tài khoản gửi (Google Account → Security → App passwords).
2. Điền đúng App Password 16 ký tự sau dấu `=`, không dùng mật khẩu Gmail thường, không thêm dấu nháy.
3. Server đọc hai khóa này lúc gửi mail (`user_register/otp/user_otp_send.py`: `get_service_email()`,
   `get_smtp_password()`); thiếu khóa nào thì báo lỗi nêu đúng tên khóa.
