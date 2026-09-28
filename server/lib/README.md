# Tài nguyên dùng chung của server

Các file này không import module tính năng trong `server/service`.
Chỉ để ở đây những cơ chế nhiều module thật sự cần dùng chung.

| File | Trách nhiệm |
| --- | --- |
| `module_server.py` | Lắp module, phát hiện route trùng, gọi handle/setup/tick |
| `http_json.py` | Đọc/ghi JSON, giới hạn body, ánh xạ lỗi SQLite sang HTTP |
| `session.py` | Cấp/tra/xóa token phiên dùng chung |
| `passwords.py` | Một triển khai băm và đối chiếu mật khẩu |
| `machine_access.py` | Tra người dùng và quyền máy; module truyền vai trò được phép |
| `machine_transport.py` | Hộp thư lệnh, long-poll, kết quả và heartbeat trong một tiến trình |
| `hashing.py` | Băm SHA-256, fingerprint request |
| `checks.py` | Kiểm dạng ID, dọn trạng thái hết hạn |
| `rate_limit.py` | Giới hạn request theo IP |

Kết nối SQLite ở `server/database/connection.py`. Các bản copy HTTP, connection,
băm/đối chiếu mật khẩu cũ đã bỏ. Quyền Menu/Kho, hạn mã mời và SMTP thuộc
module sở hữu tính năng; route tập trung ở `server/config/routing.py`.
