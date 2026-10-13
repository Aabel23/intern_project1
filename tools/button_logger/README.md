# FlexMix button logger

Ghi log nhiễu / bấm nút của bảng nút (PCF8575, I2C bus 1, 0x20) ra file Markdown, để xem qua đêm
vì sao máy `version1.1` thỉnh thoảng tự vào test mode (nút 15) hoặc restart (nút 14).

## Chạy trên Pi

```bash
pip install smbus2            # nếu chưa có (venv của version1.1 đã có)
cd flexmix_button_logger
nohup python3 button_logger.py --mode-file /đường/dẫn/version1.1/test_gui/mode.json > run.out 2>&1 &
```

- Log nằm ở `logs/button_log_<ngày_giờ>.md`. Mỗi dòng được ghi và fsync ngay nên mất điện vẫn còn log.
- Dừng: `pkill -INT -f button_logger.py` (script ghi phần **Tóm tắt** cuối file).
- Mặc định chỉ đọc, chạy song song với backend được. Muốn tách hẳn bus I2C: `sudo systemctl stop flexmix-backend`,
  chạy với `--init`, xong nhớ `sudo systemctl start flexmix-backend`.
- Thử trên máy không có Pi: `python3 button_logger.py --fake`.

## Đọc log

| Sự kiện | Ý nghĩa |
|---|---|
| `NHIỄU` | nút xuống rồi lên < 20 ms: nhiễu điện, không phải tay người |
| `NGẮN` / `BẤM` | < 350 ms / ≥ 350 ms |
| `MULTI` | ≥ 4 bit đổi cùng lúc: nhiễu bus, sụt áp hoặc dây I2C lỏng |
| `I2C-LỖI` | đọc chip thất bại |
| `KẸT-ĐỌC` | vòng đọc bị đứng > 100 ms |
| `TEST MODE BẬT/TẮT` | `mode.json` đổi; đối chiếu với dòng nút 15 ngay trước đó |

Nhìn nút 14 và 15 (có ⚠). Nếu có `NHIỄU` hoặc `NGẮN` trên 15 sát trước một dòng `TEST MODE BẬT` thì
đúng là nhiễu làm bật test mode. Nếu `TEST MODE BẬT` xuất hiện mà **không** có dòng nào ở nút 15 thì
nguyên nhân không nằm ở nút (ví dụ ghi `mode.json` từ nơi khác).

## Giới hạn

- Chu kỳ đọc mặc định 2 ms nên không thấy xung ngắn hơn khoảng đó. Nhiễu sub-ms mà backend (quét mỗi 250 ms) cũng không thấy.
- Mỗi phút ghi tối đa 60 dòng sự kiện, phần dư chỉ được đếm trong dòng nhịp ♥ và phần tóm tắt.
