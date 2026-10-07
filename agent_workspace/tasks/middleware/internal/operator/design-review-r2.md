# Review R2 — thiết kế bảo vệ gói tin (`design.md` R2)

**Phạm vi:** Tôi chỉ đọc, không sửa file và không chạy gì. Các counterexample dưới đây được suy từ đặc tả, **chưa thử thật**.

**Đã đọc:** `operator/design-feedback-r1.md`, `packet-security/design.md` (nguồn quyết định chính), `packet-security.html`, root HTML (nay chỉ còn là trang dẫn), các banner trỏ về `design.md` trong `index/protocol/keys/duplicates/roadmap.md`, và `machine_transport.py` (đã đọc ở R1).

## Verdict

**Chưa đạt.** R2 đã đóng phần lớn các lỗi cấu trúc của R1:
- bỏ handshake tự ghép;
- chỉ còn một cơ chế xác thực;
- byte schema dùng tiền tố độ dài (LP);
- có trust root đặt ngoài hệ thống online;
- có ledger với trạng thái `unknown`.

Tài liệu cũng chỉ còn một nguồn quyết định: root HTML là trang dẫn và các file nghiên cứu đều có banner trỏ về `design.md`.

Còn **4 lỗi bất biến bảo mật có counterexample cụ thể** (F1–F4). Đây là lỗi thiết kế, không phải chỗ thiếu adapter. F1 nghiêm trọng nhất: khi request bị phát lại, server có thể mã hóa response hai lần với cùng key và nonce.

## Findings OPEN

| ID | Mức | Loại | Vị trí | Tóm tắt |
|---|---|---|---|---|
| F1 | **Chặn** | Bất biến | design.md:148–150, 155, 158, 172–175, 187 | Trạng thái "chỉ seal một lần" gắn với đối tượng context trong RAM, không gắn với `(server_kid, enc, M)`. Request bị phát lại hoặc gửi đồng thời sẽ seal lần hai dưới cùng (k, n) |
| F2 | **Chặn** | Bất biến | design.md:208 | Ledger của máy có khóa `(generation, command_id)`, nên mất chống trùng khi máy enroll lại |
| F3 | **Chặn** | Bất biến | design.md:203–206, 189–193 | Command không có hạn của ý định (`deadline`). Liên kết với poll chỉ chứng minh lần giao còn mới, không chứng minh ý định còn mới |
| F4 | **Chặn** | Bất biến | design.md:185–186, 213–218 | Restore backup làm ledger operation lùi về trạng thái cũ, và việc thu hồi credential không ngăn được thực thi lại |
| F5 | Nên sửa | Tham số trước khi chọn profile | design.md:62–75 | Thiếu cửa sổ "đóng băng" manifest và khóa trung gian online. Root offline mâu thuẫn với manifest có hạn ngắn |
| F6 | Nên sửa | Thiết kế | design.md:79–81 | "Recovery mạnh" chưa định nghĩa, trong khi cài lại app là đường thay khóa phổ biến nhất |
| F7 | Chặn trước khi chọn profile | Phụ thuộc prototype | design.md:52–58 | Chưa có phương án B nếu Dart không có thư viện HPKE có Export |
| F8 | Nên sửa | Thiếu wire profile | design.md:107, 110, 123–125 | Bootstrap không có encoding cho trường `sig` rỗng; "dạng query được phép" chưa liệt kê |
| F9 | Nên sửa | Implementation | design.md:169–170 | Không có cơ chế phát hiện đồng hồ server chạy lùi (thiếu high-water mark lưu bền) |
| F10 | Nên sửa | DoS | design.md:184, 262 | Mọi bootstrap dùng chung `credential_kid="bootstrap"`, nên ai cũng làm cạn được quota login toàn hệ thống |
| F11 | Gợi ý | Implementation | design.md:189–193 | Thứ tự deadline long-poll server/máy chưa ràng buộc, làm tăng số lệnh rơi vào `unknown` |
| F12 | Gợi ý | Tối ưu | design.md:49–50, 177, 187 | Có phương án replay trong RAM kèm watermark, rẻ hơn (xem mục "Lập luận không hợp lệ") |

### F1 — Seal response hai lần (chặn)

