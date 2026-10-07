# Phát hiện đối chiếu R5 — nghiên cứu, chưa nghiệm thu

Ngày 07/10/2026. Đường dẫn `D` dưới đây luôn là **agent_workspace/tasks/middleware/internal/packet-security/design.md**. Dẫn `D:500–505` nghĩa là file đó, dòng 500–505 của snapshot đã đọc; SHA256 trong [READ_SCOPE.json](READ_SCOPE.json). Canonical design và code giữ nguyên. [SOURCES.md](SOURCES.md) ghi nguồn thực tế và phần đã đọc. “Cao” là chắc về nguồn/code/quan hệ logic, không là chứng nhận composition. Tất cả trace/test dưới đây **chưa chạy**.

## F01 — P0: durable COMMIT phải gắn journal mode, không chỉ FULL

**Đối chiếu:** D:196–212,500–512; packet-security.html:224–225 và phần §4 hiển thị FULL. Code hiện trạng `server/database/connection.py:14–19` chỉ set foreign_keys; không pin synchronous/journal_mode ở hàm này. Không mở DB để suy cấu hình runtime.

**Nguồn:** [S04, SQLite synchronous](https://www.sqlite.org/pragma.html#pragma_synchronous) phân biệt WAL+FULL với rollback journal; EXTRA bổ sung directory sync trong DELETE mode. **Mức chắc chắn cao** về nội dung official; trung bình về khả năng lỗi deployment chưa biết.

**Suy luận riêng:** R5 đã có điều kiện stable media flush và fault gate; đây là yêu cầu làm cụ thể gate, không kết luận mọi cấu hình R5 đều sai. Trace cần bác bỏ: same epoch được authority xác nhận sau reboot → CAS đã COMMIT → Seal → power loss → transaction CAS biến mất → packet vẫn fresh → attempt/CID lại claim/Seal. Nếu boot luôn đổi epoch hoặc medium bảo đảm commit survives thì trace đó bị chặn; cần chứng cứ chứ không mặc định.

**Đánh đổi:** WAL+FULL hoặc rollback+EXTRA tăng sync/latency; chọn theo platform và SQLite version đã pin, không tự thay architecture. Flush success không bao hàm firmware/controller honest. **Kiểm cần làm:** crash/power-loss trước/sau commit ở server/máy; ghi invariant surviving CAS trước gọi Seal/executor; thử disk-full/I/O/COMMIT exception; không đánh pass từ kill process đơn thuần.

## F02 — P0: NTS là một thành phần, chưa là trusted-clock capability

**Đối chiếu:** D:77–90,227–250,556–561. Clock dùng cho manifest expiry, packet admission và cleanup; mất bound ảnh hưởng cả confidentiality invariant và availability.

**Nguồn:** [S06, RFC 8915 §§8.5–8.7](https://www.rfc-editor.org/rfc/rfc8915.html#section-8.5). Cold-boot certificate validation có khó khăn khi clock sai; authenticated NTP vẫn chịu asymmetric delay, độ lệch chịu ràng buộc bởi distance policy. **Chắc chắn cao**; chưa xác minh Android/Pi/OS daemon thực.

**Suy luận riêng:** Một boolean “NTS enabled” không đủ mở CLOCK_UNTRUSTED. Gate cần trust CA/pin, first-time certificate policy, uncertainty bound, holdover drift, suspend/resume, clock-adjust authority và fallback policy. Nếu network bị chặn, hành vi locked là tradeoff hiện R5 chọn, không tự mở unsigned time repair.

**Kiểm cần làm:** cold boot clock ±1 ngày, asymmetric delay, stale/expired certificate, nguồn time mất, OS auto-switch SNTP/NITZ, suspend dài; mọi claim/Seal/cleanup đóng khi uncertainty vượt bound. Không đặt số Δ/σ/MAXDIST cho sản phẩm từ ví dụ RFC.

## F03 — HPKE Export và chữ ký ngoài: R5 có cơ sở, proof composition còn thiếu

**Đối chiếu:** D:26–43,146–149,193–225. **Nguồn:** [S01, RFC 9180 §§5.3,9.1.1,9.7,9.8](https://www.rfc-editor.org/rfc/rfc9180.html#section-9.1.1). RFC cho Export, chỉ ra replay/PFS limits và gợi ý signature trên enc/ct để chống KCI. Base không xác thực sender; response dùng exported secret không là chữ ký server. **Chắc chắn cao** về RFC; composition R5 chỉ giả thuyết có điều kiện.

**Suy luận riêng:** Protected request signature bind cả M/enc/ct là hợp lý cho A0/A1; nó không thay session→principal→credential binding sau Open, kiểm quyền feature hay containment khi server bị chiếm. Bootstrap thiếu signature phải giữ nhánh mode explicit. Response cho request do client trung thực sinh có secret chung dưới recipient public key đã tin; kết luận hẹp A0/A1 dựa secret không lộ, không nâng thành third-party evidence. Khi recipient key lộ, chữ ký người dùng có thể vẫn ngăn giả request mới nếu signing key độc lập còn an toàn, nhưng không cứu nội dung traffic cũ hay response authenticity.

**Kiểm:** F8 plus tráo enc/ct/M, kid alias/algorithm mismatch, cross-route/cross-deployment/cross-epoch, invalid KEM inputs, key compromise sandbox mô phỏng; không tự viết primitive. Khóa/suite hiện chưa chọn. Không có formal proof trong lượt này.

## F04 — P0/P1: response determinism làm durable Seal ownership thành nghĩa vụ cứng

**Đối chiếu:** D:193–216,254–272. **Nguồn:** [S01 §§5.3,9.8](https://www.rfc-editor.org/rfc/rfc9180.html#section-9.8), [S02 §§4.4,6.5](https://www.rfc-editor.org/rfc/rfc9458.html#section-4.4), [S03 §8](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38d.pdf).

R5 Export labels cho một context cố định cho key/nonce cố định; OHTTP thêm random response_nonce và KDF nên hai response không cùng cách dẫn xuất. OHTTP cũng không thay application replay policy. **Chắc chắn cao** về khác biệt; không suy OHTTP tự an toàn hơn toàn bộ.

**Suy luận riêng:** UNIQUE(audience,kid,attempt) rộng hơn CID(M,enc) giúp cùng M/enc nhưng ct thay vẫn không reseal. CAS phải là authority dùng một lần, không hidden counter của thư viện. Crash sau CAS trước lưu sealed bytes chấp nhận mất response; attempt mới trả semantic outcome từ ledger. Trong protected mode attacker không sửa M mà giữ signature; bootstrap attacker có thể chiếm attempt_id public với context riêng: chủ yếu availability, như D:545–546 đã thừa nhận.

**Chưa rõ:** D:205–206 nói mọi non-winner chỉ transport error không ciphertext, D:213–214 cho retransmit exact sealed bytes; HTML §2.5 diễn tả cached retransmit. Cần bảng state phân biệt owner Seal với cached resend và quy tắc expired/revoked/current quyền. Đây là ambiguity hợp đồng, chưa chứng minh exploit. Cached bytes không là invocation Seal mới.

**Kiểm:** concurrent duplicate và variant ct cùng M/enc, replay after Open/error/full store, crash CAS→Seal→persist→send; đếm raw response AEAD Seal call theo CID chứ không chỉ response thành công. OHTTP-style random response nonce chỉ là candidate đổi protocol **cần người dùng chốt**, không thay design ở lượt này.

## F05 — P0: bootstrap cần phân loại side effects và assurance riêng

**Đối chiếu:** D:94–114,136,152–155,205–208; packet-security.html §2.3/2.4 nói bootstrap có thể bỏ operation ledger. Code `server/service/user_login/user_login_process.py:20–27` tạo phiên; `server/lib/security/user_session.py:23–32` ghi phiên SQLite. Đăng ký ở `user_register_process.py:28–29,64–73,126–130,136–142`; OTP ở `otp/user_otp_process.py:12–16,95–118,122–148` giữ state/limits RAM rồi gọi SMTP ngoài lock.

**Nguồn:** [S07, NIST SP 800-63B-4 §§3.1.3,3.2.2,4](https://pages.nist.gov/800-63-4/sp800-63b.html); [S05, RIFL §§3–4.1](https://web.stanford.edu/~ouster/cgi-bin/papers/rifl.pdf). Email confirmation khác email authentication/MFA; new authentication challenge không tự reset failure budget. **Cao** về source/code; **trung bình** về cần thay bootstrap contract vì mức bảo đảm chưa chốt.

**Suy luận riêng:** “Không protected machine write” không tương đương bootstrap không side effect. R5 attempt claim chống cùng packet, không dedup register/resend/login bằng attempt mới. Crash SMTP đã gửi nhưng response chưa lưu, client retry mới có thể gửi lại; crash commit account trước account_created RAM làm outcome không rõ. Lost RAM không tự đồng nghĩa account tạo trùng (DB uniqueness có thể chặn), nhưng không có bằng chứng semantic outcome bền. OTP verified được cache success trong cùng phiên là state kết quả, không tự chứng minh OTP đã bị sử dụng hai lần để cấp hai quyền mới.

**Hướng kiểm:** inventory từng route: login token issue; register pending; OTP delivery/consume; first credential bind; recovery. Tách repeat result với repeat authorization, quota gửi với quota đoán, attempt với business challenge. Chốt flow nào unknown qua crash, flow nào idempotent/restart reset chấp nhận được; recovery/key bind cần consume bền atomic với chuyển quyền, không tự áp exactly-once email delivery.

## F06 — P0: enrollment/recovery chưa có ceremony kiểm được

**Đối chiếu:** D:94–108. **Nguồn:** [S07 §§4.1,4.2.1.1,4.5–4.6](https://pages.nist.gov/800-63-4/sp800-63b.html#authenticator-event-management). Recovery code có entropy, hash, throttle và notification requirements; binding/recovery là sự kiện quyền riêng. **Cao** về nguồn; **trung bình** khi chọn policy cho dự án, không tuyên bố AAL compliance.

**Suy luận riêng:** R5 đúng khi không cho chỉ bearer/password/OTP thay khóa cũ, nhưng “authenticated session + challenge” cho first enrollment cần xác định installation/account đã có credential khác hay chưa. Một account từng enroll không được đi nhánh “first-install” để né recovery. Challenge phải bind account, new public key, purpose, epoch, expiry và approved action; old-key PoP hay recovery approval cùng transaction chuyển credential/consume. Notification không thay authentication, product QR public không chứng minh possession máy.

**Kiểm:** parallel bind cùng challenge hai keys, session switch, stolen token, first-install flag reset, old key revoke giữa verify và commit, recovery code reuse sau crash/restore, recovery notification target đổi cùng request. Cần người dùng chốt lost-all-factors/admin reprovisioning policy và việc dừng machine write.

## F07 — Ledger/GC: dùng RIFL để soi assumptions, không nhập exactly-once actuator

**Đối chiếu:** D:312–363,375–387. **Nguồn:** [S05 §§3–4.4](https://web.stanford.edu/~ouster/cgi-bin/papers/rifl.pdf). Completion record phải atomic với storage side effect; GC chỉ an toàn khi stale retry bị từ chối. **Cao** cho nguyên tắc, R5 vật lý chưa có proof.

**Suy luận riêng:** Direct SQL có thể cùng transaction; actuator không thể ghép vật lý vào SQLite commit, do đó claimed-before-executor và unknown là bảo đảm hẹp có chủ ý. Token/credential rotation không mở namespace mới cho command. Giữ unresolved không prune tạo nguy cơ storage exhaustion lâu dài; quota chặn admission mới giữ safety nhưng cần dự trữ cho result/reconciliation để không làm recovery tự kẹt. Identity operation độc lập attempt là điều kiện giữ intent retry.

**Kiểm:** F2/F4, command đã execute mất result, rotate credential, same operation payload conflict, GC boundary với packet future-skew, ticket expiry, outstanding unknown lâu ngày, power-loss claim/result. Không lấy lease GC hay benchmark RIFL áp thẳng; không cho client mới sinh ý định sau lỗi vận chuyển nếu chưa đối soát.

## F08 — P0: hash/witness frontier là detection evidence, chưa là nguồn continuity tự đủ

**Đối chiếu:** D:338–357,506–554. **Nguồn:** [S10, Memoir §§I,II-D,III](https://www.ieee-security.org/TC/SP2011/PAPERS/2011/paper024.pdf) phân biệt snapshot hợp lệ nhưng cũ và message replay; trusted state phải nằm ngoài rollback storage. **Cao** về giới hạn; **trung bình** về toàn composition chưa mô hình hóa.

**Suy luận riêng:** R5 đã nói không alarm ≠ continuity và live VM restore không hỗ trợ. Issuer MAC giúp A2 không tự khai seq cao để quarantine toàn server. Fresh audit expected-at-issuance tránh lẫn out-of-order telemetry với rollback. Tuy nhiên peer chưa từng thấy latest frontier không phát hiện suffix mất; đồng loạt peer/DB restore cũng không được giải quyết bằng hash chain. Recovery authority phải xác minh epoch hiện hành bằng ceremony ngoài snapshot, không chỉ artifact có chữ ký trên disk còn hạn. “Authority confirm current” cần challenge/session freshness để old confirmation không mở admission.

**Chưa rõ:** encoding/size bound/verification của extension evidence seq tăng và lifecycle audit challenge chưa freeze. Không tự redeliver unresolved vì seq tăng hoặc missing frontier. Physical machine identity surviving reflash/re-enroll cần inventory thật, không giả định hardware chống clone.

**Kiểm:** N2/N2o/N3 plus witness issued/commit boundaries; fake high seq/MAC; two forks cùng seq khác head, higher seq không extension, stale challenge, audit concurrent dispatch, authority replay, restore tất cả peers. Memoir proof không là proof R5; không áp safe deterministic replay vào Seal/executor vật lý.

## F09 — P0: revoke linearization là yêu cầu mới, hiện trạng không có admission transaction

**Đối chiếu:** D:305–308,389–400. Code `server/lib/security/user_session.py:35–45,56–61`; `server/lib/machine/machine_access.py:12–23`; `server/service/dashboard_sync/menu_sync/machine_menu_update.py:57–72`; `server/service/machine_share/machine_staff_revoke.py:15–26`.

**Nguồn:** [S04 transaction durability](https://www.sqlite.org/pragma.html#pragma_synchronous), [S05 atomic completion](https://web.stanford.edu/~ouster/cgi-bin/papers/rifl.pdf), [S07 invalidation §4.5](https://pages.nist.gov/800-63-4/sp800-63b.html). Thứ tự admission/revoke cụ thể là **policy riêng R5**, không điều RFC/NIST chứng minh.

**Suy luận từ code, cao:** Menu check_access đọc session và quyền qua helpers, sau đó send không cùng một authoritative admission transaction với revoke; không thấy durable operation claim ở flow đã đọc. Trace đề xuất kiểm: T1 check hợp lệ → T2 logout/revoke COMMIT → T1 enqueue. Hiện trạng không đạt invariant R5 “revoke trước claim reject”; đây là gap triển khai R5 chưa có, không nói design tự sai. Staff revoke check_login trước transaction cũng cần session recheck nếu R5 yêu cầu admission chính revoke được tuyến tính hóa.

**Đánh đổi:** BEGIN IMMEDIATE trước read quyền/claim cho writer ordering nhưng giữ lock ngắn; wait máy ngoài transaction. Cần review target/right cùng conn ở feature, không kéo rule feature vào lib. Revoke sau dispatch vẫn không remote-kill; cache outcome phải policy quyền hiện hành. **Kiểm:** barrier-controlled race revoke/claim/queue-take, assert hai thứ tự commit, outcome cache sau revoke, transaction error và deadlock/busy handling. Không chạy DB sản phẩm.

## F10 — P1: quotas cần bound cả crypto trước claim và recovery sau đầy kho

**Đối chiếu:** D:404–416,436–440,358–361. **Nguồn:** [S02 §6.2.2](https://www.rfc-editor.org/rfc/rfc9458.html#section-6.2.2), [S03 Appendix B](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38d.pdf), [S07 §3.2.2](https://pages.nist.gov/800-63-4/sp800-63b.html).

**Suy luận riêng:** Per-credential quota sau chữ ký chưa đủ chống unknown kid/malformed signature/anonymous HPKE decap flood; R5 đã có global crypto bound nhưng chưa đặc tả queue admission/fairness hay saturation response. Attempt store toàn bootstrap sentinel không dùng kid để chia source quota. Quota principal không được key bằng client header/IP giả. Retention bound là capacity model dưới assumptions, không measurement SQLite bytes. Bootstrap password hashing, SMTP workers và log sink cần bound riêng; protected reserved workers chưa tự bảo vệ nếu mọi lane chung SQLite bị busy/full.

**Kiểm:** no-verify packet không chiếm durable claim; valid A2 flood vẫn bounded; bootstrap saturation không làm heartbeat/result deadline mất do common DB lock; unknown-store-full giữ record và có đường recovery bounded. Không tự chọn ngưỡng từ tải giả; benchmark crypto/hashing/write contention nằm ở future prototype.

## F11 — P0: dependency gate Dart/Python chưa có bằng chứng end-to-end

**Đối chiếu:** D:53–63,146–149,193–194,453–454. **Nguồn:** [S08 API maintainer](https://pyhpke.readthedocs.io/en/latest/api.html), [S09 package maintainer](https://pub.dev/packages/turnkey_crypto), [S01 enc serialization §7.1.1](https://www.rfc-editor.org/rfc/rfc9180.html#section-7.1.1).

**Đã thấy, cao:** PyHPKE docs 0.6.5 có setup context, info/AAD, export; docs không chứng minh implementation đã audit. Turnkey README có HPKE tên API và ví dụ cắt enc33 P-256, trong khi RFC P-256 enc65. **Bổ sung source:** S09 `formatHpkeBuf` có giải nén wrapper enc33; enc33 đơn thuần không chứng minh KEM sai. Umbrella API không expose generic HPKE context; `hpkeEncrypt` tự dựng AAD, không nhận info/AAD từ caller và trong file đó chưa thấy Export context. Source main/cache không được đồng nhất với release 0.2.0. **Chưa rõ:** conformance toàn package, Export qua API khác và suite coverage; chưa được chọn dependency.

**Suy luận riêng:** Chỉ API single-shot trả enc,ct/plaintext có thể không cho giữ đúng context request để Export response. Adapter cần Setup→one request Seal/Open→two Export labels trên cùng context; không dựng context fresh để “lấy Export” gây mismatch, không dùng ContextR.Seal thay AEAD response. Full info=M dài vượt khuyến nghị interoperability 64 byte trong RFC §7.2.1, không vượt normative crypto limit; candidate phải nhận byte exact, không silently truncate.

**Kiểm:** pinned tag/commit+archive hash, original vectors KEM/key schedule/export, cross Dart/Python encode, both AEAD candidates, negative fields, no secret logging, secure RNG/FFI memory/thread/lifetime. Không cài package hay chạy vector trong lượt này. R5 fallback nghiên cứu FFI giữ nguyên; mọi đổi suite/wire cần duyệt.

## Những điều chưa kết luận

Không có blocker mật mã mới được chứng minh bằng exploit/proof; có P0 cần làm cụ thể gate và P1 hợp đồng còn mơ hồ. Không xác nhận thời gian, media, key storage hoặc Caddy topology của deployment. Không đo CPU/latency/wire/memory; không chạy product tests, crypto vectors, simulation hoặc formal verification. Các test ở đây là tiêu chí/trace đề xuất. Ba HTML đọc text theo nhu cầu, không visual QA và không sửa HTML.
