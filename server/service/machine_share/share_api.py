"""Route chia sẻ máy; server.main gộp vào cùng cổng với các API khác."""

from server.config.routing import APP_ACCEPT_SHARE, APP_CREATE_SHARE, APP_MY_MACHINES
from .share_flow import accept_invite, create_invite, list_my_machines


ROUTES = {
    APP_CREATE_SHARE: create_invite,
    APP_ACCEPT_SHARE: accept_invite,
    APP_MY_MACHINES: list_my_machines,
}
