# Đồng bộ dashboard

App đọc dữ liệu của máy (kho, menu) để vẽ các tab dashboard. Menu đi đường riêng, xem mục **Tab Menu** bên dưới. Server
không lưu dữ liệu này: nó kiểm tra quyền rồi chuyển lệnh xuống máy qua hộp thư relay
trong RAM, máy đọc MySQL của nó và trả về. Mọi tab dùng chung một sublink, phân
biệt bằng `lenh` trong body. Lệnh ghi (nạp kho, bật/tắt món) không đi qua đây.

## Luồng

```
App  ─ POST /app/dong-bo {token, machine_id, lenh}   header If-None-Match: <ETag đang giữ>
 └→ Server: token → quyền với máy → QUYEN_DONG_BO[lenh] → máy online?
     └→ hộp thư máy → Máy (/machine/hoi-lenh): chạy hàm theo lenh, tính ETag
          ├ ETag trùng: gói rỗng
          └ khác:      JSON nén gzip
        Máy ─ POST /machine/tra-dong-bo (body = gói, thông tin trong header)
 ←─ Server chuyển nguyên gói, không giải nén: 304 nếu rỗng, 200 + gzip nếu có dữ liệu
App: 304 giữ danh sách cũ; 200 cập nhật và lưu ETag mới
```

## Route

| Route | Gửi | Kết quả |
| --- | --- | --- |
| POST `/app/dong-bo` | body `token`, `machine_id`, `lenh`; header `If-None-Match` (tùy chọn) | `200` JSON gzip + `ETag`, hoặc `304` + `ETag` |
| POST `/machine/tra-dong-bo` | header `X-Product-Key`, `X-Lenh-Id`, `ETag`; body là JSON đã gzip, rỗng = không đổi | `{"da_nhan": true}` |

Lỗi của `/app/dong-bo` trả JSON `{"loi": ...}`:

| Status | Khi nào |
| --- | --- |
| 401 | token sai/hết hạn (kèm `login_required: true`) |
| 403 | không quản lý máy, lệnh không có trong bảng, hoặc vai trò không đủ quyền |
| 503 | máy offline (không heartbeat trong 15 giây) |
| 502 | máy báo lỗi (MySQL...) hoặc không trả kết quả trong 20 giây |

## Lệnh

Bảng quyền ở `sync_rules.py` (`QUYEN_DONG_BO`), hàm đọc ở `machine/main.py` (`LENH_DONG_BO`).

| `lenh` | Quyền | Máy gọi | Dữ liệu |
| --- | --- | --- | --- |
| `dong_bo_nguyen_lieu` | owner, manager | `database.admin_functions.ingredients.ingredients_payload()` (`version1.0`) | `ingredients`: `ingredient_id`, `name`, `amount`, `max_gram`, `max_set`, `pump_no`, `in_stock`... |

`max_set = false` nghĩa là máy chưa khai báo mức tối đa, `max_gram` đang là giá trị
mặc định; app hiện dòng cảnh báo.

## Nạp kho: `/machine/refill`

App gửi `POST /machine/refill` với `{token, machine_id, target, value}`:

| Trường | Giá trị |
| --- | --- |
| `target` | id nguyên liệu (số > 0) hoặc `"all"` |
| `value` | `"full"` = đổ đầy tới `max_gram`; hoặc số gram = đặt lượng tồn (chỉ khi `target` là một id) |

Server kiểm quyền (`QUYEN_NAP_KHO` trong `sync_rules.py`) và dạng gói (sai → 400), rồi
chuyển xuống máy thành lệnh `nap_kho`. Máy gọi
`database.admin_functions.ingredients.refill()` (`version1.0`) — cùng hàm nạp với trang
admin của máy — rồi dựng lại menu màn bán hàng. Trả `200` + kết quả, hoặc `502 {"loi"}`
khi máy báo lỗi, `503` khi máy offline.

## ETag và nén

