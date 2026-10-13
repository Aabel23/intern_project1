# G0 · Quyết định bản giao khách đầu tiên

**Quyết định G0 đã được user duyệt trong hội thoại ngày 13/10/2026; chi tiết từng module còn chốt ở phiếu riêng.** Nguồn: `production-roadmap-report.html` Phase 0, `mvp-roadmap.html` Mốc 1–2 đã duyệt, và các quyết định hệ IoT v1.1 đã xác nhận. User mở rộng phạm vi khách đầu và đổi đường kết nối.

## 0.1 · Khách đầu tiên dùng được gì

**Đã chốt trong Mốc 1–2:** người dùng tự đăng ký email/OTP, đăng nhập, nhận máy bằng mã niêm phong, hỏi trạng thái trực tiếp; menu thật từ máy; tắt/bật món và đọc lại; quyền theo từng máy; chia sẻ qua QR và BLE; app tự đi cloud → LAN → Bluetooth, đường tại chỗ chỉ cho việc vận hành được phép. Máy vẫn pha món tại chỗ khi mất Internet.

**User bổ sung 13/10/2026:** khách đầu tiên dùng mọi chức năng đã bàn. Ngoài Mốc 2, user chọn thêm **sửa menu/giá, kho, đơn hàng, OTA và báo cáo**. Đăng ký/đăng nhập, nhận và chia sẻ máy, đọc dữ liệu từ máy là các luồng user nêu đích danh. Đây là phạm vi giao khách mới; các phase sau G0 trong roadmap 44 bước hiện chưa bao trùm đủ các module này và phải được lập lại trước khi phân công coder.

**Cần đặc tả tiếp:** ca sử dụng, quyền và tiêu chí đạt cho năm nhóm mới; luồng pha món và an toàn phần cứng trên máy; danh sách món/thiết bị để nghiệm thu. Không suy ra rằng code hoặc lộ trình hiện tại đã hoàn thành các nhóm mới.

**Ca sử dụng đề xuất để duyệt phạm vi (chưa phải nghiệm thu):**

| Người dùng làm gì | Dấu hiệu đạt cần chứng minh | Phần phải quyết trước phiếu coder |
|---|---|---|
| Tạo tài khoản, đăng nhập, nhận máy, chia sẻ máy | Hai tài khoản thật nhìn đúng máy và đúng vai; người lạ không nhận hoặc điều khiển được | Quyền Manager/Employee và thu hồi khi offline |
| Đọc trạng thái, menu và dữ liệu máy | Mỗi lượt hỏi có dữ liệu mới từ đúng máy; menu app khớp dữ liệu MySQL máy | Hợp đồng CRC, công thức/ảnh và cache |
| Bật/tắt món, sửa giá | Lệnh ghi một lần, app đọc lại giá/trạng thái thật, sai quyền bị từ chối | Đã chốt lệnh tách, giá nguyên đồng, Owner/Manager chỉ sửa giá qua cloud; quyền Manager cần module share/vai |
| Xem và cập nhật kho | Tồn trước/sau khớp máy, lệnh lặp không ghi hai lần | User chốt nạp đầy theo bình; cần chốt sức chứa/ánh xạ bình và quyền |
| Xem ticket QR | Danh sách và trạng thái phản ánh ticket thật trên máy | User chốt ticket QR hiện có; không đưa số ly, thanh toán, hủy/hoàn giả vào app |
| Xem báo cáo | Chỉ số đối chiếu được với dữ liệu gốc cùng khoảng thời gian | Chỉ số, nguồn, kỳ và quyền xem |
| Cập nhật phần mềm máy | Bản sai chữ ký/hash bị từ chối; bản đúng chỉ cài khi máy an toàn và có cách quay lui | User chốt tải trong LAN/HTTP với chữ ký/hash; cần chốt điều kiện rảnh/rollback |

Luồng pha chế trên máy và checklist an toàn phần cứng cần chốt theo phần cứng khách. Không đưa màn hình demo, hằng route hoặc test giả lập vào cột “đạt”.

**Bằng chứng đóng bước:** danh sách ca sử dụng và ngoài phạm vi của bản giao đầu được user duyệt, gồm cả năm nhóm mới.

## 0.2 · Đường khách tới server

