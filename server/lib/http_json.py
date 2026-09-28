"""Đọc body JSON và gửi trả lời JSON; mọi module dùng chung, mỗi module tự chọn giới hạn body."""

# Thư viện chuẩn
import json
import sqlite3

# Trong lib
from .rate_limit import too_many_requests


def read_body(request, max_body):
    """Body thô; ValueError nếu Content-Length sai hoặc ngoài 1..max_body, TimeoutError nếu client gửi chậm."""
    length = int(request.headers.get("Content-Length", 0))
    if not 1 <= length <= max_body:
        raise ValueError("Kích thước không hợp lệ")
    return request.rfile.read(length)


def read_json(request, max_body):
    """Body JSON object; None nếu sai kích thước, sai định dạng hoặc quá thời gian."""
    try:
        data = json.loads(read_body(request, max_body))
        # Phải ghi lại được: surrogate lẻ (\ud800) không mã hóa UTF-8 khi băm/ghi SQLite,
        # lồng quá sâu thì không gửi tiếp cho app được.
        json.dumps(data, ensure_ascii=False).encode("utf-8")
    except (ValueError, UnicodeDecodeError, TimeoutError, RecursionError):
        return None
    return data if isinstance(data, dict) else None


def discard_body(request, limit):
    """Đọc bỏ body trước khi trả lỗi sớm, tránh Windows cắt kết nối (RST) khi client còn đang gửi."""
    try:
        request.rfile.read(min(int(request.headers.get("Content-Length", 0)), limit))
    except (ValueError, TimeoutError):
        pass


def send_json(request, data, status=200):
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    try:
        request.send_response(status)
        request.send_header("Content-Type", "application/json; charset=utf-8")
        request.send_header("Content-Length", str(len(body)))
        if isinstance(data, dict) and "retry_after" in data:
            request.send_header("Retry-After", str(data["retry_after"]))
        request.end_headers()
        request.wfile.write(body)
    except (BrokenPipeError, ConnectionResetError):
        pass  # App đã ngắt kết nối.


def handle_routes(request, routes, max_body, error, limited=False):
    """handle() chung của module: tra đường dẫn, đọc JSON, gọi flow, gửi (kết quả, status).

    routes: {đường_dẫn: hàm_flow(data) -> (kết quả, status)}.
    error(message): thân lỗi theo dạng app của module đang đọc, vd {"loi": message}.
    limited: giới hạn request theo IP trước khi đọc body (API chưa cần token).
    Trả False nếu đường dẫn không thuộc routes.
    """
    route = routes.get(request.path)
    if route is None:
        return False
    if limited and too_many_requests(request.client_address[0]):
        discard_body(request, max_body)
        send_json(request, {**error("Quá nhiều yêu cầu"), "retry_after": 60}, 429)
        return True
    data = read_json(request, max_body)
    if data is None:
        send_json(request, error("JSON không hợp lệ"), 400)
        return True
    try:
        result, status = route(data)
    except sqlite3.Error:
        result, status = error("Database tạm thời không sẵn sàng"), 503
    send_json(request, result, status)
    return True


def invalid(message):
    """Thân lỗi của module dạng {"valid", "message"}."""
    return {"valid": False, "message": message}


def valid_status(body):
    """Status của thân dạng {"valid", ...}: 200 khi valid, 429 khi kèm retry_after, còn lại 400."""
    if body["valid"]:
        return 200
    return 429 if "retry_after" in body else 400


def with_valid_status(routes):
    """Module dạng {"valid"}: flow chỉ trả thân, status suy ra bằng valid_status()."""
    return {path: _add_valid_status(route) for path, route in routes.items()}


def _add_valid_status(route):
    def call(data):
        body = route(data)
        return body, valid_status(body)
    return call
