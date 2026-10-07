> Cập nhật review 06/10/2026: [design.md](design.md) là nguồn quyết định hiện hành. Nội dung bên dưới là nghiên cứu/backlog trước review; không dùng các lựa chọn cũ trái design.md để triển khai.

> Hồ sơ nội bộ cho agent. Chuyển từ tài liệu HTML ngày 06/10/2026; nội dung và bằng chứng cũ được giữ, chưa kiểm lại sản phẩm. Sơ đồ gốc giữ dưới dạng mã SVG trong khối XML.

MIDDLEWARE BẢO VỆ GÓI TIN

# Debounce, chống trùng và chống phát lại

Gửi ít hơn, không chạy nghiệp vụ hai lần, và không chấp nhận packet cũ.

HTML offline · Theo mẫu hiện có · Đề xuất cần kiểm chứng

## Ba cơ chế khác nhau

| Cơ chế | Định danh / nơi thực thi | Quy tắc |
| --- | --- | --- |
| Debounce | Action + target, trước gửi | Gộp sửa/read trong khoảng chờ đã đo. Mutation dùng in-flight lock; không debounce toàn client, heartbeat/poll/result. |
| Anti-replay | Transport nonce, receiver | Mỗi attempt mới; claim UNIQUE atomic scoped credential/version/direction sau verify. Store tồn tại đủ cửa sổ nhận và qua restart. |
| Idempotency | Operation ID + immutable fingerprint | Retry giữ ID nghiệp vụ nhưng nonce/time/signature/IV mới. Cùng ID khác nội dung/context → conflict. |

Retry an toàn — ba loại ID

```xml
<svg aria-label="Retry an toàn — ba loại ID" role="img" viewbox="0 0 1000 450" xmlns="http://www.w3.org/2000/svg"><rect fill="#e4f3f0" height="64" rx="8" stroke="#218777" width="800" x="100" y="10"></rect><text fill="#17354e" font-size="18" text-anchor="middle" x="500" y="35">Người dùng thực hiện một hành động</text><text fill="#486074" font-size="14" text-anchor="middle" x="500" y="58">Operation ID ổn định qua mọi retry của hành động</text><path d="M500 80 V100" stroke="#218777" stroke-width="2"></path><path d="M494 94 L500 100 L506 94" fill="none" stroke="#218777" stroke-width="2"></path><rect fill="#e4f3f0" height="64" rx="8" stroke="#218777" width="800" x="100" y="100"></rect><text fill="#17354e" font-size="18" text-anchor="middle" x="500" y="125">Attempt mạng A hoặc B</text><text fill="#486074" font-size="14" text-anchor="middle" x="500" y="148">Request ID/replay nonce/time/AEAD IV mới mỗi attempt</text><path d="M500 170 V190" stroke="#218777" stroke-width="2"></path><path d="M494 184 L500 190 L506 184" fill="none" stroke="#218777" stroke-width="2"></path><rect fill="#e4f3f0" height="64" rx="8" stroke="#218777" width="800" x="100" y="190"></rect><text fill="#17354e" font-size="18" text-anchor="middle" x="500" y="215">Server kiểm phiên và quyền hiện hành</text><text fill="#486074" font-size="14" text-anchor="middle" x="500" y="238">Sau verify + anti-replay mới claim operation ledger</text><path d="M500 260 V280" stroke="#218777" stroke-width="2"></path><path d="M494 274 L500 280 L506 274" fill="none" stroke="#218777" stroke-width="2"></path><rect fill="#e4f3f0" height="64" rx="8" stroke="#218777" width="800" x="100" y="280"></rect><text fill="#17354e" font-size="18" text-anchor="middle" x="500" y="305">Command tới máy</text><text fill="#486074" font-size="14" text-anchor="middle" x="500" y="328">Command identity bền; bind operation; máy có dedup ledger</text><path d="M500 350 V370" stroke="#218777" stroke-width="2"></path><path d="M494 364 L500 370 L506 364" fill="none" stroke="#218777" stroke-width="2"></path><rect fill="#e4f3f0" height="64" rx="8" stroke="#218777" width="800" x="100" y="370"></rect><text fill="#17354e" font-size="18" text-anchor="middle" x="500" y="395">Completed / pending / unknown</text><text fill="#486074" font-size="14" text-anchor="middle" x="500" y="418">Kết quả mất không chứng minh tác vụ chưa thực hiện</text></svg>
```

Luồng đề xuất; chưa triển khai hoặc kiểm chứng trên thiết bị.

## Ledger và lỗi cần xử lý

Ledger server scope principal + action/target + operation ID. Fingerprint từ inner payload/context ổn định, không từ ciphertext vốn đổi mỗi retry. Atomic claim chống race; trạng thái in-progress/completed/unknown, kết quả và expiry theo policy. Không giữ transaction SQLite mở trong lúc đợi máy. Không xóa pending rồi chạy lại khi owner crash mà side effect chưa biết.

Server dedup không đủ nếu máy đã làm và result mất. Machine ledger cùng transaction dữ liệu khi có thể; actuator vật lý có cửa sổ crash giữa tác động và ghi ledger, cần đối soát/recovery. Không hứa exactly-once vật lý.

Replay store không được đuổi nonce còn hiệu lực chỉ vì đầy. Giới hạn admission, fail closed cho writes khi store không sẵn sàng, clock-skew policy rõ. Khóa bị revoke vẫn chặn truy cập cached outcome. [RFC 9110 §9.2.2](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.2.2) là căn cứ thận trọng với retry thao tác không idempotent; ledger và state machine trên là đề xuất ứng dụng.

## Policy theo thao tác

| Luồng | Hướng |
| --- | --- |
| Search/edit/read UI | Debounce theo target; cancel/stale response policy. |
| Refill/menu update/remove/share | Submit lock + operation ID; không nuốt hai ý định khác nhau. |
| Heartbeat | Fresh attempt; không cached outcome dài hạn khiến trạng thái sống giả. |
| Poll | Mỗi lượt request mới; command dedup độc lập. |
| Result resend | Giữ command/result identity; mới packet nonce/IV; kết quả xung đột bị chặn. |
| Login/OTP | Limiter và bootstrap policy; không cache/retry tạo token hoặc OTP thiếu lifecycle định nghĩa. |
