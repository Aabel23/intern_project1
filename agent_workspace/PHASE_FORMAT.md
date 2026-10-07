# Tài liệu tóm tắt và kế hoạch nội bộ

## Quy ước hiện hành — 06/10/2026

Người dùng chỉ cần vài file HTML để đọc tóm tắt hệ thống. Quy ước này thay
hướng dẫn trước đây yêu cầu mỗi chuyên đề, phase lớn và phase con có trang HTML.
Độ chi tiết của kế hoạch giữ trong Markdown, không quyết định số trang người dùng đọc.

## HTML cho người dùng

- Điểm vào: `tasks/<tên-task>/index.html`. Mặc định một trang; chỉ thêm 1–2 trang
  theo nội dung khi tổng quan không đủ để hiểu kiến trúc/luồng hoặc quyết định chính.
- Với middleware, bộ đọc gồm `index.html`, `architecture.html`, `packet-security.html`.
- Viết tiếng Việt có dấu; ưu tiên “Bạn cần biết”, thành phần và luồng hoạt động/dữ
  liệu, ranh giới trách nhiệm, đề xuất/hiện trạng và vấn đề cần chốt. Bỏ phần không áp dụng.
- HTML kiến trúc bao phủ feature thực tế và từng luồng: cửa vào, dữ liệu, kiểm tra,
  kho lưu, tác động, kết quả và nhánh lỗi/timeout. Dùng mục lục, neo và phần mở rộng
  để giữ vài trang nhưng vẫn đủ chi tiết cho người dùng sửa thiết kế.
- Trang index.html có sơ đồ tiến độ plan và trạng thái theo từng bước, kèm chú thích
  lỗi. Hồ sơ phân công chi tiết, nguồn file:dòng dày đặc, ma trận test và nhật ký
  bàn giao vẫn trong Markdown. Không tạo trang riêng theo mỗi phase/phase con/task.
- Luồng hệ thống dùng sơ đồ khối SVG/HTML có nhãn, mũi tên, dữ liệu truyền và chú
  giải hiện trạng/đề xuất. HTML mở offline, đọc trên màn nhỏ và in được.
- Chỉ ghi kết quả đã có bằng chứng; nghiên cứu đọc mã khác kết quả test. Đề xuất
  chưa thực hiện phải ghi rõ, không bịa lịch, số đo, ngưỡng tải hoặc trạng thái đạt.
- `../phase-00.pdf` là mẫu trình bày khi có file. Nếu không có, ghi giới hạn đối chiếu;
  không chép công nghệ hoặc số liệu của dự án khác. Review tham chiếu tại
  `../version1.0/docs/review_version1_0.html` phải được đối chiếu với mã hiện tại.

## Chuẩn chất lượng báo cáo — 07/10/2026

Mọi báo cáo thiết kế HTML trong quy trình team lấy `FexMix_Munual.html` tại gốc
repo làm mẫu chính về bố cục và cách dẫn dắt: tổng quan khối lớn trước → mục lục
trái/nội dung phải → từng thành phần theo Làm gì, sơ đồ, nguồn, bước/tham số.
`FlexMix_System_Manual.html` là mẫu bổ sung. Phải đọc mẫu trực tiếp trước khi dựng;
không chỉ yêu cầu chung “giống manual” hoặc bắt đầu bằng pipeline kỹ thuật dài.

