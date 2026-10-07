# Review thiết kế mật mã cho middleware gói tin, vòng 1

**Phạm vi:** Tôi chỉ đọc tài liệu và mã, không chạy test, không sửa file. Không có chuỗi tấn công nào trong báo cáo đã được thử thật. Mọi số liệu dưới đây là tính toán từ định dạng hoặc giả định đã ghi rõ, không phải số đo.

**Đã đọc:** `CRYPTOGRAPHY_MIDDLEWARE_DESIGN.html` (gọi tắt là ROOT), `packet-security.html`, `internal/packet-security/{index,protocol,keys,duplicates,roadmap}.md`, mục 6 của `CODE_STYLE.md`, và các file mã `server/lib/http/{http_server,http_json,http_rate_limit}.py`, `server/lib/machine/machine_transport.py`, `server/lib/security/user_session.py`, `machine/server_connection/*`, `app/flutter_app/lib/core/server_client.dart`.

**Không có trong repo:** cấu hình Caddy. Vì vậy tôi không đưa ra kết luận nào về TLS termination hay `X-Forwarded-For`.

## Verdict

**Chưa đủ điều kiện để chọn profile.** Hai bộ tài liệu đang mô tả hai hệ thống khác nhau:

- ROOT là một profile cụ thể: DPoP, handshake X25519 tự thiết kế, AES-GCM, Redis, chỉ cho app POST.
- Bộ nghiên cứu mới cấm tự viết handshake, coi mã hóa payload là yêu cầu chính, và bắt buộc bảo vệ cả lệnh gửi tới máy.

Vấn đề gốc là **chưa định nghĩa kẻ tấn công mà lớp mã hóa ứng dụng phải chống**. Không có kẻ tấn công cụ thể thì không thể đánh giá đúng hay sai, càng không thể nói "tối ưu". Còn 5 lỗi chặn trước khi chọn profile (B1–B5).

## Bảng phát hiện

Mức độ theo `CODE_STYLE.md` §6. Phân loại: **[P]** = chặn trước khi chọn profile, **[I]** = nghĩa vụ khi triển khai, **[O]** = ngoài threat model.

| ID | Mức | Loại | Vị trí | Tóm tắt |
|---|---|---|---|---|
| B1 | Chặn | P | ROOT:109,146,329 ↔ roadmap.md:13, index.md:47 | Chưa có kẻ tấn công cho lớp mã hóa ứng dụng; ROOT nói lớp này là tùy chọn, roadmap nói là yêu cầu chính |
| B2 | Chặn | P | ROOT:142–143 ↔ protocol.md:25, roadmap.md:103 | Handshake tự thiết kế: phía app không được xác thực, không có key confirmation; mâu thuẫn trực tiếp với quy tắc "không tự viết handshake" |
| B3 | Chặn | P | ROOT:142, protocol.md:53 | Khóa định danh server lấy "qua kênh tin cậy" không được định nghĩa; nếu lấy qua TLS thì Caddy có thể đứng giữa toàn bộ lớp này |
| B4 | Chặn | P | ROOT:51,167,326 ↔ protocol.md:42,53; `machine_transport.py:25,53`; `machine_server_request.py:12` | Đường lệnh tới máy (có tác động vật lý) không có profile; mã lệnh là bộ đếm reset sau mỗi lần restart |
| B5 | Chặn | P | ROOT:152,167,175,280 ↔ protocol.md:13 | Hai chữ ký cùng khóa thiết bị cộng với GCM; không xác định được cái nào là bắt buộc |
| H1 | Chặn | I | ROOT:74,184,204,338 ↔ `http_server.py:11,39`, shared-state-evolution.md:124 | Dùng Redis/replica trong khi kiến trúc là một process; tính bền của replay store khi restart chưa được đặc tả |
| H2 | Chặn | I | ROOT:193,205 ↔ duplicates.md:29–31 | ROOT yêu cầu "lưu kết quả cùng transaction", không làm được với lệnh qua máy; thiếu trạng thái unknown |
| H3 | Chặn | I | ROOT:168,174,176 | Byte AAD không xác định: nhãn "aad" nằm ở đâu, "bỏ digest" là bỏ field nào |
| H4 | Chặn | I | ROOT:168,208 | Bind theo `path` thô và HTTP status ngoài, trong khi proxy có thể sửa cả hai |
| M1 | Nên sửa | I | ROOT:203–204 | Thời hạn giữ replay theo cửa sổ thời gian; Raspberry Pi không có RTC |
| M2 | Nên sửa | I | ROOT:337,339; roadmap P3.4 | Race giữa thu hồi phiên và request đã verify |
| M3 | Nên sửa | I | ROOT:155,167 | Base64 hai lớp, overhead lớn không cần thiết |
| M4 | Nên sửa | I | ROOT:202 | Giới hạn 2^20 là số tùy ý; bộ đếm mất khi restart |
| M5 | Nên sửa | I | `http_rate_limit.py:11–26` | Limiter theo IP phía sau proxy; chưa có ngân sách cho chi phí verify |
| O1 | — | O | ROOT:107, index.md:51 | Máy hoặc app bị chiếm quyền; server bị chiếm quyền |

