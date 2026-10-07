> Cập nhật review 06/10/2026: [design.md](design.md) là nguồn quyết định hiện hành. Nội dung bên dưới là nghiên cứu/backlog trước review; không dùng các lựa chọn cũ trái design.md để triển khai.

> Hồ sơ nội bộ cho agent. Chuyển từ tài liệu HTML ngày 06/10/2026; nội dung và bằng chứng cũ được giữ, chưa kiểm lại sản phẩm. Sơ đồ gốc giữ dưới dạng mã SVG trong khối XML.

MIDDLEWARE BẢO VỆ GÓI TIN

# Giao thức bảo vệ hai chiều

Mã hóa trước gửi; xác thực, giải mã và kiểm quyền trước xử lý.

HTML offline · Theo mẫu hiện có · Đề xuất cần kiểm chứng

## Hướng giao thức cần prototype

Đề xuất envelope phiên bản hóa: mã hóa inner payload bằng AEAD; metadata có encoding duy nhất được ràng buộc bằng AAD; nếu dùng chữ ký độc lập, ký ciphertext và context HTTP đã quy định. Verify chữ ký ngoài trước giải mã giúp xác thực sender trước xử lý plaintext. Không mặc định mọi ứng dụng phải có cả chữ ký và MAC: lựa chọn xác thực phải khớp trust model.

