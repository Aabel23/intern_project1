# M-02 · Máy nối cloud và phục hồi

**Trạng thái:** Sau M-01 review; BLOCKED B-01; M-02 giữ main.py/routing rồi giao M-03.

## Input chung / cổng

Đọc `documentation/plan/assignments.md`, `documentation/architect/features/contracts.html`, `contracts/COMPATIBILITY.md`, `contracts/messages/security-boundary.md` và hợp đồng module bên dưới. Quyết định chat mới nhất có ưu tiên. Trạng thái của phiếu theo bảng security-boundary.md; thiếu đặc tả thực thì báo Planner, không tự chọn. Mặc định cấu hình đã do Planner chọn, không cần user duyệt từng số. Payload examples là plaintext để kiểm nghiệp vụ, không cho gửi rõ qua mạng.

## Giới hạn và bàn giao

Chỉ skeleton; không menu/share/LAN/BT vận hành/OTA/đổi email/khôi phục mật khẩu. Không sửa `contracts/**`; lỗi hợp đồng báo Planner. Không ghi OTP/password/token/khóa/mã niêm phong/App Password trong file hoặc log. Không sửa vấn đề ngoài phiếu. Các file ghi chung chỉ chuyển người sở hữu sau review nhỏ; không commit code người khác. Chạy ca có giá trị xác minh hành vi, ghi kết quả không chứa bí mật. Kết quả phải gồm diff đúng file được phép, cách chạy, ca đã đạt/không chạy và blocker. Coder không tự đổi thiết kế khi test fail.

## File và hàm

Sửa `version1.1/machine/server_connection/machine_server_request.py`: `post_json`, `poll_command`, `send_result`; `machine/main.py`: `poll`, `reply`, `run` (không thêm status handler); `machine/config/routing.py` đúng server path. Tạo `machine/server_connection/auth.py`: `authenticate_request` theo wire đã chốt; tests `tests/machine/test_cloud.py`. Đọc identity API M-01. Không sửa pairing/env/identity. Timeout urllib hiện 10s phải thay theo COMPATIBILITY theo mặc định Planner; không ghi product_key.

## Input/output / thứ tự

relay-status.md. Authenticate độc lập mọi poll/result bằng key bound, không trust serial trong body. Server URL phải bảo vệ theo B-01, kiểm certificate/hostname; không disable validation khi fail. poll decode data.command nullable, truyền command nguyên bản; reply gửi request_id/result đúng máy. long poll HTTP timeout > poll hold. Không app session/refresh token trên máy. Startup M-01 identity trusted→run poll một thread→handle→reply→poll. Lỗi mạng: print code đã lọc, delay 1s hiện hành được giữ tối thiểu; không busy spin. HTTP 401 identity fail dừng poll và báo Operator, không tự register key khác; 503/network retry nối ra. Không hàng đợi bền, không replay result sau expiry.

## Lỗi và ca kiểm

Sai version/schema result không dispatch; unknown instruction M-03 handler trả lỗi chuẩn. Test HTTP local fake boundary (không nghiệm thu): timeout máy lớn hơn hold; command null giữ run; connection drop rồi tiếp tục không tạo identity mới; body không product_key; wrong cert từ chối; result request_id đúng command; không retry expired terminal. `PYTHONPATH=version1.1 python3 -m unittest discover -s tests/machine -p 'test_cloud.py'`. I-01 mới chứng minh cloud auth thật, reconnect Pi thật. Main hiện vẫn menu/ingredient handlers: giữ nội dung, skeleton server chỉ giao instruction status; không đổi handler/menu routes.

Thêm `machine/server_connection/cloud_protection.py`: `seal_request`, `open_response`, `bootstrap_time`; dùng PyHPKE0.6.5/cryptography, identity private P256 M-01; ký envelope low-s, HPKE public pin máy; response exporter mở đúng poll/result context. Bootstrap bằng MACHINE_HELLO_SEND signed bound key, timestamp0 ngoại lệ đọc time; không NTP gate. Không request signing chung plain auth.py tự chế. Time offset monotonic sau handshake; unknown-key/cert/signature stop, không product_key fallback. M-02 thêm HELLO vào routing máy nếu hiện có không thay path. Clock offset/remaining_ms dùng cùng boot monotonic; từ lúc nhận command còn remaining_ms, không trừ cả long-poll hold trước dispatch vì server tính lúc trả command; trừ thời gian deserialize/đợi xử lý kể từ HTTP response nhận.
