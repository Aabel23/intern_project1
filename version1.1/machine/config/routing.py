"""Đường dẫn API mà machine gọi lên server."""

# Đường dẫn API mà machine sử dụng: /machine/<mục_tiêu>/<hành_động>, khớp server/configuration/routing.py.
MACHINE_ACTIVATION_SEND = "/machine/activation/send"
MACHINE_HELLO_SEND = "/machine/hello/send"
MACHINE_COMMAND_POLL = "/machine/command/poll"
MACHINE_RESULT_SEND = "/machine/result/send"
MACHINE_PERMISSION_GET = "/machine/permission/get"
MACHINE_EVENT_SEND = "/machine/event/send"
MACHINE_UPDATE_GET = "/machine/update/get"
MACHINE_UPDATE_REPORT = "/machine/update/report"
