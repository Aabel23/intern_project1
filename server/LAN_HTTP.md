# Bản đầu qua LAN/HTTP

App và máy cùng truy cập IP nội bộ của server. Giữ nguyên MySQL, SMTP, khóa HPKE/chữ ký và file trust; chỉ thay URL và lớp vận chuyển. Ví dụ khi IP LAN của server là `192.168.1.10`:

```bash
python3 server/tools/provision_keys.py --url http://192.168.1.10:8080
```

Trong `server/configuration/.env`, đặt `SERVER_TRANSPORT=http`, `SERVER_BIND_HOST=192.168.1.10`, `SERVER_BIND_PORT=8080`; bỏ `TLS_CERT_FILE` và `TLS_KEY_FILE`. `SERVER_BIND_HOST` phải là IP nội bộ cụ thể hoặc loopback, không phải `0.0.0.0`. Trên máy đặt `SERVER_URL=http://192.168.1.10:8080`; build app với URL đó theo [hướng dẫn Flutter](../flutter_app/README.md). Server vẫn kiểm phong bì và quyền trên cùng các route. Gmail SMTP vẫn cần server có đường gửi email ra ngoài.

Khi mở truy cập Internet, đặt lại `SERVER_TRANSPORT=https`, chứng chỉ TLS và URL HTTPS rồi build app/cấu hình máy với URL mới; routing và body nghiệp vụ giữ nguyên. Kiểm thử trên Android thật và Pi/LAN thật trước khi phát hành.
