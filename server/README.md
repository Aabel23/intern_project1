# Server FlexMix

Python stdlib HTTPS + MySQL. Mọi body nằm trong phong bì HPKE (`contracts/messages/cloud-protection.md`,
`v2-decisions.md`). Một process, không cần Redis hay framework.

## Dựng lần đầu

1. **Khóa và cấu hình công khai** (một lần, rồi commit các file công khai nó ghi ra):

   ```bash
   pip install -r server/requirements.txt
   python3 server/tools/provision_keys.py --url https://<tên miền server>
   ```

   Khóa bí mật nằm ở `server/secrets/` (gitignore). Chép thư mục đó lên máy chủ. Mất khóa hay
   đổi khóa thì mọi app/máy đã phát hành phải cập nhật lại.

2. **MySQL 8**: tạo database và user, rồi chạy lần lượt `server/migrations/001_accounts.sql`,
   `002_devices_sessions.sql`.

3. **Chứng chỉ HTTPS** từ CA công khai cho đúng tên miền (ví dụ certbot/Let's Encrypt).

4. **Biến môi trường** (đường dẫn tuyệt đối; file khóa quyền 0600):

   ```bash
   DB_HOST=127.0.0.1  DB_PORT=3306  DB_NAME=flexmix  DB_USER=flexmix  DB_PASSWORD=...
   SMTP_USER=<gmail>  SMTP_FROM=<gmail>  SMTP_APP_PASSWORD=<app password Gmail>
   OTP_HASH_SECRET=<32 byte base64url: python3 -c "import secrets,base64;print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip('='))">
   APP_ENV=production            # hoặc test + TEST_RECIPIENT_ALLOWLIST=<hai email thử>
   SERVER_BIND_HOST=0.0.0.0  SERVER_BIND_PORT=443
   TLS_CERT_FILE=/etc/letsencrypt/live/<miền>/fullchain.pem
   TLS_KEY_FILE=/etc/letsencrypt/live/<miền>/privkey.pem
   SERVER_HPKE_KEY_FILE=.../server/secrets/server-hpke.pem
   SERVER_SIGNING_KEY_FILE=.../server/secrets/server-sign.pem
   SERVER_TRUST_FILE=.../server/secrets/server-trust.json
   ```

5. Chạy từ thư mục gốc repo: `python3 -m server.main`.

## Đăng ký máy ở xưởng

Trên Pi: `cd version1.1 && python3 -m machine.config.provision --name FlexMix-02` in ra
`operator_command`. Chạy lệnh đó trên server (cần biến DB_*):

```bash
python3 -m server.src.factory_register --serial <serial> --name FlexMix-02 --public-key <b64u>
python3 -m server.src.factory_register --serial <serial> --unbind      # gỡ chủ (có audit)
```

Trường `qr` in ra là nội dung tem niêm phong dán lên máy.

## Test

```bash
TEST_DB_NAME=flexmix_test TEST_DB_HOST=127.0.0.1 TEST_DB_PORT=3306 TEST_DB_USER=... TEST_DB_PASSWORD=... \
  PYTHONPATH=. python3 -m unittest discover -s tests/server
python3 -m unittest discover -s tests/machine
```
