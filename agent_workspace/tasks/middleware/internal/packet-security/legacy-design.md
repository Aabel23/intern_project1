# Bản thiết kế cũ — lưu đối chiếu, KHÔNG LÀ ĐẶC TẢ HIỆN HÀNH

Nguồn: CRYPTOGRAPHY_MIDDLEWARE_DESIGN.html trước vòng review 06/10/2026. Giữ nội
dung người dùng đã chỉnh để đối chiếu. [Thiết kế chính](design.md) thay các quyết
định handshake/DPoP/Redis/replay/idempotency trong bản này.

FlexMix · Tài liệu thiết kế · 06/10/2026

# Cryptography Middleware cho HTTP API

Đề xuất giao thức mã hóa và xác thực giữa app Flutter và API server, kèm ranh giới tin cậy, hợp đồng gói tin và lộ trình tích hợp với code hiện tại.

**Trạng thái:** Tài liệu thiết kế để thẩm định; chưa phải tính năng đã triển khai hoặc chứng nhận tuân thủ ngân hàng. Mọi kết luận về mức bảo đảm cần threat model, kiểm thử độc lập và quy trình vận hành khóa.

## 1 · Bức tranh toàn cục

Đọc từ trái sang phải: **app chuẩn bị yêu cầu → HTTPS chuyển yêu cầu → server kiểm tra bảo mật → tính năng kiểm quyền và xử lý**. Tên khối mô tả công việc; thuật toán chi tiết giữ ở mục 4.

### Yêu cầu đi từ app đến nơi xử lý như thế nào?

```
<svg aria-label="Sơ đồ ranh giới mật mã đề xuất: app giữ khóa ký thiết bị và X25519 tạm; HTTPS TLS 1.3 tới server; middleware xác minh DPoP, giải mã AES-GCM, chống replay rồi mới gọi feature; SQLite giữ binding, Redis giữ replay; máy có giao thức riêng." role="img" viewbox="0 0 1120 500" width="1120">
<defs><marker id="crypto-ov-arrow" markerheight="7" markerwidth="7" orient="auto" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0 0 10 5 0 10Z" fill="var(--accent)"></path></marker></defs>
<text class="phase-label" x="24" y="22">APP ANDROID</text><text class="phase-label" x="292" y="22">BIÊN HTTPS</text><text class="phase-label" x="560" y="22">SERVER PYTHON · MIỀN TIN CẬY</text><text class="phase-label" x="858" y="22">DỮ LIỆU / NGHIỆP VỤ</text>
<rect class="ui" height="274" rx="10" width="235" x="20" y="38"></rect><text class="head" text-anchor="middle" x="137" y="65">App chuẩn bị yêu cầu</text>
<rect class="store" height="66" rx="6" width="199" x="38" y="85"></rect><text text-anchor="middle" x="137" y="111">Khóa ký thiết bị</text><text class="small" text-anchor="middle" x="137" y="131">kiểm chứng nơi bảo vệ khóa</text>
<rect class="store" height="66" rx="6" width="199" x="38" y="168"></rect><text text-anchor="middle" x="137" y="194">Khóa mã hóa của phiên</text><text class="small" text-anchor="middle" x="137" y="214">gửi và nhận dùng hai khóa riêng</text>
<text class="small" text-anchor="middle" x="137" y="274">ví dụ: gửi nội dung menu mới</text>
<rect class="proc" height="187" rx="10" width="220" x="288" y="82"></rect><text class="head" text-anchor="middle" x="398" y="112">Kênh HTTPS an toàn</text><text text-anchor="middle" x="398" y="145">kiểm tra đúng máy chủ</text><text text-anchor="middle" x="398" y="177">token + bằng chứng giữ khóa</text><text text-anchor="middle" x="398" y="209">gói yêu cầu đã mã hóa</text><text class="small" text-anchor="middle" x="398" y="244">bảo vệ dữ liệu trên đường truyền</text>
<rect class="proc" height="274" rx="10" width="278" x="542" y="38"></rect><text class="head" text-anchor="middle" x="681" y="65">Lớp kiểm tra và mã hóa</text>
<rect class="store" height="46" rx="6" width="238" x="562" y="88"></rect><text text-anchor="middle" x="681" y="116">Kiểm phiên và khóa thiết bị</text>
<rect class="store" height="46" rx="6" width="238" x="562" y="150"></rect><text text-anchor="middle" x="681" y="178">Giải mã · kiểm ký · chống gửi lại</text>
<rect class="store" height="46" rx="6" width="238" x="562" y="212"></rect><text text-anchor="middle" x="681" y="240">Mã hóa kết quả trả về</text>
<text class="small" text-anchor="middle" x="681" y="289">server đọc dữ liệu sau giải mã</text>
<rect class="store" height="274" rx="10" width="242" x="854" y="38"></rect><text class="head" text-anchor="middle" x="975" y="65">Xử lý và lưu dữ liệu</text>
<rect class="store" height="50" rx="6" width="202" x="874" y="85"></rect><text text-anchor="middle" x="975" y="114">Kho phiên và khóa công khai</text>
<rect class="store" height="50" rx="6" width="202" x="874" y="149"></rect><text text-anchor="middle" x="975" y="178">Kho ID yêu cầu đã dùng</text>
<rect class="store" height="50" rx="6" width="202" x="874" y="213"></rect><text text-anchor="middle" x="975" y="242">Tính năng kiểm quyền và xử lý</text>
<path class="edge" d="M255 175H282" marker-end="url(#crypto-ov-arrow)"></path><path class="edge" d="M508 175H536" marker-end="url(#crypto-ov-arrow)"></path><path class="edge" d="M820 175H848" marker-end="url(#crypto-ov-arrow)"></path>
<rect class="device" height="73" rx="9" width="1076" x="20" y="345"></rect><text class="head" text-anchor="middle" x="558" y="372">Luồng Raspberry Pi và đọc trạng thái: thiết kế riêng</text><text class="small" text-anchor="middle" x="558" y="397">Luồng máy báo còn hoạt động, chờ lệnh và đọc trạng thái cần quy tắc tích hợp riêng.</text>
<path class="edge dash" d="M975 312V328H681V318" marker-end="url(#crypto-ov-arrow)"></path>
<path class="edge dash" d="M681 312V336H137V318" marker-end="url(#crypto-ov-arrow)"></path>
<text class="small" text-anchor="middle" x="560" y="465">Chiều về (nét đứt): tính năng → lớp bảo vệ mã hóa kết quả → HTTPS → app giải mã</text>
</svg>
```

Đây là **thiết kế đề xuất, chưa triển khai**. Middleware bảo vệ app ↔ dịch vụ xử lý; HTTPS vẫn bắt buộc. Chữ ký, mã hóa và DPoP không thay thế kiểm quyền chủ máy/nhân viên trong module nghiệp vụ.

**Chú giải:** Xanh dương = app; cam = kênh truyền và lớp bảo vệ đề xuất; trắng = chức năng hoặc kho dữ liệu; tím = luồng máy cần thiết kế riêng. Mũi tên liền là chiều gửi; nét đứt là chiều trả kết quả. Tính năng nghiệp vụ là hiện có; lớp bảo vệ mật mã là đề xuất.

### Ví dụ: bạn bấm “Lưu menu”

1. **App chuẩn bị yêu cầu:** lấy nội dung menu, ký bằng khóa thiết bị và mã hóa bằng khóa gửi của phiên. Khóa ký chứng minh quyền giữ khóa; khóa mã hóa che nội dung. Hai loại khóa có nhiệm vụ khác nhau.
2. **Kênh HTTPS an toàn:** app kiểm chứng chỉ và tên máy chủ trước khi gửi. HTTPS bảo vệ đường truyền; gói mã hóa bên trong là lớp bảo vệ bổ sung. Khối này biểu thị kênh truyền, không phải một module nghiệp vụ riêng.
3. **Lớp kiểm tra và mã hóa:** server kiểm phiên và bằng chứng giữ khóa thiết bị (DPoP), giải mã, kiểm chữ ký và xác nhận ID yêu cầu chưa từng được dùng. Kiểm tra thất bại thì dừng, không gọi tính năng.
4. **Xử lý và lưu dữ liệu:** tính năng menu kiểm bạn có quyền sửa máy này hay không rồi mới cập nhật. Qua kiểm tra bảo mật chưa có nghĩa là được phép thực hiện thao tác.
5. **Trả kết quả:** tính năng trả kết quả cho lớp bảo vệ; lớp này mã hóa bằng khóa nhận của phiên rồi gửi qua HTTPS. App giải mã và hiển thị. Lỗi sau xác thực cũng được mã hóa; lỗi trước khi biết khóa phiên trả thông báo tối giản qua HTTPS.

