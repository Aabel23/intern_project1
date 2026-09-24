"""Điều khiển điện thoại Android qua adb: đọc cây giao diện, chạm theo chữ, gõ phím."""

import html
import re
import subprocess
import time
from dataclasses import dataclass

UI_DUMP = "/sdcard/flexmix_e2e_ui.xml"


@dataclass
class Node:
    text: str
    desc: str
    cls: str
    x: int
    y: int
    checked: bool
    enabled: bool

    @property
    def label(self):
        return self.text or self.desc


class Phone:
    def __init__(self, serial=None):
        self.base = ["adb"] + (["-s", serial] if serial else [])

    def adb(self, *args, timeout=60, check=True):
        result = subprocess.run(self.base + list(args), capture_output=True, timeout=timeout)
        if check and result.returncode != 0:
            raise RuntimeError(f"adb {' '.join(args)}: {result.stderr.decode('utf-8', 'replace')}")
        return result.stdout.decode("utf-8", "replace")

    def shell(self, *args, **kwargs):
        return self.adb("shell", *args, **kwargs)

    def nodes(self):
        # uiautomator đôi khi báo lỗi khi màn hình đang chuyển cảnh, thử lại vài lần.
        for _ in range(5):
            self.shell("uiautomator", "dump", UI_DUMP, check=False)
            xml = self.adb("exec-out", "cat", UI_DUMP, check=False)
            if "<hierarchy" in xml:
                break
            time.sleep(0.5)
        else:
            raise RuntimeError("Không đọc được giao diện điện thoại (uiautomator dump).")
        nodes = []
        for match in re.finditer(r"<node [^>]*>", xml):
            raw = match.group(0)
            # Giá trị chứa dấu " (ví dụ tên Bluetooth 43" TV) thì uiautomator bọc bằng dấu nháy đơn.
            attr = lambda name: html.unescape(
                next(g for g in re.search(f"""{name}=(?:"([^"]*)"|'([^']*)')""", raw).groups() if g is not None))
            x1, y1, x2, y2 = map(int, re.search(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", attr("bounds")).groups())
            nodes.append(Node(attr("text"), attr("content-desc"), attr("class").split(".")[-1],
                              (x1 + x2) // 2, (y1 + y2) // 2,
                              attr("checked") == "true", attr("enabled") == "true"))
        return nodes

    def find(self, pattern, cls=None, nodes=None):
        for node in nodes if nodes is not None else self.nodes():
            if (cls is None or node.cls == cls) and re.search(pattern, node.label):
                return node
        return None

    def labels(self):
        return [node.label for node in self.nodes() if node.label]

    def wait(self, pattern, timeout=30, cls=None):
        deadline = time.monotonic() + timeout
        while True:
            node = self.find(pattern, cls)
            if node is not None:
                return node
            if time.monotonic() > deadline:
                raise AssertionError(f"Không thấy /{pattern}/ sau {timeout}s. Đang hiện: {self.labels()}")
            time.sleep(0.7)

    def wait_gone(self, pattern, timeout=30):
        deadline = time.monotonic() + timeout
        while self.find(pattern) is not None:
            if time.monotonic() > deadline:
                raise AssertionError(f"/{pattern}/ vẫn còn sau {timeout}s.")
            time.sleep(0.7)

    def tap(self, target, timeout=30, cls=None):
        node = target if isinstance(target, Node) else self.wait(target, timeout, cls)
        self.shell("input", "tap", str(node.x), str(node.y))
        time.sleep(0.8)
        return node

    def keyboard_shown(self):
        return "mInputShown=true" in self.shell("dumpsys", "input_method")

    def hide_keyboard(self):
        # BACK chỉ khi bàn phím đang hiện, nếu không sẽ thoát màn hình.
        if self.keyboard_shown():
            self.back()

    def type_into(self, index, text):
        """Gõ vào ô nhập thứ index (tính từ trên xuống) của màn hình hiện tại."""
        fields = [node for node in self.nodes() if node.cls == "EditText"]
        self.tap(fields[index])
        self.shell("input", "text", text.replace(" ", "%s"))
        self.hide_keyboard()

    def back(self):
        self.shell("input", "keyevent", "4")
        time.sleep(0.8)

    def swipe_down(self):
        # Kéo xuống để tải lại (RefreshIndicator).
        self.shell("input", "swipe", "540", "700", "540", "1700", "400")
        time.sleep(1)

    def launch(self, package):
        self.shell("am", "force-stop", package)
        self.shell("monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1")
        time.sleep(2)

    def screenshot(self, path):
        with open(path, "wb") as file:
            file.write(subprocess.run(self.base + ["exec-out", "screencap", "-p"],
                                      capture_output=True, timeout=30).stdout)

    def bluetooth_address(self):
        return self.shell("settings", "get", "secure", "bluetooth_address").strip()

    def wifi_ip(self):
        match = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", self.shell("ip", "-f", "inet", "addr", "show", "wlan0"))
        return match.group(1) if match else None

    def cleanup(self):
        self.shell("rm", "-f", UI_DUMP, check=False)
