# Thiết kế đã chốt

## Tài liệu người dùng và hồ sơ nội bộ

- Người dùng chỉ cần vài file HTML theo `agent_workspace/PHASE_FORMAT.md`.
  Giữ các trang tổng quan, kiến trúc và quyết định chính; không sinh HTML cho từng phase.
- Trang kiến trúc phải có bản đồ feature thực tế từ service/app/máy và sơ đồ khối
  từng luồng: cửa vào, dữ liệu, kiểm tra, kho lưu, tác động, kết quả và nhánh lỗi.
  Chi tiết hệ thống người dùng cần duyệt đặt trong HTML, có mục lục và phần mở rộng.
- Trạng thái hiện tại và đề xuất tách rõ; biểu đồ theo hai manual tham chiếu,
  có nhãn/mũi tên/chú giải, Phóng to/Mã nguồn, mở offline và in được.
- Kế hoạch hiển thị một sơ đồ tiến độ ngay trong trang tổng quan: ✓ đã qua review
  và kiểm, ✗ lỗi/chưa đạt kèm chú thích, → đang làm, ○ chưa làm, ⏸ chờ/phụ thuộc.
  Chi tiết điều phối, nghiên cứu, thảo luận và bằng chứng vẫn là Markdown nội bộ.
- Không bịa kết quả, số đo hoặc tuyên bố đã đối chiếu mẫu chưa đọc được.

## Quy trình đã thống nhất — 06/10/2026

1. Người dùng nêu ý tưởng; operator giao hai architect độc lập đề xuất, phản biện
   trực tiếp qua các lượt trao đổi, ghi phương án/đánh đổi và giải quyết vấn đề chặn.
2. Operator hợp nhất thiết kế; dựng HTML chi tiết để người dùng sửa và chốt.
   Hai agent đồng thuận không thay cho người dùng chốt thiết kế.
3. Sau khi người dùng chốt, gọi planner chia phase nhỏ theo phụ thuộc và đầu ra
   kiểm được; không tách cơ học tới mức tăng bàn giao vô ích. Operator review plan.
4. Một coder làm từng bước của plan; một reviewer độc lập kiểm diff và bằng chứng.
   Có lỗi thì sửa/kiểm lại trước khi mở bước phụ thuộc.
5. Operator cập nhật sơ đồ plan ✓/✗ và chú thích ngay sau mỗi lượt; giữ lịch sử lỗi
   và cách sửa trong Markdown. Chỉ hoàn tất khi điều kiện nghiệm thu có bằng chứng.

Chi tiết vai, quyền và cổng bàn giao ở `agent_workspace/TEAM.md`.

## Quy ước kiến trúc

Người dùng đã yêu cầu khóa thiết kế hiện tại. Quy ước chi tiết nằm trong
[MODULE_PATTERN.md](MODULE_PATTERN.md). Chỉ thay kiến trúc hoặc quy ước đặt tên
khi người dùng yêu cầu thay đổi đó; các sửa lỗi và bổ sung tính năng thông thường
tiếp tục theo cấu trúc dưới đây.

- Biến routing theo `đối_tượng_lớn_mục_tiêu_chính_hành_động`: Python
  `MACHINE_MENU_UPDATE`, Dart `machineMenuUpdate`; path tiếng Anh cùng thứ tự
  `/<app|machine>/<đối_tượng>/<mục_tiêu>/<hành_động>`: `/app/machine/menu/update`.
  Chi tiết trong MODULE_PATTERN.md.
- Route HTTP nằm trong `server/config/routing.py`, chia nhóm bằng comment.
- `server/main.py` import trực tiếp các module và mặc định chạy toàn bộ.
  Không thêm registry import động hoặc cơ chế chọn/tháo module.
- Mỗi tính năng giữ nghiệp vụ, kiểm tra, cấu hình và truy vấn riêng trong folder
  hiện tại. Không import nội bộ của tính năng khác.
- File tính năng Python dùng `đối_tượng_thành_phần_hành_động.py`, snake_case tiếng Anh:
  `machine_share_main.py`, `machine_share_create.py`, `machine_share_accept.py`,
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

- Hàm nhiều module dùng tương đồng đặt trong `server/lib`; helper chỉ dùng chung
  nội bộ một module giữ trong module đó. Ghi bước rõ trong luồng xử lý,
  dùng helper lib cho cơ chế chung. Dashboard_sync đã rework cả menu, kho và danh sách máy.

- Menu_sync phía server làm phẳng: main/get/update; mỗi luồng trong một file,
  validate đặt cùng file, thứ tự bước ghi bằng comment. Không ép mỗi bước thành file.

- Cửa vào menu_sync là `machine_menu_main.py` → `handle(request)`.

- Ingredient_sync phía server: `machine_ingredient_main.py` → get/refill.
- Machinelist_sync phía server: `machine_list_main.py` → get/rename/remove;
  cửa vào có `handle(request)` cho POST và `handle_get(request)` cho trạng thái GET.
- Mỗi luồng giữ kiểm tra và SQL riêng tại file tác vụ; quyền/phiên/heartbeat dùng
  helper chung. Gỡ máy giữ `BEGIN IMMEDIATE` trước khi đọc quyền.

- Machine_share đã chốt: cửa vào `machine_share_main.py`, các tác vụ create/accept/list/revoke
  giữ kiểm tra và nghiệp vụ; SQL/schema ở `server/database/machine`.
  `init_db` khởi tạo bảng mã mời; transaction do tác vụ điều phối qua cùng conn.

- Machine_register: cửa vào `machine_register_main.py`, nghiệp vụ/transaction trong
  `machine_register_process.py`; SQL tạo máy/gán chủ ở database/machine/machine_write.py.

- Machine_link: `machine_link_main.py` là cửa vào HTTP, process điều phối ba tác vụ;
  hộp thư/heartbeat/timeout dùng chung giữ trong lib/machine/machine_transport.py.

- Cửa vào HTTP user_login/user_register dùng hậu tố main; giữ nghiệp vụ hiện tại.
