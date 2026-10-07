# TASK — <tên việc>

## Yêu cầu gốc

<giữ nguyên lời người dùng>

## Phạm vi và trạng thái

- Branch: <tên branch>
- File/luồng liên quan: <danh sách>
- Trạng thái: MỚI | ĐÃ RÕ | ĐANG LÀM | ĐANG KIỂM | XONG

## Tài liệu người dùng

- Trang tóm tắt: `index.html`; chỉ thêm 1–2 HTML theo nội dung khi thật sự cần.
- HTML mô tả hệ thống/luồng và trạng thái chính; nghiên cứu, phân công và bằng
  chứng chi tiết giữ trong Markdown. Không tạo HTML theo từng phase.

## Cổng thiết kế

- Hai architect: <session/đề xuất và lượt phản biện qua lại>.
- Quyết định, đánh đổi và vấn đề còn lại: <Markdown nội bộ>.
- Thiết kế HTML và phiên bản: <...>.
- Người dùng đã chốt: CHƯA; chỉ chuyển planner khi có câu trả lời chốt.

## Kế hoạch nội bộ (sau chốt thiết kế, từ planner)

### Phase lớn — <giai đoạn triển khai team AI>

- Kế hoạch nội bộ: `internal/phases/<ten-giai-doan>/index.md`.
- Mục tiêu, đầu vào, phạm vi, cổng nghiệm thu: <...>.
- Team / thứ tự bàn giao: operator → planner → coder → reviewer độc lập → operator.
- Phụ thuộc / đi tiếp / quay lui: <...>.

#### Phase con — <tên và mục tiêu>

- Đặc tả nội bộ: `internal/phases/<ten-giai-doan>/<ten-phase-con>.md`.
- Nghiên cứu/source/file:dòng và giả thuyết cần kiểm: <...>.
- Định hướng/lý do/luồng hoạt động và dữ liệu: <...>.
- Input, yêu cầu, task/bước, file/caller: <...>.
- Vai phụ trách/hiện vật bàn giao: <...>.
- Phép kiểm, acceptance, lỗi/timeout/quay lui: <...>.
- Trạng thái và bằng chứng: CHƯA THỰC HIỆN.

## Tiến độ từng bước

| ID | Phụ thuộc | Input → output | Coder/reviewer | Kiểm/rollback | Trạng thái + bằng chứng/lỗi |
|---|---|---|---|---|---|
| <ID> | | | | | ○ CHƯA LÀM |

Operator cập nhật cùng sơ đồ index.html. ✓ chỉ sau review/kiểm đạt; ✗ ghi nguyên
nhân và bước sửa; → đang làm/review; ⏸ chờ phụ thuộc. Giữ lịch sử lỗi ở hồ sơ nội bộ.

## Tiêu chí nghiệm thu

| Mã | Điều kiện → kết quả cần thấy | Lệnh/quan sát kiểm | Trạng thái và bằng chứng |
|---|---|---|---|
| TC1 | | | CHƯA |

## Thời gian từng khối và toàn luồng (khi task có flow nhiều bước)

- Lệnh, môi trường, mã phiên đo, đường dẫn log: <...>
- Số mẫu và số lỗi: <...>

| Flow | Khối | p50 | p95 | Tổng flow p50/p95 | Trước/sau | Giới hạn phép đo |
|---|---|---:|---:|---:|---|---|
| <tên> | <tên> | | | | | |

## Bàn giao và quyết định

- Coder: <file, diff, lệnh, exit code, giới hạn>
- Tester: <test, lỗi bắt được, lệnh, exit code>
- Reviewer/security: <mã phát hiện, file:dòng, kịch bản; hoặc phạm vi đã xem>
- Lead: <đạt, sửa tiếp, hay cần người dùng chốt; lý do và bằng chứng>
