# Thư viện dùng chung của server

## Module đang dùng

Các block trong `server/` import trực tiếp; sửa ở đây là ảnh hưởng mọi nơi gọi.

| File | Hàm | Ai dùng |
| --- | --- | --- |
| `hashing.py` | `sha256_hex(text)` | product key (đăng ký máy, relay), token phiên (`session.py`), mã mời (`share_flow.py`), OTP (`otp_generator.py`) |
| `hashing.py` | `request_fingerprint(data)` | chống gửi lại khác nội dung cùng `request_id`: `login_flow.py`, `registration_flow.py` |
| `checks.py` | `is_request_id(value)` | `login_flow.py`, `registration_flow.py` |
| `checks.py` | `is_machine_id(value)` | `machine_register_verify.py`, `share_flow.py`, `manage_flow.py`, `machine_relay/relay_api.py` |
| `checks.py` | `remove_expired(states)` | dọn phiên RAM hết hạn: `login_flow.py`, `registration_flow.py` |
| `module_server.py` | `make_handler(modules)`, `ModuleServer` | `server/main.py` và chạy riêng module (`menu_sync_flow.py`): gọi `handle`/`handle_get`/`tick` của từng module |
| `http_json.py` | `read_json`, `read_body`, `discard_body`, `send_json` | mọi `*_api.py` |
| `valid_api.py` | `handle_valid_routes(request, routes, limited)` | module có flow trả `{"valid", "message"}`: đăng ký, đăng nhập, đăng ký máy, chia sẻ, quản lý máy |
| `rate_limit.py` | `too_many_requests(ip)` | `valid_api.py` khi `limited=True` (đăng ký, đăng nhập) |

Đổi `sha256_hex` là đổi cách băm mọi dữ liệu đã lưu trong DB (key, token, mã mời):
dữ liệu cũ sẽ không khớp nữa.

## Bản sao tham khảo cũ

`http_api.py`, `connection.py`, `user_password.py`, `password_verify.py` là bản copy
để tham khảo từ trước, **không module nào import**. Nguồn của chúng đã thay đổi
(server HTTP riêng đã bỏ, `hash_password` chuyển vào `server/database/user/user_add.py`),
nên đừng dùng; chỉ xóa khi người dùng yêu cầu.
