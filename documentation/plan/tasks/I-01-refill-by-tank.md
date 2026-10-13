# I-01 · Xem tồn và xác nhận nạp đầy từng bình

**Trạng thái:** phiếu Planner, chưa duyệt để sửa production code. User chọn thao tác nạp đầy **từng bình** cho khách đầu tiên; không nhập số gram, không kiểm đếm tồn thủ công. Những quyết định về dung tích và sổ kho ở cuối phiếu vẫn cần chốt. Kiểm thử Android thật thuộc cổng trước phát hành.

## Ranh giới nghiệp vụ

- Máy giữ số tồn thật trong MySQL. App đọc bản chụp kho bằng `nhan_kho` và gửi `nap_kho` cho đúng một `ingredient_id` sau khi người vận hành xác nhận đã đổ đầy bình vật lý.
- `nap_kho` là phép **đặt** `amount = max_gram` của bình đã khai báo, không phải cộng thêm. Bấm lại khi bình vẫn đầy không được làm tồn vượt dung tích. Máy cập nhật `in_stock`, trạng thái món và menu màn bán sau khi ghi.
- Bản đầu không có `target="all"`, `value` bằng gram, `kiem_dem_kho`, nhập/sửa dung tích qua app hoặc sửa tồn theo ý người vận hành. App không ghi thẳng MySQL.
- Chỉ hiện nút nạp đầy cho bình có `max_gram` thật. Một nguyên liệu không gắn với bình vật lý cần được phân biệt với bình có thể nạp; schema hiện chưa có cờ riêng, nên tiêu chí chọn bình phải được chốt trước coder.

## Hành vi code hiện tại cần đối chiếu

| Vị trí | Hành vi đang chạy | Khoảng cách tới I-01 |
|---|---|---|
| `version1.1/database/schema/schema.sql` bảng `ingredient` | `amount`, `threshold_gram`, `max_gram DECIMAL(10,2) NULL`, `type`, `gpio`; không có sổ kho. | `max_gram=NULL` chưa có dung tích thật; không thể coi là bình đã khai báo. |
| `version1.1/database/services/inventory.py` `list_ingredients()` | Trả `amount`, `max_gram`, `max_set`, `in_stock`, loại/vị trí; khi thiếu dung tích dùng `DEFAULT_MAX_GRAM=10000` chỉ để hiển thị. | App đang thấy một mức tối đa ước lượng; không được dùng mức này để nạp thật. |
| Cùng file, `refill()` | `SELECT ... FOR UPDATE`, đặt `amount` bằng `max_gram` hoặc mặc định 10 kg; nhận một ID hoặc `all`, `full` hoặc số gram; commit rồi đọc lại tồn/cờ. | Phải từ chối bình thiếu `max_gram`; giới hạn đúng một ID và `full`; cân nhắc kết quả trước/sau. |
| `machine/ingredient_sync/machine_ingredient_validate.py`, `machine_ingredient_sync.py` | Validator nhận `all`, `full`, số gram không âm. `nap_kho` gọi DB rồi dựng lại `menu-data.js`, cảnh báo nếu dựng thất bại. `nhan_kho` dùng CRC32 danh sách kho. | Thu hẹp dạng lệnh và hiển thị rõ khi đã ghi tồn nhưng dựng menu thất bại. |
| `flutter_app/lib/feature/machine_ingredient/ui/machine_ingredient_tab.dart` | Đọc tồn thật; nút từng dòng `Nạp đầy`, nút nổi `Nạp tất cả`; gửi `{target, value:'full'}`. Cảnh báo dung tích mặc định nhưng vẫn cho nạp. | Bỏ `Nạp tất cả`; vô hiệu nút khi `max_set=false` hoặc không phải bình; lời xác nhận phải nói rõ bình vật lý. |
| `server/src/relay.py`, `version1.1/machine/main.py` | Server whitelist `nap_kho`, chỉ cho owner; máy cache 32 kết quả theo `request_id` trong RAM. | Quyền vai chia sẻ chưa có; cache RAM không là bằng chứng chống lặp sau restart. |

## Dạng lệnh tối thiểu đề xuất

`nhan_kho` giữ đường hiện có. `nap_kho` chỉ nhận `{"ingredient_id": 7, "value": "full"}` (hoặc giữ khóa `target` hiện có để tránh đổi không cần thiết; chọn một dạng trước coder). Máy kiểm ID nguyên dương, tồn tại, có dung tích thật và được phép nạp; không nhận `all` hay số gram. Kết quả nên chứa `ingredient_id`, `before`, `after`, `max_gram`, `in_stock` và phiên bản kho mới; lỗi phải nói rõ bình chưa khai báo dung tích, bình không phù hợp, hoặc dung tích nhỏ hơn tồn hiện tại. Không âm thầm hạ tồn khi người dùng bấm “nạp đầy” nếu số tồn đã lớn hơn mức tối đa.

