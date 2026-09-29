# Kho nguyên liệu và nạp kho

App xem kho hoặc yêu cầu nạp. Máy giữ dữ liệu kho; server chỉ xác thực và chuyển lệnh/kết quả.

## API và gói tin

Các gói gửi bằng POST là JSON. GET dùng query trên URL. Token thuộc app; product_key thuộc máy nếu API yêu cầu. Các ví dụ trường dữ liệu minh họa cấu trúc, không phải giá trị thực.

| Phương thức | Route | Ai gọi | Gửi lên | Nhận về |
| --- | --- | --- | --- | --- |
| POST | /app/nhan-kho | App | token, machine_id, version (mặc định 0) | status, version; ingredients khi status=ok |
| POST | /app/nap-kho | App | token, machine_id, target, value | kết quả nạp từ máy, có thể kèm warning |
| POST | /machine/hoi-lenh | Máy | product_key | lenh hoặc null |
| POST | /machine/tra-ket-qua | Máy | product_key, id, ket_qua | da_nhan: true |

## A. Lấy kho

### 1. App yêu cầu dữ liệu kho

POST `/app/nhan-kho` với `{token, machine_id, version: 0}`. App đã có kho thì gửi version đang giữ.

Hàm tham gia:

- App receiveIngredients(): gửi yêu cầu.
- Server machine_ingredient_main.handle(): nhận URL.

### 2. Server kiểm và giao lệnh

Server kiểm phiên/quyền và version, đặt lệnh `{instruction: "nhan_kho", data: {version}}`. Máy POST `/machine/hoi-lenh` với `{product_key}` để lấy lệnh trong response.

Hàm tham gia:

- Server machine_ingredient_get.nhan_kho() / check_access() / is_version() / send(): kiểm và giao lệnh.
- Máy poll_command(): lấy lệnh.

### 3. Máy đọc kho và trả kết quả

Phiên bản khớp thì `{status: "up_to_date", version}`; khác thì `{status: "ok", version, ingredients}`. Máy POST `/machine/tra-ket-qua` với `{product_key, id, ket_qua}`.

Hàm tham gia:

- Máy nhan_kho() / read_ingredients() / version_of(): đọc và so phiên bản.
- Máy send_result(): gửi kết quả.

### 4. Server trả kho và app hiển thị

Server trả ket_qua cho POST ở bước 1. App cập nhật khi ok, giữ kho hiện tại khi up_to_date. Dữ liệu kho trả JSON trực tiếp, không dùng packet nén của menu.

Hàm tham gia:

- Server deliver() / send() / send_json(): chuyển kết quả đến app.


## B. Nạp kho

### 1. App gửi yêu cầu nạp

POST `/app/nap-kho` với `{token, machine_id, target, value}`. target là ID nguyên liệu hoặc "all"; value là "full" hoặc số gram. target="all" chỉ chấp nhận value="full".

Hàm tham gia:

- App refill(): gửi yêu cầu nạp.
- Server machine_ingredient_refill.nap_kho() / is_refill(): kiểm quyền và gói.

### 2. Server giao lệnh; máy nạp dữ liệu

Máy nhận `{instruction: "nap_kho", data: {target, value}}` qua `/machine/hoi-lenh`, kiểm tham số và cập nhật kho. Sau đó dựng lại menu màn bán hàng.

Hàm tham gia:

- Server send(): giao lệnh.
- Máy nap_kho() / check_refill() / refill_ingredient() / republish_store_menu(): kiểm, nạp và dựng menu.

### 3. Máy trả kết quả; app tải kho mới

Máy gửi `{product_key, id, ket_qua}` lên `/machine/tra-ket-qua`. Server trả kết quả cho request nạp ban đầu; app tải lại kho. Nếu dựng menu thất bại sau khi đã ghi kho, kết quả có warning; dữ liệu nạp đã được ghi.

Hàm tham gia:

- Máy send_result(): trả kết quả.
- Server deliver() / send_json(): phản hồi app.


## Nhánh lỗi và lưu ý

Gói sai trả 400; hết phiên 401; thiếu quyền 403; offline 503; máy lỗi/timeout 502. Luồng nạp hiện không có cơ chế conflict phiên bản như cập nhật menu.

## Cấu trúc và cách đọc

```text
ingredient_sync/
    machine_ingredient_main.py     nhận HTTP, chọn luồng, trả response
    machine_ingredient_get.py      kiểm version, giao lệnh lấy kho
    machine_ingredient_refill.py   kiểm target/value, giao lệnh nạp kho
    README.md
    INGREDIENT_SYNC_FLOW.html
    __init__.py
```

Cửa vào `machine_ingredient_main.handle(request)` được đăng ký trong
`server/main.py`. Body JSON tối đa 4096 byte; JSON sai trả `{loi}` với HTTP 400.

| File | Input | Xử lý và output |
| --- | --- | --- |
| `machine_ingredient_main.py` | HTTP POST | Chọn route, đọc JSON và gửi `(body, status)` do luồng trả về |
| `machine_ingredient_get.py` | `{token, machine_id, version?}` | Kiểm quyền owner/manager → version nguyên 0..2^32-1, mặc định 0 → send nhan_kho với `{version}` |
| `machine_ingredient_refill.py` | `{token, machine_id, target, value}` | Kiểm quyền owner/manager → is_refill → send nap_kho với `{target, value}` |

Mỗi file luồng chứa phần validate riêng và comment theo bước. Bool không được
coi là số. Target là ID nguyên dương hoặc `"all"`; value là `"full"` hoặc số gram
0..99999999.99. Nạp toàn bộ chỉ nhận `"full"`.

`check_access` dùng chung tại `server/lib/machine/machine_access.py`; `send` dùng
hộp thư tại `server/lib/machine/machine_transport.py`. Token chỉ dùng ở server.
Hai luồng trả nguyên kết quả máy và HTTP status từ transport, bao gồm warning.
Response trả trên request app ban đầu; server không lưu kho hay tạo hộp thư riêng.

## Kiểm tra

Chạy từ `androidv0.1`:

```sh
python -m unittest tests.python.test_server tests.python.test_server_modules
python -m unittest tests.python.test_machine_relay
```