**User đổi ngày 13/10/2026:** bản đầu kết nối qua **LAN bằng HTTP**. Về sau khi đưa lên Internet dùng HTTPS và chuyển điểm kết nối; giữ cùng routing và logic sản phẩm. **Giữ lớp mã hóa và kiểm quyền bên trong** đã chốt. Quyết định mới này thay giả định phải có HTTPS Internet ở bản giao đầu. Tailscale Serve hiện chỉ là đường thử trong tailnet.

**Luồng G0:** điện thoại và máy của khách → LAN cửa hàng → server truy cập được trong LAN. Khi triển khai Internet về sau, điện thoại và máy → HTTPS → server theo cùng routing và hợp đồng. Tài khoản/OTP vẫn cần đường gửi email đi ra ngoài; điều này được kiểm ở môi trường thử và không biến đường app → server thành Internet.

**Bằng chứng đóng bước:** sơ đồ đường LAN/HTTP và đường Internet/HTTPS về sau được user duyệt; địa chỉ LAN, vị trí server và người vận hành được ghi khi chọn địa điểm khách.

## 0.3 · Kênh app và thiết bị đích

**Đã chốt:** bản đầu chỉ Android; nghiệm thu phải chạy trên Android và Raspberry Pi thật.

**User duyệt 13/10/2026:** bản pilot khách đầu phát APK release ký số trực tiếp, ghi phiên bản và đường cập nhật; Google Play quyết ở lần mở rộng sau. Dùng Raspberry Pi 5 và Samsung SM-A256E làm thiết bị thử tham chiếu. Thiết bị khách thực tế được ghi khi khảo sát; bộ tham chiếu không thay cho nghiệm thu tại khách.

**Còn ghi khi khảo sát:** model/OS máy khách thực tế, người giữ tem QR/mã niêm phong và checklist pha chế tại chỗ. Nếu khách chưa có thiết bị, ghi rõ là chưa chọn và không dùng thiết bị tham chiếu làm bằng chứng nghiệm thu tại khách. Bằng chứng đóng bước G0: kênh phát và bộ thử tham chiếu đã được user duyệt; khảo sát thiết bị khách là điều kiện trước phát hành.

## 0.4 · Tiêu chí go/no-go

**Đề xuất điều kiện chặn giao:** I-01, Mốc 2 và cả năm nhóm bổ sung qua nghiệm thu trên thiết bị thật; không có lỗi làm sai chủ/quyền, lộ bí mật, thành công giả, lặp thao tác ghi, mất dữ liệu không khôi phục được, hoặc máy pha không an toàn; bản release cài được; server và máy khởi động lại được; backup/restore và luồng khách tự dùng đã diễn tập. Lỗi còn lại phải có người nhận và quyết định chấp nhận cụ thể. Chủ dự án duyệt phát hành; một người hỗ trợ được chỉ định trước ngày lắp. Đề xuất quan sát sau lắp 7 ngày với kênh liên lạc trực tiếp do khách và người hỗ trợ thống nhất.

**User duyệt 13/10/2026:** chính user ký go/no-go; chỉ định người hỗ trợ trước ngày lắp; quan sát sau lắp 7 ngày. Người hỗ trợ cụ thể và kênh báo lỗi phải ghi trong hồ sơ triển khai trước ngày lắp; không phát hành khi chưa có. Các điều kiện chặn trong đoạn trên là checklist đề xuất dùng cho quyết định go/no-go, rà lại trên bản release và thiết bị thực tế.

## Trạng thái cổng

**G0 đã qua cổng quyết định ngày 13/10/2026:** user duyệt phạm vi, LAN/HTTP, APK ký số trực tiếp, thiết bị thử tham chiếu, người ký và cửa sổ theo dõi. Chi tiết hợp đồng từng module chốt trước phiếu coder của module đó; model/OS máy khách, người hỗ trợ và kênh báo lỗi chốt trước phát hành. Lộ trình mở rộng ở `first-customer-expanded-roadmap.md` thay phần bao phủ thiếu của roadmap 44 bước cũ. G0 không đồng nghĩa sản phẩm hoặc module đã nghiệm thu.

**Thứ tự kiểm theo yêu cầu mới của user:** phần kiểm thử trên điện thoại Android thật để sau; vẫn giữ ca này trước khi phát hành cho khách. Kiểm thử tự động không dùng điện thoại có thể chạy trong lúc chuẩn bị và thực thi từng module. Mốc I-01/G1 cũ phải tách tiêu chí Android thật sang cổng phát hành khi lập lại roadmap.
