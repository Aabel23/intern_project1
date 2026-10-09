# Danh sách, tên và quyền quản lý máy

App lấy danh sách máy thuộc tài khoản, đổi tên hoặc gỡ quyền. Cổng trạng thái đọc heartbeat của máy.

Xem [bốn sơ đồ luồng của machine list](MACHINE_LIST_DECISION_TREE.html) để theo dõi từng request giữa app, server và máy.

## API và gói tin

Các gói gửi bằng POST là JSON. GET dùng query trên URL. Token thuộc app; product_key thuộc máy nếu API yêu cầu. Các ví dụ trường dữ liệu minh họa cấu trúc, không phải giá trị thực.

| Phương thức | Route | Ai gọi | Gửi lên | Nhận về |
| --- | --- | --- | --- | --- |
| POST | /app/user/machine/list | App | token | valid, machines |
| POST | /app/machine/name/update | Chủ máy | token, machine_id, name | valid, name, message |
| POST | /app/user/machine/remove | Chủ hoặc nhân viên | token, machine_id | valid, deleted, message |
| GET | /app/machine/status/get | App | machine_id trong query URL | trạng thái máy theo heartbeat |

## A. Hiển thị danh sách

### 1. App hỏi danh sách máy

POST `/app/user/machine/list` với `{token}`. Server trả `{valid, machines: [{machine_id, name, role}]}` cho các máy tài khoản có quyền.

Hàm tham gia:

- App loadMyMachines() / myMachines(): gửi yêu cầu và cập nhật danh sách.
- Server list_my_machines(): kiểm phiên và đọc danh sách.

### 2. App xem máy đang online hay offline

GET `/app/machine/status/get?machine_id=...`. Server đọc giờ heartbeat gần nhất để trả trạng thái; không gửi lệnh mới xuống máy.

Hàm tham gia:

- App status(): hỏi trạng thái.
- Server handle_get() / is_online() / last_seen_of(): đọc trạng thái heartbeat.


## B. Đổi tên

### 1. Chủ nhập tên mới và gửi

POST `/app/machine/name/update` với `{token, machine_id, name}`. Server kiểm phiên, mã máy, tên 1–150 ký tự rồi quyền chủ; lưu tên mới và trả `{valid, name, message}`.

Hàm tham gia:

- App renameMachine(): gửi tên đã chọn.
- Server machine_list_rename.rename_machine() / check_login() / is_machine_id() / clean_name() / is_owner(): kiểm và xử lý.

### 2. App hiển thị tên đã đổi

App tải lại `/app/user/machine/list` và cập nhật dòng máy; thất bại thì hiển thị message.

Hàm tham gia:

- App loadMyMachines(): làm mới danh sách.


## C. Gỡ máy hoặc bỏ quản lý

### 1. Người dùng xác nhận gỡ

POST `/app/user/machine/remove` với `{token, machine_id}`. Server kiểm phiên và mã máy, mở transaction với BEGIN IMMEDIATE rồi kiểm quyền. Chủ gọi thì xóa máy cùng quyền và mã mời; nhân viên gọi thì chỉ xóa quyền của chính mình. Response `{valid, deleted, message}`; deleted=true là xóa máy, false là bỏ quyền.

Hàm tham gia:

- App removeMachine(): gửi sau khi xác nhận.
- Server machine_list_remove.remove_machine() / is_owner() / can_manage() / remove_manager(): xác định nhánh và cập nhật database.

### 2. App bỏ máy khỏi giao diện

App làm mới danh sách. Nếu máy đang chọn bị gỡ, app bỏ chọn và xóa menu/kho đang hiển thị. Máy bị chủ xóa cần đăng ký lại trước khi heartbeat được chấp nhận.

Hàm tham gia:

- App forgetMachine() / loadMyMachines(): bỏ dữ liệu máy cũ và làm mới.


## Nhánh lỗi và lưu ý

Nhân viên không đổi tên được dù tự gọi API. Gỡ máy bởi chủ làm mất quyền toàn bộ nhân viên; bỏ quyền bởi nhân viên không xóa máy. GET trạng thái hiện không yêu cầu token; không mô tả nó như API đã kiểm quyền.

## Cấu trúc và cách đọc

```text
machinelist_sync/
    machine_list_main.py     nhận HTTP, chọn luồng, trả response
    machine_list_get.py      danh sách máy và trạng thái heartbeat
    machine_list_rename.py   chủ máy đổi tên
    machine_list_remove.py   chủ xóa máy hoặc nhân viên bỏ quyền
    README.md
    MACHINELIST_FLOW.html
    __init__.py
```

Cửa vào: `machine_list_main.handle(request)` cho POST và `handle_get(request)`
cho GET. Server đăng ký module trực tiếp trong `server/main.py`.

| File | Input | Xử lý và output |
| --- | --- | --- |
| `machine_list_main.py` | HTTP request | Khớp route, đọc JSON/query, gọi luồng và trả JSON trên request ban đầu |
| `machine_list_get.py` | `{token}` hoặc `machine_id` | `list_my_machines` kiểm phiên, SELECT theo user_id, trả `{valid, machines}`; `machine_status` đọc RAM, trả `{machine_id, online, last_seen}` |
| `machine_list_rename.py` | `{token, machine_id, name}` | Kiểm phiên → mã máy → strip tên 1–150 ký tự → quyền chủ → UPDATE; trả `{valid, name, message}` |
| `machine_list_remove.py` | `{token, machine_id}` | Kiểm phiên → mã máy → BEGIN IMMEDIATE → quyền; chủ DELETE máy, nhân viên bỏ quyền; trả `{valid, deleted, message}` |

Các luồng trả thân JSON; cửa vào gắn HTTP 200 khi `valid=true`, 400 khi
`valid=false` (kể cả hết phiên, kèm `login_required=true`). JSON sai hoặc body
ngoài 1–4096 byte trả 400; lỗi SQLite trả 503. GET trạng thái trả 200 và không
kiểm token hoặc dạng mã máy. Mọi phản hồi trả trên request ban đầu.

SQL riêng nằm ngay trong file tác vụ. `machine_read.is_owner/can_manage` kiểm
quyền qua cùng conn của luồng; `machine_write.remove_manager` chỉ xóa quyền
manager của người gọi. `get_connection` commit khi thành công, rollback khi lỗi.
Gỡ máy khóa ghi trước khi đọc quyền, cascade xóa quyền và mã mời. Đổi tên giữ
cách kiểm quyền rồi UPDATE qua cùng conn, không thêm BEGIN IMMEDIATE.

Phiên dùng `server/lib/security/user_session.py`; mã máy dùng
`server/lib/validation/identifier_validate.py`; HTTP và heartbeat dùng lib chung.
Module không chờ máy online; danh sách, đổi tên và gỡ máy đều xử lý trên server.

## Kiểm tra

Chạy từ `androidv0.1`:

```sh
python -m unittest tests.python.test_machine_list tests.python.test_server tests.python.test_server_modules
```
