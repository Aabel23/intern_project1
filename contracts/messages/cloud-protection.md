# Cloud protection v1 · TLS + phong bì bên trong

> **Cập nhật 12/10/2026:** `v2-decisions.md` (D1–D10, cách 3 trên version1.1) thắng mọi chỗ mâu thuẫn với file này.

User chốt giữ hai lớp ngay skeleton ngày 12/10/2026. Không TLS-only, không mTLS/chứng chỉ xưởng. Server mở phong bì từng chặng, kiểm phiên/quyền và đóng phản hồi của poll; không tự đọc trạng thái thay máy. Đây là lựa chọn kỹ thuật Planner theo cryptography.html; không mở LAN/BT vận hành.

## Bộ thuật toán / thư viện

- HTTPS kiểm CA/cert/hostname; server Python `ssl.SSLContext(PROTOCOL_TLS_SERVER)` minimum TLS1.2 (TLS1.3 được dùng nếu có), cert công cộng do Operator cấp qua đường cấu hình, không self-signed bypass. Private cert/HPKE/signing files 0600, không commit. Một server, `http.server.ThreadingHTTPServer` + semaphore 64 active requests; HTTP body max64KiB, read timeout30s. Không Flask/FastAPI/Redis.
- HPKE RFC9180 mode_base, DHKEM(X25519,HKDF-SHA256) id32, HKDF-SHA256 id1, AES128GCM id1. Server/Pi PyHPKE 0.6.5, cryptography; Kotlin Bouncy Castle bcprov-jdk15to18 1.86 qua MethodChannel `flexmix/crypto`; không Dart primitive. X25519 public raw32 bytes; enc raw32 bytes. Server một key kid=`server-hpke-1`.
- Máy ký ECDSA P256/SHA256. Private PKCS8 PEM; public SEC1 uncompressed65 bytes base64url. Signature wire raw r||s64 bytes, normalize low-s; verifier từ chối high-s/non64/zero/out-of-range. Không DER trên wire. Coder dùng cryptography encode/decode_dss_signature và thư viện Kotlin chuẩn, không tự elliptic arithmetic.
- Public server HPKE/signing pins phân phối cùng app asset `assets/server-trust.json` và cấu hình máy public `server-trust.json` trước bán; không private key xưởng. App trust không nhận từ API unsigned. Không rollover/remote manifest trong skeleton; đổi pin phải cập nhật build/config cả ba phía và có review.

## Encode byte chuẩn

`b64u` = base64url RFC4648 không padding, decoder kiểm roundtrip; `J(x)` = UTF8 JSON **array** compact không whitespace, ASCII strings chỉ domain/route/ID/kid, ints decimal. Không canonical object JSON. Body plaintext bất kỳ JSON v1 đúng từng hợp đồng, không cần canonical bởi signature bao phủ ciphertext bytes.

HTTP POST body envelope object chỉ `{pv,route,method,receiver,kid,send_id,sent_at_ms,machine_key_id,enc,ct,sig}`. pv=1; method=`POST`; receiver=`server`; send_id UUIDv4 mới **mỗi lần gửi HTTP**, khác request_id/claim_id; sent_at_ms integer UTC epoch ms; machine_key_id string hoặc null; sig string hoặc null. AAD=J([1,route,"POST","server",kid,send_id,sent_at_ms,machine_key_id]); info ASCII `flexmix-cloud-v1`. HPKE enc/ct b64u; ký bytes J(["flexmix-machine-envelope-v1",b64u(AAD),enc,ct]); các chuỗi enc/ct đã validated encoding. App sig=null,machine_key_id=null. Máy sau bind keyid đúng serial bound, sig bắt buộc. Activation challenge chưa bind dùng null; activation bind gửi machine key mới trong plaintext, sig trên envelope kiểm bằng chính key mới **sau** kiểm proof mã+challenge, không tin trước.

Plaintext `{auth,body}`: app authenticated auth={access_token}; anonymous auth=null; máy auth=null; body là payload v1. Refresh token/password/OTP/seal_code nằm bên trong encrypted body, không header. Header route trùng HTTP path; kid/receiver/method sai→reject. Không client user_id tự khai thay auth context.

Server kiểm size/route/kid/pv→machine outer signature nếu đã bound→HPKE open→sent_at_ms lệch <=300000ms→replay send_id→body/schema→auth/permission→handler. Anonymous registration cũng có phong bì. Replay cache (kid,send_id) 10 phút RAM, max10000, full từ chối RATE_LIMITED không evict live entries. Mỗi retry HTTP dùng context/send_id mới nhưng giữ request_id/claim_id nghiệp vụ. Client trước request đầu gọi time bootstrap bên dưới; không yêu cầu Pi có NTP/đồng hồ OS đúng. Không bypass sent_at với handler có tác dụng. Public lỗi trước open chỉ `{pv:1,error:{code:"INVALID_ENVELOPE"|"UNSUPPORTED_VERSION"|"UNKNOWN_KEY"|"RATE_LIMITED"}}`; không detail mở mã/chữ ký. Handler errors sau open phải trả phong bì.

