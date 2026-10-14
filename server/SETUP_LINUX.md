# Chạy server FlexMix trên Linux

> Hướng dẫn này ghi cách dựng HTTPS qua tailnet. Bản đầu LAN/HTTP theo quyết định mới xem mục **Bản đầu qua LAN/HTTP** trong [server/README.md](README.md); không dùng các lệnh chứng chỉ/Tailscale bên dưới cho đường LAN đó.

Hướng dẫn này dành cho Ubuntu có MySQL 8, Python 3, Tailscale và một bản sao repo. Điện thoại Android và máy pha phải truy cập được máy Linux qua cùng tailnet. Chạy các lệnh từ **thư mục gốc repo**. Đây là cách dựng server để nghiệm thu trên thiết bị thật; chưa thay cho biên bản nghiệm thu [I-01](../documentation/plan/tasks/archive/I-01-skeleton-acceptance.md).

Server Python tự phục vụ HTTPS ở `127.0.0.1:8443`; Tailscale Serve đưa nó ra `https://<tên-máy>.ts.net` trong tailnet. Server cần MySQL, Gmail SMTP, hai khóa ứng dụng và chứng chỉ TLS. Không có chế độ chạy HTTP hoặc khóa placeholder.

## 1. Chuẩn bị Python và MySQL

Trên Ubuntu, cài các gói còn thiếu theo trình quản lý gói của máy. Ví dụ:

```bash
sudo apt update
sudo apt install python3 python3-venv mysql-server
```

Nếu chuyển từ server cũ, **khôi phục database cũ** để giữ tài khoản, quyền sở hữu máy và phiên; không chạy lại migration trên database đã có bảng. Với database mới hoàn toàn, tạo database và user ứng dụng:

```bash
sudo mysql
```

Trong cửa sổ `mysql>`, nhập các lệnh sau và thay mật khẩu mẫu bằng mật khẩu riêng:

```sql
CREATE DATABASE flexmix CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
CREATE USER 'flexmix'@'127.0.0.1' IDENTIFIED BY '<mật-khẩu-mạnh>';
GRANT SELECT, INSERT, UPDATE, DELETE ON flexmix.* TO 'flexmix'@'127.0.0.1';
EXIT;
```

Chạy migration **chỉ một lần** cho database mới, bằng tài khoản quản trị MySQL:

```bash
sudo mysql flexmix < server/migrations/001_accounts.sql
sudo mysql flexmix < server/migrations/002_devices_sessions.sql
mysql -h 127.0.0.1 -u flexmix -p flexmix -e 'SHOW TABLES;'
```

Lệnh cuối hỏi mật khẩu ứng dụng và phải liệt kê các bảng. Nếu MySQL đã đặt trên máy khác, dùng địa chỉ/tài khoản tương ứng trong `.env`; không chạy các lệnh tạo database ở trên.

Tạo môi trường Python trong thư mục đã được Git bỏ qua:

```bash
mkdir -p server/secrets
chmod 700 server/secrets
python3 -m venv server/secrets/venv
server/secrets/venv/bin/python -m pip install -r server/requirements.txt
server/secrets/venv/bin/python -m pip check
```

## 2. Chuyển khóa ứng dụng và xác định URL

Nếu Linux **thay server cũ**, chép an toàn ba file sau từ `server/secrets/` của server cũ sang cùng thư mục trên Linux: `server-hpke.pem`, `server-sign.pem`, `server-trust.json`. Repo không chứa các khóa bí mật. Giữ nguyên database nếu đây là cùng hệ thống. Không chạy `provision_keys.py` trước khi chép khóa: nếu thiếu file, lệnh sẽ tạo khóa mới. Khóa mới buộc app và máy cập nhật cấu hình công khai trước khi kết nối được.

```bash
chmod 600 server/secrets/server-hpke.pem server/secrets/server-sign.pem
```

Nếu đây là hệ thống **mới hoàn toàn**, bỏ bước chép khóa. Bước `provision_keys.py` bên dưới sẽ tạo cặp khóa mới. Không gửi hoặc commit `server/secrets/` hay `server/configuration/.env`.