Khuôn thành phần, nguyên tắc diễn đạt và cổng chất lượng dùng chung nằm tại
[Chuẩn báo cáo theo manual](agents/architect.md#chuẩn-báo-cáo-theo-manual).
Operator/người dựng áp dụng; reviewer kiểm độc lập nội dung và bằng chứng render
trên desktop, màn nhỏ, bản in cùng các điều khiển/offline trước khi giao. Architect
chỉ bàn giao nội dung và đặc tả, không thay vai ghi file hoặc tự nhận đã kiểm UI.
Báo cáo Markdown nội bộ giữ nghiên cứu/điều phối/bằng chứng; không bắt buộc dựng
HTML riêng cho báo cáo nội bộ hoặc phase. Phạm vi thiếu phép kiểm phải ghi rõ.

Ưu tiên nhiều sơ đồ nhỏ phân rã hệ thống → nhóm chức năng → luồng con → nhánh
cần kiểm riêng, với neo cha/con và mapping khối tới mã, trách nhiệm, hợp đồng và
phụ thuộc. Chia đủ để mỗi luồng đơn giản, chính xác và truy được chủ sở hữu dữ
liệu/tác động; giữ vài trang HTML và không ép mỗi khối thành module/file. Chi tiết
ở mục “Phân rã hệ thống thành các luồng con” trong chuẩn architect. Kết luận code
sạch, ít chồng chéo hoặc dễ thay thế cần đối chiếu mã/caller và bằng chứng kiểm;
sơ đồ thiết kế chỉ nêu mục tiêu và điều kiện nghiệm thu cho phần chưa triển khai.

## Tiêu chí sơ đồ trực quan

- Tham chiếu hình thức: `../FexMix_Munual.html` và `../FlexMix_System_Manual.html`,
  cùng ảnh mẫu người dùng cung cấp. Chỉ mượn hình thức, không chép nghiệp vụ.
- Nền giấy ấm/than chì theo chế độ sáng/tối; app xanh lam, xử lý cam san hô,
  thiết bị tím, quyết định vàng, kết quả thành công xanh lá. Không chỉ dùng màu:
  có nhãn và chú giải cho từng loại khối.
- Xử lý dùng chữ nhật, quyết định dùng hình thoi, lưu trữ dùng hình trụ;
  RAM có nét đứt và ghi rõ không bền. Mũi tên có chiều, nhánh quyết định có nhãn.
- Mỗi sơ đồ ghi hiện trạng/đề xuất, nguồn đối chiếu và mô tả đọc được;
  tránh chữ đè đường nối hoặc nhãn bị cắt. Tách tổng quan và luồng xử lý khi cần.
- Có nút “Phóng to” và “Mã nguồn”, hoạt động offline; hỗ trợ Escape và trả focus.
  SVG gốc đọc được khi tắt JavaScript. Trên điện thoại cho kéo ngang kèm gợi ý;
  bản in giữ đủ sơ đồ và ẩn điều khiển. Kiểm bằng trình duyệt và bản in thực tế.

## Markdown cho agent

- `TASK.md`: yêu cầu gốc, phạm vi, trạng thái, quyết định, mục lục kế hoạch nội bộ
  và bằng chứng mới. Dùng `tasks/TEMPLATE.md`.
- `internal/`: nghiên cứu, hợp đồng, thiết kế chi tiết, lộ trình và các phase.
  Ví dụ `internal/phases/<giai-doan>/index.md` và `<phase-con>.md`.
- Không bắt buộc số file hoặc số phase con; chỉ tách khi đủ trách nhiệm rõ ràng.
- Kế hoạch hai cấp vẫn gồm phase lớn của team và phase con có đầu vào/đầu ra riêng.
  Mỗi cấp ghi mục tiêu, phụ thuộc, phân công/bàn giao, bằng chứng, acceptance và
  điều kiện đi tiếp/quay lui. Task/bước nằm trong phase con khi cần phân cấp.
- Phase con ghi nghiên cứu/nguồn file:dòng, giả thuyết, định hướng/lý do, yêu cầu,
  file/caller, thứ tự bước, nhánh lỗi/timeout/hủy, phép kiểm và đầu ra có thể kiểm.
- Sơ đồ nội bộ có thể là Mermaid hoặc nguồn SVG trong Markdown; chỉ sơ đồ cần
  người dùng hiểu mới đưa vào HTML tóm tắt. Không sinh HTML để lưu nguồn sơ đồ.
- Theo quy trình người dùng đã chốt: hai architect phản biện → thiết kế HTML được
  người dùng chốt → planner → một coder → reviewer độc lập → operator cập nhật ✓/✗.
  Không lập plan triển khai trước cổng chốt thiết kế. Tester/security tham gia khi cần.
- Test/harness phải có trước cổng cần nó; chỉ mở việc phụ thuộc khi đầu vào đã có
  bằng chứng. Phase mở rộng chỉ kích hoạt theo yêu cầu hoặc số đo; không tự đổi
  kiến trúc đã chốt. Thay API phải xét đồng thời server, app, máy và test.
- Khi kiểm: ghi lệnh, môi trường, output/exit code, tiêu chí đạt/chưa đạt và giới
  hạn. Với flow nhiều bước, giữ số mẫu/lỗi, timing từng khối và tổng flow, p50/p95,
  log và so sánh trước/sau nếu có sửa trong hồ sơ nội bộ.
- Khi có thay đổi đáng kể cho người dùng, cập nhật tóm tắt HTML tương ứng; không
  xuất thêm HTML chỉ để phản chiếu mọi cập nhật của hồ sơ agent.

## Plan và sơ đồ theo dõi

- Mỗi bước có ID ổn định, mục tiêu duy nhất, input/output, phụ thuộc, file/caller,
  vai bàn giao, tiêu chí kiểm và cách quay lui. Chia nhỏ theo đầu ra nghiệm thu,
  không ép mỗi file/hàm thành một phase. Kế hoạch phải phù hợp thiết kế đã chốt.
- Plan nội bộ là nguồn các bước; operator cập nhật sơ đồ HTML tại index.html bằng
  bằng chứng sau mỗi lượt. Dùng chữ/ký hiệu cùng màu: ○ chưa làm, → đang làm/review,
  ✓ đạt, ✗ chưa đạt/lỗi kèm nguyên nhân và bước sửa, ⏸ chờ phụ thuộc hoặc chờ chốt.
- ✓ cần reviewer và kiểm phù hợp đã đạt. Không biến checkbox tự tick hay dữ liệu
  localStorage thành nghiệm thu; không tô xanh bước chưa chạy. Lỗi đã sửa giữ lịch
  sử trong Markdown. Bước phụ thuộc không đi tiếp nếu bước trước chưa đạt.
- Khi thiết kế đang chờ người dùng, chỉ hiện sơ đồ quy trình và các cổng chờ;
  không tự dựng phase thực thi rồi báo đã chốt. Cập nhật thành plan cụ thể sau chốt.
