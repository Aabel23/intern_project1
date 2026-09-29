# Thiết kế module và quy ước đặt tên

Thiết kế này được chốt theo yêu cầu người dùng. Các lần sửa sau giữ cấu trúc và
quy ước này, trừ khi người dùng yêu cầu thay đổi thiết kế.

Nguyên tắc: mỗi module sở hữu ánh xạ route, gói tin, kiểm tra đầu vào, nghiệp vụ,
cấu hình riêng và truy vấn riêng; các đường dẫn HTTP được cấu hình tập trung. Module không import code của tính năng khác.
Thay nội bộ một module chỉ cần giữ hợp đồng đầu vào/đầu ra và dữ liệu dùng chung.

## Routing và khởi động

`server/config/routing.py` giữ các đường dẫn HTTP, chia nhóm theo tính năng bằng comment.
Module import các hằng route và tự ánh xạ sang hàm xử lý trong `ROUTES`.
`server/main.py` import trực tiếp các module và đăng ký trong tuple `MODULES`;
mặc định luôn chạy toàn bộ. Không có registry import động hay tùy chọn chọn module.

```sh
python -m server.main
python -m server.main --port 8001
```

Thêm tính năng: thêm hằng vào routing, viết module rồi import/đăng ký ở main.

## Tên biến routing

Dùng tiếng Anh theo thứ tự `<đối_tượng_lớn>_<mục_tiêu_chính>_<hành_động>`.
Đối tượng là miền nghiệp vụ (`USER`, `MACHINE`), mục tiêu là dữ liệu hoặc tác vụ
(`MENU`, `OTP`, `STAFF`), hành động đứng cuối (`GET`, `UPDATE`, `SEND`, `VERIFY`).
Không dùng `APP` làm đối tượng chỉ vì app gọi route. GET/UPDATE diễn tả nghiệp vụ,
không bắt buộc trùng HTTP method; route lấy menu hiện vẫn dùng POST.

Python dùng UPPER_SNAKE_CASE; Dart dùng lowerCamelCase với cùng thứ tự ý nghĩa:

| Python | Dart | Ý nghĩa |
| --- | --- | --- |
| `MACHINE_MENU_GET` | `machineMenuGet` | Lấy menu từ máy |
| `MACHINE_MENU_UPDATE` | `machineMenuUpdate` | Cập nhật giá/trạng thái món trong menu |
| `USER_OTP_SEND` | `userOtpSend` | Gửi OTP cho người dùng |
| `MACHINE_STAFF_REVOKE` | `machineStaffRevoke` | Thu hồi quyền nhân viên |

`MACHINE_MENU_UPDATE` dùng `/app/cap-nhat-menu`; lệnh máy là `cap_nhat_menu`.
Đây là thao tác cập nhật món, không phải đường gửi phản hồi của thao tác lấy menu.
Các bên app/server/machine phải cập nhật đồng thời khi đổi URL hoặc tên lệnh.

## Giao diện với server

| Thành phần | Hợp đồng |
| --- | --- |
| `ROUTES` | Các route POST của module; server kiểm tra trùng route trước khi khởi động |
| `handle(request) -> bool` | Xử lý POST; trả False nếu route không thuộc module |
| `GET_ROUTES`, `handle_get(request)` | Tùy chọn, tương tự cho GET |
| `setup()` | Tùy chọn; khởi tạo/nâng cấp dữ liệu riêng, chạy lại an toàn |
| `tick()` | Tùy chọn; dọn trạng thái định kỳ |

`server/lib/http/http_json.py` cung cấp đọc/ghi JSON, giới hạn body và xử lý lỗi SQLite.
Module tự chọn giới hạn body, kiểm tra gói tin và quyết định kết quả.
Route lấy từ `server/config/routing.py`. Flow đăng nhập cũng dùng cùng hằng khi trả route xác minh cho app.

## Bên trong module

Không bắt buộc đủ bộ `request / process / validate / store`, không bắt buộc số file.
Giữ các hàm liên quan gần nhau. Tách file khi một phần đủ lớn hoặc có trách nhiệm
riêng thực sự. Một helper kiểm tra nhỏ có thể nằm ngay trong flow.

## Đặt tên file tính năng

Dạng chung: `<đối_tượng>_<thành_phần>_<hành_động>.py`, snake_case tiếng Anh.
Đối tượng là thứ được xử lý (`user`, `machine`); thành phần là tính năng hoặc
dữ liệu (`login`, `register`, `share`, `menu`, `ingredient`, `otp`); phần cuối
nói việc chính file thực hiện. Server và máy dùng cùng tên cho cùng trách nhiệm,
vị trí thư mục cho biết nơi chạy.

