# Đồng bộ dashboard

Mỗi tab dashboard của app là một folder, **chia theo tab, không chia theo nguồn dữ liệu**:

| Folder | Tab | Route | Dữ liệu ở đâu |
| --- | --- | --- | --- |
| `menu_sync/` | Menu | `/app/nhan-menu`, `/app/gui-menu` | của máy, hỏi xuống qua hộp thư |
| `ingredient_sync/` | Kho | `/app/nhan-kho`, `/app/nap-kho` | của máy, hỏi xuống qua hộp thư |
| `machinelist_sync/` | Máy | `/app/may-cua-toi`, `/app/doi-ten-may`, `/app/go-may`, GET `/machine/trang-thai` | của server (bảng `machines`, giờ heartbeat) |

`sync_rules.py`: bảng vai trò được làm từng việc (`QUYEN_MENU`, `QUYEN_KHO`,
`QUYEN_NAP_KHO`) và `check_access(data, roles)` dùng chung cho Menu và Kho:
token → người dùng → có quản lý máy → vai trò đủ quyền.

## Tab dữ liệu máy (Menu, Kho)

Server không lưu dữ liệu máy. Module kiểm quyền và dạng gói, rồi gọi
`machine_link.link_queue.send(machine_id, instruction, data)`: lệnh nằm trong hộp thư
tới khi máy long-poll lấy, máy trả kết quả, server chuyển nguyên cho app.

```
App ─ POST /app/nhan-kho {token, machine_id, version}
 └→ ingredient_sync: check_access → is_version → send("nhan_kho", {version})
      Máy ─ /machine/hoi-lenh → {id, instruction: "nhan_kho", data: {version}}
      Máy: version trùng → {"status": "up_to_date", "version"}
           khác         → {"status": "ok", "version", "ingredients": [...]}
      Máy ─ /machine/tra-ket-qua {id, ket_qua}
 ←─ 200 + kết quả máy
```

`version` là CRC32 của dữ liệu do máy tính; app chưa có dữ liệu gửi `0`. Menu làm y như
vậy với `menu_version`, kết quả thêm gói `packet` = base64(zlib(JSON)), xem
`machine/menu_sync/menu_sync_packet.py`.

### Route

| Route | Gửi | Kết quả |
| --- | --- | --- |
| `/app/nhan-menu` | `token`, `machine_id`, `menu_version` | `{status: up_to_date \| ok, menu_version, packet?}` |
| `/app/gui-menu` | `token`, `machine_id`, `menu_version`, `thay_doi: [{drink_id, available?, price?}]` | `{status: ok \| conflict, menu_version, packet}`; `conflict` = app đang giữ bản cũ, máy không ghi |
| `/app/nhan-kho` | `token`, `machine_id`, `version` | `{status: up_to_date \| ok, version, ingredients?}` |
| `/app/nap-kho` | `token`, `machine_id`, `target` (id hoặc `"all"`), `value` (`"full"` hoặc số gram, số gram chỉ khi `target` là id) | kết quả `refill()` của máy, kèm `warning` nếu dựng lại menu màn bán hàng lỗi |

`ingredients`: `ingredient_id`, `name`, `amount`, `max_gram`, `max_set`, `pump_no`,
`in_stock`. `max_set = false` nghĩa là máy chưa khai báo mức tối đa, `max_gram` đang là
giá trị mặc định; app hiện dòng cảnh báo.

### Lỗi

Thân lỗi `{"loi": ...}`:

| Status | Khi nào |
| --- | --- |
| 400 | gói sai dạng (version âm, `thay_doi` rỗng hoặc có cột lạ, `target`/`value` sai) |
| 401 | token sai/hết hạn (kèm `login_required: true`) |
| 403 | không quản lý máy này, hoặc vai trò không đủ quyền |
| 503 | máy offline (không heartbeat trong 15 giây) |
| 502 | máy báo lỗi (MySQL, món không có trên máy...) hoặc không trả kết quả trong 20 giây |

## Mã nguồn

| | Server | Máy | App |
| --- | --- | --- | --- |
| Menu | `menu_sync/` | `machine/menu_sync/` (SQLite `machine/database/database.db`) | `lib/feature/data_sync/products_sync.dart` |
| Kho | `ingredient_sync/` | `machine/ingredient_sync/` (MySQL của `version1.0`) | `lib/feature/data_sync/ingredients_sync.dart` |
| Máy | `machinelist_sync/` | — | `lib/UI/dashboard/dashboard/dashboard_controller.dart` |

Mỗi module theo mẫu api / verify / flow trong `androidv0.1/MODULE_PATTERN.md`. Thử riêng:
`python sandbox/server_module/run_modules.py menu_sync ingredient_sync link login`.
