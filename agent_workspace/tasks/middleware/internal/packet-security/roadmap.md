> Cập nhật review 06/10/2026: [design.md](design.md) là nguồn quyết định hiện hành. Nội dung bên dưới là nghiên cứu/backlog trước review; không dùng các lựa chọn cũ trái design.md để triển khai.

> Hồ sơ nội bộ cho agent. Chuyển từ tài liệu HTML ngày 06/10/2026; nội dung và bằng chứng cũ được giữ, chưa kiểm lại sản phẩm. Sơ đồ gốc giữ dưới dạng mã SVG trong khối XML.

MIDDLEWARE BẢO VỆ GÓI TIN

# Kế hoạch team AI cho middleware gói tin

32 phase con có nghiên cứu, định hướng, requirements, nhiệm vụ và gate.

HTML offline · Theo mẫu hiện có · Đề xuất cần kiểm chứng

## Lộ trình triển khai đúng phạm vi

8 giai đoạn lớn của cả team AI, mỗi giai đoạn có 4 phase con. P0→P1→P2→P3→P4→P5→P6→P7. Thiết kế replay/idempotency được nghiên cứu từ P1 để tránh sửa wire format muộn. Mã hóa payload là yêu cầu chính trong P1–P3, không phải nhánh tùy chọn cuối kế hoạch.

Đây là kế hoạch nghiên cứu/triển khai mới. Hồ sơ HTTP/runtime cũ là backlog hỗ trợ; không còn đại diện đầy đủ cho middleware người dùng yêu cầu.

## P0 · Khảo sát và threat model

Đầu vào: evidence của giai đoạn trước; P0 nhận code hiện tại và yêu cầu người dùng. Lead chỉ chuyển gate khi đặc tả, vectors, thay đổi và giới hạn có thể review.

<a id="p0-1"></a>

### P0.1 · Inventory hai chiều

| Mục | Chi tiết |
| --- | --- |
| Nghiên cứu và thông tin | Đối chiếu code và chuyên đề liên quan; tách dữ kiện đã đọc, lựa chọn đề xuất và điều chưa đo. Ghi nguồn/phiên bản và giả thuyết vào HTML trước patch. |
| Định hướng / việc làm | Đọc đủ auth/dashboard/heartbeat/poll/result/GET/send_json; lập packet matrix và vị trí plaintext. |
| Yêu cầu bắt buộc | Không bỏ sót outbound hay response; xác định người được giải mã. |
| Hiện vật / gate | Bản đồ callers và trust boundaries; spec và output kiểm chứng được reviewer/security đọc, không chỉ checklist đánh dấu. |
| Phân công cả team | Planner chốt scope/callers/dependencies → tester chuẩn bị vector/fault cases → coder triển khai theo kiến trúc khóa → reviewer kiểm hợp đồng/transaction → cybersecurity kiểm threat/key → lead tổng hợp gate. |
| Handoff và kiểm | Bàn giao spec, file/caller matrix, vectors, patch, lệnh và output kiểm, residual risks. Toàn bộ test/simulator ở tests/. Không coi test mô phỏng là evidence thiết bị thật. |
| Lỗi / rollback | Gate không đạt thì giữ phase đang mở; ghi blocker và recovery. Patch version/schema có migration/quay lui; packet invalid không được fallback plaintext hoặc unsigned. |

<a id="p0-2"></a>

### P0.2 · Phân loại hành động

| Mục | Chi tiết |
| --- | --- |
| Nghiên cứu và thông tin | Đối chiếu code và chuyên đề liên quan; tách dữ kiện đã đọc, lựa chọn đề xuất và điều chưa đo. Ghi nguồn/phiên bản và giả thuyết vào HTML trước patch. |
| Định hướng / việc làm | Liệt kê read/write, tác động vật lý và retry đang có; phân biệt ý định mới với retry. |
| Yêu cầu bắt buộc | Không áp một debounce/idempotency policy cho mọi route. |
| Hiện vật / gate | Action-policy matrix; spec và output kiểm chứng được reviewer/security đọc, không chỉ checklist đánh dấu. |
| Phân công cả team | Planner chốt scope/callers/dependencies → tester chuẩn bị vector/fault cases → coder triển khai theo kiến trúc khóa → reviewer kiểm hợp đồng/transaction → cybersecurity kiểm threat/key → lead tổng hợp gate. |
| Handoff và kiểm | Bàn giao spec, file/caller matrix, vectors, patch, lệnh và output kiểm, residual risks. Toàn bộ test/simulator ở tests/. Không coi test mô phỏng là evidence thiết bị thật. |
| Lỗi / rollback | Gate không đạt thì giữ phase đang mở; ghi blocker và recovery. Patch version/schema có migration/quay lui; packet invalid không được fallback plaintext hoặc unsigned. |

<a id="p0-3"></a>

### P0.3 · Mục tiêu bí mật

| Mục | Chi tiết |
| --- | --- |
| Nghiên cứu và thông tin | Đối chiếu code và chuyên đề liên quan; tách dữ kiện đã đọc, lựa chọn đề xuất và điều chưa đo. Ghi nguồn/phiên bản và giả thuyết vào HTML trước patch. |
| Định hướng / việc làm | Chốt proxy có được đọc không, server có được đọc không; đánh giá metadata, endpoint compromise, key exposure. |
| Yêu cầu bắt buộc | Không claim bất khả truy; giữ mô hình hai chặng hiện tại. |
| Hiện vật / gate | Threat model và residual risks; spec và output kiểm chứng được reviewer/security đọc, không chỉ checklist đánh dấu. |
| Phân công cả team | Planner chốt scope/callers/dependencies → tester chuẩn bị vector/fault cases → coder triển khai theo kiến trúc khóa → reviewer kiểm hợp đồng/transaction → cybersecurity kiểm threat/key → lead tổng hợp gate. |
| Handoff và kiểm | Bàn giao spec, file/caller matrix, vectors, patch, lệnh và output kiểm, residual risks. Toàn bộ test/simulator ở tests/. Không coi test mô phỏng là evidence thiết bị thật. |
| Lỗi / rollback | Gate không đạt thì giữ phase đang mở; ghi blocker và recovery. Patch version/schema có migration/quay lui; packet invalid không được fallback plaintext hoặc unsigned. |

<a id="p0-4"></a>

### P0.4 · Baseline và dependency

