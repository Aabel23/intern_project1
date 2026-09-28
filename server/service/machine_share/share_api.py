"""HTTP của chia sẻ máy: nhận POST từ app, đọc body, gọi flow, gửi JSON trả lời.

    POST /app/tao-ma-chia-se  {token, machine_id}            chủ tạo mã mời
    POST /app/nhan-chia-se    {token, code}                  nhân viên nhận mã
    POST /app/nhan-vien-may   {token, machine_id}            chủ xem nhân viên
    POST /app/thu-hoi-quyen   {token, machine_id, user_id}   chủ thu hồi quyền
"""

# Server chung: đường dẫn, xử lý HTTP
from server.config.routing import APP_ACCEPT_SHARE, APP_CREATE_SHARE, APP_MACHINE_STAFF, APP_REVOKE_STAFF
from server.lib.http_json import handle_routes, invalid, with_valid_status

# Trong module machine_share
from .share_flow import accept_invite, create_invite, list_staff, revoke_staff

ROUTES = with_valid_status({
    APP_CREATE_SHARE: create_invite,
    APP_ACCEPT_SHARE: accept_invite,
    APP_MACHINE_STAFF: list_staff,
    APP_REVOKE_STAFF: revoke_staff,
})
MAX_BODY = 4096


def handle(request):
    """True nếu request thuộc module này và đã trả lời (server chính chỉ gọi hàm này)."""
    return handle_routes(request, ROUTES, MAX_BODY, invalid)