## Chi tiết các lỗi chặn

### B1 — Chưa có kẻ tấn công cho mã hóa payload

**Mâu thuẫn:** ROOT:146 và ROOT:329 bước (4) nói handshake + AES-GCM "chỉ khi có yêu cầu bảo vệ payload sau TLS termination". roadmap.md:13 lại nói mã hóa payload "là yêu cầu chính, không phải nhánh tùy chọn".

**Vì sao chặn:** Chỉ có một kẻ tấn công mà lớp mã hóa ứng dụng chống được nhưng TLS 1.3 không chống được. Đó là một bên đọc được plaintext tại Caddy (log, mirror, admin proxy) nhưng **không** có quyền trên process server. Nếu Caddy và server chạy cùng host, cùng admin, thì mã hóa payload gần như không thêm gì, chỉ tăng độ phức tạp.

Không được gộp các kẻ tấn công sau vào cùng một loại:

- Kẻ nghe trên mạng: TLS 1.3 đã đủ.
- Proxy hoặc Caddy bị chiếm: cần lớp ứng dụng **và** khóa không đi qua proxy (xem B3).
- Endpoint bị chiếm: ngoài threat model (O1).

**Sửa tối thiểu:** Viết bảng kẻ tấn công A0–A3. Mỗi loại ghi năng lực, khóa họ nắm, và thuộc tính hệ thống phải giữ. Sau đó chọn một trong hai:

- **Profile T:** TLS + ràng buộc khóa thiết bị.
- **Profile E:** T + mã hóa payload.

**Phép kiểm có thể bác bỏ:** Với A1 (proxy đọc được plaintext tại Caddy), tồn tại một trường của payload mà Profile T để lộ còn Profile E không. Nếu không chỉ ra được trường nào thì E là thừa.

### B2 — Handshake tự thiết kế

**Chuỗi vấn đề (ROOT:142–143):** Chỉ server ký transcript. Ephemeral key của app không được ký bằng khóa thiết bị. Hai phía không có bước key confirmation. Transcript chứa "user/device/key ID", nhưng chính server tự điền các giá trị đó.

**Hậu quả:**

- Server không có bằng chứng mật mã rằng `K_request` thuộc về thiết bị đã enroll. Lớp mã hóa phải dựa vào chữ ký Ed25519 bên trong để xác thực, nên chính GCM không xác thực nguồn gửi.
- Kẻ cầm token bị lộ có thể chạy handshake và nhận một session hợp lệ. Họ không gửi được request vì thiếu chữ ký thiết bị, nhưng vẫn tốn tài nguyên session của server.
- Không có chứng minh (Tamarin/ProVerif hay tương tự) cho PFS hoặc chống unknown-key-share.
- ROOT:146 tự cảnh báo "không ghép thông điệp tùy ý", nhưng sơ đồ 4.1 chính là ghép thông điệp tùy ý.

**Sửa tối thiểu:** Bỏ handshake. Dùng HPKE (RFC 9180) theo khung encapsulated request/response của Oblivious HTTP (RFC 9458): mỗi request một `enc` mới, response mã hóa bằng khóa export từ context HPKE.

Đổi lại sẽ **mất PFS** khi khóa tĩnh của server bị lộ. Để giới hạn mức mất này: xoay khóa gateway theo epoch E và xóa khóa cũ, khi đó cửa sổ lộ ≤ E cộng thời gian overlap.

**Phép kiểm:** Bộ vector chính thức của RFC 9180 phải pass trên cả Dart và Python. Nếu thư viện Dart không có HPKE thì giả thuyết này bị bác bỏ và phải quay lại quyết định.

### B3 — Trust anchor của khóa server

ROOT:142 viết "đã được app tin cậy qua quy trình cấp phát". protocol.md:53 viết "trust server đã xác thực qua TLS".