## Phản hồi

HPKE receiver context export(ASCII `flexmix-response-v1`,16) = response AES128 key, **không** dùng sender context.seal ở hướng ngược. Một context cho một request/response duy nhất. Random nonce12 bytes CSPRNG; response AAD=J(["flexmix-response-v1",send_id,http_status,route]); AESGCM encrypt plaintext response hợp đồng v1, ct gồm tag16. HTTP body `{pv:1,send_id,status,nonce,ct}` base64url nonce/ct. App/máy kiểm send_id/status/AAD và decrypt exporter; không chấp nhận success plaintext. Gói poll mang command bên trong response này, nên chỉ máy khởi tạo poll mở được. Kết quả máy gửi bằng request HPKE mới có chữ ký; server kiểm pending+identity rồi đóng response app bằng exporter context app đang chờ. Vì vậy cả request và response qua proxy vẫn ciphertext.

## Bootstrap serial → public key

MACHINE_ACTIVATION_SEND step=`challenge`, v,serial (không auth): HPKE/TLS unsigned; server tra factory serial, cấp challenge_id/nonce32 random/expires_at120s + server_time_ms, purpose=`bind_machine_key`. Unknown serial MACHINE_UNTRUSTED. Rate limit 5/serial/phút+20/IP/phút. Challenge lưu bền activation_challenges bound serial; pending không owner.

step=`bind`, v,serial,challenge_id,seal_code b64u32,public_key b64u65,proof raw64. Factory verifier=SHA256(ASCII `flexmix-seal-v1`||0x00||UTF8 serial||0x00||raw S32), so constant-time. Server giữ verifier, **không dùng verifier làm HMAC key**. Seal chỉ HPKE/TLS tới backend. Proof ký J(["flexmix-bind-v1",serial,public_key,challenge_id,nonce,expires_at]) bằng private mới. Server kiểm challenge serial/hạn/once, verifier, proof và outer signature key mới; atomic bind unique serial. Same key bind retry chỉ khi cùng challenge đã commit lưu result durable trong bảng activation_challenges, khác key KEY_CONFLICT; không chủ. Consume challenge và bind transaction. Không ai tự khai serial được hãng tin. Mã S32 nằm factory máy+QR niêm phong; user không cần nhập tay. Người có cả mã và máy trước người mua có khả năng nhận chủ, rủi ro user đã chấp nhận; không thêm quy trình recovery.

Server claim signing P256 key=`server-sign-1` pinned máy. challenge_signature trên J(["flexmix-claim-v1",claim_id,machine_id,user_id,purpose,nonce,expires_at]); proof máy trên J(["flexmix-claim-accept-v1",base64url(challenge_bytes),local_session_binding]) bằng bound machine key. Begin lấy user_id từ auth; complete kiểm account, machine key bound, challenge original, UUIDv4 local_session_binding nằm trong chữ ký máy và transaction owner. Server không trực tiếp kiểm BT transcript, key confirmation hay radio; dựa vào máy chỉ ký sau gate phiên bt-claim.md. local_session_binding=UUIDv4 phiên BT đã qua app confirm/machine ACK; máy kiểm phiên/generation còn sống trước ký.

## Kiểm tương thích bắt buộc

S-01/A-01 trước review phải có vector HPKE RFC9180 chính thức đúng suite mode_base, cùng fixture request→response exporter kiểm Python↔Kotlin hai hướng. mode_psk cho BT không là gate của hai phiếu account; M-01/BT chỉ phát vector và implementation theo profile đã chốt khi cổng B-03 mở. Fixture test có seed/key cố định **test-only**, không factory/production key. Header/route/kid/send_id/ciphertext/signature sửa một byte phải fail; wrong key/tag/export context fail; replay fail; low-s kiểm. Không chỉ roundtrip một thư viện. Wire fixture sau triển khai ở `tests/fixtures/crypto/` do S-01 giữ, A/M chỉ đọc; expected bytes từ vector chuẩn, không code tự sinh oracle.

