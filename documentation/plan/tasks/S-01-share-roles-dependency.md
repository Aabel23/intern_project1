# S-01 · Share máy và quyền theo vai cho khách đầu

**Trạng thái:** phiếu Planner về phụ thuộc, chưa duyệt hợp đồng chi tiết và chưa cho sửa production code. Phạm vi khách đầu có share máy, Manager và Employee. Giá chỉ Owner/Manager sửa qua cloud; danh sách vé QR O-01 trước mắt chỉ Owner xem; kho I-01 nạp đầy từng bình. Các đường tại chỗ và chính sách quyền phải được khóa trước khi giao coder.

## Code đang chạy

| Lớp | Bằng chứng | Hiện trạng |
|---|---|---|
| Server DB | `server/migrations/002_devices_sessions.sql` | `devices` chỉ có `owner_user_id`; chưa có membership, vai, lời mời, `acl_version` hay lịch sử quyền. `device_audit` chỉ ghi hành động máy. |
| Server nghiệp vụ | `server/src/devices.py` `list_user_machines`, `owner_of`, `remove_machine` | Chỉ liệt kê máy do chính user sở hữu, trả role cố định `owner`; gỡ máy đặt owner về null. Chưa có endpoint share/role/member/permission thực thi. |
| Server relay | `server/src/relay.py` `command_send`, `RelayHub.send` | Allowlist lệnh chung và kiểm `owner_of == user_id` khi gửi, rồi kiểm lại trước khi trả. Chưa có policy theo instruction/vai; lệnh xuống máy không mang actor/role đã xác thực. |
| Máy | `version1.1/machine/main.py`, `machine/pairing/machine_bluetooth_pair.py` | Chỉ nhận lệnh menu/kho/trạng thái qua cloud relay. BLE hiện dùng **nhận chủ**, không phải chuyển lời mời giữa hai điện thoại hay cấp quyền tại chỗ. Không có bản sao ACL đã ký để kiểm quyền offline. |
| App | `flutter_app/lib/feature/machines/data/machine_service.dart`, `dashboard/ui/machines_tab.dart` | Decoder chỉ chấp nhận role `owner`; tab có nút share nhưng `DeviceSharePage` chưa có QR/mã mời thật, nút tạo lại/thu hồi gọi `notAvailableYet`. Hai màn Bluetooth chỉ là UI. Manager/Employee chưa thể xuất hiện trong danh sách máy. |
| Routing/tài liệu | `server/configuration/routing.py`, `documentation/architect/features/machine-sharing.html` | Có tên đường share/role/permission và mô tả luồng, nhưng không có route handler. Một số quyết định trong tài liệu còn ghi “tạm chốt”; không xem tên route là triển khai xong. |

## Ma trận quyền cần đưa vào hợp đồng

| Việc | Slice đầu đề xuất | Phụ thuộc |
|---|---|---|
| Xem máy, trạng thái, menu, kho | Owner/Manager/Employee đã là member | Server query membership và app parse role; quyền đọc sau thu hồi phải mất ngay trên server. |
| Bật/tắt món | Owner/Manager/Employee | Lệnh riêng M-01C; server kiểm instruction, máy kiểm trên đường tại chỗ khi có đường đó. |
| Sửa giá | Owner/Manager, **cloud only** | M-01D phụ thuộc role; từ chối Employee ở server và từ chối đường LAN/Bluetooth tại máy. |
| Xem danh sách vé QR | **Owner only** cho O-01 | Không tự mở cho Manager/Employee khi share được triển khai; sau đó có quyết định riêng. |
| Xem kho, nạp đầy từng bình | Xem: mọi member; nạp: cần chốt vai được phép | I-01 chưa khóa ma trận quyền và định danh bình. Không suy ra quyền ghi từ quyền xem. |
| Tạo lời mời | Owner/Manager theo tài liệu thiết kế | Người mới vào làm Employee; cần xác nhận Manager có được share trong bản đầu. |
| Nâng/hạ Manager | Owner | Cần check version ACL và ghi lịch sử cùng transaction. |
| Gỡ thành viên, chuyển chủ | Chưa khóa cho bản đầu | Tài liệu mô tả nhưng còn “tạm chốt”; tách phiếu sau nếu khách đầu cần. |

UI chỉ ẩn nút để dễ dùng. Server là nơi quyết quyền cho cloud; máy kiểm quyền từ bản sao đã ký cho lệnh trực tiếp tại chỗ. Trả lời relay sau thu hồi phải kiểm lại membership và quyền đúng **instruction** đã gửi, không chỉ còn là member.

## Chuỗi phiếu nhỏ nhất có thể triển khai