**Chuỗi tấn công:** Nếu public key của server được tải qua chính đường TLS kết thúc tại Caddy, thì A1 có thể thay key đó. Sau đó A1 giải mã và mã hóa lại toàn bộ payload. Lớp E sụp hoàn toàn đúng trước kẻ tấn công duy nhất mà nó được tạo ra để chống.

**Sửa tối thiểu:** Neo một khóa ký offline trong APK và trong image của máy. Khóa gateway được khóa offline đó ký kèm thời hạn. Rotation dùng chứng chỉ có `not_after`; mất khóa offline thì bắt buộc cập nhật app.

**Phép kiểm:** Test thay key giả qua proxy phải bị app từ chối.

### B4 — Đường lệnh tới máy không có profile

**Từ mã:**

- Máy xác thực bằng `product_key` tĩnh gửi trong mọi body (`machine_server_request.py:12`). Key này cũng nằm trong payload ghép cặp BLE (`machine/pairing/README.md:23`).
- Lệnh có `id = next(DEM_LENH)` với `count(1)` trong RAM (`machine_transport.py:25,53`), nên sau restart id lại bắt đầu từ 1.
- `take()` lấy lệnh ra khỏi hàng chờ trước khi máy nhận được (dòng 88).

**Hậu quả:**

1. Ledger chống trùng trên máy, theo đúng thiết kế P5.3 (khóa theo command id), sẽ coi lệnh mới sau restart server là bản trùng và bỏ qua. Ngược lại, nếu ledger chỉ lưu tạm thì lệnh cũ có thể bị nhận như lệnh mới.
2. Ai có `product_key` đều giả được máy: lấy lệnh của máy và trả kết quả giả. ROOT không có profile nào cho luồng máy (ROOT:51,326).

**Sửa tối thiểu:**

- `command_id` là số ngẫu nhiên 128 bit (CSPRNG).
- Server ký lệnh với các trường: `machine_id`, `command_id`, `operation_id`, `poll_nonce`, `instruction`, `H(data)`.
- Máy lưu ledger `command_id` bền.
- Khóa máy theo từng máy, cấp lúc enrollment, thay cho `product_key` dùng làm bearer.

**Phép kiểm:** Restart server giữa hai lệnh thì máy phải thực thi đúng cả 2. Replay lại lệnh đã ký thì máy thực thi 0 lần.

### B5 — Cơ chế xác thực trùng lặp

Mỗi request hiện có ba lớp xác thực:

- Chữ ký DPoP: Ed25519 trên `htm`, `htu`, `iat`, `jti`, `ath` (ROOT:152).
- Chữ ký Ed25519 thứ hai trên `signed_fields`, nằm **bên trong** ciphertext (ROOT:167–175).
- GCM tag.

**Mâu thuẫn:** protocol.md:13 nói verify chữ ký ngoài **trước** giải mã, nhưng ROOT:280 verify sau giải mã. Hai chữ ký dùng chung một khóa thiết bị. Tách miền hiện chỉ dựa vào cấu trúc: JWS có đúng 1 dấu chấm, còn `signing_input` có 8. Không có nhãn tách miền rõ ràng hay chứng minh.

**Thực tế:** Repo không có OAuth Authorization Server (token opaque, `user_session.py:23–30`). Định dạng DPoP JWT không đem lại khả năng liên thông nào, chỉ tốn byte và mã.

**Sửa tối thiểu:**

- **Profile T:** một chữ ký trên chuỗi bind tới `H(body)`.
- **Profile E:** người gửi được xác thực bằng một chữ ký nằm ngoài AEAD, ký lên `enc‖ct`. Hoặc dùng chế độ HPKE Auth nếu chấp nhận dùng khóa KEM tĩnh cho thiết bị.

Chọn một, ghi lý do vào ADR.

**Phép kiểm:** Bỏ từng lớp đi một; nếu có thuộc tính nào trong bảng B1 bị mất thì lớp đó là cần thiết.

## Các lỗi chặn khi triển khai và nên sửa

### H1 — Replay store

ROOT nhắc Redis và replica 5 lần, nhưng server là `ThreadingHTTPServer` một process.

**Hệ quả rút gọn được:** Ở Profile E, khóa session hoặc epoch chỉ nằm trong RAM. Sau restart, packet cũ không còn qua được AEAD, nên replay set có thể để trong RAM mà không mất tính đúng.

