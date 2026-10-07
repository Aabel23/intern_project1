# Intake trước planner — 07/10/2026

## Yêu cầu và trạng thái

Người dùng yêu cầu gọi planner đọc architect hiện tại và lập plan chi tiết nhiều
phase để bắt đầu dev, có cây thư mục và quy định module folder. Phạm vi theo task
middleware đang mở: server/app/máy/tests. Đây là cho phép lập plan; không suy ra
mọi lựa chọn production trong R5 đã được chốt hoặc đã giao coder triển khai.

Đã gọi Claude CLI `--agent planner --model opus --effort medium --permission-mode plan`
với công cụ chỉ đọc. CLI exit 1, `is_error=true`, 1 turn, không có modelUsage;
thông báo chạm monthly spend limit. Chưa nhận plan từ Opus. Operator đã hỏi người
 dùng về GPT planner cho lượt này hoặc chờ Opus; không tự thay model trước câu trả lời.

## Nguồn quyết định

- R5: `internal/packet-security/design.md`; HTML hiện hành: architecture.html và
  packet-security.html. Lộ trình HTTP G0–G7 và roadmap gói tin cũ là backlog lịch sử.
- Vai architect/planner/coder đã cập nhật về phân rã luồng, mapping khối/file,
  code phẳng, mini region và coder Sonnet medium/GPT Sol low. Planner vẫn Opus medium.
- AGENTS/MODULE_PATTERN khóa import trực tiếp, route constants và ranh giới feature;
  cây mới không được ngầm đổi mô hình module hoặc tạo registry.

## Các cổng có bằng chứng từ đọc mã hiện tại

| Cổng | Nguồn | Bằng chứng | Việc phải được plan giải quyết |
| --- | --- | --- | --- |
| C1 | `app/flutter_app/lib/feature/user_auth/user_login_request.dart:19–28`; `server/service/user_login/user_login_process.py:20–27`; `server/config/routing.py:10–12` | App gọi verify sau login; server trả token ngay và không có route verify | Dùng hợp đồng đăng nhập một bước hiện tại làm đầu vào cho sửa caller/fixture; không phục hồi API cũ chỉ để test pass. |
| C2 | `internal/packet-security/design.md:172–179`; `server/database/machine/machine_write.py:17–19` | Draft GET yêu cầu machine_id decimal; server cấp fm_UUID | Chốt query profile giữ opaque ID và GET wire adapter; cập nhật đặc tả/caller/tests cùng nhau trước rollout. |
| Nền kiểm | `tests/python/test_server_security.py:41,83`; `tests/python/test_server.py:57,239`; `TASK.md` mục tạm dừng/review thiết kế | Fixture còn dùng LOGIN_STATES, login_id/verify/tick cũ | Chạy baseline mới ở bước được giao, phân biệt fixture cũ với lỗi thật; số lỗi/timing trong TASK là lịch sử. |

Đã đọc/đối chiếu nguồn và có review read-only độc lập. Chưa sửa sản phẩm hoặc chạy
lại test ở lượt lập intake này. Production suite/library/time/keystore/persistence
vẫn cần bằng chứng và quyết định trong các phase có phụ thuộc.

## Cây file hiện trạng — danh sách được đọc từ filesystem

Các đường dẫn dưới đây có thật tại thời điểm intake; không phải cây module đề xuất.
Planner phải đánh dấu thêm/sửa/giữ trong cây đích và gắn từng thay đổi với phase.

### server/config

```text
server/config/config.py
server/config/path.py
server/config/routing.py
```

### server/lib

```text
server/lib/README.md
server/lib/http/__init__.py
server/lib/http/http_json.py
server/lib/http/http_rate_limit.py
server/lib/http/http_server.py
server/lib/machine/__init__.py
server/lib/machine/machine_access.py
server/lib/machine/machine_transport.py
server/lib/security/__init__.py
server/lib/security/data_hash.py
server/lib/security/user_password.py
server/lib/security/user_session.py
server/lib/validation/__init__.py
server/lib/validation/identifier_validate.py
server/lib/validation/state_expire.py
```

### server/database

```text
server/database/__init__.py
server/database/connection.py
server/database/machine/README.md
server/database/machine/__init__.py
server/database/machine/init_db.py
server/database/machine/machine_read.py
server/database/machine/machine_share_schema.sql
server/database/machine/machine_share_store.py
server/database/machine/machine_write.py
server/database/machine/schema.sql
server/database/user/README.md
server/database/user/__init__.py
server/database/user/schema.sql
server/database/user/user_add.py
server/database/user/user_read.py
```

### server/service

