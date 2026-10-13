# Lộ trình phạm vi khách đầu · bản đề xuất 13/10/2026

**Trạng thái: chờ chủ dự án duyệt thiết kế.** Tài liệu này cập nhật phần còn thiếu của roadmap 44 bước sau khi phạm vi khách đầu được mở rộng. Giữ các cổng G0–G4, nhưng không coi tỷ lệ 44 bước cũ là tỷ lệ hoàn thành phạm vi mới. Kiểm thử Android thật đặt ở cổng trước phát hành theo yêu cầu user; test tự động và kiểm trên server/máy vẫn làm trong từng module.

## Phần đã được quyết

- Khách đầu dùng đăng ký/đăng nhập, nhận/chia sẻ máy, đọc trạng thái và dữ liệu máy, menu, sửa giá, kho, đơn hàng, báo cáo và OTA.
- Bản đầu app và máy tới server bằng HTTP trên LAN; lớp phong bì, chữ ký, phiên và quyền bên trong vẫn giữ. Sau này đổi endpoint sang HTTPS Internet, cùng routing và ngữ nghĩa. Chuyển endpoint cần cập nhật cấu hình máy và bản build app.
- Transport LAN/HTTP đã code ở `2c4ec6b`, hướng dẫn ở `aae08e8`. Test tự động đạt theo `execution-dispatch-2026-10-13.md`; chưa nghiệm thu thiết bị thật.

## Thứ tự công việc và cổng

| Lượt | Đầu ra phải có trước lượt kế | Bằng chứng đóng |
|---|---|---|
| G0 | Khóa phạm vi cụ thể, kênh phát app, máy đích, người ký phát hành và hỗ trợ | Phiếu `g0-first-customer-decision.md` được duyệt, việc chưa rõ có người và hạn xử lý |
| Nền kết nối | Server LAN/HTTP, trust, tài khoản/claim/relay, máy tự chạy; sửa phiếu I-01 theo LAN | Test máy tính, server LAN và Pi; Android thật tại cổng phát hành |
| Menu đọc và bật/tắt | Khóa hợp đồng menu, cache và lệnh vận hành tách riêng; sau đó máy → app → relay | Gói menu có kiểm phiên bản/toàn vẹn; bật/tắt đọc lại đúng, sai quyền bị từ chối |
| Share và vai | Hoàn thiện Owner/Manager/Employee và kiểm quyền theo instruction ở server/máy/app | Hai tài khoản khác vai chỉ thực hiện đúng lệnh của vai mình |
| Sửa giá | Sau vai/quyền, khóa lệnh riêng chỉ qua cloud cho Owner/Manager | Giá nguyên đồng đọc lại đúng, Employee và đường tại chỗ bị từ chối |
| Kho | Khóa nạp gram, kiểm đếm, đơn vị, quyền và chống lặp; sau đó máy → app | Tồn trước/sau và ledger khớp, lệnh lặp không nạp hai lần, lỗi được hiển thị thật |
| Đơn hàng | Khóa nghĩa của “đơn” và vòng đời; máy giữ dữ liệu, app đọc và thao tác được duyệt | Ticket/đơn trên app khớp máy; không hiển thị tiền, số ly, thanh toán nếu chưa có dữ liệu thật |
| Báo cáo | Khóa chỉ số và nguồn; xây từ đơn/kho/sự kiện đã có thật | Tổng hợp đối chiếu dữ liệu gốc, rõ khoảng thời gian và quyền xem |
| OTA | Khóa nơi phát bản, cách tải gói, chữ ký, điều kiện máy rảnh và rollback; máy kiểm trước khi cài | Gói sai bị từ chối; nâng cấp/khôi phục trên thiết bị thật, không ngắt pha nguy hiểm |
| G2 | Share QR/BLE, quyền và chuyển cloud → LAN → Bluetooth cùng các module trên | Review toàn hệ và test tự động; biên bản Pi/LAN, Android được gom vào cổng phát hành |
| G3 | Server/DB/SMTP, backup-restore, release ký số, Android và Pi thật, diễn tập | Go/no-go có người ký, bản build và runbook cố định |
| G4 | Lắp khách, khách tự thực hiện luồng, quan sát sau giao | Biên bản khách và nhật ký hỗ trợ theo thời gian đã chốt |