| Mục | Chi tiết |
| --- | --- |
| Nghiên cứu và thông tin | Đối chiếu code và chuyên đề liên quan; tách dữ kiện đã đọc, lựa chọn đề xuất và điều chưa đo. Ghi nguồn/phiên bản và giả thuyết vào HTML trước patch. |
| Định hướng / việc làm | Kiểm fixture hiện hành; inventory thư viện Dart/Python và thiết bị; đo kích thước/latency nền. |
| Yêu cầu bắt buộc | Kết quả test cũ lỗi không coi là hàng rào đạt. |
| Hiện vật / gate | Baseline tái lập và shortlist thư viện; spec và output kiểm chứng được reviewer/security đọc, không chỉ checklist đánh dấu. |
| Phân công cả team | Planner chốt scope/callers/dependencies → tester chuẩn bị vector/fault cases → coder triển khai theo kiến trúc khóa → reviewer kiểm hợp đồng/transaction → cybersecurity kiểm threat/key → lead tổng hợp gate. |
| Handoff và kiểm | Bàn giao spec, file/caller matrix, vectors, patch, lệnh và output kiểm, residual risks. Toàn bộ test/simulator ở tests/. Không coi test mô phỏng là evidence thiết bị thật. |
| Lỗi / rollback | Gate không đạt thì giữ phase đang mở; ghi blocker và recovery. Patch version/schema có migration/quay lui; packet invalid không được fallback plaintext hoặc unsigned. |

## P1 · Đặc tả envelope và liên thông

Đầu vào: evidence của giai đoạn trước; P0 nhận code hiện tại và yêu cầu người dùng. Lead chỉ chuyển gate khi đặc tả, vectors, thay đổi và giới hạn có thể review.

<a id="p1-1"></a>

### P1.1 · Wire format

| Mục | Chi tiết |
| --- | --- |
| Nghiên cứu và thông tin | Đối chiếu code và chuyên đề liên quan; tách dữ kiện đã đọc, lựa chọn đề xuất và điều chưa đo. Ghi nguồn/phiên bản và giả thuyết vào HTML trước patch. |
| Định hướng / việc làm | Định nghĩa version, header/envelope, inner payload, signed fields và AAD encoding. |
| Yêu cầu bắt buộc | Encoding duy nhất; allowlist version/suite; mọi context quan trọng được xác thực. |
| Hiện vật / gate | Spec byte-exact; spec và output kiểm chứng được reviewer/security đọc, không chỉ checklist đánh dấu. |
| Phân công cả team | Planner chốt scope/callers/dependencies → tester chuẩn bị vector/fault cases → coder triển khai theo kiến trúc khóa → reviewer kiểm hợp đồng/transaction → cybersecurity kiểm threat/key → lead tổng hợp gate. |
| Handoff và kiểm | Bàn giao spec, file/caller matrix, vectors, patch, lệnh và output kiểm, residual risks. Toàn bộ test/simulator ở tests/. Không coi test mô phỏng là evidence thiết bị thật. |
| Lỗi / rollback | Gate không đạt thì giữ phase đang mở; ghi blocker và recovery. Patch version/schema có migration/quay lui; packet invalid không được fallback plaintext hoặc unsigned. |

<a id="p1-2"></a>

### P1.2 · Mã hóa và xác thực

| Mục | Chi tiết |
| --- | --- |
| Nghiên cứu và thông tin | Đối chiếu code và chuyên đề liên quan; tách dữ kiện đã đọc, lựa chọn đề xuất và điều chưa đo. Ghi nguồn/phiên bản và giả thuyết vào HTML trước patch. |
| Định hướng / việc làm | So sánh HPKE với session AEAD qua giao thức chuẩn; quyết định chữ ký ngoài/authenticated mode. |
| Yêu cầu bắt buộc | Không tự viết handshake; base encryption không chứng minh sender được ủy quyền. |
| Hiện vật / gate | ADR suite và trust model; spec và output kiểm chứng được reviewer/security đọc, không chỉ checklist đánh dấu. |
| Phân công cả team | Planner chốt scope/callers/dependencies → tester chuẩn bị vector/fault cases → coder triển khai theo kiến trúc khóa → reviewer kiểm hợp đồng/transaction → cybersecurity kiểm threat/key → lead tổng hợp gate. |
| Handoff và kiểm | Bàn giao spec, file/caller matrix, vectors, patch, lệnh và output kiểm, residual risks. Toàn bộ test/simulator ở tests/. Không coi test mô phỏng là evidence thiết bị thật. |
| Lỗi / rollback | Gate không đạt thì giữ phase đang mở; ghi blocker và recovery. Patch version/schema có migration/quay lui; packet invalid không được fallback plaintext hoặc unsigned. |

<a id="p1-3"></a>

### P1.3 · Hai chiều và bootstrap

| Mục | Chi tiết |
| --- | --- |
| Nghiên cứu và thông tin | Đối chiếu code và chuyên đề liên quan; tách dữ kiện đã đọc, lựa chọn đề xuất và điều chưa đo. Ghi nguồn/phiên bản và giả thuyết vào HTML trước patch. |
| Định hướng / việc làm | Đặc tả response binding/status, login/enrollment trước key, logout và lỗi proxy. |
| Yêu cầu bắt buộc | Không tin business error chưa verify; không unsigned fallback. |
| Hiện vật / gate | Request/response/error contract; spec và output kiểm chứng được reviewer/security đọc, không chỉ checklist đánh dấu. |
| Phân công cả team | Planner chốt scope/callers/dependencies → tester chuẩn bị vector/fault cases → coder triển khai theo kiến trúc khóa → reviewer kiểm hợp đồng/transaction → cybersecurity kiểm threat/key → lead tổng hợp gate. |
| Handoff và kiểm | Bàn giao spec, file/caller matrix, vectors, patch, lệnh và output kiểm, residual risks. Toàn bộ test/simulator ở tests/. Không coi test mô phỏng là evidence thiết bị thật. |
| Lỗi / rollback | Gate không đạt thì giữ phase đang mở; ghi blocker và recovery. Patch version/schema có migration/quay lui; packet invalid không được fallback plaintext hoặc unsigned. |

<a id="p1-4"></a>

### P1.4 · Vectors Dart–Python

