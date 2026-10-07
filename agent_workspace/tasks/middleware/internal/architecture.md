> Hồ sơ nội bộ cho agent. Chuyển từ tài liệu HTML ngày 06/10/2026; nội dung và bằng chứng cũ được giữ, chưa kiểm lại sản phẩm. Sơ đồ gốc giữ dưới dạng mã SVG trong khối XML.

KẾ HOẠCH PHÁT TRIỂN / 05.10.2026

# Kiến trúc và ranh giới trách nhiệm

Middleware phục vụ vận chuyển chung; nghiệp vụ và quyền tiếp tục ở module đã chốt.

Tài liệu thiết kế và kế hoạch · Offline / In đượcTrang này là nghiên cứu chuyên đề. Kế hoạch thực thi chính thức đi theo phase lớn → phase con; xem [bản đồ chương trình](index.md). Task chi tiết đã chuyển tới phase con liên kết bên dưới.

## Bản đồ thành phần

Hiện trạngĐề xuấtKho dữ liệuLỗi / điều kiện cần chốt

Ranh giới hệ thống và điểm tích hợp middleware

```xml
<svg aria-label="Ranh giới hệ thống và điểm tích hợp middleware" role="img" viewbox="0 0 1080 365" xmlns="http://www.w3.org/2000/svg"><title>Ranh giới hệ thống và điểm tích hợp middleware</title><defs><marker id="arrow-43603" markerheight="7" markerwidth="7" orient="auto" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0 0L10 5L0 10z" fill="#667b8d"></path></marker></defs><path d="M270 80L420 80" fill="none" marker-end="url(#arrow-43603)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="61.199999999999996" x="314.4" y="58.0"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="345.0" y="74.0">HTTP JSON</text><path d="M660 80L810 80" fill="none" marker-end="url(#arrow-43603)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="102.0" x="684.0" y="58.0"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="735.0" y="74.0">handle(request)</text><path d="M930 130L930 235" fill="none" marker-end="url(#arrow-43603)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="61.199999999999996" x="899.4" y="160.5"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="930.0" y="176.5">đọc / ghi</text><path d="M810 80L660 285" fill="none" marker-end="url(#arrow-43603)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="50" x="710.0" y="160.5"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="735.0" y="176.5">send()</text><path d="M420 285L270 285" fill="none" marker-end="url(#arrow-43603)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="88.39999999999999" x="300.8" y="263.0"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="345.0" y="279.0">lệnh qua poll</text><path d="M270 285L420 80" fill="none" marker-end="url(#arrow-43603)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="122.39999999999999" x="283.8" y="160.5"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="345.0" y="176.5">heartbeat / result</text><rect fill="#edf2f6" height="100" rx="10" stroke="#59748a" stroke-width="1.8" width="240" x="30" y="30"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="150" y="58">App Flutter</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="84">Token phiên trong JSON</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="105">Request đọc / thao tác ghi</text><rect fill="#e4f3f0" height="100" rx="10" stroke="#218777" stroke-width="1.8" width="240" x="420" y="30"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="540" y="58">Biên HTTP chung</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="84">http_server + http_json</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="105">Lifecycle đề xuất tại đây</text><rect fill="#edf2f6" height="100" rx="10" stroke="#59748a" stroke-width="1.8" width="240" x="810" y="30"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="930" y="58">Module nghiệp vụ</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="84">main → tác vụ</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="105">Quyền / validate / transaction</text><rect fill="#edf2f6" height="100" rx="10" stroke="#59748a" stroke-width="1.8" width="240" x="30" y="235"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="150" y="263">Máy tại quán</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="289">Poll / thực thi / result</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="310">Menu + Kho tại máy</text><rect fill="#eaf0fc" height="100" rx="10" stroke="#5271b4" stroke-width="1.8" width="240" x="420" y="235"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="540" y="263">Transport RAM</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="289">HOP_THU / DANG_CHO</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="310">Heartbeat / condition</text><rect fill="#eaf0fc" height="100" rx="10" stroke="#5271b4" stroke-width="1.8" width="240" x="810" y="235"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="930" y="263">SQLite server</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="289">Users / sessions / machines</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="310">Managers / invites</text></svg>
```

Đối chiếu main, HTTP helpers, transport và caller. Server không gọi chủ động xuống máy. Luồng result qua HTTP machine_link rồi deliver; lớp màu xanh là đề xuất.

## Hợp đồng giữ xuyên suốt

| Ranh giới | Giữ nguyên | Giới hạn thay đổi |
| --- | --- | --- |
| Khởi động | [`server/main.py`](../../../../server/main.py) import trực tiếp MODULES, chạy toàn bộ | Không registry động hoặc tháo module |
| HTTP→module | handle(request) → bool; GET qua handle_get | Context chỉ thêm nội bộ, không đổi chữ ký hàng loạt |
| Module→flow | MAX_BODY, error callback, body/status | Không chuẩn hóa hai dạng response ngầm |
| App→server | token JSON, login_required khi hết phiên | Authorization là nhánh đổi contract riêng |
| Server→máy | id / instruction / data; không token app | Idempotency/durability phải cập nhật các bên |
| Quyền/SQL | SQL tham số, get_connection, task giữ transaction | Remove giữ BEGIN IMMEDIATE trước đọc quyền |

## Phương án được chọn

Mở rộng server/lib/http bằng các thay đổi nhỏ có test hành vi. Giữ parse trong handle_routes ở bản đầu; không đọc rfile ở middleware rồi đọc lại trong module. Chỉ thêm helper/file mới nếu có trách nhiệm đủ rõ, không lớp rỗng cho đẹp cấu trúc.

Gần hạn không đổi framework/schema/giao thức. Mở rộng runtime, device credential, command bền vững và nhiều worker được tách ở [nhánh dài hạn](expansion.md) với điều kiện kích hoạt.

## Bản đồ file

| Nhóm | File nền | Phần việc |
| --- | --- | --- |
| Lifecycle | [`server/lib/http/http_server.py`](../../../../server/lib/http/http_server.py) · [`server/lib/http/http_json.py`](../../../../server/lib/http/http_json.py) | Context, exception biên, response một lần |
| Body/quota | [`server/lib/http/http_rate_limit.py`](../../../../server/lib/http/http_rate_limit.py) · [`server/config/config.py`](../../../../server/config/config.py) | Framing, deadline, admission/limiter |
| Transport | [`server/lib/machine/machine_transport.py`](../../../../server/lib/machine/machine_transport.py) | Queue/capacity khi có task riêng |
| Danh tính | [`server/lib/security/user_session.py`](../../../../server/lib/security/user_session.py) · [`server/lib/machine/machine_access.py`](../../../../server/lib/machine/machine_access.py) | Phiên và cơ chế tra quyền, không đưa rule feature vào lib |
| Kiểm | [`tests/run_tests.py`](../../../../tests/run_tests.py) · tests/python/ | Tất cả test và mô phỏng ở tests/ |

## Điều kiện đổi phương án

Chỉ đánh giá runtime khác khi parser/capacity/deployment hiện tại không đáp ứng yêu cầu đã kiểm, hoặc có môi trường production cần tính năng vận hành cụ thể. Prototype phải chạy cùng contract/load suite và giữ module API. Quyết định kiến trúc trình riêng trước code.
