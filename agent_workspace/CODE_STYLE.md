# Quy ước code và chuẩn chất lượng

Mọi vai đọc file này trước khi viết, test hoặc review code. Mục đích là để các phiên khác nhau cho ra code giống nhau. Kiến trúc và tên file do `../AGENTS.md` và `../MODULE_PATTERN.md` quyết định; file này không thay hai file đó. Khi file này mâu thuẫn với code đã chốt, code đã chốt thắng; báo lead để sửa file này.

Ví dụ chuẩn để đối chiếu:
- Luồng nghiệp vụ: `server/service/dashboard_sync/menu_sync/machine_menu_update.py`
- Helper dùng chung: `server/lib/http/http_json.py`
- Test module: `tests/python/test_machine_share.py`
- Request Flutter: `app/flutter_app/lib/feature/machine_menu/machine_menu_request.dart`

## 1. Nguyên tắc chung

1. **Viết giống code xung quanh.** Trước khi viết, đọc ít nhất một file anh em cùng module. Theo tên, mật độ comment, cách trả lỗi của file đó.
2. **Thay đổi nhỏ nhất đủ đúng.** Không refactor, đổi tên, format lại hoặc "dọn" ngoài phạm vi task. Diff chỉ chứa dòng có lý do.
3. **Đơn giản hơn trừu tượng.** Không thêm class, factory, registry, lớp base hoặc config cho một chỗ dùng. Ba dòng lặp lại tốt hơn một helper sai chỗ.
4. **Không đoán hợp đồng.** Tên trường gói tin, route, lệnh máy và dạng lỗi lấy từ code hiện có, không tự chuẩn hoá.

### Luồng xử lý phẳng, bám plan

- Thực thi đúng bước/tiêu chí đã giao; không thêm nghiệp vụ, fallback hoặc abstraction
  ngoài plan. Plan thiếu quyết định thì báo operator, không tự đoán.
- Ưu tiên guard và thoát sớm; sau `return`/`raise`/`continue` không bọc phần còn lại
  bằng `else` thừa. Hạn chế `if/else` nhiều tầng; nhánh loại trừ nhau giữ dạng rõ nhất.
- Giữ đúng vòng đời tài nguyên, transaction/khóa, quyền và thứ tự tác động khi làm
  phẳng. Không chuyển nesting sang ternary/boolean khó đọc hay helper vụn.
- Tinh gọn bằng bỏ cơ chế thừa trong phạm vi task; không bỏ kiểm hoặc ép ít dòng.

### Khối chức năng và mini region trong file

- Mỗi file giữ một trách nhiệm chức năng chính theo MODULE_PATTERN và plan;
  nhiều hàm cùng trách nhiệm được ở chung. Không trộn tác vụ độc lập và không ép
  một bước thành một file. Cửa vào/hợp đồng rõ, không import nội bộ feature khác.
- Tham khảo `machine_menu_main.py` và `machine_menu_update.py` ở menu_sync hiện tại:
  cửa vào điều phối; file tác vụ nhóm cấu hình, kiểm giá trị/gói và luồng chính.
- Dùng chú thích tiếng Việt để chia các nhóm code liền nhau theo nhiệm vụ thật,
  ví dụ `# Cấu hình riêng`, `# Nhóm 1: kiểm giá trị`, `# Nhóm 2: luồng chính`;
  Dart dùng `//`. Chỉ tạo nhóm khi giúp đọc nội dung; không bắt buộc bộ region cố định.
- Luồng nghiệp vụ có comment bước liên hệ plan; comment quan trọng giải thích
  lý do/ràng buộc, điều kiện dừng, quyền, transaction và tác động. Helper chung
  giữ docstring theo vai trò, không ép đánh số bước như luồng nghiệp vụ.
- Không dùng region để che việc trộn trách nhiệm, không thêm comment/separator
  cho từng dòng hoặc sửa hàng loạt ngoài task. Việc tách file mới phải nằm trong
  plan và giữ ranh giới/hợp đồng đã chốt.

## 2. Python (server, machine, tests)

