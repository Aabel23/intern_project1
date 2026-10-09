# Thiết kế chính — bảo vệ gói tin, bản review R5 + quyết định 07/10/2026

Ngày 06/10/2026; **người dùng chốt 11 quyết định D/C ngày 07/10/2026**. Chưa triển khai.
Tài liệu này là nguồn quyết định chính thay phần giao thức trong bản HTML gốc và
các shortlist nghiên cứu. Không thay code, route, schema hoặc quy ước module khi chưa có plan.

## 0. Quyết định đã chốt — 07/10/2026

Người dùng chốt bộ `D1-B, C2-B, C4-B, C1-A, C3-A, D2-C, D3-B, D4-B, D5-A, D6-A, D8-C`
sau đối chiếu hệ thống ([system-fit](/home/abel/.secondbrain/projects/internproj/project1_app/archive/middleware-operator-2026-10/system-fit-2026-10-07.md)). Các mục
bên dưới đã sửa theo bộ này; phương án bị loại và so sánh chỉ còn ở hồ sơ nghiên cứu
([D](/home/abel/.secondbrain/projects/internproj/project1_app/archive/middleware-operator-2026-10/decision-options-2026-10-07.md), [C](/home/abel/.secondbrain/projects/internproj/project1_app/archive/middleware-operator-2026-10/crypto-options-2026-10-07.md)).
Chốt thiết kế **không** là bằng chứng thư viện build được, vector đạt hay số đo đã có.

| Mã | Thiết kế đã chốt | Mục chịu ảnh hưởng |
| --- | --- | --- |
| D1-B | Root ký manifest là file khóa mã hóa passphrase trên **máy ký air-gapped**; backup ở hai nơi; manifest đã ký chuyển qua phương tiện kiểm soát | §3 |
| C2-B | **ECDSA P-256/SHA-256 cho cả root, app và máy**, mỗi vai key riêng; wire r‖s 64 byte, low-s | §2, §3 |
| C4-B | Khóa ký app bắt buộc Android Keystore mức **TEE trở lên** đã kiểm, không đạt thì từ chối enroll; máy/server giữ key file riêng quyền 0600 | §3 |
| C1-A | HPKE suite **DHKEM(X25519, HKDF-SHA256) 0x0020 / HKDF-SHA256 0x0001 / AES-128-GCM 0x0001**; enc 32, key 16, nonce 12, tag 16 byte | §2, §4 |
| C3-A | App: **Bouncy Castle HPKE qua Kotlin MethodChannel**; server và Pi: **PyHPKE** (kéo `cryptography`). Dart không tự làm crypto | §2 |
| D2-C | App kiểm OS clock bằng **thời gian do server ký** qua kênh time riêng ngoài packet profile; khóa ký thời gian nằm trong trust package cài cùng APK | §6 |
| D3-B | Máy được **provision lúc lắp**: sinh cặp khóa, admin đăng ký public key; chủ nhận claim code niêm phong; app yêu cầu máy ký nonce khi claim | §3 |
| D4-B | **Recovery code** một lần cấp lúc enroll, lưu hash, rate limit, thu hồi/báo credential cũ; đường admin đối soát là nền | §3 |
| D5-A | **Server Python tự kết thúc TLS** bằng `ssl` stdlib, không proxy; cert tự cấp được pin trong `network_security_config` | §1, §9 |
| D6-A | **Chuyển toàn profile một đợt qua bảo trì** cho deployment thử nghiệm hiện tại | §13 |
| D8-C | **Bỏ GET `/app/machine/status/get`**; `online`/`last_seen` trả trong `USER_MACHINE_LIST` | §4 |

Hai chỗ đổi design R5 đã được người dùng chấp nhận khi chốt: C3-A thay câu fallback
FFI ở §2; D2-C thêm kênh time có chữ ký server ở §6.

## 1. Mục tiêu và phạm vi bảo đảm

Chọn hướng **E: mã hóa ứng dụng hai chiều + chứng minh nguồn gửi**, vì người dùng
đã yêu cầu payload có lớp mã hóa riêng ngoài HTTPS. Không để E là tính năng tùy chọn.
Server nghiệp vụ được giải mã. App↔server và máy↔server là hai chặng độc lập;
không phải E2EE app↔máy mà server không đọc được. Không bổ sung relay/runtime mới.

| Đối thủ | Năng lực | Cam kết có điều kiện / giới hạn |
| --- | --- | --- |
| A0: mạng | Nghe, sửa, chặn, phát lại traffic; không có khóa endpoint | TLS và envelope bảo vệ nội dung/toàn vẹn; availability không được bảo đảm |
| A1: trung gian TLS | Đọc/sửa plaintext HTTP tại proxy, tráo key config/packet; không có root ký config, khóa server hay credential endpoint | Không đọc nội dung inner; không tạo packet nghiệp vụ mới hợp lệ; có thể chặn traffic và thấy route/kid/kích thước/thời gian |
| A2: tài khoản hợp lệ | Có token và khóa của chính mình, gửi input độc hại/concurrent/flood | Không được suy ra quyền máy khác; quota/validation và quyền vẫn bắt buộc ở feature |
| A3: endpoint/control plane | Đọc private key/RAM server hoặc app/máy, thay APK/root trust, restore state bí mật, chiếm người quản trị phát hành | Ngoài bảo đảm nội dung/nguồn gửi; cần containment, revoke và recovery; không tuyên bố bất khả xâm phạm |

A1 là **mô hình thiết kế**. Theo D5-A không có proxy vận hành: server Python tự
kết thúc TLS, nên mọi bên kết thúc TLS khác (proxy kiểm thử, middlebox trên LAN,
cert pin bị bỏ qua) được coi là A1. Phép kiểm giá trị của E: proxy test kết thúc TLS chỉ thấy envelope, không đọc được
mật khẩu/token/menu inner và không thay gateway key bằng key tự tạo. Nếu proxy có
quyền root trên server thì A1 trở thành A3; E không che plaintext khỏi người đó.

Không hứa anonymity, chống chối bỏ, chống lượng tử hoặc forward secrecy sau khi
private key recipient lâu dài bị lộ. HPKE có giới hạn này (RFC 9180 §9.7.4).
Các thuộc tính đều phụ thuộc thư viện đúng, CSPRNG tốt, trust anchor đúng,
endpoint chưa bị chiếm, durable storage đúng và policy hiện hành.

## 2. ADR: một lớp xác thực nguồn, bỏ handshake tự ghép

- Bỏ profile tự ghép X25519/HKDF handshake, DPoP JWT cộng chữ ký payload bên trong.
- Hướng prototype: **HPKE Base single-shot RFC 9180** cho từng attempt request;
  **một chữ ký ngoài** trên context + `enc` + ciphertext của credential người gửi.
- Response dùng key/nonce Export từ **chính context request**, theo kiểu singleton
  ở RFC 9180 §9.8. Chính sách single-response bên dưới là bắt buộc.
- Không tự viết KEM/KDF/AEAD hay handshake. Adapter gọi thư viện HPKE có vector
  chuẩn; profile ứng dụng này không tự nhận OHTTP/RFC 9458 compliant hoặc có anonymity.
- Không bỏ chữ ký ngoài: HPKE Base ai có public key server cũng tạo ciphertext được.
  Chữ ký ngoài bind credential với ciphertext/context và cho verify trước decap.
- Không dùng HPKE Auth để giả định có chữ ký không thể giả khi recipient key lộ:
  RFC 9180 §9.1.1 nêu KCI. Chữ ký ngoài dùng khóa độc lập với recipient KEM.
