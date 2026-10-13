# U-01 · Gói cập nhật máy qua LAN HTTP có chữ ký

**Vai:** Planner Codex. **Trạng thái:** bản thiết kế để chốt; chưa giao coder, chưa nghiệm thu. **Phạm vi:** phần mềm máy trong `version1.1/`, không gồm phát hành app hay cập nhật hệ điều hành.

## Quyết định đã có

- Khách đầu tiên cần OTA. Máy tải gói qua LAN HTTP. Máy **bắt buộc kiểm chữ ký phát hành và SHA-256 của gói trước khi cài**; HTTP không tạo quyền tin cậy cho gói.
- Khoá riêng phát hành giữ offline, không nằm trên server. Khoá công khai phát hành ghim sẵn trên máy. Phiên bản chỉ tăng; chỉ chuyển bản khi máy không đang pha đơn; khởi động lỗi phải quay về bản đang chạy. Server trước, máy sau, app cuối. Nguồn: `documentation/architect/features/software-update.html`.
- Lệnh máy ↔ server vẫn đi qua phong bì HPKE và chữ ký máy theo hợp đồng v2; việc tải file gói là luồng riêng. Chuyển LAN HTTP sang Internet HTTPS sau này không đổi route nghiệp vụ.

**Xung đột tài liệu cần cập nhật sau khi chốt phiếu:** `documentation/architect/features/software-update.html` mục Endpoint hiện ghi tải file qua TLS. Quyết định LAN HTTP của user thay câu đó cho bản đầu; không suy ra rằng có thể bỏ kiểm chữ ký/hash khi chuyển sang HTTPS.

## Bằng chứng mã hiện tại

`server/configuration/routing.py` và `version1.1/machine/config/routing.py` đã có `/machine/update/get` và `/machine/update/report`. `server/src/cloud_protection.py` chưa đưa hai route này vào `machine_routes()/all_routes()`, `server/src/http.py` chưa dispatch chúng. Máy chưa có client OTA. `version1.1/deploy/install.sh` cài trực tiếp vào cây dự án và `version1.1/deploy/kiosk/flexmix-backend.service` chạy từ đó; chưa thấy hai slot phát hành và cơ chế rollback. Vì vậy route constant và sơ đồ A/B chưa được coi là chức năng hoạt động.

## Hợp đồng tin cậy đề xuất để user duyệt

1. **Bản phát hành:** hãng tạo gói và một manifest có ít nhất release ID, phiên bản tăng đơn điệu, loại/model máy tương thích, kích thước, SHA-256 của đúng byte gói và định danh khoá ký. Chữ ký offline bao phủ các trường ảnh hưởng đến cài đặt, đặc biệt phiên bản, model và SHA-256. Cần chốt thuật toán, dạng byte ký/canonical encoding và cách đổi/thu hồi khoá trước khi tạo wire contract. Không dùng khoá HPKE server hoặc khoá danh tính máy làm khoá phát hành.
2. **Phân phối:** server trả `release: null` hoặc metadata bản được phát qua `MACHINE_UPDATE_GET` trong phong bì hiện có. File gói có thể tải qua HTTP LAN; metadata và URL là đầu mối tải, **chữ ký phát hành ghim trên máy mới là nguồn xác thực bản cài**. Không tự theo redirect ra Internet/host khác, không nhận URL file từ nguồn khác. Chốt giới hạn kích thước, host/path cho file và nơi server lưu gói trước khi coder thêm route tải file.
3. **Máy kiểm trước mọi tác động:** tải vào file tạm trong vùng dành cho cập nhật; áp giới hạn byte; kiểm kích thước thực, SHA-256 và chữ ký/manifest; kiểm đúng model và phiên bản cao hơn bản đã xác nhận. Mọi lỗi kiểm phải bỏ file tạm, giữ bản hiện chạy và chỉ báo `rejected` với mã lỗi đã lọc. Không giải nén/chạy/cài một byte gói nào trước khi mọi kiểm tra hoàn tất.
4. **Cài và quay về:** chỉ chuyển bản khi gate nghiệp vụ xác nhận không có đơn đang pha. Đặt bản mới ở slot không chạy; đổi slot bằng thao tác nguyên tử, theo dõi sống/khỏe sau khởi động, tự quay về slot cũ nếu thất bại hoặc hết hạn. Chỉ báo `ok` sau khi bản mới qua health gate; báo `rolled_back` sau khi máy thực sự chạy lại bản cũ. Giữ trạng thái cài/rollback bền qua mất điện và retry. Cần khảo sát Pi/OS, service và đường dữ liệu thực tế để biến quy tắc này thành lệnh cài cụ thể.
5. **Server và báo cáo:** lưu kết quả theo máy + release ID để retry không tạo hai lần cài; quyền phát bản và trạng thái triển khai phải tách khỏi quyền Owner/Manager điều khiển máy. `MACHINE_UPDATE_REPORT` chỉ chấp nhận danh tính máy đã đăng ký; không lấy chuỗi lỗi thô từ máy vào log hoặc UI.

