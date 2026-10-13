# R-01 · Nguồn dữ liệu và chỉ số báo cáo đầu tiên

Trạng thái: **đề xuất, cần user duyệt tên chỉ số và phạm vi trước khi viết code**. Phạm vi là báo cáo của **một máy được chọn**, đọc từ MySQL trên máy qua relay hiện có. Server chuyển yêu cầu/kết quả và kiểm quyền; chưa sao chép vé, kho hoặc sự kiện lên server. Khi máy offline, báo cáo mới không lấy được.

## Bằng chứng dữ liệu hiện có

| Nguồn | Có thể khẳng định | Không thể khẳng định |
|---|---|---|
| `version1.1/database/schema/schema.sql` → `order_ticket`; `database/services/order_ticket.py` | Mỗi vé có một `drink_id`, trạng thái thật, lúc phát/quét/kết thúc; `issue()` chụp `drink_name` và `price` tại lúc phát. `status='used'` là ly đã pha xong. | Không có số lượng nhiều ly, phương thức/thời điểm/thực nhận thanh toán, hoàn tiền, chiết khấu hay thuế. Vé phát chưa chắc đã thu tiền. Giá/tên snapshot cũ có thể null. |
| `ingredient` và `database/services/inventory.py` | Mức tồn và `in_stock` **hiện tại**, ngưỡng, dung tích khai báo hoặc mặc định. | Không có bảng sổ biến động kho: không tính được nhập/xuất theo ngày, hao hụt hay mức tồn lịch sử. |
| `error_log` và `database/services/error_log.py` | Số dòng lỗi theo thời gian/severity/bước nếu đọc trực tiếp. | Đây là log kỹ thuật, không phải sổ bán hàng hoặc nhật ký thao tác theo người. Một sự cố có thể tạo nhiều dòng; không gọi số dòng là số lần hỏng máy. |
| `documentation/architect/features/machine-events.html`; server | Tài liệu mô tả event/outbox và bản sao server. | Schema máy chưa có outbox/journal, server chưa nhận/lưu sự kiện. Không lấy số liệu hay lịch sử thao tác từ một bản sao chưa tồn tại. |
| `flutter_app/lib/feature/dashboard/ui/overview_tab.dart` | Thẻ tổng quan đang hiện dấu `—`. | Nhãn “Doanh thu”, “Đơn hàng”, “Giá trị TB” hiện không có nguồn dữ liệu tương ứng. |

`version1.1/store_gui/sync_menu.py` đã dùng `status='used'` và `completed_at` để xếp món bán chạy. Điều này hỗ trợ cách đếm **ly đã pha**, nhưng không chứng minh đã thu tiền. Báo cáo lịch sử phải dùng `order_ticket.drink_name`/`price`, không join giá/tên hiện hành của `drink` vì menu có thể đổi hoặc món bị xóa mềm.

## Chỉ số tối thiểu đề xuất

Chỉ lấy vé có `status='used'` và `completed_at` nằm trong khoảng `[from, to)` theo giờ máy:

1. **Ly đã pha** = `COUNT(*)`. Một vé tương ứng một ly trong schema hiện tại.
2. **Tổng giá trên vé của ly đã pha** = `SUM(order_ticket.price)` cho giá snapshot không null. Ghi rõ “Giá trên vé, chưa đối soát thanh toán”; **không đặt nhãn Doanh thu**. Trả thêm `missing_price_count` để tổng không bị hiểu là đầy đủ khi có hàng cũ thiếu giá.
3. **Theo ngày hoàn tất** = số ly và tổng giá trên vé theo ngày của `completed_at`, dùng cùng điều kiện và cùng múi giờ; tổng các ngày phải bằng số tổng kỳ.

Ngoài kỳ đã chọn, có thể hiển thị riêng **tồn kho hiện tại**: số nguyên liệu `in_stock=false` và thời điểm máy trả lời. Không gộp với đồ thị theo ngày; nó là snapshot, không phải chỉ số lịch sử. Chưa đưa `error_log` vào dashboard đầu tiên vì “số lỗi” dễ bị đọc thành “số lần pha lỗi”.

Ví dụ kết quả **đề xuất** của instruction đọc `nhan_bao_cao` qua relay:

```json
{
  "machine_time":"2026-10-13T15:00:00+07:00",
  "period":{"from":"2026-10-01T00:00:00+07:00","to":"2026-10-14T00:00:00+07:00"},
  "completed_cups":27,
  "ticket_price_sum_vnd":815000,
  "missing_price_count":1,
  "days":[{"date":"2026-10-13","completed_cups":3,"ticket_price_sum_vnd":90000,"missing_price_count":0}],
  "current_out_of_stock_ingredients":2
}
```