| Mục | Chi tiết |
| --- | --- |
| Nghiên cứu và thông tin | Đối chiếu code và chuyên đề liên quan; tách dữ kiện đã đọc, lựa chọn đề xuất và điều chưa đo. Ghi nguồn/phiên bản và giả thuyết vào HTML trước patch. |
| Định hướng / việc làm | Tạo vectors tiếng Việt, số, escaping, query, empty body, ciphertext/AAD và chữ ký. |
| Yêu cầu bắt buộc | Byte-exact và negative vectors; không reserialize để verify. |
| Hiện vật / gate | Bộ vectors chuẩn trong tests/; spec và output kiểm chứng được reviewer/security đọc, không chỉ checklist đánh dấu. |
| Phân công cả team | Planner chốt scope/callers/dependencies → tester chuẩn bị vector/fault cases → coder triển khai theo kiến trúc khóa → reviewer kiểm hợp đồng/transaction → cybersecurity kiểm threat/key → lead tổng hợp gate. |
| Handoff và kiểm | Bàn giao spec, file/caller matrix, vectors, patch, lệnh và output kiểm, residual risks. Toàn bộ test/simulator ở tests/. Không coi test mô phỏng là evidence thiết bị thật. |
| Lỗi / rollback | Gate không đạt thì giữ phase đang mở; ghi blocker và recovery. Patch version/schema có migration/quay lui; packet invalid không được fallback plaintext hoặc unsigned. |

## P2 · Khóa, provisioning và recovery

Đầu vào: evidence của giai đoạn trước; P0 nhận code hiện tại và yêu cầu người dùng. Lead chỉ chuyển gate khi đặc tả, vectors, thay đổi và giới hạn có thể review.

<a id="p2-1"></a>

### P2.1 · Storage prototype

| Mục | Chi tiết |
| --- | --- |
| Nghiên cứu và thông tin | Đối chiếu code và chuyên đề liên quan; tách dữ kiện đã đọc, lựa chọn đề xuất và điều chưa đo. Ghi nguồn/phiên bản và giả thuyết vào HTML trước patch. |
| Định hướng / việc làm | Đo signing/encryption với secure storage nền tảng và machine target; kiểm thư viện bằng vectors. |
| Yêu cầu bắt buộc | Không giả định hardware support; private key không vào log. |
| Hiện vật / gate | Prototype và capability matrix; spec và output kiểm chứng được reviewer/security đọc, không chỉ checklist đánh dấu. |
| Phân công cả team | Planner chốt scope/callers/dependencies → tester chuẩn bị vector/fault cases → coder triển khai theo kiến trúc khóa → reviewer kiểm hợp đồng/transaction → cybersecurity kiểm threat/key → lead tổng hợp gate. |
| Handoff và kiểm | Bàn giao spec, file/caller matrix, vectors, patch, lệnh và output kiểm, residual risks. Toàn bộ test/simulator ở tests/. Không coi test mô phỏng là evidence thiết bị thật. |
| Lỗi / rollback | Gate không đạt thì giữ phase đang mở; ghi blocker và recovery. Patch version/schema có migration/quay lui; packet invalid không được fallback plaintext hoặc unsigned. |

<a id="p2-2"></a>

### P2.2 · App binding

| Mục | Chi tiết |
| --- | --- |
| Nghiên cứu và thông tin | Đối chiếu code và chuyên đề liên quan; tách dữ kiện đã đọc, lựa chọn đề xuất và điều chưa đo. Ghi nguồn/phiên bản và giả thuyết vào HTML trước patch. |
| Định hướng / việc làm | Thiết kế enrollment sau auth, session/key proof binding và migration token. |
| Yêu cầu bắt buộc | Public key tự khai chưa là danh tính; chặn key substitution. |
| Hiện vật / gate | Schema/binding và auth flows; spec và output kiểm chứng được reviewer/security đọc, không chỉ checklist đánh dấu. |
| Phân công cả team | Planner chốt scope/callers/dependencies → tester chuẩn bị vector/fault cases → coder triển khai theo kiến trúc khóa → reviewer kiểm hợp đồng/transaction → cybersecurity kiểm threat/key → lead tổng hợp gate. |
| Handoff và kiểm | Bàn giao spec, file/caller matrix, vectors, patch, lệnh và output kiểm, residual risks. Toàn bộ test/simulator ở tests/. Không coi test mô phỏng là evidence thiết bị thật. |
| Lỗi / rollback | Gate không đạt thì giữ phase đang mở; ghi blocker và recovery. Patch version/schema có migration/quay lui; packet invalid không được fallback plaintext hoặc unsigned. |

<a id="p2-3"></a>

### P2.3 · Machine provisioning

| Mục | Chi tiết |
| --- | --- |
| Nghiên cứu và thông tin | Đối chiếu code và chuyên đề liên quan; tách dữ kiện đã đọc, lựa chọn đề xuất và điều chưa đo. Ghi nguồn/phiên bản và giả thuyết vào HTML trước patch. |
| Định hướng / việc làm | Thiết kế liên kết key với máy/owner, QR exposure và luồng thay máy. |
| Yêu cầu bắt buộc | Không dùng product key truyền trong body làm signing key. |
| Hiện vật / gate | Provisioning và ownership proof; spec và output kiểm chứng được reviewer/security đọc, không chỉ checklist đánh dấu. |
| Phân công cả team | Planner chốt scope/callers/dependencies → tester chuẩn bị vector/fault cases → coder triển khai theo kiến trúc khóa → reviewer kiểm hợp đồng/transaction → cybersecurity kiểm threat/key → lead tổng hợp gate. |
| Handoff và kiểm | Bàn giao spec, file/caller matrix, vectors, patch, lệnh và output kiểm, residual risks. Toàn bộ test/simulator ở tests/. Không coi test mô phỏng là evidence thiết bị thật. |
| Lỗi / rollback | Gate không đạt thì giữ phase đang mở; ghi blocker và recovery. Patch version/schema có migration/quay lui; packet invalid không được fallback plaintext hoặc unsigned. |

<a id="p2-4"></a>

### P2.4 · Rotation/revoke

