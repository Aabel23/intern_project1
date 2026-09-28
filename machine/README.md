# Phần mềm máy FlexMix (Raspberry Pi)

Máy pha nối với server qua relay HTTP và ghép đôi với app qua Bluetooth.
Tầng dữ liệu (`database.*`, MySQL) nằm ở mã nguồn máy pha `version1.0`, không có trong repo này.

## Cấu hình riêng của từng máy

Tên, product key và địa chỉ server **không nằm trong mã nguồn**. Mỗi máy có một file
`machine/config/machine.env` (đã có trong `.gitignore`):

```
MACHINE_NAME=FlexMix-02
PRODUCT_KEY=fm_<32 ký tự hex ngẫu nhiên>
SERVER_URL=http://<IP server>:8000
```

Tạo cho máy mới (sinh key ngẫu nhiên, không bao giờ ghi đè file đã có):

```sh
python -m machine.config.create_env --name FlexMix-02 --server http://192.168.1.10:8000
python machine_qr.py --from-env          # in tem QR dán lên máy
```

Muốn để file ở chỗ khác (ví dụ `/etc/flexmix/machine.env`) thì đặt biến môi trường
`FLEXMIX_MACHINE_ENV`. Product key là bí mật của máy: ai có key có thể đăng ký
chiếm máy trước chủ thật, nên không commit, không gửi qua chat.

## Chạy

```sh
# Relay: heartbeat + nhận lệnh từ app (cần package database của máy pha trên PYTHONPATH)
cd machine && python main.py
# Bluetooth pairing trên Pi (xem pairing/README.md)
python3 -m machine.pairing.bluetooth_pairing
```

## Giao thức relay

Máy xưng danh bằng `product_key` trong mọi request; server tra ra `machine_id` đã cấp
lúc app đăng ký máy, nên máy không cần biết ID của mình.

| Request | Body | Ý nghĩa |
| --- | --- | --- |
| POST `/machine/heartbeat` | `product_key` | báo máy còn sống (mỗi 5 giây) |
| POST `/machine/hoi-lenh` | `product_key` | long-poll lấy lệnh `{id, instruction, data}` trong hộp thư của máy này, `lenh` null nếu hết giờ chờ |
| POST `/machine/tra-ket-qua` | `product_key`, `id`, `ket_qua` | trả kết quả cho app đang chờ |

`main.py` tra `instruction` trong bảng `COMMANDS` gộp từ các module (`menu_sync/`,
`ingredient_sync/`), mỗi module một bảng `{instruction: hàm}`; xem
`server/service/dashboard_sync/README.md` cho từng lệnh.

Key sai hoặc chưa đăng ký thì server trả 403. Lỗi trong lúc chạy lệnh (tham số sai,
MySQL mất kết nối) được trả về app dạng `{"loi": ...}`, vòng lặp của máy vẫn chạy tiếp.

## Kiểm tra

```sh
python -m unittest machine.pairing.test_bluetooth_pairing machine.test_relay -v
```

`test_relay` chạy vòng lặp thật của `main.py` với server thật (SQLite tạm) và database máy giả.
Muốn thử với app trên điện thoại mà không có Pi: xem `sandbox/README.md`.
