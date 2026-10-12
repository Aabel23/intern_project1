# A-02 · App nhận và chọn máy

> **Đã code theo hợp đồng v2 (12/10/2026)** — [`v2-decisions.md`](../../../contracts/messages/v2-decisions.md) thắng mọi chỗ mâu thuẫn trong phiếu này (bind tại xưởng thay activation tại chỗ, BLE bỏ R2/Q2, Wi-Fi tùy chọn). Trạng thái BLOCKED bên dưới là lịch sử.

**Trạng thái:** Sau A-01 review, cùng claim server/máy đã chốt; BLOCKED B-01/B-03. Giữ dashboard/pubspec tới review rồi giao A-03.

## Input chung / cổng

Đọc `documentation/plan/assignments.md`, `documentation/architect/features/contracts.html`, `contracts/COMPATIBILITY.md`, `contracts/messages/security-boundary.md` và hợp đồng module bên dưới. Quyết định chat mới nhất có ưu tiên. Trạng thái của phiếu theo bảng security-boundary.md; thiếu đặc tả thực thì báo Planner, không tự chọn. Mặc định cấu hình đã do Planner chọn, không cần user duyệt từng số. Payload examples là plaintext để kiểm nghiệp vụ, không cho gửi rõ qua mạng.

## Giới hạn và bàn giao

Chỉ skeleton; không menu/share/LAN/BT vận hành/OTA/đổi email/khôi phục mật khẩu. Không sửa `contracts/**`; lỗi hợp đồng báo Planner. Không ghi OTP/password/token/khóa/mã niêm phong/App Password trong file hoặc log. Không sửa vấn đề ngoài phiếu. Các file ghi chung chỉ chuyển người sở hữu sau review nhỏ; không commit code người khác. Chạy ca có giá trị xác minh hành vi, ghi kết quả không chứa bí mật. Kết quả phải gồm diff đúng file được phép, cách chạy, ca đã đạt/không chạy và blocker. Coder không tự đổi thiết kế khi test fail.

## File và hàm

Sửa `flutter_app/lib/feature/dashboard/ui/machine_qr_page.dart`: `_MachineQrPageState.detect`, `scanAgain`; `feature/machine_register/ui/machine_register_bluetooth_page.dart`: `_MachinePairingPageState`; `feature/dashboard/ui/machines_tab.dart`: `MachinesTab`, MachineItem và onTap; `feature/dashboard/ui/dashboard_page.dart`: `_MainDashboardState` load/select. Tạo `feature/machine_register/data/claim_service.dart`: `parseSealedQr`, `provisionWifi`, `beginClaim`, `completeClaim`; `feature/dashboard/data/machine_service.dart`: `listMachines`; `feature/dashboard/data/selected_machine.dart`: value only. Pubspec/Android Bluetooth permissions chỉ B-03 SDK quyết định; không sửa app_navigation.dart/cloud_client.dart; cần thay shared API báo A-01 trước, không hai writer. Tests `flutter_app/test/machine_claim/`.

## Hợp đồng input/output

claim.md. Scanner chỉ sealed factory QR v1 đúng format được B-03 chốt; không share QR. UI hiện đang nói 'QR chia sẻ' cần nội dung đúng nhận máy. App giữ seal và wifi password chỉ RAM thời gian claim, clear khi dispose/success/cancel; không persistence/log. User nhập wifi sau handshake bảo vệ; gửi tới máy, không server. Máy trusted sau activation rồi app begin/BT proof/complete đúng claim. Mất response complete retry same claim; đọc list xác nhận. Selection chỉ id có trong list account; logout/new account clear selection; refresh list mất máy selected thì clear. Không chọn machine nạp sẵn; list load/network fail hiển thị lỗi riêng, không coi thành empty success. Card online ghi server cloud, không nói trạng thái trực tiếp.

## Thứ tự / lỗi

1. QR validation và BT secure channel đã chốt. 2. Wifi / activation. 3. begin/proof/complete. 4. reload list/select. 5. Dashboard callback injection, không global fake list. Sai mã từ chối trước wifi; WIFI_FAILED/MACHINE_UNTRUSTED/ALREADY_OWNED/CLAIM_* hiển thị rõ; không auto retry claim ID mới khi không biết commit cũ. Skeleton không có action rename/share/remove thật: disable hoặc ẩn entry đang placeholder trong MachinesTab, không triển khai route. BT button chỉ nhận máy, không share/vận hành.

## Ca / cách kiểm

Widget/service fake: QR sai không connect; sai seal không gửi wifi; begin chưa complete không thêm card; complete fail không owner; mất response retry cùng ID; list của account khác không giữ selection; selected id bị xóa clears; logout clears. `flutter test test/machine_claim`; analyze file đổi; BLE/QR/wifi thực trên Android+Pi dành I-01, fake không bằng chứng nghiệm thu.

## B-03 ngày12/10/2026 · profile đã khóa, gate còn BLOCKED

User chọn HPKE PSK + review phiên, không Noise adapter. Đọc toàn bộ `contracts/messages/bt-claim.md`; không tự chọn cipher/provider/framing/state/nonce/retry. App confirmation R2 và machine ACK Q2 bắt buộc trước Wi-Fi/claim; session binding UUIDv4 chỉ từ phiên đó, không serial/claim_id/GATT ACK. Tất cả role/serial/session/Nm/Nc/h0/h1/h2 và stage kiểm theo profile; ephemeral HPKE key khác signing key bound. Request/response context/exporter một lần, không reverse HPKE seal hoặc resend ciphertext.

B-03 thiếu review phiên độc lập, RFC mode_psk/vector/exporter BC1.86↔PyHPKE0.6.5, Android runtime/BLE thật và OS Wi-Fi API/time budget M-01. Giữ BLOCKED cho tới Planner ghi đủ bằng chứng; không viết code khi chỉ profile đã có. Lỗi build/API/vector hoặc phát hiện design mới báo Planner/Operator, không tự vá primitive/adapter hoặc mở cổng.
