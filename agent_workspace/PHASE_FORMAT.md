# Định dạng phase cho một task

## Hai file tham chiếu

- `../phase-00.pdf` (tính từ gốc repo `androidv1.0`) là **mẫu cấu trúc và cách trình bày của một phase**: trang mở đầu, tóm tắt, số liệu, sơ đồ, phụ thuộc, từng component/task, phát hiện và câu hỏi. Nội dung trong PDF thuộc dự án khác; không chép công nghệ, số liệu hoặc kết luận của nó sang `androidv1.0`.
- `../version1.0/docs/review_version1_0.html` là **đầu vào review hiện trạng của repo FlexMix version1.0**, không phải kế hoạch triển khai và không phải mẫu nội dung của mọi phase. Planner phải kiểm lại các phát hiện liên quan trên mã `androidv1.0` trước khi biến chúng thành việc phải làm.

## Cách chia task

Một task có thể gồm một hoặc nhiều phase, đánh số `00`, `01`, `02`... theo thứ tự phụ thuộc. Mỗi phase là một phần việc có mục tiêu và kết quả kiểm được, đủ nhỏ để coder và tester thực hiện mà không phải tự đoán phạm vi. Không chia phase chỉ để đạt số lượng hoặc số trang như PDF.

Planner đề xuất toàn bộ chuỗi phase trước khi bắt đầu code. Với mỗi phase, ghi rõ:

1. **Tên, mục tiêu và lý do đứng ở vị trí này.** Phase `00` dành cho điều kiện nền hoặc rủi ro chặn các phase sau nếu có.
2. **Đầu vào, đầu ra, hợp đồng phải giữ.** Nêu người dùng/thiết bị nào tương tác, đường request hoặc dữ liệu đi qua những đâu, file liên quan có `file:dòng` cho hiện trạng.
3. **Component → task → bước.** Mỗi task có kết quả quan sát được, file dự kiến sửa, thứ tự, phụ thuộc, người/thiết bị bị ảnh hưởng. Nêu nhánh lỗi, huỷ, timeout hoặc rollback khi liên quan.
4. **Xong khi và phép kiểm.** Ghi tiêu chí dạng “điều kiện → kết quả”, lệnh test/quan sát và bằng chứng sẽ thu. Phân biệt test máy phát triển với kiểm trên Raspberry Pi hoặc thiết bị thật.
5. **Rủi ro, giả định, quyết định cần chốt.** Mã phát hiện từ review phải được gán vào một phase/task cụ thể hoặc ghi rõ ngoài phạm vi kèm lý do. Không tự đánh dấu một giả định là sự thật.
6. **Cần từ phase trước / mở đường cho phase sau.** Một phase chỉ được coi là xong khi tiêu chí của nó có bằng chứng; phần chưa kiểm được ghi trạng thái và lý do, không báo đạt.

## Báo cáo HTML cho từng phase

Lead lưu `agent_workspace/tasks/<tên-task>/phase-00.html`, `phase-01.html`... tương ứng. Đây là **một báo cáo riêng cho mỗi phase**, theo phong cách của `phase-00.pdf`, mở được trực tiếp bằng trình duyệt và in được. Không dùng một file HTML tổng hợp thay cho các phase.

Mỗi file HTML có các phần sau, bỏ phần không áp dụng thay vì điền nội dung giả:

1. Trang mở đầu: tên task/phase, ngày, trạng thái, quy mô thực tế và chú giải mức ưu tiên.
2. “Bạn cần biết” và tóm tắt 30 giây: phase làm gì, kết quả mong đợi, rủi ro chính.
3. Sơ đồ khối/luồng khi chúng giúp hiểu hệ thống; mỗi sơ đồ ghi nguồn và chỗ nào là suy luận.
4. Bảng component/task, thứ tự thực hiện, phụ thuộc và file chính.
5. Chi tiết từng task: làm gì, các bước, xong khi, đường lỗi, phép kiểm, phát hiện liên quan.
6. Phát hiện còn mở, câu hỏi cần quyết định, việc ngoài code và rủi ro tiến độ (nếu có).
7. Kết quả thực hiện: file đã đổi, lệnh kiểm, output/exit code, tiêu chí đạt/chưa đạt và giới hạn kiểm chứng. Khi mới lập kế hoạch, ghi “chưa thực hiện”, không viết như thể đã chạy.
8. Số đo của tester cho luồng nhiều bước: tên flow và từng khối, số mẫu, p50/p95, lỗi, môi trường và đường dẫn log máy đọc được. Reviewer ghi khối nào chiếm thời gian, mức tin cậy của phép đo, giả thuyết và quyết định sửa hoặc chưa sửa. Nếu có sửa, báo cáo so sánh trước/sau trong cùng điều kiện và test hồi quy.

Số đếm, trạng thái và phát hiện trong báo cáo phải lấy từ task và kết quả kiểm thực tế. Viết tiếng Việt có dấu, câu ngắn, giải thích thuật ngữ khó. Báo cáo HTML là hiện vật để người dùng đọc; `TASK.md` là hồ sơ vận hành cho team. Cập nhật cả hai khi phase thay đổi hoặc kết thúc.
