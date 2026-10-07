> Cập nhật review 06/10/2026: [design.md](design.md) là nguồn quyết định hiện hành. Nội dung bên dưới là nghiên cứu/backlog trước review; không dùng các lựa chọn cũ trái design.md để triển khai.

> Hồ sơ nội bộ cho agent. Chuyển từ tài liệu HTML ngày 06/10/2026; nội dung và bằng chứng cũ được giữ, chưa kiểm lại sản phẩm. Sơ đồ gốc giữ dưới dạng mã SVG trong khối XML.

MIDDLEWARE BẢO VỆ GÓI TIN

# Nghiên cứu middleware mã hóa gói tin

Lớp mã hóa hai chiều của hệ thống, có quản lý khóa và cơ chế chống lặp độc lập.

HTML offline · Theo mẫu hiện có · Đề xuất cần kiểm chứng

## Mục tiêu đã xác nhận

Middleware ở đây là lớp bảo vệ gói tin trước khi gửi và kiểm chứng trước khi giao cho endpoint nghiệp vụ hoặc máy thực thi. Phạm vi gồm mã hóa payload request và response riêng của hệ thống, xác thực nguồn gửi, chống sửa đổi, chống phát lại, chống xử lý trùng và debounce. HTTPS tiếp tục bảo vệ đường truyền.

“Mã hóa riêng” nghĩa là hệ thống sở hữu envelope, khóa, chính sách và lifecycle; dùng thuật toán/thư viện đã được kiểm chứng. Không tự phát minh thuật toán mật mã. Không có cam kết “bất khả truy” tuyệt đối: bên được phép giải mã và thiết bị bị chiếm quyền vẫn có thể đọc plaintext.

## Bản đồ kỹ thuật cần hiểu

| Kỹ thuật | Bảo vệ gì | Giới hạn / định hướng |
| --- | --- | --- |
| HTTPS/TLS | Đường truyền và danh tính server | Giữ bắt buộc; app-layer encryption không thay TLS. |
| AEAD: AES-GCM hoặc ChaCha20-Poly1305 | Bí mật payload và phát hiện sửa ciphertext/AAD | Ứng viên; chọn suite sau prototype Dart–Python, không ghép AES-CBC + hash tùy tiện. |
| Ký số: Ed25519 hoặc ECDSA P-256 | Bằng chứng sở hữu private key của bên gửi | Không mã hóa; cần public key tin cậy, binding danh tính và revoke. |
| HMAC | Xác thực bằng secret chung | Bên nào có secret cũng tạo MAC; cần key riêng, không dùng bearer đang truyền. |
| KEM/key agreement + KDF | Thiết lập và phân tách khóa | Nghiên cứu HPKE hoặc giao thức có thư viện phù hợp; không tự viết handshake ECDH. |
| Hash / Content-Digest | Fingerprint byte nội dung | Hash không khóa không chứng minh ai gửi. |
| Replay nonce + cửa sổ thời gian | Chặn packet hợp lệ bị gửi lại | Claim atomic, bền qua restart, sau kiểm mật mã. |
| Operation ID + ledger | Chặn nghiệp vụ chạy lại khi retry | ID ổn định, fingerprint/context cố định, kiểm cả server và máy. |
| Debounce / in-flight lock | Giảm thao tác/gửi lặp phía client | Không phải hàng rào bảo mật server. |
| Secure storage / rotation / revoke | Giảm khả năng lộ khóa và giới hạn thiệt hại | Không nhúng secret chung APK; cần recovery khi mất thiết bị. |
| Padding / hạn chế log | Giảm lộ kích thước hoặc plaintext qua vận hành | Không ẩn hoàn toàn IP, thời gian hay endpoint khỏi hạ tầng mạng. |
| Rate limit / body bounds / version allowlist | Giữ tài nguyên và chống downgrade | Mật mã không ngăn DoS; chi phí verify/decrypt phải có ngân sách. |

## Hiện trạng phải sửa trước khi tích hợp

Flutter có hai đường gửi độc lập: `core/http_json.dart` và `core/server_client.dart`. Machine có `machine_server_request.py` và heartbeat tự tạo request. Server đọc/trả JSON qua `server/lib/http/http_json.py`. Chưa có pipeline gói tin ký/mã hóa chung trong các đường này.

Server chỉ lưu hash token và hash product key. Không thể dùng các hash này để xác minh HMAC bằng secret gốc. Không dùng token/product key vừa có trong payload làm khóa ký. Poll response chứa lệnh máy nên phải bảo vệ chiều nhận, không chỉ request.

Đối chiếu: [user_session.py](../../../../../server/lib/security/user_session.py), [http_json.py](../../../../../server/lib/http/http_json.py), [machine_transport.py](../../../../../server/lib/machine/machine_transport.py). Các nhận định trên là đọc mã, chưa phải kết quả kiểm tấn công.

## Phạm vi bảo mật thực tế

| Tình huống | Lớp bảo vệ dự kiến |
| --- | --- |
| Nghe lén mạng | HTTPS + AEAD payload. |
| TLS kết thúc ở proxy | Proxy không có khóa ứng dụng thì không đọc payload; vẫn thấy routing/metadata. |
| Server nghiệp vụ cần xử lý | Server được giải mã; đây là hai chặng app↔server và machine↔server. |
| Muốn server cũng không đọc được app→machine | Cần mô hình end-to-end riêng; ảnh hưởng kiểm quyền/nghiệp vụ, chưa tự đổi kiến trúc đã chốt. |
| Lộ khóa dài hạn và ciphertext cũ | Forward secrecy phụ thuộc giao thức khóa; thêm mã hóa không mặc định có thuộc tính này. |
| Máy/app bị chiếm quyền | Plaintext trước mã hóa/sau giải mã và thao tác hợp lệ có thể bị lộ/lạm dụng. |

## Nguồn nền

[OWASP TLS](https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Security_Cheat_Sheet.html) cho vai trò đường truyền; [RFC 5116](https://www.rfc-editor.org/rfc/rfc5116.html) cho AEAD; [RFC 9180](https://www.rfc-editor.org/rfc/rfc9180.html) cho HPKE. Các đề xuất triển khai trong bộ tài liệu là thiết kế ứng dụng, chưa phải profile chuẩn đã hoàn tất.
