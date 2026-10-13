# Phân luồng thực thi · phạm vi khách đầu ngày 13/10/2026

**Trạng thái:** Codex đã commit lát transport LAN/HTTP ở `2c4ec6b` và hướng dẫn ở `aae08e8`. Ba Codex agent đã rà độc lập menu/giá, kho–đơn hàng–báo cáo, và OTA cùng transport; kết quả nằm trong [lộ trình mở rộng](first-customer-expanded-roadmap.md). Không dùng Claude. User để kiểm thử trên Android thật sau. G0 và roadmap 44 bước chưa được duyệt lại cho phạm vi mới; không đánh dấu đã qua cổng.

## Đích và thứ tự

1. **P-01 · Planner cập nhật lộ trình:** giữ toàn bộ nhóm đã duyệt ở Mốc 1–2, thêm sửa menu/giá, kho, đơn hàng, OTA, báo cáo. Tách thành module có phụ thuộc, ca sử dụng và cổng nghiệm thu. Sửa `production-roadmap-report.html` cùng sổ tiến độ để không còn mô tả 44 bước cũ là đầy đủ. Chuyển Android thật sang cổng trước phát hành; các kiểm thử tự động vẫn chạy theo task. Đầu ra là HTML roadmap để user duyệt, chưa code.
2. **P-02 · Planner đặc tả đường LAN/HTTP:** từ cùng routing và hợp đồng hiện có, viết phiếu file/hàm/kiểm thử cho app, server, máy. Bản đầu dùng LAN/HTTP; đường Internet/HTTPS về sau phải dùng lại routing và logic. Giữ phong bì mã hóa, chữ ký, phiên và kiểm quyền bên trong. Chỉ mở HTTP trong phạm vi LAN được chốt; không đổi giao thức nghiệp vụ. Đầu ra là phiếu coder riêng cho từng bên, thứ tự sửa và ca kiểm trên máy tính/Pi; chưa code.
3. **P-03 · Planner chia năm nhóm chức năng mới:** mỗi nhóm có hợp đồng, bên giữ dữ liệu, quyền theo vai, thao tác offline/online, luồng lỗi, file cụ thể và ca kiểm. Chỉ phát phiếu coder cho module sau khi thiết kế của module được user quyết. Không suy ra hành vi đơn hàng/OTA/báo cáo từ tab demo hoặc tên tài liệu.
4. **Coder theo từng phiếu đã khóa:** một người giữ file chung mỗi lượt; server, máy, app chỉ sửa trong phạm vi phiếu. Mỗi task qua review nhỏ; module qua review lớn đúng một lần. Kết quả kiểm tự động và Pi/LAN được ghi; Android thật để cổng phát hành.

## Phân khối cho phạm vi mở rộng

Codex giữ vai điều phối. Mỗi dòng là một khối để Planner lập hợp đồng và phiếu riêng; chưa phải quyền cho coder tự hoàn thiện chức năng theo tên khối.

| Thứ tự | Khối / người ghi chính dự kiến | Nền code cần đối chiếu | Quyết định phải khóa trước coder |
|---|---|---|---|
| 1 | **Menu và giá** · máy, sau đó app; server chỉ relay | `machine/menu_sync/`, `feature/machine_menu/`, `documentation/architect/features/menu.html` | Nguồn chuẩn giá/công thức/ảnh, quyền sửa, khi nào thay phiên menu, hành vi offline |
| 2 | **Kho** · máy, sau đó app; server chỉ relay | `machine/ingredient_sync/`, `database/services/inventory.py`, `feature/machine_ingredient/` | Nạp/trừ/sửa/xóa nào giao khách, quyền, đồng bộ và ca kiểm số lượng |
| 3 | **Đơn hàng** · máy và app | `database/services/order_ticket.py`, `feature/orders/demo_orders.dart` | Ai tạo đơn, trạng thái đơn, quan hệ với lượt pha, hủy/hoàn, dữ liệu báo cáo |
| 4 | **Báo cáo** · nguồn dữ liệu máy trước, app hiển thị sau | `database/services/order_ticket.py`, `error_log.py`, `documentation/architect/features/machine-events.html` | Chỉ số/khung thời gian, quyền xem, dữ liệu cần server giữ bản sao, hành vi khi mất mạng |
| 5 | **Cập nhật phần mềm OTA** · máy trước, app theo dõi sau | `documentation/architect/features/software-update.html`, `version1.1/deploy/` | Ai phát bản, quyền duyệt, cách kiểm bản cài, phục hồi khi cập nhật lỗi, lúc nào được ngắt nghiệp vụ pha |

