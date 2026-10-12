# C-04 · Kiến trúc contracts tối thiểu cho skeleton

**Vai:** Architect. **Trạng thái:** chờ C-02 và C-03. **Loại:** tổng hợp kiến trúc, không code.

## Đặc tả

Tổng hợp hai nghiên cứu độc lập thành một thiết kế vận hành cho bốn luồng: đăng ký/phiên, nhận máy, relay và hỏi trạng thái trực tiếp. Nêu khối nào phát, chuyển, kiểm và trả thông điệp; cùng một ý nghĩa nghiệp vụ đi qua cloud, LAN/Bluetooth về sau ra sao mà skeleton chỉ cần cloud. Tách thông điệp chung khỏi chứng thực của từng đường. Nêu tradeoff và điểm cần user quyết.

## Input và bối cảnh cần đọc

- Kết quả C-02, C-03; code và tài liệu repo trong phạm vi hai phiếu đó; `documentation/architect/features/account.html` và `documentation/architect/cryptography.html`.
- Không truy cập kho ghi nhớ cá nhân, kể cả qua liên kết trong repo; Operator không chuyển nội dung hay kết luận từ đó vào prompt.

## File được tạo hoặc sửa

- Dự thảo `documentation/architect/features/contracts.html` theo style tài liệu hiện có. Chỉ viết khi nhận đủ hai nghiên cứu; Operator sẽ so với quyết định user trước khi đưa user đọc.
- Không sửa code hoặc các tài liệu kiến trúc khác.

## Hợp đồng đầu ra

Một sơ đồ khối và luồng skeleton; danh mục thông điệp ở mức ý nghĩa, chưa ép tên trường/thuật toán; bảng trách nhiệm app/server/máy; bảng điểm khác nhau giữa trạng thái server và trạng thái máy; tối đa các quyết định thật sự cần user chốt. Phần menu/share/offline chỉ nêu ranh giới tương thích về sau.

## Ca kiểm và cách kiểm

Đi bộ qua tình huống email mới → nhận máy mới → hỏi máy → trả lời; thêm nhánh sai mã niêm phong, máy đã có chủ, máy offline và kết quả về muộn. Một câu hỏi trạng thái không bị thay bằng cache server. Người không có máy trong quyền không hỏi được.

## Phạm vi cấm

Không đọc second brain, không tự coi nghiên cứu là quyết định user, không chọn chi tiết gói/thuật toán chưa được chốt, không code, không mở `project1_server`.
