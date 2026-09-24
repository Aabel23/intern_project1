"""Gửi mã OTP xác minh email qua Gmail."""

import smtplib
import sys
from email.message import EmailMessage
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from server.config.config import (
    SERVICE_EMAIL,
    SMTP_HOST,
    SMTP_PORT,
    SMTP_TIMEOUT_SECONDS,
    get_smtp_password,
)
from .otp_generator import OTP_TTL_SECONDS

SUBJECT = "Mã xác minh email"


def build_email(client_mail, code):
    """Tạo email chứa mã OTP."""
    minutes = OTP_TTL_SECONDS // 60
    email = EmailMessage()
    email["From"] = SERVICE_EMAIL
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
        smtp.login(SERVICE_EMAIL, get_smtp_password())
        smtp.send_message(email)


def send_otp(client_mail, code):
    """Chỉ gửi mã được truyền vào. otp_flow quản lý cooldown và trạng thái."""
    try:
        send_email(build_email(client_mail, code))
    except (smtplib.SMTPException, OSError, ValueError):
        return "Không gửi được email, vui lòng thử lại"
    return None
