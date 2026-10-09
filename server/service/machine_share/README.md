# Chia sẻ máy và thu hồi quyền

Chủ máy tạo mã mời; nhân viên nhận mã để có quyền quản lý. Feature này làm việc với server/database, không giao lệnh xuống máy.

## API và gói tin

Các gói gửi bằng POST là JSON. GET dùng query trên URL. Token thuộc app; product_key thuộc máy nếu API yêu cầu. Các ví dụ trường dữ liệu minh họa cấu trúc, không phải giá trị thực.

| Phương thức | Route | Ai gọi | Gửi lên | Nhận về |
| --- | --- | --- | --- | --- |
| POST | /app/machine/share/create | Chủ máy | token, machine_id | valid, code, machine_id, expires_in, message |
| POST | /app/machine/share/accept | Nhân viên | token, code | valid, machine_id, machine_name, message |
| POST | /app/machine/staff/list | Chủ máy | token, machine_id | valid, staff |
| POST | /app/machine/staff/revoke | Chủ máy | token, machine_id, user_id | valid, message |

## A. Mời nhân viên

### 1. Chủ gửi yêu cầu tạo mã

POST `/app/machine/share/create` với `{token, machine_id}`. Server kiểm người gọi là chủ, tạo mã và lưu hash. Response `{valid, code, machine_id, expires_in, message}`.

Hàm tham gia:

- App createShare(): xin mã mời.
- Server create_invite() / check_login() / is_machine_id() / replace_invite(): kiểm quyền và lưu mã.

### 2. Chủ đưa mã cho nhân viên

App hiển thị mã bằng QR; cũng có thể chuyển gói chia sẻ qua Bluetooth. Mã hết hạn sau 5 phút và dùng một lần. Tạo mã mới làm mã cũ chưa dùng hết hiệu lực.

Hàm tham gia:

- App createCode(): hiển thị mã mời.
- App parseMachineQr(): đọc gói chia sẻ ở phía nhận.

### 3. Nhân viên gửi mã nhận quyền

POST `/app/machine/share/accept` với `{token, code}`. Server kiểm mã còn hạn/chưa dùng, đánh dấu dùng và thêm quyền manager trong transaction. Response `{valid, machine_id, machine_name, message}`.

Hàm tham gia:

- App acceptShare(): gửi mã nhận quyền.
- Server accept_invite() / find_valid_invite() / mark_used() / add_manager(): xác minh và cấp quyền.

### 4. App cập nhật danh sách máy

App gọi POST `/app/user/machine/list` với `{token}`, nhận `{valid, machines}` rồi hiển thị máy mới. Chủ nhận mã của mình vẫn giữ quyền owner.

Hàm tham gia:

- App loadMyMachines(): tải danh sách mới.
- Server my_machines(): trả máy người dùng quản lý.


## B. Xem và thu hồi nhân viên

### 1. Chủ lấy danh sách nhân viên

POST `/app/machine/staff/list` với `{token, machine_id}`. Server kiểm quyền chủ rồi trả `{valid, staff}`.

Hàm tham gia:

- App listStaff() / loadStaff(): lấy và hiển thị nhân viên.
- Server list_staff(): kiểm quyền và đọc danh sách.

### 2. Chủ thu hồi quyền của một người

POST `/app/machine/staff/revoke` với `{token, machine_id, user_id}`. user_id là nhân viên bị thu hồi. Server xóa quyền manager, trả `{valid, message}`. Nhân viên không còn quyền với máy; danh sách app cập nhật khi tải lại.

Hàm tham gia:

- App revokeStaff() / revoke(): gửi yêu cầu và làm mới danh sách.
- Server revoke_staff() / remove_manager(): kiểm quyền và xóa quyền nhân viên.


## Nhánh lỗi và lưu ý

Nhân viên không được tự tạo mã hoặc xem/thu hồi nhân viên. Mã dùng rồi/hết hạn bị từ chối. Thu hồi không xóa tài khoản và không xóa quyền owner.

## Cấu trúc và cách đọc

Cửa vào: `machine_share_main.py` → `handle(request)` đọc JSON tối đa 4096 byte,
chọn tác vụ và trả response trên request POST ban đầu. Thành công trả HTTP 200,
lỗi nghiệp vụ/JSON trả 400, lỗi SQLite trả 503. Lỗi phiên có `login_required: true`.

| File trong module | Trách nhiệm |
| --- | --- |
| `machine_share_main.py` | Ánh xạ bốn route và xử lý HTTP qua helper lib |
| `machine_share_create.py` | Kiểm phiên/mã máy/quyền chủ, sinh mã, tính hạn và gọi database lưu hash |
| `machine_share_accept.py` | Kiểm phiên/mã mời, điều phối xác minh và cấp quyền trong transaction |
| `machine_staff_list.py` | Kiểm phiên/mã máy/quyền chủ, gọi database lấy nhân viên |
| `machine_staff_revoke.py` | Kiểm phiên/dữ liệu/quyền chủ, gọi database thu hồi manager |

SQL nằm trong `server/database/machine/machine_share_store.py`;
thu hồi dùng `server/database/machine/machine_write.py` → `remove_manager()`.
Các hàm database nhận cùng `conn` do tác vụ cung cấp, không tự mở kết nối hoặc commit.
Nhận mã giữ `BEGIN IMMEDIATE` trước khi tìm mã; đánh dấu dùng và thêm manager
cùng commit/rollback để một mã chỉ có một người nhận thành công.

`server/database/machine/init_db.py` khởi tạo `machine_share_schema.sql` sau bảng
users/machines. Khởi tạo lại giữ dữ liệu hiện có; module không có hook `setup()`.

Mã tạo từ 24 byte ngẫu nhiên (32 ký tự), lưu SHA-256. Dạng mã nhận chấp nhận chuỗi
20–100 ký tự như trước. QR/Bluetooth dùng `{"type":"share","code":"..."}`;
[xem gói chia sẻ](../../../app/flutter_app/lib/feature/machine_share/QR.md).
Danh sách máy `/app/user/machine/list` thuộc module `machinelist_sync`.

```sh
python -m unittest tests.python.test_machine_share tests.python.test_server_modules -v
```
