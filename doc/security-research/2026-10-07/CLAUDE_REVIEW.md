# CLAUDE_REVIEW — phản biện độc lập R5 (lượt Claude, 07/10/2026)

**Trạng thái:** chốt khoảng 02:20. C01–C05 có verdict, C06 làm một phần, C07 có ánh xạ. Việc còn lại ghi ở cuối file.
Phiên bắt đầu 02:11 Asia/Ho_Chi_Minh theo scheduler.

**Bàn giao đầu vào:** Codex kết thúc bình thường (`execution-status.json`: finished 02:04, exit 0).
HANDOFF.md không còn placeholder, nên lượt này **review** đầu ra Codex chứ không làm lại R01–R03.
SHA256 của design R5 và 9 file code trong READ_SCOPE.json khớp lúc 02:12. Locator dòng Codex còn dùng được.

**Ký hiệu:** `D` = `agent_workspace/tasks/middleware/internal/packet-security/design.md`.
Đường dẫn code tính từ thư mục gốc repo. Verdict gồm **Đồng ý**, **Đồng ý một phần**, **Bác bỏ** và **Chưa đủ bằng chứng**.
Mọi trace dưới đây là suy luận trên giấy. **Chưa chạy** test, vector, benchmark hay mô phỏng power-loss.
Không có formal proof.

## 0. Giới hạn của lượt này (đọc trước)

