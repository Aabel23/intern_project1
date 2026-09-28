"""Route chia sẻ máy; module tự nghe, server.main chỉ gọi handle()."""

from server.config.routing import (
    APP_ACCEPT_SHARE,
    APP_CREATE_SHARE,
    APP_MACHINE_STAFF,
    APP_REVOKE_STAFF,
)
from server.lib.valid_api import handle_valid_routes
from .share_flow import accept_invite, create_invite, list_staff, revoke_staff


ROUTES = {
    APP_CREATE_SHARE: create_invite,
    APP_ACCEPT_SHARE: accept_invite,
    APP_MACHINE_STAFF: list_staff,
    APP_REVOKE_STAFF: revoke_staff,
}


def handle(request):
    """True nếu request thuộc module này và đã trả lời (server chính chỉ gọi hàm này)."""
    return handle_valid_routes(request, ROUTES)
