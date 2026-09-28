# App FlexMix (Flutter, Android)

App quản lý máy pha: tài khoản, thêm/chia sẻ máy qua QR hoặc Bluetooth, menu và kho.

## Cấu trúc

- `lib/app/`: lắp ghép màn hình và điều hướng. Auth và dashboard không import nhau.
- `lib/config/`: địa chỉ server và route HTTP, chia nhóm như server.
- `lib/core/`: vận chuyển HTTP, lỗi/phiên và cấu trúc gói QR/Bluetooth dùng chung.
- `lib/shared/ui/`: theme và widget trình bày dùng chung, không biết feature.
- `lib/feature/<tính năng>/`: request, dữ liệu/trạng thái và `ui/` của chính tính năng.

Các feature: `user_auth`, `machine_register`, `machine_share`, `machine_list`,
`machine_menu`, `machine_ingredient`, `orders`, `dashboard`.
Dashboard lắp ghép các tab; màn hình QR ở đây phân luồng tem đăng ký và mã chia sẻ.
`orders` hiện dùng dữ liệu demo, chưa có API đơn hàng.

Request từng feature dùng extension trên `ServerClient`: route, payload và kiểm tra
kết quả nằm trong feature. Client chung không import feature và không biết nghiệp vụ.
`core/http_json.dart` giữ cách đọc phản hồi đăng nhập/OTP hiện có; `ServerClient`
xử lý hai dạng phản hồi tài khoản/máy cùng thông báo phiên hết hạn.
UI gọi request hoặc state của feature; không tự tạo HTTP client.
Không bắt buộc thêm controller/model/repository khi chưa có trách nhiệm cần tách.

## Build và kiểm tra

Chạy từ `app/flutter_app`:

```powershell
flutter analyze
flutter test ../../tests/flutter
flutter build apk --release --dart-define=SERVER_URL=http://<IP server>:8000
```

`lib/config/app_config.dart` chứa URL mặc định; `--dart-define=SERVER_URL=...` ghi đè.
Test điện thoại từ thư mục gốc: `python tests/e2e/run_e2e.py` (ADB USB reverse).
Bộ test và công cụ mô phỏng nằm trong `../../tests/`; không đặt test trong app.
