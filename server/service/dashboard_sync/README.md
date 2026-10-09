# Dashboard: chọn máy, menu và kho

Dashboard kết hợp danh sách máy, trạng thái kết nối, menu và kho. Mỗi mini-module có tài liệu riêng; bảng này là các API app sử dụng.

## API và gói tin

Các gói gửi bằng POST là JSON. GET dùng query trên URL. Token thuộc app; product_key thuộc máy nếu API yêu cầu. Các ví dụ trường dữ liệu minh họa cấu trúc, không phải giá trị thực.

| Phương thức | Route | Ai gọi | Gửi lên | Nhận về |
| --- | --- | --- | --- | --- |
| POST | /app/user/machine/list | App | token | valid, machines |
| GET | /app/machine/status/get | App | machine_id trong query | trạng thái heartbeat |
| POST | /app/machine/name/update | Chủ máy | token, machine_id, name | valid, name, message |
| POST | /app/user/machine/remove | App | token, machine_id | valid, deleted, message |
| POST | /app/machine/menu/get | App | token, machine_id, menu_version | status, menu_version, packet khi có dữ liệu mới |
| POST | /app/machine/menu/update | App | token, machine_id, menu_version, thay_doi | status: ok/conflict, menu_version, packet |
| POST | /app/machine/ingredient/get | App | token, machine_id, version | status, version, ingredients khi có dữ liệu mới |
| POST | /app/machine/ingredient/refill | App | token, machine_id, target, value | kết quả nạp, warning tùy trường hợp |

## A. Mở dashboard và chọn máy

### 1. App lấy danh sách máy

POST `/app/user/machine/list` với `{token}`. Server trả `{valid, machines}`; app chọn máy và hiển thị tên/quyền.

Hàm tham gia:

- App loadMyMachines(): lấy và áp dụng danh sách.
- Server list_my_machines(): kiểm phiên và đọc máy.

### 2. App xem trạng thái kết nối

GET `/app/machine/status/get?machine_id=...`. Trạng thái được tính từ heartbeat, không bảo đảm request nghiệp vụ tiếp theo sẽ thành công.

Hàm tham gia:

- App status(): hỏi trạng thái.
- Server handle_get() / is_online(): đọc heartbeat.


## B. Đọc menu và kho

### 1. App gửi yêu cầu đọc dữ liệu

Menu: POST `/app/machine/menu/get` với `{token, machine_id, menu_version}`. Kho: POST `/app/machine/ingredient/get` với `{token, machine_id, version}`. Hai luồng độc lập, cùng chọn một máy.

Hàm tham gia:

- App receiveMenu() / receiveIngredients(): gửi yêu cầu.
- Server nhan_menu() / nhan_kho(): kiểm và giao lệnh.

### 2. Máy nhận lệnh và trả dữ liệu

Máy gọi `/machine/command/poll` rồi gửi kết quả lên `/machine/result/send`. Bản không đổi trả up_to_date; bản mới trả menu nén hoặc kho JSON. Server phản hồi trên request app ban đầu.

Hàm tham gia:

- Server send() / take() / deliver(): chuyển lệnh và kết quả.
- Máy nhan_menu() / nhan_kho(): đọc dữ liệu.

### 3. App cập nhật màn hình

App đọc kết quả, giữ bản cũ nếu up_to_date. Đổi máy hoặc đóng dashboard thì bỏ kết quả cũ trả về muộn.

Hàm tham gia:

- App ProductsSync.load() / reset(): quản lý dữ liệu menu.
- App dashboard controller: quản lý máy đang chọn.


## C. Thay đổi dữ liệu

### 1. App gửi tác vụ cần làm

Đổi tên/gỡ máy gửi API quản lý máy. Cập nhật món gửi `/app/machine/menu/update`; nạp kho gửi `/app/machine/ingredient/refill`. Các gói được liệt kê ở bảng đầu.

Hàm tham gia:

- Server rename_machine() / remove_machine(): sửa dữ liệu quản lý trên server.
- Server cap_nhat_menu() / nap_kho(): chuyển tác vụ dữ liệu xuống máy.

### 2. App đọc kết quả và tải lại khi cần

Đổi tên/gỡ máy làm mới danh sách. Menu conflict tải bản mới và yêu cầu sửa lại. Nạp xong tải kho mới; warning dựng menu được giữ trong kết quả.

Hàm tham gia:

- App loadMyMachines() / forgetMachine(): làm mới máy.
- App ProductsSync._send() / _apply(): đọc kết quả cập nhật món.


## Nhánh lỗi và lưu ý

Chi tiết: MACHINELIST_FLOW.html, MENU_SYNC_FLOW.html và INGREDIENT_SYNC_FLOW.html trong các folder mini-module tương ứng. Trang Orders hiện là dữ liệu demo; không mô tả như feature đồng bộ server.

## Tài liệu kỹ thuật và vận hành

# Đồng bộ dashboard

Mỗi tab dashboard của app là một folder, **chia theo tab, không chia theo nguồn dữ liệu**:

