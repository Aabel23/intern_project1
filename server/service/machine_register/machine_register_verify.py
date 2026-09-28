"""Kiểm tra gói app gửi; chưa có danh sách key nhà máy để đối chiếu."""


def verify_machine(data):
    if not isinstance(data, dict):
        return "Dữ liệu phải là JSON object"
    name = data.get("machine_name")
    key = data.get("product_key")
    if not isinstance(name, str) or not name.strip() or len(name) > 150:
        return "Tên máy không hợp lệ"
    if not isinstance(key, str) or not key.strip() or len(key) > 1024:
        return "Product key không hợp lệ"
    return None

