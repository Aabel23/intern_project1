# Đăng ký máy

Flow nằm trong `machine_register_flow.py`.

- `machine_register_api.py`: HTTP handler riêng và hai route đăng ký máy.
- `machine_register_flow.py`: kiểm tra gói, lưu SQLite, cấp ID hoặc trả ID cũ.
- `machine_register_verify.py`: kiểm tra trường dữ liệu và đối chiếu ID/key đã đăng ký.

POST `/app/dang-ky-may`:

```json
{"type":"pairing","machine_name":"FlexMix-01","product_key":"key-cua-may","token":"TOKEN_DANG_NHAP"}
```

`token` lấy từ kết quả đăng nhập. Người đăng ký đầu tiên thành `owner` trong
`machine_managers`; tài khoản khác gửi lại cùng key bị từ chối.

Trả `valid`, `registered`, `created`, `machine_id`, `verify_route`, `message`.
`type` từ Bluetooth được phép gửi kèm; hai trường bắt buộc là tên và key.
Gửi lại cùng key trả cùng ID, không sửa tên hoặc tạo bản ghi mới.
Key được lưu dưới dạng SHA-256 trong `machines.product_key_hash`.

POST `/app/xac-minh-dang-ky-may`:

```json
{"machine_id":"fm_ID_SERVER_TRA_VE","product_key":"key-cua-may"}
```

Trả `valid`, `verified`, `machine_id`, `message` khi khớp bản ghi.
Đây là kiểm tra đăng ký đã lưu, không phải bước kích hoạt riêng.
Chưa có danh sách key nhà máy nên không xác minh key có thực sự do nhà máy cấp.
Chưa gán cửa hàng, chưa cấp credential hoặc gửi ID xuống Raspberry Pi.

Chạy từ thư mục dự án (chọn một server trên port 8000):

```sh
python -m server.service.machine_register.machine_register_api
```

`python -m server.server` cũng đã đăng ký hai route này. Module đăng nhập
không import hoặc cung cấp route đăng ký máy. Khi khởi động, server bổ sung cột/index cho DB cũ;
không xóa dữ liệu. Không chạy các server này đồng thời trên cùng port.

App tự POST gói sau Bluetooth rồi hiển thị ID server trả về.
ID chưa tự thêm vào dashboard vì máy chưa nhận ID mới để heartbeat.

```sh
python -m unittest server.service.machine_register.test_flow -v
```
