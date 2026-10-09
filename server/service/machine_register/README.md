# Đăng ký máy

App lấy tên máy và product key bằng QR hoặc Bluetooth, rồi gửi một request đăng ký lên server. Người đăng ký đầu tiên trở thành chủ máy.

## API và gói tin

Các gói gửi bằng POST là JSON. GET dùng query trên URL. Token thuộc app; product_key thuộc máy nếu API yêu cầu. Các ví dụ trường dữ liệu minh họa cấu trúc, không phải giá trị thực.

| Phương thức | Route | Ai gọi | Gửi lên | Nhận về |
| --- | --- | --- | --- | --- |
| POST | /app/user/machine/register | App | token, machine_name, product_key | valid, registered, created, machine_id, message |

## A. Lấy gói thông tin máy

### 1. Người dùng chọn QR hoặc Bluetooth

QR chứa gói thông tin máy. Với Bluetooth, app tìm máy gần đó và kết nối để nhận gói. Đây là giao tiếp cục bộ, chưa gọi API đăng ký server.

Hàm tham gia:

- App parseMachineQr(): đọc gói QR.
- App scan() / connect(): tìm và kết nối Bluetooth.
- Máy run_server() / handle_connection(): cung cấp gói pairing.

### 2. App đọc tên và product key

App lấy machine_name/product_key từ gói pairing rồi chuẩn bị request. QR chia sẻ quyền là loại gói khác, không dùng để đăng ký máy mới.

Hàm tham gia:

- App parseMachineQr(): phân biệt loại gói.
- App registerMachine(): chuẩn bị dữ liệu đăng ký.


## B. Đăng ký trên server

### 1. App gửi gói đăng ký

POST `/app/user/machine/register` với `{token, machine_name, product_key}`. Token thuộc người dùng đang đăng nhập.

Hàm tham gia:

- App registerMachine() / ServerClient.account(): gửi JSON kèm token.

### 2. Server kiểm thông tin và gán chủ

Server kiểm tên/key và phiên đăng nhập, tìm máy theo hash product key. Máy mới thì tạo bản ghi; máy chưa có chủ thì gán người gọi làm chủ. Cùng chủ gửi lại thì trả cùng ID; máy thuộc người khác thì từ chối và yêu cầu chủ chia sẻ.

Hàm tham gia:

- Server machine_register_main.handle() / receive_register(): nhận và điều phối.
- Server check_machine() / check_login(): kiểm thông tin và phiên.
- Server find_id_by_key_hash() / get_owner_id() / add_machine() / set_owner(): tìm máy và lưu quyền trong transaction.

### 3. Server trả ID máy và app tải danh sách

Response thành công: `{valid: true, registered: true, created, machine_id, message}`. App quay về dashboard và gọi `/app/user/machine/list` với `{token}` để cập nhật danh sách. Không có request xác minh đăng ký máy thứ hai.

Hàm tham gia:

- Server send_json(): trả response.
- App loadMyMachines(): tải lại danh sách máy.


## Nhánh lỗi và lưu ý

Product key không được trả trong danh sách máy; database lưu hash key. Đăng ký máy không cần máy online nếu app đã có gói pairing. Nhánh lỗi trả valid=false/message hoặc login_required khi phiên hết hạn.

## Cấu trúc và cách đọc

- `machine_register_main.py`: cửa vào `handle(request)`, ánh xạ route và đọc/trả JSON qua lib; body tối đa 4096 byte.
- `machine_register_process.py`: kiểm dữ liệu, kiểm phiên, băm key, điều phối transaction tìm/tạo máy và gán chủ.
- `server/database/machine/machine_read.py`: `find_id_by_key_hash()` và `get_owner_id()` đọc trong transaction của tác vụ.
- `server/database/machine/machine_write.py`: `add_machine()` tạo ID `fm_` + UUID và lưu máy; `set_owner()` lưu quyền chủ.

SQL/schema nằm trong database. Các hàm ghi nhận cùng `conn`, không tự commit.
`BEGIN IMMEDIATE` được thực hiện trước khi tìm máy, bảo đảm request đồng thời
cùng key chỉ tạo một máy. Tạo máy và gán chủ cùng commit/rollback.
Schema máy và index do `server/database/machine/init_db.py` khởi tạo/nâng cấp,
giữ dữ liệu hiện có khi chạy lại.

Tên/key được kiểm trước phiên đăng nhập: tên tối đa 150 ký tự, key tối đa 1024 ký tự,
đều phải là chuỗi và không chỉ chứa khoảng trắng. Tên được strip khi tạo máy;
key được băm SHA-256 nguyên giá trị. Gửi lại cùng key không đổi tên máy.
Trường `type` có thể gửi kèm, không bắt buộc.

Response trả trên request POST ban đầu: thành công HTTP 200; lỗi dữ liệu/phiên/quyền
HTTP 400; lỗi SQLite HTTP 503. Không có request xác minh đăng ký thứ hai.
Route `/app/xac-minh-dang-ky-may` đã bỏ. Không gửi ID hoặc lệnh xuống máy;
máy dùng product key khi heartbeat/nhận lệnh.

Hiện chưa đối chiếu key với danh sách key nhà máy, chưa gán cửa hàng hoặc cấp credential.
Đây là giới hạn hiện tại, không thay đổi trong refactor.

```sh
python -m unittest tests.python.test_machine_register tests.python.test_server_modules -v
```
