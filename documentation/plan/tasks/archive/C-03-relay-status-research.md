# C-03 · Research relay và câu hỏi trạng thái trực tiếp

**Vai:** Researcher Sonnet medium. **Trạng thái:** có thể bắt đầu song song C-02. **Loại:** research + case study, không code.

## Câu hỏi được giao

Thiết kế tối thiểu để app hỏi một máy đang kết nối ra server, nhận **câu trả lời hiện tại từ máy** qua relay, và phân biệt câu trả lời đó với cờ online mà server tự suy ra. Nghiên cứu timeout, mất kết nối, kết quả về muộn, gửi lại cùng mã và kiểm người hỏi có quyền trên máy. Tìm case study/chuẩn công khai phù hợp với mô hình máy nằm sau router.

## Input và bối cảnh cần đọc

- Chỉ tài liệu và code trong repo: `documentation/architect/features/command-relay.html`, `documentation/architect/system-architecture.html`, `server/configuration/routing.py`, `version1.1/machine/main.py`, `version1.1/machine/server_connection/machine_server_request.py`, `flutter_app/lib/feature/dashboard/`.
- Nguồn công khai có trích dẫn trực tiếp. Không truy cập kho ghi nhớ cá nhân, kể cả qua liên kết trong repo.

## File được tạo hoặc sửa

Không sửa file. Báo cáo cho Operator; không ghi báo cáo thô vào repo.

## Hợp đồng đầu ra

Mô tả hai luồng riêng: server báo online dựa vào kết nối của máy, và app hỏi trạng thái trực tiếp được máy trả lời. Có bảng kết quả thành công, offline, timeout, máy trả lỗi và kết quả đến sau timeout. Đề xuất tối thiểu cho skeleton, nêu phần chỉ cần khi sau này có lệnh ghi.

## Ca kiểm và cách kiểm

Dùng sơ đồ chuỗi thời gian để chứng minh một yêu cầu của app không thể bị đáp bằng dữ liệu cache như thể là mới; người không có quyền không hỏi được; máy ngắt giữa chừng không làm request treo vô hạn. Chỉ ra bằng chứng code hiện tại cho mỗi điểm phải thay.

## Phạm vi cấm

Không đọc second brain; không sửa code; không kéo menu sync, LAN/Bluetooth vận hành, hệ sự kiện hay hàng đợi lệnh bền vào skeleton; không mở `project1_server`.
