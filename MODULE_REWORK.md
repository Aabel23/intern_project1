# Quy trình rework một module

Mục tiêu: nhìn folder biết cửa vào, mở file hiểu luồng, đọc hàm biết nhiệm vụ.
Áp dụng từng module; dựa trên cách đã thống nhất khi chỉnh `menu_sync`.

## 1. Chọn phạm vi

- Người dùng chỉ module cần chỉnh và các điều phải giữ nguyên.
- Người thực hiện đọc code, tìm nơi gọi, tài nguyên chung và các phụ thuộc.
- Ghi rõ trách nhiệm hiện tại, điểm khó đọc và phạm vi ảnh hưởng.

**Đầu ra:** phạm vi rework và danh sách ràng buộc. Mặc định giữ URL, tên lệnh,
chuẩn gói tin, quyền truy cập, mã lỗi và hành vi nghiệp vụ.

## 2. Thống nhất luồng hiện tại

- Giải thích từ lúc nhận request đến lúc trả kết quả, có dẫn file/hàm thực tế.
- Phân biệt app, server, máy và các tác vụ nền.
- Người dùng xác nhận nghiệp vụ hoặc chỉnh cách hiểu trước khi đổi cấu trúc lớn.
- Nếu phát hiện lỗi, ghi riêng; không âm thầm trộn sửa nghiệp vụ vào refactor.

**Đầu ra:** bản mô tả luồng đúng với code và mục đích của người dùng.

## 3. Phân tích thành từng bước

Mỗi bước cần ghi rõ:

| Thành phần | Nội dung |
| --- | --- |
| Bên thực hiện | App, server hay máy |
| Input | Request hoặc kết quả bước trước |
| Xử lý | Công việc cụ thể |
| Output | Dữ liệu hoặc trạng thái chuyển tiếp |
| Nhánh lỗi | Dừng, trả lỗi, thử lại hoặc xử lý tiếp |
| Quan hệ | Nối tiếp, chờ kết quả hoặc thực sự chạy song song |

Phân tích theo bước không có nghĩa mỗi bước phải thành một file.
Với HTTP, ghi rõ response trả trên request ban đầu hay có cơ chế nhận kết quả riêng.

**Đầu ra:** luồng xử lý đủ rõ để triển khai và chọn kịch bản kiểm thử.

## 4. Chia trách nhiệm

- Xác định một cửa vào của module.
- Tách các thao tác nghiệp vụ độc lập, ví dụ lấy menu và cập nhật menu.
- Cơ chế nhiều module dùng tương đồng đặt trong `server/lib`.
- Helper chỉ dùng nội bộ module giữ tại module; helper riêng của một luồng ưu tiên
  nằm ngay trong file luồng đó.
- Không sao chép trạng thái dùng chung như phiên đăng nhập hoặc hộp thư máy.
- Module không gọi nội bộ của module tính năng khác.

**Đầu ra:** ranh giới giữa cửa vào, nghiệp vụ và cơ chế dùng chung.

## 5. Chốt cấu trúc trước khi sửa lớn

Đề xuất cây folder ngắn, giải thích nhiệm vụ và input/output của mỗi file.
Người dùng góp ý về cách đọc và bảo trì; triển khai khi hướng đã thống nhất.
Nếu người dùng đã cho phép tự quyết cấu trúc thì tiếp tục trong phạm vi đó,
không hỏi lại chỉ để hoàn thành thủ tục.

Ví dụ đã chốt cho menu phía server:

```text
menu_sync/
    machine_menu_main.py
    machine_menu_get.py
    machine_menu_update.py
    README.md
```

- `<đối_tượng>_<tính_năng>_main.py`: cửa vào và chọn luồng.
- Các file còn lại đặt theo tác vụ, ví dụ `get`, `update`.
- Mỗi thao tác ngắn nằm trọn trong một file.
- Hàm điều phối thể hiện thứ tự; comment chia bước và nhóm hàm phụ.
- Chỉ tách thêm file khi có trách nhiệm đủ rõ và giúp đọc/sửa dễ hơn.
- Không ép số file, số tầng hoặc bộ request/process/validate/store cố định.
- Không đánh số các file chứa những luồng độc lập.

