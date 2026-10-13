# G0 · Quyết định bản giao khách đầu tiên

**Bản nháp để user duyệt · 13/10/2026.** Nguồn: `production-roadmap-report.html` Phase 0, `mvp-roadmap.html` Mốc 1–2 đã duyệt, và các quyết định hệ IoT v1.1 đã xác nhận. Yêu cầu hiện tại của user mở rộng phạm vi khách đầu và đổi đường kết nối. Bản này không tự duyệt G0 và không phát sinh phiếu coder.

## 0.1 · Khách đầu tiên dùng được gì

**Đã chốt trong Mốc 1–2:** người dùng tự đăng ký email/OTP, đăng nhập, nhận máy bằng mã niêm phong, hỏi trạng thái trực tiếp; menu thật từ máy; tắt/bật món và đọc lại; quyền theo từng máy; chia sẻ qua QR và BLE; app tự đi cloud → LAN → Bluetooth, đường tại chỗ chỉ cho việc vận hành được phép. Máy vẫn pha món tại chỗ khi mất Internet.

**User bổ sung 13/10/2026:** khách đầu tiên dùng mọi chức năng đã bàn. Ngoài Mốc 2, user chọn thêm **sửa menu/giá, kho, đơn hàng, OTA và báo cáo**. Đăng ký/đăng nhập, nhận và chia sẻ máy, đọc dữ liệu từ máy là các luồng user nêu đích danh. Đây là phạm vi giao khách mới; các phase sau G0 trong roadmap 44 bước hiện chưa bao trùm đủ các module này và phải được lập lại trước khi phân công coder.

**Cần đặc tả tiếp:** ca sử dụng, quyền và tiêu chí đạt cho năm nhóm mới; luồng pha món và an toàn phần cứng trên máy; danh sách món/thiết bị để nghiệm thu. Không suy ra rằng code hoặc lộ trình hiện tại đã hoàn thành các nhóm mới.

**Bằng chứng đóng bước:** danh sách ca sử dụng và ngoài phạm vi của bản giao đầu được user duyệt, gồm cả năm nhóm mới.

## 0.2 · Đường khách tới server

**User đổi ngày 13/10/2026:** bản đầu kết nối qua **LAN bằng HTTP**. Về sau khi đưa lên Internet dùng HTTPS và chuyển điểm kết nối; giữ cùng routing và logic sản phẩm. **Giữ lớp mã hóa và kiểm quyền bên trong** đã chốt. Quyết định mới này thay giả định phải có HTTPS Internet ở bản giao đầu. Tailscale Serve hiện chỉ là đường thử trong tailnet.

**Luồng G0:** điện thoại và máy của khách → LAN cửa hàng → server truy cập được trong LAN. Khi triển khai Internet về sau, điện thoại và máy → HTTPS → server theo cùng routing và hợp đồng. Tài khoản/OTP vẫn cần đường gửi email đi ra ngoài; điều này được kiểm ở môi trường thử và không biến đường app → server thành Internet.

**Bằng chứng đóng bước:** sơ đồ đường LAN/HTTP và đường Internet/HTTPS về sau được user duyệt; địa chỉ LAN, vị trí server và người vận hành được ghi khi chọn địa điểm khách.

## 0.3 · Kênh app và thiết bị đích

**Đã chốt:** bản đầu chỉ Android; nghiệm thu phải chạy trên Android và Raspberry Pi thật.

**Đề xuất để user duyệt:** bản pilot khách đầu phát APK release ký số trực tiếp, ghi phiên bản và đường cập nhật; Google Play quyết ở lần mở rộng sau. Dùng Raspberry Pi 5 làm thiết bị tham chiếu vì bộ cài hiện nhận diện Pi 5; dùng Samsung SM-A256E làm Android tham chiếu vì repo từng ghi E2E trên máy đó. Đây chỉ là thiết bị tham chiếu, không khẳng định thiết bị khách sẽ giống.

**Cần user chốt:** kênh APK trực tiếp hay Google Play; thiết bị tham chiếu trên có dùng được không; model/OS máy khách thực tế, người giữ tem QR/mã niêm phong và checklist pha chế tại chỗ. Nếu khách chưa có thiết bị, ghi rõ là chưa chọn và không dùng thiết bị tham chiếu làm bằng chứng nghiệm thu tại khách. Bằng chứng đóng bước: kênh phát và bộ thiết bị đích được duyệt.

## 0.4 · Tiêu chí go/no-go

**Đề xuất điều kiện chặn giao:** I-01, Mốc 2 và cả năm nhóm bổ sung qua nghiệm thu trên thiết bị thật; không có lỗi làm sai chủ/quyền, lộ bí mật, thành công giả, lặp thao tác ghi, mất dữ liệu không khôi phục được, hoặc máy pha không an toàn; bản release cài được; server và máy khởi động lại được; backup/restore và luồng khách tự dùng đã diễn tập. Lỗi còn lại phải có người nhận và quyết định chấp nhận cụ thể. Chủ dự án duyệt phát hành; một người hỗ trợ được chỉ định trước ngày lắp. Đề xuất quan sát sau lắp 7 ngày với kênh liên lạc trực tiếp do khách và người hỗ trợ thống nhất.

**Cần user chốt:** tên người ký go/no-go, tên người hỗ trợ và kênh báo lỗi; có đồng ý 7 ngày quan sát và các điều kiện chặn trên không. Thời gian 7 ngày là đề xuất, chưa thành cam kết. Bằng chứng đóng bước: bảng tiêu chí và người phụ trách được user duyệt.

## Trạng thái cổng

G0 chỉ được ghi **qua cổng** sau khi phạm vi và đường kết nối mới được user duyệt trong tài liệu, lựa chọn phân phối/thiết bị và go/no-go có người chịu trách nhiệm, bốn bước 0.1–0.4 được kiểm độc lập và ghi `done` vào `roadmap-progress.json`. Các phase sau G0 phải được cập nhật cho đủ năm nhóm chức năng mới và đường LAN/HTTP trước khi phát phiếu coder.

**Thứ tự kiểm theo yêu cầu mới của user:** phần kiểm thử trên điện thoại Android thật để sau; vẫn giữ ca này trước khi phát hành cho khách. Kiểm thử tự động không dùng điện thoại có thể chạy trong lúc chuẩn bị và thực thi từng module. Mốc I-01/G1 cũ phải tách tiêu chí Android thật sang cổng phát hành khi lập lại roadmap.