- Response AEAD chỉ cho bảo đảm A0/A1 dưới điều kiện secret context chưa lộ và
  invariant quyền Seal/retention/durability ở §5–6 được giữ. Client
  biết response key nên không có bằng chứng chống chối bỏ của server; đó không là mục tiêu.
- Token opaque vẫn nằm trong inner payload, giữ cơ chế hash lookup hiện tại;
  sau giải mã đối chiếu session→principal→credential/key. Token không là khóa ký
  hay khóa mã hóa; không đưa token app xuống command máy.
- Không Redis/replica bắt buộc. Replay/idempotency dùng SQLite durable trong
  kiến trúc một process hiện tại. Không dùng replay RAM chỉ vì đã dùng HPKE.

**Suite và dependency đã chốt (C1-A, C2-B, C3-A).** HPKE dùng một profile cố định
DHKEM(X25519, HKDF-SHA256) `0x0020`, KDF HKDF-SHA256 `0x0001`, AEAD AES-128-GCM
`0x0001`: `enc=32`, key 16, nonce 12, `tag=16` byte. Chữ ký ngoài, chữ ký manifest
và chữ ký máy đều là ECDSA P-256/SHA-256: ký canonical bytes qua API hash đúng một
lần (không prehash thêm), wire r‖s 64 byte fixed-width, low-s; reject DER, high-s,
trailing bytes. Khóa KEM recipient của server tách hẳn khóa ký. Chỉ một thuật toán
được allowlist theo key record, không chọn `alg` tự khai.

Thư viện: app gọi **Bouncy Castle** (`bcprov-jdk18on`, HPKE context có AAD/Export)
trong Kotlin qua **MethodChannel**, cùng cầu với signer Android Keystore; Dart chỉ
chuyển bytes, không tự làm crypto. Server và Pi dùng **PyHPKE** (kéo `cryptography`)
cho context/AAD/Export, `cryptography` cho ECDSA. Đây là dependency bên thứ ba đầu
tiên của server, phải pin version/hash. Câu fallback FFI của R5 được thay: MethodChannel
tới thư viện chuẩn là đường chính; nếu BC hoặc PyHPKE không đạt vector chuẩn, liên
thông đúng byte hoặc Export đúng RFC 9180 thì **dừng rollout** và quay lại người dùng
chọn stack khác, không tự ghép HPKE từ primitive và không tự đổi nền tảng.
Không tự hạ cấp sang plaintext/unsigned khi thiếu thư viện hoặc secure storage.
PyHPKE upstream chưa có audit độc lập; gate §10 bù bằng vector chuẩn và negative tests.

## 3. Trust anchor, enrollment và rotation

- APK/image máy chứa public root ký manifest được cài qua kênh phát hành đáng tin.
  Private root ký manifest ở môi trường quản trị riêng, không tại proxy/server online.
  **D1-B:** root P-256 sinh và giữ trên **một máy ký air-gapped** (không nối mạng),
  file khóa mã hóa bằng passphrase, backup mã hóa ở hai nơi tách biệt. Manifest chưa
  ký và đã ký chuyển qua phương tiện được kiểm soát; máy ký không nhận code/file
  chạy được từ phương tiện đó. File khóa có thể bị sao chép nếu máy/backup bị lộ:
  đó là rủi ro được chấp nhận so với token phần cứng. APK release phải có keystore
  phát hành riêng (hiện còn ký debug key), tách khỏi root packet.
- Manifest ký canonical bytes gồm deployment/audience, manifest_sequence monotonic,
  version/profile/suite, **recovery_epoch**, key ID, HPKE public key server, mục đích, trạng thái active/
  retiring/revoked, validity và policy version. Key ID không được tái sử dụng.
- Client verify bằng root đã cài, giữ sequence cao nhất trong storage chống rollback
  theo khả năng nền tảng; config có sequence thấp hơn bị từ chối. Cache key không
  tự bỏ kiểm hạn/thu hồi. Không lấy root mới chỉ bằng response của proxy/TLS.
- Root offline ký manifest theo lịch provision/rotation đã quản trị; có thể ký trước
  public key configs cho kỳ kế tiếp, private key online chỉ load trong epoch cần dùng.
  Không bắt buộc thêm khóa intermediate online. Client enforce `max_manifest_validity`
  và overlap bound từ trust package, không do manifest tự nới; thời gian mất mạng/
  manifest bị giữ lại quá hạn làm fail closed. Đây là tradeoff availability/rotation,
  tham số và cadence phải chốt bằng yêu cầu vận hành trước production, không số đo giả.
  Nếu A1 trì hoãn manifest thu hồi khi key online đã lộ, độ trễ nhận thu hồi tối đa
  không hơn remaining manifest validity + trusted-clock uncertainty **trong giả định
  clock/time bounds được giữ**. Không hứa xóa ciphertext attacker đã đọc.
- Root rotation: trust package phát hành ký bởi root cũ và xác thực qua kênh cập
  nhật; khi root cũ bị lộ cần kênh recovery độc lập/update app hoặc firmware.
  Chữ ký root cũ không chứng minh key mới đáng tin sau khi root cũ bị chiếm.
- Client clock chưa đáng tin, state chống rollback bị mất hoặc manifest hết hạn:
  mọi route có encrypted response bị chặn, chỉ cho recovery ngoài protocol theo
  trusted release/provisioning; không mở bootstrap Seal khi clock không đáng tin.
  Không dùng giờ chưa xác thực do proxy trả để tự mở đường tiếp tục.
- Thời hạn key epoch **không tự chứng minh** cửa sổ lộ ciphertext ≤ epoch: key
  có thể đã bị exfiltrate và giữ lại. Xóa secret cũ chỉ giảm phơi nhiễm nếu việc
  xóa/backup/đối thủ thực sự thỏa mô hình. Không gọi rotation là PFS.
- **C4-B:** khóa ký app là ECDSA P-256 non-exportable trong Android Keystore; enroll
  chỉ nhận khi KeyInfo/attestation cho mức **TEE hoặc StrongBox**; mức software thì
  từ chối enroll, không hạ cấp. Server và máy giữ private key trong file riêng, owner
  dịch vụ, quyền 0600, backup có kiểm soát; không TPM bắt buộc (Pi 5 không có sẵn).
  Rooted OS hoặc clone thẻ SD máy nằm ngoài bảo đảm.
- App enroll credential qua authenticated session + server challenge bound public
  key + proof-of-possession. Thay key phải có credential cũ hoặc recovery mạnh,
  không chỉ token bearer vừa đăng nhập; recovery báo/thu hồi credential cũ.
  Không auto rebind chỉ bằng mật khẩu/OTP: thay credential không có key cũ cần
  admin/owner đối soát bằng kênh đã provision độc lập (recovery code một lần, lưu
  hash server và rate limit) hoặc trusted administrative reprovisioning. Nếu không
  có yếu tố/kênh này thì không cấp quyền machine write cho credential mới.
  **D4-B:** đường mặc định là recovery code ngẫu nhiên entropy cao, cấp một lần lúc
  enroll, người dùng giữ ngoài điện thoại; server chỉ lưu hash, rate limit, dùng xong
  vô hiệu; khôi phục thu hồi và thông báo credential cũ. Mất cả code và key thì qua
  admin đối soát ngoài kênh; đường admin luôn tồn tại. Mất cả
  recovery code/key không được giải quyết bằng bỏ verify. Thông báo credential cũ
  là bằng chứng hỗ trợ, không là yếu tố duy nhất. Pending operation giữ unknown
  sau re-enroll; không tự đổi ID/ticket rồi gọi lại.
