# Kiểm diff R5 (sau R4) — thiết kế bảo vệ gói tin

**Phạm vi:** Tôi chỉ đọc `operator/design-feedback-r4.md`, `packet-security/design.md` R5 (§4, §5, §6, §12 và bảng test) và `operator/security-obligations.md`. Không sửa file, không chạy gì. Mọi trace đều suy từ đặc tả, chưa chạy.

## Verdict

**Không tìm thấy blocker kiến trúc mới trong phạm vi review này. Các production gate vẫn chưa đạt.**

Kết luận này không có nghĩa thiết kế tối ưu, không thể bị xâm phạm hay đã được chứng nhận. Nó chỉ nói rằng tôi không dựng được counterexample khái niệm nào với các mục được giao. Còn 3 nghĩa vụ đặc tả nhỏ (O1–O3), không chặn.

## Kiểm từng mục

**R4-B1 (witness của server) — đóng.** Tôi đã thử lại đúng trace của R4: A2 gửi `seq = 2^64−1` kèm witness giả hoặc không có witness. Theo dòng 501–503, packet đó chỉ bị reject, không quarantine.

Quarantine chỉ xảy ra khi đủ cả ba điều kiện: MAC tạo bằng `kw` hợp lệ, audience và epoch đúng, và `seq` lớn hơn seq đã commit ở server. A2 chỉ có thể nộp witness mà server từng thực sự cấp. Nếu server đã cấp một witness có seq cao hơn seq hiện tại của nó, thì đó đúng là rollback thật, nên quarantine lúc đó là đúng.

Witness không gắn với principal, nên bất kỳ ai cũng có thể chuyển tiếp một witness thật. Điều đó không gây hại vì witness chỉ phản ánh sự thật.

Đổi epoch hoặc `kw` thì witness cũ mất hiệu lực, và việc này không bị coi là báo động mới (dòng 505). Test N2 (dòng 555) có thể dùng để bác bỏ thiết kế nếu sai.

**R4-S1 (bảng M) — đóng.** Bảng M đã có `peer_seen_server_seq` và `server_seq_witness` (dòng 138–139). Version là `0x0005` draft, và draft3/4 bị reject (dòng 125). Mô tả M ở dòng 193 cũng đã cập nhật. Witness rỗng chỉ được phép khi seq bằng 0 và thuộc một policy cụ thể, nên không có đường lách khi `seq ≠ 0` mà witness rỗng.

**R4-S2 (frontier của máy) — đóng.** Inner request giờ luôn có đủ 4 segment, với segment thứ tư là `machine_frontier` dạng nhị phân cố định (dòng 157–160). Dữ liệu này không còn nằm trong JSON nên không còn mơ hồ về cách phân tích.

**R4-S3 (câu cũ "chỉ khóa writes") — đóng.** Dòng 408 và 484 giờ ghi là "mọi route có claim/Seal". Còn các cụm "mở writes" ở dòng 335/337 trong bối cảnh restore. Chúng nên được đổi thành "mở admissions" cho khớp với dòng 342. Đây chỉ là chỉnh câu chữ, không phải lỗ hổng, vì quarantine ở dòng 342 đã khóa admissions.

**R4-S4 (response tới sai thứ tự) — đóng.** Theo dòng 533–535, client chỉ giữ giá trị seq lớn nhất trong cùng epoch và không báo động khi response về sai thứ tự.

**Challenge kiểm frontier của máy (mục mới) — sound có điều kiện.** Lập luận như sau:
- Mọi seq trong telemetry đã ký đều được đọc từ ledger **trước** khi gửi.
- Server lưu `expected` là giá trị lớn nhất trong số telemetry đã verify, tính tại thời điểm cấp challenge.
- Máy đọc ledger **sau** khi nhận challenge.

Vì vậy, nếu ledger chỉ tăng đơn điệu, reply phải có seq ≥ `expected`. Reply nhỏ hơn `expected`, hoặc bằng seq nhưng khác head, chỉ có thể là do ledger bị lùi hoặc phân nhánh. Telemetry tới sai thứ tự không còn gây quarantine nhầm. Phạm vi quarantine chỉ là chính máy đó. Trường hợp seq lớn hơn mà thiếu bằng chứng nối dài ledger thì không redeliver, tức an toàn theo hướng không làm gì.