Các giá trị trong ví dụ chỉ minh họa cấu trúc. Nếu bất kỳ giá legacy nào có phần lẻ VND, không làm tròn ngầm; cách biểu diễn phải được chốt trước. Số tổng giá không cộng giá của vé `unused`, `in_progress`, `expired`, `noqr_err`; vé phát trong kỳ nhưng hoàn tất ngoài kỳ tính theo ngày hoàn tất. `completed_at` null ở `used` là dữ liệu bất thường: trả riêng số hàng bất thường hoặc lỗi rõ ràng, không lặng lẽ bỏ.

## Luồng đọc, quyền và bộ lọc

- App gửi `machine_id`, `from`, `to` qua `MachineService.ask`; server xác thực và kiểm quyền **đọc báo cáo của máy** trước khi chuyển, kiểm lại trước khi trả. Server hiện chỉ mô hình owner trong relay, nên lát cắt đầu chỉ owner. Không cho app gửi SQL, status hoặc timezone tùy ý để thay nghĩa chỉ số.
- Máy validate khoảng ngày, giới hạn độ dài kỳ và dùng query aggregate trong MySQL. Đề xuất mặc định 7 ngày gần nhất, giới hạn 31 ngày cho một request để tránh truy vấn quá rộng; số ngày này cần chốt. Bộ lọc đầu chỉ có máy và khoảng ngày, không cộng nhiều máy ở app hoặc server.
- Khoảng thời gian là **nửa mở** `[from, to)` để hai ngày/kỳ liền nhau không đếm trùng. `DATETIME` MySQL không chứa múi giờ; phải định nghĩa timezone máy và serialize rõ offset. Ngày trong `days` lấy theo timezone đó, không theo timezone điện thoại.
- Kết quả là snapshot tại lúc máy đọc. App hiển thị `machine_time`/“Cập nhật lúc …”; khi máy offline chỉ có thể hiện cache có ghi “dữ liệu cũ” nếu sau này chốt cache. Không hứa hẹn báo cáo từ Internet khi máy không kết nối LAN/server.
- Độ lớn kết quả bị chặn bởi giới hạn kỳ; máy trả aggregate, không đẩy toàn bộ vé lên server/app để tính. Không đưa QR payload/hash, tên hoặc ghi chú khách vào báo cáo aggregate.

## Kiểm chứng khi triển khai

1. Fixture có vé đủ năm trạng thái, phát hôm trước nhưng hoàn tất hôm sau, đổi giá/tên món sau khi phát, món bị xóa mềm, snapshot price null. Chỉ `used` theo `completed_at` được đếm; tổng giá dùng snapshot và `missing_price_count` đúng.
2. Hai kỳ kề nhau `[a,b)` và `[b,c)` cộng đúng bằng `[a,c)`; ngày hoàn tất khớp tổng kỳ. Kiểm timezone và ngày chuyển tháng/năm bằng timezone đã chốt.
3. Thiếu quyền, quyền bị thu hồi khi relay chờ, máy offline/timeout, `from>=to`, kỳ vượt trần và dữ liệu legacy bất thường đều có kết quả rõ; không lộ dữ liệu máy khác.
4. Số nguyên liệu hết hàng chỉ phản ánh `ingredient.in_stock` hiện tại, đổi sau khi bán không làm đổi số ly/giá lịch sử. Server không tạo bản sao order/event chỉ để chạy report.

## Quyết định cần user chốt

1. Tên hiển thị của tổng giá: đề xuất **“Tổng giá trên vé đã pha”**; có chấp nhận dùng số này trong thẻ Tổng quan thay “Doanh thu” không? Nếu cần doanh thu thực thu, phải có nguồn thanh toán/hoàn tiền được chốt riêng.
2. Chọn timezone chuẩn cho `DATETIME` trên máy và kỳ báo cáo; xử lý khi đồng hồ máy bị lệch.
3. Chọn mặc định 7 ngày và trần 31 ngày, hoặc phạm vi khác; có cần lọc từng món trong bản đầu không?
4. Vai nào được xem báo cáo sau khi share machine hoàn tất; bản đầu đề xuất owner.
5. Giá legacy null hoặc có phần lẻ VND: chỉ rõ hiển thị và có/không cộng vào tổng; không dùng giá món hiện tại để điền lịch sử.
6. Có cần thống kê lỗi kỹ thuật/biến động kho lịch sử ở bản đầu? Nếu có, phải thiết kế nguồn sự kiện/sổ kho thật trước khi hứa chỉ số.