- Máy enroll bằng provisioning/owner confirmation tin cậy và proof-of-possession,
  không cho người chỉ có product-key/QR công khai thay credential máy. Product key
  là mã nhận biết/khởi tạo, không là bằng chứng máy đã enroll trong protected mode.
  **D3-B:** lúc lắp/cài máy (nối tiếp bước sinh product key và in tem QR), máy sinh
  cặp khóa P-256 và nhóm vận hành đăng ký public key + physical ID qua công cụ admin.
  Chủ nhận claim code niêm phong; khi claim, app đã enroll gửi code và yêu cầu máy
  ký nonce do server cấp để chứng minh máy thật giữ khóa. Claim code dùng một lần, rate
  limit. Dây chuyền provision và code phải được bảo vệ; máy cũ cần re-provision.
  `machine/config/create_env.py` hiện chỉ còn `.pyc`, cần khôi phục mã nguồn trước khi sửa.
- Trạng thái credential/session/revoke được kiểm sau verify và trước claim/commit.
  Cache chỉ dùng với invalidation/version rõ; mặc định đọc authoritative record.

Bootstrap trước enrollment dùng HPKE tới key server tin cậy để che login/register/
OTP/recovery payload và response, nhưng **chưa có chữ ký credential** nên không
claim nguồn gửi hoặc binding user. Route bootstrap có allowlist cố định, giới hạn
riêng và không thực hiện protected machine write. Login thường không được tự đổi
key của installation đã enroll. Mật khẩu/token bị lộ là rủi ro recovery phải kiểm.

## 4. Encoding không mơ hồ và dispatch

Đây là bảng encoding thiết kế cho vector, **chưa là wire contract production**.
`LP(x) = uint32_be(len(x)) || x`; độ dài đếm byte, không đếm ký tự. Không nối text
với dấu phân cách tùy ý. `Tuple(x...) = LP(x1)||...||LP(xn)`; số field cố định theo version.

| Field request `M`, đúng thứ tự | Encoding và kiểm |
| --- | --- |
| domain | ASCII `flexmix-packet-request-draft5` |
| version | uint16_be `0x0005` cho **draft5 nội bộ**, reject draft3/4; không là production version đã chốt |
| suite | fixed profile ID ASCII, lookup cấu hình, không từ algo client tự khai |
| audience | deployment ID ASCII từ cấu hình tin cậy, không Host/forwarded header |
| server_kid | ASCII key ID, đúng purpose/validity trong manifest |
| credential_kid | ASCII opaque key ID; bootstrap dùng đúng sentinel `bootstrap` |
| method | ASCII uppercase, so với method thực mà handler nhận |
| route_id | tên constant hiện tại như `MACHINE_MENU_UPDATE`, không đổi route HTTP |
| query | raw ASCII query bytes trong dạng được profile cho phép; không sort/decode/re-encode |
| attempt_id | 16 byte CSPRNG, mới mỗi attempt, không dùng làm IV |
| issued_at | uint64_be epoch seconds |
| expires_at | uint64_be; ≥ issued_at và span ≤ policy maximum |
| operation_id | 16 byte **server cấp** trong operation ticket cho mutation; all-zero sentinel cho no-ledger read/bootstrap |
| recovery_epoch | 16 byte identifier hiện hành ngoài vùng backup rollback, bind deployment; bootstrap cũng phải khớp epoch client được cấp tin cậy |
| peer_seen_server_seq | uint64_be, high-water server đã cấp, không tự khai để quarantine |
| server_seq_witness | 32 byte MAC witness; no-witness sentinel là zero-length chỉ cho policy enrollment/bootstrap/first-request, seq phải zero |

Mọi field bọc LP kể cả field fixed width; integer có đúng số byte và không sign.
Không chấp nhận alternative encodings, unknown/duplicate fields, field dài vượt policy.
Header HTTP lặp/conflicting Content-Length/Transfer-Encoding hoặc framing lỗi phải
bị từ chối trước verify. Không gzip/nén input; giới hạn cả ciphertext và plaintext.

- `info = Tuple(ASCII("flexmix-hpke-request-draft5"), M)`.
- HPKE `aad = Tuple(ASCII("flexmix-aad-request-draft5"), M)`.
- `signature_input = Tuple(ASCII("flexmix-sig-request-draft5"), M, enc, ct)`.
  Ký byte chuẩn trực tiếp qua API thuật toán profile; không thêm prehash chưa đặc tả.
- Outer binary envelope là uint16_be version + LP(M) + LP(enc) + LP(ct) + LP(sig).
  Outer version phải bằng M.version; exact frame length, không trailing bytes.
  Bootstrap chỉ được dùng sentinel kid trên route bootstrap allowlist và `LP(sig)`
  là uint32_be(0). Protected route bắt buộc credential kid không sentinel và sig
  đúng độ dài thuật toán. Sentinel+nonempty sig, protected+empty sig hoặc bootstrap
  metadata trên route máy/ghi đều reject; không bỏ field để chọn mode ngầm.
  Không hai lớp base64 hoặc plaintext chứa signature-b64/payload-b64.
- Inner request frame là `LP(auth_json_bytes)||LP(business_json_bytes)||LP(operation_ticket_bytes)||LP(machine_frontier)`.
  Bốn segments luôn tồn tại; đoạn machine_frontier zero-length cho non-machine.
  Route machine dùng fixed binary `uint64_be(ledger_seq)||32_byte_head_hash||LP(audit_challenge_id)`;
  challenge ID rỗng cho telemetry thông thường, 16 byte cho audit reply. Đoạn này
  được chữ ký ngoài bảo vệ qua ciphertext, không đặt uint64 binary trong JSON.
  auth JSON có token/session proof nếu route cần; business là JSON object nguyên bản.
  Đây là một lớp binary frame trong encryption, không base64 kép. Freeze chính
  business bytes lúc tạo ý định; token rotation chỉ đổi auth bytes, không fingerprint.
  Parse mỗi JSON segment với hard bound; duplicate keys, surrogate lỗi, NaN/Infinity
  bị reject; không reserialize để verify. Adapter mới dựng request feature theo
  contract hiện tại, không buộc feature đổi chữ ký khi chưa có task hợp đồng.
- Server map actual HTTP path/query/method từ routing allowlist sang logical route,
  so với `M`; mismatch thì reject. Route ID chỉ là protocol label, không thêm registry
  module động hay rename constants. Proxy rewrite chỉ hợp lệ khi deployment map
  tĩnh một-một đã kiểm; cấu hình chưa rõ thì reject, không tin X-Forwarded-* tùy ý.
- Query rỗng cho mọi route protected; profile không có wire adapter cho GET.
- **D8-C:** bỏ GET `/app/machine/status/get` (không token, mỗi máy một request). Danh
  sách máy `USER_MACHINE_LIST` trả thêm `online` và `last_seen` cho từng máy, sau
  kiểm phiên/quyền như hiện tại; dashboard bỏ vòng gọi status và refresh bằng tải
  lại danh sách. Đây là thay hợp đồng: server, app, test và e2e đổi cùng lúc; route
  GET chỉ gỡ sau khi inventory xác nhận không còn caller. Sau mốc chuyển, request tới
  route đã bỏ bị reject, không có ngoại lệ plaintext.

## 5. Response: đúng context, một lần seal