- ETag = 32 ký tự đầu SHA-256 của JSON đã sắp khóa (`sort_keys`), nên cùng dữ liệu luôn
  ra cùng ETag. Máy so với ETag app gửi; trùng thì không gửi lại dữ liệu.
- Nén bằng `Content-Encoding: gzip`; `HttpClient` của Dart tự giải nén.
- App bỏ ETag khi đổi máy (`IngredientsSync.reset()`).

## Thêm một lệnh đồng bộ mới

1. `sync_rules.py`: thêm `"dong_bo_x": {"owner", "manager"}`.
2. `machine/main.py`: thêm `"dong_bo_x": ham_doc` vào `LENH_DONG_BO` (hàm trả dict JSON được).
3. App: tạo `lib/feature/data_sync/x_sync.dart` theo khuôn `ingredients_sync.dart`,
   gọi `api.sync(machineId, 'dong_bo_x', etag)` (trả `null` khi 304).

## File liên quan

| Phần | File |
| --- | --- |
| Server | `server/server.py` (`app_dong_bo`, `may_tra_dong_bo`, `gui_va_cho`), `sync_rules.py` |
| Máy | `machine/main.py` (`pack_sync`), `machine/server_connection/instruction_api.py` (`send_sync`) |
| App | `lib/UI/dashboard/machine_api.dart` (`sync`), `lib/feature/data_sync/ingredients_sync.dart`, `lib/UI/dashboard/minitab/inventory_tab.dart` |

## Test

```sh
python -m unittest machine.test_relay -v          # 200, 304, dữ liệu đổi, 502, 503, 403
cd app/flutter_app && flutter test                # gửi lại ETag, giữ danh sách khi 304
python sandbox/e2e/run_e2e.py --skip-build        # điện thoại thật + máy giả
```

## Tab Menu: `menu_sync/`

Tab Menu vừa nhận vừa gửi gói tin. Máy là nguồn menu (bảng `drink` trong
`machine/database/database.db`); server chỉ kiểm tra token, quyền (`QUYEN_MENU` trong
`sync_rules.py`) và dạng gói rồi chuyển qua hộp thư relay, không giải nén, không lưu.

```
App ─ POST /app/nhan-menu {token, machine_id, menu_version}
 └→ Server → máy lệnh nhan_menu
      ├ menu_version trùng: {"status": "up_to_date", "menu_version"}
      └ khác:               {"status": "ok", "menu_version", "packet"}

App ─ POST /app/gui-menu {token, machine_id, menu_version, thay_doi: [{drink_id, available?, price?}]}
 └→ Server kiểm dạng gói → máy lệnh gui_menu
      ├ menu_version là bản máy đang có: ghi trong một transaction → {"status": "ok", ... gói mới}
      └ máy đã có bản khác:              không ghi → {"status": "conflict", ... gói mới nhất}
```

`packet` = base64(zlib(JSON)), JSON là
`{type: "menu_sync", v: 1, menu_version, generated_at, fields: [...], drinks: [[...], ...]}`;
mỗi món là một mảng theo thứ tự `fields`. `menu_version` là CRC32 của `drinks`, app
chưa có menu gửi `0`. Mã máy: `machine/menu_sync/menu_sync_packet.py`; mã server: `menu_sync/`
(`menu_sync_api.py` đọc/ghi HTTP, `menu_sync_verify.py` kiểm tra + chuyển lệnh xuống máy,
`menu_sync_flow.py` xỏ hai phần lại; chạy riêng: `python -m server.service.dashboard_sync.menu_sync.menu_sync_flow`); mã app: `lib/feature/data_sync/products_sync.dart`.

| Status | Khi nào |
| --- | --- |
| 400 | `menu_version` không phải số 0..2³²−1; `thay_doi` rỗng, quá 200 dòng, cột ngoài `available`/`price`, sai kiểu hoặc giá âm |
| 401 / 403 | như `/app/dong-bo` |
| 503 | máy offline |
| 502 | máy báo lỗi (ví dụ `drink_id` không có trên máy; cả gói không được ghi) hoặc hết thời gian chờ |
