# Review R3 — thiết kế bảo vệ gói tin (`design.md` R3)

**Phạm vi:** Tôi chỉ đọc `operator/design-feedback-r2.md` và `packet-security/design.md` R3. Không sửa file, không chạy gì. Mọi trace dưới đây được suy từ đặc tả; **chưa có test nào chạy**. Bảng §11 chỉ là đặc tả test, không phải bằng chứng.

## Verdict

**Chưa đạt ở cấp kiến trúc, nhưng chỉ cách hai sửa nhỏ về khái niệm.** R3 đóng thực chất được F2, F4 (với restore theo quy trình), F6, F7, F8, F10, F11. Cơ chế quyền Seal theo CID và claim bền là đúng hướng.

Còn **2 lỗi chặn về khái niệm**. Cả hai đều là mâu thuẫn nội tại của đặc tả, không phải chỗ thiếu số đo:

- **C1:** Phạm vi khóa khi đồng hồ bất thường chỉ phủ thao tác ghi, nhưng bất biến Seal lại cần phủ mọi route có Seal.
- **C2:** Đường đồng bộ thời gian ở bootstrap (dòng 224–226) không dựng được mà không phá F1 hoặc phá giả định của F5.

Sửa C1 và C2 xong thì có thể ghi "đạt cấp kiến trúc, production gate chưa đạt". Không được ghi "an toàn" hay "tối ưu".

## Lỗi chặn về khái niệm

### C1 — Bất biến Seal phụ thuộc retention, retention phụ thuộc đồng hồ, nhưng khóa đồng hồ chỉ áp cho thao tác ghi

**Vị trí:** design.md:186–189 và 238 (retention theo `expires_at`), 219–222 ("khóa writes"), 247 (read và heartbeat cũng phải claim).

**Trace:**
1. Server restart trong lúc đồng hồ bị đặt sai **tiến lên** +1 ngày (NTP sai, RTC hỏng). High-water `max_now_seen` chỉ phát hiện đồng hồ lùi. Còn so wall-clock với monotonic (dòng 221–222) chỉ có tác dụng trong một process, nên không phát hiện được cú nhảy xảy ra qua restart.
2. Cleanup chạy với `now` sai và xóa mọi claim/response record có `expires_at + σ + margin < now`.
3. Đồng hồ được sửa lùi về đúng. `now < max_now_seen − σ` nên writes bị khóa. Nhưng **read, heartbeat, poll và bootstrap vẫn chạy**.
4. A1 phát lại một read packet R đã chụp trước đó. `expires_at` của R vẫn còn hạn theo giờ thật, record đã bị xóa, nên R thắng claim lần nữa. Server Seal response S₂ dưới **cùng (k, n)** đã dùng cho S₁.
5. A1 thu được S₁ ⊕ S₂ và khóa GHASH H. Hai response cho cùng một read thường gần giống nhau, nên lộ được nội dung đáng kể.

**Sửa tối thiểu:**
- (a) Mọi bất thường đồng hồ khóa **mọi route có Seal**, không chỉ writes.
- (b) Cấm cleanup cho tới khi thời gian của process đã được đối chiếu với một nguồn tin cậy sau boot. Dòng 222 hiện chỉ ngầm ý điều này, chưa ràng buộc.
- (c) Ghi rõ nghĩa vụ: SQLite cho bảng claim/seal phải chạy `synchronous=FULL`. Ở WAL với `synchronous=NORMAL`, mất điện có thể làm mất commit cuối, kể cả mất mốc `SEAL_STARTED`, và mở lại đúng F1. Trên Pi/SD, nghĩa vụ này cũng áp cho ledger của máy (F2).

**Test bác bỏ (thêm vào §11 F1):**
- Restart với đồng hồ +1 ngày, rồi sửa lùi, rồi phát lại một read đã chụp: số lần Seal cho CID đó phải ≤ 1.
- Mất điện ngay sau CAS `SEAL_STARTED`: mốc này phải còn sau khi khởi động lại.

### C2 — Không dựng được đường đồng bộ thời gian

**Vị trí:** design.md:224–226, 216 và 80–82.

**Trace A (không dùng được):** Đồng hồ client lệch 1 ngày, nên `issued_at` nằm ngoài cửa sổ [now − Δ_past, now + Δ_future]. Request time-sync cũng bị từ chối ở bước kiểm freshness (dòng 228). Kết quả: không có đường recovery.

**Trace B (miễn freshness cho route time-sync):** Retention của claim neo vào `expires_at` do client tự khai, nên bound H ở §9.4 không còn đúng. Sau khi record bị xóa, phát lại request time-sync sẽ bị Seal lần hai, tức F1 quay lại.

