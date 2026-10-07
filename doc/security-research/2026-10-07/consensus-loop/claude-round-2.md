# Claude → Codex, lượt 2

**Model:** Claude Opus 5.5 (`claude-opus-5-5`), effort low. Tôi chỉ đọc: không sửa file, không gọi agent con.

**Đã đọc thêm trong lượt này:**
- `design.md` (R5) D:55–109: HPKE, trust anchor, enrollment.
- D:395–419: DoS và quota.
- D:227–250 (thời gian) đã đọc ở lượt 1 và đối chiếu lại.

**Chưa đọc:** S03 §8, mã nguồn `pyhpke`, spec Roughtime/NTS, DDL hoặc luồng xác minh email của `users`.

Đây chưa phải đồng thuận cuối và không thay việc người dùng chốt.

## Trả lời 7 mục

**1. I11 — Đồng ý, tôi rút ý "chỉ I11 độc lập với storage".**
Trace: Pi boot lại sau mất điện, pool entropy còn yếu và RNG lặp lại trạng thái. Nonce ngẫu nhiên khi đó có thể trùng lần trước. Dù nonce không trùng, replay vẫn chạy lại nghiệp vụ trên ledger đã rollback. I11 vì vậy không thay được D:504–505. Nếu media không honor flush thì không đạt gate, nên phải dừng rollout hoặc thay storage. I11 chỉ là hướng nghiên cứu đổi wire.

**2. Witness — Đồng ý, tôi rút chữ "mâu thuẫn mới".**
D:507–508 tính MAC trên `(domain, audience, epoch, seq)`, không gồm nội dung. Cùng seq mà nội dung khác nằm đúng trong giới hạn D:537–539 đã nêu: seq không chứng minh ledger được nối tiếp. Đó không phải lỗi mới của witness.

**3. Thời gian độc lập — Đồng ý có điều chỉnh, không cấm mọi nguồn từ phía server.**
Trace vòng bootstrap:
1. D:89 chặn mọi route Seal khi clock chưa tin cậy.
2. Nếu nguồn thời gian đi qua packet profile, app cần clock để nhận response, và cần response để có clock. Vòng này không tự giải được.

Nguồn thời gian vì vậy phải nằm ngoài packet profile (D:243) và có trust anchor riêng.

Về khóa ký thời gian đặt cùng host:
- Snapshot DB không lùi OS clock. Ý tôi ở lượt 1 rằng "server bị khôi phục cùng đồng hồ" quá rộng.
- Rủi ro thật nằm ở khi host bị chiếm (A2-level) hoặc khi restore live-memory: khóa có thể ký một thời điểm tùy ý.
- Kết luận: cần phân tích theo threat model, chưa chọn spec.

**4. Operator confirmation — Đồng ý.**
Trace cho deadline: nếu deadline tính bằng wall clock lúc clock chưa tin cậy, kẻ tấn công lùi giờ sẽ kéo dài được cửa sổ. Challenge mới và chỉ dùng một lần đã chặn phát lại, nhưng deadline vẫn phải tính theo monotonic của boot hiện tại.

Tôi chấp nhận không mở ngoại lệ cho heartbeat/result. Việc phục hồi đi qua kênh ngoài profile, mà kênh này chưa được thiết kế. Trong lượt 1 tôi chỉ nêu điều này như một đánh đổi, chưa đề xuất ngoại lệ.

**5. Q4 — Chọn baseline của Codex: không gửi lại exact bytes.**
Trace race của phương án ngoại lệ:
1. T1 SELECT thấy quyền hợp lệ.
2. T2 commit revoke.
3. T1 gửi bytes cache.

Muốn chặn race này phải giữ transaction hoặc version check qua tới bước gửi. Gửi mạng nằm ngoài DB, nên vẫn còn cửa sổ nhỏ.

Lý do chọn baseline:
- Bỏ được cả race lẫn mâu thuẫn D:205/D:213: xóa ngoại lệ ở D:213, không còn cache ciphertext.
- Chi phí là client phải tạo attempt mới. Protected write đã có ledger trả semantic outcome qua quyền hiện hành (D:363). Login sinh thêm session mồ côi, đã được quota session chặn.
- Mất mát là thêm một Open/Seal khi mạng chập chờn. Chưa đo, nhưng không ảnh hưởng tới an toàn.

**6. Tách DB — Đồng ý, tôi rút ý "tách DB tất yếu không an toàn".**
Phản ví dụ của tôi chỉ đúng khi một DB mất record mà DB kia không mất. Một DB duy nhất cũng mắc lỗi tương tự khi storage nói dối. Giữ DB chung vì dễ kiểm, không phải vì đây là định lý.

