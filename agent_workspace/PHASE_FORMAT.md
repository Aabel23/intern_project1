# Định dạng kế hoạch phase lớn / phase con của team AI


## Phase lớn và phase con của team AI

Theo yêu cầu người dùng ngày 05/10/2026, kế hoạch triển khai có hai cấp:
**phase lớn** là giai đoạn triển khai của cả team AI; **phase con** là phần việc
có đầu vào/đầu ra riêng, đủ rõ để giao và kiểm. Task/bước nằm bên trong phase con,
không thay phase con bằng danh sách chuyên đề hay task phẳng.

- Trang tổng quan `index.html` → `phases/<ten-giai-doan>/index.html` → các file
  `<ten-phase-con>.html`. Tên file theo nội dung, số hiệu phase chỉ để tra phụ thuộc.
- Mỗi phase lớn: mục tiêu, phạm vi, đầu vào, sơ đồ phụ thuộc phase con, team tham
  gia và thứ tự bàn giao, cổng nghiệm thu, điều kiện đi tiếp/quay lui.
- Mỗi phase con: nghiên cứu mã và nguồn có file:dòng; thông tin đã biết/giả thuyết
  cần kiểm; luồng hoạt động/dữ liệu bằng sơ đồ khối; định hướng và lý do; câu hỏi
  cần giải quyết; yêu cầu chức năng/ràng buộc; việc cần làm theo thứ tự; file/caller;
  phân công từng vai; input/output/bằng chứng bàn giao; phép kiểm và acceptance;
  nhánh lỗi/timeout/hủy/rollback; trạng thái thực và giới hạn kiểm chứng.
- Lead điều phối; planner nghiên cứu/đặc tả; tester sở hữu test/số đo; một coder
  ghi sản phẩm mỗi task; reviewer rà diff; cybersecurity tham gia theo rủi ro.
  Vai không cần chạy đồng thời. Chỉ mở việc phụ thuộc khi đầu vào đã có bằng chứng.
- Kế hoạch chưa triển khai ghi rõ CHƯA THỰC HIỆN. Nghiên cứu đọc mã khác kết quả
  test. Test/harness được chuẩn bị trước cổng cần nó, tránh phụ thuộc vòng.
- Phase mở rộng chỉ kích hoạt theo nhu cầu/số đo; không buộc làm mọi nhánh hoặc
  tự thay thiết kế đã chốt. PDF không là điều kiện chặn khi người dùng đã bỏ yêu cầu.

## Quy ước tài liệu người dùng đọc

Theo yêu cầu người dùng ngày 05/10/2026, mọi báo cáo, nghiên cứu, kế hoạch và
tài liệu bàn giao để người dùng đọc phải là HTML, theo bố cục mẫu trong file này.
Quy ước áp dụng cả nghiên cứu trước triển khai, không chỉ báo cáo phase có code.
Markdown chỉ giữ cho hồ sơ vận hành nội bộ như TASK.md, hướng dẫn và file vai.
Nếu file mẫu PDF chưa có trong môi trường, bám bố cục được mô tả dưới đây và
ghi rõ chưa đối chiếu được hình thức với PDF; không tạo số liệu hoặc kết quả giả.

## Hai file tham chiếu

- `../phase-00.pdf` (tính từ gốc repo `androidv1.0`) là **mẫu cấu trúc và cách trình bày của một phase**: trang mở đầu, tóm tắt, số liệu, sơ đồ, phụ thuộc, từng component/task, phát hiện và câu hỏi. Nội dung trong PDF thuộc dự án khác; không chép công nghệ, số liệu hoặc kết luận của nó sang `androidv1.0`.
- `../version1.0/docs/review_version1_0.html` là **đầu vào review hiện trạng của repo FlexMix version1.0**, không phải kế hoạch triển khai và không phải mẫu nội dung của mọi phase. Planner phải kiểm lại các phát hiện liên quan trên mã `androidv1.0` trước khi biến chúng thành việc phải làm.

## Bộ tài liệu dài hạn

Theo yêu cầu cập nhật của người dùng ngày 05/10/2026, planner phải vạch toàn bộ
lộ trình dài hạn và chia thành file HTML con có tên theo nội dung. `index.html`
là cửa đọc, có sơ đồ tổng thể và liên kết tới từng phần. Không dùng tên
`phase-00.html` / `phase-XX.html` cho tài liệu bàn giao. Số chặng chỉ dùng trong
lộ trình để biểu thị thứ tự, không thay tên nội dung.

Tùy phạm vi, tách tổng quan, kiến trúc, vòng đời request, mô hình/luồng dữ liệu,
bảo mật, sức chứa/độ tin cậy, kiểm chứng, vận hành và lộ trình mở rộng. Không tạo
file rỗng chỉ cho đủ nhóm. Mỗi file phải có nội dung đủ để lập task thực hiện.