- **Tải bản gốc vào `sources/` bị chặn:** lệnh `curl` cần quyền mà phiên non-interactive không cấp. Lệnh bị từ chối tự động, nên không có file gốc mới và không có SHA256.
- **Kiểm SQLite build local bị chặn:** lệnh `python3 -c` (chỉ dùng DB `:memory:`) cũng bị từ chối. Vì vậy không biết SQLite version, compile default synchronous hay autocommit mode thực tế. Chỉ biết từ `python3 --version` là Python 3.14.4.
- **Nguồn đọc qua WebFetch ngày 07/10/2026:** đây là bản markdown hóa do một model nhỏ trích dẫn, không phải bản gốc byte-exact. Mức tin của đoạn trích là "trích qua công cụ"; cần đối chiếu bản gốc trước khi đưa vào canonical. Các nguồn đã đọc:
  - S04 [sqlite.org/pragma.html#pragma_synchronous](https://www.sqlite.org/pragma.html#pragma_synchronous): mục synchronous, ma trận Rollback/WAL, fullfsync.
  - S11 (mới) [sqlite.org/wal.html](https://www.sqlite.org/wal.html): §1 Disadvantages, §2.3, §3.3 Persistence of WAL mode.
  - S01 [RFC 9180](https://www.rfc-editor.org/rfc/rfc9180.html): §§5.3, 9.1.1, 9.7.3, 9.7.4, 9.8, 9.9. Bản tóm có trích một phần.
  - S06 [RFC 8915](https://www.rfc-editor.org/rfc/rfc8915.html): §§8.5–8.7.
- **Chưa tự đọc:** S03 (NIST 38D), S05 (RIFL), S07 (NIST 63B-4), S10 (Memoir) và S08/S09. Khi viện dẫn chúng, review này ghi rõ "theo ghi chú Codex".
- **Code chỉ đọc source:** không mở DB, env, SMTP config, secret hay dữ liệu tài khoản. Không đọc `user_otp_send.py`.

---

## C01 — durable COMMIT / Seal / executor (F01, I01, một phần F04)

**Verdict: Đồng ý về nội dung.** Phân loại đây là **lỗi đặc tả gate cần sửa chữ**: D:502 kê một cấu hình mà chính SQLite nói có thể không durable.
Không phải blocker kiến trúc mới. Tuy vậy, tác động nặng hơn Codex mô tả (xem trace).

### Bằng chứng nguồn

- S04, mục FULL (trích): *"FULL is atomic, consistent, isolated, and durable (ACID) in WAL mode and is atomic, consistent, and isolated with a rollback journal … FULL is not necessarily durable across a power loss in rollback mode, so if durability is desired, it is best to set the synchronous mode to EXTRA."*
- S04, mục EXTRA: thêm sync thư mục sau khi unlink journal ở **DELETE** mode. *"Without EXTRA … a single transaction that commits right before a power loss might get rolled back upon reboot."* Đồng thời *"EXTRA is no different from FULL in WAL mode."*
- Ma trận S04: Rollback+FULL = "Maybe not durable"; WAL+FULL = ACID; Rollback+EXTRA = ACID.
- S11 §3.3: *"Unlike the other journaling modes, PRAGMA journal_mode=WAL is persistent."* Ngược lại, TRUNCATE khi mở lại quay về DELETE.
- S11 §1: *"WAL does not work over a network filesystem."*

### Bảng journal mode cho commit bảo mật (đề xuất, chờ user duyệt)

| journal_mode | synchronous | Theo S04/S11 | Ghi chú cho R5 |
|---|---|---|---|
| WAL | FULL hoặc EXTRA | ACID; WAL sync mỗi commit | Mode bền vững qua connection; cấm network FS; cần kiểm checkpoint |
| DELETE | EXTRA | ACID | Phải set lại synchronous mỗi connection (xem dưới) |
| DELETE | FULL | "Maybe not durable" | **Không đạt** cho claim/CAS/ledger, đúng như F01 |
| TRUNCATE/PERSIST/MEMORY/OFF | bất kỳ | Không thấy S04 mô tả durability riêng cho TRUNCATE/PERSIST; MEMORY/OFF không bền | Loại khỏi profile, trừ khi có nguồn chính thức. **Chưa đủ bằng chứng** để chấp nhận |

**Tiền điều kiện chưa được R5 nêu:**

1. `synchronous` không lưu trong file DB. Mỗi `connect()` mới cần set lại.
   - `server/database/connection.py:14–19` mở connection mới cho mỗi lần dùng và hiện chỉ set `foreign_keys`.
   - Đây là suy luận từ việc pragma có dạng query/set theo connection; **chưa kiểm** bằng runtime vì bị chặn. Cần một bước khẳng định khi triển khai: đọc lại `PRAGMA synchronous` và `PRAGMA journal_mode` trên chính connection commit, trước khi coi commit là authoritative. I01 của Codex đã đề xuất điều này; tôi đồng ý.
2. Compile-time default của bản SQLite trong distro chưa xác định.
3. S04 ghi `fullfsync` chỉ có tác dụng trên macOS. Trên Linux/Pi, độ bền phụ thuộc honest flush của thiết bị (D:504–505 đã thừa nhận).

### Trace tác động: mạnh hơn "phá invariant" chung chung

Cấu hình giả định: rollback journal + FULL, tức đúng chữ D:502 nếu người triển khai giữ mặc định DELETE.

1. Route direct SQL thực hiện claim và ghi nghiệp vụ trong cùng transaction (D:375). Sau đó CAS SEAL_STARTED được commit (D:208–210), Seal response R1 với `key, nonce = Export(ctx)`, rồi gửi đi.
2. A0 chụp lại `(M, enc, ct, sig)` và R1.
3. Mất điện ngay sau commit. Theo S04, transaction cuối có thể bị rollback.
   - Nếu chỉ mất CAS mà claim còn: replay gặp claim cũ, rơi vào nhánh non-winner (D:205), **an toàn**.
   - Nhánh nguy hiểm cần mất cả claim, nghĩa là claim và CAS nằm trong cùng transaction cuối hoặc FS mất nhiều hơn một transaction. S04 chỉ mô tả "a single transaction", nên tôi **không khẳng định** mất được nhiều hơn một.
4. Sau boot: clock được xác minh lại (D:237–239); epoch **giữ nguyên** vì đây là mất điện, không phải restore. D:347–348 chỉ yêu cầu xác nhận epoch hiện hành, không đổi epoch.
5. Packet còn trong `expires_at`, nên A0 replay. Server Open thành công (khóa HPKE tĩnh còn), thắng claim mới, chạy nghiệp vụ lại (business state cũng đã rollback), CAS rồi Seal R2 **với cùng Export key/nonce**.
6. Nếu plaintext R1 ≠ R2 (ví dụ `server_seq` hoặc payload khác), đây là **AEAD nonce reuse dưới cùng key**:
   - A0 lấy được XOR của hai plaintext.
   - Với GCM, nonce reuse cho phép suy ra khóa xác thực, dẫn tới khả năng giả tag cho context đó.
   - ChaCha20-Poly1305 dùng chung khóa Poly1305 một lần cho cùng (key, nonce), nên cũng có khả năng giả mạo.
   - Kết luận này dựa trên kiến thức mật mã chuẩn, **lượt này chưa đọc lại S03 §8 bản gốc**.
7. Nếu A0 đã chặn R1 không cho tới client, A0 có thể dựng response giả cho attempt đó. Đây là vi phạm bảo đảm A0 của D:16 và D:44, không chỉ lỗi availability.

**Phần giữ R5:**
- Nếu dùng WAL+FULL hoặc DELETE+EXTRA và media honest, trace bị chặn ở bước 3.
- C1b (D:570) và gate D:504–505 đã yêu cầu fault test.
- Nhưng power-loss test chỉ có thể làm lộ lỗi, không chứng minh không có lỗi. Vì vậy cấu hình đúng phải được đặc tả **trước** test, không chỉ dựa vào test. Đây là lý do coi đây là sửa chữ D:502, không phải "đủ vì đã có gate".

**Phép kiểm còn thiếu (chưa làm):**
- Assert runtime journal_mode/synchronous trên mỗi connection commit bảo mật.
- Power-cut thật trên thiết bị đích, đặt giữa claim → CAS → Seal; đếm Seal theo CID.
- Thử disk-full/I/O error ở COMMIT.
- Kill process **không** thay được power-loss (S04: *"Transactions are durable across application crashes regardless of the synchronous setting"*). Đồng ý với F01 về điểm này.

**Đề xuất cho user (không tự sửa canonical):**
- Sửa D:502 thành "WAL + synchronous ≥ FULL, hoặc DELETE + EXTRA; journal mode khác bị cấm cho commit bảo mật; xác minh trên mỗi connection".
- Cân nhắc yêu cầu claim và CAS ở **hai transaction riêng, claim commit trước**. Khi đó việc mất transaction cuối chỉ có thể làm mất CAS, rơi vào nhánh non-winner. Đây là phòng thủ chiều sâu, cần user/architect cân nhắc vì tăng một fsync.

---

## C02 — trusted time / cold boot / manifest freeze (F02, I02)

**Verdict: Đồng ý một phần.** Đồng ý NTS-boolean không đủ. Bác bỏ một phần lo ngại "time repair mở lại old manifest". Bổ sung một mâu thuẫn availability chưa được nêu.

### Bằng chứng (S06, RFC 8915)

- §8.5: client thường không có clock đáng tin khi sync lần đầu, nên khó kiểm hạn chứng thư. Các giảm nhẹ RFC nêu:
  - lưu thời gian đã sync bền và từ chối cert có `notAfter` sớm hơn giá trị đã lưu;
  - bắt strict validation trên hệ có clock nuôi pin;
  - kiểm NTP reply khớp validity của cert;
  - dùng nhiều nguồn.
- §8.6: delay attack *"cryptographic means do not provide a feasible way to mitigate"*. Sai số bị chặn bởi nửa RTT; dùng MAXDIST.
- §8.7: *"SHOULD NOT revert from NTS-protected to unprotected NTP … without explicit user action."*

### Phân tích độc lập

1. **R5 đã có một nửa giảm nhẹ §8.5.** `max_now_seen` bền (D:234–236) đúng là "store time persistently". Tuy nhiên đó chỉ là **cận dưới**. A0 không đẩy clock lùi dưới high-water được, nhưng vẫn có thể giữ clock chậm trong phạm vi delay ≤ RTT/2 (§8.6). Vì vậy σ trong D:81–83 và D:436 phải bao gồm nửa RTT tối đa chấp nhận (MAXDIST) của đường time. Đồng ý với F02.
2. **Bác bỏ một phần "time repair mở lại old manifest".**
   - D:72–73 giữ `manifest_sequence` cao nhất. Manifest có sequence thấp hơn bị từ chối **bất kể thời gian**, nên sửa giờ không mở lại manifest cũ đã bị thay thế trên client đó.
   - Rủi ro thời gian chỉ còn ở trường hợp D:81–83: A1 **giữ lại** manifest thu hồi, client chưa từng thấy bản mới, và clock bị làm chậm thì kéo dài hạn của manifest hiện có. Đây là cửa sổ R5 đã thừa nhận, với bound "remaining validity + uncertainty".
   - Codex nên thu hẹp phát biểu cho đúng trường hợp này.
3. **Mâu thuẫn availability cần user chốt.** D:237–239 yêu cầu sau **mỗi boot** phải có CLOCK_UNTRUSTED cho tới khi xác minh OS time bằng nguồn xác thực. D:243 cấm route time-sync trong packet profile. D:556–558 không tin SNTP/NITZ.
   - Trên Android, app thông thường không kiểm được OS time có đến từ NTS hay không.
   - Tôi **chưa tìm được nguồn chính thức Android** chứng minh có hay không API như vậy, nên đánh giá này là **chưa đủ bằng chứng**.
   - Nếu đúng là không có, phía app gần như không thể qua gate D:558, trừ khi app tự chạy client NTS hoặc có nguồn thời gian ký nonce-bound ngoài OS. Ví dụ là kiểu Roughtime; tôi chỉ biết tên giao thức, **chưa đọc** draft IETF nên không viện dẫn.
   - Đây là câu hỏi kiến trúc cho user, vì nó đụng D:243. Xem CLAUDE_TO_CODEX Q2.
4. **Cold-start deadlock:** thiết bị không RTC, mất mạng tới nguồn time thì R5 fail closed toàn bộ route có Seal. D:79–80 đã nhận đây là tradeoff, nên không báo lại như phát hiện mới.
5. **Không mượn Date correction của OHTTP:** đồng ý HANDOFF. A1 điều khiển header Date nên không dùng được.

**Capability cần inventory (không đặt số):**

| Bên | Câu hỏi phải có bằng chứng | Hành vi khi thiếu |
|---|---|---|
| Server | Daemon NTS nào, trust store, chính sách lúc không có RTC, có tự fallback NTP không, đọc được uncertainty không | Không mở admission sau boot |
| App Android | App có đọc được nguồn/độ tin của system time không; nếu không thì phải chọn nguồn riêng (cần user) | Chặn route có Seal |
| Máy (Pi) | Có RTC không, daemon NTS, CLOCK_BOOTTIME (D:296–299) | Chặn protected request mới (D:249–250) |

**Phép kiểm còn thiếu:** giữ nguyên danh sách F02. Thêm hai mục:
- Cert NTS-KE có `notAfter` < high-water phải bị từ chối.
- Bị strip NTS sang NTP thường thì không được tự fallback.

---

## C03 — bootstrap và credential recovery (F05, F06, I03, I04)

**Verdict: Đồng ý một phần F05.** Bác bỏ mức lo ngại với login, đồng ý với register/recovery. **Đồng ý F06**, và bổ sung một counterexample mới về giai đoạn migration.

### Sự thật từ code hiện trạng (chỉ source)

- **Login** `server/service/user_login/user_login_process.py:20–47`:
  - Không có bộ đếm sai mật khẩu theo tài khoản.
  - Giới hạn duy nhất là limiter theo `request.client_address[0]`, gọi ở `server/lib/http/http_json.py:64` và bật bởi `user_login_main.py:28`.
  - Sau reverse proxy, địa chỉ này là IP proxy. Khi đó toàn bộ người dùng chung một bucket: A2 có thể làm nghẽn login của mọi người, và không có ngân sách đoán theo tài khoản. R5 D:406–412 đã nói IP chỉ là tín hiệu thô và topology là gate. Đây là **gap hiện trạng**, không phải lỗi R5.
- **OTP** `server/service/user_register/otp/user_otp_generate.py:6–8` và `otp/user_otp_process.py`:
  - Mã 6 chữ số, tối đa 5 lần sai cho mỗi mã.
  - Mỗi lần gửi lại reset `attempts = 0` (`user_otp_process.py:117`).
  - Tối đa 5 lần gửi/email/giờ (`:93`); `EMAIL_LIMITS` nằm trong RAM (`:13`).
  - Suy ra cận trên ≈ 25 lần đoán/email/giờ khi process không restart, tức ≈ 2,5·10⁻⁵/giờ. Restart xóa bộ đếm.
  - Rủi ro thấp, chỉ cho phép đăng ký tài khoản với email không sở hữu, nhưng **bound không bền qua restart**.
- **Register:**
  - `add_user_with_hash` bắt `sqlite3.IntegrityError` thành "đã tồn tại" (`server/database/user/user_add.py:75–79`). Từ đó suy ra DB có ràng buộc unique cho username/email, nhưng **chưa đọc DDL** để xác nhận.
  - Crash sau commit insert, trước `account_created=True` (`user_register_process.py:127–130`): retry tạo registration mới và nhận lỗi "đã tồn tại" cho chính tài khoản vừa tạo. Hậu quả là **outcome không rõ/UX**, không tạo tài khoản trùng. Đồng ý F05.
  - Khi `verified=True`, `confirm_otp` trả thành công với bất kỳ mã hợp lệ cú pháp nào (`otp/user_otp_process.py:132–133`). Nhưng `finish_registration` chỉ trả cached outcome hoặc retry insert cùng `user_data`, không cấp quyền mới. Đồng ý với nhận định của Codex rằng đây là "cached semantic success", không phải tái sử dụng quyền.

### Phản biện F05

- **Login có thể là no-ledger an toàn.** Thứ tự R5 cho login: claim → verify mật khẩu → `create_session` commit (`user_session.py:23–32`) → CAS → Seal.
  - Crash sau `create_session` chỉ để lại token mồ côi chưa ai nhận. Token này là bí mật không rời server và tự hết hạn. Retry bằng attempt mới cấp token mới.
  - Hệ quả chỉ là tài nguyên (số session), không phải bảo mật. Vì vậy "bootstrap no-ledger" **chấp nhận được với login**, với điều kiện có quota session/account. **Bác bỏ** nếu F05 ngụ ý login cần operation ledger.
- **Nhưng D:207 vẫn bắt bootstrap thắng attempt claim + CAS bền.** Như vậy mỗi login ẩn danh, kể cả sai mật khẩu nếu claim xảy ra trước verify, là một hoặc hai commit fsync (sau C01: WAL+FULL). Flood bootstrap biến thành áp lực fsync lên **cùng file SQLite** với protected lane. Reserved workers (D:409–410) không giữ chỗ cho write lock/fsync. Đây là bổ sung cho F10. Xem C06 phần DoS.
- **Recovery không được là no-ledger.** Đồng ý: consume recovery code và chuyển credential phải cùng transaction bền (D:399–400 đã yêu cầu cho sensitive confirmation).

### Counterexample mới cho F06/I04: migration "first enrollment race"

- **Tiền đề:** D:94 cho first enrollment chỉ cần "authenticated session + server challenge + PoP". Mọi tài khoản hiện có **chưa có credential** lúc rollout.
- **Trace:**
  1. Kẻ tấn công có mật khẩu bị lộ của tài khoản U (U chưa enroll).
  2. Kẻ đó login bootstrap và enroll khóa của mình như "first installation".
  3. U enroll sau thì bị xếp là "additional/replace". Theo D:95–100, U cần credential cũ, mà đó là khóa của kẻ tấn công, hoặc cần recovery mạnh.
  4. Nếu U chưa có recovery code thì không được cấp machine write (D:100), trong khi kẻ tấn công **đã có** quyền machine write qua credential đầu tiên.
- **Kết luận:** "first-install" vừa là đường né (F06 đã nêu) vừa là đường chiếm trước trên các tài khoản cũ. Mật khẩu là yếu tố duy nhất cho credential đầu tiên.
- **Hướng cần user chốt:**
  - Credential đầu tiên của tài khoản có sẵn cần thêm yếu tố/kênh nào (email confirmation + thông báo + trì hoãn, xác nhận của owner/admin)?
  - Thông báo cho kênh đã biết có bắt buộc không?
  - Có cho nhiều installation song song không, và credential đầu tiên có quyền thu hồi credential sau không?
- Tôi **không** đề xuất mức AAL; S07 tôi chưa tự đọc.

---

## C04 — ledger máy / epoch / frontier / rollback (F07, F08, I05)

**Verdict: Đồng ý F07.** **Đồng ý một phần F08:** phần lớn counterexample HANDOFF liệt kê R5 đã tự xử lý hoặc tự thừa nhận. Có một mâu thuẫn thật ở "authority xác nhận epoch mỗi boot".

### Đối chiếu từng counterexample của HANDOFF với R5

| Counterexample | R5 xử lý ở đâu | Kết luận |
|---|---|---|
| Chưa peer nào nhận witness commit cuối | D:537–540 thừa nhận | Giới hạn đã biết, không phải phát hiện mới |
| Peers + server snapshot cùng lùi | D:538–540, D:349–351 | Đã biết; dựa vào recovery_epoch và vận hành |
| seq lớn giả / không MAC | D:513–515, N2 | R5 xử lý: chỉ reject packet |
| Response tới sai thứ tự | D:551–553, N2o | R5 xử lý |
| Audit reply seq thấp / cùng seq khác head | D:531–532 | R5 xử lý, chỉ quarantine máy đó |
| seq cao hơn nhưng không có extension | D:532–534 | R5 chặn redelivery; **format extension proof chưa freeze** (D:525 tự nhận) |
| Challenge cũ | D:529–531 (một outstanding, deadline, reused không chứng minh) | R5 xử lý |
| Rotate/reflash máy | D:312–316, D:352–353, N3 | Xử lý về nguyên tắc; **danh tính vật lý qua reflash chưa có cơ chế** (đồng ý F08) |
| Claim bền nhưng tác động vật lý không transactional | D:382–385 | Đã thừa nhận; không hứa exactly-once |
| **Authority confirmation replay** | D:347–348 chỉ ghi "current epoch confirmation từ nguồn ngoài rollback domain" | **Gap thật**, xem dưới |

### Phát hiện: mâu thuẫn giữa "xác nhận epoch mỗi boot" và "authority offline"

- D:347–348 yêu cầu mỗi boot phải quarantine cho tới khi có current epoch confirmation từ ngoài rollback domain, và không tin artifact trên disk.
- Một xác nhận "epoch E là hiện hành" mà **không gắn nonce/boot** vẫn đúng mãi tới khi epoch đổi.
- **Trace:** snapshot disk cũ chứa DB cũ và xác nhận E. Restore bị thực hiện ngoài quy trình (không đổi epoch). Boot thấy xác nhận E còn đúng nên mở admission trên DB đã rollback.
  - D:349–351 nói loại restore này "không được hỗ trợ", và D:342 nói boot không có artifact hiện hành thì không mở.
  - Nhưng muốn phân biệt "hiện hành" với "cũ còn chữ ký hợp lệ" thì cần **freshness theo challenge**, tức một authority **online** mỗi boot.
- **Mâu thuẫn:** R5 chọn root offline (D:68, D:75–77) và không thêm runtime mới (D:12). Không có thành phần nào được chỉ định để trả lời challenge mỗi boot.
- Các lựa chọn, cần user chốt:
  - (a) operator xác nhận thủ công mỗi lần boot server (đắt về availability);
  - (b) dịch vụ/khóa xác nhận online nằm ngoài snapshot domain (thêm thành phần, trái D:12/D:77 nếu không được duyệt);
  - (c) thu hẹp bảo đảm: chấp nhận artifact có hạn ngắn, kèm rủi ro restore nằm trong hạn đó.
- Codex I05 đã chạm "nonce-bound confirmation", nhưng chưa chỉ ra xung đột với lựa chọn root offline.

### Hiện trạng code liên quan (đã được D:308–309 thừa nhận ở mức thiết kế, nay có trace cụ thể)

- `server/lib/machine/machine_transport.py:25` dùng `DEM_LENH = count(1)` trong RAM. `deliver()` (`:91–100`) chỉ khớp `(lenh_id, machine_id)`.
- **Trace:**
  1. Lệnh id=5 đã được máy lấy.
  2. Server restart, counter quay về 1.
  3. Lệnh mới thứ 5 cho cùng máy cũng có id=5.
  4. Máy gửi kết quả muộn cho lệnh cũ, và kết quả này được ghép vào lệnh mới. App nhận sai outcome (ví dụ báo thành công cho thay đổi menu khác).
- **Chưa đủ bằng chứng** về phía máy: tôi chưa đọc code máy để biết nó có loại id cũ hoặc có giới hạn thời gian không. Đây là bằng chứng cụ thể cho vì sao R5 đòi command_id CSPRNG 16 byte (D:289) và ledger bền.

**Phép kiểm cần thêm:**
- Boot từ snapshot có xác nhận epoch cũ còn hạn → không được mở admission.
- Kết quả muộn qua restart server không được ghép vào lệnh mới.

---

## C05 — revoke transaction và queue dispatch (F09, I06)

**Verdict: Đồng ý F09.** Bổ sung chi tiết ranh giới transaction, vì hiện trạng còn yếu hơn F09 mô tả.

| Bước | Code | Connection/transaction | Quan sát |
|---|---|---|---|
| Đọc phiên | `server/lib/security/user_session.py:35–45` | connection riêng, chỉ SELECT | Autocommit read |
| Kiểm quản lý máy | `server/lib/machine/machine_access.py:18`, `server/database/machine/machine_read.py:58–65` | connection riêng thứ hai | Không cùng snapshot với bước đọc phiên |
| Kiểm owner/manager | `machine_access.py:20`, `machine_read.py:49–55` | connection riêng thứ ba | Ba lần đọc ở ba thời điểm khác nhau |
| Enqueue | `server/service/dashboard_sync/menu_sync/machine_menu_update.py:72` → `machine_transport.py:45–58` | RAM, không DB | Không có claim bền |
| Máy lấy lệnh | `machine_transport.py:83–88` | RAM | **Không kiểm lại quyền/phiên lúc take** |
| Staff revoke | `server/service/machine_share/machine_staff_revoke.py:15–26` | check_login ở connection riêng; `is_owner` rồi DELETE trong `get_connection()` | SELECT chạy trước DML. Với chế độ transaction legacy của sqlite3 (mặc định cũ), BEGIN ngầm chỉ mở trước DML. **Chưa xác minh** default thực trên Python 3.14.4 vì lệnh kiểm bị chặn |

**Trace hai thứ tự (chưa chạy):**
- **Thứ tự 1 (revoke trước):**
  1. T1 `check_access` OK.
  2. T2 owner revoke manager và COMMIT.
  3. T1 enqueue.
  4. Máy take và thực thi.
  5. Kết quả: manager đã bị thu hồi vẫn sửa được menu. Vi phạm D:392–393 "revoke trước claim thì reject".
- **Thứ tự 2 (revoke sau take):** đã dispatch rồi mới revoke. R5 D:396–397 chấp nhận khả năng máy vẫn thực thi. Không vi phạm.

**Kết luận:**
- Đây là gap triển khai của thiết kế chưa triển khai, không phải lỗi R5. Đồng ý cách phân loại của F09.
- Chi tiết mới so với F09:
  - Hiện trạng **không dùng chung một connection ngay cả cho các lần đọc**.
  - `take()` không có điểm kiểm quyền.
  - Staff revoke không dùng `BEGIN IMMEDIATE`. AGENTS.md chỉ bắt buộc điều đó cho luồng "gỡ máy", nên đây **không vi phạm** quy ước hiện tại; nó chỉ chưa đạt D:398 khi R5 được triển khai.
- Hướng làm đúng R5 (không cần kiến trúc mới):
  - `BEGIN IMMEDIATE` → đọc phiên + quyền → claim → commit → enqueue.
  - Lúc take: kiểm lại quyền/deadline/ticket và mark dispatched trong cùng transaction (D:305).
  - SQL quyền đặt tại feature hoặc ở helper `database/machine` nhận `conn`; `machine_read.py` đã hỗ trợ tham số `conn`.

---

## C06 — thư viện HPKE và giới hạn DoS (F10, F11, I07, I09); làm được một phần

### Thư viện. Verdict: Đồng ý F11/I07, thêm chứng cứ Turnkey không đạt gate R5 ở dạng hiện có

- **Turnkey `hpke.dart`, nhánh main** ([source](https://github.com/tkhq/dart-sdk/blob/main/packages/crypto/lib/src/hpke.dart), đọc qua WebFetch, **không pin release 0.2.0**):
  - Hàm public: `hpkeEncrypt({plainTextBuf, targetKeyBuf})`, `hpkeAuthEncrypt(...)`, `hpkeDecrypt({ciphertextBuf, encappedKeyBuf, receiverPriv})` cùng helper HKDF.
  - AAD dựng nội bộ từ `buildAdditionalAssociatedData(senderPubBuf, targetKeyBuf)`. info là hằng số label/suite nội bộ.
  - **Không có hàm Export** trong file.
  - Hệ quả với R5: không truyền được `info = Tuple(..., M)` và `aad = Tuple(..., M)` (D:146–147), cũng không lấy được Export cho response (D:193–194). Ở dạng API hiện có, Turnkey **không đáp ứng** profile R5. Đây là kết luận về API bề mặt.
  - Tôi **chưa kiểm** key schedule có khớp RFC 9180 từng byte không, và chưa chạy vector.
  - Không suy ra "Dart không có HPKE"; chỉ loại candidate này khỏi đường dùng trực tiếp.
- **PyHPKE** ([repo](https://github.com/dajiaji/pyhpke)):
  - README có `create_sender_context` / `create_recipient_context`. Hỗ trợ DHKEM P-256/384/521/X25519/X448, HKDF-SHA256/384/512, AES-GCM, ChaCha20Poly1305 và Export-only.
  - Maintainer ghi đã qua official test vectors nhưng *"has not been formally audited"*. Đây là tuyên bố của maintainer, **không phải kiểm của lượt này**.
  - Source nằm ở `src/pyhpke/`. Hai URL file context tôi đoán đều 404, nên **chưa đọc concrete export/seq**. Còn mở như F11 nói.
- Chưa xác minh ngày phát hành chính xác của cả hai package. Không cài, không chạy code nguồn.

### DoS. Verdict: Đồng ý F10/I09, bổ sung một điểm định lượng hóa được sau

- D:207 bắt bootstrap ghi attempt claim + CAS bền. Kết hợp C01 (WAL+FULL), mỗi request bootstrap đã Open được sẽ tốn ≥1 fsync trên file SQLite chung với heartbeat/result/protected writes.
- Reserved workers (D:409–410) không giữ chỗ cho **write lock và băng thông fsync** của SQLite. Đường recovery/result vì thế có thể bị flood bootstrap hợp lệ cú pháp làm chậm.
- Có hai hướng, cần user/architect chọn:
  - token bucket bootstrap tính theo **số commit**, không chỉ số request;
  - tách file DB cho attempt bootstrap. Hướng này đổi kiến trúc lưu trữ, **cần duyệt**.
- Không đặt ngưỡng; phải đo trên thiết bị đích.
- Hiện trạng: limiter IP sau proxy gộp mọi client vào một bucket (xem C03). Đây đúng là rủi ro D:411–412 đã nêu.

---

## C07 — ánh xạ verdict cho mọi F/I của Codex

Nhóm: **R5** = giữ nguyên R5; **Gate** = làm cụ thể gate/sửa chữ; **User** = đổi hợp đồng/kiến trúc, cần người dùng chốt; **Env** = deployment không được hỗ trợ.

| ID | Verdict | Nhóm | Lý do ngắn / chỗ review |
|---|---|---|---|
| F01 / I01 | Đồng ý; tác động nặng hơn (nonce reuse response dưới A0) | Gate (sửa D:502) | C01 |
| F02 / I02 | Đồng ý một phần; bác "repair mở manifest cũ" nhờ sequence high-water D:72 | Gate + User (nguồn time của app) | C02 |
| F03 | Đồng ý; RFC §9.1.1 khuyên ký `(enc, ct)` cho KCI, R5 D:40–43 khớp | R5 | §9.1.1 đọc qua WebFetch; chưa formal |
| F04 | Đồng ý khác biệt OHTTP. Về "mơ hồ D:205 vs D:213": **đồng ý một phần**. D:205 nói nhánh không thắng không ciphertext *mới*, D:213 nói chỉ phát lại bytes đã có; hai câu không mâu thuẫn logic nhưng thiếu bảng state | Gate (I08) | Cần làm rõ: resend cached bytes sau revoke/expiry có được không. Tôi đề xuất **không**, xem Q4 |
| F05 / I03 | Đồng ý một phần; login no-ledger chấp nhận được, register/recovery thì không | Gate + User | C03 |
| F06 / I04 | Đồng ý; thêm counterexample migration first-enrollment | User | C03 |
| F07 | Đồng ý | R5 | Chưa tự đọc RIFL (S05) |
| F08 / I05 | Đồng ý một phần; phần lớn counterexample R5 đã thừa nhận; gap thật là xác nhận epoch mỗi boot vs root offline | User | C04 |
| F09 / I06 | Đồng ý; hiện trạng dùng ba connection cho đọc quyền và `take()` không kiểm quyền | Gate (triển khai đúng R5) | C05 |
| F10 / I09 | Đồng ý; thêm áp lực fsync của bootstrap | Gate + User nếu tách DB | C06 |
| F11 / I07 | Đồng ý; Turnkey API không có Export/info/AAD tùy biến | Gate + User (chọn lib/FFI) | C06 |
| I08 | Đồng ý | Gate/User | Q4 |
| I10 | Đồng ý; lượt này cũng không tải được bản gốc (bị chặn quyền, không phải DNS) | R5 quy trình | §0 |
| I11 | Đồng ý giữ P2; **lưu ý**: response nonce ngẫu nhiên kiểu OHTTP **giảm** hậu quả C01 (Seal lại không còn trùng nonce) nhưng không thay ledger | User | Đáng cân nhắc nâng ưu tiên nếu không chứng minh được durability trên media đích |
| I12 | Chưa đủ bằng chứng để đánh giá lợi ích; đồng ý ràng buộc "không consume nonce từ input chưa auth" | P2 | — |

**Env (deployment không hỗ trợ), nhắc lại từ R5, không phải phát hiện mới:**
- live VM/memory restore (D:349–351);
- đồng loạt restore mọi peer (D:537–540);
- media không honor flush (D:504–505);
- SQLite trên network FS (S11 §1).

## Nhiệm vụ đã làm / còn lại

**Đã làm:**
- Đọc HANDOFF, SCHEDULE, status và mọi đầu ra Codex.
- Đọc design R5 đầy đủ (580 dòng).
- Đọc source code liên quan C03/C05, kèm `machine_transport.py`, `http_json.py`, `user_add.py`, `user_otp_generate.py`.
- Đọc S04/S11/S01/S06 qua WebFetch; đọc Turnkey `hpke.dart` và README PyHPKE.
- Viết verdict C01–C06 và ánh xạ C07.

**Còn lại (theo ưu tiên):**
1. Tải bản gốc S01/S04/S06/S11 vào `sources/` kèm SHA256 khi có phiên được cấp quyền mạng/shell.
2. Đọc S03 §8 (hậu quả nonce reuse GCM) để chính thức hóa mức tác động C01.
3. Đọc DDL bảng `users` để xác nhận unique (C03).
4. Đọc concrete `src/pyhpke` context (export, seq) tại tag v0.6.5.
5. Tìm nguồn chính thức Android về nguồn/độ tin system time (C02).
6. Đọc code máy (phía Pi) để chốt trace ghép kết quả qua restart (C04).
7. Xác minh default transaction/synchronous của sqlite3 trên Python 3.14.4 và SQLite runtime bằng DB `:memory:` (bị chặn lượt này).
8. Tự đọc S05/S07/S10 thay vì dựa ghi chú Codex.
