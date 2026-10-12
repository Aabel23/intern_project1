"""Send one OTP-style test email with the inherited Gmail SMTP flow.

Fill SERVICE_EMAIL and SMTP_PASSWORD in server/configuration/.env, then run:
    python3 tests/manual/send_otp_smtp.py

This checks delivery only; the code is not stored or valid for registration.
"""

from email.message import EmailMessage
from pathlib import Path
import secrets
import smtplib


RECIPIENT = "nguyenhoanganh15112005@gmail.com"
ENV_PATH = Path(__file__).resolve().parents[2] / "server" / "configuration" / ".env"


def read_env(name: str) -> str:
    if not ENV_PATH.is_file():
        raise SystemExit(f"Missing config file: {ENV_PATH}")
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator and key.strip() == name:
            value = value.strip().strip('"\'')
            if value:
                return value
    raise SystemExit(f"Fill {name} in {ENV_PATH}")


def build_email(sender: str, code: str) -> EmailMessage:
    email = EmailMessage()
    email["From"] = sender
    email["To"] = RECIPIENT
    email["Subject"] = "FlexMix - mã OTP thử nghiệm"
    email.set_content(
        f"Mã OTP thử nghiệm của bạn là: {code}\n\n"
        "Đây là thử nghiệm gửi email. Mã này chưa được gắn với tài khoản "
        "và không thể dùng để xác minh trên ứng dụng.\n"
    )
    return email


def main() -> None:
    sender = read_env("SERVICE_EMAIL")
    password = read_env("SMTP_PASSWORD")
    code = f"{secrets.randbelow(1_000_000):06d}"
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as smtp:
        smtp.login(sender, password)
        smtp.send_message(build_email(sender, code))
    print(f"SMTP accepted test email for {RECIPIENT}.")
    print("Check the recipient inbox. The OTP is not shown here.")


if __name__ == "__main__":
    main()
