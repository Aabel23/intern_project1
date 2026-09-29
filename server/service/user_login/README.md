# Đăng nhập và đăng xuất

App gửi tài khoản, sau đó hỏi kết quả xác minh để lấy token. Token được gửi kèm các request cần đăng nhập.

## API và gói tin

Các gói gửi bằng POST là JSON. GET dùng query trên URL. Token thuộc app; product_key thuộc máy nếu API yêu cầu. Các ví dụ trường dữ liệu minh họa cấu trúc, không phải giá trị thực.

| Phương thức | Route | Ai gọi | Gửi lên | Nhận về |
| --- | --- | --- | --- | --- |
| POST | /app/dang-nhap | App | request_id, username, password | valid, login_id, verify_route, message |
| POST | /app/xac-minh-dang-nhap | App | request_id, login_id | valid, verified, token, message; retry_after nếu chưa có kết quả |
| POST | /app/dang-xuat | App | token | valid, message |

## A. Đăng nhập

### 1. App gửi tài khoản lên server

POST `/app/dang-nhap`, gói `{request_id, username, password}`. request_id là 32 ký tự hex, dùng để nhận biết cùng một lần thử đăng nhập.

Hàm tham gia:

- App requestLogin(): tạo mã yêu cầu và gửi tài khoản.
- App postJson(): gửi HTTP JSON.

### 2. Server kiểm tài khoản và trả mã lần đăng nhập

Server kiểm request_id, so mật khẩu với database và giữ kết quả trong bộ nhớ. Đúng mật khẩu thì tạo token trong kết quả được giữ. Response request này là `{valid: true, login_id, verify_route, message}`; valid ở đây xác nhận đã nhận yêu cầu, chưa phải thông báo đăng nhập thành công.

Hàm tham gia:

- Server user_login_main.handle() / handle_routes(): nhận URL và đọc JSON.
- Server receive_login() / verify_login() / login_result(): kiểm tài khoản và giữ kết quả.
- Server get_credentials() / matches_password() / create_session(): đọc mật khẩu, so sánh và tạo phiên.

### 3. App hỏi kết quả xác minh

POST `/app/xac-minh-dang-nhap` với `{request_id, login_id}` nhận ở bước trước. Server đối chiếu hai mã và trả kết quả đã giữ. Thành công: `{valid: true, verified: true, token, message}`. Sai tài khoản: `{valid: false, message}`; chưa xong thì có retry_after.

Hàm tham gia:

- App requestLogin(): gửi request thứ hai.
- Server send_verification(): đối chiếu mã và trả kết quả.

### 4. App mở dashboard hoặc hiển thị lỗi

App giữ token khi thành công và mở dashboard. Các API sau dùng token này. Nếu thất bại thì hiển thị message; không gọi URL riêng để nhận token.

Hàm tham gia:

- App _submit(): đọc kết quả đăng nhập và chuyển màn hình.


## B. Đăng xuất

### 1. App yêu cầu đăng xuất

POST `/app/dang-xuat` với `{token}`. Server xóa phiên tương ứng rồi trả `{valid: true, message}`. App xóa token đã lưu và về màn đăng nhập.

Hàm tham gia:

- App logout(): gửi yêu cầu.
- Server end_session(): xóa phiên trong database.


## Nhánh lỗi và lưu ý

Hai route đăng nhập giới hạn theo IP; logout không áp dụng giới hạn đó. Kết quả đăng nhập giữ 60 giây. Cùng request_id nhưng đổi nội dung bị từ chối. Mật khẩu không gửi lại app; token lưu dạng hash trong database.