### Bố cục file
- Dòng đầu là docstring tiếng Việt, một câu, nói file làm gì và đầu vào → đầu ra. Ví dụ: `"""Cập nhật menu: JSON app → (kết quả máy hoặc lỗi, HTTP status)."""`
- Thứ tự: docstring → import → hằng cấu hình riêng → hàm kiểm nhỏ → luồng chính ở cuối.
- Import tuyệt đối từ gốc (`from server.lib.machine.machine_access import check_access`). Trong cùng package lib được dùng import tương đối. Nhóm import theo thư viện chuẩn → trong dự án; file có nhiều nhóm thì ghi comment nhóm như `# Thư viện chuẩn`, `# Trong lib`.
- Mỗi import một tên khi file hiện có làm vậy (xem test). Không `import *`.

### Tên
- Hàm, biến: snake_case. Hằng module: UPPER_SNAKE_CASE, đặt đầu file kèm comment nói vì sao có giới hạn đó.
- Tên route theo `ĐỐI_TƯỢNG_MỤC_TIÊU_HÀNH_ĐỘNG` (`MACHINE_MENU_UPDATE`).
- Hàm kiểm trả bool đặt `is_<thứ>` (`is_price`, `is_changes`).
- Code mới dùng tên tiếng Anh. Tên tiếng Việt đã có trong code hoặc gói tin (`thay_doi`, `loi`, `cap_nhat_menu`, `QUYEN_MENU`) giữ nguyên; không đổi tên chỉ để thống nhất ngôn ngữ.

### Comment và docstring
- Comment, docstring viết tiếng Việt có dấu.
- Luồng chính đánh dấu bước bằng comment `# Bước 1: ...`, `# Bước 2: ...`; mỗi bước nói làm gì và điều gì khiến dừng. Helper trong `server/lib` không đánh số bước.
- Comment giải thích **vì sao** hoặc điều không hiển nhiên (ví dụ `bool` là lớp con của `int`), không diễn lại dòng code.
- Helper dùng chung có docstring nêu giá trị trả về và các trường hợp `None`/ngoại lệ.

### Kiểm đầu vào
- Coi mọi trường từ app/máy là không tin cậy. Kiểm kiểu chính xác, loại `bool` khỏi số, giới hạn độ dài/khoảng giá trị, từ chối trường lạ.
- Kiểm phiên và quyền **trước** khi kiểm nội dung; trả lỗi ngay khi sai (`if error: return error`).
- Một phần tử sai thì từ chối cả gói; không sửa ngầm dữ liệu sai.

### Lỗi và gói trả về
- Giữ đúng dạng của module: nhóm tài khoản/máy trả `{valid, message, ...}`; Menu/Kho/cổng máy trả `{"loi": ...}` khi lỗi và `(body, status)` trong flow.
- Thông báo lỗi cho người dùng viết tiếng Việt, ngắn, không lộ SQL, đường dẫn, stack trace hay token.
- Chỉ bắt ngoại lệ cụ thể (`except (ValueError, TimeoutError)`); không `except Exception` hay `except:` trơn trừ khi ở ranh giới và có comment lý do.

### Database
- Luôn dùng `get_connection()` từ `server/database/connection.py` và tham số `?`; không ghép chuỗi vào SQL.
- Thao tác ghi nhiều dòng nằm trong một transaction; luồng đọc-rồi-ghi quyền dùng `BEGIN IMMEDIATE` như module gỡ máy.
- SQL riêng của tính năng nằm trong module đó; SQL danh tính/quyền dùng chung ở `server/database/`.

### Bảo mật và log
- Không log hoặc trả token, mật khẩu, OTP, payload QR. Token chỉ dùng ở server, không gửi xuống máy.
- So sánh bí mật bằng `hmac.compare_digest`.

### Định dạng
- Thụt 4 dấu cách. Dòng tối đa khoảng 120 ký tự như code hiện có.
- Không thêm type hint hàng loạt vào file chưa dùng; file đã dùng thì giữ.
- Không có formatter bắt buộc: không chạy black/ruff --fix lên cả file vì sẽ tạo diff ngoài phạm vi.

## 3. Dart / Flutter

