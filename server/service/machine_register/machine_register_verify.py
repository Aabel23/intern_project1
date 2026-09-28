"""Kiểm tra gói đăng ký máy app gửi; chỉ đọc, không ghi database, không đọc/ghi HTTP.

Chưa có danh sách key nhà máy để đối chiếu: key nào đúng dạng cũng đăng ký được.
"""

# Server chung: dạng lỗi
from server.lib.http_json import invalid


def is_text(value, max_length):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= max_length


def check_machine(data):
    """Tên máy 1-150 ký tự, product key 1-1024 ký tự; trả lỗi hoặc None."""
    if not is_text(data.get("machine_name"), 150):
        return invalid("Tên máy không hợp lệ")
    if not is_text(data.get("product_key"), 1024):
        return invalid("Product key không hợp lệ")
    return None
