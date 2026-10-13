# O-01 · Danh sách vé QR trên app

Trạng thái: **đề xuất triển khai, chưa duyệt hợp đồng chi tiết**. Khách đầu tiên chỉ xem các vé QR đã có trong `order_ticket` của máy; không tạo, thanh toán, hủy, hoàn tiền hoặc điều khiển pha từ app. Mỗi vé hiện tương ứng **một món**, không có số lượng ly hay phương thức thanh toán trong bảng.

## Bằng chứng mã hiện tại

- `version1.1/database/services/order_ticket.py`: `issue()` lưu `drink_name` và `price` cùng lúc phát vé; trạng thái thật là `unused`, `in_progress`, `used`, `expired`, `noqr_err`. `claim()` mới đánh dấu quá hạn, nên một vé cũ chưa quét có thể vẫn là `unused` trong DB. `recent()` hiện join tên món từ bảng `drink` và không đọc snapshot giá: không dùng nguyên hàm này cho app.
- `version1.1/database/schema/schema.sql`: `order_ticket` có `serial`, snapshot `drink_name`/`price` (nullable vì hàng cũ), `status`, `created_at`, `scanned_at`, `completed_at`; không có quantity/payment. `serial` là mã nội bộ, không nằm trên payload QR v1.4.
- `flutter_app/lib/feature/orders/ui/orders_tab.dart` đang hiện dữ liệu giả từ `demo_orders.dart`, gồm mã `#FM`, nhiều ly, thanh toán và nhãn `cancelled` không tương ứng DB. Tab hiện chưa nhận `MachineController`.
- `server/src/relay.py` chỉ cho năm instruction hiện có và kiểm owner máy; `machine/main.py` chỉ đăng ký lệnh menu/kho/trạng thái. Chưa có đường đọc vé QR qua relay.

## Lát cắt chỉ đọc

1. App chọn máy qua `MachineController`, gọi relay cloud/LAN đang dùng với instruction đề xuất `nhan_ve_qr` và `{ "before_serial": null, "limit": 20 }`. Trên làm mới, bỏ cursor và tải trang đầu. Khi đổi máy, xóa ngay danh sách/cursor máy cũ và bỏ kết quả cũ về trễ. Không mở quyền xem vé qua Bluetooth trong lát cắt này.
2. Server thêm instruction vào allowlist relay; xác thực session và **quyền xem máy** trước khi chuyển lệnh, kiểm lại quyền trước khi trả. Bản server hiện chỉ có owner, nên lát cắt đầu cho owner; khi module share machine hoàn tất, áp chính sách quyền xem của vai được chốt, không suy ra quyền từ UI. Server không query/biến đổi vé, nhưng relay hiện nhìn thấy và giữ kết quả plaintext trong RAM ngắn hạn; không hứa riêng tư đầu cuối máy→app.
3. Máy đọc các cột cần thiết của `order_ticket` trực tiếp, không join `drink`, không `SELECT *`. Query keyset: `WHERE (%s IS NULL OR serial < %s) ORDER BY serial DESC LIMIT %s` với `validated_limit + 1` để biết còn trang; hoặc hai nhánh SQL tương đương khi cursor null. Giới hạn đề xuất **20 vé/trang, max 20**, cần đo worst-case tên Unicode + phong bì HPKE dưới giới hạn HTTP 65536 byte, nếu quá thì hạ max hoặc đổi trần có chọn lọc. `before_serial` là số nguyên dương hoặc null. Mỗi lời gọi đọc trạng thái hiện thời trong một truy vấn; trạng thái có thể đổi giữa hai trang, nhưng serial không đổi và không lặp hàng do phân trang keyset.
4. Trả `serial`, `drink_name` snapshot, `price_vnd` snapshot, `status` nguyên giá trị DB, `created_at`, `scanned_at`, `completed_at`. Dùng `next_before_serial` bằng serial cuối trang khi còn dữ liệu, ngược lại null. Không trả `payload`, `payload_hash`, ghi chú khách, và không suy ra thanh toán/số ly/doanh thu từ vé.
5. App hiển thị `Vé #<serial>`, tên/giá tại lúc phát vé và nhãn trạng thái đúng. `unused` = "Chưa quét" (có thể đã quá hạn nhưng chưa có lượt quét); `in_progress` = "Đang pha"; `used` = "Đã pha"; `expired` = "Hết hạn"; `noqr_err` = "Pha lỗi, không có QR". Không gộp `noqr_err` thành "Đã hủy". Hàng snapshot null hiển thị "Tên/giá chưa được lưu"; không lấy giá/tên hiện tại trong `drink` làm dữ liệu lịch sử.

