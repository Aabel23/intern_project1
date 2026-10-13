# Cách đánh dấu tiến độ roadmap giao khách đầu tiên

Thiết kế hiển thị timeline theo Phase đã được user chốt làm mẫu roadmap chính ngày 13/10/2026. Việc chốt mẫu hiển thị không tự duyệt nội dung 44 bước hoặc cổng triển khai.

Nguồn tiến độ duy nhất là [`roadmap-progress.json`](roadmap-progress.json). Trang [`production-roadmap-report.html`](production-roadmap-report.html) đọc sổ này khi mở qua `python3 -m documentation.serve_architect` tại gốc repo và tự cập nhật mỗi 15 giây. Trạng thái ban đầu `0/44` nghĩa là **chưa ghi bằng chứng đóng bước trong sổ mới**, không có nghĩa mọi code đều chưa viết. `todo` hiển thị là “Chưa xác nhận” vì trạng thái công việc cũ chưa được kiểm lại.

## Quy tắc cho agent

1. Nhận bước nào thì cập nhật đúng ID đó thành `doing`, ghi tên người thực hiện. Không đánh dấu hộ bước của agent khác.
2. Làm xong và có kết quả kiểm thì ghi `review`, thêm đường dẫn bằng chứng. Người thực hiện không tự ghi `done` cho việc của mình.
3. Người kiểm đối chiếu bằng chứng với tiêu chí ở cột “Bằng chứng”, rồi ghi `done` cùng tên người kiểm. Nếu chưa đạt, trả về `doing` với nguyên nhân.
4. Bị vướng thì ghi `blocked` và lý do trong `note`. Khi vướng mắc cần đổi thiết kế, báo user và chờ quyết định; không tự sửa code.
5. Các bước cần quyết định của user chỉ được ghi `done` khi có quyết định của user. Cổng G0–G4 chỉ được duyệt sau khi mọi bước bắt buộc đạt và user xác nhận cổng; agent không tự nhận cổng đã qua.
6. Bằng chứng chỉ là **đường dẫn/định danh** tới biên bản, kết quả kiểm hoặc commit. Không ghi OTP, mật khẩu, khóa hay dữ liệu khách vào sổ.

## Lệnh cập nhật

Chạy từ gốc repo. Tên trạng thái cố định: `todo`, `doing`, `review`, `done`, `blocked`.

```bash
python3 documentation/plan/roadmap_progress.py step 1.2 doing --by "Agent A"
python3 documentation/plan/roadmap_progress.py step 1.2 review --by "Agent A" --evidence "documentation/plan/evidence/I-01-baseline.md"
python3 documentation/plan/roadmap_progress.py step 1.2 done --by "Agent A" --reviewer "Người kiểm" --evidence "documentation/plan/evidence/I-01-baseline.md"
python3 documentation/plan/roadmap_progress.py step 1.3 blocked --by "Agent B" --note "Thiếu thiết bị Pi; đã báo người phụ trách"
python3 documentation/plan/roadmap_progress.py check
```

Sau khi user duyệt một cổng, operator mới ghi (ví dụ):

```bash
python3 documentation/plan/roadmap_progress.py gate G0 --by "Tên người duyệt" --evidence "đường-dẫn-quyết-định"
```

Không dùng ví dụ trên để đánh dấu tiến độ thật. Các lệnh chỉ minh họa cú pháp; sổ hiện chưa có bước nào đạt. Nếu bước đã `done` phát hiện hồi quy, trả về `doing` hoặc `blocked` và ghi nguyên nhân. Cổng đã qua phải được xem xét lại trước khi phát hành.