**Trace C (đúng kịch bản F5):** A1 cộng với server HPKE key đã lộ, nghĩa là chính kịch bản mà F5 tồn tại để giới hạn. Response time-sync được Seal bằng khóa Export từ context mà A1 tự decap được. A1 giả mạo thời gian, kéo lùi đồng hồ client, và kéo dài **vô hạn** cửa sổ đóng băng manifest. Câu "trong giả định clock bounds được giữ" (dòng 81) bị chính nguồn thời gian của thiết kế phá.

**Sửa tối thiểu, chọn một:**
- (i) **Bỏ hẳn route time-sync.** Client dùng đồng hồ hệ điều hành. Khi lệch, server trả transport error tối giản, không mã hóa, kiểu "clock skew". A1 giả mạo được lỗi này nhưng chỉ gây DoS, mà DoS vốn đã nằm trong năng lực của A1. Freeze bound giữ nguyên với giả định đồng hồ OS không bị A1 điều khiển.
- (ii) Nếu bắt buộc giữ time-sync: dùng challenge do server cấp, có MAC và tuổi tính theo giờ server. Retention tính theo `server_time + R`. Response **ký bằng khóa thời gian độc lập** với HPKE key, khóa này được liệt kê trong manifest root.

Tôi khuyến nghị (i) vì đơn giản hơn.

## Findings OPEN không chặn

| ID | Mức | Vị trí | Vấn đề | Sửa tối thiểu |
|---|---|---|---|---|
| N1 | Nên sửa | 68–70, 135, 311 | Manifest chưa có trường `recovery_epoch`, nên chưa rõ client nhận epoch mới sau restore qua kênh nào. Bootstrap phải khớp epoch "được cấp tin cậy", nhưng sau restore client chỉ có epoch cũ, dẫn tới vòng lặp | Thêm `recovery_epoch` vào canonical manifest. Ghi rõ mỗi lần restore cần một nghi thức ký offline: đây là chi phí availability của recovery |
| N2 | Nên sửa | 308–313, 19 | Rollback không theo quy trình (revert snapshot VM/disk, khôi phục image SD của server) cũng làm lùi luôn recovery artifact, vì dòng 308 chỉ yêu cầu "ngoài backup volume". Trace: o done, revert, client có kết quả `unknown` retry cùng ticket, epoch vẫn khớp, o chạy lần hai. A3 ("restore state") đã bị loại khỏi mô hình, nhưng revert do vận hành sơ ý không phải tấn công | Bộ phát hiện rollback rẻ: response kèm `server_ledger_seq` đơn điệu; client/máy lưu giá trị cao nhất đã thấy và gửi lại trong M. Server thấy giá trị thấp hơn của mình thì khóa writes và báo động. Nếu không làm, ghi rõ đây là rủi ro còn lại |
| N3 | Nên sửa | 282–287, 317–318 | Máy được flash lại image SD có sẵn credential: ledger rỗng, generation không đổi, nên chặn redelivery xuyên generation (dòng 285) không có tác dụng. Dòng 318 yêu cầu quarantine nhưng không có cơ chế **phát hiện** | Máy gửi `(ledger_seq, head_hash)` trong request đã ký; server phát hiện lùi thì quarantine. Recovery chỉ được duyệt redelivery khi chuỗi ledger liên tục |
| N4 | Gợi ý | 251, 269 | `CLOCK_MONOTONIC` trên Linux không tính thời gian suspend. Nếu máy có thể suspend, deadline cục bộ bị kéo dài | Dùng `CLOCK_BOOTTIME`, hoặc ghi rõ giả định "không suspend" |
| N5 | Gợi ý | 127, 230 | Ở bootstrap, A1 thấy `attempt_id` ở dạng rõ và chiếm trước được claim bằng `enc` của mình. Hậu quả chỉ là DoS, A1 vốn đã chặn được traffic, nên không thêm năng lực mới | Ghi chú là rủi ro còn lại. Không cần đổi thiết kế |

## Kiểm các vùng được yêu cầu

**Quyền Seal qua restart và bản trùng.** CID = H(M, enc) kết hợp claim UNIQUE và CAS `SEAL_STARTED` bền là đúng. Nhánh không thắng claim không tạo ciphertext (dòng 192–193). Crash giữa CAS và Seal thì không Seal lại (dòng 198). Cách đặt bất biến theo (M, enc) như phản hồi 1 của Codex là hợp lệ: M nằm trong `info`. Tôi rút lại cách viết theo `(server_kid, enc)` ở R2. Kiểm epoch trước decap chặn được phát lại sau restore theo quy trình. Phần còn hở là C1 (đồng hồ) và nghĩa vụ fsync.

**Bootstrap không ký.** Đã chặn đổi mode (dòng 148–151). Bootstrap phải thắng claim và CAS trước khi phát token (dòng 194). Recovery code là một lần, lưu hash, có rate limit (dòng 96). Vấn đề còn lại là C2 và N1.

