# Thuật toán, khóa và tham số — lựa chọn nghiên cứu 07/10/2026

> **Đã chốt 07/10/2026:** người dùng chọn `D1-B, C2-B, C4-B, C1-A, C3-A, D2-C, D3-B, D4-B, D5-A, D6-A, D8-C`; thiết kế hiện hành ở [design.md §0](../packet-security/design.md). Hồ sơ dưới đây là nghiên cứu lưu trữ, gồm cả phương án bị loại.

> Bản ghi tranh luận từ log phiên: [transcript](decision-debate/transcript-sol-high-2026-10-07.md) — 77/86 tin nhắn bị runtime Codex mã hóa, không đọc được. Bản nghiên cứu dưới đây là hợp nhất; transcript giữ cả phương án ban đầu và phản biện.

Hai GPT Sol high đã đọc độc lập repo/nguồn chính thức, trao đổi và kiểm lại phương án. Các mục C1–C4 có bốn lựa chọn; C5 là bảng tham số và chính sách cần chốt, không tạo bốn con số tùy tiện. Chưa đổi design.md, chưa chọn thay bạn, chưa prototype/vectors/benchmark production.

## Phần đã quy định và phần còn mở

Thiết kế R5 đã quy định HPKE Base single-shot mỗi attempt, một chữ ký ngoài độc lập, response key/nonce Export từ chính context request, SQLite claim/CAS bền và tối đa một response Seal. Không đổi sang HPKE Auth, session handshake tự ráp, token làm key hoặc plaintext fallback. keys.md/protocol.md là hồ sơ cũ, không ghi đè design.md.

Mở: bộ HPKE, profile chữ ký root/app/máy, dependency/bridge, mức bảo vệ khóa tối thiểu; key lifecycle và hard bounds vận hành. Nguồn repo: design.md:33–63,67–114,119–160,193–225,229–270,404–447,507–544. Pubspec hiện chưa có crypto dependency; APK release còn debug signing (android/app/build.gradle.kts:33–36). Không gọi thiếu cấu hình PRAGMA là bằng chứng SQLite mặc định không FULL; deployment durability vẫn chưa kiểm.

## C1. Bộ thuật toán HPKE

HPKE kết hợp KEM tạo bí mật, KDF sinh khóa và AEAD mã hóa/xác thực nội dung. Chọn bộ có thư viện đúng và phù hợp thiết bị.

**Điều kiện:** Giữ HPKE Base một request/context và response dùng Export cùng context. Mỗi bộ có profile ID cố định, không thương lượng alg tùy client. Khóa KEM recipient ở server, không phải khóa ký Android; hai curve độc lập. KDF cả bốn là HKDF-SHA256 (0x0001), nonce 12 và tag 16 byte.

### C1-A. X25519 + AES-128-GCM ⭐

KEM 0x0020, AEAD 0x0001; enc 32 byte, khóa AEAD 16 byte.

- Cần thêm: Stack HPKE có AAD/Export ở C3.
- Ưu: enc ngắn; có vector chuẩn.
- Nhược: Cần kiểm AES trên thiết bị thật; không đồng nghĩa toàn hệ thống 256-bit security.
- Công sức ước lượng: Vừa

### C1-B. X25519 + ChaCha20-Poly1305

KEM 0x0020, AEAD 0x0003; enc 32 byte, khóa AEAD 32 byte.

- Cần thêm: Stack C3 hỗ trợ ChaCha.
- Ưu: enc ngắn; ứng viên phù hợp khi không có tăng tốc AES.
- Nhược: Tốc độ phải đo; khóa 32 byte không nâng X25519 lên mức 256-bit.
- Công sức ước lượng: Vừa

### C1-C. P-256 + AES-128-GCM

KEM 0x0010, AEAD 0x0001; enc 65 byte, khóa AEAD 16 byte.

- Cần thêm: Stack C3 hỗ trợ DHKEM P-256.
- Ưu: Có vector chuẩn và hệ sinh thái P-256.
- Nhược: enc thêm 33 byte so với A/B; không tự được Android hardware backing cho HPKE sender.
- Công sức ước lượng: Vừa

