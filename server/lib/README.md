# Thư viện dùng chung của server

## Module đang dùng

Các block trong `server/` import trực tiếp; sửa ở đây là ảnh hưởng mọi nơi gọi.

| File | Hàm | Ai dùng |
| --- | --- | --- |
| `hashing.py` | `sha256_hex(text)` | product key (đăng ký máy, `machine_link/link_verify.py`), token phiên (`session.py`), mã mời (`share_flow.py`), OTP (`otp_generator.py`) |
| `hashing.py` | `request_fingerprint(data)` | chống gửi lại khác nội dung cùng `request_id`: `login_flow.py`, `user_register_flow.py` |
| `checks.py` | `is_request_id(value)` | `login_flow.py`, `user_register_flow.py` |
| `checks.py` | `is_machine_id(value)` | `share_verify.py`, `share_flow.py`, `machinelist_verify.py`, `dashboard_sync/sync_rules.py` |
| `checks.py` | `remove_expired(states)` | dọn phiên RAM hết hạn: `login_flow.py`, `user_register_flow.py` |
| `module_server.py` | `make_handler(modules)`, `ModuleServer` | `server/main.py` và `sandbox/server_module/run_modules.py`: gọi `handle`/`handle_get`/`tick` của từng module |
| `http_json.py` | `read_json`, `send_json`, `handle_routes`, `invalid`, `valid_status`, `with_valid_status` | mọi `*_api.py` |
| `session.py` | `create_session`, `user_from_request`, `check_login`, `end_session`, `NOT_LOGGED_IN` | mọi module cần biết người gọi; đăng nhập tạo phiên, đăng xuất xóa phiên |
| `rate_limit.py` | `too_many_requests(ip)` | `http_json.handle_routes(..., limited=True)`: đăng ký, đăng nhập |

Đổi `sha256_hex` là đổi cách băm mọi dữ liệu đã lưu trong DB (key, token, mã mời):
dữ liệu cũ sẽ không khớp nữa.

## Bản sao tham khảo cũ

`http_api.py`, `connection.py`, `user_password.py`, `password_verify.py` là bản copy
để tham khảo từ trước, **không module nào import**. Nguồn của chúng đã thay đổi
(server HTTP riêng đã bỏ, `hash_password` chuyển vào `server/database/user/user_add.py`),
nên đừng dùng; chỉ xóa khi người dùng yêu cầu.
