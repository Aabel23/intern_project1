# Quản lý máy FlexMix

Tạo bảng trong `server/database/database.db` từ thư mục gốc dự án:

```sh
python -m server.database.machine.init_db
```

Lệnh chạy lại được, không xóa dữ liệu; cũng tạo bảng tài khoản/phiên nếu chưa có.

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
| `last_seen` | Unix timestamp lần liên lạc gần nhất, NULL nếu chưa liên lạc; chưa được code nào đọc/ghi |
| `heartbeat_interval_seconds` | Chu kỳ báo cũ (thiết kế heartbeat), mặc định 5 giây, phải lớn hơn 0; chưa được code nào đọc/ghi |
| `notes` | Ghi chú |
| `created_at`, `updated_at` | Thời gian UTC; trigger tự cập nhật `updated_at` khi sửa thông tin máy |

Chưa có bảng cửa hàng nên `store_id` chưa đặt khóa ngoại.
Online/offline không dùng database: server suy ra từ lần poll/gửi kết quả cuối và lệnh máy đang làm,
lưu trong bộ nhớ (`LAN_THAY_CUOI`, `DANG_LAM`, ngưỡng 15 giây), không phải cột `status`.
Hai cột `last_seen` và `heartbeat_interval_seconds` chưa được nối với code nên không tự cập nhật.

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
Đăng ký máy gán người quét đầu tiên làm chủ; chia sẻ thêm quyền nhân viên.

```sql
-- Máy do user 1 quản lý
SELECT m.* FROM machines m
JOIN machine_managers mm ON mm.machine_id = m.machine_id
WHERE mm.user_id = 1;
```

## File quản lý dữ liệu máy

Schema dùng chung ở đây gồm máy và quyền quản lý. Module chia sẻ tự giữ bảng mã mời.

| File | Nội dung |
| --- | --- |
| `machine_read.py` | Tra danh tính máy và quyền quản lý dùng chung |
| `machine_write.py` | Xóa quyền nhân viên, dùng cho thu hồi và tự rời máy |
| `machine_write.py` → `add_machine()`, `set_owner()` | Tạo máy và gán chủ |
| `machine_share_store.py`, `machine_share_schema.sql` | SQL mã mời, danh sách/thêm nhân viên; init_db khởi tạo schema chia sẻ máy |
| `service/dashboard_sync/machinelist_sync/machine_list_{get,rename,remove}.py` | SQL riêng của danh sách máy, đổi tên và xóa máy |

Transaction do flow sở hữu; các bước đọc quyền và ghi liên quan dùng cùng `conn`.
`init_db` khởi tạo schema tài khoản, máy và mã mời; giữ dữ liệu hiện có khi chạy lại.
