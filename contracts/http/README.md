# Mẫu giao thức HTTP

Thư mục này gom các mẫu gói tin HTTP theo hai lớp. Hợp đồng chuẩn vẫn là [`../messages/`](../messages/) và [`../COMPATIBILITY.md`](../COMPATIBILITY.md); khi mâu thuẫn, [`../messages/v2-decisions.md`](../messages/v2-decisions.md) được ưu tiên.

## Hai lớp cần phân biệt

1. `wire/` minh họa **body HTTP trên đường truyền**. [`app-request.json`](wire/app-request.json) không có chữ ký máy; [`machine-request.json`](wire/machine-request.json) có chữ ký máy. [`response.json`](wire/response.json) là phản hồi mã hóa. [`preopen-error.json`](wire/preopen-error.json) là lỗi công khai trước khi server mở được request. Lỗi nghiệp vụ sau khi mở request vẫn nằm trong response mã hóa. Các chuỗi `EXAMPLE_ONLY` chỉ giữ chỗ, không phải bản mã, chữ ký, khóa hay vector kiểm thử.
2. `flows/` minh họa **plaintext bên trong phong bì sau giải mã**, sắp theo luồng. Đây không phải body được gửi rõ qua HTTP. Mỗi request gồm `{auth,body}`; response là payload nghiệp vụ `{v,ok,data}` hoặc `{v,ok,error}`.

Tất cả request dùng POST. Đường dẫn HTTP phải trùng `route` trong request envelope. Các file dưới đây là mẫu để đọc; không gửi trực tiếp, không dùng làm fixture mật mã hoặc test tương thích.

| Luồng | Mẫu | Hợp đồng |
|---|---|---|
| Tài khoản | [`register.request`](flows/account/register.request.plaintext.json), [`register.mail-error`](flows/account/register.mail-error.plaintext.json), [`login.response`](flows/account/login.response.plaintext.json) | [`auth.md`](../messages/auth.md) |
| Nhận máy | [`begin.request`](flows/claim/begin.request.plaintext.json), [`begin.owned-error`](flows/claim/begin.owned-error.plaintext.json) | [`v2-decisions.md`](../messages/v2-decisions.md), mục Claim |
| Đọc trạng thái qua relay | [`status.request`](flows/relay/status.request.plaintext.json) → [`poll.response`](flows/relay/poll.response.plaintext.json) → [`result.request`](flows/relay/result.request.plaintext.json) → [`status.response`](flows/relay/status.response.plaintext.json); nhánh [`timeout`](flows/relay/status.timeout-error.plaintext.json), [`invalid-version`](flows/relay/status.invalid-version.request.plaintext.json) | [`v2-decisions.md`](../messages/v2-decisions.md), mục D7+D8 |

Các mẫu trước đây ở `contracts/examples/` đã được gộp vào đây. Mẫu `invalid-status-data` cũ không còn là ví dụ lỗi 400 đúng theo v2: server chuyển `data` của lệnh relay, máy mới xử lý nội dung. Mẫu claim begin đã đổi sang `serial`; mẫu poll đã bỏ `deadline_at` theo v2. Không có fixture claim proof hoặc ciphertext hợp lệ trong thư mục này; vector mật mã thuộc `tests/fixtures/crypto/`.
