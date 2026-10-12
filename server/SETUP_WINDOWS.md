# Chạy server FlexMix trên laptop Windows

Hướng dẫn dùng laptop làm server, MySQL lưu dữ liệu, Gmail gửi OTP và Tailscale cung cấp HTTPS.
Điện thoại và máy pha cần tham gia cùng mạng Tailscale với laptop, được phép truy cập server.
USB dùng để cài app; kết nối đến server đi qua Tailscale.

URL của laptop hiện tại: `https://abea.tailb17258.ts.net`.
Nếu triển khai trên laptop khác, thay tên miền và đường dẫn bằng thông tin của máy đó.

## 1. Vào project và bật MySQL

Mở PowerShell:

```powershell
cd D:\PROJECT\CODE\InternProj\androidv1.0\intern_project1
powershell -NoProfile -ExecutionPolicy Bypass -File server/tools/mysql.ps1 start
```

Trên laptop hiện tại, MySQL 8.4.11 đã cài ở `E:\Development\mysql-8.4.11-winx64`.
Dữ liệu và cấu hình nằm ở `E:\Development\mysql-flexmix`.
Database `flexmix` đã chạy migration 001/002 và có 8 bảng. Không chạy lại hai migration
trên database này. User app `flexmix` có quyền SELECT/INSERT/UPDATE/DELETE.

Kết quả mong đợi: `MySQL is running at 127.0.0.1:3306.`

