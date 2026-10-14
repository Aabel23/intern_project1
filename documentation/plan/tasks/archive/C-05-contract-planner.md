# C-05 · Khóa hợp đồng skeleton và phát phiếu coder

**Vai:** Planner Opus high. **Trạng thái:** chờ C-01, C-04 và quyết định cuối của user. **Loại:** đặc tả kỹ thuật, chưa code sản phẩm.

## Đặc tả

Biên dịch thiết kế đã được user chốt thành hợp đồng đủ chặt cho coder: đăng ký/OTP/đăng nhập/refresh, gửi OTP qua Gmail SMTP của tài khoản chủ dự án, nhận máy, danh sách/chọn máy, relay và câu hỏi trạng thái trực tiếp. Viết phiếu riêng cho từng slot S-01…S-03, M-01…M-03, A-01…A-03 và I-01 trong `assignments.md`. Mỗi phiếu phải quy định file, hàm, dữ liệu, trạng thái lỗi, ca kiểm, cách kiểm và phạm vi cấm; không để coder tự chọn thiết kế.

## Input và bối cảnh cần đọc

- `documentation/plan/archive/contracts-decision-log.md`, tài liệu C-04 đã được user phản biện/chốt, quyết định user trong chat, `documentation/plan/archive/assignments.md`, lộ trình HTML.
- Code hiện hành đúng các file của từng slot; hiến pháp và quy trình repo đang áp dụng.

## File được tạo hoặc sửa

- `contracts/messages/` chỉ cho luồng skeleton; ví dụ đúng và lỗi hiện ở `contracts/http/flows/` (trước đây là `contracts/examples/`); `contracts/COMPATIBILITY.md`.
- Phiếu coder riêng trong `documentation/plan/tasks/`.
- Chỉ cập nhật routing ở phiếu coder được giao sau này, không làm trong C-05.

## Hợp đồng đầu ra

Mỗi thông điệp ghi người gửi/nhận, ý nghĩa, trường bắt buộc/tùy chọn, ràng buộc, thành công/lỗi, quy tắc phiên bản và ví dụ. Câu hỏi trạng thái có mã tương quan xuyên suốt app–server–máy và không thể được đáp bằng cache server. Phiếu coder phân file sở hữu rõ, không hai phiếu cùng ghi một file đồng thời.

Với S-01, đặc tả riêng luồng server gửi OTP từ Gmail của chủ dự án qua SMTP với App Password lưu ở cấu hình server, lỗi xác thực hoặc gửi thư, và OTP chỉ tới email của người đang đăng ký. Hai địa chỉ thử nghiệm và ranh giới môi trường thử lấy từ `assignments.md`. Không đưa App Password vào app hay tài liệu.

Với I-01, viết trình tự nghiệm thu cụ thể: tự yêu cầu gửi OTP tới từng email thử nghiệm qua API sản phẩm; nhận OTP do user báo và xác minh qua API; kiểm đăng nhập và luồng máy thật; cuối cùng xác định chính xác các bản ghi thử và cách xóa khỏi DB sau khi ca đạt. Biên bản chỉ ghi kết quả và phạm vi dọn dữ liệu, không ghi mã OTP. Nếu tài khoản thử còn cần cho ca kế tiếp, dọn sau ca đó; không đụng tài khoản hoặc máy ngoài phạm vi thử.

## Ca kiểm và cách kiểm

Kiểm mọi ví dụ khớp đặc tả; giả lập đi bộ toàn bộ luồng trên giấy với kết quả thành công và lỗi. Đối chiếu mỗi phiếu với một hợp đồng và một tiêu chí nghiệm thu của skeleton. Nếu còn thiếu quyết định về bảo vệ hoặc nhận máy, dừng và báo Operator, không điền mặc định.

## Phạm vi cấm

Không code app/server/máy; không phát phiếu coder khi hợp đồng còn mơ hồ; không mở rộng sang menu sync, share hoặc offline trong đợt skeleton.
