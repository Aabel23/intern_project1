# Tài nguyên dùng chung của server

Nhóm theo trách nhiệm, không theo thứ tự bước của feature.
Hàm nhiều module dùng tương đồng nằm ở đây; helper riêng của feature giữ trong feature.
Lib không import server/service.

| Nhóm | File | Trách nhiệm |
| --- | --- | --- |
| HTTP | `http/http_server.py` | Mở cổng, lắp module, dispatch HTTP, kiểm route trùng |
| HTTP | `http/http_json.py` | Đọc/ghi JSON và xử lý route |
| HTTP | `http/http_rate_limit.py` | Giới hạn request theo IP |
| Security | `security/user_session.py` | Cấp, tra và xóa phiên người dùng |
| Security | `security/user_password.py` | Băm và kiểm mật khẩu |
| Security | `security/data_hash.py` | SHA-256 và fingerprint request |
| Machine | `machine/machine_access.py` | Kiểm quyền truy cập máy |
| Machine | `machine/machine_transport.py` | Hộp thư lệnh, kết quả và heartbeat |
| Validation | `validation/identifier_validate.py` | Kiểm định dạng request_id/machine_id |
| Validation | `validation/state_expire.py` | Dọn trạng thái RAM hết hạn |

Kết nối SQLite vẫn ở server/database/connection.py. Quyền cho từng tác vụ,
chuẩn gói tin và thứ tự bước thuộc module nghiệp vụ. Chỉ thay đường dẫn import;
không tạo bản sao trạng thái phiên, rate limit hay transport ở đường dẫn cũ.
