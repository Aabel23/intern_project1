"""Các giá trị cấu hình dùng chung của server."""

from .path import EMAIL_ENV_PATH

SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8000
HEARTBEAT_TIMEOUT_SECONDS = 15
COMMAND_TIMEOUT_SECONDS = 20
# Máy hỏi lệnh được giữ tối đa chừng này giây (long-poll); nhỏ hơn timeout 10s của máy.
POLL_WAIT_SECONDS = 8

# Tài khoản gửi mail và mật khẩu nằm trong config/.env, không ghi vào mã nguồn.
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465
SMTP_TIMEOUT_SECONDS = 10

# Token phiên đăng nhập của app.
SESSION_TTL_SECONDS = 30 * 24 * 3600
# 32 byte ngẫu nhiên -> token base64url 43 ký tự.
TOKEN_BYTES = 32
# Lọc thô độ dài token nhận từ app trước khi tra DB.
TOKEN_MIN_LENGTH = 20
TOKEN_MAX_LENGTH = 100

# Mã mời chia sẻ máy, dùng một lần.
INVITE_TTL_SECONDS = 5 * 60
# 24 byte ngẫu nhiên -> mã base64url 32 ký tự.
INVITE_CODE_BYTES = 24
INVITE_CODE_MIN_LENGTH = 20
INVITE_CODE_MAX_LENGTH = 100


def read_env(name: str) -> str:
    """Đọc một khóa trong config/.env khi cần, tránh nạp secret lúc import module."""
    for line in EMAIL_ENV_PATH.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator and key.strip() == name:
            value = value.strip().strip('"\'')
            if value:
                return value
    raise ValueError(f"Thiếu {name} trong {EMAIL_ENV_PATH}")


def get_smtp_password() -> str:
    return read_env("SMTP_PASSWORD")


def get_service_email() -> str:
    return read_env("SERVICE_EMAIL")