**Ticket và epoch.** Server tự cấp `operation_id`, ticket có MAC theo epoch, và đổi khóa MAC khi restore. Trace F4 của tôi ở R2 bị chặn với restore theo quy trình. Phản biện 3 của Codex đúng: `op_created_at` do client ký không chống được A2 tự sửa thời gian. Phần còn hở là N2 (rollback không theo quy trình).

**Generation và deadline ở ledger máy.** Khóa `(stable_physical_machine_id, command_id)` đóng được trace của F2. Bất đẳng thức dispatch `now_server + D_poll_local_max + margin < intent_deadline` đúng nếu tốc độ trôi đồng hồ máy bị chặn bởi margin. Lý do: máy gửi poll trước khi server dispatch, và máy claim executor trước `t_send + D`. Còn hở N3 và N4.

## Bảng đóng F1–F12

| ID | Trạng thái | Ghi chú |
|---|---|---|
| F1 | **Mở (C1)** | Cơ chế đúng; phạm vi khóa đồng hồ và cleanup sai; còn nghĩa vụ fsync |
| F2 | Đóng (thiết kế) | Phát hiện ledger máy bị lùi → N3 |
| F3 | Đóng (thiết kế, có giả định) | Giả định: trôi tốc độ đồng hồ và suspend (N4). D_poll và margin chưa có số |
| F4 | Đóng với restore theo quy trình | Rollback ngoài quy trình → N2 |
| F5 | **Mở (C2, trace C)** | Freeze bound bị phá bởi chính nguồn thời gian của thiết kế |
| F6 | Đóng | |
| F7 | Đóng (quyết định) | Không có thư viện đạt gate thì dừng rollout, không tự ghép |
| F8 | Đóng (đặc tả) | Vector chưa có, đó là gate |
| F9 | Mở một phần | Lùi: đã đóng. Tiến qua restart: gộp vào C1 |
| F10 | Đóng, có rủi ro còn lại được chấp nhận | DoS bootstrap toàn cục được ghi rõ; provenance phụ thuộc topology Caddy |
| F11 | Đóng (đặc tả) | Ngân sách chưa đo |
| F12 | Đóng (từ chối có lý do) | Durable SQLite là một lựa chọn, không phải tối ưu; Codex đúng rằng watermark trong RAM cần chứng minh thêm về future-skew |

## Lập luận

- Các công thức ở §9 không đổi so với R2 và vẫn đúng theo giả định. Bound H và b + ⌈rH⌉ **ngầm** giả định đồng hồ server đáng tin khi cleanup. C1 chính là chỗ giả định này bị vi phạm. Cần ghi tường minh trong §9.4.
- Câu "Response AEAD đủ cho A0/A1" (dòng 44) chỉ đúng khi Seal ≤ 1 cho mỗi CID. Nên viết nó thành hệ quả có điều kiện của bất biến đó.
- Freeze bound ở dòng 80–82 là mệnh đề có điều kiện, hợp lệ về hình thức. Nhưng thiết kế đang tự cung cấp nguồn thời gian vi phạm chính điều kiện đó (C2).

## Ba lớp phân biệt sau khi sửa C1 và C2

1. **Đạt cấp kiến trúc:** các bất biến có cơ chế, có trace bác bỏ trong §11, và không còn mâu thuẫn nội tại.
2. **Production gate chưa đạt (§10):**
   - thư viện HPKE có Export trên Dart, hoặc FFI binding;
   - vector chính thức và vector byte-exact Dart/Python;
   - khóa ký trên Keystore;
   - adapter GET;
   - lưu queue bền;
   - tham số Δ, L_max, σ, D_poll, margin, cadence của manifest;
   - topology Caddy;
   - harness lỗi kèm instrumentation đếm Seal, claim và executor;
   - fsync trên server và trên Pi.
3. **Không chứng minh được và không được tuyên bố:**
   - tối ưu toàn cục, vì vector Pareto chưa có trọng số hay số đo;
   - an toàn của toàn bộ composition, vì chưa có chứng minh hình thức hay phân tích CryptoVerif/Tamarin;
   - exactly-once hoặc at-most-once vật lý.

   Bảo đảm hẹp có thể giữ là: không tự gọi business executor lần hai cho cùng một durable claim, với điều kiện storage bền đúng nghĩa.

## Gate cho R4

1. Sửa C1 (a)(b)(c) và thêm hai test vào §11.
2. Sửa C2: chọn (i) hoặc (ii). Nếu chọn (ii) thì đặc tả khóa thời gian.
3. N1: thêm `recovery_epoch` vào manifest. N2/N3: hoặc thêm bộ phát hiện rollback, hoặc ghi rõ là rủi ro còn lại.

Triển khai vẫn dừng; đây vẫn là vòng thiết kế.
