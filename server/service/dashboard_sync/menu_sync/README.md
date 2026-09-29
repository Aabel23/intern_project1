# Menu sync — luồng app, server và máy

Feature có hai việc: lấy menu hiện tại từ máy và cập nhật giá/trạng thái món.
Server chuyển yêu cầu/kết quả; máy giữ dữ liệu menu. Ví dụ ID và phiên bản dưới
đây là minh họa. `packet` là chuỗi chứa menu đã nén, không phải URL.

## A. App lấy menu

### 1. App gửi yêu cầu lấy menu lên server

POST `/app/nhan-menu`, body:

```json
{"token": "token_app", "machine_id": "may_01", "menu_version": 0}
```

Token xác định người dùng, machine_id chọn máy. menu_version là phiên bản app
đang giữ; app chưa có menu gửi 0. Server cũng mặc định 0 nếu thiếu trường này.

Hàm tham gia:

- App `ProductsSync.load()`: bắt đầu tải menu cho máy đang chọn.
- App `receiveMenu()`: tạo yêu cầu lấy menu.
- App `ServerClient.machineData()`: gửi dữ liệu máy kèm token.

### 2. Server nhận yêu cầu và kiểm tra

Server khớp URL, đọc JSON rồi kiểm phiên đăng nhập, quyền với máy và phiên bản.
Nếu không hợp lệ, server trả lỗi cho app ngay; chưa giao lệnh xuống máy.

Hàm tham gia:

- Server `machine_menu_main.handle()`: cửa vào menu_sync.
- Server `handle_routes()` / `read_json()`: chọn luồng và đọc gói JSON.
- Server `machine_menu_get.nhan_menu()`: điều phối yêu cầu lấy menu.
- Server `check_access()`: kiểm phiên và quyền máy.
- Server `is_menu_version()`: kiểm phiên bản là số nguyên 32 bit hợp lệ.

### 3. Server chuẩn bị lệnh; máy hỏi server để nhận lệnh

Server đặt lệnh vào hộp thư và chờ kết quả. Máy POST `/machine/hoi-lenh` với:

```json
{"product_key": "key_may"}
```

Server trả lệnh trong response của request này:

```json
{"lenh": {"id": 123, "instruction": "nhan_menu", "data": {"menu_version": 0}}}
```

Server không gọi URL riêng trên máy. Token app không được gửi xuống máy.
Nếu chưa có lệnh, máy chờ hoặc nhận `{"lenh": null}` rồi hỏi tiếp.

Hàm tham gia:

- Server `send()`: đưa lệnh vào hộp thư, chờ kết quả.
- Máy `poll()` / `poll_command()`: hỏi server lấy lệnh.
- Server `machine_link_process.poll()` / `take()`: xác thực máy và trả lệnh.

### 4. Máy đọc menu và chuẩn bị kết quả

Máy so menu_version app gửi với phiên bản dữ liệu hiện tại:

- Giống nhau: trả `{"status": "up_to_date", "menu_version": 456}`, không gửi lại menu.
- Khác nhau: đóng gói menu và trả
  `{"status": "ok", "menu_version": 456, "packet": "chuoi_menu_da_nen"}`.

Hàm tham gia:

- Máy `handle_command()`: chọn chức năng theo tên lệnh.
- Máy `machine_menu_sync.nhan_menu()`: xử lý lấy menu.
- Máy `read_drinks()` / `menu_version_of()`: đọc món và tính phiên bản.
- Máy `reply_with_menu()` / `build_packet()` / `encode_packet()`: đóng gói menu.

### 5. Máy gửi kết quả lên server

POST `/machine/tra-ket-qua`, ví dụ:

```json
{"product_key": "key_may", "id": 123, "ket_qua": {"status": "ok", "menu_version": 456, "packet": "chuoi_menu_da_nen"}}
```

ID giúp server ghép kết quả với đúng lệnh đang chờ. Server xác thực máy rồi
phản hồi `{"da_nhan": true}` cho request gửi kết quả của máy.

Hàm tham gia:

- Máy `reply()` / `send_result()`: gửi kết quả cùng ID lệnh.
- Server `machine_link_process.send_result()` / `deliver()`: chuyển kết quả
  đến yêu cầu app đang chờ của đúng máy.

### 6. Server trả menu cho app; app hiển thị

Server trả nguyên `ket_qua` làm response cho POST `/app/nhan-menu` ở bước 1.
Không có link gửi menu riêng và app không cần tạo request khác để nhận kết quả.
Nếu `ok`, app giải nén packet và cập nhật danh sách; nếu `up_to_date`, giữ menu cũ.

Hàm tham gia:

- Server `send()`: nhận kết quả máy và kết thúc chờ.
- Server `send_json()`: trả HTTP response cho app.
- App `_apply()` / `decodeMenuPacket()`: đọc gói menu, cập nhật món và phiên bản.
- App `ProductsSync.load()`: cập nhật trạng thái tải/lỗi cho giao diện.

## B. App cập nhật món trong menu

