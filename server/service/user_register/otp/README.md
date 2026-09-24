# Luồng đăng ký và OTP

`main.py` chỉ nối route và khởi động API. `user_register/registration_flow.py` quản lý trạng thái đăng ký theo `registration_id`:

1. `user_verify.verify_user` kiểm tra dữ liệu; hợp lệ thì bật `data_valid`.
2. Registration flow băm mật khẩu, giữ dữ liệu đăng ký và yêu cầu `otp_flow` gửi mã.
3. `otp_flow` gọi sinh mã và gửi email; trả kết quả ngay, không chờ người dùng trong một thread.
4. Khi API xác minh tới, registration flow gọi `otp_flow.confirm_otp`; thành công thì bật `otp_verified`.
5. Đủ hai cờ, registration flow gọi `user_register.register_user` rồi bật `account_created`.

`otp_flow` chỉ giữ email, hash OTP, lượt sai, thời hạn, cooldown và trạng thái gửi/xác minh. Không đọc bảng users, không giữ mật khẩu, không tạo tài khoản.

App gửi `request_id` ngẫu nhiên 32 ký tự hex khi đăng ký và giữ nguyên khi thử lại cùng dữ liệu. Server trả `registration_id`; app dùng ID này khi gửi lại/xác minh OTP. Các cờ do server quyết định, không nhận từ app.

Giới hạn hiện tại: OTP 5 phút, phiên 15 phút, tối đa 5 lần sai/mã, gửi cách nhau 60 giây và tối đa 5 lần/email/giờ (kể cả gửi lỗi). API giới hạn 30 request/IP/phút, body 16 KiB, timeout đọc 10 giây. Tối đa 1000 phiên; server dọn phiên hết hạn trong vòng lặp phục vụ.

Trạng thái ở RAM, dùng cho một tiến trình server; khởi động lại mất phiên/cooldown. Chưa triển khai HTTPS. Server đăng ký chỉ mở ba route đăng ký/OTP; các route máy chạy riêng.

Kiểm thử: `python -m unittest server.service.user_register.test_flow`. Dùng database tạm và giả lập gửi email.
