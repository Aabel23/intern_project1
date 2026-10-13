# M-01 · Menu, bật/tắt món và sửa giá

**Planner draft 13/10/2026.** User đã chốt tách lệnh bật/tắt khỏi sửa giá; Owner/Manager sửa giá chỉ qua cloud. User cũng duyệt gói gồm món+công thức+danh mục tra cứu, giá nguyên đồng, ảnh tải riêng theo hash, CRC trên byte JSON canonical nội dung, tách phiên bản nội dung khỏi trạng thái bán/tồn, trần 256 KB trên gói nén trước base64. Cần phiếu wire/vector cụ thể trước coder; quyền Manager còn phụ thuộc share/vai chưa có code đầy đủ.

## Bằng chứng nền

- Máy: `version1.1/machine/menu_sync/machine_menu_sync.py` đang dùng một `cap_nhat_menu` cho `available` và `price`; `machine_menu_pack.py` tính CRC32 của danh sách drink. `machine_menu_store.py` đọc MySQL, chưa có công thức trong gói.
- Server: `server/src/relay.py` whitelist `cap_nhat_menu` và kiểm `owner_of`; chưa có quyền theo vai/instruction.
- App: `flutter_app/lib/feature/machine_menu/ui/machine_menu_tab.dart` dùng lệnh gộp cho công tắc, chưa có sửa giá. `machine_controller.dart` chưa kiểm CRC/phiên bản gói.
- Hợp đồng thiết kế: `documentation/architect/features/menu.html` yêu cầu gói công thức, giá nguyên đơn vị đồng, 256 KB, tách lệnh vận hành và sửa giá.

## Phụ thuộc và thứ tự phiếu coder

1. **M-01A · Hợp đồng đọc menu:** viết biểu diễn byte canonical cho CRC, nội dung `recipes/lookups`, trần 256 KB trên gói nén trước base64, phiên bản nội dung/trạng thái, ý nghĩa `up_to_date/conflict`. Viết vector gói hợp lệ/hỏng để máy và app cùng kiểm. Đây là bước Planner trước coder.
2. **M-01B · Đọc menu an toàn:** sau M-01A, máy dựng gói theo hợp đồng; app kiểm `v`, `menu_version`, CRC, kích thước, trường bắt buộc và cache đúng máy. Server relay cùng route hiện có và chỉ giữ gói RAM nếu hợp đồng yêu cầu. Test gói lỗi, đổi máy và dữ liệu thật MySQL. Android thật để cổng phát hành.
3. **M-01C · Bật/tắt món:** lệnh riêng, dữ liệu chỉ `drink_id` và `available` cùng phiên bản phù hợp; máy kiểm, ghi một transaction, chống lặp theo request ID và trả trạng thái đọc lại; server/app cập nhật whitelist và hiển thị. Quyền vận hành Owner/Manager/Employee theo ma trận đã duyệt, cả cloud/LAN/Bluetooth ở các đường được phép.
4. **S-roles · Share/vai:** hoàn thiện quyền Owner/Manager/Employee theo máy ở app, server và máy, trước M-01D. Server phải kiểm quyền theo instruction; chỉ kiểm `owner_of` hiện tại không đáp ứng Manager.
5. **M-01D · Sửa giá:** lệnh riêng qua cloud, giá nguyên đồng không âm; Owner/Manager, Employee bị chặn. Máy kiểm `menu_version`, ghi một lần, đọc lại; app có nhập/duyệt thay đổi và xử lý conflict. Đường LAN/Bluetooth tại chỗ từ chối lệnh giá.

## Ca review bắt buộc

Menu 0 món, món đổi/xóa trong lúc app mở, packet bị cắt/CRC sai/quá trần, giá lẻ hoặc âm, lệnh ghi gửi lại sau timeout, hai điện thoại đổi giá cùng phiên bản, Manager/Employee/Owner và quyền bị thu hồi, đổi máy khi response cũ về. Biên bản phải phân biệt test tự động, Pi/LAN và Android thật; không nhận module chỉ dựa trên widget demo.

## Quyết định còn mở

- Cách biểu diễn byte CRC chính xác và vector; user đã chốt nội dung/phiên bản về mặt ngữ nghĩa.
- Recipe/lookups lấy bảng nào và định dạng trường cụ thể; ảnh dùng hash riêng và trần 256 KB áp gói nén trước base64 đã chốt.
- Ma trận quyền tại chỗ và cách thu hồi khi máy offline trong module share/vai.

Những điểm trên thuộc thiết kế đã ghi ở tài liệu menu nhưng còn “tạm chốt” hoặc thiếu vector. Khi phát hiện khác code, đưa user chọn trước khi sửa.