| Tên dễ đọc | Tên kỹ thuật | Vai trò |
| --- | --- | --- |
| App chuẩn bị yêu cầu | Flutter transport chung | Đóng gói, ký, mã hóa và gửi yêu cầu cho các tính năng. |
| Kênh HTTPS an toàn | TLS 1.3 | Bảo vệ kênh vận chuyển và kiểm tra đúng máy chủ. |
| Lớp kiểm tra và mã hóa | Crypto middleware | Đứng trước tính năng; đề xuất dùng AES-GCM để mã hóa và Ed25519 để kiểm chữ ký. |
| Kho phiên và khóa công khai | SQLite · phiên / public key | Lưu phiên và liên kết người dùng, thiết bị, khóa. Khóa ký riêng của app không gửi lên server. |
| Kho ID yêu cầu đã dùng | Redis · replay jti | Nhớ ID trong cửa sổ chống phát lại; không thay bản ghi bền vững để tránh thực hiện trùng thao tác khi gửi lại hợp lệ. |
| Tính năng kiểm quyền và xử lý | Module nghiệp vụ hiện tại | Kiểm quyền chủ máy/nhân viên và thực hiện tác vụ cụ thể. |

Nguồn giải thích: thiết kế trong tài liệu này, không phải kết quả kiểm thử triển khai. Lần chỉnh sửa này đổi nhãn và bổ sung cách đọc sơ đồ tổng quan, giữ nguyên giao thức; chưa đối chiếu hình thức với PDF mẫu.

