# Hợp đồng v2 · D1–D10 áp lên version1.1 (user chốt 12/10/2026)

User duyệt toàn bộ đề xuất D1–D10 trong `reports/Thiết kế triển khai hệ IoT.md` và chọn **cách 3**: giữ nguyên nghiệp vụ máy pha chế của `version1.1` (menu, kho, pump, order), chỉ thay lớp kết nối của máy (`machine/config`, `machine/server_connection`, `machine/pairing`, `machine/main.py`), cộng server và app. Không cần chờ thông số phần cứng Pi; nghiệm thu thiết bị thật làm sau.

**Thứ tự ưu tiên:** file này thắng mọi chỗ mâu thuẫn trong `cloud-protection.md`, `claim.md`, `bt-claim.md`, `relay-status.md`, `auth.md`, `COMPATIBILITY.md`, `security-boundary.md`. Phần không nhắc tới ở đây giữ nguyên.

## D1 · Danh tính máy tạo ở xưởng

- Trạm xưởng chạy trên Pi: `python -m machine.config.provision --name <tên>`. Lệnh này đọc serial CPU, sinh khóa ký P-256 (PKCS8 PEM, file 0600, ghi atomic) nếu chưa có, sinh `S` 32 byte CSPRNG nếu chưa có (file 0600), rồi in JSON `{serial, public_key, qr}`. Chạy lại không đổi khóa hay S.
- Operator chạy trên server: `python -m server.src.factory_register --serial <serial> --name <tên> --public-key <b64u65>`. Chèn `devices(serial, name, public_key, key_id)`. Idempotent theo `(serial, public_key)`; cùng serial khác khóa → `KEY_CONFLICT`, chỉ đổi được bằng `--rekey` (ghi audit).
- `key_id = "mk_" + b64u(SHA256(public_key))[:22]`. Máy tự tính, không cần server cấp.
- **Bỏ route `MACHINE_ACTIVATION_SEND`** cùng bảng `activation_challenges`, `seal_verifier`. Server không bao giờ thấy hay lưu `S`. `S` chỉ còn là PSK của phiên BLE. Gate "retry commit chưa rõ" biến mất.
- `machine_id` (UUID) do server cấp lúc đăng ký. Máy biết nó qua phản hồi `MACHINE_HELLO_SEND`, lưu cache không bí mật.

## D2 · Khôi phục quyền chủ

- `USER_MACHINE_REMOVE` (`/app/user/machine/remove`) body `{v, machine_id}`: Owner tự nhả máy; `owner_user_id=NULL`, ghi `device_audit`. Không phải Owner → `FORBIDDEN 403`.
- Operator: `python -m server.src.factory_register --unbind --serial <serial>` (xóa owner) và `--rekey` (đổi khóa máy hỏng/flash lại), đều ghi `device_audit`.
- **Cửa sổ claim:** máy chỉ quảng bá BLE nhận chủ khi lần hello gần nhất báo `owned=false`, hoặc trong 10 phút đầu sau khi dịch vụ khởi động. Reset vật lý có thời gian ân hạn cần nút cứng; để phiên bản sau.

## D3 + D4 · Phiên BLE v2

Giữ nguyên transport (GATT service/RX/TX, framing `u32be+UTF8 ≤8192`), suite HPKE mode_psk, `PSK=S`, `psk_id="flexmix-seal-v1:"+serial`, exporter một lần cho mỗi phản hồi. Thay đổi:

- Nhãn `flexmix-bt-claim-v2` / `flexmix-bt-response-v2`, `pv:2`. Bản v1 và v2 gặp nhau thì fail đóng.
- **Bỏ stage `confirm`** và trạng thái `WAIT_CONFIRM/CONFIRMED`. Stage hợp lệ: `probe|wifi|claim`.
- Hello `H={pv:2,type:"hello",serial,session_id,machine_nonce,public_key,machine_public_key}`; `h0=b64u(SHA256(F(H)))`.
- `info=J(["flexmix-bt-claim-v2","app","machine",serial,session_id,h0])`.
- Request `R={pv:2,type:"request",session_id,send_id,stage,enc,ct}`, AAD `J([2,"flexmix-bt-claim-v2","app","machine",serial,session_id,h0,send_id,stage])`.
- Response `Q={pv:2,type:"response",session_id,send_id,stage,nonce,ct}`, khóa `export("flexmix-bt-response-v2",16)`, AAD `J([2,"flexmix-bt-response-v2","machine","app",serial,session_id,h0,send_id,stage,b64u(SHA256(F(R)))])`.
- Plaintext chung `{type,serial,session_id,machine_nonce,client_nonce,...}`.
- `probe` → `authenticated` thêm `{machine_public_key, machine_id|null, online}`. `h1=b64u(SHA256(F(H)‖F(R1)‖F(Q1)))`. Sau Q1 cả hai phía đã xác nhận khóa.
- `wifi` (tùy chọn, tối đa một lần) mang `session_transcript=h1`, `ssid`, `password` → `wifi_result {session_transcript:h1, ok:true, machine_id|null, online}`. Sau đó `h2=b64u(SHA256(F(H)‖F(R1)‖F(Q1)‖F(R2)‖F(Q2)))`.
- `claim` mang `session_transcript` = transcript mới nhất (`h1` nếu bỏ qua Wi-Fi, `h2` nếu có), cùng `challenge` và `server_challenge_signature` → `claim_proof {claim_id, local_session_binding, machine_proof}`. Một claim mỗi phiên; xong thì đóng.
- Cache `send_id` tối đa 3. Lỗi trước khi mở được probe: đóng im lặng. Lỗi sau đó: phản hồi mã hóa `{type:"error",code}` rồi đóng.

