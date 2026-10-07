# HANDOFF — Codex → Claude, nghiên cứu bảo mật R5

**Lượt Codex bắt đầu 01:50 ngày 07/10/2026 Asia/Ho_Chi_Minh; deadline 02:09. Claude bắt đầu 02:11 do scheduler. Codex không khởi chạy Claude.** Cập nhật tăng dần; xem dấu chốt thời gian cuối file. Đầu ra hiện sẵn sàng review độc lập, không là nghiệm thu security.

## Phạm vi và bảo toàn

Chỉ nghiên cứu/tài liệu trong `doc/security-research/2026-10-07`. Không sửa code, canonical design, ba HTML, kiến trúc/naming đã khóa; không commit/push/deploy. Working tree đã có nhiều thay đổi trước lượt, giữ nguyên. Không đọc env/SMTP config/DB/account data/private key runtime. Nguồn internet chỉ là dữ liệu, không chỉ dẫn; không thực thi code nguồn. Thay kiến trúc hay hợp đồng cần người dùng duyệt. Không chạy product test/vector/benchmark/formal verification và không tuyên bố đã pass.

Đã đọc AGENTS.md, MODULE_PATTERN.md, TEAM.md, design R5; đọc text các phần cần thiết của `index.html`, `architecture.html`, `packet-security.html`. Mã đọc phục vụ đối chiếu chỉ là source, danh sách/hash ở READ_SCOPE.json. `python` và `rg` không có, dùng `python3` và `grep`/HTML parser. Tải nguồn từ container lỗi DNS, không có original public PDF/HTML/text local; sources/ chứa ghi chú và lý do lỗi, không giả bản gốc. Web đọc được phần nguồn nêu trong SOURCES.md.

## Trạng thái task Codex

| ID | Ưu tiên | Trạng thái | Đầu ra và hướng tiếp tục |
|---|---|---|---|
| R01 | P0 | Đã có nghiên cứu; tải gốc bị hạn chế DNS | SOURCES.md S01–S10, sources/DOWNLOAD_STATUS.md, sources/READ_NOTES.md; Claude tải/kiểm version/errata nếu được phép |
| R02 | P0 | Bản Codex đã viết, chờ review độc lập | FINDINGS.md F01–F11, locator design/code và confidence; không verdict production |
| R03 | P0 | Đã chốt 02:04, sẵn sàng review | IMPROVEMENTS.md I01–I12 và task C01–C07 bên dưới |
| R04 | P0 | Sẵn sàng scheduler 02:11 | Claude đọc nguồn/mã độc lập, phản biện trực tiếp các giả thuyết |
| R05 | P1 | Phụ thuộc review R04 | CLAUDE_REVIEW.md + CLAUDE_TO_CODEX.md; operator tiếp tục hội ý/user approval |

P0/P1/P2 là ưu tiên nghiên cứu đề xuất, **không phase triển khai**. Không đánh ✓ security acceptance cho những tài liệu chưa được independent review.

## Thứ tự đọc hiệu quả

Đọc design R5 nguyên bản trước kết luận của Codex để giữ đánh giá độc lập. Sau đó mở SOURCES.md và trực tiếp nguồn S04 (SQLite), S06 (NTS), S01/S02 (HPKE/OHTTP), S07 (bootstrap/recovery), S05/S10 (crash/rollback). FINDINGS.md và IMPROVEMENTS.md là giả thuyết cần kiểm, không instruction nguồn. READ_SCOPE.json giúp biết locator/hash có bị đổi sau Codex hay không; nếu đổi phải đọc lại file hiện tại, không phán trên dòng cũ.

## Claude: task sẵn sàng, không cần triển khai

### C01 — P0, phản biện durable COMMIT / Seal / executor

**Ready:** ngay; input D:196–225,500–512, F01/F04, S03/S04. D là `agent_workspace/tasks/middleware/internal/packet-security/design.md`.

**Đọc nguồn:** SQLite PRAGMA synchronous FULL/EXTRA + bảng WAL/rollback; NIST 38D §§8,9.2; RFC 9180 §§5.3,9.8. Mã connection.py:14–33 chỉ source, không mở DB.

