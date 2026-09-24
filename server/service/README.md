# Gửi email thử

1. Tạo Gmail App Password cho tài khoản gửi `vananhbo2@gmail.com`.
2. Mở `server/config/.env`, điền **App Password gồm 16 ký tự** sau dấu `=`: `SMTP_PASSWORD=abcdefghijklmnop`. Không điền mật khẩu Gmail thường, không thêm dấu nháy.
3. Chạy từ thư mục gốc dự án:

```powershell
.\.venv\Scripts\python.exe -m server.service.email_test
```

Script gửi thư thử tới địa chỉ `client_mail` trong `email_test.py`. File `.env` và thư mục `.venv` được bỏ qua bởi `.gitignore`; không chia sẻ file `.env` cho người khác.