1. **S-01A · Membership và policy cloud:** schema thành viên duy nhất theo `(machine_id,user_id)`, vai Employee/Manager, owner duy nhất hiện ở `devices`; một hàm kiểm `(user,machine,instruction)` dùng cho list và relay; giữ hành vi owner hiện có. Chốt ý nghĩa thu hồi owner trước migration.
2. **S-01B · Lời mời online:** Owner/Manager tạo mã ngẫu nhiên một lần có hạn; người nhận đăng nhập chấp nhận; người mời xác nhận đúng tài khoản trước khi cấp Employee. DB transaction dùng mã mời đã băm, hạn, trạng thái, người tạo/người nhận; chống hai lần accept/sign và kiểm quyền người mời **lúc xác nhận**. App làm QR trước; Bluetooth giữa hai điện thoại chỉ chuyển cùng mã mời khi đường đó có triển khai thật.
3. **S-01C · Quản trị vai và danh sách:** Owner đổi Employee↔Manager; danh sách thành viên và version ACL; gỡ thành viên sau khi chính sách được khóa. App refresh máy/role sau thay đổi, xóa dữ liệu máy ngay khi mất quyền.
4. **S-01D · Bản sao ACL máy và đường tại chỗ:** server phát bản đã ký theo version, máy kéo về và lưu bền vững, kiểm máy ID/phiên bản/hạn bằng giờ server và đồng hồ đơn điệu. LAN/Bluetooth quản lý chỉ được coi là hỗ trợ sau khi có xác thực app→máy, truyền actor, kiểm ACL và kiểm lệnh cấm tại chỗ. BLE claim hiện có không phải nền đó.
5. **Tích hợp module:** M-01D giá cần S-01A trước; O-01 giữ owner-only và không bị nới quyền tình cờ; I-01 quyền nạp cần chốt trước coder; thử revoke giữa lúc relay chờ và khi máy offline.

Không cần chờ bản sao ACL ở máy để cho Manager dùng lệnh **qua cloud** nếu server kiểm role hiện hành, route xuống máy đáng tin và máy nhận được chứng cứ actor/quyền theo hợp đồng đã ký. Cách ràng buộc đó phải được đặc tả; không để `data` do app tự khai vai. Đường LAN/Bluetooth trực tiếp phải chờ S-01D.

## Quyết định phải khóa trước coder

1. Khách đầu bắt buộc share bằng QR online và Bluetooth chuyển mã mời cùng đợt hay có thể giao từng đường? App/máy hiện chưa có đường BLE hai điện thoại.
2. Manager được tạo lời mời và gỡ đúng người mình thêm như tài liệu “tạm chốt” không? Người được share có tự rời máy không? Chủ chuyển quyền/gỡ máy khi đang có member xử lý thế nào?
3. Quyền nạp đầy bình I-01 cho vai nào? Xem vé QR sau O-01 có giữ Owner-only hay mở thêm vai ở lượt sau?
4. Trên LAN/Bluetooth trực tiếp, app chứng minh account/role với máy bằng gì; hạn bản sao ACL, nhịp kéo, và chính sách khi bản sao hết hạn là gì? Tài liệu đề xuất 7 ngày/6 giờ nhưng chưa biến thành hợp đồng máy.
5. `acl_version`, định dạng byte ký, khóa tin cậy, rollback/chống replay, và cập nhật máy sau thu hồi được ràng buộc ra sao; lệnh cloud mang actor/quyền nào để máy ghi nhật ký và kiểm lại?
6. Khi lời mời hoặc vai đổi trong khi hai app đang thao tác, thông báo/xử lý conflict và lịch sử audit tối thiểu gồm những gì?

## Ca kiểm cho coder sau khi khóa hợp đồng

- Hai account nhận cùng mã chỉ một người thắng; mã hết hạn/dùng lại/tạo bởi người đã bị gỡ không cấp quyền; Manager được/hạn chế đúng ma trận.
- Owner, Manager, Employee thấy đúng máy và thao tác; Employee không đổi giá; Manager đổi giá qua cloud, giá qua LAN/Bluetooth bị chặn; O-01 vẫn Owner-only.
- Thu hồi khi lệnh đang chờ chặn response; khi app đổi máy/mất quyền xóa cache dữ liệu; máy offline áp đúng hạn bản sao đã ký và không nhận ACL cũ/sai máy.
- Thay vai đồng thời không ghi đè lặng lẽ; ghi quyền, tăng version và audit cùng một transaction; máy khởi động lại vẫn giữ/kiểm bản sao hợp lệ.
- Test server+DB, máy và Flutter tự động trước; Pi/LAN và Android thật tại cổng tích hợp/phát hành theo lịch user đã chốt.
