# C-02 · Research danh tính máy và nhận chủ lần đầu

**Vai:** Researcher Sonnet medium. **Trạng thái:** có thể bắt đầu song song C-03. **Loại:** research + case study, không code.

## Câu hỏi được giao

Nghiên cứu cách một máy mới chứng minh danh tính và gắn với tài khoản đầu tiên khi người dùng có mã niêm phong trong hộp, máy gửi wifi qua Bluetooth và máy kết nối server. So sánh phương án về rủi ro chiếm máy trước, thay bo mạch/reset và vận hành bán qua đại lý. Tìm ít nhất hai case study hoặc chuẩn công khai có thể kiểm nguồn; nêu phần phù hợp và không phù hợp với repo.

## Input và bối cảnh cần đọc

- Chỉ tài liệu và code trong repo: `documentation/architect/features/machine-activation.html`, `documentation/architect/cryptography.html`, `version1.1/machine/pairing/`, `version1.1/machine/config/`, `version1.1/machine/server_connection/`, `server/configuration/routing.py`.
- Nguồn công khai có trích dẫn trực tiếp. Không truy cập kho ghi nhớ cá nhân, kể cả qua liên kết trong repo.

## File được tạo hoặc sửa

Không sửa file. Báo cáo cho Operator; không ghi báo cáo thô vào repo.

## Hợp đồng đầu ra

Một bảng gồm: phương án, điều kiện tiên quyết, luồng chứng minh người đứng cạnh máy và máy thật, cách server kiểm, dữ liệu cần đặt lên máy trước khi bán, rủi ro còn lại, nguồn case study. Đề xuất một hướng kèm điều kiện khiến hướng đó không còn phù hợp. Đánh dấu rõ suy luận của researcher; không gọi đó là quyết định của user.

## Ca kiểm và cách kiểm

Phản biện ít nhất các tình huống: người mở hộp trước, người biết lại mã niêm phong sau khi bán lại, máy reset, giả serial CPU, nghe lén Bluetooth, và server thấy khóa máy lần đầu. Mỗi kết luận kỹ thuật có nguồn hoặc bằng chứng code.

## Phạm vi cấm

Không đọc second brain; không dùng quyết định từ vault trong prompt hoặc báo cáo; không sửa code, không chọn công nghệ thay user, không mở `project1_server`.
