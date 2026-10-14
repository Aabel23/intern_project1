# M-03 · Máy tự đọc trạng thái

> **Đã code theo hợp đồng v2 (12/10/2026)** — [`v2-decisions.md`](../../../../contracts/messages/v2-decisions.md) thắng mọi chỗ mâu thuẫn trong phiếu này (bind tại xưởng thay activation tại chỗ, BLE bỏ R2/Q2, Wi-Fi tùy chọn). Trạng thái BLOCKED bên dưới là lịch sử.

**Trạng thái:** Sau M-02 review; trường trạng thái đã chốt Planner, handler có thể đặc tả nhưng chưa phát.

## Input chung / cổng

Đọc `documentation/plan/archive/assignments.md`, `documentation/architect/features/contracts.html`, `contracts/COMPATIBILITY.md`, `contracts/messages/security-boundary.md` và hợp đồng module bên dưới. Quyết định chat mới nhất có ưu tiên. Trạng thái của phiếu theo bảng security-boundary.md; thiếu đặc tả thực thì báo Planner, không tự chọn. Mặc định cấu hình đã do Planner chọn, không cần user duyệt từng số. Payload examples là plaintext để kiểm nghiệp vụ, không cho gửi rõ qua mạng.

## Giới hạn và bàn giao

Chỉ skeleton; không menu/share/LAN/BT vận hành/OTA/đổi email/khôi phục mật khẩu. Không sửa `contracts/**`; lỗi hợp đồng báo Planner. Không ghi OTP/password/token/khóa/mã niêm phong/App Password trong file hoặc log. Không sửa vấn đề ngoài phiếu. Các file ghi chung chỉ chuyển người sở hữu sau review nhỏ; không commit code người khác. Chạy ca có giá trị xác minh hành vi, ghi kết quả không chứa bí mật. Kết quả phải gồm diff đúng file được phép, cách chạy, ca đã đạt/không chạy và blocker. Coder không tự đổi thiết kế khi test fail.

## File/hàm

Tạo `version1.1/machine/status/machine_status_request.py`: `read_status(data)`, `COMMANDS={"machine.status.read":read_status}`; `machine/status/__init__.py`; tests `tests/machine/test_status.py`. Sửa `machine/main.py` import/ghép STATUS_COMMANDS và `handle_command` cho cấu trúc lỗi chuẩn skeleton chỉ instruction này, không đổi menu/ingredient errors. Main M-02 bàn giao riêng trước sửa. Đọc `machine/config/identity.py`, env version API đã chốt; nếu không có software_version đọc constant MACHINE_SOFTWARE_VERSION="1.1" từ config/identity.py do M-01 thêm (phiên bản runtime repo1.1); không phiên bản server hay request.

## Input/output / thứ tự

relay-status.md. Before handler dispatch kiểm remaining_ms chưa hết bằng monotonic tại nhận; data phải object rỗng. `read_status` đọc CPU serial hiện tại và monotonic uptime tại lúc xử lý, tăng read_sequence; không cache snapshot/clock server. Không IO DB, không GPIO/pump/menu. Handler trả result success đúng schema hoặc MACHINE_READ_FAILED không traceback. Unknown instruction mới trả UNSUPPORTED_INSTRUCTION, invalid data trả INVALID_DATA, expired command trả COMMAND_EXPIRED không đọc. Không gọi server status như nguồn máy.

## Ca / cách kiểm

Patch monotonic và serial reader độc lập: 2 lượt cho sequence tăng/uptime khác; serial là nguồn hiện tại chứ command.machine_id tự khai; invalid/nonempty data không đọc; deadline hết không đọc; missing serial trả lỗi; main COMMANDS dispatch status thật; menu handler không bị sửa. `PYTHONPATH=version1.1 python3 -m unittest discover -s tests/machine -p 'test_status.py'`; reboot thực I-01 quan sát uptime/sequence reset nhưng key bền. Không thêm telemetry CPU temp/order/menu.