Các nhánh menu, kho và OTA có thể được **thiết kế** song song. Coder chỉ nhận từng phiếu khi hợp đồng tương ứng được duyệt; server relay và hợp đồng chung có một người sửa mỗi lượt. Sửa giá cho Manager phụ thuộc share/vai thật vì relay hiện chỉ kiểm Owner; không gắn nhãn đạt cho giá trước khi quyền theo vai hoạt động. Báo cáo phụ thuộc dữ liệu đơn hàng và các sự kiện được chọn. Bản phát hành đòi tất cả các module giao khách, không lấy trạng thái G2 cũ làm bằng chứng đủ phạm vi mới.

## Kết quả kiểm code và quyết định cần khóa

### Menu và giá

Máy đã có `nhan_menu` và `cap_nhat_menu` cho giá/trạng thái tại `version1.1/machine/menu_sync/`. App chỉ hiển thị menu và bật/tắt tại `flutter_app/lib/feature/machine_menu/`; decoder hiện chỉ kiểm hình dạng gói, chưa kiểm CRC/phiên bản. `documentation/architect/features/menu.html` mô tả lệnh bật/tắt riêng. **User chốt 13/10/2026:** tách lệnh bật/tắt khỏi sửa giá; Owner/Manager sửa giá chỉ qua cloud. Giá dùng số nguyên đồng và gói có công thức, trần 256 KB theo quyết định đã lưu. **Còn phải khóa ở hợp đồng module:** nội dung CRC/version và ảnh; quyền Manager phụ thuộc module share/vai vì relay/app hiện chỉ có Owner. Không thêm UI sửa giá theo lệnh gộp hiện có.

### Kho

Máy có `nhan_kho`, `nap_kho`; app có đọc tồn và nạp đầy/tất cả. Thiết kế kho yêu cầu nạp gram, kiểm đếm và ledger actor/command ID, trong khi schema hiện chưa có ledger. **Cần chốt:** thao tác khách cần, đơn vị và sức chứa bình, quyền Owner/Manager, quy tắc trừ tồn/kiểm đếm và chống lặp. Chưa coi nút “Nạp đầy” là hoàn thành kho.

### Đơn hàng và báo cáo

Máy có `order_ticket` QR và vòng đời `unused/in_progress/used/expired/noqr_err`; tab đơn hàng app là demo, server chưa có relay đọc đơn. Bảng ticket có snapshot tên/giá lúc bán, nhưng `recent()` hiện lấy tên từ bảng drink hiện thời. **Cần chốt:** khách muốn xem ticket QR hay đơn bán có hủy/hoàn, số ly, thanh toán; trạng thái và quyền thao tác; chỉ số báo cáo, khoảng thời gian và nguồn dữ liệu. Lát read-only đầu tiên sau quyết định là relay danh sách ticket giới hạn, dùng tên/giá snapshot và hiển thị trạng thái thật; không đưa số liệu demo vào báo cáo.

### OTA

Máy/server có hằng route OTA nhưng server chưa dispatch. `documentation/architect/features/software-update.html` yêu cầu tải gói qua TLS, xung đột với transport HTTP LAN đã chọn. **Cần chốt:** gói tải bằng đường nào trong LAN, chữ ký/hash và khóa phát bản, điều kiện máy rảnh, trình tự cài/rollback theo layout Pi. Lát đầu tiên là manifest và kiểm chữ ký gói trước khi cho cài; không kích hoạt OTA chỉ vì route đã tồn tại.

### Transport và phát hành

Review độc lập không thấy đường vòng rõ ràng bỏ qua phong bì/kiểm quyền trong LAN HTTP, nhưng `usesCleartextTraffic` Android hiện bật toàn app. Trước bản Internet cần giới hạn lại chính sách mạng và chuyển URL/trust đồng bộ. Chưa có test Android/Pi thật, MySQL fixture, SMTP/OTP thật, bản APK ký số và người vận hành được xác nhận; các mục này vẫn chặn phát hành.

## Quy tắc thực thi

Mỗi module: quyết định sản phẩm → hợp đồng và ví dụ → phiếu file/hàm/test → coder → review nhỏ → kiểm tự động → review module → kiểm thiết bị thật tại cổng đã định. Phát hiện lệch thiết kế được ghi ở đây và đưa chủ dự án chọn trước khi sửa code. Các thay đổi tài liệu cũ trong working tree không được tự gộp vào commit của module.
