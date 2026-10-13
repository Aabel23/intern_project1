# App FlexMix (Flutter, Android)

App quản lý máy pha: tài khoản email/OTP, nhận máy bằng tem QR + Bluetooth, danh sách máy,
trạng thái trực tiếp, menu và kho qua relay. Hợp đồng: `contracts/messages/v2-decisions.md`.

## Build APK

Điều kiện một lần: server đã được dựng bằng `python3 server/tools/provision_keys.py --url http://<IP-LAN>:8080`
(xem `server/LAN_HTTP.md`). Lệnh đó ghi `assets/server-trust.json` và `lib/shared/cloud/server_endpoint.dart`;
commit hai file này là các máy khác chỉ cần pull rồi build.

```bash
cd flutter_app
flutter pub get
flutter build apk --release --dart-define=FLEXMIX_SERVER_BASE_URL=http://<IP-LAN>:8080
```

Trỏ sang server khác bằng `--dart-define=FLEXMIX_SERVER_BASE_URL=https://<host>` khi chuyển lên Internet.
App chỉ chấp nhận HTTP tới IP nội bộ/loopback đã cấu hình; HTTPS vẫn dùng được. Cả hai đường giữ `server-trust.json`, phong bì HPKE và kiểm quyền. Nếu file trust còn là `{}`, app dừng ở màn "Không thể tải cấu hình kết nối an toàn". Kiểm thử trên Android thật được thực hiện ở cổng trước phát hành.

## Kiểm tra

```bash
flutter analyze
flutter test
```

Giao thức BLE phía app (`android/.../ClaimProtocol.kt`) còn được chạy với code máy Python trong
`tests/kotlin-interop` (xem `tests/machine/test_kotlin_interop.py`).

## Cấu trúc

- `lib/shared/cloud/`: phong bì HPKE gọi native (`flexmix/crypto`), làm mới phiên, đồng hồ server.
- `lib/feature/user_auth/`: đăng ký, OTP, đăng nhập.
- `lib/feature/machines/`: danh sách máy, relay (`MachineService.ask`), controller dùng chung các tab.
- `lib/feature/machine_register/`: nhận máy (tem QR → Bluetooth → Wi-Fi nếu cần → server).
- `lib/feature/machine_menu/`, `machine_ingredient/`: tab Sản phẩm và Kho đọc/ghi qua relay.
- `android/app/src/main/kotlin/.../`: `CloudCrypto` (HPKE cloud), `ClaimProtocol` + `ClaimBle` +
  `ClaimChannel` (phiên BLE nhận máy), `SessionStore` (Keystore), `FlexJson` (byte J() khớp server).
- `orders` và chia sẻ máy vẫn là giao diện mẫu, chưa có API.
