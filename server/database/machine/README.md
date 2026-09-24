# Quản lý máy FlexMix

Tạo bảng trong `server/database/database.db` từ thư mục gốc dự án:

```sh
python -m server.database.machine.init_db
```

Lệnh chạy lại được, không xóa dữ liệu hay sửa bảng `users`.

| Cột | Ý nghĩa |
| --- | --- |
| `machine_id` | Mã máy duy nhất, ví dụ `MAY-01`, khớp cấu hình trên máy |
| `name` | Tên hiển thị của máy, bắt buộc |
| `store_id` | ID cửa hàng, có thể để NULL khi chưa phân bổ |
| `model` | Dòng máy |
| `serial_number` | Serial duy nhất, để NULL nếu chưa biết |
| `firmware_version` | Phiên bản phần mềm trên máy |
| `location` | Vị trí lắp đặt |
| `status` | `active`: sử dụng, `maintenance`: bảo trì, `disabled`: ngừng sử dụng |
| `last_seen` | Unix timestamp của heartbeat gần nhất, NULL nếu chưa liên lạc |
| `heartbeat_interval_seconds` | Chu kỳ heartbeat, mặc định 5 giây, phải lớn hơn 0 |
| `notes` | Ghi chú |
| `created_at`, `updated_at` | Thời gian UTC; trigger tự cập nhật `updated_at` khi sửa thông tin máy |

Chưa có bảng cửa hàng nên `store_id` chưa đặt khóa ngoại.
Online/offline được suy ra từ `last_seen` và ngưỡng timeout (server hiện dùng 15 giây),
không phải cột `status`. Hiện endpoint heartbeat vẫn lưu trong bộ nhớ;
bảng này chưa được nối với endpoint, nên `last_seen` chưa tự nhận heartbeat.

Ví dụ thêm máy (không chạy tự động khi khởi tạo):

```sql
INSERT INTO machines (machine_id, name, store_id)
VALUES ('MAY-01', 'FlexMix quầy chính', 1);
```

## Bảng `machine_managers`

Liên kết máy với tài khoản (`users.id`) đang quản lý máy đó.
Một máy có thể có nhiều người quản lý, một người quản lý nhiều máy.

| Cột | Ý nghĩa |
| --- | --- |
| `machine_id` | Khóa ngoại tới `machines`, xóa máy thì xóa liên kết |
| `user_id` | Khóa ngoại tới `users`, xóa tài khoản thì xóa liên kết |
| `role` | `owner`: chủ máy (tối đa một người/máy), `manager`: người được giao quản lý |
| `created_at` | Thời điểm gán quyền (UTC) |

Khóa chính `(machine_id, user_id)` nên không gán trùng một người cho một máy.
Chưa có API ghi bảng này; đăng ký máy qua QR/Bluetooth chưa tự gán người quét.

```sql
-- Máy do user 1 quản lý
SELECT m.* FROM machines m
JOIN machine_managers mm ON mm.machine_id = m.machine_id
WHERE mm.user_id = 1;
```

## File quản lý dữ liệu máy

Các service không viết SQL bảng máy trực tiếp mà gọi qua ba file:

| File | Nội dung |
| --- | --- |
| `machine_read.py` | tra máy theo product key, khớp ID/key, chủ máy, quyền quản lý, máy của một tài khoản, danh sách nhân viên |
| `machine_write.py` | thêm máy, gán chủ, thêm/xóa quyền nhân viên |
| `machine_invite.py` | lưu mã mời mới (xóa mã cũ), tìm mã còn hiệu lực, đánh dấu đã dùng |

Hàm ghi luôn nhận `conn` để nơi gọi giữ giao dịch (`BEGIN IMMEDIATE`); hàm đọc nhận
`conn` tùy chọn, bỏ trống thì tự mở kết nối.
