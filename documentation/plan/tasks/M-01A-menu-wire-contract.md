# M-01A · Đề xuất hợp đồng gói menu v2

Trạng thái: **đề xuất để coder/reviewer dùng sau khi chốt các lựa chọn cuối tài liệu**. Phạm vi này chỉ định dạng dữ liệu và golden vector; không đổi mã đang chạy. Máy giữ dữ liệu thật. Gói đầy đủ đi nguyên dạng qua relay, LAN hoặc Bluetooth.

## Dữ liệu và ranh giới phiên bản

Gói có hai phần độc lập:

- **Nội dung**: món, giá, hash ảnh, công thức và các bảng tra cứu. `content_version` là CRC32 unsigned của **byte UTF-8 JSON nội dung**.
- **Trạng thái**: `available` và `in_stock` của từng món. `state_version` là CRC32 unsigned của **byte UTF-8 JSON trạng thái**. Kho thay đổi làm món hết hàng không tạo xung đột cho người sửa giá.

Không đưa `generated_at`, hai số phiên bản, hoặc phần trạng thái vào byte nội dung. Tránh CRC tự tham chiếu bằng cách tính CRC trên hai mảng byte **trước khi** dựng phong bì. App giải base64 để có lại đúng mảng byte và tính CRC trực tiếp trên đó; app không serialize JSON lần nữa.

## Phong bì

`packet` trong kết quả relay là `base64(zlib(UTF8(JSON phong bì)))`. Với LAN/Bluetooth, gửi đúng byte zlib trước base64. Giới hạn **262144 byte zlib**, kiểm trước khi mã hóa base64. Phong bì:

```json
{
  "type":"menu_sync",
  "v":2,
  "min_app_v":2,
  "content_version":123456789,
  "state_version":987654321,
  "generated_at":"2026-10-13T09:30:00+07:00",
  "content_b64":"<base64 của byte JSON nội dung>",
  "state_b64":"<base64 của byte JSON trạng thái>"
}
```

`v` là phiên bản cấu trúc phong bì; app kiểm `min_app_v` trước khi giải nội dung. Hai version là số nguyên unsigned 32-bit. `generated_at` chỉ để hiển thị, không tham gia CRC. Cùng nội dung và trạng thái với thời điểm dựng khác nhau phải giữ nguyên hai version. Gói trả `status: "ok"` hoặc `"conflict"` chứa cả hai version ở kết quả ngoài và trong phong bì; app kiểm chúng bằng nhau. `status: "up_to_date"` chỉ có hai version, không có `packet`.

## Byte JSON nội dung

Máy tạo một snapshot nhất quán của MySQL. JSON không có khoảng trắng, dùng UTF-8, khóa theo đúng thứ tự dưới đây; các mảng hàng sắp theo khóa nêu trong bảng. Chuỗi Unicode chuẩn hóa NFC; `null` là JSON null; số tiền và lượng gram là số nguyên, không dùng float hoặc ký hiệu mũ. Python có thể dùng `json.dumps(..., ensure_ascii=False, separators=(",", ":"))` sau khi chuẩn hóa giá trị. Byte này là nguồn để tính `content_version` và để Dart parse sau khi đã kiểm CRC.

```json
{"drinks":[[1,"Trà đào",null,35000,null,null,null,false]],"recipes":[[1,1,7,1250]],"lookups":{"glasses":[],"drink_types":[],"categories":[],"ingredients":[[7,"Đào"]],"drink_categories":[]}}
```

| Mảng | Cột theo thứ tự | Thứ tự hàng |
|---|---|---|
| `drinks` | `drink_id`, `drink_name`, `image_sha256`, `price_vnd`, `glass_id`, `drink_type_id`, `garnish`, `featured` | `drink_id` tăng |
| `recipes` | `drink_id`, `step_no`, `ingredient_id`, `target_centigram` | `(drink_id, step_no, ingredient_id)` tăng |
| `glasses` | `glass_id`, `glass_name`, `art`, `capacity_ml`, `sort_order` | `glass_id` tăng |
| `drink_types` | `drink_type_id`, `type_name`, `art`, `sort_order` | `drink_type_id` tăng |
| `categories` | `category_id`, `category_name`, `description` | `category_id` tăng |
| `ingredients` | `ingredient_id`, `ingredient_name` | `ingredient_id` tăng |
| `drink_categories` | `drink_id`, `category_id` | `(drink_id, category_id)` tăng |

`image_sha256` là 64 ký tự hex thường của **byte file ảnh**, hoặc null khi món không có ảnh; ảnh không nằm trong gói và được lấy riêng theo hash. Giá trong schema là `DECIMAL(10,2)`: chỉ chấp nhận giá có phần lẻ bằng 0 khi đổi sang `price_vnd`. `target_gram DECIMAL(10,2)` nhân 100 chính xác thành `target_centigram`. `recipe_action` và `store_setting` chưa vào gói. Không đưa số tồn kho vào gói menu.

## Byte JSON trạng thái

```json
{"drinks":[[1,true,true]]}
```

Mỗi hàng gồm `drink_id`, `available`, `in_stock`, sắp `drink_id` tăng. ID trạng thái phải khớp chính xác tập ID trong nội dung. Thay một cờ chỉ làm đổi `state_version`. App chỉ thay snapshot đang hiện sau khi kiểm phong bì, hai CRC, cấu trúc và tính khớp ID.

## Lệnh đọc và ghi

