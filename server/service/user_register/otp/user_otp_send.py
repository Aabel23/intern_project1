"""Gửi mã OTP xác minh email qua Gmail."""

import smtplib
from email.message import EmailMessage

from server.config.path import EMAIL_ENV_PATH
from .user_otp_generate import OTP_TTL_SECONDS

# Tài khoản gửi mail và mật khẩu nằm trong config/.env, không ghi vào mã nguồn.
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465
SMTP_TIMEOUT_SECONDS = 10

SUBJECT = "Mã xác minh email"


def build_email(client_mail, code):
    """Tạo email chứa mã OTP."""
    minutes = OTP_TTL_SECONDS // 60
    email = EmailMessage()
    email["From"] = get_service_email()
    email["To"] = client_mail
    email["Subject"] = SUBJECT
    email.set_content(
        f"Mã xác minh của bạn là: {code}\n\n"
        f"Mã có hiệu lực trong {minutes} phút và chỉ dùng được một lần.\n"
        "Nếu bạn không yêu cầu mã này, hãy bỏ qua email."
    )
    return email


def send_email(email):
    """Gửi email qua SMTP. Tách riêng để dễ thay thế khi test."""
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT_SECONDS) as smtp:
        smtp.login(get_service_email(), get_smtp_password())
        smtp.send_message(email)


def send_otp(client_mail, code):
    """Chỉ gửi mã được truyền vào. user_otp_process quản lý cooldown và trạng thái."""
    try:
        send_email(build_email(client_mail, code))
    except (smtplib.SMTPException, OSError, ValueError):
        return "Không gửi được email, vui lòng thử lại"
    return None


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