Inner response byte UTF-8 JSON có version, audience, attempt_id, route_id,
operation_id, **business_status**, outcome và payload. App kiểm đủ binding trước dùng
business_status/payload. `server_seq` trong JSON là **chuỗi ASCII decimal canonical**
không leading zero (trừ `"0"`), parse integer uint64, reject out-of-range; không dùng
float/double JSON cho giá trị 64-bit. `server_seq_witness` là base64url không padding
của đúng 32 byte, decode rồi re-encode phải byte-exact (43 ký tự); từ chối encoding
khác/field lặp. Trường witness trong M vẫn là byte raw LP, không base64 kép body.
Outer HTTP status chỉ là transport hint: đổi 200↔500 không
được biến lỗi thành thành công, bỏ token hoặc tự retry mutation.

- Dùng request HPKE context Export với labels riêng `flexmix-response-key-draft5`
  (Nk byte) và `flexmix-response-nonce-draft5` (Nn byte), theo RFC 9180 §9.8.
- `response_aad = Tuple(ASCII("flexmix-aad-response-draft5"), M)`.
- **Quyền Seal gắn với durable claim, không với Python/Dart context object.**
  Define response identity `CID=SHA256(Tuple(M,enc))`; `M` gồm server_kid, audience,
  credential_kid, attempt_id, recovery_epoch, peer_seen_server_seq và server_seq_witness. HPKE info/AAD dùng đúng M.
  Chỉ luồng thắng atomic attempt claim và durable `response_seal_started` CAS từ
  false→true có quyền Seal. Mỗi CID tối đa một invocation Seal trong lifetime
  packet còn có thể hợp lệ, qua threads/restart; CID trùng sau expires chỉ nhận
  transport error, không tái tạo key rồi mã hóa lỗi. Không claim invariant theo
  `(server_kid,enc)` đơn lẻ: M khác làm key schedule khác, nhưng vẫn cấm reuse enc
  chủ động tại sender. Hash collision là giả định cryptographic, không equality proof.
- **Mọi nhánh không thắng claim**, replay, expired, revoked, full/error store sau
  Open, chỉ trả transport error tối giản **không ciphertext**, kể cả context còn có.
  Bootstrap cũng phải thắng attempt claim + response CAS trước phát token/kết quả.
- Sau claim, serialize xong rồi CAS Seal-started bền; thành công/lỗi chỉ một outcome.
  State trong response record: CLAIMED→SEAL_STARTED→SEALED→SENT/CLOSED; ghi
  SEAL_STARTED durable **trước** gọi Seal. Context object không là nguồn quyền.
  Nếu crash giữa CAS và lưu ciphertext, không reconstruct để Seal lần nữa; caller
  chỉ retry bằng attempt mới. Nếu Seal lỗi/gửi ngắt không Seal error lần hai.
- Retransmit cùng attempt chỉ có thể dùng exact sealed bytes đã có; không đổi status,
  message hoặc payload. Client chỉ chấp nhận đúng một outcome của một attempt.
- Retry hợp lệ tạo context HPKE/attempt mới; semantic outcome cache từ ledger được
  bảo vệ bằng context mới. Không lưu/reuse response key cho nhiều attempts.
- Lỗi trước xác thực/không có quyền claim/không có context response: transport error tối giản, client
  không tin như business outcome; không phản chiếu secret/plaintext. Không parse
  untrusted proxy error để logout/đổi quyền hoặc kết luận tác vụ chưa chạy.
- Khóa/context export là ephemeral RAM có deadline và giới hạn số outstanding;
  không backup. Restart mất context thì trả unknown ở caller khi kết quả chưa rõ.

Nonce uniqueness chỉ có điều kiện: không clone/restore HPKE context, không tái dùng
randomness/enc, không nhiều Seal dưới cùng response key. Không viết `P=0` cho toàn
hệ thống: vẫn có rủi ro lỗi RNG, key/context collision, compromise và code sai.

## 6. Anti-replay và đồng hồ

Server là nơi quyết định thời gian: `issued_at ∈ [now-Δ_past, now+Δ_future]`,
`expires_at ≥ now`, `expires_at-issued_at ≤ L_max`. Δ và L chưa có số đo nên là
tham số policy bắt buộc phải chốt trước rollout. Clock nhảy lùi/vượt độ lệch vận hành hoặc chưa được xác minh sau boot → fail closed
**mọi route có Seal** (read/write/login/bootstrap/heartbeat/poll/result). Không
cleanup claim/Seal/ticket records trong trạng thái CLOCK_UNTRUSTED. Không chỉ khóa writes.
Lưu high-water `max_now_seen` bền cùng claim transaction; lúc startup và mỗi claim,
`now < max_now_seen-σ` khóa mọi route có Seal và mọi cleanup thời hạn. Trong process so wall-clock delta với monotonic
elapsed; sai lệch lớn khóa mọi route có Seal/cleanup cả nhảy tới trước.
Sau **mỗi boot** mặc định CLOCK_UNTRUSTED; không nhận encrypted request hoặc prune
cho tới xác minh OS time qua authenticated time service/trusted provisioning ngoài
protocol (ví dụ NTS với trust configuration đã kiểm). High-water chỉ là cross-check,
không tự chứng minh đồng hồ chưa nhảy tới trước qua restart. Mọi bước cleanup cũng
persist max_now_seen và kiểm clock authority trong cùng transaction, không chỉ claim.
High-water trong backup không chống restore: recovery_epoch và recovery procedure
ở mục ledger là nguồn riêng. **Không có route time-sync trong packet profile.** Client/máy dùng OS clock có
nguồn tin cậy không do A0/A1 điều khiển; sai clock phải sửa ở tầng OS/provisioning.

**D2-C — kênh thời gian có chữ ký server.** Server và Pi đồng bộ OS clock bằng chrony
NTS đã kiểm. App kiểm OS clock qua một endpoint time **riêng, ngoài packet profile**:
app gửi nonce CSPRNG, server trả `Tuple(domain "flexmix-time-draft5", audience, nonce,
uint64_be(server_time), uint64_be(uncertainty))` ký bằng **khóa ký thời gian** P-256
riêng purpose. Public key này nằm trong trust package cài cùng APK, không lấy từ
manifest (manifest cần giờ đúng mới kiểm được hạn). App đo RTT bằng elapsed
realtime, chấp nhận nếu nonce khớp và RTT không vượt bound; khoảng tin cậy là
`[server_time − uncertainty, server_time + uncertainty + RTT]`. OS clock nằm ngoài
khoảng thì fail closed mọi route Seal và hướng dẫn người dùng sửa giờ OS; app không
tự đặt OS clock và không chỉnh offset nội bộ để bỏ qua kiểm. Kênh time không miễn
freshness cho route nào, không cấp quyền, không đổi key validity. Đây là một nguồn:
server bị chiếm (A3) có thể ký giờ sai — nằm ngoài bảo đảm như §1. A0/A1 chỉ có thể
trì hoãn/chặn (DoS), không giả được giờ. Bound RTT, uncertainty và chu kỳ kiểm phải đo.
Transport error clock-skew không ciphertext chỉ là diagnostic không tin cậy: proxy
có thể gây DoS nhưng không được app dùng nó để tự chỉnh thời gian/key validity.
Không miễn freshness cho bootstrap để sửa clock. Freeze bound của manifest phụ thuộc
OS clock/trusted-time assumptions thật; thiếu capability này thì không production.
Máy chưa có clock đáng tin vẫn dùng nonce+local deadline để verify poll response,
nhưng không được gửi protected request mới trước khi OS clock được provision đúng.
Không suy ra mọi Pi thiếu/có RTC; inventory capability thiết bị là gate.