## Chia lát việc sau khi duyệt thiết kế

| Lát | Chủ file dự kiến | Đầu ra kiểm được |
|---|---|---|
| U-01A: chuẩn gói/manifest và khoá phát hành | Hợp đồng OTA mới, công cụ phát hành riêng | Vector chữ ký/hash độc lập; gói bị sửa một byte, sai model, sai/giảm phiên bản đều bị từ chối |
| U-01B: máy kiểm và staging | `version1.1/machine/` module OTA mới | Tải HTTP LAN giới hạn byte, không redirect ngoài nguồn; xác minh trước giải nén/cài; cúp mạng/file hỏng giữ bản cũ |
| U-01C: server phát metadata/file và nhận report | `server/src/`, migration mới | Chỉ máy bound hỏi/báo; release ID idempotent; gói không ký hợp lệ không thể được đánh dấu đã cài |
| U-01D: cài A/B và rollback | `version1.1/deploy/`, service máy | Đổi slot lúc máy rảnh, health check và rollback qua reboot/mất điện thật |
| U-01E: tích hợp | `tests/`, biên bản thiết bị | Kiểm end-to-end server LAN HTTP → Pi; mất mạng, gói bị sửa, reboot lỗi, đang pha đơn; Android thật để cổng phát hành sau |

Lát U-01A/B có thể chuẩn bị trước khi cài A/B, nhưng **không được coi OTA hoàn tất** khi mới tải và kiểm gói. Không sửa route/protocol sản xuất hoặc service máy chỉ từ phiếu dự thảo này.

## Còn phải quyết trước khi coder

1. Ai tạo/ký/duyệt một release; ai được yêu cầu server phát bản cho từng máy và quyền thu hồi? Cần ranh giới vận hành rõ, không suy từ vai Owner của app.
2. Model Pi/OS và sơ đồ cài hiện tại nào là đích; ứng dụng, cấu hình danh tính/khóa, database và dữ liệu bán hàng nằm ở đâu? Phân định chính xác phần được thay với phần phải sống qua rollback.
3. Dạng gói, thuật toán chữ ký, định dạng manifest/byte ký, quy tắc tăng phiên bản và chính sách quay lại bản cũ khi bản mới đã đánh dấu tốt.
4. URL/host file, giới hạn dung lượng, nơi giữ file tạm và dung lượng trống tối thiểu trên Pi; có cho server riêng cấp file hay cùng server API LAN?
5. Tín hiệu “đang pha đơn” và health check nào đủ để chuyển/giữ bản mới; thời gian chờ kiểm sức khoẻ (tài liệu đang để 5 phút) và cách báo trạng thái sau mất điện.

Sau khi các điểm này được chốt, Planner cập nhật thiết kế OTA và hợp đồng wire, phát phiếu coder theo từng lát, rồi review độc lập. Chưa có Android hoặc Pi thật trong đợt này.