**Mục lục**
[1 · Tổng quan](#overview)[2 · Đánh giá bản nháp](#assessment)[3 · Phạm vi](#scope)[4 · Giao thức](#profile)[5 · Luồng xử lý](#flow)[6 · Tích hợp repo](#integration)[7 · Vận hành](#operation)[8 · Nghiệm thu](#acceptance)[9 · Nguồn](#sources)


## 2 · Đánh giá và điều chỉnh bản thiết kế ban đầu

| Ý tưởng ban đầu | Đánh giá / quyết định thiết kế |
| --- | --- |
| “E2EE” khi server giải mã | Đây là mã hóa từ app đến *dịch vụ xử lý tin cậy*. Nếu gateway, proxy hoặc log giải mã được payload, không còn bảo mật đầu cuối tới dịch vụ đó. Server vẫn nhìn thấy plaintext để xử lý nghiệp vụ. |
| JWT + token đưa vào chữ ký gọi là DPoP | [DPoP RFC 9449](https://www.rfc-editor.org/rfc/rfc9449.html) là proof JWT riêng với `htm`, `htu`, `iat`, `jti`, `ath`; access token phải gắn với public key qua `cnf.jkt` hoặc bản ghi phiên tương đương. Ký chuỗi tự tạo có token không tự động thành DPoP. |
| Timestamp + Redis SETNX = idempotency | Chúng chống phát lại trong cửa sổ ngắn. Idempotency nghiệp vụ, nhất là thanh toán, cần khóa và kết quả bền vững trong cùng transaction nghiệp vụ; hết TTL 60 giây không được phép thực hiện lại lệnh. |
| ECDH lúc đăng nhập = PFS | Chỉ đạt bảo mật chuyển tiếp cho phiên cũ nếu cả hai phía dùng khóa ECDH tạm thời, xác thực transcript, xóa secret tạm thời và hủy khóa phiên sau vòng đời. Khóa phiên còn hoạt động hoặc bị sao lưu vẫn có thể giải mã lưu lượng phiên đó. |
| Ghi đè `res.json` | Repo dùng Python `http.server`, không có Express `res.json`. Cần một lớp bao quanh đọc request và ghi response tại HTTP transport chung. |
| “Chống chối bỏ” tuyệt đối | Chữ ký chỉ chứng minh một khóa đã ký; ràng buộc khóa với người, thiết bị, thời điểm, chống chiếm thiết bị và lưu chứng cứ quyết định giá trị pháp lý. Không thể hứa “an toàn tuyệt đối”. |

## 3 · Phạm vi và ranh giới tin cậy

### Mục tiêu bảo vệ

Payload request/response bí mật và toàn vẹn; token bị đánh cắp riêng lẻ không dùng được; request cũ không chạy lại; mỗi yêu cầu được gắn với phiên, thiết bị và khóa ký.

### Giả định bắt buộc

HTTPS với TLS 1.3 tại biên; app xác minh chứng chỉ và tên máy chủ; máy chủ thời gian được đồng bộ; CSPRNG và thư viện mật mã được kiểm định; khóa riêng app lưu bằng cơ chế bảo vệ của hệ điều hành.

### Ngoài phạm vi của middleware

Thiết bị bị root hoặc malware điều khiển, server ứng dụng bị chiếm, lỗi phân quyền nghiệp vụ, metadata HTTP như IP, thời điểm và kích thước gần đúng. Attestation chỉ cung cấp tín hiệu rủi ro tại thời điểm kiểm tra; padding chỉ giảm một phần rò rỉ kích thước.

HTTPS là lớp bắt buộc ngay cả khi payload được mã hóa ở tầng ứng dụng. Không bật HTTP plaintext ngoài môi trường phát triển cách ly. TLS 1.3 cung cấp trao đổi khóa tạm thời cho kênh vận chuyển; mã hóa tầng ứng dụng chỉ có ý nghĩa bổ sung khi cần bảo vệ payload qua một số lớp trung gian hoặc cần bằng chứng gắn với khóa thiết bị. Xem [RFC 8446](https://www.rfc-editor.org/rfc/rfc8446.html).

## 4 · Profile giao thức đề xuất: `flexmix-secure-v1`

Chọn một bộ thuật toán cố định cho v1 để tránh hạ cấp: **Ed25519** cho chữ ký, **X25519 + HKDF-SHA-256** cho thỏa thuận/derivation khóa, **AES-256-GCM** với nonce 96 bit và tag 128 bit cho dữ liệu. Có thể thay profile sau qua phiên bản mới và kiểm thử tương thích. Ed25519 và X25519 dùng *hai cặp khóa khác nhau*.

### 4.1 · Đăng ký thiết bị và thiết lập phiên

```
<svg aria-label="Sơ đồ khối thiết lập phiên: xác thực TLS, đăng ký public key Ed25519, tạo X25519 tạm ở hai phía, xác minh transcript có nhánh từ chối, HKDF sinh hai khóa, cấp token bound với khóa thiết bị." role="img" viewbox="0 0 1000 760" width="1000">
<defs><marker id="crypto-handshake-arrow" markerheight="7" markerwidth="7" orient="auto" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0 0 10 5 0 10Z" fill="var(--accent)"></path></marker></defs>
<rect class="ui" height="52" rx="7" width="260" x="370" y="20"></rect><text class="head" text-anchor="middle" x="500" y="51">App đăng nhập qua TLS</text>
<path class="edge" d="M500 72V103" marker-end="url(#crypto-handshake-arrow)"></path>
<polygon class="warn" points="500,110 630,160 500,210 370,160"></polygon><text text-anchor="middle" x="500" y="155">TLS + danh tính</text><text text-anchor="middle" x="500" y="173">hợp lệ?</text>
<path class="edge" d="M630 160H790" marker-end="url(#crypto-handshake-arrow)"></path><text class="edge-label" text-anchor="middle" x="711" y="150">Không</text>
<rect class="bad" height="52" rx="7" width="180" x="795" y="134"></rect><text text-anchor="middle" x="885" y="164">Từ chối thiết lập</text>
<path class="edge" d="M500 210V240" marker-end="url(#crypto-handshake-arrow)"></path><text class="edge-label" x="525" y="230">Có</text>
<rect class="proc" height="58" rx="7" width="320" x="340" y="245"></rect><text text-anchor="middle" x="500" y="270">App đăng ký public key Ed25519</text><text class="small" text-anchor="middle" x="500" y="289">server lưu user/device/key ID, trạng thái thu hồi</text>
<path class="edge" d="M500 303V331H245V348" marker-end="url(#crypto-handshake-arrow)"></path><path class="edge" d="M500 331H755V348" marker-end="url(#crypto-handshake-arrow)"></path>
<rect class="ui" height="62" rx="7" width="280" x="105" y="353"></rect><text text-anchor="middle" x="245" y="379">App tạo X25519 tạm</text><text class="small" text-anchor="middle" x="245" y="398">gửi ephemeral public key</text>
<rect class="proc" height="62" rx="7" width="280" x="615" y="353"></rect><text text-anchor="middle" x="755" y="379">Server tạo X25519 tạm</text><text class="small" text-anchor="middle" x="755" y="398">ký transcript + trả public key</text>
<path class="edge" d="M245 415V443H500V456" marker-end="url(#crypto-handshake-arrow)"></path><path class="edge" d="M755 415V443H500"></path>
<polygon class="warn" points="500,463 640,513 500,563 360,513"></polygon><text text-anchor="middle" x="500" y="508">App xác minh TLS +</text><text text-anchor="middle" x="500" y="526">chữ ký transcript?</text>
<path class="edge" d="M640 513H790" marker-end="url(#crypto-handshake-arrow)"></path><text class="edge-label" text-anchor="middle" x="715" y="502">Sai</text>
<rect class="bad" height="52" rx="7" width="180" x="795" y="487"></rect><text text-anchor="middle" x="885" y="518">Hủy phiên</text>
<path class="edge" d="M500 563V593" marker-end="url(#crypto-handshake-arrow)"></path><text class="edge-label" x="528" y="584">Đúng</text>
<rect class="proc" height="62" rx="7" width="320" x="340" y="598"></rect><text text-anchor="middle" x="500" y="624">Hai phía ECDH + HKDF</text><text class="small" text-anchor="middle" x="500" y="644">K_request ≠ K_response; xóa secret tạm</text>
<path class="edge" d="M500 660V689" marker-end="url(#crypto-handshake-arrow)"></path>
<rect class="good" height="50" rx="7" width="320" x="340" y="694"></rect><text text-anchor="middle" x="500" y="724">Cấp token bound với khóa thiết bị</text>
</svg>
```

Đây là **profile đề xuất**. Ed25519 ký và X25519 thỏa thuận khóa dùng hai cặp khóa riêng. Bắt tay cần thư viện giao thức đáng tin cậy; không suy ra PFS chỉ từ ECDH.

1. Sau khi xác thực người dùng qua TLS, app tạo khóa ký Ed25519 riêng cho thiết bị; đăng ký public key qua luồng xác thực. Server lưu `user_id`, `device_id`, `key_id`, public key, trạng thái thu hồi. Khóa riêng không đi lên server. Khi chốt profile Android, kiểm tra trên thiết bị mục tiêu khả năng tạo và dùng đúng thuật toán trong Android Keystore, mức bảo vệ phần cứng và khả năng attestation; không suy ra Ed25519 được bảo vệ bằng phần cứng chỉ vì API mật mã hỗ trợ Ed25519. Nếu profile Ed25519 không đáp ứng mức bảo vệ yêu cầu, chọn profile ký có phiên bản riêng được Keystore hỗ trợ (ví dụ ES256) và cập nhật đồng bộ DPoP, chữ ký payload, binding, test vector; không đổi thuật toán ngầm trong cùng profile.
2. App và server tạo mỗi bên một cặp X25519 **tạm thời cho phiên**. Server ký transcript bắt tay bằng khóa định danh server đã được app tin cậy qua quy trình cấp phát và xoay khóa; transcript gồm version, hai ephemeral public key, session ID, user/device/key ID và ngữ cảnh phiên. App xác minh chữ ký và TLS trước khi chấp nhận khóa.
3. Hai phía tính ECDH shared secret rồi HKDF với salt/context gắn transcript để sinh `K_request` và `K_response` 32 byte độc lập. Xóa ephemeral private key và shared secret sau derivation. Lưu key phiên đang hoạt động trong vùng bảo vệ, có TTL và giới hạn số lần mã hóa.
4. Server cấp access token ràng buộc với thumbprint của public key ký thiết bị. Profile này có thể dùng token mờ (opaque) và tra binding trong DB, hoặc JWT ký hợp lệ với `cnf.jkt`; không cần đổi sang JWT chỉ để dùng DPoP.

Bắt tay ECDH trên TLS phải được thiết kế và kiểm thử bằng thư viện giao thức đáng tin cậy; không ghép thông điệp tùy ý rồi tuyên bố có PFS. Nếu không có yêu cầu bảo mật payload sau TLS termination, TLS 1.3 + DPoP có thể là phiên bản triển khai đầu tiên.

### 4.2 · Request được bảo vệ

| Thành phần | Định nghĩa và kiểm tra |
| --- | --- |
| `Authorization: DPoP <token>` | Token access bound với public key của thiết bị; không đưa token vào body JSON. |
| `DPoP: <proof JWT>` | Header `typ=dpop+jwt`, `alg=EdDSA`, JWK công khai; claims `htm`, `htu`, `iat`, `jti`, `ath` theo RFC 9449. Server so khớp thumbprint với phiên; `jti` bằng request ID. |
| `X-Request-ID`, `X-Timestamp` | ID ngẫu nhiên tối thiểu 128 bit; thời gian UTC dạng Unix seconds. Ràng buộc các giá trị này trong AAD và chữ ký ứng dụng. |
| `Content-Type` | `application/vnd.flexmix.secure+json`; server từ chối profile lạ, field thừa và header bảo mật lặp. |
| Body | JSON envelope gồm `v`, `sid`, `nonce`, `ciphertext`, `tag`; byte nhị phân mã hóa base64url không padding. Giới hạn kích thước trước parse và giải mã. |

```
POST /app/cap-nhat-menu HTTP/1.1
Authorization: DPoP <opaque-access-token>
DPoP: <signed-proof-jwt>
X-Request-ID: <random-128-bit-base64url>
X-Timestamp: 1791264000
Content-Type: application/vnd.flexmix.secure+json

{"v":1,"sid":"<session-id>","nonce":"<base64url-12-byte>",
 "ciphertext":"<base64url>","tag":"<base64url-16-byte>"}
```

Plaintext trước mã hóa chứa `{"payload_b64":"...","signature_b64":"..."}`. `payload_b64` là byte UTF-8 JSON nghiệp vụ gốc; signature Ed25519 ký digest của **byte gốc** cùng metadata có phân định rõ. V1 chỉ cho POST không có query string trên route bảo vệ; GET và query được chuẩn hóa ở profile kế tiếp. Không ký chuỗi nối tự do `Method + URL + ...` vì có thể mơ hồ và khác nhau giữa Python/Dart.

```
signed_fields = ["flexmix-secure-v1", "req", method, path,
                 timestamp, request_id, session_id,
                 base64url(SHA256(access_token)),
                 base64url(SHA256(payload_bytes))]
signing_input = UTF8(join(".", map(base64url_utf8, signed_fields)))
signature = Ed25519.sign(device_private_key, signing_input)
aad = signing_input_without_payload_digest  // cùng quy tắc mã hóa, nhãn "aad"
{ciphertext, tag} = AES-256-GCM.encrypt(K_request, nonce, plaintext, aad)
```

Các thành phần `base64url_utf8` chỉ chứa chữ, số, `-`, `_`, nên dấu chấm phân tách không mơ hồ. AAD phải có nhãn miền riêng, cùng version, hướng, method, path, timestamp, request ID, session ID và hash token; không dùng lại byte chữ ký như AAD. Viết test vector byte chính xác cho Dart/Python trước khi triển khai.

### 4.3 · Nonce, replay và idempotency

### Chống phát lại một request

```
<svg aria-label="Sơ đồ khối chống replay: xác thực mật mã trước; sai thì từ chối không chiếm jti; đúng thì Redis SET NX; jti cũ hoặc Redis lỗi thì từ chối; jti mới vào nghiệp vụ." role="img" viewbox="0 0 900 870" width="900"><defs><marker id="replay-arrow" markerheight="7" markerwidth="7" orient="auto" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0 0 10 5 0 10Z" fill="var(--accent)"></path></marker></defs>
<rect class="ui" height="60" rx="7" width="300" x="300" y="30"></rect><text text-anchor="middle" x="450" y="65">Request ID + timestamp + DPoP</text><path class="edge" d="M450 90V142" marker-end="url(#replay-arrow)"></path>
<rect class="proc" height="75" rx="7" width="360" x="270" y="150"></rect><text text-anchor="middle" x="450" y="181">Token · proof · GCM · Ed25519</text><text class="small" text-anchor="middle" x="450" y="202">xác minh trước khi ghi replay</text><path class="edge" d="M450 225V272" marker-end="url(#replay-arrow)"></path>
<polygon class="warn" points="450,280 610,345 450,410 290,345"></polygon><text text-anchor="middle" x="450" y="350">Hợp lệ?</text>
<path class="edge" d="M290 345H140V472" marker-end="url(#replay-arrow)"></path><text class="edge-label" x="208" y="334">Không</text><rect class="bad" height="70" rx="7" width="200" x="40" y="480"></rect><text text-anchor="middle" x="140" y="508">Từ chối</text><text class="small" text-anchor="middle" x="140" y="530">không chiếm jti</text>
<path class="edge" d="M450 410V472" marker-end="url(#replay-arrow)"></path><text class="edge-label" x="472" y="449">Có</text><rect class="store" height="65" rx="7" width="300" x="300" y="480"></rect><text text-anchor="middle" x="450" y="518">Redis SET NX theo jti</text><path class="edge" d="M450 545V582" marker-end="url(#replay-arrow)"></path>
<polygon class="warn" points="450,590 610,650 450,710 290,650"></polygon><text text-anchor="middle" x="450" y="655">jti mới?</text>
<path class="edge" d="M290 650H140V752" marker-end="url(#replay-arrow)"></path><text class="edge-label" x="198" y="638">Cũ / Redis lỗi</text><rect class="bad" height="65" rx="7" width="200" x="40" y="760"></rect><text text-anchor="middle" x="140" y="798">Từ chối request</text>
<path class="edge" d="M610 650H760V752" marker-end="url(#replay-arrow)"></path><text class="edge-label" x="686" y="638">Mới</text><rect class="good" height="65" rx="7" width="200" x="660" y="760"></rect><text text-anchor="middle" x="760" y="798">Vào nghiệp vụ</text>
</svg>
```

Replay cache dùng chung mọi replica; Redis lỗi thì route bảo vệ từ chối.



### Retry hợp lệ của thao tác ghi

```
<svg aria-label="Sơ đồ khối idempotency: tra khóa bền vững trong transaction; khóa chưa có thì thực hiện và lưu kết quả; đã có thì so hash payload, giống trả kết quả cũ, khác trả 409." role="img" viewbox="0 0 900 870" width="900"><defs><marker id="idem-arrow" markerheight="7" markerwidth="7" orient="auto" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0 0 10 5 0 10Z" fill="var(--accent)"></path></marker></defs>
<rect class="ui" height="60" rx="7" width="300" x="300" y="30"></rect><text text-anchor="middle" x="450" y="65">Retry + idempotency_key</text><path class="edge" d="M450 90V137" marker-end="url(#idem-arrow)"></path>
<rect class="store" height="70" rx="7" width="340" x="280" y="145"></rect><text text-anchor="middle" x="450" y="175">Tra khóa bền vững</text><text class="small" text-anchor="middle" x="450" y="196">trong transaction nghiệp vụ</text><path class="edge" d="M450 215V252" marker-end="url(#idem-arrow)"></path>
<polygon class="warn" points="450,260 610,320 450,380 290,320"></polygon><text text-anchor="middle" x="450" y="325">Khóa đã có?</text>
<path class="edge" d="M290 320H150V442" marker-end="url(#idem-arrow)"></path><text class="edge-label" x="215" y="308">Chưa</text><rect class="proc" height="75" rx="7" width="220" x="40" y="450"></rect><text text-anchor="middle" x="150" y="481">Thực hiện tác vụ</text><text class="small" text-anchor="middle" x="150" y="503">lưu kết quả cùng transaction</text>
<path class="edge" d="M450 380V457" marker-end="url(#idem-arrow)"></path><text class="edge-label" x="472" y="420">Có</text><polygon class="warn" points="450,465 610,525 450,585 290,525"></polygon><text text-anchor="middle" x="450" y="520">Hash payload</text><text text-anchor="middle" x="450" y="539">giống?</text>
<path class="edge" d="M150 525V672" marker-end="url(#idem-arrow)"></path><rect class="good" height="65" rx="7" width="220" x="40" y="680"></rect><text text-anchor="middle" x="150" y="718">Trả kết quả mới</text>
<path class="edge" d="M450 585V672" marker-end="url(#idem-arrow)"></path><text class="edge-label" x="472" y="634">Khác</text><rect class="bad" height="65" rx="7" width="240" x="330" y="680"></rect><text text-anchor="middle" x="450" y="718">HTTP 409</text>
<path class="edge" d="M610 525H770V672" marker-end="url(#idem-arrow)"></path><text class="edge-label" x="686" y="513">Giống</text><rect class="good" height="65" rx="7" width="220" x="660" y="680"></rect><text text-anchor="middle" x="770" y="718">Trả kết quả cũ</text>
<text class="small" text-anchor="middle" x="450" y="816">Request ID chống replay khác khóa idempotency.</text>
</svg>
```

TTL ngắn của replay cache không thay thế bản ghi idempotency bền vững.

* Nonce AES-GCM tạo bằng CSPRNG, 96 bit, **không được lặp với cùng key**. Hai chiều dùng key khác nhau; xoay key trước 220 lần mã hóa mỗi chiều hoặc khi hết TTL, tùy điều kiện nào tới trước. Giới hạn này là chính sách v1 bảo thủ, phải xác nhận bằng phân tích lưu lượng thực tế.
* Chấp nhận proof trong cửa sổ ví dụ ±60 giây nếu đồng hồ đồng bộ. Nếu đồng hồ di động lệch nhiều, dùng `DPoP-Nonce` do server phát theo RFC 9449; thông báo thời gian server và retry an toàn.
* Chỉ sau khi xác thực token, proof, tag và chữ ký mới đánh dấu `jti` đã dùng bằng Redis `SET key value NX EX ttl`. Key có namespace theo token/key ID và hash request ID, TTL dài hơn toàn bộ khoảng proof có thể được nhận. Redis lỗi thì từ chối các route bảo vệ; không tự động cho qua.
* Với thao tác ghi có hiệu ứng tài chính, lưu `idempotency_key`, hash payload, trạng thái và kết quả trong kho bền vững cùng transaction nghiệp vụ. Retry cùng khóa và cùng payload trả kết quả cũ; cùng khóa nhưng payload khác trả 409. Request ID chống replay *khác* khóa idempotency cho retry hợp lệ.

### 4.4 · Response và padding

Server mã hóa **cả thành công và lỗi sau xác thực** bằng `K_response` và nonce mới. AAD response gắn version, nhãn `res`, method/path, request ID, session ID và HTTP status; app xác minh tag trước khi parse JSON. Lỗi xảy ra trước khi biết session key trả mã lỗi tối giản qua TLS, không phản chiếu token, proof hoặc chi tiết xác thực. Response có thể ký bằng khóa server khi cần chứng cứ hai chiều; AES-GCM một mình chỉ chứng minh bên giữ session key đã tạo dữ liệu.

Padding đặt *bên trong plaintext trước mã hóa* theo các bucket kích thước có giới hạn (ví dụ 256/512/1024 byte), ghi chiều dài payload thật trong phần được mã hóa. Giới hạn payload lớn, đo overhead và tránh nén trước mã hóa trên dữ liệu có lẫn secret do rủi ro rò rỉ độ dài. Padding không che metadata hoặc thời điểm request.

### 4.5 · Xác nhận thao tác nhạy cảm

### Luồng bảo vệ thao tác nhạy cảm

```
<svg aria-label="Sơ đồ khối: request qua HTTPS và middleware; route nhạy cảm nhận challenge gắn với thao tác; người dùng xác nhận trên app; server kiểm proof dùng một lần và quyền nghiệp vụ trước khi thực hiện và ghi audit; nhánh sai bị từ chối." role="img" viewbox="0 0 1040 790" width="1040">
<defs><marker id="sensitive-arrow" markerheight="7" markerwidth="7" orient="auto" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0 0 10 5 0 10Z" fill="var(--accent)"></path></marker></defs>
<text class="phase-label" x="24" y="24">APP / NGƯỜI DÙNG</text><text class="phase-label" x="385" y="24">MIDDLEWARE + SERVER</text><text class="phase-label" x="805" y="24">NGHIỆP VỤ</text>
<rect class="ui" height="70" rx="8" width="270" x="25" y="55"></rect><text text-anchor="middle" x="160" y="84">Gửi thao tác qua HTTPS</text><text class="small" text-anchor="middle" x="160" y="105">token + DPoP + request ID mới</text>
<rect class="proc" height="70" rx="8" width="330" x="380" y="55"></rect><text text-anchor="middle" x="545" y="84">Kiểm token, chữ ký, replay</text><text class="small" text-anchor="middle" x="545" y="105">và giải mã request</text>
<path class="edge" d="M295 90H374" marker-end="url(#sensitive-arrow)"></path><path class="edge" d="M545 125V155" marker-end="url(#sensitive-arrow)"></path>
<polygon class="warn" points="545,160 700,210 545,260 390,210"></polygon><text text-anchor="middle" x="545" y="206">Route nhạy cảm?</text>
<path class="edge" d="M700 210H910V341" marker-end="url(#sensitive-arrow)"></path><text class="edge-label" x="748" y="199">Không</text>
<rect class="proc" height="72" rx="8" width="330" x="380" y="292"></rect><text text-anchor="middle" x="545" y="318">Tạo challenge dùng một lần</text><text class="small" text-anchor="middle" x="545" y="341">gắn người, máy, thao tác, hash tham số</text>
<path class="edge" d="M545 260V286" marker-end="url(#sensitive-arrow)"></path><text class="edge-label" x="566" y="278">Có</text>
<rect class="ui" height="130" rx="8" width="270" x="25" y="292"></rect><text text-anchor="middle" x="160" y="320">Hiển thị nội dung xác nhận</text><text text-anchor="middle" x="160" y="343">Sinh trắc học / khóa màn hình</text><text class="small" text-anchor="middle" x="160" y="369">khóa riêng cho thao tác nhạy cảm</text><text class="small" text-anchor="middle" x="160" y="390">ký challenge sau xác thực</text>
<path class="edge" d="M374 328H301" marker-end="url(#sensitive-arrow)"></path><path class="edge" d="M295 392H335V457H374" marker-end="url(#sensitive-arrow)"></path>
<rect class="proc" height="72" rx="8" width="330" x="380" y="430"></rect><text text-anchor="middle" x="545" y="456">Kiểm proof và challenge</text><text class="small" text-anchor="middle" x="545" y="479">TTL · binding · hash · dùng một lần</text>
<path class="edge" d="M545 502V526" marker-end="url(#sensitive-arrow)"></path>
<polygon class="warn" points="545,532 700,580 545,628 390,580"></polygon><text text-anchor="middle" x="545" y="576">Xác nhận hợp lệ?</text>
<path class="edge" d="M390 580H305" marker-end="url(#sensitive-arrow)"></path><text class="edge-label" x="342" y="570">Không</text><rect class="bad" height="65" rx="8" width="270" x="25" y="548"></rect><text text-anchor="middle" x="160" y="586">Từ chối · không thực hiện</text>
<path class="edge" d="M700 580H750V381H799" marker-end="url(#sensitive-arrow)"></path><text class="edge-label" x="724" y="570">Có</text>
<rect class="good" height="68" rx="8" width="210" x="805" y="347"></rect><text text-anchor="middle" x="910" y="375">Kiểm quyền nghiệp vụ</text><text class="small" text-anchor="middle" x="910" y="396">chủ máy / nhân viên</text>
<path class="edge" d="M910 415V460" marker-end="url(#sensitive-arrow)"></path>
<rect class="good" height="68" rx="8" width="210" x="805" y="466"></rect><text text-anchor="middle" x="910" y="493">Thực hiện thao tác</text><text class="small" text-anchor="middle" x="910" y="515">nếu còn quyền hợp lệ</text>
<path class="edge" d="M910 534V636H545V658" marker-end="url(#sensitive-arrow)"></path>
<rect class="store" height="72" rx="8" width="330" x="380" y="664"></rect><text text-anchor="middle" x="545" y="691">Ghi audit và trả kết quả</text><text class="small" text-anchor="middle" x="545" y="714">không ghi token hoặc dữ liệu nhạy cảm thô</text>
</svg>
```

Request thường đi thẳng tới kiểm quyền nghiệp vụ. Request nhạy cảm phải có xác nhận riêng cho đúng nội dung thao tác; mọi lần gửi lại dùng request ID mới.

Routing gắn nhãn các thao tác cần xác nhận bổ sung, ví dụ chia sẻ hoặc gỡ máy, đổi quyền và đổi thông tin bảo mật. Sau middleware, feature vẫn kiểm quyền hiện hành và yêu cầu một xác nhận mới cho đúng thao tác; chữ ký DPoP chỉ chứng minh quyền dùng khóa thiết bị, không chứng minh người dùng vừa đồng ý.

1. Server tạo challenge ngẫu nhiên dùng một lần, TTL ngắn, gắn với `user_id`, `device_id`, loại thao tác và hash của tham số đã chuẩn hóa. App hiển thị đúng nội dung cần xác nhận trước khi người dùng xác thực bằng sinh trắc học mạnh hoặc khóa màn hình; nếu dùng khóa Keystore yêu cầu xác thực cho từng lần ký, app ký challenge bằng khóa riêng dành cho thao tác nhạy cảm. Không dùng lại khóa DPoP tự động cho bước xác nhận này.
2. Server kiểm chữ ký, binding, thời hạn, hash tham số và trạng thái challenge; tiêu thụ challenge một cách nguyên tử trước khi chạy thao tác. Với thiết bị không hỗ trợ khóa xác thực mỗi lần dùng, chính sách fallback phải được định nghĩa riêng theo mức rủi ro, chẳng hạn xác thực lại với server; một cờ `biometric_ok` do app tự gửi không đủ làm bằng chứng.
3. Ghi audit cho kết quả xác nhận và thao tác: người dùng, thiết bị, key ID, loại thao tác, hash tham số, thời gian server và kết quả; tránh ghi secret hoặc dữ liệu nhạy cảm thô. Khóa dùng để xác nhận có vòng đời thu hồi riêng hoặc bị thu hồi cùng thiết bị.

### 4.6 · Tín hiệu toàn vẹn app và thiết bị

### Đăng ký khóa và đánh giá rủi ro thiết bị

```
<svg aria-label="Sơ đồ khối: app thử tạo khóa ký trong Android Keystore; server kiểm chứng khả năng bảo vệ và lưu public key; Play Integrity là tín hiệu rủi ro tùy chọn; chính sách route quyết định tiếp tục, xác nhận mạnh hơn hoặc từ chối." role="img" viewbox="0 0 1040 620" width="1040">
<defs><marker id="device-risk-arrow" markerheight="7" markerwidth="7" orient="auto" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0 0 10 5 0 10Z" fill="var(--accent)"></path></marker></defs>
<text class="phase-label" x="25" y="24">ĐĂNG KÝ THIẾT BỊ</text><text class="phase-label" x="542" y="24">REQUEST CẦN ĐÁNH GIÁ RỦI RO</text>
<rect class="ui" height="72" rx="8" width="290" x="25" y="56"></rect><text text-anchor="middle" x="170" y="84">App tạo khóa ký</text><text class="small" text-anchor="middle" x="170" y="106">thử đúng thuật toán trên thiết bị</text>
<path class="edge" d="M170 128V158" marker-end="url(#device-risk-arrow)"></path>
<rect class="proc" height="82" rx="8" width="290" x="25" y="164"></rect><text text-anchor="middle" x="170" y="192">Server kiểm attestation nếu có</text><text class="small" text-anchor="middle" x="170" y="214">challenge · chuỗi tin cậy · mức bảo vệ</text><text class="small" text-anchor="middle" x="170" y="232">và thuật toán thực tế</text>
<path class="edge" d="M170 246V274" marker-end="url(#device-risk-arrow)"></path>
<polygon class="warn" points="170,280 310,330 170,380 30,330"></polygon><text text-anchor="middle" x="170" y="326">Đạt chính sách</text><text text-anchor="middle" x="170" y="345">khóa thiết bị?</text>
<path class="edge" d="M310 330H393" marker-end="url(#device-risk-arrow)"></path><text class="edge-label" x="343" y="320">Không</text><rect class="bad" height="68" rx="8" width="175" x="400" y="296"></rect><text text-anchor="middle" x="487" y="324">Không đăng ký</text><text class="small" text-anchor="middle" x="487" y="345">hoặc profile riêng</text>
<path class="edge" d="M170 380V410" marker-end="url(#device-risk-arrow)"></path><text class="edge-label" x="191" y="401">Có</text>
<rect class="store" height="72" rx="8" width="290" x="25" y="416"></rect><text text-anchor="middle" x="170" y="444">Lưu public key + binding</text><text class="small" text-anchor="middle" x="170" y="466">user · device · key ID · thu hồi</text>
<rect class="ui" height="72" rx="8" width="300" x="620" y="56"></rect><text text-anchor="middle" x="770" y="84">Request đã qua DPoP</text><text class="small" text-anchor="middle" x="770" y="106">route rủi ro cao / đăng ký thiết bị</text>
<path class="edge" d="M770 128V158" marker-end="url(#device-risk-arrow)"></path>
<rect class="proc" height="82" rx="8" width="300" x="620" y="164"></rect><text text-anchor="middle" x="770" y="192">Play Integrity nếu áp dụng</text><text class="small" text-anchor="middle" x="770" y="214">verdict mới, gắn challenge</text><text class="small" text-anchor="middle" x="770" y="232">và ngữ cảnh thao tác</text>
<path class="edge" d="M770 246V274" marker-end="url(#device-risk-arrow)"></path>
<polygon class="warn" points="770,280 920,330 770,380 620,330"></polygon><text text-anchor="middle" x="770" y="326">Chính sách rủi ro</text><text text-anchor="middle" x="770" y="345">theo route?</text>
<path class="edge" d="M620 330H584V414" marker-end="url(#device-risk-arrow)"></path><text class="edge-label" x="585" y="319">Cho qua</text>
<rect class="good" height="68" rx="8" width="220" x="455" y="420"></rect><text text-anchor="middle" x="565" y="448">Tiếp tục kiểm quyền</text><text class="small" text-anchor="middle" x="565" y="469">và xử lý nghiệp vụ</text>
<path class="edge" d="M770 380V414" marker-end="url(#device-risk-arrow)"></path><text class="edge-label" x="791" y="402">Tăng xác nhận</text>
<rect class="warn" height="68" rx="8" width="230" x="690" y="420"></rect><text text-anchor="middle" x="805" y="448">Xác nhận thêm</text><text class="small" text-anchor="middle" x="805" y="469">theo sơ đồ thao tác nhạy cảm</text>
<path class="edge" d="M920 330H959V414" marker-end="url(#device-risk-arrow)"></path><text class="edge-label" x="930" y="320">Chặn</text>
<rect class="bad" height="68" rx="8" width="100" x="925" y="420"></rect><text text-anchor="middle" x="975" y="459">Từ chối</text>
<text class="small" text-anchor="middle" x="520" y="566">Play Integrity là tín hiệu rủi ro; quyền nghiệp vụ và khóa thiết bị vẫn được kiểm riêng.</text>
</svg>
```

Hai nhánh có vai trò khác nhau: khóa thiết bị chứng minh quyền giữ khóa; verdict toàn vẹn hỗ trợ quyết định rủi ro theo route.

Nếu phát hành qua Google Play, có thể kiểm tra Play Integrity tại đăng ký thiết bị và các thao tác rủi ro cao. App gắn `requestHash` hoặc nonce với challenge và ngữ cảnh thao tác; server xác minh verdict, đối chiếu giá trị ràng buộc và chỉ chấp nhận verdict còn mới. Lưu mức tin cậy và chính sách xử lý theo từng route: cho qua, yêu cầu xác nhận mạnh hơn hoặc từ chối. Không coi verdict là danh tính người dùng, quyền máy hoặc chứng cứ khóa Ed25519 nằm trong phần cứng; không lưu cache verdict để dùng lại cho thao tác khác. Thiết bị ngoài Google Play cần chính sách tương thích được quyết định trước khi bật bắt buộc.

## 5 · Chuỗi xử lý tại server

### 5.1 · Đường vào request bảo vệ

```
<svg aria-label="Sơ đồ khối server: HTTPS, giới hạn header và body, kiểm profile, token DPoP và thời gian, giải mã AES-GCM, kiểm Ed25519, ghi Redis SET NX, rồi mới parse JSON và gọi controller. Mỗi quyết định sai rẽ sang nhánh từ chối." role="img" viewbox="0 0 1000 1040" width="1000"><defs><marker id="request-flow-arrow" markerheight="7" markerwidth="7" orient="auto" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0 0 10 5 0 10Z" fill="var(--accent)"></path></marker></defs>
<rect class="ui" height="50" rx="7" width="290" x="355" y="18"></rect><text class="head" text-anchor="middle" x="500" y="49">HTTPS edge · request tới server</text><path class="edge" d="M500 68V94" marker-end="url(#request-flow-arrow)"></path>
<rect class="proc" height="58" rx="7" width="330" x="335" y="100"></rect><text text-anchor="middle" x="500" y="125">Route/profile · body/header limit</text><text class="small" text-anchor="middle" x="500" y="145">Content-Type · field/header lặp</text><path class="edge" d="M500 158V183" marker-end="url(#request-flow-arrow)"></path>
<polygon class="warn" points="500,190 650,238 500,286 350,238"></polygon><text text-anchor="middle" x="500" y="233">Profile + định dạng</text><text text-anchor="middle" x="500" y="250">hợp lệ?</text>
<path class="edge" d="M650 238H778" marker-end="url(#request-flow-arrow)"></path><text class="edge-label" x="713" y="228">Không</text><rect class="bad" height="54" rx="7" width="190" x="784" y="211"></rect><text text-anchor="middle" x="879" y="243">Từ chối qua TLS</text>
<path class="edge" d="M500 286V312" marker-end="url(#request-flow-arrow)"></path><text class="edge-label" x="521" y="302">Có</text>
<rect class="proc" height="58" rx="7" width="330" x="335" y="318"></rect><text text-anchor="middle" x="500" y="343">Access token · session · DPoP</text><text class="small" text-anchor="middle" x="500" y="363">alg, typ, htm, htu, ath, jkt, thời gian</text><path class="edge" d="M500 376V401" marker-end="url(#request-flow-arrow)"></path>
<polygon class="warn" points="500,408 650,456 500,504 350,456"></polygon><text text-anchor="middle" x="500" y="451">Token/proof/phiên</text><text text-anchor="middle" x="500" y="468">hợp lệ?</text>
<path class="edge" d="M650 456H778" marker-end="url(#request-flow-arrow)"></path><text class="edge-label" x="713" y="446">Không</text><rect class="bad" height="54" rx="7" width="190" x="784" y="429"></rect><text text-anchor="middle" x="879" y="461">Từ chối xác thực</text>
<path class="edge" d="M500 504V530" marker-end="url(#request-flow-arrow)"></path><text class="edge-label" x="521" y="520">Có</text>
<rect class="proc" height="58" rx="7" width="330" x="335" y="536"></rect><text text-anchor="middle" x="500" y="561">AES-GCM + AAD · chữ ký Ed25519</text><text class="small" text-anchor="middle" x="500" y="581">payload bytes + metadata; chưa ghi jti</text><path class="edge" d="M500 594V619" marker-end="url(#request-flow-arrow)"></path>
<polygon class="warn" points="500,626 650,674 500,722 350,674"></polygon><text text-anchor="middle" x="500" y="669">Tag + chữ ký</text><text text-anchor="middle" x="500" y="686">đúng?</text>
<path class="edge" d="M650 674H778" marker-end="url(#request-flow-arrow)"></path><text class="edge-label" x="713" y="664">Sai</text><rect class="bad" height="54" rx="7" width="190" x="784" y="647"></rect><text text-anchor="middle" x="879" y="679">Từ chối mật mã</text>
<path class="edge" d="M500 722V744" marker-end="url(#request-flow-arrow)"></path><text class="edge-label" x="521" y="739">Đúng</text>
<rect class="store" height="50" rx="7" width="290" x="355" y="750"></rect><text text-anchor="middle" x="500" y="780">Redis SET NX theo jti</text><path class="edge" d="M500 800V825" marker-end="url(#request-flow-arrow)"></path>
<polygon class="warn" points="500,832 650,880 500,928 350,880"></polygon><text text-anchor="middle" x="500" y="885">jti mới?</text>
<path class="edge" d="M650 880H778" marker-end="url(#request-flow-arrow)"></path><text class="edge-label" x="706" y="870">Cũ / Redis lỗi</text><rect class="bad" height="54" rx="7" width="190" x="784" y="853"></rect><text text-anchor="middle" x="879" y="885">Từ chối replay</text>
<path class="edge" d="M500 928V952" marker-end="url(#request-flow-arrow)"></path><text class="edge-label" x="521" y="946">Mới</text>
<rect class="good" height="64" rx="7" width="330" x="335" y="958"></rect><text text-anchor="middle" x="500" y="984">Parse JSON · schema · quyền</text><text class="small" text-anchor="middle" x="500" y="1004">idempotency bền vững → controller hiện tại</text>
</svg>
```

Giới hạn định dạng trước thao tác tốn tài nguyên. Chỉ sau xác thực token, tag và chữ ký mới ghi replay cache; các module vẫn kiểm quyền nghiệp vụ.



### 5.2 · Response và nhánh lỗi

```
<svg aria-label="Sơ đồ khối response: nếu chưa biết session key thì trả lỗi tối giản qua TLS; nếu đã xác thực thì kết quả thành công hoặc lỗi nghiệp vụ được mã hóa bằng K_response, nonce mới và AAD có status; app kiểm tag trước parse JSON." role="img" viewbox="0 0 1000 600" width="1000"><defs><marker id="response-flow-arrow" markerheight="7" markerwidth="7" orient="auto" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0 0 10 5 0 10Z" fill="var(--accent)"></path></marker></defs>
<rect class="ui" height="50" rx="7" width="270" x="365" y="20"></rect><text text-anchor="middle" x="500" y="51">Server chuẩn bị response</text><path class="edge" d="M500 70V100" marker-end="url(#response-flow-arrow)"></path>
<polygon class="warn" points="500,107 640,157 500,207 360,157"></polygon><text text-anchor="middle" x="500" y="152">Đã biết session key</text><text text-anchor="middle" x="500" y="170">sau xác thực?</text>
<path class="edge" d="M640 157H780" marker-end="url(#response-flow-arrow)"></path><text class="edge-label" x="705" y="147">Không</text><rect class="bad" height="58" rx="7" width="190" x="786" y="128"></rect><text text-anchor="middle" x="881" y="153">Lỗi tối giản qua TLS</text><text class="small" text-anchor="middle" x="881" y="172">không lộ proof/token</text>
<path class="edge" d="M500 207V236" marker-end="url(#response-flow-arrow)"></path><text class="edge-label" x="522" y="226">Có</text>
<rect class="proc" height="60" rx="7" width="310" x="345" y="242"></rect><text text-anchor="middle" x="500" y="267">Kết quả hoặc lỗi nghiệp vụ</text><text class="small" text-anchor="middle" x="500" y="287">JSON + HTTP status từ controller</text><path class="edge" d="M500 302V330" marker-end="url(#response-flow-arrow)"></path>
<rect class="proc" height="66" rx="7" width="350" x="325" y="336"></rect><text text-anchor="middle" x="500" y="362">AES-GCM: K_response + nonce mới</text><text class="small" text-anchor="middle" x="500" y="383">AAD gắn version, res, path, request ID, sid, status</text><path class="edge" d="M500 402V430" marker-end="url(#response-flow-arrow)"></path>
<rect class="ui" height="52" rx="7" width="310" x="345" y="436"></rect><text text-anchor="middle" x="500" y="466">App kiểm tag trước parse JSON</text><path class="edge" d="M500 488V512" marker-end="url(#response-flow-arrow)"></path>
<polygon class="warn" points="500,518 590,550 500,582 410,550"></polygon><text text-anchor="middle" x="500" y="555">Tag đúng?</text>
<path class="edge" d="M410 550H260" marker-end="url(#response-flow-arrow)"></path><text class="edge-label" x="329" y="540">Không</text><rect class="bad" height="50" rx="7" width="184" x="70" y="525"></rect><text text-anchor="middle" x="162" y="555">Bỏ response</text>
<path class="edge" d="M590 550H740" marker-end="url(#response-flow-arrow)"></path><text class="edge-label" x="650" y="540">Có</text><rect class="good" height="50" rx="7" width="184" x="746" y="525"></rect><text text-anchor="middle" x="838" y="555">Đọc kết quả</text>
</svg>
```

Thành công và lỗi *sau xác thực* đều mã hóa. Không log plaintext, token hoặc chi tiết giải mã.

**Thứ tự quan trọng:** Kiểm tra định dạng và giới hạn kích thước trước thao tác tốn tài nguyên; chỉ ghi cache replay sau xác thực mật mã để request giả không chiếm ID hợp lệ. Có thể kiểm tồn tại replay trước để tối ưu, nhưng kết quả cuối vẫn phải được xác nhận atomically bằng `SET NX` sau xác thực.

Phân quyền theo chủ máy/nhân viên vẫn do flow hiện có kiểm tra. Middleware không suy ra quyền nghiệp vụ từ chữ ký hoặc token. Không log plaintext, token, khóa, signature hay lỗi giải mã chi tiết; log request ID, key ID, loại lỗi và thời gian với chính sách lưu giữ phù hợp.

## 6 · Gắn với cấu trúc FlexMix hiện tại

### 6.1 · Vị trí middleware trong repo

```
<svg aria-label="Sơ đồ khối tích hợp: ServerClient của app gửi HTTPS vào http_server và http_json; routing quyết định route có bắt buộc secure profile; nhánh có qua middleware rồi service hiện tại; nhánh máy và GET cần hợp đồng riêng." role="img" viewbox="0 0 1000 640" width="1000"><defs><marker id="integration-arrow" markerheight="7" markerwidth="7" orient="auto" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0 0 10 5 0 10Z" fill="var(--accent)"></path></marker></defs>
<rect class="ui" height="64" rx="7" width="310" x="345" y="20"></rect><text text-anchor="middle" x="500" y="45">app/.../core/server_client.dart</text><text class="small" text-anchor="middle" x="500" y="65">DPoP · ký · mã hóa/giải mã tập trung</text><path class="edge" d="M500 84V115" marker-end="url(#integration-arrow)"></path><text class="edge-label" x="525" y="107">HTTPS</text>
<rect class="proc" height="64" rx="7" width="310" x="345" y="121"></rect><text text-anchor="middle" x="500" y="146">server/lib/http/http_server.py</text><text class="small" text-anchor="middle" x="500" y="166">http_json.py đọc/ghi trong context</text><path class="edge" d="M500 185V216" marker-end="url(#integration-arrow)"></path>
<polygon class="warn" points="500,223 650,278 500,333 350,278"></polygon><text text-anchor="middle" x="500" y="272">routing.py: route</text><text text-anchor="middle" x="500" y="290">bắt buộc profile?</text>
<path class="edge" d="M650 278H750V326" marker-end="url(#integration-arrow)"></path><text class="edge-label" x="698" y="267">Chưa</text>
<rect class="warn" height="80" rx="7" width="220" x="758" y="332"></rect><text text-anchor="middle" x="868" y="357">Giao thức riêng / rollout</text><text class="small" text-anchor="middle" x="868" y="377">/machine/* và GET trạng thái</text><text class="small" text-anchor="middle" x="868" y="394">không tự áp profile app POST</text>
<path class="edge" d="M500 333V362" marker-end="url(#integration-arrow)"></path><text class="edge-label" x="521" y="352">Có</text>
<rect class="proc" height="84" rx="7" width="330" x="335" y="368"></rect><text text-anchor="middle" x="500" y="393">Crypto middleware tại HTTP chung</text><text class="small" text-anchor="middle" x="500" y="413">token/DPoP · GCM · Ed25519 · replay</text><text class="small" text-anchor="middle" x="500" y="432">bao cả response và nhánh lỗi</text><path class="edge" d="M500 452V484" marker-end="url(#integration-arrow)"></path>
<rect class="good" height="72" rx="7" width="330" x="335" y="490"></rect><text text-anchor="middle" x="500" y="517">server/service/* → handle(request)</text><text class="small" text-anchor="middle" x="500" y="538">giữ kiểm quyền và nghiệp vụ hiện có</text>
<text class="small" text-anchor="middle" x="500" y="605">Bật profile theo route; route đã bật không được tự downgrade.</text>
</svg>
```

Đây là sơ đồ tích hợp **dự kiến**. Tài liệu chưa thay đổi mã nguồn vận hành.

| Hiện trạng đã đọc | Điểm tích hợp dự kiến |
| --- | --- |
| `server/lib/http/http_server.py` duyệt các module bằng `handle(request)`. | Lớp bảo vệ đặt ở HTTP transport chung trước gọi module; giữ route và cửa vào module. Định nghĩa route nào bắt buộc profile ở cấu hình routing, không để từng feature tự giải mã. |
| `server/lib/http/http_json.py` đọc/ghi JSON trực tiếp; mỗi feature gọi helper này. | Cần API đọc/ghi có context bảo mật hoặc wrapper request/response; không chỉ thay riêng `read_json` vì phải mã hóa mọi đường trả lỗi. |
| `server/lib/security/user_session.py` phát token opaque 32 byte, lưu hash trong SQLite; token hiện nằm trong body. | Giữ token opaque nếu muốn, thêm binding key/session và chuyển token sang Authorization. Trong giai đoạn tương thích, adapter loại bỏ trường `token` khỏi payload đã giải mã rồi truyền danh tính vào flow theo hợp đồng đã chốt; cập nhật các bên gọi và test đồng thời. |
| `app/flutter_app/lib/core/server_client.dart` là transport chung; hiện cho phép `http://`. | Đóng gói DPoP, mã hóa/giải mã tại transport; production chỉ chấp nhận HTTPS. Khóa riêng quản lý bằng secure storage/keystore phù hợp nền tảng; feature vẫn gửi JSON nghiệp vụ. |
| Máy dùng `machine/server_connection/*` và các route `/machine/*`; app có một GET `/machine/trang-thai`. | Thiết kế định danh khóa, bắt tay và rollout *riêng* cho máy. Không áp profile app POST lên heartbeat/long-poll hoặc GET trước khi định nghĩa hợp đồng của chúng. |

Thứ tự triển khai: (1) HTTPS, kiểm quyền và định danh thiết bị, gồm kiểm chứng khả năng Keystore trên máy mục tiêu; (2) token binding/DPoP với replay cache, vòng đời token và thu hồi khóa; (3) xác nhận thao tác nhạy cảm và audit; (4) chỉ khi có yêu cầu bảo vệ payload sau TLS termination mới thêm handshake, AES-GCM hai chiều, chữ ký payload/response và padding; (5) bổ sung Play Integrity theo chính sách rủi ro nếu phát hành qua Google Play; (6) chuyển từng route sang bắt buộc profile và xóa đường cũ. Không chấp nhận downgrade tự động nếu route đã bật profile.

## 7 · Quản trị khóa và vận hành

* Khóa server định danh lưu trong KMS/HSM hoặc kho khóa có kiểm soát; có `key_id`, phiên bản, quy trình xoay khóa và thời gian overlap. Public key app có trạng thái thu hồi; đăng xuất, mất thiết bị, đổi mật khẩu hoặc nghi ngờ xâm nhập phải vô hiệu hóa phiên/khóa liên quan.
* Nếu cần chứng cứ chống chối bỏ, lưu bản ghi kiểm toán chống sửa đổi gồm hash payload, signing input, chữ ký, public key/key ID, kết quả xác minh, danh tính đã xác thực và thời gian server nhận. Chứng cứ phải có chính sách lưu giữ, kiểm soát truy cập và quy trình xử lý khi khóa thiết bị bị chiếm; không lưu token hoặc payload nhạy cảm trong log thông thường.
* Khóa phiên chỉ tồn tại trong TTL cần thiết, không ghi log hay sao lưu plaintext. Nếu cần lưu để phục hồi server, phải mã hóa bằng key wrapping và ghi rõ ảnh hưởng đến PFS; ưu tiên tạo phiên mới sau restart.
* Redis replay là thành phần nhất quán dùng chung giữa mọi replica; không dùng cache cục bộ riêng lẻ. Giám sát tỉ lệ lỗi proof, tag, clock skew, replay, xoay khóa và độ trễ; không gộp lỗi xác thực vào thông tin trả client.
* Access token có TTL ngắn, scope và audience tối thiểu; refresh token của app được ràng buộc với thiết bị hoặc xoay vòng và phát hiện reuse. Đăng xuất, mất máy, đổi mật khẩu và đổi quyền phải vô hiệu hóa token, phiên, khóa liên quan; server kiểm trạng thái thu hồi trên mỗi request bảo vệ.
* Android Keystore và key attestation chỉ được coi là đạt yêu cầu khi kiểm chứng được chuỗi chứng chỉ, challenge, mức bảo vệ và thuật toán trên thiết bị thực. Khi khóa mất hoặc bị vô hiệu hóa, yêu cầu đăng ký lại qua luồng xác thực; không khôi phục khóa riêng từ backup ứng dụng.
* Đánh giá “chuẩn ngân hàng/tài chính” theo tiêu chuẩn áp dụng cụ thể (ví dụ quy định tổ chức, PCI DSS/FIPS nếu có). Tài liệu này không tự chứng minh đạt một chứng nhận.

## 8 · Điều kiện nghiệm thu và kiểm thử

1. Test vector liên ngôn ngữ Dart/Python cho HKDF, ký Ed25519, DPoP, AAD, AES-GCM, base64url và response status; byte đầu vào/đầu ra phải khớp.
2. Kiểm thử thay đổi từng byte của token, method, path, timestamp, request ID, session ID, ciphertext, tag, payload, status; tất cả trường hợp liên quan phải bị từ chối trước controller.
3. Thử replay đồng thời qua nhiều server, Redis mất kết nối, clock skew, retry hợp lệ với idempotency key, crash ở ranh giới transaction và rotate/revoke key.
4. Kiểm thử giới hạn body/header, JSON malformed, header lặp, path do proxy sửa, thiết bị mất khóa, sai phiên; không rò plaintext/token trong log, crash report và response lỗi.
5. Thử challenge nhạy cảm hết hạn, tái sử dụng, đổi tham số, đổi người dùng/thiết bị và hai request đồng thời; thao tác chỉ chạy sau khi xác nhận hợp lệ và kiểm quyền thành công. Thử refresh token reuse, thu hồi giữa phiên và phạm vi quyền tối thiểu.
6. Trên các mẫu Android mục tiêu, xác minh thuật toán ký thực sự dùng được trong Keystore, mức bảo vệ phần cứng và attestation; thử thiếu Google Play, verdict cũ, sai `requestHash`, lỗi dịch vụ và chính sách fallback theo route.
7. Security review độc lập cho protocol và triển khai; chỉ bật bắt buộc sau khi migration app/server/machine liên quan hoàn tất và test hợp đồng cũ/mới cùng chạy.

## 9 · Tài liệu gốc tham khảo

* [RFC 9449 — OAuth 2.0 DPoP](https://www.rfc-editor.org/rfc/rfc9449.html): proof, token binding, replay, nonce.
* [RFC 9421 — HTTP Message Signatures](https://www.rfc-editor.org/rfc/rfc9421.html) và [RFC 9530 — Digest Fields](https://www.rfc-editor.org/rfc/rfc9530.html): chuẩn thay thế nếu chuyển sang chữ ký HTTP chuẩn hóa ở phiên bản sau.
* [RFC 7748 — X25519](https://www.rfc-editor.org/rfc/rfc7748.html), [RFC 5869 — HKDF](https://www.rfc-editor.org/rfc/rfc5869.html), [RFC 8032 — Ed25519](https://www.rfc-editor.org/rfc/rfc8032.html).
* [NIST SP 800-38D — GCM](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38d.pdf): yêu cầu IV duy nhất, AAD và tag.
* [RFC 8446 — TLS 1.3](https://www.rfc-editor.org/rfc/rfc8446.html); [OWASP Key Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Key_Management_Cheat_Sheet.html): nền tảng vận chuyển và vòng đời khóa.
* [RFC 9700 — OAuth 2.0 Security Best Current Practice](https://www.rfc-editor.org/rfc/rfc9700.html): token bound, scope/audience, refresh token rotation và giới hạn khi khóa bị chiếm.
* [Android Keystore](https://developer.android.com/privacy-and-security/keystore), [Android Key Attestation](https://developer.android.com/privacy-and-security/security-key-attestation) và [BiometricPrompt](https://developer.android.com/identity/sign-in/biometric-auth): khả năng khóa thiết bị và xác thực mỗi lần dùng.
* [Play Integrity API](https://developer.android.com/google/play/integrity/overview): tín hiệu toàn vẹn app/thiết bị và ràng buộc verdict với yêu cầu.

FlexMix · Tài liệu thiết kế, chưa thay đổi mã nguồn vận hành.
