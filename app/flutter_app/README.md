# App FlexMix (Flutter, Android)

App quản lý máy pha: đăng ký/đăng nhập tài khoản, thêm máy (Bluetooth hoặc tem QR),
chia sẻ máy cho nhân viên (QR hoặc Bluetooth), xem menu/kho và bật tắt món qua server.

## Địa chỉ server

App không nhúng sẵn địa chỉ server; truyền lúc build/chạy:

```powershell
flutter run --dart-define=SERVER_URL=http://<IP máy chạy server>:8000
flutter build apk --release --dart-define=SERVER_URL=http://<IP máy chạy server>:8000
```

Thiếu `SERVER_URL` thì màn hình đăng nhập báo cần build lại. Điện thoại và máy chạy
server phải cùng mạng; server nghe `0.0.0.0:8000` (xem `server/START.md`).
`python tests/e2e/run_e2e.py` tự dò IP laptop, build, cài và test trên điện thoại.

## Cấu trúc

- `lib/UI/login`: đăng nhập, đăng ký + OTP.
- `lib/UI/dashboard`: khung chính, các tab và `machine_api.dart` (mọi request tới server).
  Server báo `login_required` ở bất kỳ API nào thì app quay về màn hình đăng nhập.
- `lib/feature/machine_register`: thêm máy qua Bluetooth (`BluetoothPairing.kt`) hoặc tem QR.
- `lib/feature/machine_share`: chia sẻ máy (QR, Bluetooth), danh sách và thu hồi nhân viên.
  Nội dung QR/gói Bluetooth tạo và đọc tập trung trong `machine_share_qr.dart`.
- `lib/feature/data_sync`: dữ liệu từng tab (hiện có menu sản phẩm).

## Kiểm tra

```powershell
flutter analyze
flutter test
```