Sau signature hợp lệ (bootstrap không có signature), kiểm cheap freshness/epoch
trước decap; sau HPKE.Open hợp lệ, parse giới hạn, kiểm binding session/principal/
credential hiện hành, **claim atomic durable** `UNIQUE(audience, credential_kid,
attempt_id)` trước bất kỳ side effect. Key giữ độc lập với token ID để packet không
được nhận lần nữa khi token/epoch thay. Không claim sau verify mà quên kiểm phiên.

- Khóa HPKE tĩnh sống qua restart vẫn mở packet cũ. R3 **chọn** SQLite durable
  claim/response records để giữ availability không cần epoch blackout. Có thể có
  thiết kế watermark bền + replay RAM, nhưng cần proof expiry/future skew/restored
  clocks và mất availability sau restart; không tự đổi tối ưu này trước prototype.
- Retain record tới `expires_at + safety_clock_bound + cleanup_margin`, kể cả nonce
  tới sớm; khi thiếu clock/storage/admission, từ chối. Không dùng TTL W từ thời điểm
  nhận mà quên packet có thể có issued_at trong tương lai.
- Request `verify` lâu quá phải kiểm lại freshness lúc claim; không giữ request
  được nhận sau khi expiry vì đã verify trước đó.
- Không đuổi nonce còn sống khi bảng đầy; không chỉ giới hạn client-IP. Quota per
  credential và tổng process/storage bound. Packet chưa verify không được chiếm nonce.
- Backup restore có thể rollback replay/ledger. Quy trình ở mục 7 bắt buộc;
  revoke credential đơn thuần **không** sửa được mất lịch sử side effect.
- Reads/heartbeat cũng freshness mới. Các lỗi replay không có outcome nghiệp vụ mới.

Máy không mặc định có đồng hồ đáng tin. Poll có attempt_id CSPRNG và local monotonic
deadline; command response bind đúng **poll_attempt_id**, đúng machine credential và
lệnh/operation. Máy chỉ nhận trong outstanding poll đang sống. Nonce thay freshness
clock của poll response, **không thay ledger bền chống thực thi trùng**. Restart/cancel
poll xóa outstanding IDs; response cũ không được dùng sau poll mới.

## 7. Luồng máy và ledger nghiệp vụ

Máy dùng cùng envelope request/response model cho heartbeat/poll/result, credential
riêng từng installation/machine. Server auth principal machine bằng credential record,
không chỉ product key. Poll command nằm trong response authenticated/encrypted nên
không thêm chữ ký command dư nếu command không được tách khỏi response context.
Nếu sau này command lưu/chuyển độc lập thì cần profile chữ ký command riêng trước đổi.

Command inner fields: `machine_id`, `command_id` 16-byte CSPRNG, `operation_id`,
`instruction`, immutable payload bytes/fingerprint, `poll_attempt_id`,
server-issued `intent_deadline`, operation ticket và recovery_epoch.
Server chỉ dispatch khi còn trong intent_deadline. Deadline là hạn **admission
executor**; để máy không cần wall clock, server chỉ dispatch nếu
`now_server + D_poll_local_max + verify_admit_margin < intent_deadline`.
Máy check local elapsed deadline lại ngay trước durable executor claim. Trên Linux
chọn CLOCK_BOOTTIME để tính cả suspend; nếu chưa có API tương đương, invalidate
outstanding polls khi suspend/resume/app-background và yêu cầu poll/context mới.
Không dùng CLOCK_MONOTONIC ngầm giả định tính cả suspend; capability chưa verified
thì gate chặn protected executor. Policy
D_poll và margin có hard bound/clock-rate assumptions, chưa đo thì không rollout.
Nếu chỉ cần hạn dispatch, phải dùng profile/action explicit khác, không hứa hạn
executor/hoàn tất vật lý. Completion vật lý không được suy từ admission deadline.
Long-poll server wait + budget verification/serialization/network phải < local poll
deadline; network vượt bound → máy bỏ response, server giữ unknown nếu đã dispatch.
Queue take + mark dispatched bền + kiểm quyền/deadline/ticket cùng transaction.
Trước production phải có queue persistence adapter; không giữ SQL transaction lúc
chờ poll hoặc executor. Quá hạn chưa dispatch thì failed_no_effect; đã dispatch
thì không khẳng định chưa tác động. Ledger hiện trạng RAM chưa đáp ứng gate này.
Không dùng counter RAM reset làm command identity bền. Retry delivery nếu được
recovery phê duyệt giữ command_id và operation_id, không tạo ý định mới.

Machine ledger bền key `(stable_physical_machine_id, command_id)` và fingerprint
bao gồm machine/action/operation/payload. Credential generation chỉ là column
binding/audit, không là namespace mở lại command cũ. Rotation/enrollment giữ nguyên
ledger vật lý. Không redeliver unresolved command qua generation/recovery_epoch
mới; chuyển unknown và đối soát. Thay hardware/mất ledger không tạo permission
thực thi lại command cũ. Kiểm allowed instruction + payload + binding
trước claim. Atomically ghi `claimed` **trước** gọi executor. Result resend giữ command/
operation/outcome, mới attempt/context; conflicting result bị từ chối.

Server operation key `(principal, route/action, target_machine, operation_id)`, không
phụ thuộc token đổi/rotation. Fingerprint = SHA256(Tuple(domain, immutable original
business bytes, action, target)); loại token/freshness/ciphertext ra khỏi fingerprint.
Client freeze business bytes cùng ý định, retry không serialize lại.

### Ticket ý định và recovery chống rollback

- Operation ticket cấp trước mutation qua request prepare được bảo vệ; server tự
  sinh operation_id CSPRNG, không reissue ticket từ op ID client tự chọn. Ticket
  MAC/sign bằng key server dedicated purpose (không token bearer) trên canonical
  tuple: audience, **recovery_epoch**, principal, action, physical target, digest
  business bytes, operation_id, intent_deadline/ticket_expiry. Thư viện chuẩn,
  secret giữ ngoài proxy. Client không tự thay epoch/time/target rồi giữ ID cũ.
- Prepare không có side effect vật lý; quota/ticket issue bền và request replay
  bảo vệ như route khác. Ticket sai/M.operation_id không khớp/expiry/epoch cũ
  reject. Retry giữ **nguyên ticket và business bytes**, mới attempt. Ticket ID
  collision bị UNIQUE reject/regenerate trước cấp; không ghi đè.
- `recovery_epoch` là identifier mới cấp qua trusted operator recovery artifact,
  nguồn nằm ngoài **cả backup và VM/host/disk snapshot domain** của replay/operation DB. Trước restore,
  đóng mọi admissions có Seal/side effect; sau restore operator **đổi epoch + ticket MAC key**, invalidate
  session/credential cần thiết, publish trust package/manifests; boot không có
  current authoritative recovery artifact thì không mở admissions. Chỉ high-water
  thời gian hoặc DB được restore không đủ chống rollback.
- Ticket từ epoch cũ dù re-enroll credential mới vẫn bị reject/unknown, không
  được prepare lại tự động thành ticket mới. Clients lưu pending intent và ticket;
  khi epoch đổi/re-enroll chuyển pending sang reconciliation, không đổi ID.
- Mỗi boot/recovery không tự tin một artifact từ disk snapshot: mặc định quarantine
  admissions, yêu cầu current epoch confirmation từ nguồn ngoài rollback domain.
  Live-memory/VM snapshot resume không qua recovery **không được hỗ trợ** cho
  protected runtime. Nếu môi trường không phát hiện/kiểm soát loại restore này thì
  không đạt gate deployment; không tuyên bố phần mềm đơn lẻ giải quyết full rollback.