| Phần cuối | Trách nhiệm | Ví dụ |
| --- | --- | --- |
| `request` | Nhận/gửi yêu cầu hoặc khai bảng lệnh | `machine_menu_request.py` (phía máy) |
| `process` | Điều phối nghiệp vụ | `user_login_process.py` |
| `main` | Cửa vào HTTP, chọn luồng nghiệp vụ | `machine_list_main.py` |
| `sync` | Đồng bộ dữ liệu | `machine_menu_sync.py` |
| `validate` | Kiểm dữ liệu | `user_register_validate.py` |
| `store` | Đọc/ghi dữ liệu | `machine_share_store.py` |
| `pack` | Đóng gói/encode dữ liệu | `machine_menu_pack.py` |
| `generate`, `send` | Sinh/gửi mã | `user_otp_generate.py`, `user_otp_send.py` |
| `pair`, `serve` | Ghép đôi, nhận kết nối Bluetooth | `machine_bluetooth_pair.py`, `machine_bluetooth_serve.py` |
| `heartbeat` | Báo máy còn hoạt động | `machine_server_heartbeat.py` |

Schema riêng dùng `<đối_tượng>_<thành_phần>_schema.sql`, ví dụ
`machine_share_schema.sql`. Test dùng `test_<đối_tượng>_<thành_phần>.py` để
công cụ unittest nhận diện, ví dụ `test_machine_share.py`.

```text
server/service/machine_share/
    machine_share_main.py
    machine_share_create.py
    machine_share_accept.py
    machine_staff_list.py
    machine_staff_revoke.py

machine/menu_sync/
    machine_menu_request.py
    machine_menu_sync.py
    machine_menu_validate.py
    machine_menu_store.py
    machine_menu_pack.py
```

Tên nền tảng `main.py`, `config.py`, `routing.py`, `__init__.py` và helper chung
giữ ngắn theo vai trò. Không đổi tên hàm, route hay trường gói tin chỉ để khớp tên file.

Hiện tại:

| Module | Nội dung tự sở hữu |
| --- | --- |
| `user_login` | Ánh xạ route, xác minh thông tin, trạng thái đăng nhập hai bước trong `user_login_process.py` |
| `user_register` | Dữ liệu đăng ký, OTP, gửi mail và cấu hình SMTP trong `otp/user_otp_send.py` |
| `machine_register` | Cửa vào main, kiểm tra gói và transaction trong process; SQL tạo máy/gán chủ ở database/machine/machine_write.py |
| `machine_share` | Quy tắc mời, hạn mã và điều phối quyền; SQL/schema ở `server/database/machine` |
| `dashboard_sync/machinelist_sync` | Cửa vào main; kiểm tra và SQL riêng trong get/rename/remove |
| `dashboard_sync/menu_sync` | Hai file luồng lấy/cập nhật menu; main là cửa vào HTTP |
| `dashboard_sync/ingredient_sync` | Quyền Kho/nạp Kho, kiểm gói Kho, tạo lệnh Kho và trả kết quả |
| `machine_link` | Cửa vào machine_link_main; process xác minh máy và điều phối heartbeat/hỏi lệnh/trả kết quả qua transport chung |

Tên thư mục hiện tại được giữ để tránh trộn đổi tên với thay đổi ranh giới trách nhiệm.

## Những tài nguyên thực sự dùng chung

| Tài nguyên | Giao diện | Vì sao dùng chung |
| --- | --- | --- |
| Phiên tài khoản | `server/lib/security/user_session.py` | Một token dùng cho mọi tính năng; tắt login không làm mất phiên đang có |
| Mật khẩu | `server/lib/security/user_password.py` | Đăng ký và đăng nhập phải dùng cùng định dạng băm |
| Tài khoản, máy, quyền quản lý | `server/database/` | Cùng một danh tính và quyền trên toàn hệ thống |
| Kết nối SQLite | `server/database/connection.py` | Transaction, commit/rollback và foreign key thống nhất |
| Tra quyền từ token/máy | `server/lib/machine/machine_access.py` | Cơ chế chung; danh sách vai trò được phép do từng module giữ |
| Hộp thư lệnh và heartbeat | `server/lib/machine/machine_transport.py` | Máy long-poll một chỗ; các tính năng gửi qua cùng kết nối máy |
| HTTP JSON, rate limit | `server/lib/` | Cơ chế vận chuyển và giới hạn request dùng chung |

Các file dùng chung không import `server.service`. Không đưa quy tắc riêng của
một tính năng vào `lib` chỉ để giảm số dòng ở module.
SQL dùng riêng nằm trong module; thao tác danh tính/quyền dùng chung vẫn ở database.
Bảng `machine_invites` do `server/database/machine/init_db.py` khởi tạo từ `machine_share_schema.sql`. Các bảng tài khoản,
phiên, máy và quyền được khởi tạo chung trước hook `setup` của module.

