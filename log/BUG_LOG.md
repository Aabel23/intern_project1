# Báo cáo sửa lỗi — androidv0.1

Mỗi lần sửa một báo cáo nhỏ. **Đổi logic/flow** = hành vi với đầu vào hợp lệ có thay đổi hay không
(nếu "Có" thì cần anh/chị duyệt, có thể hoàn tác). Kiểm chứng theo mã luồng trong `log/FLOWS.md`.
Lỗ hổng bảo mật chưa sửa: `SECURITY_NOTES.md`. Tất cả **chưa commit**.

## 2026-09-28

### B1 · Máy bị thu hồi/gỡ vẫn nằm trong danh sách app
- **Lỗi:** chủ thu hồi quyền, nhưng app nhân viên vẫn hiện máy; bấm vào chỉ nhận "Bạn không quản lý máy này".
  `loadMyMachines` chỉ *thêm* máy, không bỏ; kéo tải lại tab Máy chỉ gọi `refreshStatuses`.
- **Sửa:** `dashboard_controller.dart` lấy danh sách server làm chuẩn, xóa máy mất và bỏ chọn nếu máy đang chọn đã mất;
  `machines_tab.dart` kéo tải lại gọi `loadMyMachines`.
- **Đổi logic/flow:** Không (sửa cho đúng hành vi mong đợi).
- **Kiểm chứng:** F3 (test mới), E12 (e2e mới), toàn bộ E0–E12 ĐẠT.

### B2 · Máy offline thì tab Sản phẩm/Kho báo "chưa có món/nguyên liệu"
- **Lỗi:** chọn máy offline thì không tải gì, tab trống trông như máy không có dữ liệu.
- **Sửa:** `selectMachine` luôn tải; server trả "Máy đang offline" ngay nên tab hiện đúng lỗi. Trạng thái các máy hỏi song song.
- **Đổi logic/flow:** Nhỏ: có thêm 2 request khi chọn máy offline (trả lỗi ngay, không chờ).
- **Kiểm chứng:** F3, E3.

### B3 · `/app/gui-lenh` chuyển mọi lệnh xuống máy
- **Lỗi:** không có bảng quyền như `/app/dong-bo` và `/machine/refill`; `ten` bất kỳ (kể cả `null`) và
  `thamso` không phải object đều xuống máy.
- **Sửa:** bảng `QUYEN_LENH` (`sync_rules.py`) gồm đúng 7 lệnh máy đang hỗ trợ, owner + manager như trước;
  lệnh ngoài bảng trả 403, `thamso` sai kiểu trả 400.
- **Đổi logic/flow:** **Có, cần duyệt.** Lệnh lạ trước đây xuống máy rồi máy trả `{"loi": "Lenh khong hop le"}` (HTTP 200),
  giờ server chặn (HTTP 403). App hiện không gửi lệnh lạ nên người dùng không thấy khác.
- **Kiểm chứng:** S8, X1.

### B4 · Màn pair Bluetooth hiện toàn bộ product key
- **Lỗi:** key (thông tin xác thực của máy, xem SEC-02) hiện dạng chọn/copy được.
- **Sửa:** chỉ hiện `••••` + 4 ký tự cuối.
- **Đổi logic/flow:** Không (chỉ hiển thị).
- **Kiểm chứng:** F7, E2.

### B5 · Đăng ký được tài khoản không bao giờ đăng nhập được
- **Lỗi:** đăng ký không giới hạn độ dài; đăng nhập từ chối username > 150 hoặc mật khẩu > 1024.
- **Sửa:** `user_verify.py` dùng cùng giới hạn (username/họ tên ≤ 150, mật khẩu ≤ 1024, email ≤ 254).
- **Đổi logic/flow:** Không (chỉ chặn trường hợp vốn đã hỏng).
- **Kiểm chứng:** S2.

### O1 · Máy nhận lệnh bằng long-poll (tối ưu)
- **Trước:** máy hỏi `/machine/hoi-lenh` mỗi giây: lệnh chờ thêm tới 1s, máy rảnh vẫn 1 request/giây.
- **Sửa:** server giữ request tối đa 8s (`POLL_WAIT_SECONDS`), trả ngay khi có lệnh; máy hỏi lại ngay nếu
  server đã giữ, server cũ thì vẫn chờ 1s (tương thích hai chiều).
- **Đổi logic/flow:** **Có, cần duyệt** (cách máy và server trao đổi, giao thức JSON giữ nguyên).
- **Kiểm chứng:** S1 (test mới: lệnh tới máy < 2s), S8, E3–E12.

### T1 · E2E không chạy khi điện thoại và laptop khác access point
- **Lỗi:** app kẹt ở đăng nhập; điện thoại ("NartAnh 5G") không tới được laptop ("NartAnh 5G 3").
- **Sửa:** `run_e2e.py` mặc định qua cáp (`adb reverse`), `--wifi` giữ cách cũ; cài APK khác chữ ký thì gỡ rồi cài lại.
- **Đổi logic/flow:** Không (chỉ công cụ test).
- **Kiểm chứng:** E0.

### T2 · Cài lại app thì hộp thoại quyền Bluetooth chặn e2e
- **Sửa:** `run_e2e.py` cấp sẵn quyền bằng `pm grant`.
- **Đổi logic/flow:** Không (chỉ công cụ test).
- **Kiểm chứng:** E2 ĐẠT sau khi cài mới.

### T3 · Bộ chạy theo luồng + kịch bản tấn công
- **Thêm:** `test.ps1`, danh sách luồng S/X/A/F/E trong `sandbox/check_all.py`, bảng `log/FLOWS.md`,
  `run_e2e.py --until Ex`, tự build APK khi code app đổi; `server/test_security.py` (X1) cho `SECURITY_NOTES.md`.
- **Đổi logic/flow:** Không (chỉ công cụ test).
- **Kiểm chứng:** lần chạy `20260928-003326` toàn bộ 29 luồng ĐẠT; X1 ĐẠT (6 lỗ hổng đã biết).