- Máy cũng giữ durable ledger ngoài rotation credential; restore/mất machine
  ledger bắt buộc quarantine executor và trusted recovery, không chỉ enroll lại.
- Không thể từ dữ liệu rollback tự chứng minh external side effects kể từ backup.
  Mở lại mutations chỉ sau đối soát máy/nguồn authoritative cho phạm vi mất dữ
  liệu; nơi thiếu chứng cứ giữ unknown/quarantine. Người có quyền chủ động tạo
  **ý định mới** sau đối soát có thể làm thao tác mới; protocol không đoán ý muốn.
- Completed record chỉ prune sau ticket_expiry + replay/clock safety; ticket đó
  không thể dùng nữa, prepare không cấp lại ID/ticket cũ. unresolved/unknown giữ
  tới recovery có chứng cứ; khi quota storage đạt bound thì dừng admissions mới,
  không xóa unknown. Giới hạn backlog/retention có phép kiểm trước rollout. Parse cho business
là bước khác; JSON semantically equal nhưng byte khác sẽ conflict theo hợp đồng này.
Cached outcome chỉ được trả sau kiểm phiên/quyền **hiện hành**, revoke chặn outcome cũ.

State machine:

```
absent -> claimed -> dispatched -> done
               \          \-> unknown
                \-> unknown
claimed -- chứng minh chưa dispatch + recovery decision --> failed_no_effect
unknown -- đối soát có chứng cứ --> done / failed_no_effect
```

- Claim/write trực tiếp SQL dùng cùng connection và transaction khi side effect cùng DB.
- Khi relay tới máy: claim commit → enqueue/send → wait **ngoài transaction DB** →
  ghi kết quả transaction mới. Mark dispatched bền trước khả năng side effect.
- Crash trước claim: chưa side effect; retry có thể claim. Crash sau claim trước dispatch:
  pending, không tự xóa claim; cần bằng chứng chưa dispatch. Crash sau dispatch hoặc
  sau máy execute trước kết quả: unknown, không tự sinh lệnh mới. Crash sau done:
  retry trả semantic outcome, quyền hiện hành còn hợp lệ.
- Machine actuator: crash sau claimed nhưng trước/sau tác động không phân biệt được;
  sau restart giữ unknown và không tự gọi executor lần nữa. Không hứa exactly-once
  vật lý hoặc cả at-most-once chuyển động nội bộ nếu actuator ngoài quyền điều khiển.
  Bảo đảm thiết kế hẹp: **không tự gọi business executor lần hai cho cùng durable claim**.
- Cleanup không xóa unresolved/unknown để mở lại ID. Completed chỉ xóa theo horizon
  được profile ràng buộc; request/operation cũ phải không thể hợp lệ sau horizon đó.

## 8. Revocation và tuyến tính hóa

Logout/revoke và admission side effect cùng dùng authoritative SQLite transaction
để có thứ tự rõ. Gọi thao tác ghi hợp lệ khi admission/claim commit trước revoke commit;
revoke trước claim thì reject. Quyền target được đọc lại cùng transaction claim/direct
mutation, không chỉ check ở middleware. Đọc cache outcome cũng check quyền mới.

Đã dispatched trước revoke có thể vẫn thực thi tại máy. Thu hồi không phải rollback/
remote kill có bảo đảm. Không claim mọi tác động sau timestamp logout bị ngăn.
Luồng direct SQL giữ transaction/BEGIN IMMEDIATE hiện có; không centralize rule feature
vào lib. Tác động sensitive confirmation nếu bổ sung phải bind operation/fingerprint,
claim challenge và operation cùng transaction; không consume challenge rồi bỏ ledger.

## 9. DoS, lỗi và tối ưu có ràng buộc

Ingress hard bound trước parse/verify: connections, header/body, declared length,
framing, version/key lookup, pending key contexts và tổng crypto concurrency. Quota
per-credential sau signature hợp lệ; limiter IP chỉ là tín hiệu thô, không nguồn danh tính.
Bootstrap có quota riêng và **cũng** chịu bucket toàn pool trước claim. Per-source
bootstrap quota dùng ingress provenance từ trusted topology; không tin IP/header
client tự khai. Reserved capacity cho heartbeat/result/established credentials
không cho flood bootstrap chiếm hết worker. Global anonymous bootstrap availability
vẫn có thể bị DoS; không hứa chống chặn login bởi đối thủ A0/A1. Theo D5-A, provenance
là địa chỉ socket peer tại server TLS Python; không tin X-Forwarded-*. Topology đổi (thêm proxy theo D5-B khi ra Internet) là gate cho provenance policy, không lấy IP giả làm căn cứ khóa tài khoản. Không dùng attacker-chosen key ID để fetch URL/file tùy ý.
Nonce/operation store full/unavailable → mọi route cần claim/Seal fail closed; unknown vẫn giữ.
Không log secret, inner token/payload hoặc plaintext error; metrics label không có
attempt/principal ID vô hạn làm cardinality DoS. Bounded sink không giữ request thread
đợi log; crash dump/DB/backup có policy riêng, encryption wire không bảo vệ chúng.

Mục tiêu tối ưu là **Pareto trong các candidate qua gate security**, theo vector
`(wire_bytes, CPU_p95, durable_writes, memory_bound, recovery_cost)`; chưa có trọng
số/đo nên không khẳng định optimal toàn cục. Bỏ một chữ ký trùng giảm một verify/request,
bỏ double base64 giảm expansion; HPKE single-shot tăng KEM/request so với session AEAD.
Không gọi giải pháp tốt nhất chỉ từ tên thuật toán; prototype đánh đổi có thể đảo lựa chọn.

### Toán có giả định

1. IV ngẫu nhiên đều độc lập 96-bit với q lần/key:
   `P_collision ≤ q(q−1)/2^97`. Với q=2^20: ~6.94e-18/key; union bound m=2^16
   keys: ~4.55e-13. Đây là collision bound, **không là tổng AEAD security bound**;
   phải xét khối dữ liệu/forgery attempts và giới hạn suite từ chuẩn/thư viện.
2. HPKE single-shot: một request Seal/context; một response Seal/export key.
   IV allocator lặp **trong context** được loại nếu lifecycle đúng. Không chứng minh
   context keys giữa requests luôn khác; cần đảm bảo CSPRNG, separation và collision
   bound/security analysis của KEM/KDF. Không suy P=0 cho toàn fleet.
3. Request/command ID ngẫu nhiên 128-bit: `P_collision ≤ N(N−1)/2^129`.
   UNIQUE phát hiện collision, reject/regenerate trước side effect; không ghi đè record.
4. Replay horizon tối đa từ thời điểm claim: `H ≤ L_max+Δ_future+σ+margin`, σ là
   safety clock bound có policy. Retain theo **absolute expiry**, không TTL tùy ý.
   Admission token-bucket capacity b, sustained r cho toàn pool →
   `live_replay_records ≤ b + ceil(r·H)` nếu quota và expiry assumptions được giữ.
   Không áp λ·H cho traffic burst khi chưa bound burst. SQLite storage overhead phải đo.
5. Base64url không padding có `len=ceil(4n/3)`. Hai lớp tạo expansion ~16n/9.
   Outer binary profile tránh hai lớp. Với candidate enc32/tag16/signature64,
   request payload expansion tối thiểu crypto=112 byte, cộng M/length prefixes;
   response tag16 thêm 16 byte, cộng status/binding/encoding. Chưa đo packet thực.