Khối 1–2 có thể lập hợp đồng song song sau đường kết nối; khối 3 cung cấp dữ liệu cho 4. Khối 5 độc lập về nghiệp vụ nhưng chỉ được cài thử khi đã có đường quản trị ổn định. Không giao viết chung `machine/main.py`, route hoặc hợp đồng cho hai coder cùng lúc.

## Bằng chứng code để Planner không tự đoán

| Mảng | Điểm cần đối chiếu | Bằng chứng |
|---|---|---|
| Server transport | HTTPS được bọc trực tiếp ở entry point; cấu hình đòi file TLS | `server/src/http.py`, `server/configuration/skeleton.py` |
| App transport | URL mặc định là HTTPS; config từ chối HTTP; Android main cấm cleartext | `flutter_app/lib/shared/cloud/server_endpoint.dart`, `cloud_config.dart`, `flutter_app/android/app/src/main/AndroidManifest.xml` |
| Máy transport | URL máy từ chối HTTP | `version1.1/machine/config/env.py` |
| Bảo vệ bên trong | App/server/máy có lớp phong bì riêng | `flutter_app/lib/shared/cloud/cloud_crypto.dart`, `server/src/cloud_protection.py`, `version1.1/machine/server_connection/cloud_protection.py` |
| Chức năng hiện có | Server chỉ dispatch tài khoản, máy, relay; app có tab đơn hàng demo | `server/src/http.py`, `flutter_app/lib/feature/orders/demo_orders.dart` |
| Kết nối dữ liệu máy | Code menu và nguyên liệu hiện có cần đối chiếu hợp đồng mới | `version1.1/machine/menu_sync/`, `version1.1/machine/ingredient_sync/` |

## Cổng kiểm

- **Trước coder:** G0 và lộ trình sửa đổi được user duyệt; từng module có thiết kế, quyết định và phiếu đủ chặt.
- **Trong thực thi:** kiểm thử server, máy, Flutter/JVM và review theo phiếu; không dùng việc Android chưa thử để nhận module đã nghiệm thu thật.
- **Trước khách:** Android thật, Pi thật, LAN/HTTP, email OTP, toàn bộ chức năng giao khách và bản release được nghiệm thu. Android được dời tới đây theo yêu cầu hiện tại, không bỏ khỏi cổng phát hành.

## Vấn đề nền khi chạy kiểm

Python hệ thống ngày 13/10/2026 thiếu `pyhpke`; đã dựng môi trường test riêng ở `/tmp/flexmix-codex-test-venv` bằng `server/requirements.txt`. Bằng chứng sau khi sửa L-01:

- `tests/server/test_cloud_protection.py`: 10/10 đạt, gồm phong bì bootstrap thật qua LAN/HTTP và từ chối gói hỏng.
- `tests/server`: ban đầu 23 đạt, 25 skip vì thiếu MySQL fixture. Sau đó Codex agent chạy MySQL 8.4 cô lập trong `/tmp` trên `127.0.0.1:34367`, database chỉ dành cho test `flexmix_fixture_test`, áp migration 001/002: **48/48 đạt, 0 skip** (`python -m unittest discover -s tests/server -v`, 21 giây). Instance đã tắt; DB/service hiện có không bị đụng. Có `ResourceWarning` test về `HTTPError` chưa đóng, không làm fail.
- `tests/machine`: 20 ca, 17 đạt, 3 skip vì cần Kotlin interop fixture.
- `flutter test`: 33/33 đạt; `flutter analyze`: sạch.

**Chưa đạt cổng module:** reviewer độc lập mới rà code và thiết kế, chưa có biên bản review nhỏ/đạt theo phiếu; chưa thử Pi/LAN thật và Android thật. Chưa có biên bản G0 hoặc lộ trình mở rộng được user duyệt. Không ghi L-01 là nghiệm thu sản phẩm.

## Commit hiện tại

- `2c4ec6b Add LAN HTTP transport with pinned envelopes`: server, app và máy chấp nhận URL HTTP chỉ với IP nội bộ/loopback; server giữ cùng dispatch, phong bì và kiểm quyền. Có test tự động theo bằng chứng trên.
- `aae08e8 Document LAN HTTP setup`: hướng dẫn cấu hình tại `server/LAN_HTTP.md` và liên kết từ hướng dẫn Windows/Flutter.
- Chưa đưa các thay đổi tài liệu có sẵn trong working tree vào hai commit trên.
