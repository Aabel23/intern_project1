# Tài liệu luồng các feature

Mỗi tài liệu bắt đầu bằng bảng API/gói tin, sau đó mô tả bước app/server/máy
và liệt kê hàm tham gia bên dưới. README của feature có cùng nội dung luồng.

- [Đăng ký và OTP](user_register/REGISTER_FLOW.html)
- [Đăng nhập và đăng xuất](user_login/LOGIN_FLOW.html)
- [Đăng ký máy](machine_register/MACHINE_REGISTER_FLOW.html)
- [Chia sẻ máy](machine_share/SHARE_FLOW.html)
- [Cổng máy](machine_link/LINK_FLOW.html)
- [Dashboard tổng hợp](dashboard_sync/DASHBOARD_SYNC_FLOW.html)
- [Danh sách và quản lý máy](dashboard_sync/machinelist_sync/MACHINELIST_FLOW.html)
- [Menu](dashboard_sync/menu_sync/MENU_SYNC_FLOW.html)
- [Kho nguyên liệu](dashboard_sync/ingredient_sync/INGREDIENT_SYNC_FLOW.html)

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
