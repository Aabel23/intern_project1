# Đối chiếu shortlist D/C với hệ thống thực tế — 07/10/2026

> **Đã chốt 07/10/2026:** người dùng chọn `D1-B, C2-B, C4-B, C1-A, C3-A, D2-C, D3-B, D4-B, D5-A, D6-A, D8-C`; thiết kế hiện hành ở [design.md §0](../packet-security/design.md). Hồ sơ dưới đây là nghiên cứu lưu trữ, gồm cả phương án bị loại.

Operator Claude đọc mã hiện tại và hai shortlist GPT Sol high
([quyết định D](decision-options-2026-10-07.md), [crypto C](crypto-options-2026-10-07.md)).
Mục tiêu: kiểm xem phương án ⭐ có hợp phần cứng/mã đang có và yêu cầu "tinh gọn" không.
**Chưa qua critic độc lập; chưa prototype/đo.** Người dùng vẫn là người chốt.

## Dữ kiện hệ thống đã đọc

| Dữ kiện | Bằng chứng |
| --- | --- |
| Server chỉ dùng Python stdlib (`http.server`, `sqlite3`, `hmac`…), chạy HTTP thường `0.0.0.0:8000` trên LAN, không có domain/TLS | server/config/config.py:3–4, server/lib/http/http_server.py:11, server/START.md |
| Server chưa có file requirements; mọi phương án crypto sẽ là dependency bên thứ ba đầu tiên của server | `ls server` không có requirements; grep import |
| App đã có Kotlin + MethodChannel (`flexmix/bluetooth_pairing`) | android/.../BluetoothPairing.kt:19,44; machine_share_bluetooth_page.dart:11 |
| App ↔ máy dùng **Bluetooth Classic secure RFCOMM**, không phải BLE | BluetoothPairing.kt:183–184; machine/pairing/machine_bluetooth_pair.py |
| APK release ký bằng debug key | android/app/build.gradle.kts:36 |
| Pubspec chưa có crypto package (chỉ mobile_scanner, qr_flutter) | app/flutter_app/pubspec.yaml |
| Máy: Raspberry Pi 5, Ubuntu 24.04, **màn cảm ứng kiosk**, nút 14/15, máy quét QR USB, máy in nhãn; UI máy nằm ở mã `version1.0`, ngoài repo | FexMix_Munual.html (mục 4.1, 4.10, 4.11); machine/README.md |
| Pi 5 không có TPM gắn sẵn → C4-C/D phải mua HAT | thông số phần cứng công khai; chưa kiểm module cụ thể |
| Cấp máy hiện tại: `create_env` sinh product key, `machine_qr.py` in tem QR | machine/README.md; machine_qr.py. **Lưu ý:** `machine/config/create_env.py` chỉ còn file `.pyc`, thiếu mã nguồn |
| Status máy: GET không token, app gọi N GET song song; list máy đã import `is_online/last_seen_of` | machine_list_get.py:4,26–28; dashboard_controller.dart:105–125; machine_list_request.dart:20–29 |
| Timeout hiện có: heartbeat 5 s/timeout 15 s, poll 8 s, máy urlopen 10 s, lệnh 20 s | server/config/config.py:5–8; machine/server_connection/*.py |

## Kết luận theo từng quyết định

| QĐ | GPT ⭐ | Đề xuất sau đối chiếu | Lý do chính |
| --- | --- | --- | --- |
| D1 | A (2 token) | **B** (máy ký offline) | Nhóm nhỏ, không phải mua; vẫn đúng root offline. A mạnh hơn nếu có ngân sách |
| D2 | A (Roughtime) | **C** nếu chấp nhận đổi design; nếu không thì A | A/B/D đều thêm client mới chưa có thư viện Dart nào được kiểm. C dùng lại chữ ký server sẽ phải xây; server bị chiếm là A3, vốn ngoài bảo đảm. Điều kiện: khóa ký thời gian nằm trong trust package (APK), không phụ thuộc manifest |
| D3 | B | **B** (giữ) | Khớp quy trình hiện có: lúc cài máy đã sinh product key và in tem QR; chỉ thêm sinh cặp khóa máy + admin đăng ký public key |
| D4 | B | **B** (giữ) | Không cần dịch vụ mới; A nếu pilot ít người |
| D5 | B (Caddy, "có domain") | **A** (Python `ssl` stdlib) | Hiện không có domain, chạy LAN bằng IP. A không cài thêm gì; cert tự cấp + pin trong `network_security_config`. Chuyển B khi ra Internet có domain |
| D6 | A | **A** (giữ) | Chưa có fleet production |
| D8 | C | **C** (giữ) | Đã xác nhận trong mã: chỉ thêm 2 trường vào list, bỏ GET không token và N request |
| C1 | A | **A** (giữ) | Pi 5 (Cortex-A76) có lệnh AES phần cứng theo thông số; chưa đo |
| C2 | A (root Ed) | **B** (P-256 cả ba) | Một thuật toán, một bộ vector; Keystore/token/Python đều hỗ trợ P-256; không phụ thuộc firmware YubiKey ≥ 5.7 cho Ed25519 |
| C3 | C (Rust FFI) | **A** (Bouncy Castle + PyHPKE), cần đổi design §2 | App đã dùng MethodChannel; signer Keystore cũng bắt buộc qua Kotlin nên C vẫn cần MethodChannel. A chỉ thêm 1 Gradle dep + `pyhpke` (kéo `cryptography`); C thêm Rust + NDK + cầu FFI |
| C4 | B | **B** (giữ) | Không mua phần cứng; Pi 5 không có TPM sẵn |

Bộ trả lời gợi ý: `D1-B, D2-C, D3-B, D4-B, D5-A, D6-A, D8-C, C1-A, C2-B, C3-A, C4-B`.
Hai mục cần bạn chấp nhận đổi design.md: D2-C (§3–4 kênh thời gian) và C3-A (§2 câu fallback FFI).
Tổng cài thêm của bộ này: app 1 thư viện Gradle (`bcprov-jdk18on`);
server + Pi 2 gói pip (`pyhpke`, `cryptography`); 1 máy tính offline có sẵn để ký root.
Không proxy, không dịch vụ cloud, không phần cứng mới.

## Chỗ shortlist GPT lệch hệ thống (đã sửa chữ trong HTML)

- D3-A ghi "BLE"; hệ thống dùng Bluetooth Classic secure RFCOMM.
- "Chưa biết máy có màn hình/nút": máy có màn cảm ứng, nút, máy quét và máy in, nhưng UI ở `version1.0`.
- D5-B "cho nhóm nhỏ có domain": hiện chưa có domain.
- C3-A/B "cần mở fallback FFI": đúng về chữ design, nhưng app đã có MethodChannel và Keystore buộc phải dùng nó.

## Giới hạn

Không kiểm lại API PyHPKE/Bouncy Castle, Keystore Ed25519, AES trên Pi 5 bằng chạy thử.
Nguồn GPT dẫn được giữ trong HTML; các nhận định trên là đối chiếu mã, không phải số đo.
