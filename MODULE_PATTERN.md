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

## Giao diện với server

| Thành phần | Hợp đồng |
| --- | --- |
| `ROUTES` | Các route POST của module; server kiểm tra trùng route trước khi khởi động |
| `handle(request) -> bool` | Xử lý POST; trả False nếu route không thuộc module |
| `GET_ROUTES`, `handle_get(request)` | Tùy chọn, tương tự cho GET |
| `setup()` | Tùy chọn; khởi tạo/nâng cấp dữ liệu riêng, chạy lại an toàn |
| `tick()` | Tùy chọn; dọn trạng thái định kỳ |

`server/lib/http_json.py` cung cấp đọc/ghi JSON, giới hạn body và xử lý lỗi SQLite.
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
| `request` | Nhận/gửi yêu cầu hoặc khai bảng lệnh | `machine_menu_request.py` |
| `process` | Điều phối nghiệp vụ | `machine_share_process.py` |
| `manage` | Quản lý đối tượng: liệt kê, đổi tên, gỡ | `machine_list_manage.py` |
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
    machine_share_request.py
    machine_share_process.py
    machine_share_store.py
    machine_share_schema.sql

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
| `machine_register` | Kiểm tra gói, transaction đăng ký và SQL tạo máy/gán chủ trong `machine_register_store.py` |
| `machine_share` | Quy tắc mời, hạn mã, SQL mã mời/nhân viên, `machine_share_schema.sql`, hook `setup` |
| `dashboard_sync/machinelist_sync` | Kiểm tra, danh sách/đổi tên/gỡ máy, SQL riêng trong `machine_list_store.py` |
| `dashboard_sync/menu_sync` | Quyền Menu, kiểm gói Menu, tạo lệnh Menu và trả kết quả |
| `dashboard_sync/ingredient_sync` | Quyền Kho/nạp Kho, kiểm gói Kho, tạo lệnh Kho và trả kết quả |
| `machine_link` | Xác minh máy và HTTP heartbeat/hỏi lệnh/trả kết quả |

Tên thư mục hiện tại được giữ để tránh trộn đổi tên với thay đổi ranh giới trách nhiệm.

## Những tài nguyên thực sự dùng chung

| Tài nguyên | Giao diện | Vì sao dùng chung |
| --- | --- | --- |
| Phiên tài khoản | `server/lib/session.py` | Một token dùng cho mọi tính năng; tắt login không làm mất phiên đang có |
| Mật khẩu | `server/lib/passwords.py` | Đăng ký và đăng nhập phải dùng cùng định dạng băm |
| Tài khoản, máy, quyền quản lý | `server/database/` | Cùng một danh tính và quyền trên toàn hệ thống |
| Kết nối SQLite | `server/database/connection.py` | Transaction, commit/rollback và foreign key thống nhất |
| Tra quyền từ token/máy | `server/lib/machine_access.py` | Cơ chế chung; danh sách vai trò được phép do từng module giữ |
| Hộp thư lệnh và heartbeat | `server/lib/machine_transport.py` | Máy long-poll một chỗ; các tính năng gửi qua cùng kết nối máy |
| HTTP JSON, rate limit | `server/lib/` | Cơ chế vận chuyển và giới hạn request dùng chung |

Các file dùng chung không import `server.service`. Không đưa quy tắc riêng của
một tính năng vào `lib` chỉ để giảm số dòng ở module.
SQL dùng riêng nằm trong module; thao tác danh tính/quyền dùng chung vẫn ở database.
Bảng `machine_invites` do hook setup của module chia sẻ khởi tạo. Các bảng tài khoản,
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
