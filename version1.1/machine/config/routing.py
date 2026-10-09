"""Đường dẫn API và nhịp gọi server của machine."""

# Đường dẫn API mà machine sử dụng: /machine/<mục_tiêu>/<hành_động>, khớp server/config/routing.py.
MACHINE_COMMAND_POLL = "/machine/command/poll"
MACHINE_RESULT_SEND = "/machine/result/send"
MACHINE_HEARTBEAT_SEND = "/machine/heartbeat/send"
HEARTBEAT_INTERVAL_SECONDS = 5
