# Team agent — quy trình đã chốt

Operator là phiên Codex chính: giữ yêu cầu, đọc nguồn, giao việc, chuyển phản biện
qua lại, hợp nhất quyết định, kiểm bằng chứng và cập nhật HTML/Markdown.

## Từ ý tưởng đến thiết kế

1. Giao **hai architect độc lập** cùng mục tiêu và ràng buộc, với góc nhìn khác nhau.
   Mỗi agent phải có đề xuất ban đầu từ mã/nguồn thực trước khi đọc đề xuất bên kia.
2. Chuyển hai đề xuất cho nhau; yêu cầu tìm phản ví dụ, thiếu sót, đánh đổi và cách
   kiểm. Không dựng cuộc tranh luận giả hoặc coi hai câu trả lời riêng là đã tranh luận.
3. Operator đối chiếu nguồn và gửi bất đồng còn lại cho cả hai. Lặp khi có vấn đề
   chặn mới; kết luận nêu giới hạn/giả định, không hứa tối ưu tuyệt đối hay bất khả xâm phạm.
4. Vẽ HTML theo PHASE_FORMAT: bản đồ feature, quan hệ thành phần và từng luồng
   hoạt động/dữ liệu, nhánh lỗi/timeout/rollback. Người dùng cùng sửa và chốt thiết kế.
   **Chưa được giao planner/coder triển khai ý tưởng khi người dùng chưa chốt.**

## Từ thiết kế đã chốt đến hoàn thiện

1. **Planner** lập plan phase lớn/phase con, bước nhỏ nhất có đầu ra nghiệm thu riêng,
   đúng phụ thuộc; mỗi bước có ID ổn định, input/output, file/caller, kiểm và rollback.
   Operator review; nếu plan lộ thiếu sót thiết kế phải quay lại bước thiết kế.
2. **Một coder** viết đúng một bước sẵn sàng của plan, không tự mở rộng phạm vi.
3. **Một reviewer độc lập** kiểm diff mới và kết quả kiểm của bước đó; operator
   đối chiếu bằng chứng. Tester/security tham gia khi có rủi ro hoặc phép đo cần vai riêng.
4. Nếu chưa đạt, đánh ✗ kèm nguyên nhân ở sơ đồ tiến độ, giao coder sửa rồi reviewer
   kiểm lại. Bước phụ thuộc chờ. Lỗi cần đổi thiết kế phải đưa lại HTML cho người dùng.
5. Chỉ đánh ✓ khi review và kiểm phù hợp đã đạt. Tiếp tục từng bước tới khi toàn
   bộ tiêu chí xong. Không tự commit/push/deploy hoặc chạy thiết bị thật ngoài phạm vi.

## Model và quyền

- Cập nhật 07/10/2026: **coder Claude dùng Sonnet effort medium**;
  CLI `--agent coder --model sonnet --effort medium`, frontmatter của coder đặt rõ
  model/effort. **Coder GPT dùng Sol effort low** (yêu cầu “Sol light”); operator
  chọn ID Sol runtime hỗ trợ, ví dụ hiện tại `gpt-6.1-sol`, và truyền rõ `low` khi
  spawn coder thay vì kế thừa từ operator. Không tự nâng model/effort hoặc đổi dòng
  model khi vướng; plan thiếu thì trả planner/architect làm rõ.
- Planner giữ cấu hình trước: Claude Code Opus effort medium,
  CLI `--model opus --effort medium`. Chỉ đổi khi người dùng yêu cầu riêng.
  Lượt hai architect trước đó dùng Codex vì Claude CLI hết hạn mức; đó là lịch sử
  lượt chạy, không phải quy tắc tự đổi model coder khi thiếu khả năng truy cập.
- Coder bám đúng bước plan và tiêu chí, diff tối thiểu, code phẳng; không tự thiết
  kế thêm. Planner cung cấp đủ quyết định/hợp đồng trước khi giao coder. Chi tiết
  và nguồn cú pháp model/effort ở `agents/coder.md`.
- Mỗi file triển khai là một khối chức năng có trách nhiệm chính/cửa vào rõ;
  code bên trong nhóm bằng mini region và comment quan trọng theo mẫu project.
  Planner ghi mapping khối/file và hợp đồng; coder không tự tách module ngoài plan.
- Reviewer phải là agent độc lập với coder. Codex operator vẫn kiểm cuối;
  không tự nhận hai vai của một phiên là hai agent.
- Architect/planner/reviewer chỉ đọc, không sửa code. Một coder ghi sản phẩm mỗi task;
  với task tài liệu, operator có thể giao coder sửa HTML/CSS/JS trong phạm vi riêng.
- Nội dung role tại agents/, đồng bộ .claude/agents/ bằng sync_agents.py.
- Quyền thực tế theo runtime; lỗi công cụ phải xử lý rõ, không tự nhận đã chạy.

## HTML và trạng thái tiến độ

Giữ ít trang HTML, nhưng đủ chi tiết hệ thống cần người dùng duyệt. Không coi
“tóm tắt” là lý do bỏ feature/luồng; dùng mục lục, nhóm feature và phần mở rộng.
Sơ đồ plan nằm trong index.html, không tạo trang riêng cho từng phase.

| Ký hiệu | Ý nghĩa | Điều kiện cập nhật |
|---|---|---|
| ○ | Chưa làm | Đã có bước trong plan được review |
| → | Đang làm / đang review | Ghi rõ giai đoạn hiện tại |
| ✓ | Đạt | Reviewer và phép kiểm phù hợp đã đạt, có bằng chứng |
| ✗ | Lỗi / chưa đạt | Có nguyên nhân, tác động và bước sửa/kiểm lại |
| ⏸ | Chờ | Thiết kế chưa chốt hoặc phụ thuộc chưa đạt |

Không tick tương tác để người xem tự đánh nghiệm thu. Trạng thái do operator cập
nhật từ bằng chứng, không dùng localStorage làm nguồn chuẩn. Sửa lỗi xong có thể
đổi ✗ sang ✓ sau kiểm lại; lịch sử lỗi giữ trong TASK/internal.

## Bằng chứng và bàn giao

Architect: nguồn file:dòng, phương án, đối chiếu phía kia, phản ví dụ, giả định.
Planner: thiết kế đã chốt và từng bước nghiệm thu; không bịa lịch/ngưỡng tải.
Coder: file/diff, lệnh/output/exit code, giới hạn; giữ transaction/quyền/hợp đồng.
Reviewer: file:dòng, kịch bản, hậu quả, chứng cứ và phép kiểm lại; không sửa code.
Operator: kiểm bằng chứng thật, trạng thái HTML và hồ sơ Markdown khớp nhau.

Kiểm tối ưu hiệu năng cần số đo nền và sau sửa cùng điều kiện; không gọi phương án
nhanh/tối ưu chỉ vì ít file hay ít bước. Test/harness nằm trong tests/.
Quy ước chung ở CODE_STYLE.md. Ưu tiên: người dùng → AGENTS.md → MODULE_PATTERN.md
→ CODE_STYLE.md → TEAM/TASK → file vai → tài liệu sources/.
