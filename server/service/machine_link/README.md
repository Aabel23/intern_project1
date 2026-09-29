# Cổng máy: heartbeat, nhận lệnh và trả kết quả

Máy chủ động gọi server. Server dùng chung hộp thư lệnh để kết nối các feature app với máy; không mở endpoint riêng trên máy.

## API và gói tin

Cả ba route nhận POST JSON từ máy, kèm product_key; không dùng token app.

| Phương thức | Route | Ai gọi | Gửi lên | Nhận về |
| --- | --- | --- | --- | --- |
| POST | /machine/heartbeat | Máy | product_key | da_nhan: true |
| POST | /machine/hoi-lenh | Máy | product_key | lenh: {id, instruction, data} hoặc null |
| POST | /machine/tra-ket-qua | Máy | product_key, id, ket_qua | da_nhan: true |

## A. Duy trì kết nối

### 1. Máy báo còn hoạt động

Máy định kỳ POST `/machine/heartbeat` với `{product_key}`. Server xác thực key, ghi thời gian rồi trả `{da_nhan: true}`.

Hàm tham gia:

- Máy run_heartbeat(): gửi heartbeat.
- Server heartbeat() / machine_from_key() / mark_seen(): xác thực và ghi thời gian.


## B. Một lệnh đi từ app đến máy

### 1. App gửi yêu cầu nghiệp vụ

Ví dụ POST `/app/nhan-kho` với `{token, machine_id, version: 0}`. Feature tương ứng kiểm quyền và dữ liệu rồi chuẩn bị lệnh.

Hàm tham gia:

- Server nhan_kho() / check_access(): kiểm yêu cầu app.

### 2. Server đưa lệnh vào hộp thư

Server tạo `{id, instruction: "nhan_kho", data: {version: 0}}`, đặt vào hộp thư đúng máy và chờ kết quả. Máy offline thì app nhận HTTP 503 ngay.

Hàm tham gia:

- Server send() / is_online(): kiểm online, xếp lệnh và chờ.

### 3. Máy hỏi và nhận lệnh

Máy POST `/machine/hoi-lenh` với `{product_key}`. Server trả `{lenh: {id, instruction, data}}`; nếu chưa có lệnh thì chờ tối đa thời gian long-poll và trả lenh=null.

Hàm tham gia:

- Máy poll() / poll_command(): hỏi lệnh.
- Server poll() / take(): trả lệnh cho đúng máy.

### 4. Máy thực hiện và gửi kết quả

Máy chọn feature theo instruction, thực hiện tác vụ rồi POST `/machine/tra-ket-qua` với `{product_key, id, ket_qua}`. Server trả `{da_nhan: true}` cho máy.

Hàm tham gia:

- Máy handle_command() / reply() / send_result(): thực hiện và gửi kết quả.
- Server send_result() / deliver(): chuyển kết quả đúng lệnh/máy.

### 5. Server phản hồi app

Server trả ket_qua cho request nghiệp vụ ban đầu. Lỗi máy/timeout trả HTTP 502; timeout trước khi máy lấy lệnh thì hủy lệnh. Máy đã lấy mà chưa trả: app được yêu cầu tải lại để kiểm tra, không hứa tác vụ chưa chạy.

Hàm tham gia:

- Server send() / timeout_message() / send_json(): kết thúc chờ, xử lý timeout và trả response.


## Nhánh lỗi và lưu ý

Key sai trả HTTP 403. Hộp thư và heartbeat nằm trong RAM; restart mất trạng thái chờ. Máy khác gửi ID không thuộc mình không được chuyển kết quả. Response da_nhan=true không bảo đảm có lệnh đang chờ tương ứng.

## Cấu trúc và ranh giới

| File | Trách nhiệm |
| --- | --- |
| `machine_link_main.py` | Cửa vào `handle(request)`, ánh xạ ba route, đọc JSON và trả HTTP |
| `machine_link_process.py` | Xác minh máy rồi điều phối heartbeat/hỏi lệnh/trả kết quả |
| `server/lib/machine/machine_transport.py` | Hộp thư, ID lệnh, hàng chờ kết quả, khóa, heartbeat và timeout dùng chung |
| `server/database/machine/machine_read.py` | SQL tìm ID máy theo hash product key |

`machine_from_key()` chấp nhận key là chuỗi không trắng, tối đa 1024 ký tự;
băm SHA-256 nguyên giá trị rồi tra database. JSON sai trả 400, key sai/chưa đăng ký
trả 403, lỗi SQLite trả 503. Giới hạn body chung là 1 MB để nhận kết quả Menu/Kho.

### Ai gọi hỏi lệnh và trả kết quả?

`machine/main.py → run()` chạy heartbeat ở thread riêng, còn vòng lặp chính
hỏi lệnh → thực hiện → gửi kết quả. `poll_command()` và `send_result()` trong
`machine/server_connection/machine_server_request.py` gọi hai route này.
Hỏi lệnh và gửi kết quả không cập nhật heartbeat.

Các tác vụ Menu/Kho phía server gọi `machine_transport.send()`:
`nhan_menu`, `cap_nhat_menu`, `nhan_kho`, `nap_kho`. Máy dùng `take()` qua route
hỏi lệnh để nhận việc; dùng `deliver()` qua route trả kết quả để đánh thức
`send()` đang chờ. Máy mở request mới để gửi kết quả; server trả dữ liệu cho app
trên request nghiệp vụ ban đầu. Machinelist chỉ đọc trạng thái heartbeat.

```text
App → module sync → send() → hộp thư
Máy → machine_link.poll() → take() → nhận lệnh và thực hiện
Máy → machine_link.send_result() → deliver() → send() hết chờ → app
```

Link không diễn giải dữ liệu nghiệp vụ Menu/Kho và không import module sync.
Refactor riêng sync giữ giao diện send và hợp đồng lệnh thì không cần sửa link.
Refactor link giữ route/gói tin/xác thực và giao diện transport thì không cần sửa sync.
Đổi lệnh/dữ liệu cần cập nhật feature phía máy; đổi route/gói vận chuyển cần cập nhật
kết nối phía máy. Đổi transport cần kiểm tra cả Menu và Kho.

## Kiểm tra

```sh
python -m unittest tests.python.test_machine_relay tests.python.test_server_modules -v
```

Test relay dùng vòng lặp máy và HTTP thật với SQLite tạm, database nghiệp vụ máy giả;
không xác nhận thiết bị vật lý hoặc database sản xuất.