Luồng hoạt động và dữ liệu trình bày bằng sơ đồ khối thực sự (SVG/HTML hoặc
công cụ tương đương), có nhãn khối, mũi tên, dữ liệu truyền, nhánh lỗi và chú
giải hiện trạng/đề xuất. Không dùng đoạn sơ đồ chữ trong code block thay hình.
Sơ đồ mở offline và in rõ; dữ liệu nhạy cảm chỉ biểu thị tên trường, không dùng giá trị thật.

Lộ trình phân biệt gần hạn, trung hạn và dài hạn có điều kiện; mỗi chặng có
phụ thuộc, đầu ra, tiêu chí đi tiếp và cách quay lui. Không bịa lịch, tải hoặc
ngân sách. Những nhánh đổi API/runtime/database phải ghi điều kiện kích hoạt
và quyết định kiến trúc cần người dùng chốt trước khi triển khai.

## Cách chia task

Một task có một hoặc nhiều chặng đặt tên theo mục tiêu, theo thứ tự phụ thuộc. Mỗi chặng có kết quả kiểm được, đủ nhỏ để coder và tester thực hiện mà không phải đoán phạm vi. Số hiệu cổng nghiệm thu chỉ giúp tra phụ thuộc; không dùng làm tên tài liệu. Không chia chặng để đạt số lượng hoặc số trang.

Planner đề xuất toàn bộ lộ trình trước khi bắt đầu code. Với mỗi chặng, ghi rõ:

1. **Tên, mục tiêu và lý do đứng ở vị trí này.** Chặng nền giải quyết điều kiện hoặc rủi ro chặn việc sau khi thực sự cần.
2. **Đầu vào, đầu ra, hợp đồng phải giữ.** Nêu người dùng/thiết bị nào tương tác, đường request hoặc dữ liệu đi qua những đâu, file liên quan có `file:dòng` cho hiện trạng.
3. **Component → task → bước.** Mỗi task có kết quả quan sát được, file dự kiến sửa, thứ tự, phụ thuộc, người/thiết bị bị ảnh hưởng. Nêu nhánh lỗi, huỷ, timeout hoặc rollback khi liên quan.
4. **Xong khi và phép kiểm.** Ghi tiêu chí dạng “điều kiện → kết quả”, lệnh test/quan sát và bằng chứng sẽ thu. Phân biệt test máy phát triển với kiểm trên Raspberry Pi hoặc thiết bị thật.
5. **Rủi ro, giả định, quyết định cần chốt.** Mã phát hiện từ review phải được gán vào một phase/task cụ thể hoặc ghi rõ ngoài phạm vi kèm lý do. Không tự đánh dấu một giả định là sự thật.
6. **Phụ thuộc / mở đường cho việc sau.** Chặng chỉ được coi là xong khi tiêu chí có bằng chứng; phần chưa kiểm ghi trạng thái và lý do, không báo đạt.

## Tài liệu HTML theo nội dung

Lead lưu `agent_workspace/tasks/<tên-task>/index.html` và các file con có tên
theo nội dung. Bố cục tham khảo PDF; PDF không quyết định tên file hay ép mọi
nghiên cứu thành một phase. Khi triển khai, cập nhật kết quả ngay trong tài liệu
con liên quan và liên kết từ trang tổng quan.

Mỗi file HTML có các phần sau, bỏ phần không áp dụng thay vì điền nội dung giả:

1. Trang mở đầu: tên task/chuyên đề, ngày, trạng thái, quy mô thực tế và chú giải mức ưu tiên.
2. “Bạn cần biết” và tóm tắt 30 giây: chuyên đề làm gì, kết quả mong đợi, rủi ro chính.
3. Sơ đồ khối/luồng khi chúng giúp hiểu hệ thống; mỗi sơ đồ ghi nguồn và chỗ nào là suy luận.
4. Bảng component/task, thứ tự thực hiện, phụ thuộc và file chính.
5. Chi tiết từng task: làm gì, các bước, xong khi, đường lỗi, phép kiểm, phát hiện liên quan.
6. Phát hiện còn mở, câu hỏi cần quyết định, việc ngoài code và rủi ro tiến độ (nếu có).
7. Kết quả thực hiện: file đã đổi, lệnh kiểm, output/exit code, tiêu chí đạt/chưa đạt và giới hạn kiểm chứng. Khi mới lập kế hoạch, ghi “chưa thực hiện”, không viết như thể đã chạy.
8. Số đo của tester cho luồng nhiều bước: tên flow và từng khối, số mẫu, p50/p95, lỗi, môi trường và đường dẫn log máy đọc được. Reviewer ghi khối nào chiếm thời gian, mức tin cậy của phép đo, giả thuyết và quyết định sửa hoặc chưa sửa. Nếu có sửa, báo cáo so sánh trước/sau trong cùng điều kiện và test hồi quy.

Số đếm, trạng thái và phát hiện trong báo cáo phải lấy từ task và kết quả kiểm thực tế. Viết tiếng Việt có dấu, câu ngắn, giải thích thuật ngữ khó. Báo cáo HTML là hiện vật để người dùng đọc; `TASK.md` là hồ sơ vận hành cho team. Cập nhật cả hai khi kế hoạch hoặc chặng triển khai thay đổi/kết thúc.