Đề xuất kết quả máy:

```json
{
  "tickets": [
    {
      "serial": 132,
      "drink_name": "Trà đào",
      "price_vnd": 35000,
      "status": "used",
      "created_at": "2026-10-13T10:42:00+07:00",
      "scanned_at": "2026-10-13T10:43:00+07:00",
      "completed_at": "2026-10-13T10:45:00+07:00"
    }
  ],
  "next_before_serial": null
}
```

`next_before_serial` chỉ bằng serial cuối **trong hàng đã trả** nếu máy thấy hàng thứ `limit+1`; ví dụ một hàng trên không còn trang nên là null. Không thêm tổng số vì sẽ cần một truy vấn và dễ lệch với trạng thái live. Implementation phải đo kích thước thực tế kể cả phong bì mã hóa/base64.

## Quyền và lỗi

- App yêu cầu đăng nhập; server kiểm quyền theo `machine_id`, không chấp nhận tham số user/owner do app gửi. Nếu mất quyền khi đang chờ máy, không trả dữ liệu. Máy không nhận lệnh lọc theo user vì DB ticket không có owner.
- Máy từ chối cursor/limit sai (`INVALID_DATA`), lỗi đọc DB trả `MACHINE_READ_FAILED`, máy offline hoặc timeout theo lỗi relay hiện có. App hiển thị lỗi và giữ danh sách cũ của **cùng máy** với dấu thời gian cũ; đổi máy phải xóa dữ liệu cũ.
- Không đọc hoặc gửi payload QR trong danh sách. Serial là mã nội bộ để tra vé và hỗ trợ, không phải mã quét.

## Kiểm chứng bắt buộc khi coder triển khai

1. Fixture DB có 21+ vé; trang một 20 hàng, trang hai phần còn lại, không trùng serial; cursor 0, âm, bool, string và limit vượt trần bị từ chối. Vé mới phát giữa hai trang không làm lặp/mất các serial cũ.
2. Đổi tên/giá món và xóa mềm món sau khi phát vé: app vẫn nhận `order_ticket.drink_name`/`price`; hàng lịch sử null hiển thị thiếu snapshot, không lấy giá hiện hành.
3. Năm trạng thái DB được truyền/hiện nguyên nghĩa. Vé `unused` quá tuổi nhưng chưa quét vẫn là `unused`; test không tự biến thành `expired` trên đường chỉ đọc. `release()` có thể đưa `in_progress` về `unused` khi trang sau tải lại.
4. Server từ chối tài khoản không có quyền và thu hồi quyền trong lúc relay chờ. App đổi máy khi request cũ còn chạy không được trộn vé hai máy. Dữ liệu giả bị gỡ khỏi UI khách.
5. Kết quả tối đa 20 hàng nằm trong giới hạn envelope/HTTP thực tế, gồm tên Unicode 100 ký tự và timestamp; nếu không, điều chỉnh max/trần trước khi nhận phiếu. Test đường máy → relay → app bằng dữ liệu thật hoặc fixture tương ứng; xác nhận payload/hash/note vắng ở response, không chỉ UI. `OrdersTab` phải nhận `MachineController` từ dashboard và gắn cursor/generation với machine ID.

## Quyết định còn cần chốt

- **Quyền theo vai sau share**: owner-only cho lát cắt đầu; cần chốt vai nào được xem lịch sử vé khi quyền share hoàn tất.
- **Múi giờ**: cột MySQL là `DATETIME` không kèm timezone. Đề xuất serialize theo timezone cấu hình máy; cần chốt timezone máy và cách xử lý dữ liệu cũ trước khi ghi dấu `+07:00` như ví dụ.
- **Giá cũ có phần lẻ**: `price` là `DECIMAL(10,2)`, nullable. Giá VND mới cần nguyên; nếu có hàng cũ chứa phần lẻ, cần chốt cách hiển thị thay vì làm tròn hoặc thay bằng giá hiện tại.
- **Phạm vi hiển thị**: đề xuất tất cả vé máy theo serial mới nhất, không lọc ngày/trạng thái ở server; lọc UI chỉ trên trang đã tải dễ gây hiểu nhầm. Cần chốt có cần bộ lọc server hoặc phạm vi thời gian cho khách đầu.
- **Tên màn hình**: nên ghi “Vé QR” thay “Đơn hàng” để không hứa hẹn thanh toán, nhiều ly và hủy đơn chưa có trong dữ liệu.
