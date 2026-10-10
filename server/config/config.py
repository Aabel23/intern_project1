"""Các giá trị cấu hình dùng chung của server."""

SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8000
# Máy rảnh: poll hoặc gửi kết quả cuối cách đây dưới chừng này giây thì còn online.
# Phải lớn hơn POLL_WAIT_SECONDS để máy đang treo một poll luôn được tính là online.
MACHINE_SEEN_TIMEOUT_SECONDS = 15
COMMAND_TIMEOUT_SECONDS = 20
# Máy hỏi lệnh được giữ tối đa chừng này giây (long-poll); nhỏ hơn timeout 10s của máy.
POLL_WAIT_SECONDS = 8

# Token phiên đăng nhập của app.
SESSION_TTL_SECONDS = 30 * 24 * 3600
# 32 byte ngẫu nhiên -> token base64url 43 ký tự.
TOKEN_BYTES = 32
# Lọc thô độ dài token nhận từ app trước khi tra DB.
TOKEN_MIN_LENGTH = 20
TOKEN_MAX_LENGTH = 100