| Mục | Chi tiết |
| --- | --- |
| Nghiên cứu và thông tin | Đối chiếu code và chuyên đề liên quan; tách dữ kiện đã đọc, lựa chọn đề xuất và điều chưa đo. Ghi nguồn/phiên bản và giả thuyết vào HTML trước patch. |
| Định hướng / việc làm | Định nghĩa key epochs, overlap, logout, lost-device recovery, backup restore. |
| Yêu cầu bắt buộc | Tách key theo chiều/mục đích; không nonce reuse hoặc bypass khi revoke. |
| Hiện vật / gate | Lifecycle state machine và runbook; spec và output kiểm chứng được reviewer/security đọc, không chỉ checklist đánh dấu. |
| Phân công cả team | Planner chốt scope/callers/dependencies → tester chuẩn bị vector/fault cases → coder triển khai theo kiến trúc khóa → reviewer kiểm hợp đồng/transaction → cybersecurity kiểm threat/key → lead tổng hợp gate. |
| Handoff và kiểm | Bàn giao spec, file/caller matrix, vectors, patch, lệnh và output kiểm, residual risks. Toàn bộ test/simulator ở tests/. Không coi test mô phỏng là evidence thiết bị thật. |
| Lỗi / rollback | Gate không đạt thì giữ phase đang mở; ghi blocker và recovery. Patch version/schema có migration/quay lui; packet invalid không được fallback plaintext hoặc unsigned. |

## P3 · Middleware mã hóa hai chiều

Đầu vào: evidence của giai đoạn trước; P0 nhận code hiện tại và yêu cầu người dùng. Lead chỉ chuyển gate khi đặc tả, vectors, thay đổi và giới hạn có thể review.

<a id="p3-1"></a>

### P3.1 · Flutter adapters

| Mục | Chi tiết |
| --- | --- |
| Nghiên cứu và thông tin | Đối chiếu code và chuyên đề liên quan; tách dữ kiện đã đọc, lựa chọn đề xuất và điều chưa đo. Ghi nguồn/phiên bản và giả thuyết vào HTML trước patch. |
| Định hướng / việc làm | Bọc cả http_json và ServerClient; encrypt trước write, verify trước UI/auth callback. |
| Yêu cầu bắt buộc | Giữ inner feature contract; credentials nằm trong payload đã bảo vệ. |
| Hiện vật / gate | Patch core transport và caller tests; spec và output kiểm chứng được reviewer/security đọc, không chỉ checklist đánh dấu. |
| Phân công cả team | Planner chốt scope/callers/dependencies → tester chuẩn bị vector/fault cases → coder triển khai theo kiến trúc khóa → reviewer kiểm hợp đồng/transaction → cybersecurity kiểm threat/key → lead tổng hợp gate. |
| Handoff và kiểm | Bàn giao spec, file/caller matrix, vectors, patch, lệnh và output kiểm, residual risks. Toàn bộ test/simulator ở tests/. Không coi test mô phỏng là evidence thiết bị thật. |
| Lỗi / rollback | Gate không đạt thì giữ phase đang mở; ghi blocker và recovery. Patch version/schema có migration/quay lui; packet invalid không được fallback plaintext hoặc unsigned. |

<a id="p3-2"></a>

### P3.2 · Machine adapters

| Mục | Chi tiết |
| --- | --- |
| Nghiên cứu và thông tin | Đối chiếu code và chuyên đề liên quan; tách dữ kiện đã đọc, lựa chọn đề xuất và điều chưa đo. Ghi nguồn/phiên bản và giả thuyết vào HTML trước patch. |
| Định hướng / việc làm | Bọc post_json và heartbeat; verify command response trước thực thi; bảo vệ result. |
| Yêu cầu bắt buộc | Sai target/expiry/request binding bị chặn. |
| Hiện vật / gate | Patch transport và command gate; spec và output kiểm chứng được reviewer/security đọc, không chỉ checklist đánh dấu. |
| Phân công cả team | Planner chốt scope/callers/dependencies → tester chuẩn bị vector/fault cases → coder triển khai theo kiến trúc khóa → reviewer kiểm hợp đồng/transaction → cybersecurity kiểm threat/key → lead tổng hợp gate. |
| Handoff và kiểm | Bàn giao spec, file/caller matrix, vectors, patch, lệnh và output kiểm, residual risks. Toàn bộ test/simulator ở tests/. Không coi test mô phỏng là evidence thiết bị thật. |
| Lỗi / rollback | Gate không đạt thì giữ phase đang mở; ghi blocker và recovery. Patch version/schema có migration/quay lui; packet invalid không được fallback plaintext hoặc unsigned. |

<a id="p3-3"></a>

### P3.3 · Server ingress

| Mục | Chi tiết |
| --- | --- |
| Nghiên cứu và thông tin | Đối chiếu code và chuyên đề liên quan; tách dữ kiện đã đọc, lựa chọn đề xuất và điều chưa đo. Ghi nguồn/phiên bản và giả thuyết vào HTML trước patch. |
| Định hướng / việc làm | Bound raw/envelope, lookup key, verify/decrypt, replay context, inner parse. |
| Yêu cầu bắt buộc | Không gọi nghiệp vụ khi tag/signature sai; giữ transaction/quyền feature. |
| Hiện vật / gate | Shared helpers lib không import service; spec và output kiểm chứng được reviewer/security đọc, không chỉ checklist đánh dấu. |
| Phân công cả team | Planner chốt scope/callers/dependencies → tester chuẩn bị vector/fault cases → coder triển khai theo kiến trúc khóa → reviewer kiểm hợp đồng/transaction → cybersecurity kiểm threat/key → lead tổng hợp gate. |
| Handoff và kiểm | Bàn giao spec, file/caller matrix, vectors, patch, lệnh và output kiểm, residual risks. Toàn bộ test/simulator ở tests/. Không coi test mô phỏng là evidence thiết bị thật. |
| Lỗi / rollback | Gate không đạt thì giữ phase đang mở; ghi blocker và recovery. Patch version/schema có migration/quay lui; packet invalid không được fallback plaintext hoặc unsigned. |

<a id="p3-4"></a>

### P3.4 · Server egress

| Mục | Chi tiết |
| --- | --- |
| Nghiên cứu và thông tin | Đối chiếu code và chuyên đề liên quan; tách dữ kiện đã đọc, lựa chọn đề xuất và điều chưa đo. Ghi nguồn/phiên bản và giả thuyết vào HTML trước patch. |
| Định hướng / việc làm | Serialize/encrypt/sign response status và request binding; capture key context logout. |
| Yêu cầu bắt buộc | Không lỗi cleanup tạo response unsigned; không log plaintext. |
| Hiện vật / gate | Bảo vệ response và error paths; spec và output kiểm chứng được reviewer/security đọc, không chỉ checklist đánh dấu. |
| Phân công cả team | Planner chốt scope/callers/dependencies → tester chuẩn bị vector/fault cases → coder triển khai theo kiến trúc khóa → reviewer kiểm hợp đồng/transaction → cybersecurity kiểm threat/key → lead tổng hợp gate. |
| Handoff và kiểm | Bàn giao spec, file/caller matrix, vectors, patch, lệnh và output kiểm, residual risks. Toàn bộ test/simulator ở tests/. Không coi test mô phỏng là evidence thiết bị thật. |
| Lỗi / rollback | Gate không đạt thì giữ phase đang mở; ghi blocker và recovery. Patch version/schema có migration/quay lui; packet invalid không được fallback plaintext hoặc unsigned. |

