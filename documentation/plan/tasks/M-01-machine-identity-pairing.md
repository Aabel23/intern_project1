# M-01 · Danh tính máy và nhận wifi

**Trạng thái:** BLOCKED B-01/B-02/B-03. Sau chốt mới làm; M-02 nhận transport/routing sau review.

## Input chung / cổng

Đọc `documentation/plan/assignments.md`, `documentation/architect/features/contracts.html`, `contracts/COMPATIBILITY.md`, `contracts/messages/security-boundary.md` và hợp đồng module bên dưới. Quyết định chat mới nhất có ưu tiên. Trạng thái của phiếu theo bảng security-boundary.md; thiếu đặc tả thực thì báo Planner, không tự chọn. Mặc định cấu hình đã do Planner chọn, không cần user duyệt từng số. Payload examples là plaintext để kiểm nghiệp vụ, không cho gửi rõ qua mạng.

## Giới hạn và bàn giao

Chỉ skeleton; không menu/share/LAN/BT vận hành/OTA/đổi email/khôi phục mật khẩu. Không sửa `contracts/**`; lỗi hợp đồng báo Planner. Không ghi OTP/password/token/khóa/mã niêm phong/App Password trong file hoặc log. Không sửa vấn đề ngoài phiếu. Các file ghi chung chỉ chuyển người sở hữu sau review nhỏ; không commit code người khác. Chạy ca có giá trị xác minh hành vi, ghi kết quả không chứa bí mật. Kết quả phải gồm diff đúng file được phép, cách chạy, ca đã đạt/không chạy và blocker. Coder không tự đổi thiết kế khi test fail.

## File và hàm

Đọc/sửa `version1.1/machine/config/env.py` (`get_machine_name`, `get_server_url`, bỏ dùng `get_product_key` ở luồng skeleton); tạo `machine/config/provision.py`: `provision_machine`, vì create_env.py env.py nhắc không tồn tại. Tạo `machine/config/identity.py`: `load_or_create_identity`, `read_cpu_serial`; `machine/pairing/claim_channel.py`: `open_claim_channel`, `verify_server_challenge`, `sign_claim`; `machine/pairing/wifi_setup.py`: `configure_wifi`; `machine/server_connection/activation.py`: `activate_identity`. Sửa `machine/pairing/machine_bluetooth_pair.py` `pair_bluetooth`, `handle_connection`; `machine_bluetooth_serve.py` `run_server` chỉ cho nhận máy. Tests `tests/machine/test_identity.py`, `test_claim_channel.py`, `test_wifi_setup.py`. BLE GATT/UUID/Android peer và framing đã khóa trong bt-claim.md; không SPP. OS Wi-Fi command/API và deployment permissions còn BLOCKED, Planner phải chốt trước code; không tự chọn network manager.

## Input/output dữ liệu

`claim.md`; secret niêm phong nằm cấu hình máy provision, không sinh mã mới lúc boot. CPU serial đọc nguồn phần cứng Pi; thiếu serial dừng, không UUID giả. Identity sinh một lần rồi ghi atomic private file 0600; lỗi file hỏng dừng, không sinh khóa thay tự động. Key thuật toán/encoding/đường file chính thức cần B-02 chốt trước code. Server bind success lưu machine_id/key_id, không lấy từ serial tự khai. Không trả product_key trong message pairing hiện hành. Wifi ssid/password chỉ sau chứng thực mã dài + kênh mã hóa, không trả echo/log. `configure_wifi` chỉ đổi kết nối wifi nhận máy, trả connected hoặc WIFI_FAILED; không giấu lỗi shell/network; không tác động DB máy.

## Thứ tự / lỗi

Provision seal theo danh sách serial server đã đăng ký → boot tạo/load key → mở kênh nhận máy → app chứng minh mã đúng → wifi → activate_identity với proof bao phủ public key → ký challenge claim ràng phiên tại chỗ. Máy không tự owner. Chưa lên server trả lỗi kết nối cho app, không ready giả. Reset cục bộ không xóa private key/owner cloud. Khác key đã bind báo KEY_CONFLICT, không overwrite.

## Ca và cách kiểm

Temp config + fake CPU serial cho unit: hai boot giữ key; file permission; file hỏng/serial thiếu không tạo identity mới; product_key không xuất hiện BT; sai mã không wifi/sign; sửa challenge account/machine/purpose/hạn/nonce bị từ chối; replay/chuyển phiên BT bị từ chối; wifi fail không báo activated. Native crypto test vector sau B-03; không gọi stub là đã chứng minh mã hóa. Pi+Android thật I-01 kiểm byte traffic không có secret/wifi rõ; reboot giữ serial/key. Test dưới `tests/`, dùng `PYTHONPATH=version1.1 python3 -m unittest discover -s tests/machine` sau chốt dependency.

## B-03 ngày12/10/2026 · profile đã khóa, gate còn BLOCKED

User chọn HPKE PSK + review phiên, không Noise adapter. Đọc toàn bộ `contracts/messages/bt-claim.md`; không tự chọn cipher/provider/framing/state/nonce/retry. App confirmation R2 và machine ACK Q2 bắt buộc trước Wi-Fi/claim; session binding UUIDv4 chỉ từ phiên đó, không serial/claim_id/GATT ACK. Tất cả role/serial/session/Nm/Nc/h0/h1/h2 và stage kiểm theo profile; ephemeral HPKE key khác signing key bound. Request/response context/exporter một lần, không reverse HPKE seal hoặc resend ciphertext.

B-03 thiếu review phiên độc lập, RFC mode_psk/vector/exporter BC1.86↔PyHPKE0.6.5, Android runtime/BLE thật và OS Wi-Fi API/time budget M-01. Giữ BLOCKED cho tới Planner ghi đủ bằng chứng; không viết code khi chỉ profile đã có. Lỗi build/API/vector hoặc phát hiện design mới báo Planner/Operator, không tự vá primitive/adapter hoặc mở cổng.