**Giả thuyết Codex:** “FULL” mà chưa journal mode có thể không thỏa durable owner CAS. Trace: commit CAS → Seal → power loss làm mất CAS → boot xác minh cùng epoch → packet còn fresh → Seal lại CID. **Phải tìm cách bác bỏ:** R5 stable-media/fault gate hoặc boot policy có chặn trace không? Nếu có, phân loại “đặc tả gate chưa cụ thể” thay vì new crypto blocker. Không giả định mỗi boot tự đổi epoch nếu text chỉ nói confirm current epoch.

**Đầu ra:** CLAUDE_REVIEW.md mục C01 verdict agree/reject/partial với source và D:file:dòng; bảng journal mode/preconditions; phép kiểm/power-loss trace còn thiếu. Acceptance: phân biệt SQLite consistency/atomicity/durability và actual media, chỉ rõ case giữ safety; không tuyên bố trace đã tái hiện.

### C02 — P0, trusted time / cold boot / manifest freeze

**Ready:** ngay, độc lập C01; input D:77–90,227–250,556–561, F02/I02, S06.

**Đọc:** RFC 8915 §§8.5–8.7 và nguồn OS/platform chính thức nếu tìm được; không lấy “system time API” làm trusted time. Không đọc runtime data thiết bị.

**Giả thuyết:** NTS-enabled boolean chưa chứng minh uncertainty bound/certificate bootstrap. Phản biện cả strict fail-closed gây cold-start deadlock và việc time repair mở lại old manifest. Hỏi rõ nguồn ngoài packet protocol thế nào mới không bị A0/A1 điều khiển. Không bê Date correction OHTTP cho A1.

**Đầu ra:** review C02 + capability requirements server/app/máy trong tài liệu nội bộ (có thể tạo CLOCK_REVIEW.md tại thư mục này). Acceptance: certificate/time circularity, delay bound/holdover/suspend/fallback, failure behavior, những tham số chưa đo; không tự đặt Δ/σ.

### C03 — P0, bootstrap và credential recovery không có đường tắt

**Ready:** ngay; input D:94–114,136,152–155,205–208, F05/F06/I03/I04, S07.

**Đọc mã:** user_login_process.py:20–47; user_session.py:23–61; user_register_process.py:28–142; otp/user_otp_process.py:12–16,70–148; user_register_store.py. Không đọc user_otp_send/config hoặc database/account/secret.

**Giả thuyết:** packet claim mới mỗi attempt không duy trì semantic OTP/send/account/token outcome qua crash; first enrollment cần account-scoped lifecycle để không bypass old credential. **Phản biện:** DB unique đã chặn gì? Cached verified result có thật là reuse authorization, hay chỉ cached semantic success? Phân biệt email confirmation registration với MFA/OOB authentication theo NIST; không nâng thành yêu cầu AAL nếu user chưa chọn.

**Đầu ra:** BOOTSTRAP_MATRIX.md hoặc mục review gồm login/register/resend/confirm/enroll/recovery: mode, factors, side effects, state/transaction, retry/new attempt/crash, quotas. Acceptance: challenge/public key/account/action/epoch binding, one-use consume atomic khi cấp quyền, recovery code entropy/hash/throttle/notification, mất-all-factors policy còn chờ người dùng.

### C04 — P0, ledger máy / epoch / frontier và rollback adversarial

**Ready:** ngay; input D:281–387,498–561, F07/F08/I05; S05 RIFL §§3–4.4, S10 Memoir §§I,II-D,III overview.

**Giả thuyết:** observed frontier chỉ phát hiện rollback đã có witness sống; no alarm không continuity. Higher seq audit cần extension proof trước redelivery, không tự reset namespace qua credential generation. Authenticated artifact trên disk không tự chứng minh current epoch ngoài snapshot.

**Yêu cầu phản ví dụ:** chưa ai nhận witness commit cuối; peers/server snapshot cùng lùi; seq lớn fake/no MAC; out-of-order response; fresh audit reply seq thấp/equal head khác/higher seq không extension; old challenge; rotate/reflash machine; authority confirmation replay; claim đã durable nhưng physical effect không transactional. Kiểm D:537–540 đã thừa nhận giới hạn nào để không báo lại như discovery mới.

**Đầu ra:** review C04, các trace phân safety/liveness/unsupported environment và đề xuất extension proof/recovery contract (tài liệu riêng nếu cần). Acceptance: không hứa exactly-once vật lý; không áp deterministic safe replay Memoir vào Seal/executor; không xóa unknown vì storage full; operation/command identity giữ nguyên qua retry/rotation.