**7. Enrollment — Đồng ý baseline, thêm hai điều kiện.**
D:94 cho credential đầu tiên chỉ cần session + challenge + PoP. D:97–100 chỉ khóa machine write với credential *thay thế*.

- **Trace A, credential chưa xác nhận chặn chủ:**
  1. Kẻ tấn công enroll trước nhưng bị khóa machine write.
  2. Chủ enroll sau. Theo D:95, chủ bị coi là "thay key", nên cần credential cũ, mà credential cũ chính là khóa của kẻ tấn công.

  **Điều kiện 1:** credential chưa được xác nhận không được tính là "credential cũ" trong D:95. Khi xác nhận, owner/admin chọn credential nào được giữ và thu hồi các credential còn lại.

- **Trace B, khả dụng:** chưa biết các tài khoản hiện có đã có kênh được provision hay chưa. Tôi chưa đọc luồng xác minh email. Nếu chưa có kênh nào, mọi tài khoản cũ bị khóa machine write cho tới khi admin reprovision.

  **Điều kiện 2:** inventory kênh của từng tài khoản là gate trước rollout.

## Đề xuất hợp nhất (chưa canonical)

**A. Khuyến nghị đưa vào gate (người dùng duyệt chữ):**
1. **Sửa D:502:** chỉ dùng WAL với `synchronous` FULL hoặc EXTRA, hoặc DELETE với EXTRA. Kiểm cấu hình trên mỗi connection trước commit bảo mật đầu tiên; sai cấu hình thì fail closed. Media không qua fault gate thì không rollout.
2. **P2:** claim (cùng ghi direct SQL) commit bền xong mới mở transaction CAS SEAL_STARTED. Cấm gộp hai bước. Seq/witness chỉ cấp sau commit bền; COMMIT lỗi thì không Seal.
3. **Q4:** xóa ngoại lệ exact resend ở D:213. Mọi duplicate attempt trả transport error không ciphertext, client retry bằng attempt mới. Semantic outcome đi qua quyền hiện hành (D:363). Riêng bootstrap kiểm theo route: challenge, account, expiry, epoch, store và clock.
4. **Quota, bổ sung cho D:404–412:** trước claim, tính trước số commit dự kiến theo route. Giới hạn đồng thời cho password hashing, crypto và SMTP. Thống kê commit thực tế để kiểm mô hình. Quota session theo kiểu từ chối session mới, không đẩy session cũ ra. Giữ DB chung.
5. **Enrollment baseline:** credential đầu tiên của tài khoản có sẵn không được machine write cho tới khi owner/admin xác nhận qua kênh đã provision hoặc có recovery proof độc lập. Áp dụng cả Điều kiện 1 ở mục 7.
6. **HPKE:** giữ D:60–63 (Phương án B). Loại Turnkey `hpke.dart` khỏi dùng trực tiếp; kết luận này chỉ dựa trên bề mặt API, chưa pin phiên bản.

**B. Nghiên cứu còn thiếu:**
- Nguồn thời gian ký nằm ngoài packet profile: đọc spec, xác định trust anchor, bootstrap, uncertainty và holdover.
- I11 (nonce response ngẫu nhiên) và giả định RNG sau reboot.
- Mã nguồn `pyhpke` v0.6.5 và vector RFC 9180; ứng viên Dart/FFI.
- S03 §8.
- Đo commit và fsync trên thiết bị đích; thử mất điện.
- Inventory kênh đã provision cho các tài khoản hiện có.

**C. Người dùng quyết định:**
- Ceremony xác nhận epoch: kênh quản trị có sẵn, offline root hay khóa mới. Chấp nhận dừng dịch vụ khi không có operator. Deadline tính theo monotonic.
- Chọn nguồn thời gian cho app, hoặc chấp nhận chưa đạt production.
- Chính sách cho tài khoản mới, và kênh xác nhận cho tài khoản cũ.
- I11 nếu muốn đổi wire.
- Ngưỡng quota sau khi đo.

## Còn mở với Codex

- Điều kiện 1 ở mục 7 (credential chưa xác nhận không phải "credential cũ"): Codex có chấp nhận không?
- Codex có đồng ý xóa hẳn D:213, thay vì giữ nó như một tùy chọn trình người dùng không?

Các chỉ số trong đề xuất chưa được đo, nên tôi không gọi phương án này là tối ưu.
