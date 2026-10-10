# Tiêu chí kiểm tra FlexMix (androidv0.1)

Mọi lần sửa code phải chạy lại script dưới đây và **đạt hết** các tiêu chí trước khi commit.
Script tự chấm, không cần AI đọc log: mã thoát 0 = đạt, khác 0 = có tiêu chí không đạt.

```powershell
# Từ thư mục androidv0.1
.\test.ps1 -List                     # danh sách luồng + trạng thái lần chạy cuối
.\test.ps1 -Note "mô tả thay đổi"    # mọi luồng
.\test.ps1 -Flow S8,F3               # chỉ các luồng bị ảnh hưởng
.\test.ps1 -Flow py                  # theo nhóm: py, app, e2e, all
.\test.ps1 -Flow E4                  # e2e nối tiếp: chạy E0..E4
.\test.ps1 -Build                    # ép build lại APK (mặc định tự build khi code app đổi)
```

Không cắm điện thoại thì các luồng E ghi `BỎ QUA`, không tính là lỗi. Thêm kịch bản mới: một dòng
trong `FLOWS` của `sandbox/check_all.py` + một dòng tiêu chí ở bảng tương ứng bên dưới.

Kết quả:

- `log/FLOWS.md`: bảng trạng thái mọi luồng (lần chạy cuối, commit, thời gian); xem file này thay vì đọc log.
- `log/<thời điểm>.md`: kết quả lần chạy, đuôi log của luồng lỗi.
- `log/<thời điểm>-e2e.txt`: toàn bộ output e2e; ảnh màn hình lúc lỗi ở `sandbox/e2e/logs/<thời điểm>/loi.png`.
- `log/HISTORY.md`: một dòng mỗi lần chạy (thời điểm, commit, kết quả, ghi chú).
- `log/BUG_LOG.md`: các lỗi đã tìm và cách sửa.

Điều kiện e2e: điện thoại cắm USB (đã cho phép gỡ lỗi USB); app gọi server qua cáp (`adb reverse`,
thêm `--wifi` cho `run_e2e.py` nếu muốn thử qua Wi-Fi cùng mạng),
Bluetooth bật trên cả hai, màn hình không khóa bằng mật khẩu (script tự bật `stayon usb`
và đánh thức màn hình trước khi chạy).

## Nhóm 1 — Server (Python unittest), `py`

| # | Module | Tiêu chí đạt |
| --- | --- | --- |
| S1 | `server.test_main` | Mọi route trả JSON đúng mã HTTP; giới hạn 30 req/phút/IP cho API tài khoản; body sai trả 400 |
| S2 | `server.service.user_register.test_flow` | Đăng ký → gửi OTP → xác minh OTP tạo tài khoản; trùng username/email bị từ chối; OTP sai/hết hạn bị từ chối |
| S3 | `server.service.user_login.test_flow` | Đăng nhập hai bước trả token; sai mật khẩu không lộ user tồn tại; đăng xuất xóa phiên |
| S4 | `server.service.machine_register.test_flow` | Người quét tem đầu tiên thành chủ; người khác bị từ chối; xác minh key đúng/sai |
| S5 | `server.service.machine_share.test_flow` | Mã mời dùng một lần, hết hạn; chỉ chủ tạo mã, xem và thu hồi nhân viên |
| S6 | `server.service.machine_manage.test_flow` | Chủ đổi tên, gỡ máy (xóa quyền nhân viên); nhân viên chỉ bỏ quyền của mình |
| S7 | `machine.pairing.test_bluetooth_pairing` | Gói pairing Bluetooth đúng định dạng dòng JSON |
| S8 | `machine.test_relay` | Máy chạy một vòng lệnh (không còn thread báo online), nhận lệnh, trả kết quả và gói đồng bộ gzip/ETag qua relay; sai quyền bị chặn |
| S13 | `tests.python.test_machine_online` | Online suy từ long-poll: rảnh/bận/treo, lệnh chưa lấy, không deadlock |
| X1 | `server.test_security` | Kịch bản tấn công: phần "đã an toàn" phải đạt; lỗ hổng còn mở là `expectedFailure` (xem `SECURITY_NOTES.md`). "Unexpected success" = lỗ hổng đã được sửa, cập nhật ghi chú |

## Nhóm 2 — App tĩnh, `analyze`

| # | Tiêu chí đạt |
| --- | --- |
| A1 | `flutter analyze` báo `No issues found!` (không warning, không info) |

## Nhóm 3 — App widget test, `flutter`