Nguồn API kiểm: [PyHPKE](https://pyhpke.readthedocs.io/en/latest/api.html), [BC HPKE](https://downloads.bouncycastle.org/java/docs/bcprov-jdk18on-javadoc/org/bouncycastle/crypto/hpke/HPKE.html), [BC exporter](https://downloads.bouncycastle.org/java/docs/bcprov-jdk18on-javadoc/org/bouncycastle/crypto/hpke/HPKEContext.html). Tương thích Android BLE/PSK cần báo cáo feasibility trước phát coder, không tự bỏ lớp trong khi build fail.

## Đồng hồ bootstrap không phụ thuộc RTC/NTP

S-01 thêm USER_SESSION_BOOTSTRAP=/app/user/session/bootstrap. App request HPKE base anonymous body={v:1}, header sent_at_ms=0; server chỉ cho route này đọc time, response encrypted data={server_time_ms}. Không user/session/permission write. Máy unbound activation step challenge sent_at_ms=0; máy bound dùng MACHINE_HELLO_SEND body={v:1} outer signed key bound và sent_at_ms=0, response data={server_time_ms}. Hello không đánh online (chỉ poll). Các ngoại lệ timestamp0 phải kiểm body/route sau decrypt trước handler, không áp cho bind/register/login/relay. Bootstrap rate20/IP/phút, timeout5s, HTTP response exporter như mọi route. Client ghi server_time_ms + monotonic receipt; request sau sent_at_ms=server_time_ms+(monotonic-now minus receipt), không dùng OS wall clock. Roundtrip quá5s từ chối, gọi lại; client refresh time trước request tiếp theo khi cache đã đủ5 phút hoặc chưa có cache (restart). Wire INVALID_ENVELOPE không phân biệt clock skew nên không có trigger clock-skew tự động; khi nhận lỗi này client invalidates time cache để lần gọi do caller khởi tạo tiếp theo bootstrap lại, nhưng không tự retry request vừa lỗi. Caller retry mới giữ ID nghiệp vụ nếu hợp đồng route có ID; account write chưa idempotent không auto replay. Mỗi request vẫn send_id/context mới; restart process phải bootstrap lại. Hạn claim server dùng server-time offset này, expiry timer monotonic. Không vô tình làm NTP/RTC thành gate nhận máy.


## Asset trust và runtime provision (S-01/A-01)

JSON public asset/config đúng schema (không trường lạ): `{ "v":1, "hpke":{ "kid":"server-hpke-1", "public_key":"<b64u raw32>" }, "signing":{ "kid":"server-sign-1", "public_key":"<b64u SEC1 uncompressed65>" } }`. Signing pin chưa dùng trong account nhưng cùng schema cho máy. Placeholder không phải pin và phải fail startup. Operator cung cấp public bytes từ runtime private keys đã provision, qua file cục bộ; không tải pin từ server, không tự sinh pin production. Server load đối chiếu public derivation với public trust config; không khớp fail startup. App asset thiếu/sai fail initialization với lỗi cấu hình; tuyệt đối không HTTP fallback.

HTTPS app base origin lấy `--dart-define=FLEXMIX_SERVER_BASE_URL=https://<hostname>[:port]`; bắt buộc https, hostname, không userinfo/query/fragment/path ngoài `/`; không default localhost. HTTP path nối route hằng, không redirect: 3xx là transport error. Server bind host/port không quyết public hostname; Operator cấp DNS/cert/URL phù hợp. Development/test keys chỉ nằm fixture/test runtime tách riêng và không dùng làm pin build nghiệm thu.

Context request client TTL30 giây kể từ seal bằng monotonic; one-use openResponse xóa context cả success/decrypt/schema failure; clearContext idempotent. HTTP app account timeout10s, bootstrap5s; finally clear context trên mọi network/parse failure. Max64 contexts native in-flight, đầy trả local CONTEXT_LIMIT (không gửi mạng). Server exporter chỉ giữ trong request object, hủy khi đã close_response hoặc request kết thúc; không global map context. Response body size64KiB; plaintext16KiB; cấu trúc envelope chặt không field lạ.

RAM replay/rate/HTTP capacity state thuộc một process server, tạo một lần khi boot và truyền qua `Dependencies.state` (phiếu S-01). Thread handlers dùng chung state có lock; không global registry hoặc state riêng mỗi request. Restart xóa RAM state theo skeleton; nhiều workers/process không nằm trong phạm vi. Replay cache prune/check/insert atomic; crypto và handler không giữ state lock.


Exporter server one-response là invariant của HTTP lifecycle: dispatcher gọi close_response đúng một lần cho OpenedRequest, HTTP handler bỏ reference trong finally. `close_response` là helper nội bộ thuần encrypt, không public API/state machine; không yêu cầu mutable consumed flag hoặc phát hiện lời gọi trực tiếp lần2. Test xác minh HTTP không gọi lần2 và không tái dùng OpenedRequest cho request khác. Native client handle one-use vẫn enforced như đã khóa, kể cả decrypt fail.

## Activation retry sau Wi-Fi success (user chốt12/10/2026)

Association+DHCP thành công nhưng server lỗi/offline: máy giữ Wi-Fi mới và tự thử activation lại theo bt-claim.md, không rollback mạng cũ. Retry dùng identity/S đã provision, không cần app giữ QR/BT context; mỗi HTTP attempt fresh HPKE context/send_id, pending bind retry giữ cùng challenge_id/key để bảo toàn idempotent commit. Không auto retry MACHINE_UNTRUSTED/KEY_CONFLICT/proof/config error, không tự đổi identity. Owner/claim vẫn cần phiên BT mới hợp lệ và server transaction.

Cổng M-01/B-03 còn BLOCKED: retry timer/budget, pending-challenge durability/restart và expiry/result recovery cho commit chưa biết chưa được Planner khóa. Không sinh challenge mới khi chưa xác định bind cũ đã commit, không lưu seal_code trong file retry. OS/network manager discovery làm khi có Pi thật, không yêu cầu user chốt OS lúc này.
