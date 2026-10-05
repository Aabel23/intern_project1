# TASK — <tên việc>

## Yêu cầu gốc

<giữ nguyên lời người dùng>

## Phạm vi và trạng thái

- Branch: <tên branch>
- File/luồng liên quan: <danh sách>
- Trạng thái: MỚI | ĐÃ RÕ | ĐANG LÀM | ĐANG KIỂM | XONG

## Kế hoạch (lead ghi từ kết quả planner nếu cần)

### Phase lớn — <giai đoạn triển khai team AI>

- Trang đọc: `phases/<ten-giai-doan>/index.html`.
- Mục tiêu, đầu vào, phạm vi, cổng nghiệm thu: <...>.
- Team / thứ tự bàn giao: lead → planner → tester/coder → reviewer/security → lead.
- Phụ thuộc / đi tiếp / quay lui: <...>.

#### Phase con — <tên và mục tiêu>

- Đặc tả: `phases/<ten-giai-doan>/<ten-phase-con>.html`.
- Nghiên cứu/source/file:dòng và giả thuyết cần kiểm: <...>.
- Định hướng/lý do/luồng hoạt động và dữ liệu: <...>.
- Input, yêu cầu, task/bước, file/caller: <...>.
- Vai phụ trách/hiện vật bàn giao: <...>.
- Phép kiểm, acceptance, lỗi/timeout/quay lui: <...>.
- Trạng thái và bằng chứng: CHƯA THỰC HIỆN.

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
