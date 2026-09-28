# Chia sẻ máy

Chủ máy tạo mã mời, nhân viên nhận mã (quét QR hoặc nhận qua Bluetooth) để được
giao quản lý máy. Mọi request gửi kèm `token` nhận được khi đăng nhập
(`/app/xac-minh-dang-nhap`); token hết hạn hoặc đã đăng xuất thì server trả
`login_required: true` để app quay về màn hình đăng nhập.

| Route | Body | Kết quả |
| --- | --- | --- |
| POST `/app/tao-ma-chia-se` | `token`, `machine_id` | `code`, `expires_in`; chỉ `owner` gọi được |
| POST `/app/nhan-chia-se` | `token`, `code` | ghi người gọi là `manager`, trả `machine_id`, `machine_name` |
| POST `/app/nhan-vien-may` | `token`, `machine_id` | `staff`: `user_id`, `username`, `full_name`; chỉ `owner` |
| POST `/app/thu-hoi-quyen` | `token`, `machine_id`, `user_id` | xóa quyền `manager` của nhân viên; chỉ `owner`, không xóa được chủ |

Mã dài 32 ký tự ngẫu nhiên, lưu SHA-256 trong `machine_invites`, dùng một lần,
hết hạn sau 5 phút. Tạo mã mới thì mã cũ chưa dùng của máy đó hết hiệu lực.
Chủ nhận mã của chính mình vẫn giữ quyền `owner`. Tab Menu và Kho chỉ nhận yêu cầu
từ `owner` hoặc `manager` của máy (quyền do từng module Menu/Kho khai báo, tra qua `lib/machine_access.py`).

Nội dung QR và gói Bluetooth giống nhau: `{"type":"share","code":"..."}`
(giao thức Bluetooth: `app/flutter_app/lib/feature/machine_share/QR.md`).

```sh
python -m unittest tests.python.test_machine_share -v
```

Module tự giữ `machine_share_schema.sql`, `machine_share_store.py` và tham số mã mời trong `machine_share_process.py`.
Hook `setup()` tạo bảng khi server khởi động, giữ nguyên mã mời đã lưu.
Danh sách máy `/app/may-cua-toi` thuộc module `machinelist_sync`.
