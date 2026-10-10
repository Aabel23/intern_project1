# Tài liệu project1_app

| Thư mục | Chứa gì | Khi nào thêm file vào |
|---|---|---|
| `manual/` | Manual tổng quan toàn hệ thống: cách chạy, các luồng chính, API, vận hành | Chỉ một manual; cập nhật thay vì tạo bản mới |
| `flows/` | Mỗi file giải thích sâu một luồng app ↔ server ↔ máy | Khi một luồng trong manual cần trang riêng |
| `design/` | So sánh phương án, quyết định thiết kế, kèm nghiên cứu | Khi cần chốt giữa nhiều cách làm |
| `assets/` | `document.css`, `fonts.css`, `fonts/` dùng chung, chạy offline | Không đặt tài liệu ở đây |

## Danh mục

| File | Nội dung |
|---|---|
| [index.html](index.html) | Mục lục tra cứu: tìm kiếm, nhảy tới từng mục |
| [manual/system-manual.html](manual/system-manual.html) | Manual hệ thống FlexMix: app, server, máy |
| [flows/account-auth.html](flows/account-auth.html) | Đăng ký, OTP, đăng nhập và phiên |
| [flows/machine-register.html](flows/machine-register.html) | Đăng ký máy qua tem QR hoặc Bluetooth; người đầu tiên thành chủ |
| [flows/machine-share-manage.html](flows/machine-share-manage.html) | Danh sách máy, mã mời, quyền owner/manager, đổi tên/gỡ máy |
| [flows/machine-link.html](flows/machine-link.html) | Relay lệnh qua long-poll, hộp thư lệnh, trạng thái online |
| [flows/menu-ingredient-sync.html](flows/menu-ingredient-sync.html) | Đồng bộ menu và kho bằng CRC32 `menu_version` |
| [flows/menu-image.html](flows/menu-image.html) | Ảnh món: `image_hash`, `image/get`, cache trong app (phía máy chưa làm) |
| [design/heartbeat-vs-long-poll.html](design/heartbeat-vs-long-poll.html) | Heartbeat hay long-poll (bản có sơ đồ, case study) |
| [design/heartbeat-vs-long-poll.md](design/heartbeat-vs-long-poll.md) | Cùng nội dung, bản Markdown; code và test dẫn chiếu tới file này |

## Quy ước

- Tên file tiếng Anh, chữ thường, nối bằng `-`.
- Tài liệu HTML mới chép từ `assets/template.html` (thiết kế FexMix_Munual), nạp `../assets/fonts.css`. `menu-ingredient-sync.html` còn dùng `document.css` cũ.
- Đặc tả viết trang luồng: `agent_workspace/tasks/docs-flows/BRIEF.md`.
- Link tới mã nguồn dùng đường dẫn tương đối từ vị trí file (tài liệu ở `docs/<loại>/` thì về gốc repo bằng `../../`).
