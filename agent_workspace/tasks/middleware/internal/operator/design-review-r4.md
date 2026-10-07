# Review R4 (vòng cuối) — thiết kế bảo vệ gói tin

**Phạm vi:** Tôi chỉ đọc `design.md` R4, `operator/design-feedback-r3.md` và `operator/security-obligations.md`. Không sửa file, không chạy gì. Mọi trace dưới đây được suy từ đặc tả, chưa chạy thử.

## Verdict

**Còn 1 lỗi chặn về khái niệm, do chính R4 đưa vào.** Cơ chế phát hiện rollback dùng `peer_seen_server_seq` lấy giá trị **do peer tự khai**. Một tài khoản hợp lệ bất kỳ (A2) có thể dùng nó để đưa toàn bộ server vào quarantine. Sửa nhỏ, nêu ở R4-B1.

Sau khi sửa R4-B1 và hai lỗi toàn vẹn đặc tả (R4-S1, R4-S2), câu kết luận đúng mức sẽ là: *"không tìm thấy blocker kiến trúc mới trong phạm vi review; production gates chưa đạt"*.

## Lỗi chặn về khái niệm

### R4-B1 — Frontier do peer tự khai cho phép A2 khóa toàn hệ thống

**Vị trí:** design.md:491–493 và 508–511.

**Trace:**
1. A2 có credential hợp lệ. A2 tự dựng M với `peer_seen_server_seq = 2^64 − 1`, rồi ký đúng bằng khóa của chính mình. M do client dựng, nên chữ ký chỉ chứng minh A2 đã gửi giá trị đó, **không** chứng minh server từng cấp giá trị đó.
2. Server so sánh: seq của mình nhỏ hơn high-water mà peer khai. Theo dòng 493, server vào quarantine và ngừng mọi Seal và execute mới.
3. Quarantine được thiết kế để chỉ mở bằng recovery hoặc đối soát. Kết quả là một tài khoản thường gây được DoS **bền và toàn hệ thống** chỉ bằng một request. A0/A1 vốn chặn được traffic, nhưng phải duy trì việc chặn liên tục; ở đây A2 không cần duy trì gì, và hệ thống ở lại trạng thái khóa cho tới khi có thao tác vận hành.

Nếu server chọn bỏ qua frontier cao bất thường để tránh trường hợp trên, thì bộ phát hiện mất tác dụng.

**Sửa tối thiểu:** Frontier phải là **bằng chứng do server cấp**.
- Response inner mang `witness = MAC_kw(audience, recovery_epoch, server_seq)`.
- Peer gửi lại nguyên `(server_seq, witness)` cao nhất mà nó đã nhận.
- Server chỉ xét frontier khi MAC hợp lệ.
- `kw` là khóa có mục đích riêng.
  - Nếu snapshot khôi phục cả `kw`, MAC vẫn verify được và witness vẫn mang seq mới, nên vẫn phát hiện được rollback.
  - Nếu recovery đổi `kw` cùng epoch, witness cũ hết hiệu lực; khi đó epoch mới đã đảm nhận việc chặn.
- Frontier có MAC sai, hoặc thuộc epoch khác, thì chỉ reject request đó, **không** quarantine toàn cục.

**Test bác bỏ:** A2 gửi `peer_seen_server_seq` lớn kèm witness giả hoặc không có witness. Server không được quarantine. Ngược lại, khi có rollback thật và một peer giữ witness hợp lệ với seq cao hơn, server phải quarantine.

Với frontier của máy (dòng 494–496), phạm vi ảnh hưởng chỉ là chính máy đó: người có credential của máy chỉ tự khóa được máy của mình. Có thể chấp nhận, nhưng nên ghi rõ đây là rủi ro còn lại.

## Toàn vẹn đặc tả (nên sửa trước khi viết vector)

- **R4-S1:** Bảng M (dòng 122–137) được ghi là "đúng thứ tự, số field cố định", nhưng **không có** dòng `peer_seen_server_seq`. Trường này chỉ xuất hiện trong văn xuôi ở dòng 508. Thêm trường vào M mà không tăng `version` thì vector R3 và R4 trùng version nhưng khác byte. Sửa: thêm một dòng vào bảng, ghi rõ `version` của profile R4, và cập nhật mô tả M ở dòng 186–187.
- **R4-S2:** Dòng 494 đặt `machine_ledger_seq` và `ledger_head_hash` trong "signed inner request", còn dòng 509 ghi là "body request máy". Nhưng inner frame ở dòng 155 chỉ có `LP(auth)||LP(business)||LP(ticket)`, và kiểu được ghi là `uint64` trong khi business là JSON. Sửa: định nghĩa segment thứ tư `LP(machine_frontier)` gồm `uint64_be || 32 byte`, hoặc đưa hai giá trị vào M của route máy. Chọn một và ghi trong bảng.
- **R4-S3 (nhỏ):** Còn câu cũ sau C1. Dòng 478 (test F9) vẫn ghi "Writes fail closed", và dòng 402 vẫn ghi "protected writes fail closed" cho trường hợp store đầy. Cả hai phải đổi thành **mọi route có Seal**, vì read cũng cần claim.
- **R4-S4:** Dòng 512 ghi "responses không regress seq". Khi có request đồng thời, response có thể về sai thứ tự. Nếu client coi seq giảm là dấu hiệu rollback thì sẽ báo động giả. Sửa: client chỉ giữ giá trị lớn nhất, seq giảm ở phía client không phải là báo động; việc phát hiện chỉ diễn ra ở server, theo R4-B1.

## Rà các vùng được yêu cầu