### 1. App gửi các món cần sửa lên server

POST `/app/cap-nhat-menu`, body ví dụ:

```json
{"token": "token_app", "machine_id": "may_01", "menu_version": 456, "thay_doi": [{"drink_id": 1001, "available": false}, {"drink_id": 1002, "price": 35000}]}
```

Chỉ sửa `available` và/hoặc `price`. UI hiện dùng bật/tắt món; API cũng hỗ trợ giá.
menu_version là phiên bản app đang sửa, không được bỏ qua.

Hàm tham gia:

- App `setAvailable()` / `_send()`: tạo thay đổi và bắt đầu cập nhật.
- App `updateMenu()` / `ServerClient.machineData()`: gửi gói kèm token.

### 2. Server nhận và kiểm tra toàn bộ gói

Server kiểm phiên/quyền, phiên bản, số dòng, ID món và giá trị sửa. Một dòng sai
thì từ chối cả gói. Server chưa biết ID đó có thực sự tồn tại trên máy hay không;
phần này máy kiểm ở bước 4.

Hàm tham gia:

- Server `machine_menu_main.handle()` / `handle_routes()`: nhận URL và đọc JSON.
- Server `machine_menu_update.cap_nhat_menu()` / `check_access()`: kiểm quyền và điều phối.
- Server `is_menu_version()` / `is_changes()` / `is_change()`: kiểm phiên bản và từng dòng.
- Server `is_drink_id()` / `is_price()` / `is_number()` / `is_available()`:
  kiểm kiểu và giới hạn giá trị.

### 3. Server giao lệnh cập nhật cho máy đang hỏi lệnh

Máy vẫn POST `/machine/hoi-lenh` với product_key như luồng lấy menu.
Response server chứa:

```json
{"lenh": {"id": 124, "instruction": "cap_nhat_menu", "data": {"menu_version": 456, "thay_doi": [{"drink_id": 1001, "available": false}, {"drink_id": 1002, "price": 35000}]}}}
```

Hàm tham gia:

- Server `send()`: đưa lệnh cập nhật vào hộp thư.
- Máy `poll()` / `poll_command()`: hỏi lấy lệnh.
- Server `machine_link_process.poll()` / `take()`: trả lệnh cho đúng máy.

### 4. Máy kiểm phiên bản và cập nhật

- Phiên bản đã đổi: không ghi thay đổi, trả `conflict` kèm menu mới nhất.
- Phiên bản khớp: kiểm tất cả món, ghi trong một transaction rồi trả `ok`
  kèm menu sau cập nhật. Một thay đổi không hợp lệ thì không ghi cả gói.

Hàm tham gia:

- Máy `handle_command()` / `machine_menu_sync.cap_nhat_menu()`: chọn và xử lý cập nhật.
- Máy `check_menu_version()` / `menu_version_of()`: kiểm và so phiên bản.
- Máy `check_changes()` / `update_drink()`: kiểm món và ghi dữ liệu.
- Máy `read_drinks()` / `reply_with_menu()`: lấy menu mới nhất và đóng gói kết quả.

### 5. Máy gửi kết quả cập nhật về server

POST `/machine/tra-ket-qua`, body:

```json
{"product_key": "key_may", "id": 124, "ket_qua": {"status": "ok", "menu_version": 789, "packet": "chuoi_menu_da_nen"}}
```

Nếu xung đột, status là `conflict`, packet chứa menu hiện tại và thay đổi chưa được ghi.

Hàm tham gia:

- Máy `reply()` / `send_result()`: gửi kết quả.
- Server `machine_link_process.send_result()` / `deliver()`: ghép kết quả với lệnh chờ.

### 6. Server trả kết quả cho app; app cập nhật giao diện

Server trả kết quả trên request `/app/cap-nhat-menu` ở bước 1. App đọc menu mới.
Nếu `conflict`, app cũng tải menu từ packet nhưng báo người dùng thử sửa lại.

Hàm tham gia:

- Server `send()` / `send_json()`: kết thúc chờ và trả HTTP response.
- App `_send()` / `_apply()` / `decodeMenuPacket()`: cập nhật menu, báo xung đột nếu có.

## Khi có lỗi

- JSON/gói tin sai: HTTP 400, `{"loi": "..."}`.
- Phiên hết hạn: HTTP 401, có `login_required: true` để app yêu cầu đăng nhập lại.
- Không có quyền máy: HTTP 403.
- Máy offline: HTTP 503; máy báo lỗi hoặc chờ quá hạn: HTTP 502.
- Conflict phiên bản: HTTP 200 với status `conflict`, không phải lỗi HTTP.

## Cấu trúc code phía server

```text
menu_sync/
    machine_menu_main.py      # cửa vào HTTP
    machine_menu_get.py       # luồng lấy menu
    machine_menu_update.py    # luồng cập nhật menu
    README.md
```

Packet menu là `base64(zlib(JSON))`, chứa type `menu_sync`, v `1`, menu_version,
generated_at, fields và drinks. Server chuyển nguyên packet; app giải nén để đọc.
