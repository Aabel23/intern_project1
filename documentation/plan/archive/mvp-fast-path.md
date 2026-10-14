# Đường ngắn nhất tới MVP skeleton

**Ngày 12/10/2026 · trạng thái thực thi.** Mốc đã chốt: người dùng mới đăng ký bằng email/OTP, đăng nhập, nhận **máy thật** bằng mã niêm phong; app hỏi trạng thái **trực tiếp từ máy** qua server và hiển thị đúng câu trả lời. [Lộ trình tổng](mvp-roadmap.html), [bảng phân công](assignments.md), [hợp đồng](../../../contracts/COMPATIBILITY.md) là nguồn chi tiết. File này giữ thứ tự thực thi ngắn gọn để không mở rộng phạm vi MVP.

## Bản chốt giữ nguyên

- Server đăng ký serial + verifier mã niêm phong trước khi bán; máy tự sinh khóa lần bật đầu. Cloud dùng HTTPS/TLS **và** phong bì HPKE từ skeleton. Bluetooth nhận máy dùng HPKE PSK với bước app confirm/máy ACK trước Wi-Fi hoặc claim.
- Nếu Wi-Fi mới đã kết nối mà server tạm lỗi, máy giữ Wi-Fi và tự retry activation. Server quyết Owner duy nhất. Trạng thái trong mốc này phải là câu trả lời mới từ máy qua relay, không dùng cờ online của server thay thế.
- Chỉ phát code theo phiếu Planner; mỗi task review nhỏ, mỗi module review lớn một lần. Vấn đề đổi thiết kế ghi lại để user quyết.

## Cập nhật 12/10/2026 · cách 3 trên version1.1 (hợp đồng v2, D1–D10)

User duyệt D1–D10 và chọn giữ nghiệp vụ máy pha của `version1.1`, chỉ thay lớp kết nối máy, cộng server và app. Hợp đồng: [`contracts/messages/v2-decisions.md`](../../../contracts/messages/v2-decisions.md). Không chờ gate phần cứng; nghiệm thu thiết bị thật để sau.

| Phần | Bằng chứng | Trạng thái |
|---|---|---|
| Server: đăng ký máy ở xưởng, claim, nhả máy, relay, route máy, vá tài khoản | `tests/server` 43 test với MySQL thật + HTTPS thật, trong đó 8 test tích hợp máy↔server↔app | Code xong |
| Máy (version1.1): danh tính, phong bì cloud, vòng poll, chống chạy lặp lệnh, phiên BLE v2, GATT BlueZ, Wi-Fi NetworkManager | `tests/machine` 16 test | Code xong; GATT/Wi-Fi chưa chạy trên Pi thật |
| App: nhận máy qua BLE (Kotlin), danh sách/nhả máy, trạng thái trực tiếp, Sản phẩm/Kho qua relay | `flutter test` 31 test; `flutter analyze` sạch | Code xong; chưa build APK (sandbox không tải được Android SDK) |
| Interop app Kotlin (Bouncy Castle 1.86) ↔ máy Python (PyHPKE 0.6.5) | `tests/kotlin-interop` + `tests/machine/test_kotlin_interop.py`: trọn phiên probe→wifi→claim | Đạt trên JVM |

Còn lại: build APK và chạy trên Android thật, chạy GATT/NetworkManager trên Pi thật, HTTPS domain/cert/pin thật, Gmail thật, nghiệm thu I-01.

## Đã xong (trước 12/10/2026)

| Phần | Bằng chứng | Trạng thái |
|---|---|---|
| C-01..C-05 hợp đồng cloud/auth/claim/relay | `contracts/`, `documentation/architect/features/contracts.html` | Cloud/auth đã khóa; Bluetooth B-03 còn gate thiết bị |
| S-01 server tài khoản/HTTPS/HPKE/MySQL/SMTP | 32 test đạt gồm MySQL cô lập, RFC HPKE; review nhỏ vòng 2 PASS | Code xong, chưa Gmail/runtime thật |
| A-01 app tài khoản/HPKE/Keystore | 20 Flutter tests, APK debug + AndroidTest build; review nhỏ vòng 2 PASS | Code xong, chưa chạy Android thật |
| Review lớn module tài khoản | [Biên bản](account-module-review-2026-10-12.md) | Đã chạy một lần; finding quota login đã sửa trong v2, finding ô nhập lại mật khẩu vẫn giữ theo quyết định user |
| HPKE PSK primitive Android JVM↔Python | `tests/fixtures/crypto/rfc9180-psk.json`, 4 lượt interop + ca sai | Đạt ở mức thư viện; chưa chứng minh phiên BLE/product |

## Việc tiếp theo (sau cập nhật v2)

Các bước 1–4 của kế hoạch cũ (tách phiếu, đóng B-03, ghép nhận chủ, relay trạng thái) đã được code theo hợp đồng v2; xem bảng cập nhật ở đầu file. Còn lại, theo thứ tự:

1. **Dựng server thật:** `python3 server/tools/provision_keys.py --url https://<miền>`, commit hai file công khai nó ghi ra, chứng chỉ HTTPS CA công khai, MySQL + migration 001/002, biến môi trường (`server/README.md`).
2. **Build APK** (`flutter_app/README.md`) và chạy trên Android thật: đăng nhập, nhận máy qua BLE, trạng thái, menu/kho.
3. **Pi thật:** `python -m machine.config.provision`, Operator `factory_register`, in tem QR; chạy `machine.main` và `machine.pairing.machine_bluetooth_pair` (BlueZ GATT, NetworkManager).
4. **Nghiệm thu I-01:** Gmail thật tới hai email thử, claim máy mới, claim trùng, mất mạng, offline/timeout; ghi bằng chứng và dọn dữ liệu thử.

## Gate hiện tại

- Chưa có server thật (miền, chứng chỉ, khóa, pin); `assets/server-trust.json` còn `{}` cho tới khi chạy `provision_keys.py`.
- APK chưa được build trong sandbox (không tải được Android SDK); Kotlin đã biên dịch với android-all API 36 + Flutter embedding.
- GATT BlueZ, NetworkManager và BLE Android chưa chạy trên thiết bị thật.
- Chưa làm: reset vật lý có thời gian ân hạn (D2, cần nút cứng), chia sẻ máy, đơn hàng.

**Điểm dừng MVP:** I-01 đạt trên máy/điện thoại/server thật. Menu, share và đường offline tiếp tục theo phase đã duyệt sau mốc này.