## P4 · Debounce và anti-replay

Đầu vào: evidence của giai đoạn trước; P0 nhận code hiện tại và yêu cầu người dùng. Lead chỉ chuyển gate khi đặc tả, vectors, thay đổi và giới hạn có thể review.

<a id="p4-1"></a>

### P4.1 · Action policy UI

| Mục | Chi tiết |
| --- | --- |
| Nghiên cứu và thông tin | Đối chiếu code và chuyên đề liên quan; tách dữ kiện đã đọc, lựa chọn đề xuất và điều chưa đo. Ghi nguồn/phiên bản và giả thuyết vào HTML trước patch. |
| Định hướng / việc làm | Debounce read/edit theo target; write submit lock và cancel/stale-result policy. |
| Yêu cầu bắt buộc | Không mất ý định khác nhau hoặc chặn heartbeat/result. |
| Hiện vật / gate | UI policy và concurrency cases; spec và output kiểm chứng được reviewer/security đọc, không chỉ checklist đánh dấu. |
| Phân công cả team | Planner chốt scope/callers/dependencies → tester chuẩn bị vector/fault cases → coder triển khai theo kiến trúc khóa → reviewer kiểm hợp đồng/transaction → cybersecurity kiểm threat/key → lead tổng hợp gate. |
| Handoff và kiểm | Bàn giao spec, file/caller matrix, vectors, patch, lệnh và output kiểm, residual risks. Toàn bộ test/simulator ở tests/. Không coi test mô phỏng là evidence thiết bị thật. |
| Lỗi / rollback | Gate không đạt thì giữ phase đang mở; ghi blocker và recovery. Patch version/schema có migration/quay lui; packet invalid không được fallback plaintext hoặc unsigned. |

<a id="p4-2"></a>

### P4.2 · Freshness và clock

| Mục | Chi tiết |
| --- | --- |
| Nghiên cứu và thông tin | Đối chiếu code và chuyên đề liên quan; tách dữ kiện đã đọc, lựa chọn đề xuất và điều chưa đo. Ghi nguồn/phiên bản và giả thuyết vào HTML trước patch. |
| Định hướng / việc làm | Chốt cửa sổ W/skew, trusted time resync và retry packet mới. |
| Yêu cầu bắt buộc | Không nới window theo response chưa xác thực; IV và replay nonce riêng. |
| Hiện vật / gate | Time/nonce rules; spec và output kiểm chứng được reviewer/security đọc, không chỉ checklist đánh dấu. |
| Phân công cả team | Planner chốt scope/callers/dependencies → tester chuẩn bị vector/fault cases → coder triển khai theo kiến trúc khóa → reviewer kiểm hợp đồng/transaction → cybersecurity kiểm threat/key → lead tổng hợp gate. |
| Handoff và kiểm | Bàn giao spec, file/caller matrix, vectors, patch, lệnh và output kiểm, residual risks. Toàn bộ test/simulator ở tests/. Không coi test mô phỏng là evidence thiết bị thật. |
| Lỗi / rollback | Gate không đạt thì giữ phase đang mở; ghi blocker và recovery. Patch version/schema có migration/quay lui; packet invalid không được fallback plaintext hoặc unsigned. |

<a id="p4-3"></a>

### P4.3 · Replay store

| Mục | Chi tiết |
| --- | --- |
| Nghiên cứu và thông tin | Đối chiếu code và chuyên đề liên quan; tách dữ kiện đã đọc, lựa chọn đề xuất và điều chưa đo. Ghi nguồn/phiên bản và giả thuyết vào HTML trước patch. |
| Định hướng / việc làm | Atomic claim scoped key/epoch/direction; persistence, expiry và bounded admission. |
| Yêu cầu bắt buộc | Verify mật mã trước ghi; restart/concurrent replay vẫn bị chặn. |
| Hiện vật / gate | Store/schema và race evidence; spec và output kiểm chứng được reviewer/security đọc, không chỉ checklist đánh dấu. |
| Phân công cả team | Planner chốt scope/callers/dependencies → tester chuẩn bị vector/fault cases → coder triển khai theo kiến trúc khóa → reviewer kiểm hợp đồng/transaction → cybersecurity kiểm threat/key → lead tổng hợp gate. |
| Handoff và kiểm | Bàn giao spec, file/caller matrix, vectors, patch, lệnh và output kiểm, residual risks. Toàn bộ test/simulator ở tests/. Không coi test mô phỏng là evidence thiết bị thật. |
| Lỗi / rollback | Gate không đạt thì giữ phase đang mở; ghi blocker và recovery. Patch version/schema có migration/quay lui; packet invalid không được fallback plaintext hoặc unsigned. |

<a id="p4-4"></a>

### P4.4 · Resource failures

| Mục | Chi tiết |
| --- | --- |
| Nghiên cứu và thông tin | Đối chiếu code và chuyên đề liên quan; tách dữ kiện đã đọc, lựa chọn đề xuất và điều chưa đo. Ghi nguồn/phiên bản và giả thuyết vào HTML trước patch. |
| Định hướng / việc làm | Test malformed packet flood, store full/unavailable và CPU verify budget. |
| Yêu cầu bắt buộc | Không eviction nonce còn hiệu lực; fail policy rõ cho writes. |
| Hiện vật / gate | Fault/load report; spec và output kiểm chứng được reviewer/security đọc, không chỉ checklist đánh dấu. |
| Phân công cả team | Planner chốt scope/callers/dependencies → tester chuẩn bị vector/fault cases → coder triển khai theo kiến trúc khóa → reviewer kiểm hợp đồng/transaction → cybersecurity kiểm threat/key → lead tổng hợp gate. |
| Handoff và kiểm | Bàn giao spec, file/caller matrix, vectors, patch, lệnh và output kiểm, residual risks. Toàn bộ test/simulator ở tests/. Không coi test mô phỏng là evidence thiết bị thật. |
| Lỗi / rollback | Gate không đạt thì giữ phase đang mở; ghi blocker và recovery. Patch version/schema có migration/quay lui; packet invalid không được fallback plaintext hoặc unsigned. |