**Đầu ra:** cây file và cách đọc module đã thống nhất.

## 6. Refactor

- Triển khai đúng cấu trúc đã chốt, dùng tên cụ thể và comment giải thích nhiệm vụ.
- Giữ các hàm phụ có trách nhiệm rõ; không gom/tách chỉ để giảm hoặc tăng số hàm.
- Cập nhật import, đăng ký module, tham chiếu trong test và tài liệu.
- Nếu di chuyển helper dùng chung, cập nhật các nơi gọi cần thiết; không tự mở rộng
  sang sửa nghiệp vụ của module khác.
- Giữ nguyên các ràng buộc bước 1. Thay hợp đồng chỉ khi được yêu cầu rõ ràng,
  đồng thời cập nhật các bên sử dụng và test liên quan.

**Đầu ra:** code mới và README phản ánh đúng startpoint, luồng và phụ thuộc.

## 7. Kiểm tra, duyệt và chốt

- Chạy các test phù hợp với phần thay đổi; ưu tiên test hành vi qua ranh giới module.
- Bao phủ các nhánh có liên quan: thành công, dữ liệu sai, thiếu quyền, xung đột,
  offline hoặc timeout.
- Báo rõ kết quả, lỗi đã biết và giới hạn kiểm chứng; không nói đã test thiết bị
  nếu chỉ chạy mô phỏng.
- Người dùng mở code đánh giá khả năng đọc; chỉnh tiếp đúng điểm còn vướng.
- Cập nhật tài liệu theo cấu trúc cuối, bỏ mô tả phương án đã bỏ.
- Commit khi có yêu cầu hoặc đã được cho phép; hoàn tất module rồi mới mở rộng.

**Tiêu chí hoàn thành:** cửa vào rõ, từng thao tác dễ theo dõi, phụ thuộc hợp lý,
hợp đồng được giữ đúng, kiểm tra phù hợp đã chạy và tài liệu khớp code.

## Mẫu giao việc

> Rework module **X** theo `MODULE_REWORK.md`. Trước tiên đọc và mô tả luồng,
> chỉ ra điểm khó hiểu, đề xuất cấu trúc rồi cùng tôi chỉnh.
> Giữ nguyên **URL / tên lệnh / gói tin / nghiệp vụ / quyền truy cập**.
> Phạm vi bổ sung hoặc ngoại lệ: **…**

## Cách phối hợp

Người dùng quyết định nghiệp vụ, ràng buộc và cách đọc mong muốn. Người thực hiện
chịu trách nhiệm khảo sát code, đề xuất cấu trúc cụ thể, triển khai và kiểm chứng.
Chốt luồng và cây file sớm để tránh thử nhiều cấu trúc khi tiêu chí còn chưa rõ.

## Cách viết tài liệu luồng hoạt động

Viết theo các bước có chủ thể: app gửi gì → server kiểm gì → máy làm gì →
server trả gì → app hiển thị gì. Mỗi bước ghi link, HTTP method, gói tin hoặc
kết quả nếu có. Bên dưới bước đó liệt kê các hàm tham gia và mô tả ngắn.
Không dùng danh sách hàm làm nội dung chính của luồng. Phân biệt request mới
với response của request trước; ghi rõ nhánh lỗi và xung đột tại bước phát sinh.

Tài liệu HTML luồng đặt bảng API ở đầu: Phương thức | Route | Ai gọi | Gửi lên | Nhận về.
Sau đó viết bước theo tác vụ app/server/máy, liệt kê hàm tham gia và mô tả ngắn
bên dưới từng bước. Đồng bộ nội dung HTML/Markdown khi chỉnh luồng.