### C1-D. P-256 + ChaCha20-Poly1305

KEM 0x0010, AEAD 0x0003; enc 65 byte, khóa AEAD 32 byte.

- Cần thêm: Stack C3 hỗ trợ tổ hợp này.
- Ưu: Kết hợp backend P-256 với AEAD không dựa tăng tốc AES.
- Nhược: enc lớn hơn; phải đo latency/packet thay vì suy từ tên thuật toán.
- Công sức ước lượng: Vừa

**Khuyến nghị có điều kiện:** A là thứ tự prototype đầu; B nếu số đo cho thấy ChaCha phù hợp hơn. C/D nếu dependency hoặc backend cần P-256. Chưa có benchmark để gọi bộ nào nhanh nhất.

**Nguồn:** [RFC9180: suite và vectors](https://www.rfc-editor.org/rfc/rfc9180.html#appendix-A)

## C2. Thuật toán chữ ký theo vai

Root ký manifest; app và máy ký request bằng credential riêng. Chữ ký không dùng chung khóa với HPKE.

**Điều kiện:** Mọi khóa tách purpose/kid và chủ thể. Ed25519 thuần ký canonical bytes, sig 64 byte. P-256/SHA-256 ký canonical bytes qua API hash đúng một lần; wire r||s 64 byte, low-s, không nhận DER/trailing/high-s. Không prehash thêm trước SHA256withECDSA. Root algorithm độc lập kiểu giữ root D1.

### C2-A. Root Ed / app P-256 / máy P-256 ⭐

Root Ed25519; credential app và máy ECDSA P-256/SHA-256.

- Cần thêm: Android Keystore bridge; signer root Ed tương thích; Python verify.
- Ưu: App theo đường Keystore P-256 phổ biến; máy phù hợp TPM P-256 nếu dùng.
- Nhược: Hai thuật toán và chuyển DER→raw/low-s cần vector liên thông.
- Công sức ước lượng: Vừa

### C2-B. Root P-256 / app P-256 / máy P-256

ECDSA P-256/SHA-256 cho ba vai, mỗi vai vẫn có key riêng.

- Cần thêm: Signer root P-256 và Keystore/TPM adapter nếu dùng.
- Ưu: Một họ thuật toán; nhiều token/HSM hỗ trợ.
- Nhược: Phải giữ hash/encoding/low-s chính xác ở mọi API; không dùng một key cho ba vai.
- Công sức ước lượng: Vừa

### C2-C. Root Ed / app Ed / máy P-256

Root và app Ed25519; máy P-256. App Ed hardware chỉ được nhận khi khả năng thực đã kiểm.

- Cần thêm: Ed signer app native/software và bảo vệ private key; signer root Ed.
- Ưu: Ed có chữ ký cố định, không xử lý DER ở app.
- Nhược: Không mặc định Ed trong TEE/StrongBox. Software Ed phải wrap bằng key Keystore, private signing key vào RAM app, yếu hơn non-exportable signer.
- Công sức ước lượng: Vừa–cao

### C2-D. Root P-256 / app Ed / máy P-256

Root và máy P-256; app Ed25519 có cùng điều kiện hardware/software như C.

- Cần thêm: Root P-256 và app Ed signer/storage riêng.
- Ưu: Phù hợp root token P-256, app dùng Ed khi có lý do rõ.
- Nhược: Hai họ thuật toán; app Ed chưa chứng minh tương thích hardware fleet và C4 strict tiers.
- Công sức ước lượng: Vừa–cao

**Khuyến nghị có điều kiện:** A nếu root token hỗ trợ Ed và app TEE P-256 đạt; B nếu muốn thống nhất P-256. C/D chỉ khi chấp nhận và kiểm được điều kiện Ed-app.

**Nguồn:** [Android Keystore](https://developer.android.com/privacy-and-security/keystore) · [RFC8032 Ed25519](https://www.rfc-editor.org/rfc/rfc8032.html) · [YubiKey 5.7](https://docs.yubico.com/hardware/yubikey/yk-tech-manual/yk5-firmware-5.7.html)

## C3. Thư viện và cách nối Flutter–Python

Cần API HPKE context, AAD và Export. Chỉ có hàm encrypt/decrypt không đủ cho response theo thiết kế.

**Điều kiện:** Bốn stack dưới là ứng viên, chưa pin/build/vectors/benchmark đạt. A/B qua Kotlin MethodChannel cần bạn mở rộng fallback FFI ở design.md:59–63. C/D dùng FFI đúng hướng fallback hiện tại. Không tự ghép HPKE từ primitive. Keystore signer là adapter riêng, không phải BC/Rust giữ khóa ký thay Keystore.

### C3-A. Bouncy Castle Android + PyHPKE — đổi quy định

BC HPKE qua Kotlin MethodChannel; server và Pi dùng PyHPKE context/AAD/Export.

- Cần thêm: BC Java package, Kotlin bridge, PyHPKE và dependencies Python.
- Ưu: Không cần thêm Rust/C toolchain ở Android; dễ thử với Kotlin/Python.
- Nhược: MethodChannel không phải FFI; PyHPKE upstream chưa audit; hai implementation cần kiểm liên thông.
- Công sức ước lượng: Vừa

### C3-B. Bouncy Castle Android + OpenSSL — đổi quy định

BC qua Kotlin; server/Pi gọi OpenSSL ≥3.2 HPKE C API bằng binding.

- Cần thêm: BC/Kotlin; OpenSSL native và binding Python.
- Ưu: Tránh phụ thuộc PyHPKE nếu muốn native backend.
- Nhược: Đổi fallback như A; thêm C ABI/build/backend packaging.
- Công sức ước lượng: Cao

### C3-C. Rust HPKE FFI + PyHPKE ⭐

Rust hpke qua Flutter FFI/bridge; server/Pi PyHPKE.

- Cần thêm: Rust/Android NDK, FFI bridge, crate hpke, PyHPKE.
- Ưu: Giữ fallback FFI; có API/vectors để prototype.
- Nhược: Toolchain mới và hai implementation; chưa audit liên thông/build thiết bị.
- Công sức ước lượng: Cao

### C3-D. OpenSSL FFI cả hai phía

Flutter FFI và Python binding dùng OpenSSL ≥3.2 HPKE context/AAD/Export.

- Cần thêm: OpenSSL native cho ABI Android/Pi/server; C wrapper và bindings.
- Ưu: Một crypto engine cho cả hai phía; giữ fallback FFI.
- Nhược: C ABI/packaging/update nặng; system OpenSSL có thể thiếu phiên bản/API cần dùng.
- Công sức ước lượng: Cao

**Khuyến nghị có điều kiện:** C nếu giữ fallback FFI và nhóm nhận Rust; A nếu nhóm quen Kotlin/Python và bạn đồng ý mở fallback sang platform channel. Không chọn production chỉ từ danh sách API.

**Nguồn:** [BC HPKEContext AAD/Export](https://downloads.bouncycastle.org/java/docs/bcprov-jdk18on-javadoc/org/bouncycastle/crypto/hpke/HPKEContext.html) · [PyHPKE upstream](https://github.com/dajiaji/pyhpke) · [Rust hpke](https://docs.rs/hpke/latest/hpke/) · [OpenSSL3.2 HPKE](https://docs.openssl.org/3.2/man3/OSSL_HPKE_CTX_new/) · [Pyca public HPKE API](https://cryptography.io/en/49.0.0/hazmat/primitives/hpke/)

## C4. Mức bảo vệ private key tối thiểu

Chọn mức thiết bị bắt buộc có, rồi từ chối enrollment khi không đạt. File mã hóa và hardware-backed signer có bảo đảm khác nhau.

**Điều kiện:** Root theo D1: offline với A/B/C; Cloud KMS online chỉ sau khi bạn chọn D1-D và chấp nhận sửa thiết kế. APK release key riêng. A áp dụng Keystore signer cho P-256; Ed software ở C2-C/D là ngoại lệ được chọn rõ: key wrapped, vào RAM, không non-exportable signer. B/C/D chỉ nhận Ed app nếu chứng minh TEE/StrongBox hỗ trợ thật; hiện chưa có bằng chứng. TPM signing không thay ledger bền/chống rollback.

### C4-A. Keystore best effort + file khóa riêng

App P-256 dùng Android Keystore, security level có thể software hoặc TEE; máy/server file owner riêng, 0600, backup có kiểm soát.

- Cần thêm: Keystore bridge; file permissions/backup; Ed software cần wrapping và signer riêng nếu chọn.
- Ưu: Ít phần cứng/cài thêm.
- Nhược: Không bắt buộc hardware; rooted OS/SD clone ngoài bảo đảm. Ed software có key trong RAM.
- Công sức ước lượng: Thấp–vừa

### C4-B. TEE app bắt buộc + file máy/server ⭐

Khóa ký app phải ở TEE (hoặc mức cao hơn) đã kiểm: P-256 là baseline; Ed chỉ khi chứng minh hỗ trợ. Máy/server giữ key file 0600.

- Cần thêm: Keystore security-level gate; không thêm TPM bắt buộc.
- Ưu: Mốc nhẹ cho intern mà app có hardware-backed signing.
- Nhược: Từ chối điện thoại không đủ; máy/server vẫn có rủi ro sao chép file.
- Công sức ước lượng: Vừa

### C4-C. TEE app + hardware signing trên máy

App đạt TEE; máy P-256 dùng TPM/secure element non-exportable; server key file riêng.

- Cần thêm: TPM/secure element mỗi máy, driver/binding và provisioning.
- Ưu: Giảm clone private signing key qua SD máy.
- Nhược: Tăng BOM/tích hợp; không bảo vệ ledger chỉ bằng TPM, server key vẫn file.
- Công sức ước lượng: Cao

### C4-D. StrongBox app + hardware máy/server

App bắt buộc StrongBox đã kiểm, máy hardware signer; server private key at-rest sealed bằng TPM hoặc cơ chế tương đương.

- Cần thêm: Thiết bị StrongBox, phần cứng máy/server, tích hợp/provisioning.
- Ưu: Mức phần cứng bắt buộc cao hơn cho fleet được quản lý.
- Nhược: Server unseal vào RAM để decap không chống root/process compromise; coverage và chi phí cao; Ed StrongBox chưa chứng minh.
- Công sức ước lượng: Cao

**Khuyến nghị có điều kiện:** B nếu fleet P-256/TEE thực đạt; A cho pilot chấp nhận software protection. C khi cần giảm clone SD máy; D khi quản lý được fleet phần cứng nghiêm ngặt.

**Nguồn:** [Android Keystore](https://developer.android.com/privacy-and-security/keystore) · [Android attestation](https://developer.android.com/privacy-and-security/security-key-attestation) · [TPM ECDSA/P-256](https://tpm2-tools.readthedocs.io/en/latest/man/tpm2_create.1/)

## C5. Key map, tham số và lifecycle

Độ dài mật mã theo chuẩn/profile; thông số vận hành cần bound và số đo. Không chọn bốn TTL hoặc bốn độ dài tag để lấp số lượng option. Những công thức dưới đây là ngân sách thiết kế có giả định, không phải số đo hay giá trị production.

### Tổ hợp và phụ thuộc cần giữ

| Tổ hợp | Điều kiện |
| --- | --- |
| C2-A/B + C4-B | Ứng viên P-256/TEE nhẹ cho app; xác minh security level từng loại máy. |
| C2-C/D + C4-A | Ed app software chỉ khi bạn chấp nhận key wrapped bằng AES Keystore và plaintext trong RAM; không gọi non-exportable Ed signer. |
| C2-C/D + C4-B/C/D | Chưa chứng minh tương thích; chỉ dùng khi Ed TEE/StrongBox được kiểm trên fleet. Không tự hạ xuống software. |
| C3-A/B | Cần bạn mở fallback FFI sang MethodChannel; chưa tự sửa design. |
| C1 bất kỳ + C3 bất kỳ | Phải kiểm đúng suite/mode/AAD/Export/vector. Có API không phải bằng chứng build/interop/production. |

### Ai giữ khóa nào

| Khóa | Thuật toán/độ dài | Nơi giữ | Đổi/thu hồi |
| --- | --- | --- | --- |
| Root ký manifest | Ed25519 hoặc P-256 theo C2; private material theo token/thư viện, không raw key tự ghép | Theo D1: A/B/C offline; D Cloud KMS online chỉ khi bạn chấp nhận đổi thiết kế. Public root trong APK/image, không ở proxy | Root rotation qua trusted release; root bị lộ cần kênh recovery độc lập. |
| APK release key | Keystore ký APK riêng, không dùng root packet | Máy/CI phát hành có kiểm quyền | Release hiện còn debug key; phải sửa trước phát hành trusted package. |
| Server HPKE recipient | X25519/P-256 theo C1; enc 32/65 byte | Private server, public trong manifest ký root | Active/retiring/revoked; không coi rotation là PFS. |
| Credential app | Ed25519/P-256 theo C2, sig wire 64 byte | Mỗi installation; C4 quy định signer/storage | Bind user/session+PoP; đổi key dùng credential cũ hoặc recovery mạnh. |
| Credential máy | P-256/SHA-256 theo C2, sig wire 64 byte | Mỗi máy; file riêng hoặc hardware C4 | Bind physical ID; đổi key không đổi namespace operation/command ledger. |
| HPKE sender ephemeral | Thư viện sinh CSPRNG mỗi attempt, không reuse enc chủ động | App/máy RAM, không backup context | Một request Seal/context; retry tạo attempt/context mới. |
| Response key + nonce | Export labels riêng; key 16/32 theo C1, nonce12 | Hai endpoint RAM, không proxy/backup | CAS bền trước một response Seal; lỗi/crash không Seal lần hai. |
| Ticket MAC key | Đề xuất HMAC-SHA256, key CSPRNG 32 byte và full tag32; chưa chốt | Server riêng purpose, không bearer token, không root | Đổi epoch/ticket key sau restore; ticket cũ bị reject. |
| Witness kw | HMAC-SHA256 đã quy định; đề xuất key CSPRNG32, witness32 | Server riêng purpose, ổn định trong recovery_epoch | Giữ khả năng verify committed witness trong epoch; quản trị backup/restore. |

### Tham số cố định theo RFC hoặc thiết kế

| Tham số | Giá trị | Ý nghĩa/giới hạn |
| --- | --- | --- |
| HPKE mode | Base 0x00, một request/context | Đã quy định hướng; không dùng Auth để bỏ chữ ký. |
| AEAD nonce/tag | 12 / 16 byte ở cả bốn C1 | Nonce là nội bộ HPKE/Export, khác attempt_id; không rút tag. |
| Chữ ký wire | 64 byte Ed25519 hoặc P-256 raw r||s low-s | Production profile phải freeze encoding/hash và negative vectors. |
| attempt / operation / recovery epoch | 16 byte mỗi loại | Attempt CSPRNG mới; operation server cấp; epoch ngoài rollback domain. |
| CID/fingerprint/frontier hash | SHA-256, 32 byte | Purpose/domain khác nhau; giữ canonical byte hợp đồng. |
| Witness | 32 byte MAC; JSON base64url unpadded43 ký tự | Trong M là raw bytes; không base64 kép. |
| Timestamp/sequence | uint64_be trong M; server_seq JSON decimal string | Không JSON double cho uint64. |
| Frame LP / version | LP uint32_be length; draft5 uint16_be0x0005 | Draft nội bộ, chưa production version; bound byte và reject trailing/duplicate. |

### Thông số vận hành chưa được đo

| Nhóm | Chính sách/công thức đề xuất | Dữ liệu cần có |
| --- | --- | --- |
| Δ_future, Δ_past, σ và clock drift | Lấy bound xác minh được của clock app/server và độ trễ. Ngân sách thảo luận Δ_future ≥ εclient+εserver+drift; Δ_past thêm bound network/queue phù hợp route. | D2 time thật sau boot/suspend, worst-case clock/error/delay; p99 không phải maximum an toàn. |
| L_max mỗi route, poll deadline | issued_at trong cửa sổ Δ; expires_at≥now; span≤L_max. p99 giúp chọn hard cap, packet vượt cap reject. Poll cap phải đủ wait/verify/admit được bound. | Server hiện POLL_WAIT8s, machine HTTP timeout10s, command timeout20s chỉ là config cũ, không packet TTL production. |
| Replay retain / dung lượng | Retain tới expires_at+safety_clock_bound+cleanup_margin. Horizon phân tích H≤L_max+Δ_future+σ+margin theo giả định thiết kế; records≤burst+ceil(rate·H). | Peak/burst/QPS, row size SQLite, disk budget; đầy thì fail closed, không đuổi record sống. |
| Payload/header/JSON/kid/audience bounds | Cap outer trước crypto; cap từng inner segment, depth/count; cap pending context và crypto concurrency. Không lấy LP uint32 max làm cap thực. | Max menu/list/status payload, RAM budget, wire sizes; GET-header cap chỉ khi chọn D8-A. |
| Manifest cadence/validity, server key epoch/overlap | Cadence+slack ký trễ≤max_manifest_validity do trust package enforce; retiring decap chỉ trong key/manifest validity và absolute packet expiry. Hard cap inflight/overlap; revoked không tiếp tục như retiring. | Ai ký/D1; outage/thu hồi chấp nhận; D2 uncertainty; không đặt số ngày rồi gọi đã đo. |
| Credential rotation/revoke và restore | Rotation không reset ledger/physical ID/epoch. Credential revoked reject sau verify trước claim dù key HPKE còn. Restore đổi epoch+ticket key ngoài rollback domain. | Recovery D4, backup có kiểm soát, durable frontier/unknown reconciliation. |

### Chi phí byte tính được

Overhead có thể tính trước, không phải benchmark: với ciphertext gồm tag16 và chữ ký64, outer draft5 có 18 byte framing. Request protected = 18 + |M| + |enc| + |plaintext_inner_frame| + 16 + 64 byte; tương ứng 130 + |M| + |plaintext_inner_frame| với X25519, 163 + |M| + |plaintext_inner_frame| với P-256. Bootstrap không có chữ ký trừ64. Chưa gồm HTTP/TLS, không suy latency từ số byte.

### Điều kiện kiểm trước production

- Pin package/version và API thật: SetupBase, info, AAD, enc, Export riêng labels; không chỉ encrypt/decrypt.
- RFC vectors gồm Export; Dart/native–Python byte-exact cho từng C1/C2; DER/raw/low-s, invalid key/point/signature, malformed/trailing/duplicate frames.
- Gate response Seal và claim/CAS bền qua concurrency/crash/restore/clock/full store; thư viện stateful không tự thực thi one-response rule.
- Inventory Android KeyInfo/TEE/StrongBox và Pi/TPM; build/packaging/latency/peak RAM/DB trên thiết bị thật; test/harness chỉ đặt trong tests/ sau user chốt phạm vi.

**Chưa chốt thêm:** canonical manifest bytes/production profile IDs/version và bound field lengths phải được freeze khi chọn suite/caller; không tự cập nhật design.md trong lượt nghiên cứu.

**Nguồn tham số:** [design.md](../packet-security/design.md) §2–10, §12; [RFC9180](https://www.rfc-editor.org/rfc/rfc9180.html), [RFC8032](https://www.rfc-editor.org/rfc/rfc8032.html).

**Hồ sơ tranh luận:** [crypto-debate-sol-high-2026-10-07.md](decision-debate/crypto-debate-sol-high-2026-10-07.md).

## Trạng thái review cuối

Critic đã đọc bản hợp nhất sau sửa: không còn blocker nội dung; JSON/MD/HTML có 16 option khớp. Kiểm ảnh desktop/mobile và PDF bảng khóa tại vùng lấy mẫu đạt, chưa rà toàn PDF. Đây là review shortlist có điều kiện, chưa nghiệm thu crypto production. [UI evidence](crypto-ui-evidence-2026-10-07.json).
