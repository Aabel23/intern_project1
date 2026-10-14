# Cách đánh dấu tiến độ roadmap giao khách đầu tiên

[`../plan.json`](../plan.json) là nguồn nội dung lộ trình; [`../plan.html`](../plan.html) chỉ tải và hiển thị JSON. Khi chỉnh lộ trình, đọc và sửa `plan.json`, không đọc hoặc sửa nội dung trong HTML. Giữ nguyên ID, nội dung và bằng chứng của bước đã hoàn tất; phạm vi mới được bổ sung vào cùng plan, không tạo một roadmap hoặc sổ tiến độ khác. Đây là quy tắc user chốt ngày 13/10/2026 và cách lưu nội dung user yêu cầu ngày 14/10/2026.

Nguồn tiến độ duy nhất là [`roadmap-progress.json`](roadmap-progress.json). Trang `plan.html` tải `plan.json`, sau đó đọc sổ tiến độ khi mở qua `python3 -m documentation.serve_architect` tại gốc repo và tự cập nhật mỗi 15 giây. **G0 đã đạt 4/4 bước và được user duyệt.** 21 bước bổ sung trong `plan.json` đang là bản chi tiết chờ user duyệt; chúng đều ở trạng thái `todo`.

## Quy tắc cho agent

1. Nhận bước nào thì cập nhật đúng ID đó thành `doing`, ghi tên người thực hiện. Không đánh dấu hộ bước của agent khác.
2. Làm xong và có kết quả kiểm thì ghi `review`, thêm đường dẫn bằng chứng. Người thực hiện không tự ghi `done` cho việc của mình.
3. Người kiểm đối chiếu bằng chứng với tiêu chí ở cột “Bằng chứng”, rồi ghi `done` cùng tên người kiểm. Nếu chưa đạt, trả về `doing` với nguyên nhân.
4. Bị vướng thì ghi `blocked` và lý do trong `note`. Khi vướng mắc cần đổi thiết kế, báo user và chờ quyết định; không tự sửa code.
5. Các bước cần quyết định của user chỉ được ghi `done` khi có quyết định của user. Cổng G0–G4 chỉ được duyệt sau khi mọi bước bắt buộc đạt và user xác nhận cổng; agent không tự nhận cổng đã qua.
6. Bằng chứng chỉ là **đường dẫn/định danh** tới biên bản, kết quả kiểm hoặc commit. Không ghi OTP, mật khẩu, khóa hay dữ liệu khách vào sổ.
7. Không xóa, đánh số lại, đặt về `todo` hay làm lại bước đã `done`. Phát hiện hồi quy hoặc yêu cầu mới thì ghi vấn đề và bổ sung bước mới vào `plan.json` cùng sổ này; phần đã đạt vẫn giữ bằng chứng gốc.

## Lệnh cập nhật

Chạy từ gốc repo. Tên trạng thái cố định: `todo`, `doing`, `review`, `done`, `blocked`.

```bash
python3 documentation/plan/progress/roadmap_progress.py step 1.2 doing --by "Agent A"
python3 documentation/plan/progress/roadmap_progress.py step 1.2 review --by "Agent A" --evidence "documentation/plan/evidence/I-01-baseline.md"
python3 documentation/plan/progress/roadmap_progress.py step 1.2 done --by "Agent A" --reviewer "Người kiểm" --evidence "documentation/plan/evidence/I-01-baseline.md"
python3 documentation/plan/progress/roadmap_progress.py step 1.3 blocked --by "Agent B" --note "Thiếu thiết bị Pi; đã báo người phụ trách"
python3 documentation/plan/progress/roadmap_progress.py check
```

Sau khi user duyệt một cổng, operator mới ghi (ví dụ):

```bash
python3 documentation/plan/progress/roadmap_progress.py gate G0 --by "Tên người duyệt" --evidence "đường-dẫn-quyết-định"
```

Không dùng ví dụ trên để đánh dấu tiến độ thật. Các lệnh chỉ minh họa cú pháp; G0 hiện có bốn bước `done`. Khi phát hiện hồi quy, tạo bước xử lý mới và liên kết bằng chứng về bước gốc; không xóa dấu hoàn tất cũ. Nếu hồi quy ảnh hưởng phát hành, chặn cổng chưa duyệt cho tới khi bước xử lý mới đạt.
