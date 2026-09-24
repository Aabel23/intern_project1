"""Nối endpoint với luồng. Chạy: python -m server.service.user_register.main"""
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from server.config.routing import APP_REGISTER_USER, APP_SEND_OTP, APP_VERIFY_OTP
from server.service.user_register.user_register.registration_flow import (
    receive_register,
    resend_otp,
    confirm_otp,
    cleanup,
)
from server.service.user_register.user_register.user_register_api import run_api

ROUTES = {
    APP_REGISTER_USER: receive_register,
    APP_SEND_OTP: resend_otp,
    APP_VERIFY_OTP: confirm_otp,
}

if __name__ == "__main__":
    run_api(ROUTES, cleanup)