6. `CPU_req = verify_sig + HPKE_decap + AEAD_open(n) + quota/DB`;
   response Export+Seal; số crypto operations không phải latency. Gate benchmark
   riêng mobile/server/machine và recovery throughput, không dùng unittest wall time.

## 10. Gate trước khi coder làm product crypto

- Threat/config boundary và trust package xác minh bằng kênh provisioning thực;
  test tráo/rollback/expired manifest và mất clock/storage phải fail closed.
- Suite/dependency API pinned, official vectors + byte-exact Dart/Python, negative
  ciphertext/signature/context/response-binding; không tự triển khai primitive.
- Request retry/context mới; response error/send race chỉ Seal một lần; clone/RNG
  fault và restart phải được phát hiện hoặc invalidated trước mở writes.
- Replay concurrent/durable/expiry/clock rollback/backup restore/full store có test.
- Ledger crash points, token rotation, revoke race, quyền đổi, machine lost result,
  command identity qua restart và unknown recovery kiểm được; không claim exactly-once.
- Heartbeat/poll/result/auth/bootstrap đều có wire adapter; GET status đã gỡ theo
  D8-C cùng caller; route compatibility cập nhật app/server/machine/tests đồng thời.
  Lib không import feature/service.
- Suite đã chốt (C1-A/C2-B/C3-A) nhưng chưa có vector chạy: BC và PyHPKE phải đạt
  official vectors RFC 9180 cho suite 0x0020/0x0001/0x0001 và liên thông đúng byte
  trước khi coder dùng. Kênh time D2-C, enrollment D3-B, recovery D4-B và TLS D5-A
  cần spec/test riêng.
- Không triển khai cho tới khi operation retention, recovery/trust rotation và
  wire production version có vector/spec cụ thể. Các mục còn mở là implementation gates,
  không được che bằng verdict design review đạt hoặc đổi nhãn thành ngoài phạm vi.

## Nguồn và giới hạn

