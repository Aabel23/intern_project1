"""Đường dẫn HTTP của server, chia theo module xử lý."""

# Tên biến: ĐỐI_TƯỢNG_MỤC_TIÊU_HÀNH_ĐỘNG; path: /<bên_gọi>/<đối_tượng>/<mục_tiêu>/<hành_động>,
# tiếng Anh, chữ thường. Bên gọi là app (token) hoặc machine (product_key); với bên
# gọi machine, đối tượng chính là máy nên bỏ: /machine/<mục_tiêu>/<hành_động>.
# Chi tiết trong MODULE_PATTERN.md.

# Đăng ký tài khoản và xác minh OTP
USER_ACCOUNT_REGISTER = "/app/user/account/register"
USER_OTP_SEND = "/app/user/otp/send"
USER_OTP_VERIFY = "/app/user/otp/verify"

# Đăng nhập và đăng xuất
USER_SESSION_LOGIN = "/app/user/session/login"
USER_SESSION_LOGOUT = "/app/user/session/logout"

# Đăng ký máy qua QR hoặc Bluetooth
USER_MACHINE_REGISTER = "/app/user/machine/register"

# Chia sẻ máy và quản lý quyền nhân viên
MACHINE_SHARE_CREATE = "/app/machine/share/create"
MACHINE_SHARE_ACCEPT = "/app/machine/share/accept"
MACHINE_STAFF_LIST = "/app/machine/staff/list"
MACHINE_STAFF_REVOKE = "/app/machine/staff/revoke"

# Dashboard — danh sách, đổi tên, gỡ máy và trạng thái kết nối
USER_MACHINE_LIST = "/app/user/machine/list"
MACHINE_NAME_UPDATE = "/app/machine/name/update"
USER_MACHINE_REMOVE = "/app/user/machine/remove"
MACHINE_STATUS_GET = "/app/machine/status/get"  # GET, app gọi

# Dashboard — đồng bộ Menu
MACHINE_MENU_GET = "/app/machine/menu/get"
MACHINE_MENU_UPDATE = "/app/machine/menu/update"
MACHINE_IMAGE_GET = "/app/machine/image/get"

# Dashboard — đồng bộ và nạp Kho
MACHINE_INGREDIENT_GET = "/app/machine/ingredient/get"
MACHINE_INGREDIENT_REFILL = "/app/machine/ingredient/refill"

# Cổng máy — long-poll nhận lệnh và trả kết quả
MACHINE_COMMAND_POLL = "/machine/command/poll"
MACHINE_RESULT_SEND = "/machine/result/send"
