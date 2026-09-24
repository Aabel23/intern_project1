# Các bản sao để tham khảo

Đây là nơi tập hợp code có thể dùng lại sau này. Các module hiện tại vẫn chạy
bằng file cũ; chưa chuyển import sang thư mục này.

| File | Hàm/lớp | Nguồn |
| --- | --- | --- |
| http_api.py | RegisterHandler, RegisterServer, run_api(routes, cleanup) | server/service/user_register/user_register/user_register_api.py |
| connection.py | connect(), get_connection() | server/database/connection.py |
| user_password.py | hash_password() | server/security/user_password.py |
| password_verify.py | _matches_password() | server/service/user_login/login_verify.py |

Ba file đầu copy nguyên nội dung. File cuối copy nguyên hàm đối chiếu mật khẩu
và các import cần thiết, không mang theo logic truy vấn tài khoản.

## Quy tắc cho agent

- Đây là bản sao tham khảo, chưa phải thư viện chung bắt buộc.
- Giữ nguyên tên hàm, hành vi và giới hạn của bản nguồn khi tham khảo.
- Khi viết module mới, có thể copy phần cần thiết vào chính module đó để giữ độc lập.
- Không tự chuyển module đang chạy sang import server.lib.
- Không tự xóa, gộp hoặc sửa các bản cũ. Chờ người dùng yêu cầu.
- Các bản sao không tự đồng bộ; đối chiếu nguồn trước khi sử dụng.
- http_api.py và connection.py vẫn dùng config chung của server. Handler HTTP
  có giới hạn kích thước request, giới hạn theo IP và callback cleanup; đọc các
  điều kiện này trước khi copy. Chưa tự khởi động HTTP hoặc kết nối DB khi import.
- Chưa đưa flow đăng ký, đăng nhập, OTP và câu SQL nghiệp vụ vào đây vì chúng
  gắn với từng tính năng.
