# Cải tiến đề xuất — P0/P1/P2, không phải phase triển khai

Ngày 07/10/2026. Đây là backlog nghiên cứu để người dùng/Claude phản biện; không sửa canonical R5. P0 = phải làm rõ trước gate production hoặc trước contract crypto; P1 = tăng tính kiểm được/khép ambiguity; P2 = khảo sát tối ưu sau safety gates. **Ưu tiên không phải độ nghiêm trọng của exploit đã xác minh.** Tất cả tiêu chí kiểm dưới đây chưa thực hiện. D = `agent_workspace/tasks/middleware/internal/packet-security/design.md`; chi tiết nguồn và độ chắc chắn ở SOURCES/FINDINGS.

## P0

### I01 — Chốt profile durability theo journal mode (F01)

- Vấn đề: D:500–505 + HTML mô tả FULL chưa chốt journal/VFS/platform; FULL không đủ trên mọi rollback-journal filesystem.
- Nguồn: S04 [SQLite synchronous](https://www.sqlite.org/pragma.html#pragma_synchronous); S03 §9.2.
- Tác động: mất claim/CAS/executor ledger sau đã cấp quyền có thể phá invariant; không khẳng định deployment hiện đã lỗi.
- Hướng sửa đề xuất: tài liệu contract chọn WAL+FULL hoặc rollback-journal+EXTRA theo chứng cứ platform, pin SQLite/VFS và media flush; mọi commit bảo mật đọc lại cấu hình thực, lỗi khóa gate. Giữ một-process/module rules.
- Tiêu chí kiểm: same-epoch reboot trace sau CAS/claim/result, journal recovery + disk full/I/O/commit error; authoritative admission chỉ sau durable commit. Process kill không thay power-loss verification.
- Người dùng chốt: **Có**, profile vận hành và chi phí durability; lượt này chỉ làm rõ tài liệu đề xuất.

### I02 — Đặc tả capability trusted time và cold boot (F02)

- Vấn đề: D:227–250,556–561; gọi tên NTS chưa có certificate bootstrap/uncertainty/holdover policy.
- Nguồn: S06 [RFC 8915 §§8.5–8.7](https://www.rfc-editor.org/rfc/rfc8915.html#section-8.5).
- Tác động: sai clock có thể mở manifest cũ/prune sớm; fail closed toàn Seal làm unavailable nếu không có provisioning path.
- Hướng sửa: inventory server/app/máy theo OS/version/time authority; định nghĩa uncertainty và authority để chuyển CLOCK_UNTRUSTED→trusted; no silent NTP fallback; chọn Δ/σ/holdover từ requirement/measurement sau đó, không số giả.
- Tiêu chí: clock ±1 ngày, jump forward/back, asymmetric delay, revoked cert, suspend, mạng mất; không cleanup/claim/Seal khi chưa chứng minh bound. Recovery ngoài packet protocol hoạt động với quyền operator rõ.
- Người dùng chốt: **Có**, availability khi mất time authority và provisioning/recovery policy.

### I03 — Bảng bootstrap route/side-effect/retry/quota (F05)

- Vấn đề: D:110–114,136,207; không có machine write không có nghĩa read-only. Login token, account insert, OTP delivery và recovery đều tạo trạng thái.
- Nguồn: S07 [NIST 63B-4](https://pages.nist.gov/800-63-4/sp800-63b.html); S05 [RIFL](https://web.stanford.edu/~ouster/cgi-bin/papers/rifl.pdf); code references F05.
- Tác động: fresh attempt bypass packet dedup; crash/RAM reset không giữ email/failure quotas/outcome; không suy account trùng khi uniqueness còn đúng.
- Hướng sửa: riêng từng route ghi mode, factor chứng minh, attempt claim, semantic dedup, challenge lifetime/consume, budget storage/SMTP/password hashing, outcome unknown khi crash. Email verification ghi đúng là confirmation; không gán MFA. Quyết định persistent anti-guess budget hoặc mô hình reset chấp nhận được có bound.
- Tiêu chí: same packet/new attempt, resend sau fail/crash, account commit mất response, confirm code concurrent, restart quota, all-zero operation_id không mở protected write. Không hứa exactly-once SMTP.
- Người dùng chốt: **Có**, policy bootstrap state/durability và trải nghiệm retry.

### I04 — Enrollment và key recovery ceremony atomic (F06)

- Vấn đề: D:94–108 mô tả policy nhưng chưa có contract first enrollment/additional install/replace/lost-all.
- Nguồn: S07 §§4.1–4.2,4.5–4.6; code auth state F05.
- Tác động: first-install branch có thể thành đường né old-key/recovery requirement nếu không account-scoped; PoP chỉ chứng minh giữ new key, không ownership quyền cũ.
- Hướng sửa: account credential lifecycle; signed/challenged binding public key+principal+purpose+epoch+expiry; approve/consume/revoke/issue trong một transaction; recovery code một lần hashed/throttled, notification độc lập. Initial enrollment và machine provisioning có kênh/owner proof riêng.
- Tiêu chí: same challenge hai keys, account switch, token theft, first-install reset, recovery race/restore, old-key revoke race, product QR public. Không tự bỏ machine-write lock khi mất tất cả yếu tố.
- Người dùng chốt: **Có**, owner/admin recovery proof, multi-installation policy và authority quyền cấp.

### I05 — Recovery epoch authority và ledger extension evidence (F08)

- Vấn đề: D:338–357,519–544 chưa freeze ceremony xác nhận current epoch ngoài snapshot và extension proof khi seq cao hơn.
- Nguồn: S10 [Memoir §§I,II-D,III](https://www.ieee-security.org/TC/SP2011/PAPERS/2011/paper024.pdf); source chỉ chỉ ra continuity assumptions, không chứng minh R5.
- Tác động: authenticated-but-stale artifact không tự cho reopen; observed frontier chưa đủ chứng minh suffix không mất. Redelivery có thể vượt safe unknown policy nếu adapter làm tắt.
- Hướng sửa: state/authority table, nonce-bound confirmation có freshness và independent rollback domain; canonical extension proof bounded; stable physical identity + rotation binding; decision log reconciliation dựa chứng cứ. Giữ cấm live-memory restore không kiểm soát.
- Tiêu chí: authority replay; latest commit không peer thấy; all peers restore; audit delayed/out-of-order; seq cao không extension; fork head; reflash lost machine ledger; unsigned/MAC giả không quarantine toàn server. Không dùng no alarm làm continuity.
- Người dùng chốt: **Có**, kênh authority/availability và quy trình đối soát; không tự thêm TPM/replica dịch vụ.

### I06 — Transaction admission/revoke/dispatch mapping từng feature (F09)

- Vấn đề: D:305,391–400 là yêu cầu tương lai; menu hiện check rồi send rời transaction, staff revoke đọc session trước transaction.
- Nguồn: S04/S05/S07; code chi tiết ở F09. Semantics claim/revoke thứ tự commit là lựa chọn R5.
- Tác động: implementation mới có thể giữ TOCTOU nếu chỉ thêm middleware; cache outcome cũng cần quyền mới.
- Hướng sửa: map feature→conn→authoritative rights→operation claim→queue take/dispatch; writer lock trước đọc quyền/admission, wait ngoài DB; giữ SQL/rule feature tại folder theo MODULE_PATTERN.
- Tiêu chí: barrier race logout/staff revoke/claim/dispatch/direct SQL; hai thứ tự commit đúng; busy/commit error không side effect; đã dispatch không remote-kill hứa hẹn.
- Người dùng chốt: **Không cần chốt kiến trúc mới nếu chỉ làm đúng R5**; cần duyệt contract nếu thay semantics/module/caller. Lượt này không triển khai.

### I07 — Dependency capability matrix và pinned vector plan (F11)

- Vấn đề: D:53–63 chưa có Dart/Python pair chứng minh same-context Export; candidate Dart enc33 khác RFC P-256 enc65 ở wire ví dụ.
- Nguồn: S08 [PyHPKE API](https://pyhpke.readthedocs.io/en/latest/api.html), S09 [Turnkey package](https://pub.dev/packages/turnkey_crypto), S01 §7.1.1.
- Tác động: “HPKE” tên package không chứng minh Base/Export/wire compliance; high-level single-shot API có thể bỏ context cần cho response.
- Hướng sửa: candidate table exact version/date/commit/license/support, Setup/Base/info/AAD/Export/enc/tag layout/RNG/key validation/errors; archive hash và original vectors; nếu Dart không qua gate thì nghiên cứu FFI theo R5, không tự primitive glue.
- Tiêu chí: original RFC vectors + cross-language request/export response + negative binding, clone/retry/exception; input=M dài không truncate; ghi version runtime. Chưa đủ candidate không kết luận không tồn tại thư viện Dart.
- Người dùng chốt: **Có** khi chọn suite/library/FFI/wire; nghiên cứu matrix tự làm được trong phạm vi tài liệu.

## P1

### I08 — Bảng response state: reject, cached resend, current auth (F04)

- Vấn đề: D:205–206 “non-winner không ciphertext” và D:213 cached retransmit dễ được implement hai cách.
- Nguồn: S01/S02/S03; ambiguity từ chính R5, chưa exploit.
- Tác động: handler có thể vô tình Seal lỗi lần hai hoặc resend stale outcome trái quyền hiện hành.
- Hướng sửa: table CLAIMED/SEAL_STARTED/SEALED/SENT/CLOSED theo expired/revoked/store unavailable/clock; exact bytes cache chỉ khi explicit allowed, không cấp ownership Seal mới; bootstrap và protected policy riêng.
- Tiêu chí: instrumentation Seal count theo CID, replay race + crash từng gap + cached response sau revoke/expiry. Không “retry success” làm test oracle duy nhất.
- Người dùng chốt: **Có** nếu chọn khác policy response/retransmit hiện tại; làm rõ từ ngữ rồi trình duyệt.

### I09 — Quota fairness, unknown retention và recovery reserve (F07/F10)

- Vấn đề: D:358–361,404–413 có bounds nhưng chưa tính shared SQLite/SMTP/hash bottleneck hay đường ghi result khi store gần/full.
- Nguồn: S02 §6.2.2; S03 Appendix B; S07 §3.2.2.
- Tác động: safe fail-closed nhưng liveness recovery có thể tự khóa; invalid anonymous packets tiêu CPU trước claim.
- Hướng sửa: bounded admission trước verify/decap/hash, per-principal sau authenticated identity, riêng email/account challenge budget và nguồn ingress trusted; reserve result/reconcile/storage capacity có accounting, không xóa unknown. Không tự chọn số workers/quota.
- Tiêu chí: saturation từng lane/common DB, flood unknown kid/sig/bootstrap/valid A2; memory/queue/record bounds có đo; recovered result còn được xử lý đúng khi new admissions bị dừng; claims không bị evict.
- Người dùng chốt: **Có** về policy tài nguyên/availability; threshold cần đo sau safety gate.

### I10 — Hồ sơ assumptions, source snapshots và review evidence

- Vấn đề: R5 review “không blocker mới” dễ bị đọc thành đạt production; original nguồn lượt này chưa lưu do DNS, library metadata mutable và cache lệch.
- Nguồn: toàn SOURCES.md và D:449–482.
- Tác động: không tái kiểm được version/errata và assumptions; thiếu chứng cứ có thể bị che bởi tên chuẩn.
- Hướng sửa: Claude tải public originals nếu runtime cho phép, lưu SHA256/URL/date/parts read; xác minh RFC errata, NIST draft vs final, concrete pinned library source. Checklist assumption owner/evidence/fail behavior cho time/storage/root/recovery/topology, trạng thái “chưa kiểm” rõ.
- Tiêu chí: mỗi finding có source và design/code locator, biết là fact/inference/open; không marks pass khi chưa execution; tài liệu render/HTML nếu sửa ở lượt sau phải qua scope/user approval.
- Người dùng chốt: **Không** cho thu thập/refine tài liệu trong phạm vi; **Có** khi thay canonical/HTML hay architecture theo task mới.

## P2

### I11 — So sánh alternative response key schedule sau safety gates

- Vấn đề: R5 fixed Export response nonce cần durable CAS; OHTTP dùng random response_nonce thêm KDF/wire/RNG dependencies.
- Nguồn: S01 §9.8, S02 §4.4/6.5; F04.
- Tác động: có thể đổi tradeoff ciphertext overhead/write/recovery; không sửa replay business hay actor unknown.
- Hướng: prototype/spec riêng so fixed singleton và randomized response candidate dưới cùng threat/admission model; không gọi OHTTP compliant/anonymity, không bỏ durable business ledger.
- Tiêu chí: byte-exact vectors, duplicate/key-nonce/error/rng faults, context collision assumptions, latency/write/wire cùng conditions; chưa có số đo.
- Người dùng chốt: **Có** trước đổi protocol. Đây là option nghiên cứu, không khuyến nghị thay R5 ngay.

### I12 — Tối ưu pre-decap replay reject và Pareto measurement

- Vấn đề: protected duplicate hợp lệ có thể tiêu verify+decap trước phát hiện claim; số operation không phải latency.
- Nguồn: D:254–270,418–447; S01 §9.7.3/S03 forgery limits.
- Hướng: chỉ khảo sát early read-only lookup sau signature + mode/freshness, reject transport cho existing attempt; không reserve/consume nonce từ input chưa auth, không trả business cache trước kiểm quyền. So với baseline bằng thiết bị thật và pinned deps.
- Tác động/đánh đổi: DB lookup thêm I/O, races vẫn phải atomic claim cuối; duplicate flood giảm crypto có thể tăng contention.
- Tiêu chí: differential semantics/race tests giữ all gates; đo CPU_p95/durable writes/memory/wire/recovery trong cùng workload, không dùng unittest wall time.
- Người dùng chốt: **Có** nếu thay pipeline/boundary canonical; nghiên cứu lý thuyết hiện không thay code.
