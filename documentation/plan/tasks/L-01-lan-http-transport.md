# L-01 · Đường LAN/HTTP, giữ hợp đồng và bảo vệ gói

**Vai:** Codex theo yêu cầu hiện tại của user. **Trạng thái 13/10/2026:** L-01S/M/A đã có code và kiểm tự động; chờ review nhỏ độc lập, Pi/LAN thật và tích hợp. **Module:** đường kết nối app ↔ server ↔ máy. Kiểm Android thật để cổng phát hành, không thuộc ca hoàn tất code của phiếu này.

## Đầu vào

User chốt bản đầu kết nối qua LAN/HTTP, giữ phong bì mã hóa/kiểm quyền bên trong; về sau đổi điểm kết nối sang Internet/HTTPS với cùng routing và logic sản phẩm. Đọc `documentation/plan/g0-first-customer-decision.md`, hợp đồng v2 và code hiện tại ở bảng dưới. Không sửa giao thức nghiệp vụ hoặc nới quyền offline.

## Chia task theo người giữ file

| Task | File được sửa | Đầu ra | Ca kiểm không dùng Android thật |
|---|---|---|---|
| L-01S server | `server/configuration/skeleton.py`, `server/src/types.py`, `server/src/http.py`, `server/main.py`, cấu hình/hướng dẫn server | Chế độ HTTPS hiện có vẫn chạy; chế độ HTTP chỉ khi cấu hình rõ, bind địa chỉ LAN; cùng dispatch và phong bì; không đòi cert TLS trong chế độ HTTP | Cấu hình thiếu/sai bị từ chối; request phong bì qua HTTP LAN thành công; gói hỏng/quyền sai vẫn bị chặn |
| L-01M máy | `version1.1/machine/config/env.py`, `machine/server_connection/machine_server_request.py`, hướng dẫn machine | Máy chấp nhận URL HTTP nội bộ được cấu hình, vẫn ghim khóa server và kiểm phong bì; HTTPS vẫn chạy | URL HTTP public bị từ chối; hello/poll/result dùng URL LAN; chữ ký/phong bì hỏng bị chặn |
| L-01A app | `flutter_app/lib/shared/cloud/cloud_config.dart`, Android manifest, hướng dẫn build | App chấp nhận URL HTTP nội bộ được cấu hình; không bỏ trust HPKE/chữ ký; HTTPS vẫn chạy cùng route | Flutter unit: local URL hợp lệ, public HTTP bị từ chối, trust sai bị từ chối; build/analyze nếu môi trường có |
| L-01I tích hợp | Test và biên bản trong `tests/` và `documentation/plan/` | App client và máy dùng cùng server LAN theo hợp đồng hiện có | Python/JVM/Flutter tự động; Pi/LAN thật khi có thiết bị; Android thật để sau |

## Ranh giới bắt buộc

- Không cho phép cleartext tới địa chỉ Internet công khai. Địa chỉ HTTP đầu vào là IP nội bộ hoặc loopback; nếu cần hostname nội bộ, Planner phải đặc tả rõ trước khi coder thêm.
- Không bỏ `server-trust.json`, HPKE, chữ ký máy, phiên hoặc kiểm quyền. Không cho phép HTTP tự động fallback từ HTTPS.
- Cấu hình HTTPS hiện tại vẫn hợp lệ để về sau chỉ đổi điểm kết nối và chế độ transport, không đổi route hay body.
- Không sửa menu, kho, share, đơn hàng, OTA hay báo cáo trong phiếu này.
- Phát hiện phải đổi hợp đồng hoặc quyền: ghi vấn đề và trả về user, không tự sửa lan sang module khác.

## Cổng review

Reviewer nhỏ so từng task L-01S/M/A/I với phiếu và phát hiện sửa thừa; reviewer lớn chỉ một lần sau toàn module. Android thật chưa chạy thì ghi rõ `chưa nghiệm thu thiết bị`, không dùng test tự động thay thế.

### Review nhỏ Codex ngày 13/10/2026 · chưa đạt

- Test HTTP bootstrap và phong bì hỏng đã có, nhưng test quyền/auth trên HTTP và hello/poll/result máy qua HTTP chưa có; cần ca chữ ký máy sai qua HTTP. `tests/server/test_machine_relay.py` hiện chỉ chạy HTTPS.
- Flutter kiểm local/public URL nhưng chưa có ca trust sai theo tiêu chí L-01A.
- `server/tools/provision_keys.py` và `version1.1/machine/config/env.py` chưa đọc/kiểm `.port`, nên `:abc` hoặc `:99999` được chấp nhận lúc cấu hình rồi mới lỗi khi dùng.
- Review xác nhận HTTP và HTTPS đi cùng `open_request → dispatch → close_response`, mặc định HTTPS và HTTP chỉ bind IP nội bộ/loopback. Chưa thấy bỏ qua phong bì/kiểm quyền. Android cleartext bật toàn app cần rà chính sách khi đưa ra Internet.

**User quyết 13/10/2026: chỉ ghi nhận, chưa sửa.** Giữ các phát hiện làm issue mở của L-01; không giao coder sửa test hay validator trong lượt này và chưa đánh dấu module đạt. Cổng phát hành vẫn cần đánh giá lại những ca còn thiếu.