- Lint theo `app/flutter_app/analysis_options.yaml` (`flutter_lints`). Thay đổi Dart phải qua `flutter analyze` không thêm cảnh báo mới.
- Format theo `dart format` chỉ trên file đã sửa.
- Tên file snake_case theo `<đối_tượng>_<thành_phần>_<vai>.dart` (`machine_menu_request.dart`); class UpperCamelCase; hàm, biến, route lowerCamelCase (`Routes.machineMenuUpdate`).
- Request của feature viết dạng `extension ... on ServerClient` trong `<feature>_request.dart`; state ở `<feature>_sync.dart`; widget ở `ui/`.
- Import bằng `package:simple_app/...`. Feature không import feature khác; chỉ dashboard lắp ghép. Auth và dashboard không import nhau.
- Tên trường JSON giữ nguyên như server (`'thay_doi'`, `'menu_version'`).
- Chuỗi giao diện tiếng Việt có dấu.

## 4. Test

- Đặt trong `tests/`; tên `test_<đối_tượng>_<thành_phần>.py`; dùng `unittest`.
- Mỗi test dùng SQLite tạm: `tempfile.TemporaryDirectory()` + `patch('server.database.connection.DB_PATH', ...)`, dọn bằng `addCleanup`. Không dùng DB thật, mạng ngoài, cổng cố định hoặc `sleep` để chờ.
- Tên test nói hành vi: `test_staff_cannot_revoke_owner`, không phải `test_1`.
- Mỗi test kiểm một hành vi; assert trên kết quả quan sát được (gói trả về, status, dòng DB), không trên chi tiết nội bộ.
- Giá trị mong đợi viết cứng từ yêu cầu, không tính lại bằng chính code đang kiểm.
- Bắt buộc có test cho đường lỗi quan trọng: thiếu quyền, gói sai, phiên hết hạn, rollback.
- Thêm file test mới thì cập nhật `tests/run_tests.py`.

## 5. Checklist trước khi bàn giao

Coder tự kiểm, reviewer kiểm lại. Mục nào không áp dụng thì ghi "không áp dụng".

- [ ] Diff chỉ chứa thay đổi thuộc task; không format lại hoặc đổi tên ngoài phạm vi.
- [ ] Bám tiêu chí của bước plan; luồng phẳng, không else thừa sau nhánh kết thúc,
  không nesting/abstraction ngoài nhu cầu và không đổi vòng đời tài nguyên.
- [ ] Tên file, route, hàm theo `MODULE_PATTERN.md` và mục 2–3 ở trên.
- [ ] Không import chéo giữa tính năng; `server/lib` không import `server.service`.
- [ ] File có một trách nhiệm chính; nhóm code/mini region hợp lý, comment nêu
  ràng buộc quan trọng và khớp các bước plan, không tách vụn hoặc trộn tác vụ.
- [ ] Kiểm phiên/quyền trước nội dung; đầu vào được kiểm kiểu và giới hạn.
- [ ] Dạng lỗi và gói tin giữ đúng hợp đồng của module; bên gọi app/server/machine đã cập nhật nếu đổi.
- [ ] SQL có tham số; ghi nhiều dòng trong transaction.
- [ ] Không log hoặc trả bí mật.
- [ ] Comment tiếng Việt giải thích vì sao; luồng chính có `# Bước N:`.
- [ ] Có test cho hành vi mới và đường lỗi; test đã chạy, ghi lệnh và exit code.
- [ ] Dart: `flutter analyze` không thêm cảnh báo.

## 6. Mức độ khi review

Reviewer dùng cùng thang để các phiên báo giống nhau:

| Mức | Khi nào | Xử lý |
|---|---|---|
| **Chặn** | Sai chức năng, mất dữ liệu, lỗ hổng quyền/bảo mật, phá hợp đồng, test sai | Phải sửa trước khi xong |
| **Nên sửa** | Vi phạm quy ước file này hoặc `MODULE_PATTERN.md`, thiếu test đường lỗi, comment sai | Sửa trong task trừ khi lead ghi lý do |
| **Gợi ý** | Ý kiến về cách viết không vi phạm quy ước | Không bắt buộc; không báo nếu chỉ là sở thích |