Lập luận này dựa trên hai giả định được nêu ở O1 và O2 bên dưới.

**Đồng hồ Android — ghi đúng mức.** Dòng 538–544 ghi rõ: đồng hồ OS không mặc định đáng tin, gate triển khai phải chứng minh có nguồn thời gian độc lập, và nếu không thì không đưa lên production.

Tôi chấp nhận phản bác về đề xuất R4 của tôi: A1 có thể phát lại manifest cũ nhiều lần để reset bộ đếm thời gian tính từ lúc nhận. Vì vậy đề xuất "elapsed kể từ lúc nhận" không chứng minh được freshness bound. Gate này vẫn **chưa được kiểm chứng**.

**Sketch trong `security-obligations.md`.** Dòng 17–18 đã thêm giả định "CLOCK_UNTRUSTED khóa mọi Seal và cleanup; cleanup chỉ theo đồng hồ đã verify". Lập luận Seal tối đa một lần giờ ghi đủ điều kiện. Nó vẫn chỉ là sketch, không phải chứng minh.

## Nghĩa vụ đặc tả (không chặn, nên ghi trước khi viết vector)

| ID | Vị trí | Nghĩa vụ | Nếu bỏ qua |
|---|---|---|---|
| O1 | design.md:497–499 | Witness chỉ được cấp cho seq đã **commit bền** (FULL + flush) **trước** lúc Seal | Server mất commit cuối dù không có rollback thật; peer giữ witness của seq chưa bền. Quarantine khi đó vẫn đúng về an toàn nhưng là cảnh báo khó phân loại. Nên ghi rõ thứ tự |
| O2 | design.md:507–513, 159 | Telemetry chỉ báo `ledger_seq` và head đã commit bền; head là hash chain `head_n = H(head_{n−1} ‖ entry_n)`, có domain riêng | Báo seq đang nằm trong RAM rồi crash sẽ gây quarantine nhầm một máy |
| O3 | design.md:183, 498 | Response inner là JSON, nên phải định nghĩa encoding cho `server_seq` (số nguyên trong miền an toàn, hay chuỗi) và cho witness 32 byte (base64url không padding?) | Vector Dart/Python không byte-exact được |

## Bảng đóng

| ID | Trạng thái |
|---|---|
| R4-B1 | Đóng (thiết kế); test N2 còn phải chạy |
| R4-S1 | Đóng |
| R4-S2 | Đóng |
| R4-S3 | Đóng; còn chỉnh câu ở dòng 335/337 |
| R4-S4 | Đóng |
| Challenge frontier máy | Đóng (thiết kế), có điều kiện O1 và O2; test N2o còn phải chạy |
| Gate đồng hồ Android | Mở như production gate, chưa verified |
| C1, C2, N1–N5 (từ R4) | Giữ trạng thái đóng như R4; N2 nay đóng nhờ R4-B1 |

## Hai lớp cần tách bạch

**Production gates chưa đạt:**
- HPKE có Export trên Dart, hoặc FFI binding, kèm vector chính thức và vector byte-exact;
- khóa ký trên Keystore;
- adapter GET;
- lưu queue bền;
- các tham số Δ, L_max, σ, D_poll, margin và lịch ký manifest;
- NTS trên server và nguồn thời gian độc lập cho app/máy;
- flush thật trên server và Pi;
- topology Caddy;
- miền rollback độc lập cho recovery artifact;
- định nghĩa extension proof cho ledger;
- harness lỗi có đếm Seal, claim và executor.

Chưa có code, test, benchmark hay formal verification nào được chạy.

**Không được tuyên bố:**
- tối ưu, vì vector Pareto chưa có trọng số hay số đo;
- an toàn của toàn bộ composition;
- exactly-once hay at-most-once vật lý;
- không thể bị xâm phạm hoặc đã được chứng nhận.

Bảo đảm hẹp có thể giữ là: không tự gọi business executor lần hai cho cùng một durable claim, với điều kiện storage bền đúng nghĩa.

Sau khi ghi O1–O3, vòng thiết kế có thể khép. Việc mở triển khai do lead quyết định, không thuộc vai reviewer.