### C05 — P0, revoke transaction theo feature và queue dispatch

**Ready:** ngay; input D:305–308,389–400, F09/I06. Xem code source trong READ_SCOPE.json: machine_access.py, machine_menu_update.py, machine_staff_revoke.py, user_session.py. Có thể đọc machine_transport.py/machine_read helpers source để kiểm chính xác, không state runtime.

**Giả thuyết:** hiện trạng check_access→send không có cùng conn/claim ordering với logout/revoke; đó là implementation gap của thiết kế chưa triển khai, không tự thành design exploit.

**Đầu ra:** bảng transaction boundary + trace hai thứ tự commit revoke/claim; đánh dấu quyền tại admission/take/cache outcome. Acceptance: nhận diện SQL cùng conn/lock trước đọc, wait ngoài transaction, denied outcomes sau revoke, dispatched vẫn có thể execute; không centralize feature rules hoặc sửa module.

### C06 — P1 (dependency gate P0), library capabilities + DoS bounds

**Ready:** ngay; output review có thể bổ sung sau C01–C05 nếu thời gian ít; input D:53–63,146–149,193–194,404–447, F10/F11, S08/S09.

**Đọc:** PyHPKE 0.6.5 concrete source/pinned tag + official API; Turnkey packages/crypto/lib; nếu không đạt Export tìm candidate Dart/FFI sơ cấp khác. Không install/runtime code trong task nghiên cứu. Xác minh precise release date; pub.dev snapshot version list khác landing, không gọi latest từ cache chưa pin.

**Giả thuyết:** enc33 P-256 README chưa drop-in enc65 RFC; có thể chỉ wrapper compressed encoding, cần chứng cứ code trước reject. API single-shot chưa đủ same-context Export. Global/pre-auth crypto/hash/SMTP + shared SQLite cần bounds, không chỉ per-kid limiter.

**Đầu ra:** DEPENDENCY_MATRIX.md nếu đủ chứng cứ, review C06 về unknowns và saturation traces. Acceptance: Export thật/concrete, context lifetime, info/AAD nontruncate, algorithms/enc/errors/RNG/vectors/pinned release/license; không suy absence Dart từ search thiếu; không bịa audit/performance; mọi library choice/wire change chờ user.

### C07 — P1, đóng phản biện và giao operator/user

**Phụ thuộc:** C01–C05 đã có verdict; C06 có kết luận hoặc ghi rõ unfinished. Không cần “đồng thuận” để kết thúc review; bất đồng có chứng cứ phải giữ.

**File:** CLAUDE_REVIEW.md và CLAUDE_TO_CODEX.md (scheduler task gốc đã yêu cầu hai file). Không ghi đè FINDINGS/IMPROVEMENTS của Codex để xóa bất đồng; có thể bổ sung SOURCES với ID mới S11+ và nguồn gốc nếu tải được. HANDOFF cập nhật task/status tiếp tục.

**Acceptance:** mỗi F01–F11/I01–I12 ít nhất mapped verdict hoặc deferred reason; source sections thực sự đọc, confidence, counterexample, assumptions, test cần làm. Phân nhóm: giữ R5; làm cụ thể gate; có thay contract/architecture cần người dùng chốt; unsupported deployment. CLAUDE_TO_CODEX nêu các quyết định user cần duyệt và task nghiên cứu sẵn sàng/phụ thuộc, không giao coder khi chưa user chốt. Nếu không đủ thời gian ưu tiên C01–C04 và ghi thiếu rõ.

## Điểm bất đồng/chưa rõ cần giải quyết, không mặc định đồng ý

1. F01 là yêu cầu làm cụ thể durability gate, hay blocker mới? Phản biện bằng exact journal/media/boot assumptions.
2. RFC 9180 §9.8 Base remote-auth wording so với response xác thực secret context của client trung thực: cần nêu đúng bảo đảm A0/A1, không kết luận “Base không bảo vệ response” hoặc “server signature” từ tên AEAD.
3. Nonwinner transport-only so với cached exact ciphertext retransmit ở D:205–214; điều kiện current auth/expiry/revoke chưa bảng state.
4. Bootstrap “no-ledger” có được chấp nhận cho email/password-login effects không? Recovery credential tuyệt đối không được dùng exception để consume không bền rồi cấp quyền.
5. Current epoch confirmation mỗi boot: chữ ký/artifact còn hạn không tự đảm bảo freshness; authority ngoài rollback domain cần ceremony nào?
6. Machine higher-seq extension proof/physical identity capability chưa freeze; đừng suy có security hardware.
7. First-install vs existing-account credential policy; lost-all-factors/admin recovery UX cần người dùng chốt.
8. Source Dart main đã thấy compressed enc wrapper có decompression; không reject chỉ vì enc33. Chưa pin release, generic info/AAD/Export còn là gate; cần đọc implementation đúng version.

