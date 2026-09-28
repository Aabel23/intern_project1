"""handle() dùng chung cho các module có flow trả {"valid", "message", ...}.

Đọc body tối đa 4096 byte, gọi flow, rồi đổi valid thành status:
200 khi valid, 400 khi không, 429 khi không kèm retry_after. limited=True thì
giới hạn request theo IP trước khi đọc body (xem rate_limit.py).
"""

import json
import sqlite3

from .http_json import discard_body, read_body, send_json
from .rate_limit import too_many_requests

MAX_BODY = 4096


def handle_valid_routes(request, routes, limited=False):
    """True nếu request.path thuộc routes và đã trả lời."""
    route = routes.get(request.path)
    if route is None:
        return False
    if limited and too_many_requests(request.client_address[0]):
        discard_body(request, MAX_BODY)
        send_json(request, {"valid": False, "message": "Quá nhiều yêu cầu", "retry_after": 60}, 429)
        return True
    try:
        result = route(json.loads(read_body(request, MAX_BODY)))
    except (ValueError, UnicodeDecodeError):
        send_json(request, {"valid": False, "message": "JSON không hợp lệ"}, 400)
        return True
    except TimeoutError:
        send_json(request, {"valid": False, "message": "Hết thời gian nhận dữ liệu"}, 408)
        return True
    except sqlite3.Error:
        send_json(request, {"valid": False, "message": "Database tạm thời không sẵn sàng"}, 503)
        return True
    status = 200 if result["valid"] else 400
    # Gửi OTP thành công cũng kèm retry_after (thời gian chờ gửi lại), không phải 429.
    if not result["valid"] and "retry_after" in result:
        status = 429
    send_json(request, result, status)
    return True
