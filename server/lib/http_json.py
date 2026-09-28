"""Đọc body JSON và gửi trả lời JSON; mọi module dùng chung, mỗi module tự chọn giới hạn body."""

import json


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
    except (ValueError, UnicodeDecodeError, TimeoutError):
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
