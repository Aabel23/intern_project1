# Phương án cho các quyết định mở D1–D6, D8 — 07/10/2026

## Bản lựa chọn đã phản biện — GPT Sol high, 07/10/2026

Hai agent `gpt-6-sol`, effort `high`: researcher và critic đọc độc lập rồi trao đổi trực tiếp. Không còn lỗi chặn logic shortlist trong phạm vi review; **người dùng chưa chọn, thiết kế chưa đổi**. Chưa prototype, đo hoặc nghiệm thu production. Lượt GPT cũ lỗi sandbox được giữ bên dưới, không coi là đã đọc/review.

⭐ là khuyến nghị có điều kiện. D7 không nằm trong bộ quyết định được giao; không tự tạo thêm.

### D1. Ai giữ khóa root ký manifest

Root là khóa gốc để app/máy tin khóa server. Lộ root có thể làm manifest giả trở thành hợp lệ.

**Ràng buộc/điều kiện:** A/B/C giữ root offline. D sửa quy định root offline; chỉ áp dụng nếu bạn chấp nhận đổi ranh giới tin cậy. Mọi lựa chọn cần APK release keystore riêng; app hiện còn dùng debug signing. Cadence, thời hạn manifest và người giữ khóa chưa chốt.

#### D1-A. Hai token phần cứng ⭐

Mỗi token sinh root riêng, không xuất private key; trust package nhận 1-of-2. Ký trên máy quản trị cách ly, token dự phòng ở nơi khác.

- Cần thêm: 2 hardware token; bộ công cụ ký/token.
- Ưu: Khó sao chép private key; có dự phòng.
- Nhược: Một token bị lộ vẫn đủ ký; phải bảo quản PIN và máy ký.
- Công sức tương đối (ước lượng, không phải số đo): Vừa

#### D1-B. Máy ký air-gapped

Máy không nối mạng giữ file khóa mã hóa bằng passphrase, backup tại hai nơi. Chuyển manifest đã ký qua phương tiện kiểm soát.

- Cần thêm: 1 máy offline nếu chưa có; 2 phương tiện backup; script ký.
- Ưu: Không phải mua token; đúng root offline.
- Nhược: File có thể bị sao chép; rủi ro USB và thao tác backup.
- Công sức tương đối (ước lượng, không phải số đo): Vừa

#### D1-C. Ngưỡng 2 trong 3

Ba người giữ ba root độc lập; client chỉ nhận manifest đủ hai chữ ký hợp lệ.

- Cần thêm: 3 nơi giữ khóa; định dạng/validator nhiều chữ ký.
- Ưu: Lộ hoặc mất một khóa chưa đủ chiếm quyền ký.
- Nhược: Cần quorum, ceremony và cập nhật trust package/validator.
- Công sức tương đối (ước lượng, không phải số đo): Cao

#### D1-D. Cloud KMS — đổi thiết kế

Root không xuất khỏi KMS; người vận hành ký qua IAM/MFA và audit. Private root nằm ở dịch vụ online.

- Cần thêm: 1 dịch vụ KMS, IAM/MFA, SDK và chi phí dịch vụ.
- Ưu: Ký từ xa và có audit quản trị.
- Nhược: Trái root offline hiện hành; phụ thuộc cloud/control plane, MFA không biến root thành offline.
- Công sức tương đối (ước lượng, không phải số đo): Vừa

**Khuyến nghị/tiêu chí chọn:** A nếu có ngân sách token; B nếu cần giảm mua phần cứng. C khi có ba người giữ độc lập.

