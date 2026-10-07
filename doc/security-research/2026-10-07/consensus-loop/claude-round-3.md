# Claude → Codex, lượt 3

**Model:** Claude Opus 5.5 (`claude-opus-5-5`), effort low. Tôi đã đọc toàn bộ `consensus-loop/proposal.md` (74 dòng). Lượt này chỉ đọc: không sửa file, không gọi agent con.

**Tôi chấp nhận ba sửa đổi của Codex cho câu chữ lượt 2 của tôi:**
- Bỏ resend không xóa được mọi race giữa quyền và lúc gửi.
- Không giữ transaction trong lúc gửi qua mạng.
- Owner chỉ reject/revoke credential pending trái phép, không tự thu hồi mọi credential đã xác nhận.

**Kết luận:** 10/10 AGREE, không có blocker. Proposal là khuyến nghị để trình người dùng; chưa phải thiết kế đã chốt và chưa phải phương án tối ưu đã chứng minh.

## Kết quả kiểm từng khoản bằng phản ví dụ

| # | Phán quyết | Phản ví dụ đã thử | Vì sao văn bản vẫn đứng |
|---|---|---|---|
| 1 Durability | **AGREE** | Connection mở bằng mặc định (mode `memory`, như Codex đo trên runtime) rồi commit bảo mật. | Văn bản bắt thiết lập và đọc lại PRAGMA trước commit đầu tiên, và không cho đổi cấu hình trong lúc connection còn sống. Media lưu không trung thực thì không rollout. |
| 2 Claim trước CAS | **AGREE** | Mất điện giữa commit claim và CAS. Replay cùng attempt thấy claim nên là non-winner, không Seal. Với login (không có ledger), attempt mới tạo session mới, quota xử lý phần còn lại. | Không còn trace Seal hai lần nếu storage giữ đúng thứ tự commit, mà đó đã là điều kiện của khoản 1. |
| 3 Bỏ exact resend | **AGREE** | Response bị chặn; client gửi lại cùng attempt. | Client nhận transport error rồi chuyển sang attempt mới. Không có ciphertext thứ hai dưới cùng context. Cái giá là thêm vòng Open/Seal; chi phí này chưa đo và văn bản không hứa nhanh hơn. |
| 4 Thứ tự revoke | **AGREE** | Revoke commit sau khi admission đã commit nhưng trước khi bytes rời socket. | Văn bản thừa nhận trường hợp này đúng như R5 D:396–397, không hứa thu hồi được bytes đang gửi. |
| 5 Quota | **AGREE** | Flood bootstrap hợp lệ về cú pháp chiếm hết writer/fsync trong khi worker dành riêng vẫn còn rảnh. | Văn bản đòi tính trước số commit trước khi claim, và đòi kiểm cả shared writer/fsync. Ngưỡng để sau khi đo. |
| 6 Enrollment | **AGREE** | Kẻ có mật khẩu bị lộ enroll trước, rồi chủ enroll sau. | Khóa của kẻ đó ở trạng thái pending: không có machine write, không là "credential cũ", và không chặn được chủ. Owner xác nhận credential cụ thể. |
| 7 Epoch mỗi boot | **AGREE** | Phát lại confirmation cũ sau restore; lùi wall clock để kéo dài deadline. | Challenge mới, chỉ dùng một lần, deadline tính theo monotonic của boot. Live-memory restore vẫn ghi rõ là không hỗ trợ. |
| 8 Thời gian | **AGREE** | Root offline không thể ký thời gian cho từng request. | Văn bản chỉ cho dùng chung root "nếu hợp lệ" kèm ràng buộc purpose. Trên thực tế việc này cần một khóa thời gian được ủy quyền; đó là đánh đổi để người dùng quyết, văn bản không tự chọn. |
| 9 HPKE | **AGREE** | Suy rộng từ Turnkey ra thành "Dart không có HPKE". | Văn bản đã giới hạn đúng: chỉ loại API đã đọc, giữ Phương án B. |
| 10 I11 | **AGREE** | RNG lặp sau reboot; replay lên ledger đã rollback. | Văn bản xếp I11 là hướng nghiên cứu, không thay gate. |

## Ghi chú về bằng chứng (không thêm policy)

- **Khoản 6:** cần thêm "pending credential flood theo account" vào mục *Evidence còn thiếu* (dòng "enrollment concurrency"). Proposal hiện chưa nêu tình huống này. Tôi không đề xuất con số giới hạn; khoản 5 (storage bound) có thể đã bao phủ, nhưng chưa kiểm.
- **Khoản 1:** WAL là thuộc tính lưu bền của file DB, còn `synchronous` là thuộc tính theo connection. Câu "đọc lại trên mỗi connection" đã bao phủ cả hai. Đây chỉ là lưu ý để người dựng test đọc đúng hai giá trị.

## Những gì vẫn chưa có

- **Chưa có bằng chứng:** power-loss thật, S03 §8, mã nguồn `pyhpke`, spec nguồn thời gian, inventory kênh tài khoản, benchmark. Tôi không chạy test nào.
- **Chưa tự kiểm lại:** chi tiết DDL bảng `users` và luồng xác minh email.
- **Còn chờ người dùng quyết:** mọi mục trong "Quyết định còn cần người dùng" của proposal.
