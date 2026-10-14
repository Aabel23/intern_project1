# S-03 · Server relay và timeout

> **Đã code theo hợp đồng v2 (12/10/2026)** — [`v2-decisions.md`](../../../../contracts/messages/v2-decisions.md) thắng mọi chỗ mâu thuẫn trong phiếu này (bind tại xưởng thay activation tại chỗ, BLE bỏ R2/Q2, Wi-Fi tùy chọn). Trạng thái BLOCKED bên dưới là lịch sử.

**Trạng thái:** Sau S-02 review; BLOCKED cloud-protection.md. S-03 người ghi cuối routing/http trong skeleton.

## Input chung / cổng

Đọc `documentation/plan/archive/assignments.md`, `documentation/architect/features/contracts.html`, `contracts/COMPATIBILITY.md`, `contracts/messages/security-boundary.md` và hợp đồng module bên dưới. Quyết định chat mới nhất có ưu tiên. Trạng thái của phiếu theo bảng security-boundary.md; thiếu đặc tả thực thì báo Planner, không tự chọn. Mặc định cấu hình đã do Planner chọn, không cần user duyệt từng số. Payload examples là plaintext để kiểm nghiệp vụ, không cho gửi rõ qua mạng.

## Giới hạn và bàn giao

Chỉ skeleton; không menu/share/LAN/BT vận hành/OTA/đổi email/khôi phục mật khẩu. Không sửa `contracts/**`; lỗi hợp đồng báo Planner. Không ghi OTP/password/token/khóa/mã niêm phong/App Password trong file hoặc log. Không sửa vấn đề ngoài phiếu. Các file ghi chung chỉ chuyển người sở hữu sau review nhỏ; không commit code người khác. Chạy ca có giá trị xác minh hành vi, ghi kết quả không chứa bí mật. Kết quả phải gồm diff đúng file được phép, cách chạy, ca đã đạt/không chạy và blocker. Coder không tự đổi thiết kế khi test fail.

## File và hàm

Tạo `server/src/relay.py`: `send_command`, `poll_command`, `receive_result`, `expire_pending`, `get_connectivity`; `tests/server/test_relay.py`. Sửa `server/src/http.py` register MACHINE_COMMAND_SEND/POLL/RESULT; `server/configuration/routing.py` chỉ nếu path không khớp hợp đồng; không sửa auth/claim/config/migrations. Kết nối list online vào get_connectivity qua callback trong http.py; không sửa device_claim.py, giữ list function nhận connectivity callable đã giao.

## Dữ liệu/input/output

Theo relay-status.md; một process/instance, RAM dict + lock/condition; không Redis/DB hàng đợi. pending chứa machine/user/request/body deadline + terminal, delivered bool và waiter; last_poll monotonic chỉ cập nhật sau auth poll hợp lệ. Poll đang mở disconnect cần giải phóng slot; một active poll/máy. Timer riêng finite expire, không chờ receive_result để timeout. Permission getter đọc owner từ DB khi send và trước reply. Identity bound sai máy không access pending. App request v1 instruction whitelist chỉ machine.status.read, data empty. Response server không tạo result như uptime/serial; source chỉ machine cho result máy đã xác thực.

## Thứ tự / lỗi

Implement connectivity→pending/id retry→poll one delivery→timer independent→result match + permission recheck→HTTP mapping. Command send giữ HTTP tới terminal; client disconnect không tạo yêu cầu mới, pending tiếp tục đến deadline. Offline không enqueue; BUSY, REQUEST_CONFLICT, REQUEST_GONE; muộn/trùng/sai máy đúng codes theo hợp đồng. Thread locking không giữ lock trong DB IO/network; sau DB check reacquire và kiểm pending vẫn sống để race không overwrite terminal. Không share/removal endpoint; test recheck dùng fixture đổi owner, không sản phẩm thêm tính năng.

## Ca / cách kiểm

Clock injection + threads deterministically: offline immediate và pending empty; online poll đúng máy; owner khác reject trước queue; correlation 2 máy/2 ID không tráo; replay same ID nối pending vs changed body conflict; busy second ID; drop máy sau dispatch timeout dù không có result; wrong machine result; duplicate/late không đổi terminal; permission mất lúc chờ trả FORBIDDEN; server restart request retry→GONE; cache same terminal giữ received_at; poll timeout command=null. `python3 -m unittest discover -s tests/server -p 'test_relay.py'`. Không dùng sleep 15s hàng loạt cho unit; I-01 đo thời gian thật.
