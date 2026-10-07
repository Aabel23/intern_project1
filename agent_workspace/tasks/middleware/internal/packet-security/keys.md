> Cập nhật review 06/10/2026: [design.md](design.md) là nguồn quyết định hiện hành. Nội dung bên dưới là nghiên cứu/backlog trước review; không dùng các lựa chọn cũ trái design.md để triển khai.

> Hồ sơ nội bộ cho agent. Chuyển từ tài liệu HTML ngày 06/10/2026; nội dung và bằng chứng cũ được giữ, chưa kiểm lại sản phẩm. Sơ đồ gốc giữ dưới dạng mã SVG trong khối XML.

MIDDLEWARE BẢO VỆ GÓI TIN

# Quản lý khóa và giới hạn bảo mật

Không có một thuật toán đơn lẻ giải quyết enrollment, lộ khóa và phục hồi.

HTML offline · Theo mẫu hiện có · Đề xuất cần kiểm chứng

## Thiết kế khóa quan trọng hơn tên thuật toán

Tách khóa mã hóa và khóa ký, tách chiều request/response, app/server/machine và môi trường. KDF có domain separation theo profile; không dùng cùng byte key cho mọi mục đích. CSPRNG cho material khóa và ID ngẫu nhiên; secret không xuất log, QR công khai hoặc APK chung.

Ứng viên AEAD: AES-GCM và ChaCha20-Poly1305. Ứng viên ký: Ed25519 và ECDSA P-256. Đây là shortlist nghiên cứu, chưa chốt suite hay dependency. Đo trên Flutter/mobile và máy thật: thư viện, hardware-backed storage, kích thước, latency, nonce persistence và vectors. Không tự viết primitive hoặc chọn chỉ vì số bit lớn.

## Lifecycle bắt buộc

| Bước | Công việc / điều kiện |
| --- | --- |
| Trust ban đầu | TLS xác minh certificate; public key server lấy qua kênh tin cậy. Pinning nếu chọn phải có rotation/recovery; không bỏ TLS validation. |
| App enrollment | Key riêng từng installation; bind public key với phiên/người dùng đã xác thực. Tự khai public key chưa chứng minh danh tính. |
| Machine enrollment | Provisioning/owner confirmation đáng tin; product key hiện có cần threat review vì người lấy key có thể giả máy. |
| Issuance và binding | Credential→principal/session/device, policy suite, mục đích, chiều, thời hạn. Token proof-binding cần thay hợp đồng và schema đồng bộ. |
| Lưu trữ | Private key mobile bằng khả năng secure storage của nền tảng; máy/server secret store và quyền file; không hứa mọi thiết bị có phần cứng an toàn. |
| Rotation | active/retiring/revoked; overlap có hạn; đang retry được xử lý rõ; không nonce/key reuse khi restart hoặc restore backup. |
| Revocation và mất thiết bị | Thu hồi key/session; không trả cached sensitive result khi mất quyền; recovery không mở đường bỏ verify. |
| Xóa và forward secrecy | Xóa key cũ theo policy. Static recipient-key encryption không tự bảo vệ ciphertext cũ nếu private key đó bị lộ. |

## HMAC hay asymmetric?

HMAC phù hợp khi hai đầu có secret riêng được provision và bảo quản; server phải giữ secret có thể dùng được, không chỉ hash. Asymmetric giúp server xác minh bằng public key, nhưng private key, enrollment và binding vẫn phải bảo vệ. Không biến hash token đang lưu thành shared secret, và không HMAC bằng token đang gửi trong cùng payload.

Nguồn lifecycle: [OWASP Key Management](https://cheatsheetseries.owasp.org/cheatsheets/Key_Management_Cheat_Sheet.html). Yêu cầu IV/nonce duy nhất và AAD xác thực: [RFC 5116](https://www.rfc-editor.org/rfc/rfc5116.html). Thiết kế cụ thể ở bảng trên là đề xuất cho hệ thống này.

## Đánh giá “bất khả truy”

Mục tiêu khả thi là người không có khóa không đọc được payload trong threat model đã chốt, không sửa/giả mạo gói mà hệ thống chấp nhận, và không kích hoạt lại nghiệp vụ bằng packet cũ. Mã hóa không làm traffic vô hình: IP, thời điểm, lưu lượng và route HTTP ở nơi TLS kết thúc có thể vẫn thấy. Padding chỉ giảm một phần suy luận kích thước, có chi phí cần đo.

Plaintext ở UI, RAM đầu cuối, log, crash dump hoặc database sau giải mã nằm ngoài bảo vệ wire encryption. Cần retention/redaction và quyền truy cập riêng. Không claim anonymity, forward secrecy hay kháng lượng tử nếu suite/threat model chưa chứng minh.
