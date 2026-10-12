# Relay và đọc trạng thái · nghiệp vụ v1

> **Cập nhật 12/10/2026:** `v2-decisions.md` (D1–D10, cách 3 trên version1.1) thắng mọi chỗ mâu thuẫn với file này.

Payload sau xác thực/giải mã; cổng wire B-01 còn mở. App tạo request_id UUIDv4 mới mỗi bấm Làm mới. Server không lấy identity từ body.

| Người gửi → nhận / route | Request | Success |
|---|---|---|
| App→server MACHINE_COMMAND_SEND | v,request_id,machine_id,instruction=`machine.status.read`,data={} | data={request_id,machine_id,source:`machine`,received_at,result} |
| Máy→server MACHINE_COMMAND_POLL | v (machine identity từ chứng thực) | data={command:null} hoặc command={v,request_id,machine_id,instruction,data,deadline_at,remaining_ms} |
| Máy→server MACHINE_RESULT_SEND | v,request_id,result | data={accepted:true} |

result thành công: {ok:true,data:{serial,software_version,uptime_seconds,read_sequence}}. serial đúng CPU của máy bound; software_version lấy cấu hình runtime hiện hành, không lấy phiên bản server; uptime_seconds integer >=0 từ monotonic process startup; read_sequence integer tăng mỗi lần handler đọc (restart bắt đầu 1). Không trả thời điểm máy như trusted timestamp; received_at là giờ server nhận, UI ghi rõ. Các trường trạng thái này do Planner chọn cho skeleton; không mở menu/hardware telemetry. result lỗi: {ok:false,error:{code:`UNSUPPORTED_INSTRUCTION`|`INVALID_DATA`|`MACHINE_READ_FAILED`|`COMMAND_EXPIRED`}}. Không str(exception) vào gói.

Server identity máy gửi phải trùng máy pending. Kiểm auth→owner hiện tại→version/format→online→pending. Offline trả MACHINE_OFFLINE 503 ngay, không queue. Online: poll đang mở hoặc last_poll_at cách server <=online_grace; không phụ thuộc hello tự khai. RAM một server, pending key (machine_id,request_id), bind user/instruction/data/deadline. Cùng request_id/same user+body còn pending nối waiter; khác nội dung hoặc user REQUEST_CONFLICT 409. Một pending khác trên máy BUSY 409. Poll giao đúng một lần trong hạn; timeout poll trả command=null. Đồng hồ hạn server dùng monotonic, deadline_at chỉ hiển thị; máy dùng remaining_ms trừ thời gian xử lý kể từ lúc client nhận HTTP response bằng monotonic (không trừ toàn long-poll hold), không tin wall clock chưa sync. Server timer kết thúc pending sau 15s kể cả poll/result không trở lại.

Terminal trả đúng một lần: máy result hợp lệ + owner còn đúng → source machine; quyền đổi → FORBIDDEN 403; hết hạn → MACHINE_TIMEOUT 504. Máy lỗi vẫn source machine, app phân biệt với lỗi relay. Muộn/trùng/sai máy → RESULT_EXPIRED 410 / RESULT_ALREADY_FINAL 409 / RESULT_MACHINE_MISMATCH 403, không đổi terminal. Retry same id trong cache terminal 60s trả cùng response và received_at; sau eviction/restart server không tạo đọc mới từ retry: request phải có trường optional `retry:true`; không có record + retry true → REQUEST_GONE 410. App không tự replay như fresh sau network failure; chỉ nút Làm mới tạo mã mới. Client mới retry:false hoặc không có, server restart không biết ID cũ nên app phải đánh retry đúng.

App chỉ hiển thị kết quả nếu request_id và machine_id còn là lượt hiện tại; chọn máy khác/refresh mới xóa nhãn kết quả mới, invalidates generation UI. Offline/timeout/error không thay bằng cache. Cờ online của list có nhãn 'Kết nối cloud', độc lập 'Máy trả lời'. Không gọi MACHINE_STATUS_GET cho phép đo. S-03 không parse dữ liệu result nghiệp vụ nếu cấu trúc envelope/source/correlation hợp lệ; chỉ relay sau chứng thực.
