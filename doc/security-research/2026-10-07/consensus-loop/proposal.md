# Phương án hợp nhất Codex–Claude để trình người dùng

Ngày 07/10/2026. ĐỀ XUẤT, chưa thay R5; không phải nghiệm thu production.
Mục tiêu: khép các ambiguity đã tìm thấy, giảm state và handoff không cần thiết,
giữ kiến trúc đã khóa. Chưa đủ benchmark/proof để gọi tối ưu tuyệt đối.

## Hợp đồng khuyến nghị

1. **Durability:** commit bảo mật chỉ chấp nhận WAL + FULL/EXTRA hoặc DELETE + EXTRA.
   Thiết lập/đọc lại PRAGMA trên mỗi connection trước commit bảo mật đầu tiên;
   không đổi cấu hình trong lifetime connection. COMMIT lỗi không cấp quyền Seal/
   tác động tiếp. Media phải honor flush; fault test hỗ trợ evidence, không là proof.
   Media không đạt thì không rollout, không dùng nonce ngẫu nhiên để miễn gate.
2. **Claim trước CAS:** commit bền claim và direct SQL cùng DB (nếu có), serialize
   outcome rồi mở transaction CAS SEAL_STARTED riêng, commit bền trước Seal.
   Không gộp claim và CAS. Crash giữa hai bước vẫn giữ claim: không Seal lại bằng
   cùng attempt; attempt mới lấy semantic outcome hoặc unknown theo ledger.
   Seq/witness chỉ cấp sau commit tương ứng bền; witness không chứng minh nội dung
   hoặc extension. Số commit tăng/chi phí cần đo, không gán trước số fsync.
3. **Response singleton:** đề xuất bỏ exact ciphertext resend ở D:213. Duplicate
   attempt chỉ transport error không ciphertext; client dùng attempt/context mới.
   Protected semantic cache kiểm quyền hiện hành; bootstrap policy theo route
   challenge/account/token còn active, expiry/epoch/clock/store. Không lưu ciphertext
   chỉ để resend; vẫn giữ durable Seal-started và state cần audit/retention. Không
   bỏ ledger/result/unknown. Lựa chọn này giảm state, chưa chứng minh nhanh hơn.
4. **Revoke ordering:** bỏ exact resend không xóa mọi race quyền→send. Giữ ordering
   authoritative transaction theo R5: revoke trước admission/claim thì reject;
   revoke sau admission đã commit không thể hứa thu hồi bytes đang gửi hay tác động
   đã dispatch. Outcome cache mới cần điểm admission quyền rõ; không giữ DB lock
   xuyên network send. Không tuyên bố thời điểm nhận bytes là điểm atomic revoke.
5. **Quota:** giữ DB chung; budget trước claim theo commit dự kiến từng route,
   cộng bound crypto/hash/SMTP/storage và accounting commit thực. Session quota
   đề xuất từ chối phiên mới khi hết budget, không đẩy phiên đang dùng ra vì token
   mồ côi. Reserve result/recovery cần kiểm shared writer/fsync, không chỉ workers.
   Ngưỡng sau đo. Tách DB chỉ nghiên cứu nếu số đo đòi hỏi và có crash/atomicity plan.
6. **Enrollment rollout:** account có sẵn chưa có credential được xác nhận không
   cấp machine write chỉ bằng password/session+PoP. Khóa mới ở trạng thái pending,
   chưa là yếu tố chứng minh quyền cũ và không được chặn chủ enroll/recover. Owner/
   admin xác nhận credential cụ thể qua kênh đã provision hoặc recovery proof độc
   lập; reject/revoke pending trái phép. Không tự thu hồi mọi credential đã xác
   nhận khác: multi-installation và quyền revoke cần user policy. Inventory kênh
   từng account trước rollout; thiếu proof thì giữ write lock/reprovision có quyền.
7. **Boot epoch:** ưu tiên trình phương án operator xác nhận qua kênh quản trị ngoài
   snapshot domain; không giả định kênh đó đã tồn tại. Bind domain/deployment/epoch/
   boot challenge mới/decision; one-use và deadline monotonic của boot khi wall
   clock chưa tin cậy. Khóa có sẵn/offline root/khóa riêng tùy ceremony được duyệt.
   Chưa xác nhận thì quarantine route có Seal/tác động, recovery ngoài profile qua
   kênh riêng. Không mở ngoại lệ heartbeat/result. Live-memory restore vẫn unsupported.
8. **Trusted time:** OS/network time API Android không tự đạt gate. Khảo sát nguồn
   time được xác thực ngoài packet profile, trust anchor được provision độc lập
   với key/manifest đang cần kiểm (có thể cùng root với purpose binding nếu hợp lệ).
   Cần bootstrap, delay/uncertainty/holdover và rollback threat evidence; không
   coi DB snapshot tự làm OS clock rollback, không blanket cấm server time đã
   chứng minh capability. Chưa có nguồn đạt => không rollout profile hiện tại.
9. **HPKE:** giữ gate Base/info/AAD/Export và vector liên ngôn ngữ. Turnkey API đã
   đọc không đáp ứng dùng trực tiếp, chưa kết luận mọi version/library Dart.
   Khảo sát pinned PyHPKE/Dart/FFI theo phương án B; chưa chọn suite/lib/wire.
10. **I11:** option nghiên cứu, RNG độc lập qua reboot và collision bound cần proof/
    vector. Không thay durable ledger/epoch/media gate; không tự nâng thành bắt buộc.

## Quyết định còn cần người dùng

Durability profile và chi phí hai transaction; bỏ exact resend; quota/session
policy; enrollment proof và multi-installation; ceremony epoch/availability;
nguồn time; suite/library/FFI và mọi thay đổi wire. Đồng thuận architect chỉ là
khuyến nghị để trình duyệt, không phải quyền triển khai hoặc chốt thiết kế.

## Evidence còn thiếu

Power-loss/storage thực, disk-full/I/O/commit fault, Seal count/CID, revoke races,
enrollment concurrency, boot confirmation replay, original source snapshots,
S03 §8, pinned HPKE source/vectors, time capability và benchmark tài nguyên.
Không đánh dấu pass hoặc dùng test kill process thay power loss.
