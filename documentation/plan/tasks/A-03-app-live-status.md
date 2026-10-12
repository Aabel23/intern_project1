# A-03 · App hỏi trạng thái trực tiếp

**Trạng thái:** Sau A-02 review; S-03/M-03 hợp đồng đã kiểm cloud-protection.md. A-03 giữ dashboard cuối.

## Input chung / cổng

Đọc `documentation/plan/assignments.md`, `documentation/architect/features/contracts.html`, `contracts/COMPATIBILITY.md`, `contracts/messages/security-boundary.md` và hợp đồng module bên dưới. Quyết định chat mới nhất có ưu tiên. Trạng thái của phiếu theo bảng security-boundary.md; thiếu đặc tả thực thì báo Planner, không tự chọn. Mặc định cấu hình đã do Planner chọn, không cần user duyệt từng số. Payload examples là plaintext để kiểm nghiệp vụ, không cho gửi rõ qua mạng.

## Giới hạn và bàn giao

Chỉ skeleton; không menu/share/LAN/BT vận hành/OTA/đổi email/khôi phục mật khẩu. Không sửa `contracts/**`; lỗi hợp đồng báo Planner. Không ghi OTP/password/token/khóa/mã niêm phong/App Password trong file hoặc log. Không sửa vấn đề ngoài phiếu. Các file ghi chung chỉ chuyển người sở hữu sau review nhỏ; không commit code người khác. Chạy ca có giá trị xác minh hành vi, ghi kết quả không chứa bí mật. Kết quả phải gồm diff đúng file được phép, cách chạy, ca đã đạt/không chạy và blocker. Coder không tự đổi thiết kế khi test fail.

## File và hàm

Tạo `flutter_app/lib/feature/dashboard/data/status_service.dart`: `readStatus(machineId,requestId,{retry=false})`; `feature/dashboard/ui/live_status_panel.dart`: LiveStatusPanel và state `refreshStatus`. Sửa `feature/dashboard/ui/dashboard_page.dart` chèn panel của selectedId; `machines_tab.dart` chỉ nếu cần callback panel, không đổi claim. Không sửa cloud_client/navigation/machine_service A-01/A-02; nếu thiếu API báo Planner. Tests `flutter_app/test/live_status/`.

## Input/output / UI

relay-status.md. Mỗi Làm mới UUIDv4 mới, instruction duy nhất, data={}; nguồn 'Máy trả lời', serial/version/uptime/sequence + received_at 'Server nhận lúc', không ghi 'Máy đo lúc'. State idle/loading/success/machineError/relayError. Chọn máy khác invalidate in-flight generation/clear success; new refresh clear fresh-result label. Accept response only request_id/machine_id đúng current generation; old result bỏ dù mounted. Không fallback MACHINE_STATUS_GET/list.online/cached result. Optional retry dùng cùng ID với retry=true; REQUEST_GONE chỉ có nút tạo lượt mới, không âm thầm đo mới.

## Thứ tự và lỗi

Service→panel→selected state binding→error messages→widget tests. MACHINE_OFFLINE hiện chưa có đường cloud, MACHINE_TIMEOUT máy chưa trả trong hạn, machineError ghi máy trả lỗi, AUTH_FAILED/SESSION_EXPIRED xử lý qua shared auth. Busy disable refresh khi một call in-flight; đổi máy vẫn bỏ old result. Network drop không coi máy chưa đọc; báo chưa nhận được đáp án và cho Làm mới. Retry HTTP do auth refresh chỉ nếu relay contract xác định same ID/retry=true; không fresh retry.

## Ca / cách kiểm

Mock service trả độc lập: refresh ID khác mỗi lần; click/selection race result cũ không render; offline/timeout xóa nhãn success; máy lỗi phân biệt relay; received_at không máy clock; list.online true nhưng máy timeout vẫn error; auth refresh không đổi ID phép đo; unknown source/malformed result không success. `flutter test test/live_status`; analyze file đổi. I-01 app thật status traffic→máy read_sequence thay đổi, tắt mạng máy→offline/timeout đúng.