Muốn kiểm tra bảng:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File server/tools/mysql.ps1 client
```

Trong cửa sổ `mysql>`:

```sql
USE flexmix;
SHOW TABLES;
EXIT;
```

`EXIT` chỉ thoát client, MySQL vẫn chạy nền.
Máy mới cần cài MySQL và tạo database theo [README](README.md); script trên dùng đường dẫn của laptop hiện tại.

## 2. Cài thư viện Python

Tạo môi trường riêng nếu chưa có:

```powershell
python -m venv server/secrets/venv
```

Nếu thư mục `server/secrets/venv` đã có, bỏ qua lệnh tạo môi trường. Cài thư viện:

```powershell
.\server\secrets\venv\Scripts\python.exe -m pip install -r server/requirements.txt
.\server\secrets\venv\Scripts\python.exe -m pip check
```

Các bước Python tiếp theo dùng môi trường này, không cần activate.

## 3. Giới hạn quyền đọc cấu hình và khóa

Thư mục `server/secrets` và file `.env` đã được bảo vệ trên laptop hiện tại.
Khi thiết lập máy mới, tạo thư mục và giới hạn quyền trước khi tạo khóa:

```powershell
New-Item -ItemType Directory -Path server/secrets -Force | Out-Null
$serverUser = [Security.Principal.WindowsIdentity]::GetCurrent().Name
icacls server/secrets /inheritance:r /grant:r "${serverUser}:(OI)(CI)F" "SYSTEM:(OI)(CI)F"
```

Server kiểm tra quyền `0600` trên Linux. Trên Windows, phần kiểm tra POSIX này được bỏ qua;
người vận hành phải bảo vệ file bằng ACL Windows. Giữ quyền thư mục chỉ cho tài khoản chạy server
và SYSTEM; kiểm tra lại quyền sau khi sao chép khóa từ máy khác.

## 4. Bật HTTPS và cấp chứng chỉ

Laptop đã cài Tailscale. Trên điện thoại, cài Tailscale, đăng nhập cùng mạng với laptop và bật kết nối.

Vào [trang DNS Tailscale](https://login.tailscale.com/admin/dns), bật **MagicDNS** và
**HTTPS Certificates**. Tài khoản cần có quyền cấu hình mạng Tailscale.

Kiểm tra tên miền của laptop:

```powershell
tailscale status --json | ConvertFrom-Json | ForEach-Object { $_.Self.DNSName }
```

Tên miền hiện tại là `abea.tailb17258.ts.net` (bỏ dấu chấm cuối khi dùng trong URL).
Cấp chứng chỉ cho server:

```powershell
tailscale cert --cert-file=server/secrets/tls.crt --key-file=server/secrets/tls.key abea.tailb17258.ts.net
```

Kết quả: `server/secrets/tls.crt` và `server/secrets/tls.key`.
Nếu Tailscale báo HTTPS chưa bật, kiểm tra lại trang DNS ở trên.
Xem [hướng dẫn HTTPS của Tailscale](https://tailscale.com/docs/how-to/set-up-https-certificates).

## 5. Tạo khóa server và cấu hình công khai cho app

```powershell
.\server\secrets\venv\Scripts\python.exe server/tools/provision_keys.py --url https://abea.tailb17258.ts.net
```

Lệnh này giữ khóa cũ nếu đã có và ghi:

- Khóa bí mật: `server/secrets/server-hpke.pem`, `server/secrets/server-sign.pem`.
- Cấu hình công khai: `server/secrets/server-trust.json`, `flutter_app/assets/server-trust.json`,
  `version1.1/machine/config/server-trust.json`.
- URL app: `flutter_app/lib/shared/cloud/server_endpoint.dart`.

Các khóa công khai và URL app được commit để máy khác có thể build app.
Khi chạy server đã triển khai trên máy khác, dùng lại khóa bí mật tương ứng;
không tạo khóa mới thay cho khóa đã dùng với app/máy phát hành.

## 6. Cấu hình Gmail gửi OTP

Trên Gmail dùng gửi OTP, bật xác minh hai bước rồi tạo **App password** tại
[Google App Passwords](https://myaccount.google.com/apppasswords).
Xem [hướng dẫn Google](https://support.google.com/accounts/answer/185833) nếu không thấy mục này.

Ý nghĩa các biến:

| Biến | Giá trị |
| --- | --- |
| `SMTP_USER` | Gmail server dùng để đăng nhập SMTP |
| `SMTP_FROM` | Địa chỉ người gửi hiển thị trong email OTP |
| `SMTP_APP_PASSWORD` | App password của Gmail đó; nhập liền, không thêm dấu cách phân nhóm |

Code hiện yêu cầu `SMTP_USER` và `SMTP_FROM` giống nhau.
`SMTP_APP_PASSWORD` là App password, không phải mật khẩu đăng nhập Gmail thông thường.
Server gửi qua `smtp.gmail.com:587` với STARTTLS; laptop cần truy cập được địa chỉ này.

## 7. Hoàn thiện file .env

```powershell
notepad server/configuration/.env
```

Giữ nguyên 5 dòng `DB_...` đã được tạo khi setup MySQL. Thêm các dòng dưới đây,
thay email, App password và OTP secret bằng giá trị của bạn. Không thêm dấu nháy:

```dotenv
SMTP_USER=your-email@gmail.com
SMTP_FROM=your-email@gmail.com
SMTP_APP_PASSWORD=your-app-password
APP_ENV=production
OTP_HASH_SECRET=replace-with-generated-value
SERVER_BIND_HOST=127.0.0.1
SERVER_BIND_PORT=8443
TLS_CERT_FILE=D:/PROJECT/CODE/InternProj/androidv1.0/intern_project1/server/secrets/tls.crt
TLS_KEY_FILE=D:/PROJECT/CODE/InternProj/androidv1.0/intern_project1/server/secrets/tls.key
SERVER_HPKE_KEY_FILE=D:/PROJECT/CODE/InternProj/androidv1.0/intern_project1/server/secrets/server-hpke.pem
SERVER_SIGNING_KEY_FILE=D:/PROJECT/CODE/InternProj/androidv1.0/intern_project1/server/secrets/server-sign.pem
SERVER_TRUST_FILE=D:/PROJECT/CODE/InternProj/androidv1.0/intern_project1/server/secrets/server-trust.json
```

Tạo giá trị cho `OTP_HASH_SECRET` một lần, rồi lưu kết quả vào `.env`:

```powershell
.\server\secrets\venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
```

Không đổi OTP secret mỗi lần khởi động. Với `APP_ENV=production`, không đặt
`TEST_RECIPIENT_ALLOWLIST` trong `.env` hoặc môi trường PowerShell.
Chế độ `test` chỉ cho gửi tới hai email được chỉ định trong `server/configuration/skeleton.py`.

Bảo vệ file cấu hình:

```powershell
$serverUser = [Security.Principal.WindowsIdentity]::GetCurrent().Name
icacls server/configuration/.env /inheritance:r /grant:r "${serverUser}:F" "SYSTEM:F"
```

## 8. Chạy trực tiếp main.py

Tại thư mục gốc project, chạy:

```powershell
.\server\secrets\venv\Scripts\python.exe -m server.main
```

`main.py` tự đọc `server/configuration/.env`. Biến môi trường đã có trong process
được ưu tiên hơn `.env`. Không cần script PowerShell để nạp cấu hình.

Server chạy ngay trong terminal và hiện log:

```text
22:30:00 INFO SERVER_READY https://127.0.0.1:8443 — Ctrl+C to stop
22:30:05 INFO HTTP POST /app/user/session/bootstrap -> 200
```

Giữ cửa sổ mở. Nhấn `Ctrl+C` để tắt; terminal sẽ hiện `SERVER_STOPPED`.
Log request ghi phương thức, route API và mã HTTP; không ghi mật khẩu, OTP, token hoặc body.

## 9. Cho điện thoại truy cập qua HTTPS

Mở PowerShell thứ hai:

```powershell
tailscale serve --bg --https=443 https+insecure://127.0.0.1:8443
tailscale serve status
curl.exe -i -X POST https://abea.tailb17258.ts.net/
```

Kết quả mong đợi: HTTP `404` và `INVALID_ENVELOPE`, vì `/` không phải route API.
Điều này kiểm tra HTTPS và việc chuyển tiếp đến server, chưa kiểm tra database hay gửi OTP.

Tailscale Serve chỉ chia sẻ trong mạng Tailscale theo quyền truy cập của mạng.
`https+insecure` bỏ xác minh chứng chỉ ở kết nối loopback từ Tailscale tới Python;
HTTPS từ điện thoại tới Tailscale vẫn xác minh chứng chỉ.
Xem [tài liệu Tailscale Serve](https://tailscale.com/docs/reference/tailscale-cli/serve).

## 10. Build lại app và thử đăng ký

App cần được build lại sau khi thay khóa công khai hoặc URL:

```powershell
cd D:\PROJECT\CODE\InternProj\androidv1.0\intern_project1\flutter_app
flutter devices
flutter run -d R5CWC220YTZ
```

`R5CWC220YTZ` là điện thoại hiện tại; nếu đổi máy, lấy ID từ `flutter devices`.
Bật Tailscale trên điện thoại, đăng ký tài khoản, nhận và xác minh OTP, rồi đăng nhập.
Kiểm tra này mới xác nhận luồng app, server, MySQL và Gmail hoạt động cùng nhau.

## Bật lại, gia hạn và sao lưu

- Sau khi khởi động laptop: bật MySQL ở bước 1 và chạy Python ở bước 8.
  Tailscale Serve chạy nền với `--bg`; kiểm tra lại bằng `tailscale serve status`.
- Khi thay `.env`: nhấn `Ctrl+C` và chạy lại Python để đọc cấu hình mới.
- Khi cần tắt MySQL: chạy `powershell -ExecutionPolicy Bypass -File server/tools/mysql.ps1 stop`.
  Tắt Python trước khi tắt MySQL.
- Chứng chỉ do `tailscale cert` ghi ra cần gia hạn trước khi hết hạn: chạy lại lệnh ở bước 4,
  rồi khởi động lại Python. Tailscale quản lý chứng chỉ phía Serve riêng.
- Giữ laptop bật, có mạng và không sleep trong lúc phục vụ app.
- Sao lưu database bằng công cụ MySQL; chỉ sao chép thư mục dữ liệu thô khi MySQL đã tắt hoàn toàn.
  Sao lưu riêng `.env` và khóa server ở nơi được bảo vệ để phục hồi đúng khóa đang dùng.
- `.env`, `server/secrets` và dữ liệu MySQL không được commit. File trust chứa khóa công khai có thể commit.

## Các lỗi thường gặp

| Lỗi | Kiểm tra |
| --- | --- |
| App báo không tải được cấu hình an toàn | File trust không còn `{}`, URL đúng HTTPS và đã build lại app |
| Server báo `CONFIG_INVALID` | `.env` đúng dạng `TEN_BIEN=gia_tri`, không còn placeholder, các đường dẫn tuyệt đối và file khóa/chứng chỉ tồn tại |
| HTTPS trả `502` | Python có chạy ở `127.0.0.1:8443` không; xem cấu hình `tailscale serve status` |
| Điện thoại không kết nối | Tailscale đã bật, cùng mạng, có quyền truy cập laptop và URL đúng tên miền |
| Server trả `SERVICE_UNAVAILABLE` | MySQL đang chạy, cấu hình `DB_...` đúng và đã chạy migration |
| `MAIL_UNAVAILABLE` | Email/App password đúng, laptop truy cập được SMTP; xem log `MAIL_AUTH`, `MAIL_SEND`, `MAIL_TIMEOUT` |
| `TEST_RECIPIENT_NOT_ALLOWED` | Đang dùng chế độ `test` và email nằm ngoài allowlist |
