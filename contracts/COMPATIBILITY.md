# Skeleton v1 · C-05

**Trạng thái: cloud đã đặc tả; BT/claim BLOCKED, chưa phát các phiếu phụ thuộc.** Lộ trình đã duyệt; các gói nghiệp vụ dưới đây là đặc tả Planner. Bảng cổng và phiếu được phép bắt đầu nằm trong `messages/security-boundary.md`. File JSON trong examples là dữ liệu đã giải mã để kiểm hợp đồng, không phải body được phép gửi rõ trên Internet/Bluetooth.

## Quy tắc chung

- Một phiên bản nghiệp vụ `v: 1`, JSON UTF-8 object, không NaN/Infinity; số nguyên trong miền an toàn JSON; UTC RFC3339 cho giờ server. Không tự bỏ qua trường bắt buộc. Trường lạ bị từ chối `INVALID_REQUEST`; v khác 1 bị từ chối `UNSUPPORTED_VERSION` trước xử lý. Không chạy song song với product_key cũ.
- POST cho mọi endpoint skeleton. Trả thành công `{v:1,ok:true,data:{...}}`; lỗi `{v:1,ok:false,error:{code:"..."}}`. Không trả traceback, SMTP transcript, OTP, mật khẩu, mã niêm phong, token hay private key trong log.
- HTTP: 400 định dạng/version; 401 phiên/danh tính; 403 quyền; 409 xung đột/trạng thái; 410 hết hạn; 429 giới hạn; 502 SMTP; 503 offline; 504 relay timeout; 500 lỗi nội bộ. UI dựa `error.code`, không dựa chuỗi tự do.
- Route hằng hiện hành là input, không chứng minh handler tồn tại. Hợp đồng mô tả payload nghiệp vụ; cổng bảo vệ phải chốt trước khi chọn HTTP body/header. Không sửa routing trong C-05.
- Token không chứa vai cố định. Server đọc quyền máy hiện hành từ DB mỗi lần nhận câu hỏi và trước trả kết quả. Owner duy nhất; skeleton chưa có share/đổi vai/chuyển chủ/gỡ máy.
- Máy đang chạy giao thức cũ phải từ chối vào skeleton. Không chuyển PRODUCT_KEY sang seal_code; không lấy product_key làm bằng chứng máy. Không giả lập thiết bị trong nghiệm thu.

## Thông số mặc định Planner (cấu hình kỹ thuật)

Một file duy nhất `server/configuration/skeleton.py` do S-01 sở hữu, immutable trong runtime; máy/app lấy timeout từ kết quả server khi cần. Giá trị mặc định: OTP 6 chữ số/10 phút, gửi lại 60 giây, tối đa 5 lần sai mỗi email, khóa15 phút rồi reset bộ đếm, 5 gửi/email/giờ và 20 gửi/IP/giờ; login 10 thất bại/IP/10 phút. Access **3600 giây**, refresh idle **2592000 giây** là user đã chốt. Claim challenge 120 giây, pending relay 15 giây, poll 20 giây, HTTP máy 25 giây, HTTP app relay 20 giây, online grace 30 giây, giữ terminal relay RAM 60 giây; tối đa 1 poll đang mở/máy và 1 pending status/máy. Planner chọn các mặc định ngoài access/refresh: 10 phút đủ đọc email; 60s hạn chế thư dồn; 5 lần sai khóa15 phút, resend không mở khóa, giới hạn đoán OTP; relay15s tạo phản hồi hữu hạn, poll20s/HTTP25s tránh cắt poll trước server; online30s chịu một nhịp poll; terminal60s đủ retry ngắn mà không lưu bền. Coder không tự đổi.

## Sở hữu và thứ tự

| Tài nguyên | Người ghi | Khi nào |
|---|---|---|
| `contracts/**` | Planner C-05 | Không coder nào sửa; thiếu hợp đồng báo Planner |
| `server/configuration/routing.py`, `server/src/http.py` | S-01 → S-02 → S-03 | Tuần tự; bàn giao sau review nhỏ, không cùng ghi |
| `server/configuration/skeleton.py`, migration nền | S-01 | S-02/S-03 đọc; thiếu cấu hình báo Planner |
| migration claim mới | S-02 | Không sửa migration S-01 đã chạy |
| `version1.1/machine/config/routing.py` | M-01 → M-02 | Tuần tự; M-03 không ghi |
| `version1.1/machine/main.py` | M-02 → M-03 | Tuần tự sau review nhỏ |
| `flutter_app/lib/app/app_navigation.dart` | A-01 | A-02/A-03 không ghi |
| `dashboard_page.dart`, `machines_tab.dart` | A-02 → A-03 | Tuần tự; A-01 logout qua callback đã giao |
| `flutter_app/pubspec.yaml`, Android config | A-01 → A-02 | Không ghi đồng thời; dependency crypto chỉ sau chốt cổng |

Chuỗi server S-01 → S-02 → S-03, máy M-01 → M-02 → M-03, app A-01 → A-02 → A-03. Sau chốt cổng của từng phiếu, ba phía cùng phase có thể làm song song với file riêng. I-01 chỉ đọc và ghi test/biên bản; không sửa sản phẩm khi phát hiện lỗi. Không chạy coder chỉ bằng bảng slot trong assignments.
