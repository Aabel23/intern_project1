# Các file quản lý user

| File | Chức năng | Gọi tới |
| --- | --- | --- |
| [`demo_user_database.py`](../../../tests/python/demo_user_database.py) | Chạy thử việc thêm một user | `user_add.add_user()` |
| [`user_add.py`](user_add.py) | Chuẩn bị từng trường và ghi user vào bảng `users` | `server.lib.security.user_password.hash_password()`, `connection.get_connection()` |
| [`user_read.py`](user_read.py) | Đọc thông tin user từ bảng `users` | `connection.get_connection()` |
| [`connection.py`](../connection.py) | Mở và đóng kết nối SQLite | `config/path.py` để lấy đường dẫn database |

Luồng thêm user: `demo_user_database.py` → `user_add.add_user()` → `user_add.add_password()` → `user_add.hash_password()` → `connection.get_connection()` → bảng `users` trong `database.db`.

Luồng đọc user: mã gọi → `user_read.py` → `connection.get_connection()` → bảng `users`.

Chạy thử từ thư mục gốc dự án:

```powershell
python tests/python/demo_user_database.py
```

`demo_user_database.py` ghi vào database thật. Username hoặc email trùng sẽ không được thêm lần nữa.
