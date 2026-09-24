"""Route đổi tên và gỡ máy; server.main gộp vào cùng cổng với các API khác."""

from server.config.routing import APP_REMOVE_MACHINE, APP_RENAME_MACHINE
from .manage_flow import remove_machine, rename_machine


ROUTES = {
    APP_RENAME_MACHINE: rename_machine,
    APP_REMOVE_MACHINE: remove_machine,
}
