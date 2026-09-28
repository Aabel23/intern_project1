# Mẫu module: cấu trúc và phong cách

Quy ước cho mọi tính năng mới và cho các module cũ khi được chuyển sang. Mẫu gốc:
`server/service/dashboard_sync/menu_sync/` (server) và `machine/menu_sync/` (máy);
`server/service/machine_manage/` là module cũ đầu tiên đã chuyển.

## 1. Ý tưởng

**`main.py` chỉ gọi các module lên.** Mỗi module tự nghe đường dẫn của mình, tự đọc
body, tự kiểm tra, tự trả lời. Thêm tính năng = thêm một folder module + một dòng
trong `MODULES` của `server/main.py`.

Server chỉ có **một cổng**, nên vẫn cần một chỗ nhận request rồi hỏi lần lượt từng
module "đường dẫn này của anh không?". Việc đó nằm ở `server/lib/module_server.py`,
không có logic nghiệp vụ nào.

Những thứ **bắt buộc dùng chung**, module gọi tới chứ không giữ bản riêng:

| Dùng chung | Ở đâu | Vì sao không để trong module |
|---|---|---|
| Hộp thư lệnh xuống máy | `service/machine_relay/relay_queue.py` (`gui_va_cho`, `is_online`) | Máy chỉ long-poll **một** chỗ cho mọi loại lệnh; mỗi module một hộp thư = mỗi máy N kết nối treo |
| Phiên đăng nhập | `service/user_login/session.py` (`user_from_request`, `NOT_LOGGED_IN`) | Một token dùng cho mọi API |
| Đọc/ghi database | `server/database/...` (`machine_read`, `machine_write`, `get_connection`) | Một database cho cả server |
| Đọc/ghi JSON | `server/lib/http_json.py` (`read_json`, `send_json`) | Giống hệt nhau ở mọi module |
| Giới hạn theo IP | `server/lib/rate_limit.py` | Đếm theo IP trên toàn server |

## 2. Module phía server

```
server/service/<nhóm>/<module>/
    <module>_api.py       HTTP: ROUTES, MAX_BODY, handle(request)
    <module>_verify.py    kiểm tra: chỉ đọc, không ghi database, không gọi mạng
    <module>_flow.py      luồng: xỏ verify với database / hộp thư, trả (kết quả, status)
    test_flow.py          gọi thẳng hàm flow, database SQLite tạm
    <MODULE>_FLOW.html    (tùy) tài liệu luồng từ lúc bấm nút trên app
```

### `*_api.py`: chỉ HTTP

- Docstring đầu file liệt kê **mọi route** với body app gửi lên, để mở file ra là biết
  module nghe ở đâu.
- `ROUTES = {đường_dẫn: hàm_flow}`; đường dẫn lấy từ `server/config/routing.py`.
- `MAX_BODY`: module tự chọn (4096 cho gói tài khoản, 64 000 cho menu...).
- `handle(request) -> bool`: `False` nếu đường dẫn không thuộc module; nếu thuộc thì
  đọc JSON, gọi flow, gửi JSON, trả `True`. Bắt `sqlite3.Error` → 503.
- Tùy chọn: `handle_get(request)` cho GET, `tick()` cho việc định kỳ (dọn phiên hết
  hạn), `module_server` gọi mỗi ~0,5 giây.
- Không có logic nghiệp vụ.

```python
def handle(request):
    """request là BaseHTTPRequestHandler của server; True nếu đã trả lời."""
    route = ROUTES.get(request.path)
    if route is None:
        return False
    data = read_json(request, MAX_BODY)
    if data is None:
        send_json(request, {"valid": False, "message": "JSON không hợp lệ"}, 400)
        return True
    try:
        result, status = route(data)
    except sqlite3.Error:
        result, status = {"valid": False, "message": "Database tạm thời không sẵn sàng"}, 503
    send_json(request, result, status)
    return True
```

### `*_verify.py`: chỉ kiểm tra

- Đăng nhập, quyền với máy, dạng dữ liệu (kiểu, độ dài, khoảng giá trị).
- **Chỉ đọc.** Được đọc database để kiểm quyền; không ghi, không gọi mạng. Khi kiểm
  tra phải cùng transaction với lệnh ghi (vd đọc vai trò rồi xóa máy), hàm verify
  nhận `conn` của flow thay vì tự mở kết nối.
- Lỗi trả về là **thân JSON gửi app**; flow tự gắn status. Dạng hay dùng:
  `check_request(data) -> (user_id, machine_id, None)` hoặc `(None, None, lỗi)`.
- Ngoại lệ đã có: `menu_sync_verify.send_to_machine` (bỏ lệnh vào hộp thư) nằm ở
  verify của menu. Module mới để hàm kiểu này ở flow.

### `*_flow.py`: nối các bước

- Docstring đầu file vẽ luồng từng route trong 1-2 dòng:
  `rename_machine: đăng nhập → mã máy → tên → phải là chủ → đổi tên`.
- Mỗi hàm route nhận body đã parse, trả **`(kết quả, HTTP status)`**.
- Không đọc/ghi HTTP, không kiểm tra lặt vặt tại chỗ: gọi verify.
- Chạy riêng được, cuối file:

