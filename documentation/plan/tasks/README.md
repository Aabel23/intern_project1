# Phiếu task

Các phiếu ở ngay thư mục này phục vụ lộ trình sau G0. **Chúng chưa tự động là lệnh giao coder**: mỗi module chỉ phát coder khi hợp đồng chi tiết đã chốt và phiếu đủ file, dữ liệu, ca kiểm theo roadmap chính.

| Module | Phiếu hiện hành | Tình trạng |
|---|---|---|
| LAN/HTTP | [L-01](L-01-lan-http-transport.md) | Đã có code; còn review/kiểm thiết bị |
| Menu và giá | [M-01](M-01-menu-and-price.md), [M-01A](M-01A-menu-wire-contract.md) | Hợp đồng wire/vector còn điểm cần chốt |
| Share và quyền | [S-01](S-01-share-roles-dependency.md) | Cần chốt ma trận quyền và thu hồi |
| Kho | [I-01](I-01-refill-by-tank.md) | Cần chốt bình/dung tích/quyền |
| Vé QR | [O-01](O-01-qr-ticket-list.md) | Có lát code; cần review theo phiếu |
| Báo cáo | [R-01](R-01-reporting-source-and-metrics.md) | Có truy vấn trên máy; cần kiểm toàn luồng |
| OTA | [U-01](U-01-ota-lan-signed-package.md) | Cần chốt người ký, điều kiện rảnh, rollback |
| Skeleton server/Pi | [SK-01](SK-01-skeleton-acceptance.md) | Phiếu đã đối chiếu D1–D10; chờ baseline, môi trường và gate phụ thuộc |

[Phiếu skeleton cũ](archive/) được giữ để đối chiếu lịch sử. `SK-01` là nghiệm thu skeleton server/Pi; `I-01` hiện hành là kho nạp đầy theo bình. Đọc tên file và mục lục này, không suy phạm vi từ mã ngắn.