Nếu menu màn bán dựng lại thất bại **sau khi transaction tồn đã commit**, trả thành công phần ghi kho cùng `warning` để app đọc lại tồn và báo việc màn bán chưa cập nhật; không gửi lại lệnh như thể chưa ghi. Cần chốt cơ chế sửa trạng thái màn bán trước khi giao khách.

## Quyền, chống lặp và dữ liệu lịch sử

- Quyền hiện chạy chỉ có owner ở server. Tài liệu kiến trúc `documentation/architect/features/inventory.html` nói mọi vai được nạp, nhưng Manager/Employee và quyền tại chỗ chưa có code hoàn chỉnh. I-01 chỉ được bật cho vai sau khi ma trận quyền và kiểm quyền trên từng đường cloud/LAN/Bluetooth được chốt. Máy phải nhận đủ danh tính/ngữ cảnh quyền nếu chạy tại chỗ.
- Bản đầu có thể dùng `request_id` hiện có khi thử lại trong cùng phiên máy; mất kết quả hoặc restart hiện không bảo đảm idempotency bền vững. Vì nạp đầy là phép đặt tới mức tối đa, thực hiện lại có thể ghi đè lượng đã tiêu thụ sau lần đầu. Trước khi giao khách cần quyết định lưu mã lệnh đã xử lý bền vững ở máy, hoặc một cơ chế tương đương để lệnh cũ không ghi lại sau restart.
- Schema chưa có `inventory_ledger`. Nếu yêu cầu truy vết ai nạp, khi nào và tồn trước/sau vẫn áp dụng cho khách đầu, thêm bản ghi trong **cùng transaction** với cập nhật tồn; nhận `actor_id` và `request_id` từ biên lệnh đã xác thực, không tin trường tự khai trong `data`. Cần thống nhất retention và cách hiển thị lịch sử trước coder.

## Ca kiểm cho phiếu coder sau khi khóa quyết định

1. Đọc kho 0/nhiều bình, đổi máy trong khi response cũ về, CRC/version trùng và khác.
2. Bình có `max_gram`: đặt đúng mức, trả tồn trước/sau và cờ `in_stock`; menu bán cập nhật. Bình thiếu `max_gram`: từ chối, không ghi mặc định 10 kg. ID sai, `all`, số gram, số âm và gói sai kiểu đều bị từ chối.
3. Tồn bằng mức tối đa, tồn vượt mức tối đa, hai yêu cầu cùng lúc, pha đang trừ kho, timeout/thử lại và restart giữa ghi/kết quả. Không mất lượng tiêu thụ vì phát lại lệnh cũ.
4. Owner/Manager/Employee theo ma trận quyền đã chốt, quyền bị thu hồi, đường LAN/Bluetooth nếu được phép; kiểm lỗi dựng `menu-data.js` sau commit.
5. Nếu có ledger: một lệnh thành công chỉ có một dòng đúng actor/request ID/before/after; rollback không có dòng; đồng thời với pha không ghi sai thứ tự.

## Quyết định cần khóa trước coder

1. **Dung tích thật:** ai nhập `max_gram` cho từng bình, lúc lắp máy hay qua app; bình không có dung tích có bị khóa nạp và cảnh báo vận hành như đề xuất không?
2. **Bình nào:** mọi hàng `ingredient`, chỉ `type=PUMP`, hay cả vị trí `MANUAL` có bình cần nạp? Schema chưa mang định danh bình riêng.
3. **Lịch sử kho:** có bắt buộc ledger cho lần giao đầu không; nếu có, người xem, thời gian giữ, và dữ liệu tối thiểu?
4. **Quyền tại chỗ:** Owner/Manager/Employee nào được nạp, khi offline dựa vào bản sao quyền nào và thu hồi ra sao?
5. **Lệnh khi không rõ kết quả:** định danh lệnh bền vững qua restart và thời hạn giữ để không ghi đè lượng đã pha sau một lần nạp thành công.
6. **Lỗi dựng menu bán:** cách sửa và tín hiệu cho người vận hành khi tồn đã ghi nhưng màn bán chưa cập nhật.

Sau khi khóa sáu mục trên, phát phiếu coder theo thứ tự schema/transaction máy → command/relay/quyền → app → kiểm liên thông. Không coi giao diện hiện có hoặc test tự động là nghiệm thu trên máy thật.
