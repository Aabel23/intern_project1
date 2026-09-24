"""Route chia sẻ máy; server.main gộp vào cùng cổng với các API khác."""

from server.config.routing import (
    APP_ACCEPT_SHARE,
    APP_CREATE_SHARE,
    APP_MACHINE_STAFF,
    APP_MY_MACHINES,
    APP_REVOKE_STAFF,
)
from .share_flow import accept_invite, create_invite, list_my_machines, list_staff, revoke_staff


ROUTES = {
    APP_CREATE_SHARE: create_invite,
    APP_ACCEPT_SHARE: accept_invite,
    APP_MY_MACHINES: list_my_machines,
    APP_MACHINE_STAFF: list_staff,
    APP_REVOKE_STAFF: revoke_staff,
}
