# Thiết kế đã chốt

Người dùng đã yêu cầu khóa thiết kế hiện tại. Quy ước chi tiết nằm trong
[MODULE_PATTERN.md](MODULE_PATTERN.md). Chỉ thay kiến trúc hoặc quy ước đặt tên
khi người dùng yêu cầu thay đổi đó; các sửa lỗi và bổ sung tính năng thông thường
tiếp tục theo cấu trúc dưới đây.

- Biến routing theo `đối_tượng_lớn_mục_tiêu_chính_hành_động`: Python
  `MACHINE_MENU_UPDATE`, Dart `machineMenuUpdate`. Chi tiết trong MODULE_PATTERN.md.
- Route HTTP nằm trong `server/config/routing.py`, chia nhóm bằng comment.
- `server/main.py` import trực tiếp các module và mặc định chạy toàn bộ.
  Không thêm registry import động hoặc cơ chế chọn/tháo module.
- Mỗi tính năng giữ nghiệp vụ, kiểm tra, cấu hình và truy vấn riêng trong folder
  hiện tại. Không import nội bộ của tính năng khác.
- File tính năng Python dùng `đối_tượng_thành_phần_hành_động.py`, snake_case tiếng Anh:
  `machine_share_request.py`, `machine_share_process.py`, `machine_share_store.py`,
  `machine_menu_sync.py`, `user_login_process.py`.
- Test dùng `test_<đối_tượng>_<thành_phần>.py`. File nền tảng như `main.py`,
  `config.py`, `routing.py`, `__init__.py` và helper dùng chung giữ tên theo vai trò.
- Không bắt buộc số file hoặc đủ bộ request/process/validate/store; chỉ tách khi
  có trách nhiệm đủ rõ. Giữ code đơn giản và dùng tài nguyên chung thực sự cần thiết.
- Phiên, danh tính/quyền máy, kết nối database và vận chuyển lệnh là tài nguyên
  dùng chung. Các helper chung không import `server.service`.
- Giữ transaction, kiểm quyền và hợp đồng gói tin khi refactor. Thay hợp đồng theo
  yêu cầu người dùng phải cập nhật các bên gọi và test liên quan cùng lúc.
- Kiểm tra phù hợp với thay đổi. Danh sách test Python hiện tại nằm trong
  `tests/run_tests.py`; chạy bằng `tests/test.ps1 -Flow py` hoặc unittest trực tiếp.

- Toàn bộ test và công cụ mô phỏng nằm trong `tests/`; không đặt test trong module nghiệp vụ.

- App Flutter theo `app/flutter_app/README.md`: `app` lắp ghép điều hướng,
  `config` giữ route, `core` giữ transport/gói tin, `shared/ui` giữ widget chung.
  Feature giữ request/state/ui riêng; chỉ dashboard lắp ghép feature khác.
  Auth và dashboard không import nhau. Test ranh giới ở `tests/python/test_app_boundaries.py`.
