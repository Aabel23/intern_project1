# Thêm máy bằng QR

Mở tab Máy → Quét QR, cấp quyền camera rồi quét tem máy.
QR phải chứa chuỗi JSON UTF-8 theo mẫu:

```json
{"type":"pairing","machine_name":"FlexMix-01","product_key":"KEY_CUA_MAY"}
```

Dùng tên và key thật của máy khi tạo tem. Không phải QR chứa URL.
App chỉ lấy ba trường trên, gửi POST `/app/dang-ky-may` đến server đang cấu hình
trong app và hiển thị ID server trả về. Không lấy địa chỉ server từ QR.
Mỗi lượt quét chỉ gửi một request, camera đóng khi nhận được QR.
Nếu QR sai hoặc server lỗi, bấm Quét lại để thử lại.

Request gửi kèm token đăng nhập. Người đầu tiên quét tem thành chủ máy (`owner`);
tài khoản khác quét lại tem sẽ bị từ chối và phải nhờ chủ chia sẻ.
Chưa truyền ID mới xuống máy.

# Chia sẻ máy cho nhân viên

Chủ máy: tab Máy → menu ⋮ của máy → Chia sẻ cho nhân viên. App gọi
`/app/tao-ma-chia-se` và hiện QR:

```json
{"type":"share","code":"MA_MOI_SERVER_TAO"}
```

Nhân viên: tab Máy → Quét QR (cùng màn hình quét tem). App gửi mã tới
`/app/nhan-chia-se`, server ghi nhân viên là `manager` của máy.
Mã dùng một lần, hết hạn sau 5 phút. Sau khi quét, dashboard đọc lại
`/app/may-cua-toi` nên máy hiện ngay trong danh sách.

## Chia sẻ qua Bluetooth

Dùng khi không tiện quét QR. Nội dung gửi đi giống hệt QR (`encodeShareQr`),
nên mã hóa sau này trong `core/machine_packet.dart` áp dụng cho cả hai đường.

1. Nhân viên: tab Máy → **Nhận chia sẻ qua Bluetooth**, cho phép hiện điện thoại
   (120 giây). App mở RFCOMM server với UUID `e53b1694-9a6d-41e7-8b4a-00e228b8164e`.
2. Chủ máy: Chia sẻ máy → **Gửi qua Bluetooth**, quét rồi chọn điện thoại nhân viên.
3. Gói tin, mỗi gói một dòng JSON UTF-8 kết thúc bằng `\n` (tối đa 4096 byte),
   cùng kiểu với pairing máy:
   - Chủ → nhân viên: `{"type":"identify"}`
   - Nhân viên → chủ: `{"type":"ready","ok":true}`
   - Chủ → nhân viên: `{"type":"share","code":"..."}`
   - Nhân viên → chủ: `{"type":"ack","ok":true}` (`ok:false` nếu không phải gói share),
     rồi chờ chủ đóng kết nối trước để ACK không bị mất.
4. App nhân viên kiểm tra gói bằng `parseMachineQr`, gọi `/app/nhan-chia-se`
   như khi quét QR. Mã vẫn dùng một lần, hết hạn sau 5 phút.

Thử với một điện thoại: laptop Windows đóng vai nhân viên bằng
`python tests/bluetooth_pair/app2app_pair.py` (cần server đang chạy và một
tài khoản thứ hai).