**Đồng hồ, cleanup và Seal.** Đặc tả đã nhất quán ở các điểm:
- mọi route có Seal bị khóa khi đồng hồ không đáng tin (dòng 221);
- không cleanup khi `CLOCK_UNTRUSTED` (dòng 222);
- mỗi lần boot mặc định coi đồng hồ là không đáng tin cho tới khi xác minh qua NTS hoặc provisioning (dòng 226–228);
- cleanup ghi high-water trong cùng transaction (dòng 230).

Trace C1a ở R3 bị chặn **với giả định** dịch vụ thời gian có xác thực thật sự độc lập.

**Không còn miễn trừ time-sync.** Đã bỏ route time-sync (dòng 232). Lỗi clock-skew chỉ là chẩn đoán, không đáng tin (dòng 234–236). Bootstrap không được miễn freshness. Cả ba trace của C2 đều bị chặn.

Còn một **rủi ro thật** cần ghi rõ:
- Đồng hồ OS của Android thường lấy qua SNTP/NITZ không xác thực. A0 có thể dịch đồng hồ điện thoại, và app không có API để biết đồng hồ có đáng tin hay không.
- Vì vậy điều kiện ở dòng 233 và 237 ("OS clock có nguồn tin cậy") nhiều khả năng **không kiểm chứng được** trên app.

Đề xuất rẻ và không phụ thuộc wall-clock: tính `max_manifest_validity` theo thời gian trôi kể từ lúc nhận manifest, đo bằng `elapsedRealtime`. A0 không chỉnh được bộ đếm này. Sau reboot, coi như chưa biết và bắt buộc tải lại manifest. Nếu không làm, ghi freshness bound của manifest là có điều kiện "A0 không điều khiển được đồng hồ thiết bị". Đây là gate triển khai, không phải lỗi khái niệm.

**`synchronous=FULL` và phần cứng.** Dòng 486–490 ghi đúng mức: FULL là cần nhưng không đủ; media phải honor flush và phải qua fault gate. Test C1b cũng đã ghi rõ "nếu không chứng minh flush thì không mở production". Đóng ở mức thiết kế, còn là gate trên phần cứng thật, nhất là SD card của Pi.

**`recovery_epoch` trong manifest.** Đã có ở dòng 70 và 501–504. Proxy giữ manifest cũ thì hệ thống bị khóa (test N1). Không dùng bootstrap cũ để gắn lại epoch. Đóng.

**Rollback detector và các giả định còn lại.** Dòng 497–500 nói đúng giới hạn:
- detector chỉ có tác dụng khi còn một peer giữ frontier mới;
- không có báo động không chứng minh lịch sử liên tục;
- resume từ live snapshot không được hỗ trợ.

Lập luận pigeonhole trong `security-obligations.md` (dòng 43–51) hợp lệ để giải thích vì sao cần ticket lifetime cộng với fail closed, và không bị diễn đạt quá mức.

Lập luận "Seal tối đa một lần" trong `security-obligations.md` (dòng 15–24) hợp lệ **có điều kiện**. Giả định "record không bị xóa khi packet còn hợp lệ" giờ được bảo vệ bởi cơ chế khóa cleanup khi đồng hồ không đáng tin cộng durability. Hai giả định này cần được ghi kèm ngay trong sketch.

## Bảng đóng

| ID | Trạng thái | Ghi chú |
|---|---|---|
| C1 | **Đóng (thiết kế)** | Điều kiện: dịch vụ thời gian có xác thực trên server, FULL cộng flush thật (gate). Còn câu cũ ở dòng 402/478 (R4-S3) |
| C2 | **Đóng (thiết kế)** | Rủi ro còn lại: đồng hồ Android không xác thực; đề xuất dùng `elapsedRealtime` |
| N1 | **Đóng** | |
| N2 | **Mở (R4-B1)** | Detector hợp lệ về ý tưởng, nhưng frontier phải là witness có MAC |
| N3 | Đóng (thiết kế, có điều kiện) | Chỉ ảnh hưởng chính máy đó; wire format thuộc R4-S2 |
| N4 | **Đóng** | `CLOCK_BOOTTIME`, hoặc invalidate khi suspend; capability là gate |
| N5 | **Đóng (rủi ro còn lại được ghi)** | Dòng 505–506 |

## Hai lớp cần tách bạch

**Production gates chưa đạt (§10 và §12):**
- thư viện HPKE/Export trên Dart hoặc FFI binding, kèm vector chính thức và byte-exact;
- khóa ký trên Keystore;
- adapter GET;
- lưu queue bền;
- tham số Δ, L_max, σ, D_poll, margin, cadence manifest;
- NTS trên server; năng lực đồng hồ của app/máy;
- flush thật trên server và trên Pi;
- topology Caddy;
- miền rollback độc lập cho recovery artifact;
- harness lỗi có đếm Seal, claim và executor.

**Không chứng minh được và không được tuyên bố:**
- tối ưu, vì vector Pareto chưa có trọng số hay số đo;
- an toàn của toàn bộ composition, vì chưa có formal verification, và sketch không phải chứng minh;
- exactly-once hay at-most-once vật lý;
- không thể bị xâm phạm hoặc đã được chứng nhận bảo mật.

## Điều kiện để chốt vòng

1. Sửa R4-B1 (witness có MAC; frontier không hợp lệ chỉ reject request, không quarantine) và thêm test bác bỏ cho trường hợp A2 khai frontier giả.
2. Sửa R4-S1 và R4-S2: cập nhật bảng M, version, segment frontier của máy.
3. Sửa R4-S3 và R4-S4 (đổi câu cũ). Ghi rủi ro đồng hồ Android, hoặc dùng `elapsedRealtime`.

Nếu chỉ có các thay đổi này và không có thay đổi nào khác, thì không cần một vòng kiến trúc mới. Chỉ cần kiểm lại diff của các mục trên. Triển khai vẫn dừng cho tới khi lead mở.