Cài và đăng nhập Tailscale theo [hướng dẫn Linux](https://tailscale.com/docs/install/linux). Trong trang DNS của tailnet, bật MagicDNS và HTTPS Certificates. Xem tên DNS của **chính máy Linux** bằng `tailscale status`; tên cũ `abea.tailb17258.ts.net` trong repo là của máy Windows, không tự chuyển sang máy Linux. Đặt biến shell cho tên mới, không có `https://` và không có dấu chấm cuối:

```bash
FLEXMIX_FQDN='<tên-máy-linux>.<tailnet>.ts.net'
```

Cấp chứng chỉ cho tên đó. Nếu lệnh cần `sudo`, sau khi cấp hãy chuyển quyền sở hữu `tls.crt` và `tls.key` về tài khoản chạy server:

```bash
tailscale cert \
  --cert-file="$PWD/server/secrets/tls.crt" \
  --key-file="$PWD/server/secrets/tls.key" \
  "$FLEXMIX_FQDN"
chmod 600 server/secrets/tls.key
```

Chứng chỉ cấp bằng `tailscale cert` ra file cần được [gia hạn định kỳ](https://tailscale.com/docs/how-to/set-up-https-certificates); Tailscale không tự cài bản gia hạn vào các đường dẫn này.

Sau khi khóa cũ đã có mặt, hoặc khi dựng hệ thống mới, ghi URL và cấu hình công khai:

```bash
server/secrets/venv/bin/python server/tools/provision_keys.py \
  --url "https://$FLEXMIX_FQDN"
```

Lệnh giữ khóa bí mật đã có, ghi `server/secrets/server-trust.json`, `flutter_app/assets/server-trust.json`, `version1.1/machine/config/server-trust.json` và URL mặc định trong `flutter_app/lib/shared/cloud/server_endpoint.dart`. Nếu URL hoặc khóa công khai đổi, build lại app. Trên máy pha, đặt `SERVER_URL=https://<tên-máy-linux>.<tailnet>.ts.net` trong `machine.env` (xem `version1.1/machine/config/env.py`) và cập nhật file trust của máy nếu khóa đổi.

## 3. Tạo cấu hình riêng của server

Tạo `server/configuration/.env` bằng editor trên Linux. Thay mọi giá trị mẫu; các đường dẫn phải là đường dẫn **tuyệt đối** (`pwd -P` giúp lấy đường dẫn repo). Không dùng lại đường dẫn `D:/...` từ Windows. File `.env` không dùng cú pháp `export` hay dấu nháy bao giá trị.

```dotenv
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=flexmix
DB_USER=flexmix
DB_PASSWORD=<mật-khẩu-MySQL>
SMTP_USER=<gmail-gửi-OTP>
SMTP_FROM=<cùng-gmail-gửi-OTP>
SMTP_APP_PASSWORD=<app-password-Gmail>
OTP_HASH_SECRET=<giá-trị-cố-định-đã-tạo>
APP_ENV=test
TEST_RECIPIENT_ALLOWLIST=<hai-email-thử-đúng-theo-skeleton.py>
SERVER_BIND_HOST=127.0.0.1
SERVER_BIND_PORT=8443
TLS_CERT_FILE=/đường/dẫn/repo/server/secrets/tls.crt
TLS_KEY_FILE=/đường/dẫn/repo/server/secrets/tls.key
SERVER_HPKE_KEY_FILE=/đường/dẫn/repo/server/secrets/server-hpke.pem
SERVER_SIGNING_KEY_FILE=/đường/dẫn/repo/server/secrets/server-sign.pem
SERVER_TRUST_FILE=/đường/dẫn/repo/server/secrets/server-trust.json
```

Tạo `OTP_HASH_SECRET` một lần bằng `server/secrets/venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(32))'`, rồi lưu kết quả trong `.env`. Nếu chuyển server cũ, giữ nguyên giá trị cũ. `SMTP_USER` và `SMTP_FROM` phải giống nhau; SMTP dùng App Password của Gmail. `APP_ENV=test` chỉ cho gửi tới **đúng hai địa chỉ** trong `server/configuration/skeleton.py`; điền cả hai, cách nhau bằng dấu phẩy. Khi dùng `APP_ENV=production`, xóa hẳn dòng `TEST_RECIPIENT_ALLOWLIST`. Biến môi trường đã đặt trong process sẽ được ưu tiên hơn `.env`.

```bash
chmod 600 server/configuration/.env
```

Server trên Linux yêu cầu các file `TLS_KEY_FILE`, `SERVER_HPKE_KEY_FILE`, `SERVER_SIGNING_KEY_FILE` có mode **chính xác `0600`** và đọc được bởi tài khoản chạy Python.

## 4. Chạy server và mở đường qua Tailscale

Trong terminal thứ nhất, tại thư mục gốc repo:

```bash
server/secrets/venv/bin/python -m server.main
```

Đợi log `SERVER_READY https://127.0.0.1:8443`. Giữ terminal mở; `Ctrl+C` để dừng. Nếu nhận `CONFIG_INVALID`, kiểm lại `.env`, file khóa, quyền `0600`, chứng chỉ và URL/trust tương ứng. Server khởi động được chưa chứng minh MySQL hay Gmail hoạt động.

Trong terminal thứ hai:

```bash
tailscale serve --bg --https=443 https+insecure://127.0.0.1:8443
tailscale serve status
curl -i -X POST "https://$FLEXMIX_FQDN/"
```

`/` không phải API: kết quả mong đợi là HTTP `404` với `INVALID_ENVELOPE`. Nó chỉ kiểm HTTPS và đường chuyển tiếp. `https+insecure` bỏ kiểm chứng chỉ **ở kết nối loopback từ Tailscale Serve tới Python**; điện thoại vẫn kiểm chứng chỉ HTTPS của tên Tailscale. Xem [Tailscale Serve](https://tailscale.com/docs/reference/tailscale-cli/serve).

Sau đó bật Tailscale trên điện thoại và máy pha, build/chạy app theo [README Flutter](../flutter_app/README.md), thử đăng ký bằng email thật và hỏi trạng thái máy theo [I-01](../documentation/plan/tasks/archive/I-01-skeleton-acceptance.md). Không coi `curl /` là nghiệm thu luồng sản phẩm.