| # | File | Tiêu chí đạt |
| --- | --- | --- |
| F1 | `auth_page_test.dart` | Đăng nhập/đăng ký hiển thị lỗi, gửi đúng gói, chuyển OTP |
| F2 | `widget_test.dart` | Dashboard: chọn máy, tab Sản phẩm/Kho, bật tắt món, nạp kho, phiên hết hạn về đăng nhập |
| F3 | `dashboard_controller_test.dart` | Danh sách máy theo server (máy bị thu hồi/gỡ biến mất); máy offline báo lỗi offline ở tab |
| F4 | `device_share_test.dart` | Chủ hiện QR mã mời, xem/thu hồi nhân viên |
| F5 | `share_bluetooth_test.dart` | Gửi/nhận mã chia sẻ qua Bluetooth |
| F6 | `machine_manage_test.dart` | Đổi tên, gỡ máy |
| F7 | `machine_register_test.dart`, `machine_qr_test.dart`, `bluetooth_pairing_test.dart` | Đăng ký máy bằng QR/Bluetooth; product key chỉ hiện 4 ký tự cuối |

## Nhóm 4 — End-to-end trên điện thoại thật, `e2e`

`sandbox/e2e/run_e2e.py`: laptop giả máy FlexMix (Bluetooth + relay) và app thứ hai; điện thoại chạy app thật.
Mỗi bước có thời hạn; quá hạn là lỗi. Dữ liệu tạm (`e2e_*`, `FlexMix-E2E-*`) phải bị xóa khi kết thúc.

| # | Bước | Tiêu chí đạt |
| --- | --- | --- |
| E0 | Chuẩn bị | Điện thoại có IP Wi-Fi; server chạy; build + cài APK (`--skip-build` bỏ qua) |
| E1 | Đăng nhập chủ | Thấy tab "Máy" ≤ 30s sau khi bấm Đăng nhập |
| E2 | Pair máy qua Bluetooth | App hiện `ID: fm_…` ≤ 60s; DB có máy, người pair là `owner`; danh sách máy hiện "Chủ máy" |
| E3 | Máy online, menu, bật món, kho | Máy "Online" ≤ 30s; tab Sản phẩm hiện menu ≤ 40s; bật "Matcha latte" → máy nhận `doi_trang_thai_mon` và công tắc bật; tab Kho hiện "Sữa tươi", "0 / 1500 g", "Bơm 1" |
| E4 | Nạp kho | "Nạp đầy" một bình → "1500 / 1500 g"; "Nạp tất cả" → "2000 / 2000 g" và "1000 / 1000 g" |
| E5 | Đổi tên máy | Chủ đổi tên trên app → DB và danh sách máy hiện tên mới |
| E6 | Chia sẻ qua Bluetooth (chủ → laptop) | App hiện "Đã gửi mã cho…"; DB có nhân viên role `manager` |
| E7 | Xem + thu hồi nhân viên | Danh sách hiện tên nhân viên; thu hồi → "Chưa giao máy cho nhân viên nào", DB xóa quyền |
| E8 | Chia sẻ qua QR | Laptop chụp màn hình đọc QR và nhận máy; DB có quyền `manager` |
| E9 | Đăng xuất | Về màn hình Đăng nhập; DB không còn phiên của chủ ≤ 10s |
| E10 | Nhân viên nhận qua Bluetooth (laptop → điện thoại) | App hiện "Đã nhận quản lý máy"; danh sách máy hiện "Được giao" |
| E11 | Phiên hết hạn | Xóa phiên trên server, kéo tải lại → app về màn hình Đăng nhập ≤ 30s |
| E12 | Nhân viên bị thu hồi thì máy biến mất | Đăng nhập lại; chủ thu hồi quyền; nhân viên kéo tải lại tab Máy → "Quán chưa có máy nào", máy không còn trong danh sách |
| E13 | Dọn dữ liệu | Không còn user `e2e_*`/máy `FlexMix-E2E-*` sau khi chạy |

## Quy tắc khi sửa lỗi

1. Ghi lỗi vào `log/BUG_LOG.md` (hiện tượng, nguyên nhân, cách sửa, test nào bắt được).
2. Thêm/ sửa test để lỗi đó bị bắt (unit, widget hoặc bước e2e).
3. Chạy `check_all.py` đầy đủ; chỉ commit khi báo `ĐẠT`.
4. Test e2e chập chờn (Bluetooth, Wi-Fi): chạy lại tối đa 2 lần; lỗi lặp lại là lỗi thật.
