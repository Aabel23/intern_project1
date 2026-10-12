# Đường ngắn nhất tới MVP skeleton

**Ngày 12/10/2026 · trạng thái thực thi.** Mốc đã chốt: người dùng mới đăng ký bằng email/OTP, đăng nhập, nhận **máy thật** bằng mã niêm phong; app hỏi trạng thái **trực tiếp từ máy** qua server và hiển thị đúng câu trả lời. [Lộ trình tổng](mvp-roadmap.html), [bảng phân công](assignments.md), [hợp đồng](../../contracts/COMPATIBILITY.md) là nguồn chi tiết. File này giữ thứ tự thực thi ngắn gọn để không mở rộng phạm vi MVP.

## Bản chốt giữ nguyên

- Server đăng ký serial + verifier mã niêm phong trước khi bán; máy tự sinh khóa lần bật đầu. Cloud dùng HTTPS/TLS **và** phong bì HPKE từ skeleton. Bluetooth nhận máy dùng HPKE PSK với bước app confirm/máy ACK trước Wi-Fi hoặc claim.
- Nếu Wi-Fi mới đã kết nối mà server tạm lỗi, máy giữ Wi-Fi và tự retry activation. Server quyết Owner duy nhất. Trạng thái trong mốc này phải là câu trả lời mới từ máy qua relay, không dùng cờ online của server thay thế.
- Chỉ phát code theo phiếu Planner; mỗi task review nhỏ, mỗi module review lớn một lần. Vấn đề đổi thiết kế ghi lại để user quyết.

## Đã xong

| Phần | Bằng chứng | Trạng thái |
|---|---|---|
| C-01..C-05 hợp đồng cloud/auth/claim/relay | `contracts/`, `documentation/architect/features/contracts.html` | Cloud/auth đã khóa; Bluetooth B-03 còn gate thiết bị |
| S-01 server tài khoản/HTTPS/HPKE/MySQL/SMTP | 32 test đạt gồm MySQL cô lập, RFC HPKE; review nhỏ vòng 2 PASS | Code xong, chưa Gmail/runtime thật |
| A-01 app tài khoản/HPKE/Keystore | 20 Flutter tests, APK debug + AndroidTest build; review nhỏ vòng 2 PASS | Code xong, chưa chạy Android thật |
| Review lớn module tài khoản | [Biên bản](account-module-review-2026-10-12.md) | Đã chạy một lần; 2 finding user ghi nhận, **chưa sửa** |
| HPKE PSK primitive Android JVM↔Python | `tests/fixtures/crypto/rfc9180-psk.json`, 4 lượt interop + ca sai | Đạt ở mức thư viện; chưa chứng minh phiên BLE/product |

## Việc tiếp theo, đúng thứ tự phụ thuộc

1. **Planner tách phần độc lập để coder chạy ngay:** từ S-02 phát phiếu server factory registration + activation challenge/bind; từ M-01 phát phiếu máy sinh/lưu khóa + cloud HPKE/activation trên mạng đã provision. Hai phiếu chỉ dùng quyết định đã chốt, không cần chờ BLE GATT/Wi-Fi API. Coder Sol low làm song song theo file riêng; review nhỏ từng phiếu.
2. **Đóng B-03 trên thiết bị thật:** khi Android/Pi được kết nối, inventory OS/network manager/BLE trực tiếp; kiểm HPKE PSK profile confirm/ACK, replay, GATT framing và Wi-Fi provision/rollback. Planner hoàn thiện đúng phần còn thiếu của M-01/A-02/S-02 rồi phát coder. Tập trung một đường nhận máy đầu tiên; chưa kéo menu/share/vận hành offline vào mốc này.
3. **Ghép nhận chủ:** máy nhận Wi-Fi, tự activation bằng serial/mã/khóa mới; app quét QR, hoàn tất claim; server transaction bảo đảm một Owner. Code M-01, S-02, A-02 và review nhỏ. Wi-Fi đã kết nối mà activation lỗi thì giữ mạng, tự thử lại.
4. **Relay trạng thái:** M-02 nối/poll server; S-03 chuyển câu hỏi và chờ kết quả; M-03 đọc trạng thái hiện tại; A-03 hiển thị câu trả lời hoặc offline/timeout rõ. Làm theo phụ thuộc trong [assignments.md](assignments.md), review nhỏ và một review lớn cho từng module sau khi đủ task.
5. **Nghiệm thu I-01:** provision HTTPS domain/cert, khóa server và public pins thật; chạy Android/Pi thật, Gmail thật tới đúng hai email thử, claim máy mới, hỏi trạng thái qua app→server→máy→server→app, thử offline/claim trùng. Ghi bằng chứng và dọn đúng dữ liệu thử theo phiếu I-01.

## Gate hiện tại

- Android/Pi có thể kết nối nhưng user chọn để sau. Không dùng APK build/JVM interop thay bằng chứng chạy trên thiết bị.
- Chưa có runtime HTTPS domain/cert/server keys/public pins; app asset `{}` cố ý fail startup. Cần provision trước nghiệm thu app↔server thật.
- B-03 còn thiếu profile/state tests trên Android/Pi và Wi-Fi API theo OS Pi thật. Đây là gate kỹ thuật của nhận máy, không phải yêu cầu bàn lại kiến trúc.

**Điểm dừng MVP:** I-01 đạt trên máy/điện thoại/server thật. Menu, share và đường offline tiếp tục theo phase đã duyệt sau mốc này.
