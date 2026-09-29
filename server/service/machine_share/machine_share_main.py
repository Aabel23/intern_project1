"""HTTP của chia sẻ máy: nhận POST từ app, đọc body, gọi flow, gửi JSON trả lời.

    POST /app/tao-ma-chia-se  {token, machine_id}            chủ tạo mã mời
    POST /app/nhan-chia-se    {token, code}                  nhân viên nhận mã
    POST /app/nhan-vien-may   {token, machine_id}            chủ xem nhân viên
    POST /app/thu-hoi-quyen   {token, machine_id, user_id}   chủ thu hồi quyền
"""

# Routing tập trung và HTTP dùng chung
from server.config.routing import MACHINE_SHARE_ACCEPT, MACHINE_SHARE_CREATE, MACHINE_STAFF_LIST, MACHINE_STAFF_REVOKE
from server.lib.http.http_json import handle_routes, invalid, with_valid_status

# Trong module machine_share
from .machine_share_create import create_invite
from .machine_share_accept import accept_invite
from .machine_staff_list import list_staff
from .machine_staff_revoke import revoke_staff


ROUTES = with_valid_status({
    MACHINE_SHARE_CREATE: create_invite,
    MACHINE_SHARE_ACCEPT: accept_invite,
    MACHINE_STAFF_LIST: list_staff,
    MACHINE_STAFF_REVOKE: revoke_staff,
})
MAX_BODY = 4096


def handle(request):
    """True nếu request thuộc module này và đã trả lời (server chính chỉ gọi hàm này)."""
    return handle_routes(request, ROUTES, MAX_BODY, invalid)