Counterexample, kẻ tấn công A1, không cần khóa nào:

1. App gửi request R = (M, enc, ct, sig). Server verify chữ ký, Open, claim thành công, rồi seal response S₁ bằng (k, n) = Export(ctx_R).
2. A1 gửi lại nguyên văn R, hoặc gửi hai bản đồng thời trước khi bản đầu claim xong. Chữ ký vẫn đúng. Recipient key tĩnh nên `SetupBaseR(enc)` dựng ra context **mới** trong RAM, ở trạng thái NEW, nhưng Export ra **đúng cùng (k, n)**. Claim thất bại vì trùng.
3. Đặc tả không cấm bước tiếp theo:
   - dòng 155 chỉ cho trả transport error tối giản khi "không có context";
   - ở đây đã có context, và dòng 148 yêu cầu seal "cả error/success".

   Vậy server seal một lỗi E dưới cùng (k, n).
4. Hậu quả:
   - C₁ ⊕ C₂ = S₁ ⊕ E. E có cấu trúc dễ đoán, nên A1 khôi phục được tiền tố của S₁. Với response login bootstrap, phần đó có thể là token phiên.
   - Hai tag GCM cùng nonce cho phép giải H, từ đó **giả mạo được response** dưới k. A1 có thể gửi app một response giả như "thành công" hoặc "unknown".

Sửa tối thiểu:
- Kiểm freshness của M **sau khi verify chữ ký và trước decap**.
- Quyền gọi Seal chỉ thuộc về luồng **thắng claim** `UNIQUE(audience, credential_kid, attempt_id)`.
- Mọi nhánh sau Open mà không thắng claim (trùng, hết hạn, store đầy hoặc lỗi, phiên bị thu hồi trước claim) chỉ trả transport error **không mã hóa**.
- Viết bất biến thành: "với mỗi `(server_kid, enc)`, tối đa một lần gọi Seal trong toàn bộ thời gian sống của recipient key". Không viết theo "mỗi context".

Phép kiểm có thể bác bỏ: gửi lại cùng R 2 lần tuần tự và 2 lần đồng thời, sau restart và trước restart; mọi body phản hồi khác bản đầu phải không chứa ciphertext.

### F2 — Ledger máy có generation trong khóa (chặn)

Counterexample:
1. Server giao command c (generation g₁). Máy claim (g₁, c), thực thi, nhưng kết quả bị mất. Server ghi `unknown`.
2. Máy enroll lại thành g₂, ví dụ do xoay khóa. Recovery được phê duyệt gửi lại c, giữ nguyên `command_id` như dòng 206 cho phép.
3. Máy tra (g₂, c), không thấy, và **thực thi lần hai**.

Sửa tối thiểu:
- Khóa ledger theo `command_id`; generation chỉ là một cột dữ liệu.
- Server không được gửi lại command qua ranh giới generation; command loại này chuyển sang `unknown` và cần đối soát.

### F3 — Command thiếu hạn ý định (chặn)

Counterexample:
1. User bấm thao tác pha chế. Máy offline, app hiện `unknown` hoặc timeout.
2. Mười giờ sau máy online và poll. Server lấy c từ queue ra, gắn với `poll_attempt_id` mới; máy chấp nhận vì poll còn sống, rồi thực thi.

Mã hiện tại thật ra đang an toàn hơn thiết kế: `timeout_message` hủy lệnh chưa được lấy (`machine_transport.py:71–80`).

Sửa tối thiểu:
- Thêm `intent_deadline` do **server** quyết định, kèm sẵn trong command.
- Server chỉ giao command khi `now_server < intent_deadline`.
- Việc lấy khỏi queue và ghi `dispatched` bền nằm trong cùng một transaction.
- Quá hạn mà chưa dispatch thì chuyển `failed_no_effect`.

Máy không cần đồng hồ, vì server là bên có thẩm quyền về thời gian.

### F4 — Restore backup cho phép thực thi lại (chặn)

Counterexample:
1. Operation o đã chạy xong (done) sau thời điểm backup B.
2. Restore B. Ledger quay về trạng thái không có o.
3. Credential bị thu hồi theo dòng 186. App enroll lại, rồi retry o với cùng `operation_id` và byte nội dung y hệt (dòng 216 bắt buộc giữ nguyên byte).
4. Server claim mới và thực thi lại.