| Folder | Tab | Route | Dữ liệu ở đâu |
| --- | --- | --- | --- |
| `menu_sync/` | Menu | `/app/machine/menu/get`, `/app/machine/menu/update` | của máy, hỏi xuống qua hộp thư |
| `ingredient_sync/` | Kho | `/app/machine/ingredient/get`, `/app/machine/ingredient/refill` | của máy, hỏi xuống qua hộp thư |
| `machinelist_sync/` | Máy | `/app/user/machine/list`, `/app/machine/name/update`, `/app/user/machine/remove`, GET `/app/machine/status/get` | của server (bảng `machines`, giờ heartbeat) |

Vai trò được phép nằm trong flow của mỗi module (`QUYEN_MENU`, `QUYEN_KHO`,
`QUYEN_NAP_KHO`). `server/lib/machine/machine_access.py` cung cấp `check_access(data, roles)`:
token → người dùng → có quản lý máy → vai trò đủ quyền.

## Tab dữ liệu máy (Menu, Kho)

Server không lưu dữ liệu máy. Module kiểm quyền và dạng gói, rồi gọi
`server.lib.machine.machine_transport.send(machine_id, instruction, data)`: lệnh nằm trong hộp thư
tới khi máy long-poll lấy, máy trả kết quả, server chuyển nguyên cho app.

```
App ─ POST /app/machine/ingredient/get {token, machine_id, version}
 └→ ingredient_sync: check_access → is_version → send("nhan_kho", {version})
      Máy ─ /machine/command/poll → {id, instruction: "nhan_kho", data: {version}}
      Máy: version trùng → {"status": "up_to_date", "version"}
           khác         → {"status": "ok", "version", "ingredients": [...]}
      Máy ─ /machine/result/send {id, ket_qua}
 ←─ 200 + kết quả máy
```

`version` là CRC32 của dữ liệu do máy tính; app chưa có dữ liệu gửi `0`. Menu làm y như
vậy với `menu_version`, kết quả thêm gói `packet` = base64(zlib(JSON)), xem
`machine/menu_sync/machine_menu_pack.py`.

### Route

| Route | Gửi | Kết quả |
| --- | --- | --- |
| `/app/machine/menu/get` | `token`, `machine_id`, `menu_version` | `{status: up_to_date \| ok, menu_version, packet?}` |
| `/app/machine/menu/update` | `token`, `machine_id`, `menu_version`, `thay_doi: [{drink_id, available?, price?}]` | `{status: ok \| conflict, menu_version, packet}`; `conflict` = app đang giữ bản cũ, máy không ghi |
| `/app/machine/ingredient/get` | `token`, `machine_id`, `version` | `{status: up_to_date \| ok, version, ingredients?}` |
| `/app/machine/ingredient/refill` | `token`, `machine_id`, `target` (id hoặc `"all"`), `value` (`"full"` hoặc số gram, số gram chỉ khi `target` là id) | kết quả `refill()` của máy, kèm `warning` nếu dựng lại menu màn bán hàng lỗi |

`ingredients`: `ingredient_id`, `name`, `amount`, `max_gram`, `max_set`, `pump_no`,
`in_stock`. `max_set = false` nghĩa là máy chưa khai báo mức tối đa, `max_gram` đang là
giá trị mặc định; app hiện dòng cảnh báo.

### Lỗi

Thân lỗi `{"loi": ...}`:

| Status | Khi nào |
| --- | --- |
| 400 | gói sai dạng (version âm, `thay_doi` rỗng hoặc có cột lạ, `target`/`value` sai) |
| 401 | token sai/hết hạn (kèm `login_required: true`) |
| 403 | không quản lý máy này, hoặc vai trò không đủ quyền |
| 503 | máy offline (không heartbeat trong 15 giây) |
| 502 | máy báo lỗi (MySQL, món không có trên máy...) hoặc không trả kết quả trong 20 giây |

## Mã nguồn

| | Server | Máy | App |
| --- | --- | --- | --- |
| Menu | `menu_sync/` | `machine/menu_sync/` (SQLite `machine/database/database.db`) | `lib/feature/machine_menu/machine_menu_sync.dart` |
| Kho | `ingredient_sync/` | `machine/ingredient_sync/` (MySQL của `version1.0`) | `lib/feature/machine_ingredient/machine_ingredient_sync.dart` |
| Máy | `machinelist_sync/` | — | `lib/feature/dashboard/dashboard_controller.dart` |

Module tự chọn cách chia file, xem `androidv0.1/MODULE_PATTERN.md`. Chạy server:
`python -m server.main`.

## Cửa vào các submodule phía server

| Submodule | Cửa vào | File tác vụ |
| --- | --- | --- |
| Máy | `machinelist_sync/machine_list_main.py` | `machine_list_get.py`, `machine_list_rename.py`, `machine_list_remove.py` |
| Menu | `menu_sync/machine_menu_main.py` | `machine_menu_get.py`, `machine_menu_update.py` |
| Kho | `ingredient_sync/machine_ingredient_main.py` | `machine_ingredient_get.py`, `machine_ingredient_refill.py` |

`server/main.py` đăng ký trực tiếp ba cửa vào. Mỗi luồng chứa validate và SQL
riêng; phiên, quyền, HTTP và vận chuyển lệnh dùng helper chung. Mỗi module có
README và HTML flow trong cùng folder.