Độc lập ở đây là giữ nghiệp vụ trong module và giảm import nội bộ giữa các tính năng.
Thay giao thức app/máy, đổi schema chung hay sửa cơ chế xác thực vẫn cần kiểm tra
các bên sử dụng hợp đồng đó. Toàn bộ module được chạy cùng server.
Trạng thái OTP, đăng nhập đang chờ và hộp thư thuộc một tiến trình; chưa hỗ trợ
chia tải chúng sang nhiều worker hoặc thay code nóng khi server đang chạy.

## Kiểm tra

```sh
python -m unittest tests.python.test_server_modules
.\tests\test.ps1 -Flow S9
.\tests\test.ps1 -Flow py
```

`tests.python.test_server_modules` kiểm route trùng và xác nhận khởi động lại server vẫn giữ dữ liệu.
Test HTTP liên tính năng nằm ở `tests/python/test_server.py`; test nghiệp vụ từng module dùng SQLite tạm.

Các gói HTTP hiện có được giữ: nhóm tài khoản/máy trả `{valid, message, ...}`;
Menu/Kho/cổng máy dùng `{loi: ...}` khi lỗi và `(body, status)` trong flow.
Chuẩn hóa hai dạng này là thay đổi hợp đồng cần làm cùng app.

## Phía máy

`machine/main.py` tra bảng `COMMANDS` của từng module theo `instruction`.
Module tự kiểm gói, thực hiện tác vụ và trả kết quả; tách validate/store/pack
chỉ khi giúp đọc và bảo trì. Máy không nhận token app; server kiểm quyền trước
khi gửi lệnh. Các thao tác ghi nhiều dòng giữ cùng một transaction.

Toàn bộ code kiểm thử nằm trong `tests/`, chia theo Python, Flutter và E2E. Module nghiệp vụ không chứa test.

## Ranh giới app Flutter

Quy ước app ở `app/flutter_app/README.md`. `lib/app` lắp ghép điều hướng;
`config` giữ route, `core` giữ transport/gói tin, `shared/ui` giữ widget dùng chung.
Mỗi feature có request/state/ui riêng. Dashboard lắp ghép các feature, không giữ
request nghiệp vụ của chúng; Auth và dashboard giao tiếp qua callback từ app.
Không thêm các tầng rỗng chỉ để đồng đều cấu trúc.

## Cấu trúc menu_sync

Riêng menu_sync phía server làm phẳng thành `machine_menu_main.py`,
`machine_menu_get.py`, `machine_menu_update.py`. Mỗi luồng nằm trọn trong một file,
validate nằm cùng file, các bước ghi bằng comment. Không ép mỗi bước thành một file.
Chi tiết ở [README menu_sync](server/service/dashboard_sync/menu_sync/README.md).
Hàm nhiều module dùng tương đồng nằm trong lib.

## Nhóm lib dùng chung

Lib chia theo HTTP, security, machine và validation; chi tiết ở
[server/lib/README.md](server/lib/README.md). Không đánh số bước cho helper chung.

Startpoint menu_sync phía server: `machine_menu_main.py` → `handle(request)`.
File main nhận HTTP, chọn luồng lấy/cập nhật menu và trả response.

File cửa vào menu_sync dùng `<đối_tượng>_<tính_năng>_main.py`: `machine_menu_main.py`.
Các file nghiệp vụ giữ hậu tố tác vụ get/update; chỉ đổi module khác khi được yêu cầu.

## Cấu trúc các submodule dashboard còn lại

`machinelist_sync`: `machine_list_main.py` → `machine_list_get.py`,
`machine_list_rename.py`, `machine_list_remove.py`. Trạng thái heartbeat nằm trong
get; SQL riêng nằm cùng tác vụ. Kiểm quyền dùng `machine_read`, bỏ quyền nhân viên
dùng `machine_write.remove_manager`; gỡ máy giữ khóa ghi trước bước kiểm quyền.

`ingredient_sync`: `machine_ingredient_main.py` → `machine_ingredient_get.py`,
`machine_ingredient_refill.py`. Validate nằm trong từng file luồng; kiểm quyền và
gửi lệnh dùng lib chung. Server trả kết quả máy trên request app ban đầu.

Ngoại lệ đã chốt cho machine_share: module giữ kiểm tra/nghiệp vụ, SQL và schema
ở `server/database/machine`; transaction do tác vụ điều phối qua cùng conn.

Machine_register: `machine_register_main.py` → `machine_register_process.py`;
SQL tạo máy/gán chủ nằm trong `server/database/machine/machine_write.py`.

Cửa vào HTTP của user_login/user_register dùng `user_login_main.py` và
`user_register_main.py`; nghiệp vụ và trạng thái vẫn giữ trong process.
