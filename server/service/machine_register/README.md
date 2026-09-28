# Đăng ký máy

Flow nằm trong `machine_register_process.py`.

- `machine_register_request.py`: khai báo route (`ROUTES`), server nạp theo `server/main.py`.
- `machine_register_process.py`: kiểm tra gói, lưu SQLite, cấp ID hoặc trả ID cũ.
- `machine_register_store.py`: SQL tạo máy và gán chủ; kiểm tra gói nằm ngay trong flow.

POST `/app/dang-ky-may`:

```json
{"type":"pairing","machine_name":"FlexMix-01","product_key":"key-cua-may","token":"TOKEN_DANG_NHAP"}
```

`token` lấy từ kết quả đăng nhập. Người đăng ký đầu tiên thành `owner` trong
`machine_managers`; tài khoản khác gửi lại cùng key bị từ chối.

Trả `valid`, `registered`, `created`, `machine_id`, `message`.
`type` từ Bluetooth được phép gửi kèm; hai trường bắt buộc là tên và key.
Gửi lại cùng key trả cùng ID, không sửa tên hoặc tạo bản ghi mới.
Key được lưu dưới dạng SHA-256 trong `machines.product_key_hash`.

Route phụ `/app/xac-minh-dang-ky-may` (đối chiếu `machine_id` với key) đã bỏ vì app không gọi.
Chưa có danh sách key nhà máy nên không xác minh key có thực sự do nhà máy cấp.
Chưa gán cửa hàng, chưa cấp credential hoặc gửi ID xuống Raspberry Pi.

Chạy qua server chung từ thư mục dự án: `python -m server.main`.
Khi khởi động, server bổ sung cột/index cho DB cũ; không xóa dữ liệu.

App tự POST gói sau Bluetooth rồi hiển thị ID server trả về.
Máy không cần biết ID: khi heartbeat/nhận lệnh, máy xưng danh bằng product key.

```sh
python -m unittest tests.python.test_machine_register -v
```