[HPKE (RFC 9180)](https://www.rfc-editor.org/rfc/rfc9180.html) là ứng viên kết hợp KEM, KDF và AEAD. Base mode không chứng minh sender đã được ủy quyền. Hai chiều, replay và forward secrecy cần đặc tả riêng; không coi HPKE là giao thức phiên hoàn chỉnh. So sánh với session AEAD dùng handshake chuẩn qua thư viện; đánh giá hỗ trợ thực tế trước chọn.

Phía gửi — plaintext chỉ tồn tại trong đầu cuối

```xml
<svg aria-label="Phía gửi — plaintext chỉ tồn tại trong đầu cuối" role="img" viewbox="0 0 1000 450" xmlns="http://www.w3.org/2000/svg"><rect fill="#e4f3f0" height="64" rx="8" stroke="#218777" width="800" x="100" y="10"></rect><text fill="#17354e" font-size="18" text-anchor="middle" x="500" y="35">Ý định và policy thao tác</text><text fill="#486074" font-size="14" text-anchor="middle" x="500" y="58">Debounce cho sửa/read; khóa submit cho mutation</text><path d="M500 80 V100" stroke="#218777" stroke-width="2"></path><path d="M494 94 L500 100 L506 94" fill="none" stroke="#218777" stroke-width="2"></path><rect fill="#e4f3f0" height="64" rx="8" stroke="#218777" width="800" x="100" y="100"></rect><text fill="#17354e" font-size="18" text-anchor="middle" x="500" y="125">Operation ID → serialize một lần</text><text fill="#486074" font-size="14" text-anchor="middle" x="500" y="148">Giữ inner bytes và fingerprint ổn định qua retry</text><path d="M500 170 V190" stroke="#218777" stroke-width="2"></path><path d="M494 184 L500 190 L506 184" fill="none" stroke="#218777" stroke-width="2"></path><rect fill="#e4f3f0" height="64" rx="8" stroke="#218777" width="800" x="100" y="190"></rect><text fill="#17354e" font-size="18" text-anchor="middle" x="500" y="215">Mã hóa AEAD</text><text fill="#486074" font-size="14" text-anchor="middle" x="500" y="238">Khóa đúng chiều; IV không lặp theo key; AAD chứa context</text><path d="M500 260 V280" stroke="#218777" stroke-width="2"></path><path d="M494 274 L500 280 L506 274" fill="none" stroke="#218777" stroke-width="2"></path><rect fill="#e4f3f0" height="64" rx="8" stroke="#218777" width="800" x="100" y="280"></rect><text fill="#17354e" font-size="18" text-anchor="middle" x="500" y="305">Ký envelope/context nếu profile yêu cầu</text><text fill="#486074" font-size="14" text-anchor="middle" x="500" y="328">Ciphertext, method, đích, version, key ID, nonce và operation ID</text><path d="M500 350 V370" stroke="#218777" stroke-width="2"></path><path d="M494 364 L500 370 L506 364" fill="none" stroke="#218777" stroke-width="2"></path><rect fill="#e4f3f0" height="64" rx="8" stroke="#218777" width="800" x="100" y="370"></rect><text fill="#17354e" font-size="18" text-anchor="middle" x="500" y="395">Gửi HTTPS</text><text fill="#486074" font-size="14" text-anchor="middle" x="500" y="418">Mỗi attempt có freshness mới; response cũng phải được xác minh</text></svg>
```

Luồng đề xuất; chưa triển khai hoặc kiểm chứng trên thiết bị.

Phía nhận — packet lỗi không vào nghiệp vụ

```xml
<svg aria-label="Phía nhận — packet lỗi không vào nghiệp vụ" role="img" viewbox="0 0 1000 540" xmlns="http://www.w3.org/2000/svg"><rect fill="#e4f3f0" height="64" rx="8" stroke="#218777" width="800" x="100" y="10"></rect><text fill="#17354e" font-size="18" text-anchor="middle" x="500" y="35">Framing và envelope có giới hạn</text><text fill="#486074" font-size="14" text-anchor="middle" x="500" y="58">Giới hạn header/ciphertext; policy version/suite/key ID</text><path d="M500 80 V100" stroke="#218777" stroke-width="2"></path><path d="M494 94 L500 100 L506 94" fill="none" stroke="#218777" stroke-width="2"></path><rect fill="#e4f3f0" height="64" rx="8" stroke="#218777" width="800" x="100" y="100"></rect><text fill="#17354e" font-size="18" text-anchor="middle" x="500" y="125">Verify nguồn và context</text><text fill="#486074" font-size="14" text-anchor="middle" x="500" y="148">Chữ ký nếu dùng; không tin key/algorithm tự khai</text><path d="M500 170 V190" stroke="#218777" stroke-width="2"></path><path d="M494 184 L500 190 L506 184" fill="none" stroke="#218777" stroke-width="2"></path><rect fill="#e4f3f0" height="64" rx="8" stroke="#218777" width="800" x="100" y="190"></rect><text fill="#17354e" font-size="18" text-anchor="middle" x="500" y="215">AEAD authenticate/decrypt</text><text fill="#486074" font-size="14" text-anchor="middle" x="500" y="238">Không sử dụng plaintext trước khi tag hợp lệ</text><path d="M500 260 V280" stroke="#218777" stroke-width="2"></path><path d="M494 274 L500 280 L506 274" fill="none" stroke="#218777" stroke-width="2"></path><rect fill="#e4f3f0" height="64" rx="8" stroke="#218777" width="800" x="100" y="280"></rect><text fill="#17354e" font-size="18" text-anchor="middle" x="500" y="305">Freshness và claim replay atomic</text><text fill="#486074" font-size="14" text-anchor="middle" x="500" y="328">Ghi nonce sau xác minh mật mã; bind danh tính/đích/chiều</text><path d="M500 350 V370" stroke="#218777" stroke-width="2"></path><path d="M494 364 L500 370 L506 364" fill="none" stroke="#218777" stroke-width="2"></path><rect fill="#e4f3f0" height="64" rx="8" stroke="#218777" width="800" x="100" y="370"></rect><text fill="#17354e" font-size="18" text-anchor="middle" x="500" y="395">Parse payload → phiên/quyền → idempotency</text><text fill="#486074" font-size="14" text-anchor="middle" x="500" y="418">Giới hạn plaintext và JSON; vẫn giữ quyền/transaction ở feature</text><path d="M500 440 V460" stroke="#218777" stroke-width="2"></path><path d="M494 454 L500 460 L506 454" fill="none" stroke="#218777" stroke-width="2"></path><rect fill="#e4f3f0" height="64" rx="8" stroke="#218777" width="800" x="100" y="460"></rect><text fill="#17354e" font-size="18" text-anchor="middle" x="500" y="485">Nghiệp vụ → bảo vệ response</text><text fill="#486074" font-size="14" text-anchor="middle" x="500" y="508">Status và request binding được xác thực; không tin lỗi chưa verify</text></svg>
```

Luồng đề xuất; chưa triển khai hoặc kiểm chứng trên thiết bị.

## Hợp đồng dữ liệu cần khóa

| Thành phần | Yêu cầu |
| --- | --- |
| version / suite / kid | Allowlist phía server theo record khóa; không fallback unsigned hoặc chọn alg tùy client. |
| audience / direction / method / target | Bind tới đúng đích, route và query; quy tắc proxy rewrite rõ, không tin forwarded header tùy ý. |
| request ID / created / expiry / replay nonce | Chống chuyển context và replay; timestamp một mình không đủ. |
| operation ID | Chỉ cùng ý định nghiệp vụ; signed/AAD để không bị đổi. |
| AEAD IV / ciphertext / tag | Encoding/độ dài chính xác theo suite; IV khác replay nonce và operation ID. |
| response status / request binding | Không nhận nhầm response; poll command bind máy, command ID, expiry và operation. |
| limits / encoding / error | Không giải nén/parse vô hạn; lỗi proxy unsigned chỉ là lỗi transport. |

## Byte và chuẩn chữ ký

Serialize một lần, xử lý chính byte UTF-8 sẽ truyền. Không JSON decode rồi encode lại để kiểm digest. [RFC 9530](https://www.rfc-editor.org/rfc/rfc9530.html) định nghĩa Content-Digest; phải tự tính lại và xác thực giá trị đó. [RFC 9421](https://www.rfc-editor.org/rfc/rfc9421.html) là hướng chuẩn hóa chữ ký thành phần HTTP; cần profile bắt buộc rõ và chống replay. Envelope ứng dụng tự thiết kế không được gọi là RFC-compliant khi chưa thực hiện đúng chuẩn.

Nếu cần canonical JSON, dùng đầy đủ [JCS RFC 8785](https://www.rfc-editor.org/rfc/rfc8785.html), không chỉ sort keys. Đặc tả reject duplicate keys, số không hữu hạn, Unicode lỗi, GET body rỗng, query escaping và content encoding. Test Dart–Python byte-exact.

## Relay hai chặng

App gửi ý định đã bảo vệ tới server. Server kiểm quyền, giải mã và tạo command riêng cho máy; không chuyển token app xuống máy. Máy verify poll response/command trước `handle_command`; result phải bind machine, command và operation. Mã hóa cả response lỗi hợp lệ; bootstrap trước enrollment cần policy riêng và trust server đã xác thực qua TLS.
