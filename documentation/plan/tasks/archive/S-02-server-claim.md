# S-02 · Server nhận chủ và danh sách máy

> **Đã code theo hợp đồng v2 (12/10/2026)** — [`v2-decisions.md`](../../../../contracts/messages/v2-decisions.md) thắng mọi chỗ mâu thuẫn trong phiếu này (bind tại xưởng thay activation tại chỗ, BLE bỏ R2/Q2, Wi-Fi tùy chọn). Trạng thái BLOCKED bên dưới là lịch sử.

**Trạng thái:** Sau S-01 review; BLOCKED B-01/B-02/B-03. Giữ server routing/http riêng rồi giao S-03.

## Input chung / cổng

Đọc `documentation/plan/archive/assignments.md`, `documentation/architect/features/contracts.html`, `contracts/COMPATIBILITY.md`, `contracts/messages/security-boundary.md` và hợp đồng module bên dưới. Quyết định chat mới nhất có ưu tiên. Trạng thái của phiếu theo bảng security-boundary.md; thiếu đặc tả thực thì báo Planner, không tự chọn. Mặc định cấu hình đã do Planner chọn, không cần user duyệt từng số. Payload examples là plaintext để kiểm nghiệp vụ, không cho gửi rõ qua mạng.

## Giới hạn và bàn giao

Chỉ skeleton; không menu/share/LAN/BT vận hành/OTA/đổi email/khôi phục mật khẩu. Không sửa `contracts/**`; lỗi hợp đồng báo Planner. Không ghi OTP/password/token/khóa/mã niêm phong/App Password trong file hoặc log. Không sửa vấn đề ngoài phiếu. Các file ghi chung chỉ chuyển người sở hữu sau review nhỏ; không commit code người khác. Chạy ca có giá trị xác minh hành vi, ghi kết quả không chứa bí mật. Kết quả phải gồm diff đúng file được phép, cách chạy, ca đã đạt/không chạy và blocker. Coder không tự đổi thiết kế khi test fail.

## File và hàm

Tạo `server/src/device_claim.py`: `verify_activation`, `begin_claim`, `complete_claim`, `list_user_machines`; `server/src/factory_register.py`: `register_serial`; `server/migrations/002_devices_claims.sql` (devices/claim_challenges/activation_challenges); tests `tests/server/test_claim.py`. Sửa `server/src/http.py` register handlers và `server/configuration/routing.py` chỉ route activation/claim/list hiện hành, không thêm endpoint share/removal. Factory CLI `python3 -m server.src.factory_register --serial SERIAL --name NAME`; đọc seal S32 từ stdin ẩn, không argv/log/file; DB config server; verifier và bind theo cloud-protection.md. CLI chỉ Operator, không public API.

## Input/output/dữ liệu

Theo claim.md. Context app từ S-01; context máy do cloud-protection.md. Factory registered serial không owner/public key; activation kiểm kiến thức mã và chứng minh private key mới rồi atomic bind serial/key. Database lock device row với unique serial, FK owner; mỗi máy duy nhất owner_user_id. begin không cấp quyền; complete claim transaction consume và set owner khi null, bắt race; commit retry đúng user đọc cùng kết quả. list chỉ của user hiện hành, không expose verifier/public key/claim nonce; online do S-03 evidence còn chưa có thì false.

## Thứ tự / lỗi

Migration→factory tool/activation→begin/complete transaction→list→HTTP mapping. Tuân claim errors; unknown serial không tự register; khác key KEY_CONFLICT; expired challenge không consume success; proof user khác/account mismatch không owner. Không giữ DB transaction chờ BT/network. SMTP/auth schema không sửa. Bản ghi thử gắn UUID id rõ cho I-01 cleanup.

## Ca / cách kiểm

MySQL thật isolated DB: serial chưa register reject; seal sai/key proof sai reject; bind same key idempotent vs different key conflict; hai complete cạnh tranh chỉ 1 owner; copy proof sang user khác/device khác reject; replay cùng claim đúng user trả kết quả cũ; commit mất response retry không owner thêm; reset máy không thay DB owner; owner list chỉ máy mình và không bí mật. `python3 -m unittest discover -s tests/server -p 'test_claim.py'`; mật mã wire/vector chỉ sau B-01. Không tự tạo máy hãng trong nghiệm thu; factory serial/mã được Operator kiểm.

Factory đăng ký không sinh S khác với máy/QR; tool nhận S32 đã provision, verifier SHA256 domain như cloud-protection.md. Public key CPU P256 bound; activation_challenges lưu serial/nonce/expiry/consumed/key/result để retry cùng bind sau commit. `list_user_machines(user_id,connectivity=None)` trả online false khi callable None; S-03 inject callable trong http.py, không sửa file claim song song.

## B-03 ngày12/10/2026 · profile đã khóa, gate còn BLOCKED

User chọn HPKE PSK + review phiên, không Noise adapter. Đọc toàn bộ `contracts/messages/bt-claim.md`; không tự chọn cipher/provider/framing/state/nonce/retry. App confirmation R2 và machine ACK Q2 bắt buộc trước Wi-Fi/claim; session binding UUIDv4 chỉ từ phiên đó, không serial/claim_id/GATT ACK. Tất cả role/serial/session/Nm/Nc/h0/h1/h2 và stage kiểm theo profile; ephemeral HPKE key khác signing key bound. Request/response context/exporter một lần, không reverse HPKE seal hoặc resend ciphertext.

B-03 thiếu review phiên độc lập, RFC mode_psk/vector/exporter BC1.86↔PyHPKE0.6.5, Android runtime/BLE thật và OS Wi-Fi API/time budget M-01. Giữ BLOCKED cho tới Planner ghi đủ bằng chứng; không viết code khi chỉ profile đã có. Lỗi build/API/vector hoặc phát hiện design mới báo Planner/Operator, không tự vá primitive/adapter hoặc mở cổng.
