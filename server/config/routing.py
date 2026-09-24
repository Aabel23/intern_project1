"""Đường dẫn HTTP do server cung cấp."""

MACHINE_STATUS = "/machine/trang-thai"
MACHINE_POLL_COMMAND = "/machine/hoi-lenh"
MACHINE_HEARTBEAT = "/machine/heartbeat"
MACHINE_SEND_RESULT = "/machine/tra-ket-qua"

APP_SEND_COMMAND = "/app/gui-lenh"
APP_REGISTER_USER = "/app/dang-ky-nguoi-dung"
APP_SEND_OTP = "/app/gui-ma-otp"
APP_VERIFY_OTP = "/app/xac-minh-otp"
APP_LOGIN = "/app/dang-nhap"
APP_VERIFY_LOGIN = "/app/xac-minh-dang-nhap"

APP_REGISTER_MACHINE = "/app/dang-ky-may"
APP_REGISTER_MACHINE_VERIFY = "/app/xac-minh-dang-ky-may"
APP_CREATE_SHARE = "/app/tao-ma-chia-se"
APP_ACCEPT_SHARE = "/app/nhan-chia-se"
APP_MY_MACHINES = "/app/may-cua-toi"

APP_SYNC_MACHINES = "/app/dong-bo-may"
APP_SYNC_MACHINES_VERIFY = "/app/xac-minh-dong-bo-may"