```python
if __name__ == "__main__":
    run_standalone((f"{__package__}.manage_api",), "Quản lý máy")
```

  `run_standalone` (trong `lib/module_server.py`) nhận **tên** module và import lúc
  chạy. Flow **không import api của chính nó**: api đã import flow, import ngược lại
  thành vòng và `from ... import <module>_flow` sẽ lỗi khi test import flow trước.
  Module cần hộp thư (gửi lệnh xuống máy) thêm `"server.service.machine_relay.relay_api"`
  vào danh sách để máy có chỗ heartbeat và hỏi lệnh.

### Định dạng trả về

Giữ đúng dạng app đang đọc cho từng route, **không đổi khi refactor**:

| Nhóm | Thân | Status |
|---|---|---|
| Tài khoản, máy, chia sẻ, quản lý máy | `{"valid": bool, "message": ..., ...}`; hết phiên thì `NOT_LOGGED_IN` (có `login_required`) | 200 khi `valid`, 400 khi không, 429 khi kèm `retry_after`, 503 lỗi database |
| Relay, menu, kho | `{"loi": ...}` khi lỗi; menu thêm `{"status": "ok" \| "up_to_date" \| "conflict", ...}` | 400 gói sai, 401 hết phiên, 403 không đủ quyền, 502 máy báo lỗi, 503 máy offline |

Muốn thống nhất hai dạng là một thay đổi riêng, phải sửa app đi kèm.

### Đăng ký module

1. Thêm hằng đường dẫn vào `server/config/routing.py`.
2. Thêm `<module>_api` vào `MODULES` trong `server/main.py`.
3. Nếu có bảng quyền theo vai trò: khai trong `sync_rules.py` (dashboard) hoặc trong verify.

## 3. Module phía máy

Máy không nghe HTTP: nó long-poll server lấy lệnh (`machine/main.py`), rồi tra bảng lệnh
của từng module.

```
machine/<module>/
    <module>_api.py        COMMANDS = {tên_lệnh: hàm_flow}; main.py tra bảng này
    <module>_verify.py     kiểm dạng lệnh server gửi xuống (raise ValueError khi sai)
    <module>_flow.py       verify → database → đóng gói kết quả
    <module>_database.py   file duy nhất đụng database của máy
    <module>_packet.py     (tùy) đóng gói/nén dữ liệu gửi lên
```

- Verify của máy **không kiểm quyền người dùng**: server đã kiểm, và máy không có bảng
  người dùng. Server cũng không chuyển token xuống máy.
- Lỗi (ValueError, lỗi database) để nổi lên: vòng lặp `main.py` bắt và trả `{"loi": ...}`
  cho app, máy vẫn chạy tiếp.
- Ghi nhiều dòng: kiểm hết rồi mới ghi, trong một transaction.

## 4. Phong cách code

**Import luôn ở đầu file**, không import trong hàm hay trong `if __name__ == "__main__"`,
chia nhóm theo nguồn, mỗi nhóm một dòng chú thích:

```python
# Thư viện chuẩn
import sqlite3

# Server chung: đường dẫn, đọc/ghi JSON
from server.config.routing import APP_REMOVE_MACHINE, APP_RENAME_MACHINE
from server.lib.http_json import read_json, send_json

# Module khác: phiên đăng nhập
from server.service.user_login.session import NOT_LOGGED_IN, user_from_request

# Trong module machine_manage
from .manage_flow import remove_machine, rename_machine
```

Thứ tự nhóm: thư viện chuẩn → server chung (`server.config`, `server.lib`,
`server.database`) → module khác (`server.service...`) → trong module (import tương đối).
Phần sau dấu hai chấm nói nhóm đó dùng để làm gì.

**Chú thích và thông báo bằng tiếng Việt.** Thông báo lỗi trả app viết cho người dùng
đọc ("Chỉ chủ máy mới đổi tên được"), không viết cho lập trình viên.

**Docstring đầu mỗi file** nói file làm gì và *không* làm gì (vd "chỉ đọc, không ghi
database, không đọc/ghi HTTP"). Chú thích trong code giải thích **vì sao**, không nhắc
lại code làm gì.

**Tên**: file `<module>_api.py`, `_verify.py`, `_flow.py`; hàm route đặt theo hành động
(`rename_machine`, `nhan_menu`); hàm kiểm tra `check_...` (trả lỗi) hoặc `is_...` (trả bool).

## 5. Chuyển một module cũ sang mẫu

1. Tạo `<module>_verify.py`: gom các kiểm tra đang nằm rải trong flow.
2. Sửa flow: gọi verify, trả `(kết quả, status)` với status **đúng như cũ** (200/400...).
3. Sửa api: `handle()` tự đọc/ghi như mẫu ở mục 2, bỏ `handle_valid_routes`.
4. Thêm khối `__main__` gọi `run_standalone`.
5. `test_flow.py`: nhận `(kết quả, status)`, kiểm cả status.
6. Chạy toàn bộ test (server + `machine.test_relay`), thử chạy riêng module, cập nhật
   file `*_FLOW.html` nếu có.

### Tình trạng

| Module | Theo mẫu |
|---|---|
| `dashboard_sync/menu_sync` (server + máy) | ✅ |
| `machine_manage` | ✅ |
| `machine_relay` | có `handle`/`handle_get`, chưa tách verify/flow; còn giữ `/app/gui-lenh`, `/app/dong-bo`, `/machine/refill` |
| `machine_register`, `machine_share`, `user_login`, `user_register` | chưa, còn dùng `lib/valid_api.py` |

Việc chung còn lại: gom kiểm "token → người dùng → quyền với máy → vai trò" (đang chép ở
share, register, menu, relay, manage) thành một hàm trong `server/lib/`.