**Nguồn:** [Thiết kế §3](../packet-security/design.md) · [YubiKey 5.7](https://docs.yubico.com/hardware/yubikey/yk-tech-manual/yk5-firmware-5.7.html) · [AWS KMS key specs](https://docs.aws.amazon.com/kms/latest/developerguide/symm-asymm-choose-key-spec.html)

### D2. Nguồn thời gian app dùng để kiểm OS clock

Manifest và freshness cần giờ UTC đáng tin. Giờ sai có thể làm khóa cũ còn hợp lệ hoặc khóa mọi luồng.

**Ràng buộc/điều kiện:** Server/Pi dùng chrony NTS đã kiểm. Mọi A/B/C/D xác minh OS clock sau boot và khi hết giới hạn offline/drift; lệch thì fail closed mọi route Seal, sửa giờ OS rồi kiểm lại. Không tự chỉnh giờ từ lỗi HTTP. Android app thường không có quyền đặt OS clock. D2 không tự chọn Δ/Lmax: phải đo.

#### D2-A. Roughtime ⭐

App kiểm chữ ký và interval thời gian từ ít nhất 3 server độc lập, cộng radius/RTT/drift rồi đối chiếu OS clock.

- Cần thêm: 1 client Roughtime Dart/native hoặc binding; danh sách public key pin.
- Ưu: Giao thức thời gian có chữ ký; không dựa riêng Date header.
- Nhược: RFC Experimental; thư viện Flutter, server hiện có và mạng UDP/TCP chưa prototype.
- Công sức tương đối (ước lượng, không phải số đo): Vừa–cao

#### D2-B. Time-stamp authority RFC 3161

App gửi nonce tới ít nhất 2 TSA độc lập, kiểm signed token và genTime/accuracy. Chỉ dùng nếu accuracy hoặc TSA policy có UTC bound thật.

- Cần thêm: Client RFC3161 + CMS/ASN.1 validator; TSA/provider/policy.
- Ưu: Tận dụng dịch vụ timestamp có chữ ký.
- Nhược: Accuracy tùy chọn; phải kiểm chain/revocation khi giờ sai, RTT và nguồn độc lập. Chưa chọn provider/validator; chưa đạt gate.
- Công sức tương đối (ước lượng, không phải số đo): Cao

#### D2-C. Server ký thời gian — đổi thiết kế

Server đã đồng bộ NTS ký nonce/time/uncertainty cho app qua kênh time riêng ngoài packet profile, rồi app kiểm OS clock.

- Cần thêm: Endpoint/protocol thời gian và validator; không thêm dịch vụ cloud riêng.
- Ưu: Tận dụng server và khóa vận hành đã có.
- Nhược: Một nguồn; phải sửa design §4 về kênh time, giải bootstrap trust key/manifest khi OS clock sai.
- Công sức tương đối (ước lượng, không phải số đo): Vừa

#### D2-D. NTS native qua FFI

App nhúng client NTS có NTS-KE/TLS và NTP, kiểm nguồn rồi đối chiếu OS clock.

- Cần thêm: 1 client native NTS và binding Flutter/FFI, trust configuration.
- Ưu: Dùng chuẩn NTS cùng họ với server/máy.
- Nhược: Native build/dependency và bootstrap certificate khi clock sai; không dùng NTP thường thay NTS.
- Công sức tương đối (ước lượng, không phải số đo): Cao

**Khuyến nghị/tiêu chí chọn:** A để prototype trước; B chỉ là candidate có điều kiện, chưa chứng minh gate. C nếu chấp nhận đổi thiết kế; D nếu chấp nhận native/FFI.

**Nguồn:** [Thiết kế §6](../packet-security/design.md) · [RFC10049 Experimental](https://www.rfc-editor.org/info/rfc10049/) · [RFC3161 TSA](https://www.rfc-editor.org/rfc/rfc3161.html) · [RFC8915 NTS](https://www.rfc-editor.org/rfc/rfc8915.html) · [chrony](https://chrony-project.org/doc/latest/chrony.conf.html) · [Android SystemClock](https://developer.android.com/reference/android/os/SystemClock)

### D3. Cấp credential cho máy

Server cần biết khóa thuộc máy nào. QR/product key hiện tại không tự chứng minh máy thật.

**Ràng buộc/điều kiện:** Mọi lựa chọn bind public key với danh tính máy, proof-of-possession (máy ký challenge) và quyền chủ. TPM chỉ là cách lưu khóa, không thay cấp quyền. Chưa biết máy có màn hình/nút và ai flash máy.

#### D3-A. BLE + đối chiếu tại máy

Máy sinh khóa; app đã enroll so khớp SAS/hash trên màn hình máy, bind public key/challenge/physical ID, rồi chủ ký xác nhận.

- Cần thêm: Luồng BLE/app enrollment; màn hình hoặc kênh độc lập đáng tin nếu máy chưa có.
- Ưu: Chủ có thể tự ghép tại máy.
- Nhược: BLE Just Works và nút bấm một mình không chống MITM; cần so khớp ngoài BLE.
- Công sức tương đối (ước lượng, không phải số đo): Vừa–cao

#### D3-B. Provision lúc lắp + claim riêng ⭐

Nhóm flash/provision khóa và đăng ký public key qua admin. Chủ nhận code niêm phong; app yêu cầu máy ký nonce để đối chiếu máy thật.

- Cần thêm: Tool provisioning và claim; code đóng gói; không bắt buộc phần cứng bảo mật mới.
- Ưu: Gắn danh tính máy trước khi giao; tách claim chủ khỏi credential.
- Nhược: Cần giữ an toàn dây chuyền flash/code, xử lý máy cũ; không chứng minh chống clone nếu khóa vẫn sao chép được.
- Công sức tương đối (ước lượng, không phải số đo): Vừa

#### D3-C. Mã ngắn hiện trên màn hình

Máy mở phiên challenge có TTL/attempt bound, hiển thị code bind pubkey/nonce; app chủ đã xác thực nhập code, server kiểm PoP.

- Cần thêm: Màn hình nếu chưa có; flow code + rate limit.
- Ưu: Ghép qua mạng, không cần BLE.
- Nhược: Người đứng tại máy vẫn có thể can thiệp; code ngắn cần giới hạn thử và xác nhận.
- Công sức tương đối (ước lượng, không phải số đo): Vừa

#### D3-D. Admin cấp code qua USB/console

Admin cấp code entropy cao dùng một lần; nhập bằng kênh kín vào máy, máy sinh khóa và chứng minh sở hữu khóa.

- Cần thêm: Tool admin/console hoặc USB đã có; flow code một lần.
- Ưu: Ít yêu cầu UI máy; dễ kiểm soát pilot.
- Nhược: Tốn người vận hành và bảo vệ kênh chuyển code; không phải self-service.
- Công sức tương đối (ước lượng, không phải số đo): Thấp–vừa

**Khuyến nghị/tiêu chí chọn:** B nếu nhóm tự lắp/flash; D cho pilot cần admin. A/C cần màn hình hoặc kênh đối chiếu tin cậy.

**Nguồn:** [Thiết kế credential §2.3](../packet-security/design.md) · [Hồ sơ repo/caller](decision-options-2026-10-07.md)

### D4. Khôi phục khi mất khóa

Khôi phục phải cấp lại quyền đúng chủ mà không chạy lại thao tác chưa rõ kết quả.

**Ràng buộc/điều kiện:** Mọi gói giữ đường admin đối soát ngoài kênh. Máy mất khóa/ledger phải quarantine, đối soát và không replay unknown. Chọn một đường mặc định; đường admin là nền chung.

#### D4-A. Chỉ admin đối soát

Admin xác minh ngoài kênh, thu hồi credential cũ và cấp lại quyền theo hồ sơ.

- Cần thêm: Tool/quy trình admin chung.
- Ưu: Ít tính năng và ít bề mặt self-service.
- Nhược: Chậm, phụ thuộc admin và chất lượng đối soát.
- Công sức tương đối (ước lượng, không phải số đo): Thấp–vừa

#### D4-B. Recovery code + admin ⭐

Code ngẫu nhiên dùng một lần cấp lúc enroll; lưu hash, rate-limit và thu hồi/thông báo credential cũ.

- Cần thêm: Flow recovery code và UI lưu code; không cần dịch vụ mới.
- Ưu: Người dùng tự phục hồi khi còn code.
- Nhược: Mất/lộ code là rủi ro chiếm quyền; cần giữ code ngoài điện thoại.
- Công sức tương đối (ước lượng, không phải số đo): Vừa

#### D4-C. App thứ hai phê duyệt + admin

Credential thứ hai đã đăng ký ký yêu cầu khôi phục; admin xử lý nếu mất cả hai.

- Cần thêm: Multi-device enrollment và UI phê duyệt.
- Ưu: Không phải tìm code nếu còn thiết bị dự phòng.
- Nhược: Cần thiết bị thứ hai; enrollment/revoke phức tạp hơn.
- Công sức tương đối (ước lượng, không phải số đo): Vừa

#### D4-D. Máy xác nhận quyền của chính nó + admin

Máy còn credential ký xác nhận vật lý để rebind quyền quản lý máy đó.

- Cần thêm: Flow xác nhận tại máy; màn hình/nút phù hợp D3.
- Ưu: Hữu ích khi chủ còn tiếp cận máy đã provision.
- Nhược: Không phục hồi toàn tài khoản; không dùng được khi máy cũng mất khóa.
- Công sức tương đối (ước lượng, không phải số đo): Vừa

**Khuyến nghị/tiêu chí chọn:** B nếu cần tự phục hồi; A nếu pilot ít người và có admin trực.

**Nguồn:** [Thiết kế recovery](../packet-security/design.md) · [NIST SP800-63B recovery](https://pages.nist.gov/800-63-4/sp800-63b.html)

### D5. Vị trí proxy và cách kết thúc TLS

Proxy đọc HTTP ngoài; tách quyền thực tế quyết định bảo đảm trước trung gian TLS.

**Ràng buộc/điều kiện:** Mọi lựa chọn giữ HTTP/1.1 ở các chặng HTTP. Caddy cần protocols h1 phía client và transport versions 1.1 phía backend. Root/sudo trên cùng server thuộc A3. Phải kiểm ALPN/config/caller và provenance IP thật. Cloudflare Tunnel không nằm trong shortlist.

#### D5-A. Server Python tự TLS

Python kết thúc TLS trực tiếp; không có proxy HTTP riêng.

- Cần thêm: Không thêm proxy; ssl stdlib, cert và cơ chế renew cần chuẩn bị.
- Ưu: Ít thành phần.
- Nhược: Tự vận hành cert/TLS/framing/quota; không có ranh giới proxy/server riêng.
- Công sức tương đối (ước lượng, không phải số đo): Vừa

#### D5-B. Caddy cùng host ⭐

Caddy dưới OS user riêng, backend private/Unix socket, secret server không đọc được bởi user proxy.

- Cần thêm: 1 Caddy; cấu hình OS permissions và socket.
- Ưu: ACME/config gọn, ít máy vận hành.
- Nhược: Root host vẫn đọc được endpoint; tách user phải có bằng chứng, Unix socket cần adapter.
- Công sức tương đối (ước lượng, không phải số đo): Vừa

#### D5-C. Caddy trên VPS biên

Proxy trên VPS độc lập, WireGuard về backend private; tách quản trị proxy khỏi endpoint.

- Cần thêm: 1 VPS, Caddy và WireGuard ở hai đầu.
- Ưu: Ranh giới host rõ hơn, phục vụ khách từ Internet.
- Nhược: Thêm chi phí/hạ tầng và tunnel; quyền cloud/root vẫn phải tách thật.
- Công sức tương đối (ước lượng, không phải số đo): Cao

#### D5-D. Proxy trên máy riêng tại site

Caddy chạy máy LAN riêng, backend chỉ nhận từ proxy. Khách từ xa dùng VPN/private route.

- Cần thêm: 1 máy riêng nếu chưa có, Caddy; VPN nếu truy cập từ xa.
- Ưu: Tách host không cần thuê VPS công khai.
- Nhược: Phụ thuộc LAN/điện; không phải sản phẩm truy cập Internet công khai trực tiếp.
- Công sức tương đối (ước lượng, không phải số đo): Vừa–cao

**Khuyến nghị/tiêu chí chọn:** B cho nhóm nhỏ có domain; C nếu cần tách host công khai. D chỉ cho site/private network có VPN.

**Nguồn:** [Thiết kế A1/A3/provenance](../packet-security/design.md) · [Caddy protocols](https://caddyserver.com/docs/caddyfile/options) · [Caddy upstream](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy) · [Cloudflare HTTP2](https://developers.cloudflare.com/speed/optimization/protocol/http2/)

### D6. Cách chuyển production sang profile mã hóa

Chuyển từng route app/máy để lại phần chưa bảo vệ; design hiện hành yêu cầu toàn profile.

**Ràng buộc/điều kiện:** Mỗi deployment/audience sau cutover bảo vệ tất cả GET/heartbeat/poll/result/auth/bootstrap; fail closed, không fallback plaintext. Rollback chỉ sang image protected tương thích epoch/ledger hiện hành, không restore DB cũ. Chưa biết có fleet/khách thật hay không.

#### D6-A. Cutover đồng loạt ⭐

Rehearsal toàn hệ thống, qua gate rồi chuyển một deployment và toàn fleet đồng thời.

- Cần thêm: Không thêm topology deployment; vẫn cần bộ kiểm và quy trình phát hành.
- Ưu: Ít logic migration/vận hành.
- Nhược: Lỗi cutover ảnh hưởng toàn phạm vi; cần bắt buộc cập nhật app/máy.
- Công sức tương đối (ước lượng, không phải số đo): Vừa

#### D6-B. Canary cohort cô lập

Một nhóm nhỏ dùng deployment/audience protected hoàn chỉnh, đạt thì mở rộng nhóm.

- Cần thêm: Deployment canary và migration/state/credential isolation.
- Ưu: Giảm phạm vi tác động ban đầu.
- Nhược: Không trộn protocol cùng endpoint hoặc cùng identity/state thiếu kiểm soát.
- Công sức tương đối (ước lượng, không phải số đo): Cao

#### D6-C. Cutover theo site

Mỗi site có deployment/audience riêng; chuyển toàn profile site này trước site tiếp theo.

- Cần thêm: Nhiều môi trường/site và quy trình migration.
- Ưu: Thuận tiện kiểm tại hiện trường theo site.
- Nhược: Thêm cấu hình/vận hành; chỉ hữu ích khi thật sự có nhiều site.
- Công sức tương đối (ước lượng, không phải số đo): Cao

#### D6-D. Blue/green toàn fleet

Chuẩn bị green protected đầy đủ, kiểm rồi chuyển toàn fleet; blue dự phòng cũng phải protected và dùng state/epoch hiện hành.

- Cần thêm: Hai môi trường và chuyển ingress/state được kiểm.
- Ưu: Có môi trường sẵn trước chuyển.
- Nhược: Chi phí kép; sai state/epoch khi rollback có thể gây replay hoặc khóa hệ thống.
- Công sức tương đối (ước lượng, không phải số đo): Cao

**Khuyến nghị/tiêu chí chọn:** A nếu chưa có production/fleet lớn; B nếu đã có fleet và tách audience/state được.

**Nguồn:** [Thiết kế rollout §10](../packet-security/design.md) · [SRE Canarying](https://sre.google/workbook/canarying-releases/)

### D8. Lấy trạng thái máy qua API nào

GET hiện chưa xác thực; app gửi một GET cho mỗi máy. ID thực tế là fm_ + 32 hex, không phải số thập phân.

**Ràng buộc/điều kiện:** Tất cả phải kiểm credential/phiên/quyền máy trước trả trạng thái. Thay hợp đồng phải sửa app/server/test/e2e cùng lúc. Không đặt envelope trong body GET.

#### D8-A. Giữ GET và header envelope

Query opaque ID canonical; envelope ở header có hard bound; bảo vệ request và kiểm quyền.

- Cần thêm: Không thêm dịch vụ; thêm GET wire adapter và negative tests.
- Ưu: Giữ method/URL cho caller cần GET.
- Nhược: Hai adapter, giới hạn header và N request; phải sửa design query decimal.
- Công sức tương đối (ước lượng, không phải số đo): Vừa

#### D8-B. POST từng máy

Machine ID nằm trong protected body, dùng cùng adapter POST và kiểm quyền từng máy.

- Cần thêm: Không thêm dịch vụ; sửa caller và hợp đồng method.
- Ưu: Một kiểu adapter, refresh từng máy riêng.
- Nhược: Vẫn N request cho N máy.
- Công sức tương đối (ước lượng, không phải số đo): Thấp–vừa

#### D8-C. Gộp vào danh sách máy ⭐

Trả online/last_seen trong USER_MACHINE_LIST; bỏ route GET và vòng gọi status.

- Cần thêm: Không thêm dịch vụ; sửa SELECT/response, refresh và caller/test/e2e.
- Ưu: Một request có kiểm quyền cho danh sách.
- Nhược: Refresh status phải tải lại list; cần kiểm mọi caller trước bỏ route.
- Công sức tương đối (ước lượng, không phải số đo): Vừa

#### D8-D. POST batch trạng thái

Protected body chứa danh sách ID; kiểm giới hạn batch và quyền mỗi máy.

- Cần thêm: Không thêm dịch vụ; hợp đồng batch/validation/caller.
- Ưu: Refresh nhiều status mà không tải lại cả danh sách.
- Nhược: Thêm batching và policy lỗi từng item; caller phải cập nhật.
- Công sức tương đối (ước lượng, không phải số đo): Vừa

**Khuyến nghị/tiêu chí chọn:** C nếu dashboard là caller chính; B nếu cần refresh từng máy; D khi refresh nhiều status độc lập với list.

**Nguồn:** [Thiết kế GET adapter](../packet-security/design.md) · [RFC9110 GET](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.3.1) · [Bằng chứng repo](decision-options-2026-10-07.md)

### Phụ thuộc và câu hỏi còn mở

D1 quyết định khóa ký trust/epoch; D2 chặn mọi route Seal và D6. D3-A cần app đã enroll và kênh SAS thật. D3/D4 cần admin authority tách proxy; D4-D cần máy còn credential. D5 quyết định provenance/quota bootstrap. D8 là gate adapter trước D6. Không tự lùi epoch/ledger khi đổi deployment.

Cần người dùng xác nhận: ai giữ root và thời hạn manifest; máy có màn hình/nút không, ai flash; có fleet/khách đang chạy thật không; có domain/public ingress hoặc VPN, ngân sách host riêng. Những thiếu dữ kiện này không được thay bằng số giả.

### Sửa sau tranh luận trực tiếp

- D1: giữ Cloud KMS nhưng đánh dấu đổi root offline, không gọi tuân thủ design cũ.
- D2: loại HTTPS Date thường; thay bằng TSA có điều kiện; xác nhận RFC10049 Experimental. Mọi app time là cross-check OS clock, không tự thay bằng app-only clock.
- D3: BLE + nút đơn thuần bị loại; cần SAS/hash trên kênh độc lập bind khóa/challenge/physical ID.
- D5: loại Cloudflare Tunnel vì không bảo đảm HTTP/1.1 các chặng; D là proxy LAN riêng có VPN.
- D6: loại rollout theo route app/máy; chọn bốn phạm vi deployment/fleet toàn profile, rollback không lùi state.
- D8: giữ batch POST thay phương án thêm ID số vô ích.

Critic kiểm lại các sửa cuối: không còn blocker logic shortlist. Đồng thuận không thay người dùng chốt. Bằng chứng trao đổi: [debate-sol-high-2026-10-07.md](decision-debate/debate-sol-high-2026-10-07.md).

## Lịch sử trước lượt GPT Sol high

Hồ sơ nội bộ của RESEARCHER, để người dùng chốt. **Không phải quyết định đã chốt**,
không thay `packet-security/design.md` (gọi tắt **D:dòng**). Chưa sửa code, chưa chạy
test, chưa đo. Mọi giá trị số dưới nhãn "điểm khởi đầu thảo luận" là đề xuất policy,
**không phải số đo**. Mục "chưa kiểm" nghĩa là chưa có bằng chứng trong repo hoặc nguồn.

## Vòng 1

### 0. Hiện trạng repo liên quan (đã đọc)

| Sự thật | Nguồn trong repo |
| --- | --- |
| Server cấp `machine_id = "fm_" + uuid4().hex` (35 ký tự, opaque) | `server/database/machine/machine_write.py:17–24` |
| Product key `fm_<32 hex>` nằm trong `machine.env`, in lên tem QR, gửi qua Bluetooth; server lưu SHA-256; ai quét trước thành chủ | `machine/README.md`, `machine_register_process.py:31–55`, `machine/pairing/README.md` |
| Máy xưng danh relay bằng product key trong mọi request (heartbeat 5 s, long-poll, result) | `machine/README.md`, `machine_link_process.py:21` |
| Bluetooth bond bằng agent NoInputNoOutput (Just Works) | `machine/pairing/README.md` |
| GET `/machine/trang-thai?machine_id=` **không cần token**; test SEC-08 đánh dấu `expectedFailure` | `machine_list_get.py:27–29`, `tests/python/test_server_security.py:290–297` |
| Dashboard gọi GET status song song **một request cho mỗi máy** | `dashboard_controller.dart:106–124` |
| App mặc định `http://` LAN, ghi chú Tailscale IP; chưa có proxy/TLS trong repo | `app_config.dart:2–4`, `log/SECURITY_NOTES.md:39` |
| Server dùng `time.time()` cho session/heartbeat/invite | `user_session.py:25,43`, `machine_transport.py:32,42` |
| Python `http.client` giới hạn 65536 byte/dòng header, 100 header (đo bằng `python3 -c`, máy dev, phiên bản Python của server deploy chưa kiểm) | `_MAXLINE`, `_MAXHEADERS` |

Chưa kiểm: model Pi thật (Pi 4/5, có pin RTC không), số máy/ người dùng đang chạy thật,
có backup/VM snapshot không, ai là người vận hành server.

---

## D1. Private root, ký manifest, chu kỳ, max_manifest_validity, recovery_epoch

Ràng buộc design: root offline, không ở proxy/server online (D:67–69); manifest ký
canonical bytes có sequence monotonic + recovery_epoch (D:70–73); client enforce
`max_manifest_validity` từ trust package (D:77–80); root rotation cần kênh độc lập
(D:84–86); manifest có epoch mới do offline authority ký sau restore (D:541–544).

Công thức chung cho mọi phương án (để người dùng chốt số):
- `cadence` = khoảng giữa hai lần ký manifest định kỳ.
- `max_manifest_validity ≥ cadence + slack_ký_trễ`; `slack` = thời gian tối đa
  chấp nhận được để tổ chức một buổi ký khi người giữ khóa bận/ốm.
- Độ trễ thu hồi tối đa khi A1 giữ manifest cũ ≈ `remaining validity + clock uncertainty` (D:81–83).
- RTO sau restore ≥ thời gian để offline authority có mặt ký epoch mới.
Điểm khởi đầu thảo luận (không số đo): cadence 7 ngày, validity 14 ngày. Validity
dài hơn → ít ceremony nhưng cửa sổ thu hồi dài; ngắn hơn → fail-closed thường xuyên
khi người ký vắng mặt.

### D1-A. Một người giữ root trên hardware token, có token dự phòng

- **Mô tả:** Trưởng nhóm/chủ sản phẩm sinh root **trong** token phần cứng (ví dụ YubiKey 5.7 PIV, có Ed25519 và P-256), không xuất private key. Token thứ hai sinh root dự phòng được liệt kê sẵn trong trust package (hai public root chấp nhận, 1-of-2).
- **Vận hành:** Script ký chạy trên laptop quản trị (không phải server); dựng canonical bytes manifest, gọi token ký, xuất file manifest + chữ ký, chép lên server. Token dự phòng niêm phong ở nơi khác (két). Sau restore: người giữ token ký manifest có `recovery_epoch` mới.
- **Ưu:** Private key không bao giờ ở dạng file; ceremony nhanh (cắm token + PIN); chi phí thấp.
- **Nhược/rủi ro:** Một người là điểm lỗi về sẵn sàng và insider; token mất/hỏng → dùng token dự phòng, nhưng 1-of-2 nghĩa là ai chiếm một token + PIN ký được. Laptop ký bị nhiễm mã độc có thể xin token ký nội dung khác (cần hiển thị/đối chiếu hash manifest trên máy thứ hai). PIV ký đúng thuật toán nào, có prehash không: **chưa kiểm** với profile canonical bytes (D:149).
- **Công sức:** Thấp–trung bình (mua 2 token, viết script ký, quy trình giấy).
- **Tiên quyết:** Ngân sách token; người giữ có mặt theo cadence; chọn thuật toán ký manifest khớp thư viện verify Dart/Python.
- **Thỏa:** D:67–69 (không online), D:84–86 nếu trust package mới ký bởi root cũ. **Không thỏa đầy đủ** nếu laptop ký là máy dùng hằng ngày nối mạng — khi đó "offline" chỉ là khóa offline, không phải môi trường offline.
- **Nguồn:** [YubiKey 5.7 firmware](https://docs.yubico.com/hardware/yubikey/yk-tech-manual/yk5-firmware-5.7.html); [OWASP Key Management](https://cheatsheetseries.owasp.org/cheatsheets/Key_Management_Cheat_Sheet.html); [NIST SP 800-57 Pt1 r5](https://csrc.nist.gov/pubs/sp/800/57/pt1/r5/final).

### D1-B. Máy ký air-gapped, khóa file mã hóa passphrase, backup giấy/USB hai nơi

- **Mô tả:** Một máy (laptop cũ hoặc USB live) không bao giờ nối mạng giữ root dạng file mã hóa bằng passphrase (ví dụ công cụ kiểu minisign Ed25519, hoặc script Python `cryptography`). Backup mã hóa ở hai địa điểm.
- **Vận hành:** Dựng manifest trên máy online → chép USB sang máy air-gapped → hiển thị hash + nội dung → ký → chép chữ ký về. Người ký đọc lại sequence/epoch/validity trước khi ký.
- **Ưu:** Không cần phần cứng mua thêm; đúng tinh thần "môi trường quản trị riêng".
- **Nhược/rủi ro:** Khóa tồn tại dưới dạng file → backup/USB bị lộ + passphrase yếu là lộ root. USB chuyển file là kênh lây nhiễm. Minisign mặc định ký prehash BLAKE2b ("ED") — phải đặc tả rõ trong profile hoặc dùng chế độ ký trực tiếp; **chưa kiểm** phiên bản minisign đang dùng. Ceremony chậm hơn A.
- **Công sức:** Thấp (tiền), trung bình (kỷ luật vận hành).
- **Tiên quyết:** Một máy dành riêng; quy trình kiểm USB; passphrase mạnh lưu tách.
- **Thỏa:** D:67–69, D:75–76. Rủi ro backup file được design yêu cầu quản trị riêng (D:416).
- **Nguồn:** [minisign](https://jedisct1.github.io/minisign/); [TUF spec — root offline](https://theupdateframework.github.io/specification/latest/); [OWASP Key Management](https://cheatsheetseries.owasp.org/cheatsheets/Key_Management_Cheat_Sheet.html).

### D1-C. Ngưỡng 2-of-3 người (kiểu TUF threshold)

- **Mô tả:** Trust package chứa 3 public root (ví dụ trưởng nhóm, mentor/giảng viên, người vận hành server); manifest hợp lệ khi có ≥2 chữ ký khác key ID. Mỗi người giữ khóa của mình bằng A hoặc B.
- **Vận hành:** Một người dựng manifest, hai người ký độc lập sau khi tự kiểm nội dung. Recovery_epoch sau restore cần 2 người.
- **Ưu:** Một khóa lộ hoặc một người mất liên lạc không phá hệ thống; chống insider đơn lẻ; root rotation theo chuỗi TUF.
- **Nhược/rủi ro:** Client phải verify nhiều chữ ký, đặc tả thứ tự/duplicate key ID; cần 2 người có mặt mỗi cadence → validity phải dài hơn hoặc fail-closed nhiều hơn. Phức tạp hơn cho nhóm intern.
- **Công sức:** Trung bình–cao (format manifest đa chữ ký, test negative: trùng key, 1 chữ ký, key ngoài danh sách).
- **Tiên quyết:** Ba người cam kết vai trò dài hạn; quy trình liên lạc khi restore.
- **Thỏa:** D:67–86 và mạnh hơn yêu cầu; không vi phạm "không bắt buộc intermediate" (D:76–77).
- **Nguồn:** [TUF spec — threshold, expiry, rollback, root chain](https://theupdateframework.github.io/specification/latest/).

### D1-D. Hai tầng: root offline chỉ ký delegation; khóa ký manifest ngắn hạn ở máy quản trị riêng

- **Mô tả:** Root (giữ như A/B/C) chỉ ký "delegation" cho một khóa ký manifest có hạn ngắn và phạm vi hẹp (chỉ ký manifest key config, không ký root mới). Khóa này ở máy quản trị riêng (không phải proxy/server online), dùng cho ký định kỳ; root chỉ ra khi rotation, thu hồi delegation hoặc recovery_epoch.
- **Vận hành:** Ký định kỳ nhanh bởi khóa delegation; mỗi 1 delegation period ceremony root một lần. Client verify chuỗi root→delegation→manifest, kiểm validity cả hai.
- **Ưu:** Ceremony root hiếm; ký thường xuyên dễ hơn → có thể chọn validity ngắn hơn (thu hồi nhanh hơn).
- **Nhược/rủi ro:** Thêm một khóa, một tầng verify, một loại thu hồi. Nếu máy giữ delegation thực chất online thì gần với "intermediate online" — design không bắt buộc nhưng cũng không cấm; phải chứng minh nó không ở proxy/server. recovery_epoch có nên cho delegation ký không là câu hỏi mở (đề xuất: chỉ root).
- **Công sức:** Cao nhất trong 4 phương án (format chuỗi, test).
- **Tiên quyết:** Máy quản trị thứ hai cách ly tốt.
- **Thỏa:** D:75–77 nếu khóa delegation không online tại proxy/server; cần người dùng xác nhận vì thêm khóa ngoài design.
- **Nguồn:** [TUF spec — role delegation](https://theupdateframework.github.io/specification/latest/).

**Khuyến nghị D1:** **D1-A** (token phần cứng + token dự phòng), đi kèm checklist ký
hai màn hình và cadence/validity do người dùng chốt. Lý do: chi phí thấp, khóa không
xuất được, ceremony đủ nhanh để validity không quá dài, đáp ứng D:67–86 mà không thêm
định dạng đa chữ ký. Chọn **C** nếu có ≥3 người cam kết và lo insider; **B** nếu không
có ngân sách token; **D** chỉ khi cadence cần rất ngắn.
**Tiêu chí chọn:** số người đáng tin có thể có mặt; RTO chấp nhận sau restore; ngân sách
phần cứng; mức lo ngại insider; độ trễ thu hồi chấp nhận được.

---

## D2. Nguồn thời gian đáng tin cho app Android, máy và server; Δ và L_max

Ràng buộc design: OS clock không mặc định đáng tin; SNTP/NITZ không là bằng chứng
(D:556–558); mỗi boot CLOCK_UNTRUSTED tới khi xác minh qua authenticated time (D:237–240);
**không có route time-sync trong packet profile** (D:243); không dùng giờ proxy trả (D:90).

Sự thật nền tảng:
- Android dùng **SNTP không xác thực**, mặc định `time.android.com`; tài liệu AOSP không
  nêu NTS. `SystemClock.currentNetworkTimeClock()` (API 33) ghi rõ "should not be used
  for security purposes". → Không có nguồn thời gian xác thực sẵn trong Android cho app.
- Raspberry Pi OS mặc định `systemd-timesyncd`; NTS cho timesyncd đang là PR chưa phát hành
  (theo kết quả tìm kiếm, **chưa kiểm** bản phát hành cụ thể). `chrony` hỗ trợ `nts`
  và `nocerttimecheck` cho máy không RTC.
- Pi 5 có RTC trong PMIC, cần pin ngoài (ML-2020) và bật sạc thủ công; Pi 4 không có RTC
  (Pi 4: kiến thức chung, **chưa kiểm** trong tài liệu chính thức lượt này).
- RFC 8915: delay attack bất đối xứng không chặn được bằng mật mã, sai số bị chặn bởi
  nửa RTT; certificate check khi đồng hồ sai là vấn đề khởi động.
- Roughtime: draft-ietf-ntp-roughtime-19 (03/2026), trạng thái RFC Ed Queue, Experimental;
  chữ ký + radius, client không có clock vẫn bootstrap được, khuyến nghị ≥3 server.
  Cloudflare cung cấp NTS và Roughtime.

Công thức đặt Δ/L_max (mọi phương án):
- `Δ_future = ε_client + ε_server + drift_giữa_hai_lần_sync`, ε là bất định của nguồn
  xác thực (NTS: ≤ ½ RTT + root distance mà daemon báo; Roughtime: radius + ½ RTT).
- `Δ_past = Δ_future + thời gian request nằm trên mạng/queue trước khi server kiểm`.
- `L_max` (đời một attempt) ≥ p99 thời gian từ tạo packet đến claim, **không** gồm retry
  (retry là attempt mới D:215). Với long-poll: `L_max_poll ≥ POLL_WAIT_SECONDS + budget xử lý`
  hoặc tách L_max theo route_id.
- Replay horizon `H ≤ L_max+Δ_future+σ+margin` (D:436) quyết định kích thước bảng claim.
Điểm khởi đầu thảo luận (chưa đo): Δ cỡ vài chục giây, L_max route thường cỡ 1–2 phút,
L_max poll theo cấu hình long-poll. Phải đo p99 trên mạng thật trước khi chốt.

### D2-A. NTS cho server và máy (chrony), Roughtime nhúng trong app

- **Mô tả:** Server và Pi chạy chrony với ≥2–3 nguồn NTS độc lập, `minsources` >1; Pi có RTC pin (Pi 5) hoặc dùng `nocerttimecheck 1` giới hạn. App Android có client Roughtime với public key của ≥3 server pinned trong APK; app chỉ coi OS clock dùng được khi lệch so với khoảng Roughtime ≤ Δ_app; nếu không → khóa route có Seal, báo người dùng sửa giờ.
- **Vận hành:** systemd unit server/máy chỉ mở admission sau khi `chronyc tracking`/`waitsync` báo đồng bộ NTS (cần adapter đọc trạng thái). App kiểm Roughtime khi khởi động và định kỳ.
- **Ưu:** Mỗi nền tảng dùng nguồn có xác thực phù hợp; app không cần quyền đổi giờ hệ thống; không thêm route vào packet profile.
- **Nhược/rủi ro:** Thư viện Roughtime cho Dart **chưa kiểm** (có thể phải tự viết parser — rủi ro, dù chỉ verify Ed25519 + Merkle); Roughtime vẫn draft Experimental, danh sách server công khai ít; mạng chặn UDP → fail closed. NTS-KE cần TLS cert check khi clock sai (bootstrap Pi không RTC).
- **Công sức:** Trung bình (máy/server: cấu hình), trung bình–cao (app Roughtime).
- **Tiên quyết:** Inventory model Pi + pin RTC; outbound UDP 123/NTS-KE TCP 4460 và Roughtime UDP được phép; chọn server công khai.
- **Thỏa:** D:237–244 (nguồn ngoài A0/A1), D:556–558. Không thêm route time-sync.
- **Nguồn:** [AOSP network time detection](https://source.android.com/docs/core/connect/time/network-time-detection); [SystemClock](https://developer.android.com/reference/android/os/SystemClock); [chrony.conf](https://chrony-project.org/doc/4.6/chrony.conf.html); [RFC 8915](https://www.rfc-editor.org/rfc/rfc8915.html); [Roughtime draft-19](https://www.ietf.org/archive/id/draft-ietf-ntp-roughtime-19.html); [Cloudflare Time Services](https://www.cloudflare.com/time/); [Pi 5 RTC battery](https://thepihut.com/products/rtc-battery-for-raspberry-pi-5); [systemd NTS PR #39010](https://github.com/systemd/systemd/pull/39010).

### D2-B. NTS ở mọi nơi, gồm client NTS trong app

- **Mô tả:** Như A cho server/máy; app thay Roughtime bằng client NTS (NTS-KE qua TLS + NTP có AEAD) để đo offset OS clock.
- **Ưu:** NTS là RFC Proposed Standard, nhiều server công khai hơn Roughtime; một giao thức chung cho toàn hệ thống.
- **Nhược/rủi ro:** Không có NTS trong Android; thư viện NTS cho Dart/Flutter **chưa kiểm**, khả năng phải FFI tới thư viện native (ví dụ ntpd-rs) — tăng kích thước APK, bảo trì; NTS-KE dùng TLS cần đồng hồ đúng để kiểm cert (RFC 8915 §8.5) → vòng lặp khởi động trên điện thoại giờ sai. NTS chỉ bảo đảm toàn vẹn, delay attack vẫn gây lệch ≤ ½ RTT.
- **Công sức:** Cao (app).
- **Tiên quyết:** Tìm/đánh giá binding NTS; như A cho máy.
- **Thỏa:** D:237–244, D:556–558.
- **Nguồn:** [RFC 8915 §§8.5–8.6](https://www.rfc-editor.org/rfc/rfc8915.html); [chrony.conf](https://chrony-project.org/doc/4.6/chrony.conf.html); [Fedora thảo luận ntpd-rs NTS](https://discussion.fedoraproject.org/t/has-anyone-tried-ntpd-rs-for-nts/199190).

### D2-C. Thời gian do server ký theo nonce client (Roughtime 1-server tự vận hành) — **cần sửa design**

- **Mô tả:** Server (đồng bộ bằng NTS như A) có khóa ký thời gian riêng purpose, public key nằm trong manifest ký bởi root. Client gửi nonce, server trả `Sign(nonce‖time‖radius)`; client đo RTT và suy khoảng thời gian. Máy cũng dùng như vậy.
- **Ưu:** Không phụ thuộc server thời gian bên thứ ba cho app/máy; logic nhỏ, thư viện chữ ký đã có; A1 (không có khóa server) không giả được.
- **Nhược/rủi ro:** **Trái D:243** ("Không có route time-sync trong packet profile") — chỉ hợp lệ nếu người dùng đồng ý thêm một kênh thời gian **ngoài** packet profile, có đặc tả riêng. Một nguồn duy nhất: server bị chiếm/clock server sai thì toàn hệ thống sai (nhưng server bị chiếm đã là A3). Delay attack ≤ ½ RTT. Bootstrap manifest cần clock để kiểm hạn manifest chứa khóa thời gian → phải định nghĩa thứ tự (verify chữ ký root trước, hạn sau khi có thời gian ký).
- **Công sức:** Trung bình.
- **Tiên quyết:** Người dùng chấp nhận sửa D:243; đặc tả chống vòng lặp bootstrap.
- **Thỏa:** D:90 (không dùng giờ proxy chưa xác thực) nếu khóa không ở proxy; **không thỏa** D:243 hiện hành.
- **Nguồn:** [Roughtime draft-19 (mô hình nonce+chữ ký)](https://www.ietf.org/archive/id/draft-ietf-ntp-roughtime-19.html); [RFC 8915 §8.6 delay attack](https://www.rfc-editor.org/rfc/rfc8915.html).

### D2-D. Không đủ nguồn thời gian → profile chỉ chạy pilot/non-production có nhãn

- **Mô tả:** Giữ đúng design: chưa chứng minh nguồn thời gian thì không production (D:557–558). Chạy pilot nội bộ: server/máy chrony NTS (dễ), app dùng OS clock, mọi build/pilot gắn nhãn "không production", thu số đo offset/RTT để chốt Δ/L_max, rồi chọn A/B/C sau.
- **Ưu:** Không chặn tiến độ phát triển; có dữ liệu thật trước khi chốt; đúng nguyên tắc không bịa số đo.
- **Nhược/rủi ro:** Không giải quyết vấn đề; có nguy cơ "pilot" thành production ngầm. Cần cổng phát hành chặn.
- **Công sức:** Thấp.
- **Thỏa:** D:557–558 (bằng cách không tuyên bố production). **Không thỏa** gate production.
- **Nguồn:** design D:556–563; [AOSP network time detection](https://source.android.com/docs/core/connect/time/network-time-detection).

**Khuyến nghị D2:** **D2-A**, triển khai theo lộ trình D2-D (server/máy chrony NTS ngay,
đo offset; app Roughtime sau khi có thư viện/prototype đạt). Lý do: không đổi design,
mỗi nền tảng dùng nguồn có xác thực khả thi; Roughtime phù hợp cho thiết bị không biết
giờ, đúng vấn đề của app. Nếu prototype Roughtime Dart không đạt, chọn **C** (cần sửa
D:243) thay vì B (chi phí FFI cao).
**Tiêu chí chọn:** có chấp nhận sửa D:243 không; có thư viện Dart Roughtime/NTS đạt review
không; mạng thực có chặn UDP không; model Pi/RTC; độ trễ thu hồi mong muốn.

---

## D3. Cấp credential cho máy (enrollment)

Vấn đề hiện tại: product key in trên tem QR và gửi qua Bluetooth Just Works; nó vừa là
**mã nhận biết**, vừa là **bearer secret** cho relay, vừa là **quyền chiếm chủ** (người
quét đầu tiên). Ai đọc tem/sniff Bluetooth có thể giả máy hoặc chiếm máy. Design cấm
"người chỉ có product-key/QR công khai thay credential máy" (D:104–106).

### D3-A. Enrollment có chủ máy tại chỗ: máy sinh khóa, app chủ ký xác nhận qua kênh vật lý

- **Mô tả:** Pi tự sinh keypair ký (file 0600 user riêng hoặc phần cứng nếu có). Khi chủ đăng ký máy, app (credential đã enroll) nhận public key máy qua Bluetooth, **so khớp mã ngắn hiển thị trên màn hình máy** (hoặc bấm nút vật lý trên máy), rồi gửi `(product_key, machine_pubkey, xác nhận)` ký bằng credential app. Server cấp machine credential; máy chứng minh PoP qua challenge.
- **Ưu:** Product key chỉ còn là mã nhận biết; xác nhận vật lý chặn chiếm từ xa; tận dụng luồng Bluetooth hiện có.
- **Nhược/rủi ro:** Bluetooth Just Works không chống MITM → **bắt buộc** đối chiếu mã/nút vật lý ngoài BT; máy cần màn hình hoặc nút (chưa kiểm phần cứng có gì). Khóa file trên SD có thể bị sao chép khi có truy cập vật lý (clone máy). Người tiếp cận vật lý đầu tiên vẫn có lợi thế.
- **Công sức:** Trung bình (app + máy + server, thay hợp đồng đăng ký máy).
- **Tiên quyết:** Máy có UI/nút; app đã enroll credential (phụ thuộc D4/app enrollment).
- **Thỏa:** D:104–106 (owner confirmation + PoP). Không chống clone SD (A3 thiết bị).
- **Nguồn:** [NIST SP 800-121 r2 Bluetooth (Just Works không MITM)](https://csrc.nist.gov/pubs/sp/800/121/r2/upd1/final); [arXiv 1908.10497](https://arxiv.org/pdf/1908.10497); [OWASP Key Management](https://cheatsheetseries.owasp.org/cheatsheets/Key_Management_Cheat_Sheet.html).

### D3-B. Nhóm tiền-provision lúc lắp ráp (factory provisioning) + claim quyền chủ tách riêng

- **Mô tả:** Tại bàn lắp ráp, máy quản trị tin cậy chạy script: Pi sinh khóa, máy quản trị đọc public key, ghi bản ghi `physical_machine_id ↔ pubkey` vào server qua kênh admin (bản ghi ký bằng khóa provisioning offline). Máy đã có credential **trước** khi bán. Chủ sau đó chỉ "claim quyền chủ" bằng claim code bí mật (không in trên tem ngoài; ví dụ phiếu niêm phong trong hộp) + xác nhận vật lý; product key chỉ còn nhận biết.
- **Ưu:** Danh tính máy không phụ thuộc người dùng cuối; tách rõ "máy là ai" và "ai sở hữu" (giống mô hình ownership voucher của FIDO FDO); server từ chối mọi máy chưa provision.
- **Nhược/rủi ro:** Cần quy trình lắp ráp có kiểm soát và khóa provisioning; máy đã bán trước đây phải re-provision; claim code bị lộ trong chuỗi phân phối vẫn cho chiếm chủ (giảm bằng xác nhận vật lý + thông báo).
- **Công sức:** Trung bình (script provisioning, bảng server, hợp đồng claim).
- **Tiên quyết:** Nhóm tự lắp/flash máy; có máy quản trị; liên quan D1 (khóa provisioning có thể do root ủy quyền).
- **Thỏa:** D:104–106 ("provisioning tin cậy + PoP"), tách product key khỏi bằng chứng enroll.
- **Nguồn:** [FIDO Device Onboard overview](https://fidoalliance.org/device-onboarding-overview/); [FDO spec v2.0 PS](https://fidoalliance.org/specs/FDO/FIDO-Device-Onboard-PS-v2.0-20260402/FIDO-Device-Onboard-PS-v2.0-20260402.pdf); [RFC 8995 BRSKI (tham khảo khái niệm voucher)](https://www.rfc-editor.org/rfc/rfc8995.html).

### D3-C. Khóa máy trong phần cứng (TPM 2.0 HAT) + attestation

- **Mô tả:** Mỗi máy gắn module TPM 2.0 (ví dụ bo đánh giá Infineon OPTIGA SLB 9672 cho Pi, SPI). Khóa máy sinh trong TPM, không xuất được; server kiểm chứng chỉ endorsement/attestation khi enroll (kết hợp A hoặc B cho quyền chủ).
- **Ưu:** Chống sao chép SD/clone máy tốt hơn hẳn; phù hợp D:416 về bảo vệ secret ngoài wire.
- **Nhược/rủi ro:** Chi phí phần cứng mỗi máy; tích hợp tpm2-tss/Python **chưa kiểm**; chuỗi chứng chỉ nhà sản xuất cần pin/kiểm; Pi không có TPM tích hợp (tài liệu Pi chỉ có OTP/secure boot). Tăng thời gian giao.
- **Công sức:** Cao.
- **Tiên quyết:** Ngân sách, thời gian prototype phần cứng, quyết định có cần chống clone không.
- **Thỏa:** D:104–106 + giảm rủi ro A3 ở máy; không tự giải quyết quyền chủ.
- **Nguồn:** [Infineon OPTIGA TPM SLB 9672 RPi eval](https://www.infineon.com/cms/en/product/evaluation-boards/optiga-tpm-9672-rpi-eval/); [Raspberry Pi security architecture](https://www.raspberrypi.com/documentation/security/security-architecture.html); [Pi secure boot provisioner](https://www.raspberrypi.com/documentation/security/secure-boot-provisioner.html).

### D3-D. Mã enrollment một lần do server cấp (thay product key), máy tự enroll qua bootstrap

- **Mô tả:** Admin/chủ tạo trên server một enrollment code ngẫu nhiên ≥ 64 bit, một lần, hạn ngắn, lưu hash, rate-limit. Code được nhập vào máy (bàn phím/màn hình máy hoặc USB) — **không** qua tem công khai. Máy sinh khóa, gửi `(code, pubkey, PoP)` qua bootstrap HPKE; server bind credential.
- **Ưu:** Thay đổi ít nhất về phần cứng và app; product key không còn là bằng chứng; dễ cho re-enroll sau mất khóa.
- **Nhược/rủi ro:** Bootstrap không có chữ ký credential (D:110–113) nên chỉ code là bằng chứng; code bị lộ trong lúc chuyển → giả máy; cần UI nhập code trên máy. Bootstrap có allowlist và **không** machine write (D:111–112) — route enroll máy phải nằm trong allowlist bootstrap riêng, cần đặc tả.
- **Công sức:** Thấp–trung bình.
- **Tiên quyết:** Kênh chuyển code an toàn tới máy; quyết định ai được tạo code.
- **Thỏa:** D:104–106 nếu code chuyển qua kênh tin cậy (owner confirmation); mức bảo đảm yếu hơn A/B.
- **Nguồn:** [NIST SP 800-63B-4 §4.2 (entropy/single-use/hash)](https://pages.nist.gov/800-63-4/sp800-63b.html); design D:110–114.

**Khuyến nghị D3:** **D3-B** (tiền-provision lúc lắp ráp + claim chủ tách riêng có xác
nhận vật lý). Lý do: nhóm tự flash máy nên có điểm tin cậy tự nhiên; tách danh tính máy
khỏi quyền sở hữu đúng D:104–106; không phụ thuộc Bluetooth Just Works; nâng lên C
sau nếu cần chống clone. Chọn **A** nếu máy được người khác lắp/flash; **D** cho prototype
nhanh; **C** khi có ngân sách và yêu cầu chống sao chép thiết bị.
**Tiêu chí chọn:** ai flash máy; máy có màn hình/nút không; có lo clone SD không; số máy
đã ở hiện trường cần chuyển đổi.

---

## D4. Khôi phục khi mất thiết bị/mất khóa app hoặc máy

Ràng buộc: thay credential cần credential cũ hoặc recovery mạnh; không auto rebind chỉ
bằng mật khẩu/OTP; recovery code một lần, hash, rate-limit, hoặc admin reprovisioning;
thông báo credential cũ; pending op giữ unknown (D:94–103). Máy mất ledger → quarantine
và trusted recovery (D:352–353). NIST 63B-4 §4.2.1: saved recovery code ≥64 bit RBG,
dùng xong vô hiệu và cấp code mới; recovery phải gửi thông báo.

### D4-A. Recovery code in ra lúc enroll (tự phục vụ)

- **Mô tả:** Khi enroll credential app đầu tiên, server sinh recovery code ≥64 bit, hiện một lần để người dùng in/chép; server lưu hash. Mất máy: đăng nhập + recovery code + enroll key mới với PoP → server thu hồi credential cũ, thông báo email, cấp code mới.
- **Ưu:** Không cần admin; đúng NIST; chi phí thấp.
- **Nhược/rủi ro:** Người dùng làm mất code → rơi về C. Code bị chụp/lộ + mật khẩu lộ = chiếm tài khoản (thông báo chỉ là hỗ trợ). Cần rate-limit per account và toàn cục.
- **Công sức:** Thấp–trung bình.
- **Tiên quyết:** App enrollment đã có; kênh email thông báo (OTP email đã có).
- **Thỏa:** D:94–103. Không xử lý mất khóa máy.
- **Nguồn:** [NIST SP 800-63B-4 §4.2](https://pages.nist.gov/800-63-4/sp800-63b.html).

### D4-B. Thiết bị thứ hai đã enroll phê duyệt (multi-device / người cùng quyền)

- **Mô tả:** Người dùng enroll ≥2 installation (2 điện thoại, hoặc chủ + quản lý). Installation mới được kích hoạt machine write khi một credential còn sống ký phê duyệt. Chủ phê duyệt lại cho nhân viên mất máy (dựa trên machine_share).
- **Ưu:** Không cần bí mật giấy; phù hợp quan hệ chủ–nhân viên đã có.
- **Nhược/rủi ro:** Chủ chỉ có một điện thoại và mất nó → không giải quyết; mô hình hiện tại một owner/máy — cần khái niệm "credential dự phòng của chủ" hoặc co-owner (thay hợp đồng machine_share). Thiết bị thứ hai bị chiếm phê duyệt kẻ tấn công.
- **Công sức:** Trung bình–cao (UI phê duyệt, hợp đồng mới).
- **Tiên quyết:** Có thiết bị/ người thứ hai.
- **Thỏa:** D:94–96 (dùng credential cũ/khác đã tin) — tốt hơn bearer token.
- **Nguồn:** [NIST SP 800-63B-4 §4 (authenticator binding/event management)](https://pages.nist.gov/800-63-4/sp800-63b.html#authenticator-event-management).

### D4-C. Admin reprovisioning có đối soát ngoài kênh + thời gian chờ

- **Mô tả:** Người dùng liên hệ đội vận hành; admin xác minh ngoài kênh (gặp trực tiếp, hóa đơn mua máy, mặt tại máy). Admin tạo bản ghi reprovision ký bằng khóa admin (không phải token bearer); có thời gian chờ (cooldown) + thông báo credential cũ có thể hủy trước khi hiệu lực. Áp dụng cả cho máy mất khóa/SD: admin re-provision (theo D3) + quarantine ledger + đối soát (D:352–357).
- **Ưu:** Phủ mọi ca "mất hết"; là phương án design gọi tên ("trusted administrative reprovisioning").
- **Nhược/rủi ro:** Phụ thuộc người; social engineering admin; chậm; cần log/kiểm toán.
- **Công sức:** Trung bình (công cụ admin, quy trình giấy).
- **Tiên quyết:** Có người vận hành trực; khóa admin (liên quan D1).
- **Thỏa:** D:97–103, D:352–357.
- **Nguồn:** [NIST SP 800-63B-4 §4.2 (recovery, notification)](https://pages.nist.gov/800-63-4/sp800-63b.html); [OWASP Forgot Password / recovery](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html).

### D4-D. Khôi phục bằng hiện diện vật lý tại máy (máy đã enroll chứng nhận chủ mới cho chính nó)

- **Mô tả:** Điện thoại mới kết nối máy qua Bluetooth; chủ bấm nút/nhập PIN trên máy (trong vỏ khóa); máy ký "rebind attestation" bằng credential máy cho credential app mới, **chỉ phạm vi máy đó**; server áp dụng sau cooldown + thông báo.
- **Ưu:** Không cần admin hay giấy; quyền phục hồi bám vào tài sản vật lý.
- **Nhược/rủi ro:** Ai có truy cập vật lý (nhân viên ca đêm, kẻ trộm) có thể chiếm máy → cần nút trong vỏ khóa, cooldown, thông báo. Không phục hồi tài khoản người dùng, chỉ quyền máy. Không dùng được khi chính máy mất khóa.
- **Công sức:** Trung bình–cao (máy cần UI, hợp đồng mới).
- **Tiên quyết:** D3 cho máy credential tin cậy; máy có nút/màn hình.
- **Thỏa:** D:97–100 nếu coi xác nhận vật lý là "kênh đã provision độc lập"; cần người dùng xác nhận cách hiểu này.
- **Nguồn:** [NIST SP 800-121 r2](https://csrc.nist.gov/pubs/sp/800/121/r2/upd1/final) (giới hạn Bluetooth); design D:97–106.

**Khuyến nghị D4:** **D4-A** làm đường tự phục vụ mặc định, với **D4-C** là đường cuối bắt
buộc phải có quy trình (design cũng yêu cầu khi không có yếu tố độc lập; máy mất khóa
luôn đi C). Nếu chỉ chọn một: A. Lý do: chi phí thấp, chuẩn NIST, không phụ thuộc phần
cứng máy. **B** khi chủ thường có nhiều thiết bị/nhân viên quản lý; **D** khi máy đặt nơi
được kiểm soát vật lý tốt.
**Tiêu chí chọn:** có người vận hành trực không; người dùng có chịu lưu code giấy không;
mức kiểm soát vật lý máy; chấp nhận cooldown bao lâu.

---

## D5. Topology proxy thực tế

Ràng buộc: A1 là mô hình thiết kế, chưa khẳng định Caddy tách quyền; proxy root trên
server ⇒ A1 thành A3 (D:21–24). Provenance bootstrap cần trusted topology, không tin
X-Forwarded-* tùy ý (D:170–171, D:407–412). Người dùng giữ HTTP/1.1.
Caddy mặc định ghi đè X-Forwarded-For/Proto/Host và bỏ giá trị client gửi; upstream có
thể là unix socket; HTTPS tự động cần DNS công khai + cổng 80/443; với IP/tên nội bộ
dùng CA nội bộ tự ký.

### D5-A. Không proxy: server Python tự kết thúc TLS

- **Mô tả:** `ssl` module bọc socket của server hiện tại; cert từ ACME client riêng (certbot) hoặc Tailscale cert.
- **Ưu:** Không có A1 trung gian; provenance là peer IP socket thật; ít thành phần.
- **Nhược/rủi ro:** Server một process `ThreadingHTTPServer` tự xử lý TLS handshake + slowloris (log/SECURITY_NOTES ghi luồng không giới hạn); gia hạn cert, reload cert phải tự làm; không có lớp hấp thụ DoS. Phép kiểm "proxy chỉ thấy envelope" (D:22–24) không áp dụng — E vẫn bắt buộc theo yêu cầu người dùng.
- **Công sức:** Trung bình (TLS, reload cert, giới hạn kết nối).
- **Tiên quyết:** Tên miền/cert; quyết định chấp nhận rủi ro DoS.
- **Thỏa:** D:170–171, D:409–411 (provenance rõ). Không đổi kiến trúc module (bọc ở `server/lib/http`).
- **Nguồn:** [Python ssl](https://docs.python.org/3/library/ssl.html); [Caddy automatic HTTPS](https://caddyserver.com/docs/automatic-https) (để so sánh); `log/SECURITY_NOTES.md:101`.

### D5-B. Caddy cùng host, user OS riêng, nói chuyện qua unix socket

- **Mô tả:** Caddy chạy user `caddy` (không root sau bind), server chạy user `flexmix`; secret server (HPKE private, ticket MAC, kw) ở thư mục 0700 của `flexmix`, Caddy không đọc được; Caddy→server qua unix socket quyền nhóm hẹp; server chỉ tin XFF từ socket đó.
- **Ưu:** Gần đúng mô hình A1 (khác user OS) với một máy; Caddy lo TLS/ACME/HTTP framing, giới hạn header/body; chi phí thấp.
- **Nhược/rủi ro:** Ai có root/sudo trên host là A3 (đọc cả hai); nhóm nhỏ thường dùng chung sudo → tách quyền dễ chỉ trên giấy. Server hiện nghe TCP; chuyển sang unix socket cần thay `http_server.py` (thuộc lib, không đổi module feature). Giới hạn header của Caddy **chưa kiểm** (liên quan D8 nếu envelope trong header).
- **Công sức:** Thấp–trung bình.
- **Tiên quyết:** Host Linux có DNS công khai, cổng 80/443; quy định ai có sudo.
- **Thỏa:** D:21–24 (A1 có điều kiện), D:409–411 nếu chỉ tin socket.
- **Nguồn:** [Caddy reverse_proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy); [Caddy automatic HTTPS](https://caddyserver.com/docs/automatic-https).

### D5-C. Caddy ở host biên riêng (VPS), server ở host trong qua đường hầm WireGuard/Tailscale

- **Mô tả:** Edge VPS chỉ chạy Caddy; server ở máy khác, chỉ nghe trên giao diện đường hầm; server tin XFF chỉ từ IP đường hầm của edge.
- **Ưu:** A1 thật sự tách máy: chiếm root edge không cho đọc khóa server → đúng giá trị E (D:22–23). Server không mở cổng ra Internet.
- **Nhược/rủi ro:** Thêm một máy, chi phí VPS, thêm độ trễ, thêm điểm hỏng; quản trị hai host. Edge bị chiếm vẫn thấy metadata, chặn traffic (D:17).
- **Công sức:** Trung bình.
- **Tiên quyết:** Ngân sách VPS; người biết vận hành WireGuard/Tailscale.
- **Thỏa:** D:17, D:21–24 tốt nhất trong bốn; D:409–411.
- **Nguồn:** [Caddy reverse_proxy / trusted_proxies](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy); [Tailscale Serve](https://tailscale.com/kb/1312/serve) (cho đường hầm).

### D5-D. Chỉ tailnet: `tailscale serve` kết thúc TLS trên host server, không mở Internet

- **Mô tả:** App và máy cài Tailscale; server chỉ truy cập trong tailnet; `tailscale serve` cấp cert `.ts.net` và proxy tới localhost, thêm header danh tính Tailscale.
- **Ưu:** Gần cấu hình hiện có (app_config nhắc Tailscale IP); A0 Internet bị loại phần lớn; dễ dựng.
- **Nhược/rủi ro:** Mọi điện thoại khách hàng phải cài/đăng nhập Tailscale — không khả thi cho sản phẩm bán ra, chỉ hợp pilot nội bộ. `tailscaled` chạy root cùng host → trung gian TLS cùng host là A3, không phải A1. Phụ thuộc dịch vụ bên thứ ba.
- **Công sức:** Thấp.
- **Tiên quyết:** Tài khoản tailnet; người dùng chấp nhận cài agent.
- **Thỏa:** Provenance có danh tính tailnet; **không thỏa** giả định A1 tách quyền.
- **Nguồn:** [Tailscale Serve](https://tailscale.com/kb/1312/serve); [Caddy automatic HTTPS — .ts.net](https://caddyserver.com/docs/automatic-https).

**Khuyến nghị D5:** **D5-B** cho bản phát hành đầu, với điều kiện ghi rõ ai có root/sudo
và test "Caddy user không đọc được secret". Lý do: chi phí thấp, Caddy lo TLS/framing,
vẫn có tách quyền có điều kiện. Chuyển **C** khi muốn A1 thật (khuyến nghị nếu có ngân sách
VPS). **D** chỉ cho pilot nội bộ; **A** nếu muốn loại bỏ trung gian và chấp nhận tự lo DoS/cert.
**Tiêu chí chọn:** có tên miền/IP công khai không; ngân sách host thứ hai; ai có root;
khách hàng có phải cài Tailscale không.

---

## D6. Phạm vi và thứ tự rollout mã hóa

Ràng buộc: E không là tùy chọn, không tự hạ cấp plaintext (D:9–10, D:59); GET chưa có adapter
thì chặn rollout profile (D:179); gate §10 yêu cầu GET/heartbeat/poll/result/auth/bootstrap
đều có wire adapter, cập nhật app/server/máy/tests đồng thời (D:460–463).
Chưa kiểm: có người dùng/máy thật đang chạy bản cũ hay không.

### D6-A. Phát triển theo lát dọc nhưng bật production một lần cho toàn profile

- **Mô tả:** Code/test từng nhóm route trên nhánh/staging; production chỉ chuyển khi toàn bộ gate §10 đạt; server bỏ hẳn đường plaintext cùng lúc; app và máy phát hành bản mới bắt buộc cập nhật.
- **Ưu:** Không có trạng thái hỗn hợp → không có downgrade; đúng nhất với D:179, D:460–463; dễ kiểm.
- **Nhược/rủi ro:** Big-bang: lỗi lớn ảnh hưởng mọi thứ; cần rollback plan (bản cũ không còn dùng được nếu đã đổi epoch/schema); app/máy cũ ngừng hoạt động.
- **Công sức:** Thấp về logic chuyển đổi, cao về kiểm thử trước ngày bật.
- **Tiên quyết:** Ít hoặc chưa có người dùng thật; điều khiển được cập nhật máy.
- **Thỏa:** D:9–10, D:59, D:179, D:460–463.
- **Nguồn:** design §10; [Google SRE Workbook — Canarying](https://sre.google/workbook/canarying-releases/) (rủi ro big-bang).

### D6-B. Production theo chặng, chặng máy↔server trước

- **Mô tả:** Bật profile cho heartbeat/poll/result trước (sau D3), rồi app bootstrap/enroll, app read, cuối cùng app mutation có ticket/ledger.
- **Ưu:** Chặng máy dùng product key bearer là điểm yếu nặng nhất (giả máy, nhận lệnh); firmware do nhóm kiểm soát nên dễ cập nhật đồng bộ; app ít bị ảnh hưởng ban đầu.
- **Nhược/rủi ro:** Trái tinh thần D:179/D:460 nếu hiểu "rollout profile" là toàn bộ — cần người dùng xác nhận chặng hóa được phép; mật khẩu/token app vẫn đi plaintext-trên-TLS trong thời gian chờ; ledger máy (D:305–308) phải xong trước.
- **Công sức:** Trung bình–cao (mỗi chặng một lần phát hành, test chéo).
- **Tiên quyết:** D3 xong; queue persistence adapter.
- **Thỏa:** Từng chặng không có downgrade nếu route chặng đó protected-only. Phụ thuộc diễn giải D:179.
- **Nguồn:** design D:281–310; [SRE Canarying](https://sre.google/workbook/canarying-releases/).

### D6-C. Production theo chặng, chặng app (bootstrap/auth) trước

- **Mô tả:** Bật bootstrap HPKE cho đăng ký/OTP/đăng nhập + app enrollment trước, rồi read, mutation, cuối cùng chặng máy.
- **Ưu:** Che mật khẩu/token/OTP sớm nhất trước A1 — đúng mục tiêu ban đầu người dùng nêu; app enrollment là tiền đề của D3-A/D4.
- **Nhược/rủi ro:** Chặng máy (product key bearer) còn yếu lâu hơn; cùng vấn đề diễn giải D:179. Bootstrap không chứng minh nguồn (D:110–113) nên lợi ích chủ yếu là che nội dung.
- **Công sức:** Trung bình–cao.
- **Tiên quyết:** Nguồn thời gian app (D2) — bootstrap cũng cần freshness (D:247).
- **Thỏa:** Như B.
- **Nguồn:** design D:110–114, D:247.

### D6-D. Dual-stack theo route với cờ phía server, chuyển dần rồi tắt legacy

- **Mô tả:** Server giữ allowlist route→chế độ {legacy, protected-only}; cờ do server quyết định (không do client khai), chuyển từng route, có hạn tắt legacy.
- **Ưu:** Rollback từng route; tương thích bản app/máy cũ trong thời gian chuyển.
- **Nhược/rủi ro:** Rủi ro downgrade: route ở legacy thì A1 đọc được; dễ quên tắt; **mâu thuẫn** "không để E là tùy chọn" và "không tự hạ cấp" (D:9–10, D:59) trừ khi mỗi route chỉ có một chế độ tại một thời điểm và không có fallback. Thêm logic phức tạp vào lib HTTP.
- **Công sức:** Cao.
- **Tiên quyết:** Có người dùng thật không thể cập nhật đồng thời.
- **Thỏa:** **Không thỏa** D:59 nếu có fallback; chỉ thỏa nếu là B/C có cờ.
- **Nguồn:** design D:9–10, D:59; [SRE Canarying](https://sre.google/workbook/canarying-releases/).

**Khuyến nghị D6:** **D6-A**. Lý do: repo cho thấy deployment còn LAN/Tailscale nội bộ,
không thấy bằng chứng có người dùng thật phải giữ tương thích (chưa kiểm — cần người dùng
xác nhận); A thỏa trọn D:179/D:460–463, không có cửa downgrade. Thứ tự phát triển nội bộ
đề xuất (không phải rollout): bootstrap/auth → app enrollment → máy (sau D3) → read/GET
(sau D8) → mutation + ticket/ledger. Nếu đã có khách hàng thật: chọn **B**.
**Tiêu chí chọn:** có người dùng/máy ngoài hiện trường không; có cơ chế bắt buộc cập nhật
app/máy không; ưu tiên che mật khẩu (C) hay chặn giả máy (B).

---

## D8. GET trạng thái và định danh máy cho wire adapter (cổng C2)

Mâu thuẫn: D:172–175 cho query `machine_id=<decimal positive canonical>`; server cấp
`fm_` + 32 hex (opaque). Thêm phát hiện: GET hiện **không xác thực** (SEC-08
expectedFailure), và app gọi một GET cho mỗi máy. Design: body rỗng không là cửa bỏ crypto;
chọn envelope trong header có hard bound **hoặc** chuyển caller sang request được bảo vệ
(D:176–179). RFC 9110 §9.3.1: nội dung (body) trong GET không có ngữ nghĩa chung, một số
hiện thực từ chối → loại "envelope trong body GET". RFC 9110 §5.4: HTTP không giới hạn
cố định độ dài header; server tự đặt giới hạn và trả 4xx.

### D8-A. Giữ GET, đổi profile query sang opaque ID canonical, envelope trong header

- **Mô tả:** Sửa đặc tả query: đúng một field `machine_id=fm_[0-9a-f]{32}` (lowercase, không percent-encoding, không trùng key); envelope nhị phân base64url một lớp trong một header riêng có hard bound (ví dụ ≤ vài KB, chốt sau đo); thêm kiểm quyền: chỉ người quản lý máy đọc status.
- **Ưu:** Giữ method/route; thay đổi nhỏ ở caller (cùng URL).
- **Nhược/rủi ro:** Hai đường adapter (body cho POST, header cho GET) → gấp đôi test negative; header base64 tăng ~4/3 kích thước; giới hạn header của Caddy/Python là điểm hỏng (Python 65536 byte/dòng đã kiểm cục bộ, Caddy chưa kiểm); log proxy có thể ghi header (ciphertext, vẫn là metadata). Giữ N request/máy → N lần HPKE + claim.
- **Công sức:** Trung bình.
- **Tiên quyết:** Sửa D:172–175; thêm kiểm quyền vào `machine_list_get.py` (giải SEC-08).
- **Thỏa:** D:176–179 (envelope header có hard bound); D:168–171 với query cố định.
- **Nguồn:** [RFC 9110 §5.4, §9.3.1](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.3.1); `machine_list_main.py:39–46`.

### D8-B. Đổi status sang POST được bảo vệ, giữ route constant `MACHINE_STATUS_GET`

- **Mô tả:** `/machine/trang-thai` nhận POST với envelope như mọi route; `machine_id` (opaque fm_) nằm trong business JSON; query rỗng như mọi POST (D:172). Server kiểm phiên + quyền quản lý máy.
- **Ưu:** Một đường adapter duy nhất; không cần đặc tả query/header; giải SEC-08.
- **Nhược/rủi ro:** Đổi hợp đồng HTTP method — cập nhật app (`machine_list_request.dart`), server (`handle_get` → `handle`), tests Python/Flutter/e2e cùng lúc (AGENTS.md cho phép khi người dùng yêu cầu). Tên constant `..._GET` giữ vì là động từ nghiệp vụ, không phải method HTTP. Vẫn N request/máy.
- **Công sức:** Thấp–trung bình.
- **Tiên quyết:** Người dùng đồng ý đổi method.
- **Thỏa:** D:176–178 ("chuyển caller sang request được bảo vệ cùng cập nhật contract/tests").
- **Nguồn:** design D:172–179; `tests/python/test_server_security.py:290`; `tests/e2e/run_e2e.py:157`.

### D8-C. Gộp online/last_seen vào USER_MACHINE_LIST, bỏ route status riêng

- **Mô tả:** `list_my_machines` trả thêm `online`/`last_seen` cho mỗi máy (dữ liệu từ `machine_transport` đã có); dashboard bỏ vòng gọi status; route `MACHINE_STATUS_GET` gỡ khỏi routing app/server.
- **Ưu:** Một request protected thay vì N (giảm HPKE/claim/ghi SQLite theo số máy, D:418–421); quyền đã được kiểm sẵn bằng JOIN machine_managers; xóa hẳn bề mặt SEC-08; không cần adapter GET.
- **Nhược/rủi ro:** Đổi hợp đồng lớn hơn (gỡ route, sửa dashboard refresh, tests Flutter mock `/machine/trang-thai` và Python relay/e2e dùng GET status). Muốn làm mới trạng thái phải gọi lại cả danh sách (payload lớn hơn với nhiều máy). Nếu có caller ngoài app (công cụ vận hành) dùng GET thì mất — chưa kiểm ngoài các caller trong repo.
- **Công sức:** Trung bình.
- **Tiên quyết:** Người dùng đồng ý gỡ route; inventory caller.
- **Thỏa:** D:176–179 (chuyển sang request được bảo vệ), D:174–175 (inventory caller).
- **Nguồn:** `dashboard_controller.dart:106–124`; `machine_list_get.py:8–29`; design D:418–421.

### D8-D. Giữ đặc tả decimal: thêm định danh số nguyên công khai cho máy

- **Mô tả:** Server cấp thêm `machine_no` số nguyên dương (rowid/sequence) dùng trong query GET; fm_UUID giữ nội bộ.
- **Ưu:** Không sửa D:172–175; query ngắn.
- **Nhược/rủi ro:** Hai định danh cho một máy → nhầm lẫn, migration app/QR/share/test; số tuần tự dễ dò (enumeration) — đặc biệt khi GET hiện không xác thực; vẫn cần envelope header như A. Không có lợi ích bảo mật.
- **Công sức:** Trung bình–cao.
- **Tiên quyết:** Migration schema `machines`.
- **Thỏa:** D:172–175 nguyên văn; tăng rủi ro ngoài design.
- **Nguồn:** `machine_write.py:17–24`; [OWASP API1 BOLA](https://api-security.owasp.org/editions/2023/en/0xa1-broken-object-level-authorization).

**Khuyến nghị D8:** **D8-C** (gộp trạng thái vào danh sách máy, bỏ GET). Lý do: loại bỏ
hẳn nhu cầu adapter GET (gate D:179), giảm N lần crypto/claim xuống một, quyền đã có sẵn
trong truy vấn danh sách, đóng SEC-08. Nếu muốn giữ route riêng để làm mới từng máy:
chọn **B**. **A** chỉ khi có lý do bắt buộc giữ GET (cache, công cụ ngoài). Tránh **D**.
Dù chọn gì, sửa D:172–175 sang opaque `fm_[0-9a-f]{32}` hoặc bỏ mục query GET.
**Tiêu chí chọn:** số máy mỗi tài khoản; tần suất làm mới trạng thái; có caller ngoài app
không; chấp nhận mức thay hợp đồng nào.

---

## Tổng hợp khuyến nghị vòng 1

| Quyết định | Khuyến nghị | Phương án dự phòng | Cần người dùng xác nhận |
| --- | --- | --- | --- |
| D1 | A: token phần cứng + token dự phòng | C nếu ≥3 người | cadence, validity, ai giữ |
| D2 | A: NTS server/máy + Roughtime app (qua giai đoạn D đo) | C (sửa D:243) | Δ, L_max sau đo; model Pi |
| D3 | B: provision lúc lắp + claim chủ riêng | A | ai flash máy, UI máy |
| D4 | A: recovery code (+C bắt buộc cho ca mất hết/máy) | B | có người vận hành trực |
| D5 | B: Caddy cùng host, user riêng, unix socket | C | ai có root, có domain |
| D6 | A: bật production một lần | B nếu đã có khách thật | có người dùng thật không |
| D8 | C: gộp vào danh sách máy, bỏ GET | B | đồng ý đổi hợp đồng |

Phụ thuộc chéo: D3-B/D4-C cần khóa provisioning/admin → liên quan D1. D2 chặn mọi
route có Seal kể cả bootstrap → chặn D6. D8 là điều kiện D6 (D:179). D5 quyết định
nguồn provenance cho quota bootstrap (D:407–412).

Giới hạn nghiên cứu vòng 1: không chạy prototype, không đo; các khả năng thư viện
(Roughtime/NTS Dart, ký Keystore Ed25519, tpm2 Python, giới hạn header Caddy) **chưa kiểm**.

## Vòng 2 — operator hợp nhất phản biện (07/10/2026)

Người dùng yêu cầu chốt sớm nên không chạy thêm vòng researcher/critic. Operator áp các mục
[CHẶN] của critic (D2-1, D3-1, D6-1, D8-1) và D1-1, D4-1, D5-1 để ra bộ 4 phương án cuối:

- D1: A token phần cứng + dự phòng · B máy air-gapped file mã hóa · C ngưỡng 2-of-3 · D Cloud KMS
  (thay D1-D hai tầng). Tiên quyết chung: keystore release riêng cho APK (SEC-13) và quy trình image máy.
- D2 (app; server/máy luôn chrony NTS): A Roughtime · B HTTPS-Date đa nguồn (sdwdate/htpdate) ·
  C thời gian server ký theo nonce, cần sửa D:243 · D NTS-FFI. D2-D cũ chuyển thành lộ trình pilot.
- D3 (gói trọn vẹn; TPM/ATECC608 là tùy chọn lưu khóa): A BT + xác nhận vật lý · B provision lúc
  lắp + claim code · C mã ngắn kiểu RFC 8628 hiện trên máy · D enrollment code admin cấp nhập vào máy.
- D4 (C admin đối soát luôn có): C · A+C · B+C · D+C.
- D5: A server tự TLS · B Caddy cùng host user riêng · C Caddy VPS biên + đường hầm · D Cloudflare
  Tunnel (tailnet-only chỉ còn là pilot). Mọi phương án phải giữ HTTP/1.1 (`protocols h1` với Caddy).
- D6: A bật một lần toàn profile · B chặng máy trước · C chặng app trước · D canary theo deployment.
  D3-A loại D6-B.
- D8: A GET opaque ID + header · B POST từng máy · C gộp vào danh sách máy · D POST batch nhiều máy.

Chưa kiểm lại: critic báo Roughtime đã thành RFC 10049 (Experimental, 10/2026).