Đề xuất `nhan_menu` nhận `{"content_version":null,"state_version":null}` khi app chưa có snapshot; nếu cả hai số trùng, trả `up_to_date`, nếu có một số khác, trả toàn gói. Khi sửa giá, `cap_nhat_menu` mang `content_version` của bản người dùng đã xem; máy so riêng version nội dung trong cùng transaction ghi. Thay đổi trạng thái dùng lệnh `bat_tat_mon` riêng và không yêu cầu content version. Quyền và đường vận chuyển theo thiết kế menu hiện hành: tắt/bật cho vai được cấp quyền vận hành; sửa giá chỉ Owner/Manager qua cloud. Lệnh ghi chỉ thành công sau khi máy trả phiên bản và snapshot mới.

## Golden vector và kiểm tra tương thích

1. Cố định hai chuỗi UTF-8 JSON đúng như ví dụ gọn ở trên, không khoảng trắng. Tạo `content.hex`, `state.hex`, CRC32 unsigned của từng chuỗi, phong bì JSON với `generated_at` cố định và byte zlib/base64. Lưu tất cả vào **một fixture** để Python và Dart đọc cùng byte. Không hard-code riêng hai bản kỳ vọng.
2. Python packer phải cho cùng `content.hex` và `state.hex` khi DB trả hàng với thứ tự bất kỳ, `Decimal('35000.00')`, Unicode có dạng tổ hợp, và timestamp khác. `content_version` không đổi khi chỉ `available`/`in_stock` đổi; `state_version` không đổi khi chỉ giá/công thức/lookup đổi.
3. Dart decoder xác nhận `v`, `min_app_v`, giới hạn kích thước, hai CRC, version ngoài khớp trong, schema cột, kiểu số và tập ID. Sửa 1 byte sau giải nén, cắt zlib, đổi version hoặc tráo ID trạng thái đều bị từ chối mà snapshot cũ còn nguyên.
4. Round trip Python → Dart qua kết quả relay JSON phải giải ra cùng byte nội dung/trạng thái. Codec raw LAN/Bluetooth dùng cùng fixture khi các transport menu đó được triển khai ở phiếu sau; không chặn M-01A vì chúng chưa tồn tại. Gói zlib đúng 262144 byte được nhận; 262145 byte bị từ chối ở máy và phía nhận. Giới hạn giải nén cần tránh cấp phát không giới hạn.

## Các lựa chọn còn phải chốt trước khi sửa production code

- **Hash ảnh và nguồn tải ảnh**: `drink.image` hiện là tên file; chưa có đường máy/server phục vụ ảnh theo SHA-256. Cần chốt cách xử lý file thiếu và nơi app tải ảnh qua LAN/Internet.
- **Phạm vi lookup**: bảng trên lấy tên ly/kiểu pha/nhóm/nguyên liệu và ánh xạ nhóm theo schema. Cần xác nhận app đầu tiên có cần `art`, `capacity_ml`, `description` hay có thể rút gọn; rút gọn trước khi tạo golden vector.
- **Đơn vị gram**: đề xuất centigram vì `recipe.target_gram` là `DECIMAL(10,2)`; cần xác nhận với cách app sẽ hiển thị gram.
- **Lệnh phiên bản**: đề xuất `null` thay số 0 để xin gói lần đầu vì CRC32 hợp lệ có thể là 0. Cần chốt tên khóa và cách chuyển từ `menu_version` v1.
- **Recipe action**: tài liệu menu ghi không có ở bản đầu; công thức `recipe` chỉ gồm phần nguyên liệu được rót. Cần xác nhận phạm vi này với chức năng hướng dẫn pha.
- **Nhất quán và cạnh tranh ghi**: đọc nhiều bảng phải cùng snapshot DB; hai lệnh sửa giá dùng cùng version không được cùng ghi thành công. Cần xác định quy tắc khóa/kiểm lại version trong transaction và ca test hai yêu cầu đồng thời.
- **Dữ liệu cũ**: kiểm dữ liệu giá `DECIMAL(10,2)` hiện có; nếu có phần lẻ, chốt cách chuyển/khước từ trước khi packer chạy. `min_app_v` ở đây là version schema menu, không phải version phát hành Android; app v1 gặp máy v2 cần mã lỗi hoặc chính sách tương thích rõ.
- **Lookup và hướng dẫn pha**: schema `drink_type` còn `method/detail`; `recipe_action` chứa bước thao tác xen bước rót. Nếu app khách đầu phải hiển thị hướng dẫn pha đầy đủ, gói chỉ có `recipe` là thiếu; chốt phạm vi trước khi dựng vector.

## Vị trí mã hiện tại cần thay sau khi chốt

`version1.1/machine/menu_sync/machine_menu_store.py`, `machine_menu_pack.py`, `machine_menu_sync.py`, `machine_menu_validate.py`; `flutter_app/lib/feature/machines/data/machine_controller.dart`, `flutter_app/lib/feature/machine_menu/ui/machine_menu_tab.dart`; `server/src/relay.py` cho lệnh tách riêng. Giới hạn HTTP hiện là 65536 byte cho request server (`server/configuration/skeleton.py`, `server/src/http.py`), 65536 byte cho response máy (`version1.1/machine/server_connection/machine_server_request.py`) và response app (`flutter_app/lib/shared/cloud/cloud_client.dart`). Tính cả base64/phong bì HPKE khi chọn giới hạn mới; không tăng mọi route cùng mức nếu chỉ kết quả menu cần gói lớn. Mã hiện tại là gói v1 chỉ có hàng `drink`, một CRC gồm cả cờ trạng thái và không kiểm CRC tại app.
