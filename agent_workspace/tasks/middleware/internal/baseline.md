> Hồ sơ nội bộ cho agent. Chuyển từ tài liệu HTML ngày 06/10/2026; nội dung và bằng chứng cũ được giữ, chưa kiểm lại sản phẩm. Sơ đồ gốc giữ dưới dạng mã SVG trong khối XML.

KẾ HOẠCH PHÁT TRIỂN / 05.10.2026

# Hiện trạng và nền kiểm chứng

Sửa test theo code hiện tại trước khi coi chúng là hàng rào cho middleware.

Tài liệu thiết kế và kế hoạch · Offline / In đượcTrang này là nghiên cứu chuyên đề. Kế hoạch thực thi chính thức đi theo phase lớn → phase con; xem [bản đồ chương trình](index.md). Task chi tiết đã chuyển tới phase con liên kết bên dưới.

## Bằng chứng đã đối chiếu

| Thành phần | Bằng chứng | Ý nghĩa với middleware |
| --- | --- | --- |
| Khởi động | `server/main.py`, tuple MODULES và create_server | Import trực tiếp, chạy mọi module; giữ nguyên |
| HTTP | `server/lib/http/http_server.py:17–34` | GET/POST duyệt module; chưa có vòng quan sát và biên lỗi tổng thể |
| JSON | `server/lib/http/http_json.py:11–27` | Kiểm kích thước và JSON object, chặn JSON sâu/surrogate; giới hạn do module chọn |
| Lỗi database | `http_json.py:72–76` | SQLite error → 503 theo error callback; chưa xử lý lỗi bất ngờ và lỗi serialize ở cùng biên |
| Giới hạn IP | `server/lib/http/http_rate_limit.py` | Lock bảo vệ fixed window 30/phút, bảng tối đa 1.000 IP; đầy bảng chặn IP mới |
| Phạm vi limit | `user_login_main.py`, `user_register_main.py` | Đăng ký/OTP/login dùng limit; logout được miễn |
| Phiên app | `server/lib/security/user_session.py` | Token nằm trong JSON, hash tra SQLite, hết hạn 30 ngày |
| Quyền máy | `server/lib/machine/machine_access.py` | Cơ chế tra quyền chung; danh sách role do tác vụ quyết định |
| GET trạng thái | `machine_list_main.py:39–47`, `machine_list_get.py:30` | Cửa vào và machine_status đều không kiểm phiên; đây là thay đổi quyền cần cập nhật caller/test khi sửa |
| Máy | `machine_link_process.py` | Xác minh product key rồi heartbeat/poll/deliver |
| Transport | `server/lib/machine/machine_transport.py` | Trạng thái RAM, lock/condition, chờ lệnh và ghép kết quả theo máy + id |
| Body | Các file main của feature | Phần lớn 4.096 byte; menu 64.000; machine_link 1.000.000 |
| Timeout | `server/config/config.py`, `server_client.dart` | Poll 8s, command 20s, heartbeat offline 15s; app timeout toàn request 25s |

Tài liệu MODULE_PATTERN còn mô tả đăng nhập hai bước, trong khi `user_login_process.py` hiện là đăng nhập một bước. Khi viết chính sách middleware, lấy caller và code hiện tại làm bằng chứng, không tái tạo endpoint đã bỏ từ tài liệu.

Baseline dưới đây lấy từ lượt nghiên cứu trước; đợt làm lại tài liệu không chạy lại test sản phẩm.

Đã chạy ngày 05/10/2026:

```
python3 -m unittest tests.python.test_server_modules tests.python.test_server tests.python.test_server_security
Ran 26 tests in 6.651s
FAILED (failures=1, errors=18)
Exit code: 1
```

Lượt đầu trong sandbox không mở được socket localhost. Lượt trên chạy ngoài sandbox và mở được socket. 17 test security lỗi ở setUp do LOGIN_STATES không còn tồn tại; một test HTTP lỗi khi patch hook tick đã bỏ; một test HTTP chờ 400 ở route cũ nhưng nhận 404. Không coi expectedFailure trong security là bằng chứng vì setUp đã lỗi trước khi test kiểm hành vi. Chưa sửa test trong đợt nghiên cứu. Log đầy đủ của lượt chạy: `/tmp/middleware-baseline-unrestricted.log`.

Chưa benchmark tải, chưa kiểm trên Raspberry Pi/Windows/điện thoại thật, chưa chứng minh hành vi của middleware vì chưa triển khai middleware mới.

Chưa có số mẫu benchmark, p50/p95, RSS hoặc tải nền. Thời gian 6,651 giây là tổng lượt unittest, không phải độ trễ request. Code sản phẩm chưa đổi; đầu ra phase này là nghiên cứu và đề xuất.

## Tác vụ chặng G0

<a id="B01"></a>

### B01 · Lập snapshot hợp đồng thực

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/foundation/contract-research.md#B01). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.

<a id="B02"></a>

### B02 · Khôi phục fixture và test lỗi thời

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/foundation/fixture-repair.md#B02). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.

<a id="B03"></a>

### B03 · Test tái hiện biên và response

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/foundation/risk-scenarios.md#B03). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.

<a id="B04"></a>

### B04 · Đo profile môi trường và ngân sách ban đầu

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/foundation/environment-baseline.md#B04). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.

## Cổng G0

Đi tiếp khi snapshot và fixture đúng, test tái hiện cho chặng kế tiếp có bằng chứng, môi trường đo được ghi. Không yêu cầu sửa mọi lỗ hổng cũ để thử lifecycle, nhưng lỗi test không được che hồi quy.
