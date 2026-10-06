# Đăng nhập và đăng xuất

App gửi tài khoản, server kiểm rồi trả token ngay trong cùng response. Token được gửi kèm các request cần đăng nhập.

## API và gói tin

Các gói gửi bằng POST là JSON. GET dùng query trên URL. Token thuộc app; product_key thuộc máy nếu API yêu cầu. Các ví dụ trường dữ liệu minh họa cấu trúc, không phải giá trị thực.

| Phương thức | Route | Ai gọi | Gửi lên | Nhận về |
| --- | --- | --- | --- | --- |
| POST | /app/dang-nhap | App | username, password | valid, token, message |
| POST | /app/dang-xuat | App | token | valid, message |

## A. Đăng nhập

### 1. App gửi tài khoản lên server

POST `/app/dang-nhap`, gói `{username, password}`.

Hàm tham gia:

- App requestLogin(): gửi tài khoản.
- App postJson(): gửi HTTP JSON.

### 2. Server kiểm tài khoản và trả token

Server so mật khẩu với database. Đúng thì tạo phiên và trả `{valid: true, token, message}`. Sai thì trả `{valid: false, message}` với thông báo chung, không lộ tên đăng nhập nào tồn tại.

Hàm tham gia:

- Server user_login_main.handle() / handle_routes(): nhận URL và đọc JSON.
- Server receive_login() / verify_login(): kiểm tài khoản.
- Server get_credentials() / matches_password() / create_session(): đọc mật khẩu, so sánh và tạo phiên.

### 3. App mở dashboard hoặc hiển thị lỗi

App giữ token khi thành công và mở dashboard. Các API sau dùng token này. Nếu thất bại thì hiển thị message.

Hàm tham gia:

- App _submit(): đọc kết quả đăng nhập và chuyển màn hình.


## B. Đăng xuất

### 1. App yêu cầu đăng xuất

POST `/app/dang-xuat` với `{token}`. Server xóa phiên tương ứng rồi trả `{valid: true, message}`. App xóa token đã lưu và về màn đăng nhập.

Hàm tham gia:

- App logout(): gửi yêu cầu.
- Server end_session(): xóa phiên trong database.


## Nhánh lỗi và lưu ý

Route đăng nhập giới hạn theo IP; logout không áp dụng giới hạn đó. Gửi lại khi mạng lỗi thì server kiểm lại và cấp token mới. Mật khẩu không gửi lại app; token lưu dạng hash trong database.