```text
server/service/README.md
server/service/dashboard_sync/README.md
server/service/dashboard_sync/ingredient_sync/README.md
server/service/dashboard_sync/ingredient_sync/__init__.py
server/service/dashboard_sync/ingredient_sync/machine_ingredient_get.py
server/service/dashboard_sync/ingredient_sync/machine_ingredient_main.py
server/service/dashboard_sync/ingredient_sync/machine_ingredient_refill.py
server/service/dashboard_sync/machinelist_sync/README.md
server/service/dashboard_sync/machinelist_sync/__init__.py
server/service/dashboard_sync/machinelist_sync/machine_list_get.py
server/service/dashboard_sync/machinelist_sync/machine_list_main.py
server/service/dashboard_sync/machinelist_sync/machine_list_remove.py
server/service/dashboard_sync/machinelist_sync/machine_list_rename.py
server/service/dashboard_sync/menu_sync/README.md
server/service/dashboard_sync/menu_sync/__init__.py
server/service/dashboard_sync/menu_sync/machine_menu_get.py
server/service/dashboard_sync/menu_sync/machine_menu_main.py
server/service/dashboard_sync/menu_sync/machine_menu_update.py
server/service/machine_link/README.md
server/service/machine_link/__init__.py
server/service/machine_link/machine_link_main.py
server/service/machine_link/machine_link_process.py
server/service/machine_register/README.md
server/service/machine_register/machine_register_main.py
server/service/machine_register/machine_register_process.py
server/service/machine_share/README.md
server/service/machine_share/__init__.py
server/service/machine_share/machine_share_accept.py
server/service/machine_share/machine_share_create.py
server/service/machine_share/machine_share_main.py
server/service/machine_share/machine_staff_list.py
server/service/machine_share/machine_staff_revoke.py
server/service/user_login/README.md
server/service/user_login/user_login_main.py
server/service/user_login/user_login_process.py
server/service/user_register/README.md
server/service/user_register/otp/README.md
server/service/user_register/otp/user_otp_generate.py
server/service/user_register/otp/user_otp_process.py
server/service/user_register/otp/user_otp_send.py
server/service/user_register/otp/user_otp_validate.py
server/service/user_register/user_register_main.py
server/service/user_register/user_register_process.py
server/service/user_register/user_register_store.py
server/service/user_register/user_register_validate.py
```

### app/flutter_app/lib

```text
app/flutter_app/lib/app/app_navigation.dart
app/flutter_app/lib/config/app_config.dart
app/flutter_app/lib/config/routing.dart
app/flutter_app/lib/core/http_json.dart
app/flutter_app/lib/core/machine_packet.dart
app/flutter_app/lib/core/server_client.dart
app/flutter_app/lib/feature/dashboard/dashboard_controller.dart
app/flutter_app/lib/feature/dashboard/ui/dashboard_page.dart
app/flutter_app/lib/feature/dashboard/ui/machine_qr_page.dart
app/flutter_app/lib/feature/dashboard/ui/machines_tab.dart
app/flutter_app/lib/feature/dashboard/ui/overview_tab.dart
app/flutter_app/lib/feature/machine_ingredient/machine_ingredient_request.dart
app/flutter_app/lib/feature/machine_ingredient/machine_ingredient_sync.dart
app/flutter_app/lib/feature/machine_ingredient/ui/machine_ingredient_tab.dart
app/flutter_app/lib/feature/machine_list/machine_list_request.dart
app/flutter_app/lib/feature/machine_menu/machine_menu_request.dart
app/flutter_app/lib/feature/machine_menu/machine_menu_sync.dart
app/flutter_app/lib/feature/machine_menu/ui/machine_menu_tab.dart
app/flutter_app/lib/feature/machine_register/machine_register_request.dart
app/flutter_app/lib/feature/machine_register/ui/machine_register_bluetooth_page.dart
app/flutter_app/lib/feature/machine_share/QR.md
app/flutter_app/lib/feature/machine_share/machine_share_request.dart
app/flutter_app/lib/feature/machine_share/ui/machine_share_bluetooth_page.dart
app/flutter_app/lib/feature/machine_share/ui/machine_share_page.dart
app/flutter_app/lib/feature/orders/demo_orders.dart
app/flutter_app/lib/feature/orders/ui/orders_tab.dart
app/flutter_app/lib/feature/user_auth/ui/auth_page.dart
app/flutter_app/lib/feature/user_auth/ui/otp_page.dart
app/flutter_app/lib/feature/user_auth/user_auth_request.dart
app/flutter_app/lib/feature/user_auth/user_login_request.dart
app/flutter_app/lib/feature/user_auth/user_register_request.dart
app/flutter_app/lib/main.dart
app/flutter_app/lib/shared/ui/app_theme.dart
app/flutter_app/lib/shared/ui/list_widgets.dart
```

### machine/server_connection

```text
machine/server_connection/machine_server_heartbeat.py
machine/server_connection/machine_server_request.py
```

### machine/menu_sync

```text
machine/menu_sync/__init__.py
machine/menu_sync/machine_menu_pack.py
machine/menu_sync/machine_menu_request.py
machine/menu_sync/machine_menu_store.py
machine/menu_sync/machine_menu_sync.py
machine/menu_sync/machine_menu_validate.py
```

### machine/ingredient_sync

```text
machine/ingredient_sync/__init__.py
machine/ingredient_sync/machine_ingredient_request.py
machine/ingredient_sync/machine_ingredient_store.py
machine/ingredient_sync/machine_ingredient_sync.py
machine/ingredient_sync/machine_ingredient_validate.py
```

### tests/python

```text
tests/python/__init__.py
tests/python/demo_user_database.py
tests/python/test_app_boundaries.py
tests/python/test_machine_bluetooth.py
tests/python/test_machine_list.py
tests/python/test_machine_register.py
tests/python/test_machine_relay.py
tests/python/test_machine_share.py
tests/python/test_server.py
tests/python/test_server_modules.py
tests/python/test_server_security.py
tests/python/test_user_login.py
tests/python/test_user_register.py
```

### tests/flutter

```text
tests/flutter/auth_page_test.dart
tests/flutter/bluetooth_pairing_test.dart
tests/flutter/dashboard_controller_test.dart
tests/flutter/device_share_test.dart
tests/flutter/machine_manage_test.dart
tests/flutter/machine_qr_test.dart
tests/flutter/machine_register_test.dart
tests/flutter/machine_sync_test.dart
tests/flutter/share_bluetooth_test.dart
tests/flutter/widget_test.dart
```
