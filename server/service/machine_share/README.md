# Chia sẻ máy

Chủ máy tạo mã mời, nhân viên quét QR để được giao quản lý máy.
Mọi request gửi kèm `token` nhận được khi đăng nhập (`/app/xac-minh-dang-nhap`).

| Route | Body | Kết quả |
| --- | --- | --- |
| POST `/app/tao-ma-chia-se` | `token`, `machine_id` | `code`, `expires_in`; chỉ `owner` gọi được |
| POST `/app/nhan-chia-se` | `token`, `code` | ghi người gọi là `manager`, trả `machine_id`, `machine_name` |
| POST `/app/may-cua-toi` | `token` | `machines`: `machine_id`, `name`, `role` |

Mã dài 32 ký tự ngẫu nhiên, lưu SHA-256 trong `machine_invites`, dùng một lần,
hết hạn sau 5 phút. Chủ quét mã của chính mình vẫn giữ quyền `owner`.
Chưa có API thu hồi quyền nhân viên; relay `/app/gui-lenh` chưa kiểm tra quyền.

```sh
python -m unittest server.service.machine_share.test_flow -v
```