Ở Profile T (chỉ ký, khóa thiết bị sống lâu), replay set mất khi restart. Packet chụp trong cửa sổ `W + δ` trước restart sẽ được nhận lại.

**Sửa:**

- Profile T: bảng SQLite có ràng buộc `UNIQUE(key_id, request_id)` và `INSERT` atomic. Hoặc thêm một `boot_epoch` vào nội dung được ký và từ chối epoch cũ.
- Cả hai profile: có lock hoặc UNIQUE để chặn hai thread cùng nhận một request.

**Phép kiểm:** Gửi 2 bản đồng thời thì đúng 1 bản được nhận. Gửi lại sau restart thì bị từ chối.

### H2 — Idempotency

ROOT:193 viết "Thực hiện tác vụ, lưu kết quả cùng transaction" và chỉ có ba trạng thái. Với lệnh qua máy, transaction không thể kéo dài qua lúc máy chạy (duplicates.md:29).

Mã hiện tại timeout thì trả "Máy chưa trả kết quả" (`machine_transport.py:80`), tức đã ngầm có trạng thái **unknown**.

**Sửa:**

- Ledger có các trạng thái `claimed`, `dispatched`, `done`, `unknown`.
- Claim nằm trong một transaction riêng. Ghi kết quả là một transaction khác.
- Trạng thái `unknown` không bao giờ tự gửi lại lệnh.

**Phép kiểm:** Inject crash ở 4 điểm: trước dispatch, sau dispatch, sau khi máy thực thi, sau khi ghi kết quả. Ở mọi trường hợp, số lần thực thi vật lý phải ≤ 1.

### H3 — AAD

Đặc tả cần một bảng byte duy nhất: thứ tự field, nhãn `req` / `res` / `aad`, cách mã hóa độ dài. Vector âm phải gồm một field rỗng và một field chứa dấu `.` trước khi base64.

### H4 — Path và status

- Bind theo **ID route logic**, tức hằng trong `server/config/routing.py` (ví dụ `MACHINE_MENU_UPDATE`), không bind theo path thô mà proxy có thể sửa.
- App chỉ tin status nằm trong plaintext đã xác thực. Status ngoài chỉ là tín hiệu transport.

**Phép kiểm:** Proxy đổi 200 thành 500 hoặc ngược lại; app không được đổi trạng thái nghiệp vụ.

### M1 — Freshness trên máy

Pi không có RTC, nên trước khi NTP đồng bộ thì timestamp vô nghĩa.

**Sửa:** Máy gửi `poll_nonce` 128 bit. Lệnh đã ký phải chứa đúng nonce đó. Như vậy freshness không cần đồng hồ.

### M2 — Race thu hồi

Request đã verify xong, rồi logout xảy ra song song, nhưng feature vẫn ghi.

**Sửa:** Kiểm lại phiên trong cùng transaction với thao tác ghi nghiệp vụ, hoặc ghi rõ cửa sổ race được chấp nhận là ≤ một transaction.

### M3 — Overhead

Xem mô hình ở dưới. Cách sửa là chỉ dùng một lớp base64, hoặc gửi body nhị phân với `Content-Type` riêng.

### M4 — Giới hạn nonce

Xem mô hình. Hãy ghi giới hạn bằng công thức và sai số chấp nhận, không ghi một con số rời. Bộ đếm phải gắn với vòng đời khóa: khóa mất khi restart thì bộ đếm reset cũng an toàn.

### M5 — Limiter và DoS

`MAX_IPS = 1000` theo IP phía sau Caddy. Tôi không kiểm được Caddy có truyền IP thật hay không vì cấu hình không có trong repo.

Bước verify phải đặt sau giới hạn kích thước và sau lookup khóa. Lookup khóa không thấy thì từ chối mà không tốn thao tác mật mã nào. Ngân sách số lần verify mỗi giây phải được đo trên host thật, không đoán.

## Mô hình định lượng

Ký hiệu và giả định: `q` = số lần mã hóa trên một khóa; nonce ngẫu nhiên đều; λ = tốc độ request được nhận; W = cửa sổ freshness; δ = độ lệch đồng hồ tối đa được chấp nhận.

1. **Va chạm nonce GCM** (IV ngẫu nhiên 96 bit, giới hạn birthday):
   - P ≤ q(q−1)/2^97.
   - q = 2^20 → P ≲ 2^−57; q = 2^32 (giới hạn của NIST SP 800-38D cho IV ngẫu nhiên) → P ≲ 2^−33.
   - Với HPKE mỗi request một context: q = 1 trên mỗi khóa, P = 0 theo cấu trúc. Thuộc tính này dựa trên `enc` mới mỗi lần, cụ thể là ephemeral key được sinh bằng CSPRNG tốt.