Thu hồi credential không liên quan gì tới ledger.

Sửa tối thiểu:
- Lưu `restore_watermark`, là thời điểm server tại lúc restore.
- Thêm `op_created_at` vào fingerprint và vào phần được ký.
- Từ chối, hoặc buộc chuyển sang `unknown` cần đối soát, mọi operation có `op_created_at < restore_watermark` mà ledger không có record.
- Client: khi enroll lại thì chuyển các operation đang treo sang `unknown`, không retry tự động.

### F5 — Cửa sổ đóng băng manifest

A1 giữ lại manifest mới. Nếu một server key cũ đã bị lộ (qua A3), client vẫn mã hóa tới key đó cho tới hết `validity`. Muốn cửa sổ này ngắn thì phải ký lại manifest thường xuyên, nhưng root lại ở môi trường offline.

Sửa:
- Root offline ký một khóa trung gian online, có hạn dài và có thể thu hồi.
- Khóa trung gian ký manifest ngắn hạn.
- Ghi rõ cửa sổ đóng băng là `manifest_validity` và nêu dứt khoát rằng đây là độ trễ thu hồi tối đa.

### F6 — Recovery chưa định nghĩa

Cài lại app hoặc mất máy luôn mất khóa cũ. Nếu "recovery mạnh" thực chất chỉ là mật khẩu cộng OTP qua bootstrap, thì người có mật khẩu và OTP thay được credential. Đây không phải lỗi của E, nhưng dòng 80 đang ngầm hứa nhiều hơn mức đó.

Sửa: định nghĩa cụ thể yếu tố recovery, thông báo cho thiết bị cũ, và có thời gian chờ trước khi credential mới được dùng cho thao tác ghi lên máy.

### F7 — Phương án B cho thư viện HPKE

Nếu Dart không có thư viện HPKE có Export và vượt qua bộ vector chuẩn, các lựa chọn là:
- (a) tự ghép HPKE từ X25519 + HKDF + AEAD, có vector RFC 9180 làm cổng kiểm;
- (b) đổi nền tảng;
- (c) dừng.

Phải chọn trước. Phương án (a) là "tự viết giao thức" đã được giới hạn rủi ro bằng vector, nên cần được chấp nhận hoặc cấm một cách tường minh.

### F8 — Thiếu wire profile cho bootstrap và query

- Bootstrap: `LP(sig)` là `LP(ε)` hay bỏ hẳn trường? Đây là chỗ hở cho tấn công đổi mode: một packet có `credential_kid=bootstrap` nhưng lại kèm chữ ký, hoặc ngược lại.
- Cần quy tắc: `credential_kid` quyết định sự có mặt của chữ ký, cộng một vector âm cho mỗi trường hợp lệch.
- Query: liệt kê các dạng được phép cho từng `route_id`; mặc định là query rỗng.

### F9 — Đồng hồ server chạy lùi

Dòng 169–170 yêu cầu fail closed khi đồng hồ nhảy lùi nhưng không nói cách phát hiện.

Sửa: lưu `max_now_seen` bền. Khi khởi động hoặc với mỗi claim, nếu `now < max_now_seen − σ` thì khóa thao tác ghi.

### F10 — DoS quota bootstrap

Mọi bootstrap dùng chung `credential_kid="bootstrap"`, nên một nguồn bất kỳ làm cạn được quota bootstrap, chặn login của mọi người dùng. Limiter theo IP đứng sau Caddy (`X-Forwarded-For`) vẫn chưa kiểm được.

Ghi đây là rủi ro còn lại về availability. Tách bucket theo IP thật; muốn có IP thật thì phải có cấu hình Caddy.

### F11 — Thứ tự deadline long-poll

Phải có ràng buộc `POLL_WAIT_server + RTT_max < deadline_local_máy`. Nếu không, server lấy command ra và ghi vào một kết nối máy đã bỏ, khiến command đó thành `dispatched → unknown`. Đây là vấn đề liveness, không phải safety, nhưng sinh ra việc đối soát thủ công.

## Lập luận không hợp lệ hoặc cần sửa