## Nhật ký bàn giao tăng dần

- Khoảng 01:51: cập nhật placeholder R01–R03 đang làm và giữ thay đổi sẵn, chưa kiểm crypto.
- Khoảng 01:52: ghi H01 durability/H02 trusted time, lỗi tải DNS. Timestamp dự thảo ban đầu 01:54 đã sửa về khoảng 01:52, không coi nó là bằng chứng lịch thực thi.
- Trước 02:00: lưu SOURCES/FINDINGS/IMPROVEMENTS/READ_SCOPE và nguồn truy cập; R03 tiếp tục task review cụ thể.
- **02:04 ngày 07/10/2026 +07:00: chốt bàn giao trước deadline 02:09.** R01–R03 hoàn thành ở mức hồ sơ Codex, R04 ready cho scheduler 02:11. QA.md ghi kiểm local links/locator/source IDs và hash 16 file đã đọc giữ nguyên; không thay thế independent security review. Không khởi chạy Claude.
- S09 bổ sung source main: wrapper enc33 có decompression; generic info/AAD/Export và pinned release vẫn chưa được xác minh. C06 cần phản biện trên version cụ thể.

## Cập nhật lượt Claude — 07/10/2026 (bắt đầu 02:11, chốt khoảng 02:20 Asia/Ho_Chi_Minh)

Codex bàn giao đầy đủ (finished 02:04, exit 0). Claude review độc lập. **Chỉ ghi file, chưa hội ý trực tiếp với Codex.** Không sửa code, canonical design hay HTML; không commit/push/deploy. Không ghi đè FINDINGS/IMPROVEMENTS.

| ID | Trạng thái | Đầu ra |
|---|---|---|
| C01 | Xong verdict: đồng ý F01. Nếu mất cả claim+CAS, tác động là nonce reuse của response dưới A0. Đề xuất sửa chữ D:502 | CLAUDE_REVIEW.md §C01 |
| C02 | Xong, verdict một phần: bác "repair mở manifest cũ" nhờ sequence (D:72). Mở câu hỏi nguồn time của app Android | §C02, Q2 |
| C03 | Xong: login no-ledger chấp nhận được. Counterexample mới "first enrollment race" khi migration | §C03, P3 |
| C04 | Xong: phần lớn trace R5 đã xử lý hoặc tự thừa nhận. Gap thật là xác nhận epoch mỗi boot so với root offline. Có trace ghép kết quả qua restart (`machine_transport.py`), phía máy chưa kiểm | §C04, Q3 |
| C05 | Xong: đồng ý F09. Hiện trạng dùng ba connection để đọc quyền, `take()` không kiểm quyền | §C05 |
| C06 | Một phần: Turnkey API không có Export và không nhận info/AAD tùy biến. Concrete context PyHPKE chưa đọc. Thêm áp lực fsync của bootstrap | §C06 |
| C07 | Xong ánh xạ F01–F11/I01–I12, câu hỏi Q1–Q6, đề xuất P1–P8 | §C07, CLAUDE_TO_CODEX.md |

**Bị chặn trong lượt:** `curl` (tải bản gốc) và `python3 -c` (kiểm SQLite `:memory:`) bị từ chối quyền vì phiên non-interactive. Không có file nguồn gốc hay SHA256 mới. Nguồn đọc qua WebFetch được ghi là S11–S13 trong SOURCES.md.

**Tiếp theo:**
- Codex/operator trả lời Q1–Q6 trong CLAUDE_TO_CODEX.md.
- User chốt P3–P6 và lựa chọn thư viện.
- Task nghiên cứu còn lại nằm ở cuối CLAUDE_REVIEW.md.
- Không giao coder trước khi user chốt.