2. **Va chạm request ID 128 bit:** với N ID sinh ra, P ≤ N²/2^129. N = 2^40 → P ≲ 2^−49.

3. **Kích thước replay set** (có bổ sung admission, không đuổi phần tử còn hiệu lực):
   - |S| ≤ λ_max · (2W + δ).
   - Ví dụ minh họa: λ = 50/s, W = 60 s, δ = 0 → ≤ 6000 mục. Đây là giả định, chưa đo.
   - λ_max phải lấy từ limiter thật.

4. **Thời hạn giữ replay:** R ≥ W + δ + thời gian tối đa từ verify tới claim. Ở Profile E, nếu R ≥ tuổi thọ khóa epoch thì không cần lưu bền (lập luận ở H1).

5. **Overhead trên dây, ước tính từ ROOT:165–175** (chưa đo):
   - Body ≈ (4/3)²·n + ~200 B.
   - Headers DPoP + Authorization + ID + timestamp ≈ 500–800 B.
   - Body nhị phân hoặc một lớp base64: n + 28 B (12 B nonce + 16 B tag), cộng 32 B `enc` nếu dùng HPKE X25519.
   - Kiểm tra bằng cách serialize 3 payload thật và đếm byte.

6. **Chi phí verify:** mỗi request = (số chữ ký) × C_verify + C_aead(n). Bỏ một chữ ký (B5) giảm đúng một C_verify. C_verify chưa đo, không ghi số.

## Hướng đơn giản hơn (đề xuất, chưa kiểm)

Một process, một SQLite, không Redis, không handshake tự thiết kế.

1. **App:**
   - TLS 1.3.
   - Một khóa thiết bị (ES256 hoặc Ed25519, tùy kết quả thử trên Keystore). Token opaque bind với thumbprint trong DB.
   - Một chữ ký trên: nhãn, route ID, `session_id`, `request_id`, `ts`, `operation_id`, `H(body)`.
   - Chỉ khi B1 chứng minh có A1 thì mới thêm HPKE/OHTTP tới khóa gateway được neo offline (B3).
2. **Máy:**
   - Mỗi máy một khóa riêng.
   - Server ký lệnh, có bind `poll_nonce`.
   - Máy ký kết quả, giữ ledger `command_id` bền.
   - `command_id` ngẫu nhiên.
3. **Replay:** đặt trong RAM nếu khóa có vòng đời epoch; nếu không thì dùng SQLite UNIQUE.
4. **Idempotency:** ledger SQLite có trạng thái `unknown`, không bao giờ tự gửi lại lệnh vật lý.

## Những điều chưa kết luận được nếu không có prototype

- Android Keystore trên thiết bị mục tiêu có Ed25519 phần cứng hay chỉ có P-256 (ROOT:141 cũng tự thừa nhận).
- Dart có thư viện HPKE đã được kiểm định hay không.
- C_verify và C_aead trên Pi và trên host server.
- Phân bố độ lệch đồng hồ của app và máy.
- Caddy và server có tách miền quản trị hay không, cùng cấu hình `X-Forwarded-For`.
- Byte-exact giữa Dart và Python.

## Gate cho vòng review tiếp

Codex cần nộp đủ các mục sau. Thiếu mục nào thì giữ verdict "chưa đủ điều kiện":

1. Bảng kẻ tấn công A0–A3 và lựa chọn T hoặc E kèm phép kiểm bác bỏ (B1).
2. Gỡ bỏ handshake ở ROOT §4.1, hoặc đưa ra chứng minh hình thức (B2).
3. Đặc tả trust anchor và rotation của khóa server (B3).
4. Profile cho máy, `command_id` bền, bind `poll_nonce` (B4, M1).
5. Một cơ chế xác thực duy nhất, có ADR (B5).
6. Gỡ Redis khỏi ROOT; đặc tả replay theo profile đã chọn (H1).
7. State machine của ledger có `unknown` và 4 điểm crash (H2).
8. Bảng byte AAD, route ID, status bên trong (H3, H4).
9. Các mô hình định lượng ở trên, viết dưới dạng công thức có giả định, không ghi số đo nếu chưa đo.
10. Sửa ROOT HTML hoặc đánh dấu là đã bị thay thế, để không còn hai bộ tài liệu mâu thuẫn.