## Claim (thay `claim.md`)

- `USER_MACHINE_ACTIVATE` step `begin`: `{v, step:"begin", serial}` → `{claim_id, machine_id, challenge:{claim_id,machine_id,user_id,purpose:"claim_owner",nonce,expires_at}, server_challenge_signature}`. Serial lấy từ QR; chưa đăng ký → `MACHINE_UNTRUSTED 401`; đã có chủ → `ALREADY_OWNED 409`.
- Chữ ký server (`server-sign-1`, raw r‖s low-s) trên `J(["flexmix-claim-v1",claim_id,machine_id,user_id,purpose,nonce,expires_at])`. `nonce` là b64u 32 byte, `expires_at` là epoch ms.
- Máy ký `J(["flexmix-claim-accept-v1",b64u(challenge_bytes),local_session_binding])`, với `challenge_bytes` là đúng mảng J ở trên.
- step `complete`: `{v, step:"complete", claim_id, machine_proof, local_session_binding}` → `{machine:{id,serial,name,role:"owner"}}`. Thứ tự kiểm: claim thuộc user → đã tiêu thụ thì trả lại kết quả cũ → hết hạn → proof → `UPDATE devices SET owner_user_id=? WHERE id=? AND owner_user_id IS NULL`. Transaction lỗi deadlock thì retry.

## D5 · Chữ ký

Giữ ECDSA P-256, raw r‖s, low-s. Máy ký bằng `deterministic_signing=True` rồi chuẩn hóa `s`. Server đã từ chối high-s.

## D6 · Sàn khởi động chống replay

Server ghi `boot_wall_ms` lúc khởi động và từ chối mọi envelope có `0 < sent_at_ms < boot_wall_ms` bằng `INVALID_ENVELOPE`. Client gặp lỗi này thì bootstrap lại đồng hồ (đã có).

## D7 + D8 · Relay

- Poll mới nhất thắng: khi máy mở poll mới, poll cũ đang treo được trả ngay `command:null`.
- Bỏ semaphore 64 chung. Thay bằng giới hạn kết nối 256, trong đó poll tối đa 160, relay chờ tối đa 48. Hết chỗ → `SERVICE_UNAVAILABLE 503`, không xếp hàng.
- Instruction cho phép (version1.1): `machine.status.read`, `nhan_menu`, `cap_nhat_menu`, `nhan_kho`, `nap_kho`. `data` là object ≤ 12 KiB, server không đọc nội dung.
- Máy chống chạy lặp theo `request_id`: nhớ 32 kết quả gần nhất, lệnh trùng thì trả lại kết quả cũ.
- Kết quả máy: `{ok:true,data}` hoặc `{ok:false,error:{code,message?}}`. `message` chỉ có khi handler version1.1 trả `{"loi": ...}` (lỗi nghiệp vụ đã kiểm); exception không bao giờ đi lên. Code: `COMMAND_FAILED`, `UNSUPPORTED_INSTRUCTION`, `INVALID_DATA`, `MACHINE_READ_FAILED`, `COMMAND_EXPIRED`.
- Wire máy↔server: poll `{v:1}` → `{command:null}` hoặc `{command:{v,request_id,machine_id,instruction,data,remaining_ms}}`; result `{v:1,request_id,result}` → `{accepted:true}`; hello `{v:1}` (sent_at 0) → `{server_time_ms, machine_id, owned}`.

## D9 · Mật khẩu

Tối thiểu **15 ký tự**, tối đa 256 (NIST SP 800-63B-4 khi mật khẩu là yếu tố duy nhất). Áp ở server và app.

## D10 · Vòng đời phiên

- Mỗi refresh token lưu riêng trong `refresh_tokens(hash, session_id, used_at)`. Token đã dùng mà quay lại → thu hồi cả phiên, trả `SESSION_EXPIRED`.
- Hạn tuyệt đối **90 ngày** từ lúc đăng nhập (`sessions.absolute_expires_at`). Refresh không kéo dài quá mốc này.

## Vá tài khoản kèm theo

- Quota login giữ chỗ nguyên tử: kiểm `failures + in_flight` và tăng `in_flight` trong cùng một lần khóa.
- Email không tồn tại vẫn chạy Argon2 trên hash giả để thời gian phản hồi như nhau.
- Tối đa 4 phép Argon2 chạy đồng thời.
- Gửi SMTP có timeout tổng 15 giây.
- Deadlock MySQL (1213) và lock wait timeout (1205) được retry tối đa 3 lần trước khi trả 503.