## P5 · Idempotency xuyên server–máy

Đầu vào: evidence của giai đoạn trước; P0 nhận code hiện tại và yêu cầu người dùng. Lead chỉ chuyển gate khi đặc tả, vectors, thay đổi và giới hạn có thể review.

<a id="p5-1"></a>

### P5.1 · Operation contract

| Mục | Chi tiết |
| --- | --- |
| Nghiên cứu và thông tin | Đối chiếu code và chuyên đề liên quan; tách dữ kiện đã đọc, lựa chọn đề xuất và điều chưa đo. Ghi nguồn/phiên bản và giả thuyết vào HTML trước patch. |
| Định hướng / việc làm | Scope ID, fingerprint inner bytes/context, retention và conflict error. |
| Yêu cầu bắt buộc | Retry cùng operation ID, nonce/IV mới; khác payload phải conflict. |
| Hiện vật / gate | Operation spec; spec và output kiểm chứng được reviewer/security đọc, không chỉ checklist đánh dấu. |
| Phân công cả team | Planner chốt scope/callers/dependencies → tester chuẩn bị vector/fault cases → coder triển khai theo kiến trúc khóa → reviewer kiểm hợp đồng/transaction → cybersecurity kiểm threat/key → lead tổng hợp gate. |
| Handoff và kiểm | Bàn giao spec, file/caller matrix, vectors, patch, lệnh và output kiểm, residual risks. Toàn bộ test/simulator ở tests/. Không coi test mô phỏng là evidence thiết bị thật. |
| Lỗi / rollback | Gate không đạt thì giữ phase đang mở; ghi blocker và recovery. Patch version/schema có migration/quay lui; packet invalid không được fallback plaintext hoặc unsigned. |

<a id="p5-2"></a>

### P5.2 · Server ledger

| Mục | Chi tiết |
| --- | --- |
| Nghiên cứu và thông tin | Đối chiếu code và chuyên đề liên quan; tách dữ kiện đã đọc, lựa chọn đề xuất và điều chưa đo. Ghi nguồn/phiên bản và giả thuyết vào HTML trước patch. |
| Định hướng / việc làm | Atomic claim, pending/completed/unknown, cache authorization, bounded status wait. |
| Yêu cầu bắt buộc | Không giữ DB transaction khi chờ máy; revoked không đọc cache. |
| Hiện vật / gate | Ledger và state tests; spec và output kiểm chứng được reviewer/security đọc, không chỉ checklist đánh dấu. |
| Phân công cả team | Planner chốt scope/callers/dependencies → tester chuẩn bị vector/fault cases → coder triển khai theo kiến trúc khóa → reviewer kiểm hợp đồng/transaction → cybersecurity kiểm threat/key → lead tổng hợp gate. |
| Handoff và kiểm | Bàn giao spec, file/caller matrix, vectors, patch, lệnh và output kiểm, residual risks. Toàn bộ test/simulator ở tests/. Không coi test mô phỏng là evidence thiết bị thật. |
| Lỗi / rollback | Gate không đạt thì giữ phase đang mở; ghi blocker và recovery. Patch version/schema có migration/quay lui; packet invalid không được fallback plaintext hoặc unsigned. |

<a id="p5-3"></a>

### P5.3 · Machine command ledger

| Mục | Chi tiết |
| --- | --- |
| Nghiên cứu và thông tin | Đối chiếu code và chuyên đề liên quan; tách dữ kiện đã đọc, lựa chọn đề xuất và điều chưa đo. Ghi nguồn/phiên bản và giả thuyết vào HTML trước patch. |
| Định hướng / việc làm | Identity không reuse qua restart; propagate operation và dedup command/result. |
| Yêu cầu bắt buộc | Server dedup không thay machine dedup. |
| Hiện vật / gate | Durable command/result contract; spec và output kiểm chứng được reviewer/security đọc, không chỉ checklist đánh dấu. |
| Phân công cả team | Planner chốt scope/callers/dependencies → tester chuẩn bị vector/fault cases → coder triển khai theo kiến trúc khóa → reviewer kiểm hợp đồng/transaction → cybersecurity kiểm threat/key → lead tổng hợp gate. |
| Handoff và kiểm | Bàn giao spec, file/caller matrix, vectors, patch, lệnh và output kiểm, residual risks. Toàn bộ test/simulator ở tests/. Không coi test mô phỏng là evidence thiết bị thật. |
| Lỗi / rollback | Gate không đạt thì giữ phase đang mở; ghi blocker và recovery. Patch version/schema có migration/quay lui; packet invalid không được fallback plaintext hoặc unsigned. |

<a id="p5-4"></a>

### P5.4 · Crash và physical effect

| Mục | Chi tiết |
| --- | --- |
| Nghiên cứu và thông tin | Đối chiếu code và chuyên đề liên quan; tách dữ kiện đã đọc, lựa chọn đề xuất và điều chưa đo. Ghi nguồn/phiên bản và giả thuyết vào HTML trước patch. |
| Định hướng / việc làm | Inject crash trước/sau execute/result/commit; reconciliation khi outcome unknown. |
| Yêu cầu bắt buộc | Không auto-execute lại tác động vật lý khi chưa biết kết quả. |
| Hiện vật / gate | Recovery procedure và fault evidence; spec và output kiểm chứng được reviewer/security đọc, không chỉ checklist đánh dấu. |
| Phân công cả team | Planner chốt scope/callers/dependencies → tester chuẩn bị vector/fault cases → coder triển khai theo kiến trúc khóa → reviewer kiểm hợp đồng/transaction → cybersecurity kiểm threat/key → lead tổng hợp gate. |
| Handoff và kiểm | Bàn giao spec, file/caller matrix, vectors, patch, lệnh và output kiểm, residual risks. Toàn bộ test/simulator ở tests/. Không coi test mô phỏng là evidence thiết bị thật. |
| Lỗi / rollback | Gate không đạt thì giữ phase đang mở; ghi blocker và recovery. Patch version/schema có migration/quay lui; packet invalid không được fallback plaintext hoặc unsigned. |

## P6 · Nghiệm thu an toàn và tương thích

