# Đăng ký tài khoản và OTP

App gửi thông tin đăng ký, nhận mã phiên, nhập OTP gửi qua email rồi tạo tài khoản. Các API này chưa cần token.

## API và gói tin

Các gói gửi bằng POST là JSON. GET dùng query trên URL. Token thuộc app; product_key thuộc máy nếu API yêu cầu. Các ví dụ trường dữ liệu minh họa cấu trúc, không phải giá trị thực.

| Phương thức | Route | Ai gọi | Gửi lên | Nhận về |
| --- | --- | --- | --- | --- |
| POST | /app/dang-ky-nguoi-dung | App | request_id, full_name, username, email, password | valid, registration_id, message; retry_after tùy kết quả |
| POST | /app/gui-ma-otp | App | registration_id | valid, registration_id, retry_after, message |
| POST | /app/xac-minh-otp | App | registration_id, code | valid, verified, account_created, message |

## A. Tạo tài khoản

### 1. App gửi thông tin đăng ký

POST `/app/dang-ky-nguoi-dung` với `{request_id, full_name, username, email, password}`. request_id là mã 32 ký tự hex của lần đăng ký.

Hàm tham gia:

- App requestRegistration() / postJson(): gửi form lên server.

### 2. Server kiểm thông tin và gửi email OTP

Server kiểm thông tin, tài khoản trùng và giữ phiên đăng ký. Server gửi OTP qua email, trả `{valid, registration_id, message, retry_after}` tùy kết quả. App cần giữ registration_id để gửi lại mã hoặc xác minh. Chưa ghi tài khoản vào database ở bước này.

Hàm tham gia:

- Server user_register_main.handle() / receive_register(): nhận request và chuẩn bị phiên.
- Server verify_user() / check_duplicate(): kiểm thông tin và tài khoản trùng.
- Server start_otp() / generate_code() / send_otp(): tạo mã và gửi email.

### 3. App nhập OTP và gửi xác minh

POST `/app/xac-minh-otp` với `{registration_id, code}`. Server kiểm phiên, mã, hạn và số lần thử. Nếu sai, app nhận `{valid: false, message}`.

Hàm tham gia:

- App verifyOtp(): gửi mã người dùng nhập.
- Server confirm_otp() / matches_code(): kiểm mã OTP.

### 4. Server tạo tài khoản và app hiển thị kết quả

Khi dữ liệu và OTP đều hợp lệ, server ghi tài khoản với mật khẩu đã băm. Response: `{valid: true, verified: true, account_created: true, message}`. App thông báo tạo tài khoản thành công; thao tác này không tự cấp token đăng nhập.

Hàm tham gia:

- Server finish_registration() / register_user(): hoàn tất và lưu tài khoản.
- Server hash_password(): băm mật khẩu.
- App màn OTP: hiển thị kết quả xác minh.


## B. Gửi lại OTP

### 1. App xin mã mới

POST `/app/gui-ma-otp` với `{registration_id}`. Server kiểm thời gian chờ và hạn phiên; đủ điều kiện thì gửi email mới. Response có message và retry_after để app đếm thời gian chờ.

Hàm tham gia:

- App requestOtp(): yêu cầu gửi lại.
- Server resend_otp() / send_otp(): kiểm điều kiện và gửi email.


## Nhánh lỗi và lưu ý

Route đăng ký/OTP có giới hạn theo IP. Thông tin phiên đăng ký và OTP giữ trong RAM; khởi động lại server làm mất phiên chưa hoàn tất. Lỗi SMTP được phản hồi để app biết chưa gửi được mã.
