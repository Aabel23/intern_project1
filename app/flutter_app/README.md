# Điều khiển máy

App Android Flutter một màn hình, không có thư viện ngoài. Code nằm trong `lib/main.dart`.

Chạy từ thư mục gốc dự án:

```powershell
python server/server.py
# Terminal khác, khi đã có module database của machine:
python machine/main.py
# Terminal khác, với Android emulator hoặc điện thoại đã kết nối:
cd app/flutter_app
flutter run
```

- Android emulator: dùng `http://10.0.2.2:8000` để truy cập server trên máy tính.
- Điện thoại qua USB: chạy `adb reverse tcp:8000 tcp:8000`, rồi nhập `http://127.0.0.1:8000` trong app.
- Server hiện chỉ nghe ở `127.0.0.1`, nên địa chỉ LAN chưa dùng được.
- Nhập mã máy, kiểm tra online hoặc chọn lệnh, sửa tham số JSON và nhấn Gửi lệnh. App hiển thị nguyên kết quả server để dễ kiểm tra.
- Chờ tối đa 25 giây; server chờ machine tối đa 20 giây. Không tự gửi lại lệnh khi lỗi vì lệnh cập nhật có thể đã được xử lý.
- Địa chỉ và mã máy chỉ giữ trong phiên đang mở. HTTP được bật để dùng server phát triển hiện tại.
- `machine/main.py` cần package `database` chưa có trong thư mục dự án này để xử lý lệnh thực tế.

Kiểm tra và build:

```powershell
flutter analyze
flutter test
flutter build apk --debug
```