Đầu vào: evidence của giai đoạn trước; P0 nhận code hiện tại và yêu cầu người dùng. Lead chỉ chuyển gate khi đặc tả, vectors, thay đổi và giới hạn có thể review.

<a id="p6-1"></a>

### P6.1 · Tamper suite

| Mục | Chi tiết |
| --- | --- |
| Nghiên cứu và thông tin | Đối chiếu code và chuyên đề liên quan; tách dữ kiện đã đọc, lựa chọn đề xuất và điều chưa đo. Ghi nguồn/phiên bản và giả thuyết vào HTML trước patch. |
| Định hướng / việc làm | Đổi method/path/query/AAD/tag/body/status/kid/operation và direction. |
| Yêu cầu bắt buộc | Mọi packet sửa/giả không vào endpoint hoặc actuator. |
| Hiện vật / gate | Cross-language negative suite; spec và output kiểm chứng được reviewer/security đọc, không chỉ checklist đánh dấu. |
| Phân công cả team | Planner chốt scope/callers/dependencies → tester chuẩn bị vector/fault cases → coder triển khai theo kiến trúc khóa → reviewer kiểm hợp đồng/transaction → cybersecurity kiểm threat/key → lead tổng hợp gate. |
| Handoff và kiểm | Bàn giao spec, file/caller matrix, vectors, patch, lệnh và output kiểm, residual risks. Toàn bộ test/simulator ở tests/. Không coi test mô phỏng là evidence thiết bị thật. |
| Lỗi / rollback | Gate không đạt thì giữ phase đang mở; ghi blocker và recovery. Patch version/schema có migration/quay lui; packet invalid không được fallback plaintext hoặc unsigned. |

<a id="p6-2"></a>

### P6.2 · Key và restart suite

| Mục | Chi tiết |
| --- | --- |
| Nghiên cứu và thông tin | Đối chiếu code và chuyên đề liên quan; tách dữ kiện đã đọc, lựa chọn đề xuất và điều chưa đo. Ghi nguồn/phiên bản và giả thuyết vào HTML trước patch. |
| Định hướng / việc làm | Unknown/revoked key, downgrade, rotation, restore/restart nonce state. |
| Yêu cầu bắt buộc | Không leak plaintext; không fallback legacy sau verify fail. |
| Hiện vật / gate | Lifecycle evidence; spec và output kiểm chứng được reviewer/security đọc, không chỉ checklist đánh dấu. |
| Phân công cả team | Planner chốt scope/callers/dependencies → tester chuẩn bị vector/fault cases → coder triển khai theo kiến trúc khóa → reviewer kiểm hợp đồng/transaction → cybersecurity kiểm threat/key → lead tổng hợp gate. |
| Handoff và kiểm | Bàn giao spec, file/caller matrix, vectors, patch, lệnh và output kiểm, residual risks. Toàn bộ test/simulator ở tests/. Không coi test mô phỏng là evidence thiết bị thật. |
| Lỗi / rollback | Gate không đạt thì giữ phase đang mở; ghi blocker và recovery. Patch version/schema có migration/quay lui; packet invalid không được fallback plaintext hoặc unsigned. |

<a id="p6-3"></a>

### P6.3 · Concurrency và retry

| Mục | Chi tiết |
| --- | --- |
| Nghiên cứu và thông tin | Đối chiếu code và chuyên đề liên quan; tách dữ kiện đã đọc, lựa chọn đề xuất và điều chưa đo. Ghi nguồn/phiên bản và giả thuyết vào HTML trước patch. |
| Định hướng / việc làm | Replay cùng packet đồng thời; retry operation mới attempt; lost response/result. |
| Yêu cầu bắt buộc | Một logical claim; pending/unknown không biến thành chưa chạy. |
| Hiện vật / gate | Concurrency/crash report; spec và output kiểm chứng được reviewer/security đọc, không chỉ checklist đánh dấu. |
| Phân công cả team | Planner chốt scope/callers/dependencies → tester chuẩn bị vector/fault cases → coder triển khai theo kiến trúc khóa → reviewer kiểm hợp đồng/transaction → cybersecurity kiểm threat/key → lead tổng hợp gate. |
| Handoff và kiểm | Bàn giao spec, file/caller matrix, vectors, patch, lệnh và output kiểm, residual risks. Toàn bộ test/simulator ở tests/. Không coi test mô phỏng là evidence thiết bị thật. |
| Lỗi / rollback | Gate không đạt thì giữ phase đang mở; ghi blocker và recovery. Patch version/schema có migration/quay lui; packet invalid không được fallback plaintext hoặc unsigned. |

<a id="p6-4"></a>

### P6.4 · Thiết bị và hiệu năng

| Mục | Chi tiết |
| --- | --- |
| Nghiên cứu và thông tin | Đối chiếu code và chuyên đề liên quan; tách dữ kiện đã đọc, lựa chọn đề xuất và điều chưa đo. Ghi nguồn/phiên bản và giả thuyết vào HTML trước patch. |
| Định hướng / việc làm | Đo điện thoại/machine target, payload limits, battery/latency và secure storage failures. |
| Yêu cầu bắt buộc | Chỉ claim trong workload/thiết bị đã kiểm; test hiện hành đạt hoặc blocker rõ. |
| Hiện vật / gate | Acceptance package; spec và output kiểm chứng được reviewer/security đọc, không chỉ checklist đánh dấu. |
| Phân công cả team | Planner chốt scope/callers/dependencies → tester chuẩn bị vector/fault cases → coder triển khai theo kiến trúc khóa → reviewer kiểm hợp đồng/transaction → cybersecurity kiểm threat/key → lead tổng hợp gate. |
| Handoff và kiểm | Bàn giao spec, file/caller matrix, vectors, patch, lệnh và output kiểm, residual risks. Toàn bộ test/simulator ở tests/. Không coi test mô phỏng là evidence thiết bị thật. |
| Lỗi / rollback | Gate không đạt thì giữ phase đang mở; ghi blocker và recovery. Patch version/schema có migration/quay lui; packet invalid không được fallback plaintext hoặc unsigned. |

## P7 · Migration, vận hành và dài hạn

Đầu vào: evidence của giai đoạn trước; P0 nhận code hiện tại và yêu cầu người dùng. Lead chỉ chuyển gate khi đặc tả, vectors, thay đổi và giới hạn có thể review.

<a id="p7-1"></a>

### P7.1 · Compatibility migration

