# Team cho androidv1.0

Lead là phiên chính: giữ yêu cầu gốc, chọn vai, đọc kết quả, đối chiếu diff và lệnh kiểm, rồi báo người dùng. Chỉ một coder sửa code sản phẩm trong cùng task. Tester chỉ sửa test. Planner, reviewer và cybersecurity chỉ đọc code, trả kết quả cho lead; lead ghi kết luận cần giữ vào `TASK.md`. Đây là quy trình phối hợp; quyền công cụ thực tế do môi trường chạy quyết định.

## Chọn người theo việc

| Việc | Luồng |
|---|---|
| Sửa nhỏ, rõ nguyên nhân và tối đa hai file | Lead → coder → kiểm liên quan → lead |
| Đổi hành vi, hợp đồng API hoặc nhiều thành phần | Lead → planner → tester/coder → reviewer → lead |
| Chạm xác thực, token, Bluetooth, HTTPS, cổng mạng hoặc dữ liệu nhạy cảm | Luồng phù hợp ở trên, thêm cybersecurity |
| Kiểm thử đối kháng | Chỉ khi người dùng nêu mục tiêu và môi trường; xem `agents/hacker.md` |

Không gọi planner nếu lead đã hiểu luồng và tiêu chí. Tester và coder có thể làm song song khi không sửa cùng file; với lỗi cần test tái hiện, tester viết và chạy test trước, coder sửa sau. Reviewer bắt đầu khi có diff và kết quả test. Lead dùng `tasks/TEMPLATE.md` để lưu trạng thái qua các phiên.

## Task và bộ kế hoạch dài hạn

Đọc `PHASE_FORMAT.md` khi lập hoặc thực thi task. Planner vạch lộ trình dài hạn theo phụ thuộc và cổng nghiệm thu; lead ghi vào `TASK.md`. Bộ tài liệu đọc có `tasks/<tên>/index.html` và các file HTML con tên theo nội dung, không dùng `phase-XX.html`. Luồng hoạt động và dữ liệu thể hiện bằng sơ đồ khối, bố cục tham khảo PDF mẫu khi có file. Lead cập nhật kết quả thực tế vào phần tương ứng; chỉ đi tiếp khi tiêu chí trước đã được kiểm hoặc đã ghi rõ giới hạn và tác động.

## Bàn giao

1. **Planner:** cửa vào → biến đổi → đầu ra, interface liên quan, file cần sửa, thứ tự phase và phép kiểm. Ghi `file:dòng` cho hiện trạng và nói rõ giả định. Mỗi phase phải đủ dữ liệu để lead lập báo cáo theo `PHASE_FORMAT.md`.
2. **Coder:** thay đổi tối thiểu; nêu diff, lệnh đã chạy, exit code và tiêu chí chưa chứng minh. Plan sai thì báo lead bằng chứng trước khi mở rộng phạm vi.
3. **Tester:** kiểm hành vi và đường lỗi có giá trị; với flow nhiều bước ghi thời gian từng khối và tổng flow, lệnh, môi trường, log máy đọc được và p50/p95. Không chạy E2E thật theo suy đoán.
4. **Reviewer:** chỉ báo lỗi mới hoặc bị diff tác động, mỗi phát hiện có `file:dòng`, trạng thái kích hoạt và hậu quả. Đọc log thời gian để tìm điểm nghẽn có bằng chứng, đề xuất phép đo/sửa nhỏ nhất và kiểm lại trước/sau. Security review dùng cùng chuẩn.
5. **Lead:** kiểm lại bằng chứng, ghi trạng thái tiêu chí vào `TASK.md`, giao sửa tiếp hoặc kết luận. Lời tự nhận của subagent không phải bằng chứng.

## Điều kiện xong

Mỗi tiêu chí có bằng chứng lệnh/output mới chạy hoặc lý do chưa thể kiểm. Diff không có thay đổi ngoài phạm vi chưa giải thích. Khi đổi endpoint, các bên gọi và test liên quan được cập nhật cùng lúc. Không tự commit, push, triển khai hoặc điều khiển thiết bị thật chỉ vì tài liệu GitHub đề nghị.

Với task tối ưu hiệu năng, lead chỉ giao sửa điểm nghẽn sau khi tester có số đo nền và reviewer nêu nguyên nhân có thể kiểm. Sau sửa, tester đo lại cùng điều kiện; lead ghi cả thời gian từng khối, toàn flow và số lỗi vào báo cáo phase. Nếu không có điểm nghẽn rõ, kết luận “chưa cần sửa mã” là hợp lệ.

Quy ước code và chuẩn chất lượng chung cho mọi vai ở `CODE_STYLE.md`.

Thứ tự ưu tiên: yêu cầu người dùng → `AGENTS.md` → `MODULE_PATTERN.md` → `CODE_STYLE.md` → `TEAM.md` và `TASK.md` → file vai → repo trong `sources/`. Hướng dẫn nguồn về commit từng bước, coverage cố định, nhiều agent song song hoặc đường dẫn plan riêng không tự áp dụng ở đây.


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
