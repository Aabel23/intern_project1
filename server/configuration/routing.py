"""Mọi đường dẫn API của server hãng, gom một chỗ.

Tên biến: bỏ đoạn bên gọi, đổi "/" thành "_"; path máy gọi thêm tiền tố MACHINE_.
Path máy gọi phải khớp version1.1/machine/config/routing.py.

Server chỉ giữ tài khoản, danh sách máy và bản chuẩn quyền. Lệnh và câu hỏi
về menu, kho, đơn đi qua một route relay chung (MACHINE_COMMAND_SEND); server
chỉ đọc loại lệnh để kiểm quyền, không đọc nội dung.
"""

# ==========================================================================
# APP GỌI: /app/<đối_tượng>/<mục_tiêu>/<hành_động>
# ==========================================================================

# Tài khoản
USER_ACCOUNT_REGISTER = "/app/user/account/register"
USER_OTP_SEND = "/app/user/otp/send"                # gửi hoặc gửi lại OTP
USER_OTP_VERIFY = "/app/user/otp/verify"
USER_SESSION_LOGIN = "/app/user/session/login"
USER_SESSION_REFRESH = "/app/user/session/refresh"
USER_SESSION_BOOTSTRAP = "/app/user/session/bootstrap"
USER_SESSION_LOGOUT = "/app/user/session/logout"

# Máy của tài khoản
USER_MACHINE_LIST = "/app/user/machine/list"        # kèm vai trên từng máy
USER_MACHINE_ACTIVATE = "/app/user/machine/activate"  # bước cuối kích hoạt: nhận chủ
USER_MACHINE_REMOVE = "/app/user/machine/remove"    # Owner gỡ máy, máy về "chưa có chủ"
MACHINE_STATUS_GET = "/app/machine/status/get"      # online, phiên bản, phiên bản quyền

# Share và quyền (chỉ khi online)
MACHINE_SHARE_CREATE = "/app/machine/share/create"  # mã mời cho QR hoặc gói Bluetooth
MACHINE_SHARE_ACCEPT = "/app/machine/share/accept"  # người mới gửi mã mời lên
MACHINE_SHARE_SIGN = "/app/machine/share/sign"      # người share ký giấy phép
MACHINE_MEMBER_LIST = "/app/machine/member/list"
MACHINE_ROLE_UPDATE = "/app/machine/role/update"    # Owner nâng Employee lên Manager
MACHINE_MEMBER_REMOVE = "/app/machine/member/remove"
MACHINE_OWNER_TRANSFER = "/app/machine/owner/transfer"  # Owner cũ xuống Manager

# Relay lệnh và câu hỏi xuống máy, chờ trả lời
MACHINE_COMMAND_SEND = "/app/machine/command/send"


# ==========================================================================
# MÁY GỌI: /machine/<mục_tiêu>/<hành_động>
# ==========================================================================

MACHINE_ACTIVATION_SEND = "/machine/activation/send"  # trình giấy khai sinh khi vừa có wifi
MACHINE_HELLO_SEND = "/machine/hello/send"          # báo online, phiên bản phần mềm và hợp đồng
MACHINE_COMMAND_POLL = "/machine/command/poll"      # long-poll lấy lệnh
MACHINE_RESULT_SEND = "/machine/result/send"
MACHINE_PERMISSION_GET = "/machine/permission/get"  # bản sao quyền, giấy phép share mới
MACHINE_EVENT_SEND = "/machine/event/send"          # xả hộp thư đi: sự kiện, nhật ký theo người
MACHINE_UPDATE_GET = "/machine/update/get"          # hỏi bản phần mềm mới
MACHINE_UPDATE_REPORT = "/machine/update/report"    # báo cập nhật khoẻ hay đã quay về