1. **(Lỗi của tôi ở R1, chấp nhận phản hồi.)** "HPKE: q=1 nên P=0" là sai. Phản hồi 2, 4 và 7 của Codex đúng.
2. **(Lỗi của R2.)** "Recipient key tĩnh mở được packet cũ ⇒ replay store phải bền" (dòng 177, phản hồi 1) là suy luận không chặt. Tiền đề đúng, nhưng kết luận không suy ra được:
   - Chỉ cần một **watermark bền**: từ chối `issued_at < boot_time + Δ_future`, với `boot_time` lấy từ high-water mark bền (F9).
   - Khi đó tập replay trong RAM là đủ, với giá phải trả là khoảng Δ_future giây từ chối sau mỗi lần restart.
   - Giả định: đồng hồ server không lùi quá σ.

   Ledger idempotency vẫn phải bền. Đây là lựa chọn Pareto, không bắt buộc. Nhưng câu "không dùng replay RAM chỉ vì đã dùng HPKE" (dòng 50) không loại được phương án này.
3. Các công thức đã kiểm lại và **đúng với giả định đã ghi**:
   - 2^40/2^97 ≈ 6.94e-18; nhân m = 2^16 được ≈ 4.55e-13.
   - H ≤ L_max + Δ_f + σ + margin. Suy ra: chấp nhận được khi t ∈ [issued_at − Δ_f, expires_at], và giữ record tới expires_at + σ + margin.
   - Token bucket: ≤ b + ⌈rH⌉.
   - Overhead mật mã 32 + 16 + 64 = 112 B; hai lớp base64 cho 16n/9.

   Thiếu một điều: bound b + ⌈rH⌉ chỉ đúng nếu **bootstrap cũng đi qua bucket toàn pool**. Hiện đặc tả chưa nói rõ.
4. Câu "Response AEAD đủ cho A0/A1" (dòng 44–45) chỉ đúng khi F1 đã được sửa. Hiện tại câu này sai trong trường hợp request bị phát lại.

## Bảng đóng mục B1–M5

| R1 | Trạng thái | Ghi chú |
|---|---|---|
| B1 | **Đóng (quyết định)** | Chọn E, có A0–A3. Còn rủi ro: chưa kiểm topology Caddy, nên giá trị thực của E chưa được chứng minh |
| B2 | **Đóng (thiết kế)** | Dùng HPKE single-shot. Phụ thuộc F7 |
| B3 | Đóng một phần | Đã có root và manifest; còn F5 |
| B4 | Đóng một phần | `command_id` ngẫu nhiên, poll binding, credential theo máy; còn F2, F3, và định nghĩa "provisioning tin cậy" |
| B5 | **Đóng** | Một chữ ký ngoài; lý do KCI hợp lệ |
| H1 | Đóng (bền) | Còn F9, F12; restore gộp vào F4 |
| H2 | Đóng một phần | State machine đúng; `claimed → failed_no_effect` chứng minh được nhờ ghi `dispatched` trước. Còn F4 |
| H3 | Đóng một phần | Request đã dùng LP; còn F8 |
| H4 | **Đóng** | `route_id` qua map tĩnh, status nằm bên trong phần mã hóa |
| M1 | Đóng một phần | Freshness của lần giao: đạt; freshness của ý định: F3 |
| M2 | **Đóng** | Tuyến tính hóa qua transaction SQLite; giới hạn với lệnh đã dispatch được nêu rõ |
| M3 | **Đóng** | Envelope nhị phân |
| M4 | **Đóng** | Ghi bằng công thức, không còn số rời |
| M5 | Mở (gate) | Chưa có tham số và số đo; còn F10 |

## Gate cho R3

1. F1–F4: sửa đặc tả, kèm counterexample ở trên được viết thành test bác bỏ (đặc tả test, chưa cần code).
2. F7: chọn phương án B và ghi vào ADR.
3. F5, F8, F9: viết đủ tham số và vector âm.
4. Bổ sung một câu cho bất biến Seal theo `(server_kid, enc)`, và nêu bootstrap có đi qua bucket toàn pool hay không.

Triển khai vẫn tạm dừng. Đây chỉ là vòng lặp thiết kế.