- [RFC 9180](https://www.rfc-editor.org/info/rfc9180/): §§9.1.1,9.7,9.8;
  HPKE/Export, KCI, replay và forward secrecy limits.
- [RFC 9458](https://www.rfc-editor.org/info/rfc9458/): tham khảo request/response
  encapsulation; không tuyên bố profile ứng dụng này tuân thủ OHTTP.
- [NIST SP 800-38D](https://csrc.nist.gov/pubs/sp/800/38/d/final): uniqueness,
  invocation/data limits của GCM; birthday bound ở trên do operator tính.
- [RFC 9449](https://www.rfc-editor.org/info/rfc9449/): DPoP là proof HTTP/token,
  không tự bảo vệ toàn body/query; không chọn DPoP cho profile candidate hiện tại.

Kết quả 5 vòng Claude Opus medium: R5 không tìm thấy blocker kiến trúc mới trong
phạm vi review. Operator bổ sung các nghĩa vụ O1–O3 bên dưới; đây là mức review
thiết kế có điều kiện, không là nghiệm thu product hay chứng nhận mật mã.

Chưa có formal verification, official-vector run, prototype, benchmark hoặc test
thực thi crypto. Review tài liệu không chứng minh sản phẩm hiện đã an toàn.

## 11. Counterexample tests bắt buộc cho R3 (đặc tả, chưa chạy)

| ID | Kịch bản | Kết quả bác bỏ lỗi |
| --- | --- | --- |
| F1 | R giống byte gửi hai lần tuần tự/concurrent, restart giữa hai lần; thêm expired/revoked/store-full sau Open | Tổng AEAD.Seal ≤1 cho response identity R; luồng không thắng claim không tạo ciphertext; crash sau SEAL_STARTED không reseal |
| F2 | Máy execute c, mất result, rotate/re-enroll g1→g2, recovery thử redeliver c | Ledger cùng physical ID còn c; không executor call lần hai; pending generation-crossing thành unknown |
| F3 | User intent hết hạn khi máy offline, poll mới nhiều giờ sau; delay response đến cuối poll-window | Không dispatch hết hạn; trước executor claim lại check deadline; budget deadline không đủ thì reject/unknown, không tác động mới |
| F4 | Restore DB trước o.done, giữ client pending ticket cũ, enroll mới rồi retry/prepare cùng op ID | Epoch/ticket cũ reject dù auth mới; prepare không nhận ID cũ; mất machine ledger khóa executor đến reconciliation |
| F8 | Bootstrap kid có nonempty sig; protected kid thiếu sig; query duplicate/encoded/unknown; outer version khác M | Reject trước nghiệp vụ/crypto đắt; không đổi mode hoặc reinterpret route |
| F9 | Clock lùi/nhảy tới trước trong process, reboot với high-water mới, restore có watermark cũ | Mọi route có Seal và cleanup fail closed; recovery artifact ngoài rollback bắt buộc, không tự cleanup rồi mở writes |

Spec này không coi test đã pass; người triển khai phải đưa instrumentation Seal/claim/
executor và fault harness thật. Chưa có chứng minh mật mã đầy đủ của composition.

## 12. Durability, rollback evidence và preconditions vận hành

- Claim, response Seal-started, operation ticket/ledger, dispatched state và machine
  executor claim phải durable trước external side effect hoặc Seal. SQLite dùng
  journal_mode được test, `synchronous=FULL`, không OFF/MEMORY/NORMAL cho các commit
  bảo mật này. `COMMIT` error không cấp quyền gọi tiếp. Không tắt sync để tăng speed.
  FULL là cấu hình cần thiết theo SQLite, không chứng minh SD/controller/OS thực sự
  giữ dữ liệu khi mất điện; storage phải honor flush/write barriers và qua fault gate.
- `server_ledger_seq` tăng cùng transaction admission/seal/operation state. Response
  inner có `server_seq` và **issuer witness**: HMAC-SHA256 bằng key `kw` riêng purpose
  trên Tuple(domain `flexmix-ledger-witness-draft5`, audience, recovery_epoch, uint64_be(seq)).
  Peer giữ `(seq,witness)` cao nhất **đã xác thực**; gửi nguyên witness trong M.
  Witness **chỉ cấp sau seq commit bền** (FULL + stable media flush) và trước Seal;
  không witness speculative seq trong RAM/transaction chưa commit. Response có thể
  phản ánh seq committed trước CAS mới hơn; đó là stale prefix hợp lệ, không overclaim.
  Server chỉ dùng frontier để quarantine khi MAC đúng, audience/epoch đúng, và
  claimed seq > local committed seq. Signature client không chứng minh issuer.
  MAC sai/thiếu, epoch sai, seq không khớp → chỉ reject packet, không quarantine toàn cục.
  Key kw tồn tại ổn định trong recovery_epoch; restore cùng key vẫn verify receipt
  newer; đổi epoch/kw làm old witness không hợp lệ, không tự xem nó là alarm mới.
  No-witness zero sentinel không là evidence continuity, chỉ được scoped policy cho phép.
- Máy gửi binary machine_frontier như §4; server giữ frontier cho physical machine.
  Telemetry đọc consistent seq/head đã commit bền, không báo pending RAM. Ledger
  hash chain: `head_n = SHA256(Tuple(ASCII("flexmix-machine-ledger-draft5"), head_previous,
  canonical_entry_n))`, genesis head 32 zero byte, seq tăng cùng transaction entry/
  state và head. canonical entry là LP tuple physical ID, uint64 seq, command ID,
  operation ID, state ASCII và fingerprint32 theo layout profile. Không thông báo
  frontier mới trước commit; extension evidence là gate adapter/harness chưa thực hiện.
  Packet telemetry out-of-order không là proof rollback: chỉ giữ maximum, không
  quarantine từ seq thấp tự thân. Khi cần continuity, server phát audit_challenge
  CSPRNG 16 byte, current epoch và snapshot expected frontier đã commit tại lúc cấp;
  một challenge outstanding, có deadline. Máy đọc durable ledger **sau khi nhận**
  challenge rồi ký response chứa challenge ID + seq/head. Missing/expired/reused
  challenge không chứng minh continuity. Audit reply seq < expected-at-issuance,
  hoặc equal seq nhưng head khác → quarantine **chỉ máy đó**. seq lớn hơn cần
  extension evidence của ledger được adapter/harness kiểm trước redelivery unresolved;
  thiếu continuity proof thì không tự redeliver. Credential rotation không reset
  frontier. Chủ thể giữ machine key có thể tự làm máy mình quarantine, không scope
  tới server hay máy khác. Không tin challenge plaintext chưa verify.
- Seq/hash chỉ phát hiện rollback khi một peer có frontier mới còn sống; không
  chứng minh không rollback khi tất cả peers hoặc database metadata cũng bị mất.
  Absence of alarm không là evidence continuity. Không hứa bảo vệ trước đồng loạt
  restore mọi state. Recovery/quarantine và epoch nguồn độc lập vẫn bắt buộc.
- Manifest chứa recovery_epoch mới do offline authority ký sau restore. Clients
  tải manifest qua bất kỳ transport nhưng chỉ tin chữ ký/root, sequence, OS time
  bound và epoch mới; đây là chi phí recovery/availability được lựa chọn. Nếu không
  có manifest ký mới thì giữ locked, không bootstrap cũ để rebind epoch.
- Flood bootstrap chiếm attempt_id nhìn thấy có thể gây DoS; không mở thêm quyền
  tạo ciphertext/business action. Anonymous bootstrap availability không được đảm bảo.

M draft5 có fixed fields seq/witness trong đúng bảng §4; không dùng các layout
R3/R4 chung version. machine_frontier là segment binary thứ tư, không field JSON
mơ hồ. Đây là draft chưa có public deployment/vector, version production phải chốt
lại khi suite/adapter có task contract. Responses có thể tới sai thứ tự: client chỉ
update high-water khi seq mới lớn hơn trong **cùng epoch**, bỏ qua seq thấp như
telemetry; không báo rollback từ response order. Server xử lý chỉ witness issuer hợp
lệ theo quy tắc trên. Epoch mới chuyển pending cũ sang reconciliation.

OS clock Android/máy **không mặc định đáng tin**: không coi SNTP/NITZ hay API đọc
system time là bằng chứng A0/A1 không chỉnh được. App kiểm bằng kênh time có chữ ký
server (D2-C, §6); server/Pi dùng chrony NTS. Gate deployment phải chứng minh hai
nguồn này hoạt động; nếu không thì profile hiện tại không được production.
Không thêm cơ chế “reset tuổi manifest khi tải lại” bằng elapsed time: A1 có thể
phát lại manifest cũ nhiều lần, nên cách đó không tự chứng minh expiry/freeze bound.
Suspend-inclusive elapsed chỉ phục vụ local outstanding request deadline, không
thay authenticated epoch time để kiểm manifest và timestamp.


Tests bổ sung (đặc tả, chưa chạy):

| Mã | Trace | Điều kiện |
| --- | --- | --- |
| C1a | Boot clock +1 ngày; cleanup thử chạy; sửa lùi; replay read/login/heartbeat R đã seal | Không cleanup hoặc Seal khi CLOCK_UNTRUSTED; mỗi CID tổng Seal≤1 |
| C1b | Power loss ngay sau CAS SEAL_STARTED/machine claimed | Durable record còn sau boot; nếu không chứng minh flush thì không mở production |
| C2 | Client clock lệch 1 ngày; proxy trả clock-skew hoặc fake time | Không có route time-sync miễn freshness; app không dùng lỗi để đổi clock/key validity |
| N1 | Restore epoch mới, proxy giữ manifest cũ | Protected routes locked/reject, không tự khôi phục epoch cũ hoặc reissue old ticket |
| N2 | Server restore lùi seq, peer giữ issuer witness hợp lệ; A2 khai seq=2^64−1 không witness/MAC giả | Witness hợp lệ mới quarantine; giả/thiếu/khác epoch chỉ reject packet, toàn server tiếp tục |
| N2o | Responses seq về sai thứ tự; telemetry máy seq cũ; audit reply seq thấp hơn expected-at-issuance | Không alarm từ out-of-order; máy chỉ quarantine từ fresh audit bound expected frontier |
| N3 | Flash máy image SD ledger cũ nhưng credential còn | Frontier server phát hiện seq/hash lùi; quarantined; missing frontier không là evidence đủ để redeliver unresolved command |
| N4 | Suspend trong lúc poll/verify | Deadline dùng suspend-inclusive clock hoặc invalidate context, không execute response sau deadline |

Sources thêm: [SQLite synchronous](https://www.sqlite.org/pragma.html#pragma_synchronous),
[RFC 8915 NTS](https://www.rfc-editor.org/info/rfc8915/). Những cấu hình này là yêu
cầu mới của thiết kế, chưa là cấu hình/khả năng đã xác nhận của deployment hiện tại.

## 13. Chuyển hệ thống sang profile bảo vệ (D6-A)

Người dùng xác nhận ngày 07/10/2026: hệ thống **chưa phục vụ người dùng thật**. Chuyển
toàn bộ app–server–máy của một deployment/audience trong **một đợt có điều phối qua
bảo trì**; không canary, không blue/green, không giữ song song giao thức cũ. Luồng
chi tiết, bảng hiện trạng mã, gate và nhánh lỗi ở
[d6-rollout](/home/abel/.secondbrain/projects/internproj/project1_app/archive/middleware-operator-2026-10/d6-rollout-2026-10-07.md); tóm tắt bắt buộc:

1. Kiểm kê app/máy, artifact/hash, trust/profile/schema; diễn tập với simulator hoặc máy riêng.
2. Bảo trì: chặn **mọi** producer tạo lệnh (kể cả đọc menu/kho đang tạo command) và
   mọi đường trao lệnh cho máy, kể cả long-poll đã vào; không chỉ đóng ingress.
3. Nhận nốt result trong khoảng drain có kiểm soát; `da_nhan=true`, timeout hoặc queue
   rỗng không chứng minh không tác động. Lệnh đã lấy/mất kết quả giữ unknown để đối soát.
4. Đóng legacy, cài app/image máy/server cùng profile, cấp trust/credential theo
   D1–D4, xác nhận recovery_epoch; boot ở trạng thái khóa tới khi kiểm xong.
5. Đạt đủ gate D6-G1…G7 thì mở toàn profile; máy chưa đối soát/offline giữ cách ly.

Sau mốc chuyển, mọi route còn tồn tại (auth/bootstrap, API app, heartbeat/poll/result)
đi qua lớp bảo vệ; client cũ bị chặn trước nghiệp vụ, không fallback plaintext. Bản
protected đầu tiên lỗi thì giữ bảo trì và sửa tiến — chấp nhận dừng toàn deployment
thử nghiệm tới khi sửa xong. Rollback mã sau này chỉ sang bản protected tương thích
state/epoch hiện hành; restore DB/disk là recovery theo §7/§12. Nếu có người dùng thật
trước lúc thực hiện, phải xem lại D6.