| Mục | Chi tiết |
| --- | --- |
| Nghiên cứu và thông tin | Đối chiếu code và chuyên đề liên quan; tách dữ kiện đã đọc, lựa chọn đề xuất và điều chưa đo. Ghi nguồn/phiên bản và giả thuyết vào HTML trước patch. |
| Định hướng / việc làm | Version matrix Flutter/server/machine; rollout key/envelope trước enforcement. |
| Yêu cầu bắt buộc | Legacy coexistence explicit có điều kiện kết thúc; không heuristic fallback. |
| Hiện vật / gate | Migration plan; spec và output kiểm chứng được reviewer/security đọc, không chỉ checklist đánh dấu. |
| Phân công cả team | Planner chốt scope/callers/dependencies → tester chuẩn bị vector/fault cases → coder triển khai theo kiến trúc khóa → reviewer kiểm hợp đồng/transaction → cybersecurity kiểm threat/key → lead tổng hợp gate. |
| Handoff và kiểm | Bàn giao spec, file/caller matrix, vectors, patch, lệnh và output kiểm, residual risks. Toàn bộ test/simulator ở tests/. Không coi test mô phỏng là evidence thiết bị thật. |
| Lỗi / rollback | Gate không đạt thì giữ phase đang mở; ghi blocker và recovery. Patch version/schema có migration/quay lui; packet invalid không được fallback plaintext hoặc unsigned. |

<a id="p7-2"></a>

### P7.2 · Rollout/rollback

| Mục | Chi tiết |
| --- | --- |
| Nghiên cứu và thông tin | Đối chiếu code và chuyên đề liên quan; tách dữ kiện đã đọc, lựa chọn đề xuất và điều chưa đo. Ghi nguồn/phiên bản và giả thuyết vào HTML trước patch. |
| Định hướng / việc làm | Diễn tập canary, key compromise và quay lui protocol/schema. |
| Yêu cầu bắt buộc | Rollback không mở unsigned writes hoặc mất ledger đang cần. |
| Hiện vật / gate | Rehearsal evidence; spec và output kiểm chứng được reviewer/security đọc, không chỉ checklist đánh dấu. |
| Phân công cả team | Planner chốt scope/callers/dependencies → tester chuẩn bị vector/fault cases → coder triển khai theo kiến trúc khóa → reviewer kiểm hợp đồng/transaction → cybersecurity kiểm threat/key → lead tổng hợp gate. |
| Handoff và kiểm | Bàn giao spec, file/caller matrix, vectors, patch, lệnh và output kiểm, residual risks. Toàn bộ test/simulator ở tests/. Không coi test mô phỏng là evidence thiết bị thật. |
| Lỗi / rollback | Gate không đạt thì giữ phase đang mở; ghi blocker và recovery. Patch version/schema có migration/quay lui; packet invalid không được fallback plaintext hoặc unsigned. |

<a id="p7-3"></a>

### P7.3 · Safe observability

| Mục | Chi tiết |
| --- | --- |
| Nghiên cứu và thông tin | Đối chiếu code và chuyên đề liên quan; tách dữ kiện đã đọc, lựa chọn đề xuất và điều chưa đo. Ghi nguồn/phiên bản và giả thuyết vào HTML trước patch. |
| Định hướng / việc làm | Counters verify/decrypt/replay/conflict/unknown; redaction logs và crash dumps. |
| Yêu cầu bắt buộc | Không token/key/plaintext; không log oracle chi tiết cho attacker. |
| Hiện vật / gate | Metrics và incident runbooks; spec và output kiểm chứng được reviewer/security đọc, không chỉ checklist đánh dấu. |
| Phân công cả team | Planner chốt scope/callers/dependencies → tester chuẩn bị vector/fault cases → coder triển khai theo kiến trúc khóa → reviewer kiểm hợp đồng/transaction → cybersecurity kiểm threat/key → lead tổng hợp gate. |
| Handoff và kiểm | Bàn giao spec, file/caller matrix, vectors, patch, lệnh và output kiểm, residual risks. Toàn bộ test/simulator ở tests/. Không coi test mô phỏng là evidence thiết bị thật. |
| Lỗi / rollback | Gate không đạt thì giữ phase đang mở; ghi blocker và recovery. Patch version/schema có migration/quay lui; packet invalid không được fallback plaintext hoặc unsigned. |

<a id="p7-4"></a>

### P7.4 · Review dài hạn

| Mục | Chi tiết |
| --- | --- |
| Nghiên cứu và thông tin | Đối chiếu code và chuyên đề liên quan; tách dữ kiện đã đọc, lựa chọn đề xuất và điều chưa đo. Ghi nguồn/phiên bản và giả thuyết vào HTML trước patch. |
| Định hướng / việc làm | Đánh giá forward secrecy, metadata padding, end-to-end app→machine và crypto agility khi có nhu cầu. |
| Yêu cầu bắt buộc | Không claim PQ/anonymity; đổi kiến trúc cần yêu cầu riêng. |
| Hiện vật / gate | Backlog có trigger và ADR; spec và output kiểm chứng được reviewer/security đọc, không chỉ checklist đánh dấu. |
| Phân công cả team | Planner chốt scope/callers/dependencies → tester chuẩn bị vector/fault cases → coder triển khai theo kiến trúc khóa → reviewer kiểm hợp đồng/transaction → cybersecurity kiểm threat/key → lead tổng hợp gate. |
| Handoff và kiểm | Bàn giao spec, file/caller matrix, vectors, patch, lệnh và output kiểm, residual risks. Toàn bộ test/simulator ở tests/. Không coi test mô phỏng là evidence thiết bị thật. |
| Lỗi / rollback | Gate không đạt thì giữ phase đang mở; ghi blocker và recovery. Patch version/schema có migration/quay lui; packet invalid không được fallback plaintext hoặc unsigned. |

## Ranh giới file và yêu cầu nghiệm thu

Flutter giữ packet/transport ở core; server shared helper ở lib, không import service; quyền/SQL/transaction trong feature theo MODULE_PATTERN. Routes ở config/routing.py và direct imports giữ nguyên. Machine adapters phải bao phủ cả heartbeat và poll/result. Wire contract đổi thì cập nhật Flutter, server, machine và tests cùng đợt.

Chưa chọn thư viện hoặc triển khai crypto. Chưa có benchmark hay chứng nhận bảo mật. Hoàn thành tài liệu không đồng nghĩa hệ thống đã mã hóa.
