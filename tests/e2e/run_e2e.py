"""Test tự động toàn bộ tính năng trên điện thoại thật + laptop, không cần bấm tay.

Chạy từ thư mục gốc androidv0.1, điện thoại cắm USB (bật gỡ lỗi USB), Bluetooth bật:
    python tests/e2e/run_e2e.py              # build + cài app rồi test
    python tests/e2e/run_e2e.py --skip-build # dùng app đang cài

Laptop đóng vai máy FlexMix (Bluetooth + relay) và app thứ hai; điện thoại chạy app thật.
Kịch bản: đăng nhập chủ → pair máy qua Bluetooth → máy online, đọc/bật tắt món, xem kho →
chia sẻ qua Bluetooth → xem + thu hồi nhân viên → chia sẻ qua QR → đăng xuất →
đăng nhập nhân viên → nhận chia sẻ qua Bluetooth → phiên hết hạn thì về màn hình đăng nhập.

Tài khoản, máy và phiên tạo ra đều mang tiền tố e2e_/FlexMix-E2E- và được xóa khi kết thúc.
Log, ảnh chụp lúc lỗi nằm trong tests/e2e/logs/<thời điểm>/.
"""

import argparse
import contextlib
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import time
import traceback
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tests.e2e.phone import Phone  # noqa: E402
from server.config.config import SERVER_PORT  # noqa: E402
from server.database.connection import get_connection  # noqa: E402
from server.database.user.user_add import hash_password  # noqa: E402
from server.lib.security.data_hash import sha256_hex  # noqa: E402

PACKAGE = "com.example.simple_app"
PYTHON = sys.executable
LOCAL_SERVER = f"http://127.0.0.1:{SERVER_PORT}"


class Run:
    """Trạng thái một lần chạy: thư mục log, tiến trình con, dữ liệu tạm cần dọn."""

    def __init__(self):
        self.logs = ROOT / "tests" / "e2e" / "logs" / time.strftime("%Y%m%d-%H%M%S")
        self.logs.mkdir(parents=True)
        self.processes = []
        self.user_ids = []
        self.env_file = None
        self.key_hash = None

    def spawn(self, name, *args, env=None):
        log = open(self.logs / f"{name}.log", "w", encoding="utf-8")
        process = subprocess.Popen(
            [PYTHON, "-u", *args], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL, env={**os.environ, "PYTHONIOENCODING": "utf-8", **(env or {})},
        )
        self.processes.append((name, process, log))
        return process

    def log_text(self, name):
        return (self.logs / f"{name}.log").read_text(encoding="utf-8", errors="replace")

    def stop_all(self):
        for _, process, log in self.processes:
            if process.poll() is None:
                process.terminate()
                with contextlib.suppress(subprocess.TimeoutExpired):
                    process.wait(10)
            log.close()
        self.processes.clear()


class StopRun(Exception):
    """Đã chạy xong luồng --until, dừng kịch bản (không phải lỗi)."""


# Số của luồng cuối cần chạy (--until E4 -> 4); None là chạy hết.
UNTIL = None


def step(name):
    # Tên bước bắt đầu bằng ID luồng (E0..E12) để check_all ghi vào log/FLOWS.md.
    number = int(name.split()[0][1:])
    if UNTIL is not None and number > UNTIL:
        raise StopRun
    print(f"\n▶ {name}", flush=True)
    return time.monotonic()


def ok(start, detail=""):
    print(f"  ✓ {time.monotonic() - start:.1f}s {detail}", flush=True)


def wait_process(run, name, process, timeout):
    try:
        code = process.wait(timeout)
    except subprocess.TimeoutExpired:
        process.terminate()
        raise AssertionError(f"{name} chưa xong sau {timeout}s:\n{run.log_text(name)[-2000:]}")
    if code != 0:
        raise AssertionError(f"{name} thoát mã {code}:\n{run.log_text(name)[-2000:]}")


def wait_for(check, timeout, message):
    deadline = time.monotonic() + timeout
    while not check():
        if time.monotonic() > deadline:
            raise AssertionError(message)
        time.sleep(0.5)


# ---------- dữ liệu tạm trong database thật ----------

def remove_stale():
    """Xóa dữ liệu của lần chạy trước bị dừng giữa chừng (chỉ các bản ghi e2e_)."""
    with get_connection() as conn:
        conn.execute("DELETE FROM machines WHERE name LIKE 'FlexMix-E2E-%'")
        conn.execute("DELETE FROM users WHERE username LIKE 'e2e\\_%' ESCAPE '\\'"
                     " AND email LIKE '%@sandbox.local'")


def create_user(run, role):
    suffix = secrets.token_hex(3)
    username, password = f"e2e_{role}_{suffix}", secrets.token_hex(8)
    full_name = {"owner": "E2E Chu may", "staff": "E2E Nhan vien"}[role]
    with get_connection() as conn:
        user_id = conn.execute(
            "INSERT INTO users (full_name, username, password, email) VALUES (?, ?, ?, ?)",
            (full_name, username, hash_password(password), f"{username}@sandbox.local"),
        ).lastrowid
    run.user_ids.append(user_id)
    return {"id": user_id, "username": username, "password": password, "full_name": full_name}


def db_one(sql, *args):
    with get_connection() as conn:
        return conn.execute(sql, args).fetchone()


def cleanup_data(run):
    with get_connection() as conn:
        if run.key_hash:
            conn.execute("DELETE FROM machines WHERE product_key_hash=?", (run.key_hash,))
        for user_id in run.user_ids:
            conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    if run.env_file and run.env_file.exists():
        run.env_file.unlink()


# ---------- server, build ----------

def machine_online(machine_id):
    with urlopen(f"{LOCAL_SERVER}/app/machine/status/get?machine_id={machine_id}", timeout=5) as response:
        return json.loads(response.read())["online"]


def server_running():
    try:
        with urlopen(f"{LOCAL_SERVER}/app/machine/status/get?machine_id=e2e", timeout=2):
            return True
    except OSError:
        return False


def laptop_ip_for(phone_ip):
    # Hỏi hệ điều hành dùng IP nào để tới điện thoại (UDP connect không gửi gói tin).
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        probe.connect((phone_ip, 9))
        return probe.getsockname()[0]


def build_and_install(run, phone, server_url):
    flutter = shutil.which("flutter")
    if flutter is None:
        raise AssertionError("Không tìm thấy lệnh flutter trong PATH.")
    app = ROOT / "app" / "flutter_app"
    with open(run.logs / "build.log", "w", encoding="utf-8") as log:
        subprocess.run([flutter, "build", "apk", "--release", f"--dart-define=SERVER_URL={server_url}"],
                       cwd=app, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=900)
    apk = app / "build" / "app" / "outputs" / "flutter-apk" / "app-release.apk"
    try:
        phone.adb("install", "-r", str(apk), timeout=300)
    except RuntimeError as error:
        # Bản đang cài ký bằng key khác (build ở máy khác): gỡ rồi cài lại.
        if "INSTALL_FAILED_UPDATE_INCOMPATIBLE" not in str(error):
            raise
        phone.adb("uninstall", PACKAGE, timeout=60)
        phone.adb("install", str(apk), timeout=300)


# ---------- thao tác trên app ----------

def login(phone, user):
    phone.launch(PACKAGE)
    phone.wait("^Đăng nhập$", 30, cls="Button")
    phone.type_into(0, user["username"])
    phone.type_into(1, user["password"])
    phone.tap("^Đăng nhập$", cls="Button")
    phone.wait("^Máy\nTab", 30)


def open_machines_tab(phone):
    phone.tap("^Máy\nTab")
    phone.wait("^Nhận chia sẻ qua Bluetooth$")


def machine_row(phone, name, pattern="", timeout=30):
    return phone.wait(f"^{name}\n{pattern}", timeout)


def open_machine_menu(phone, name):
    row = machine_row(phone, name)
    menus = [node for node in phone.nodes() if node.desc == "Show menu"]
    phone.tap(min(menus, key=lambda node: abs(node.y - row.y)))


def pick_bluetooth_device(phone, hostname, timeout=40):
    # Quét 15 giây; laptop hiện theo tên máy tính (không bắt đầu bằng FlexMix-).
    return phone.tap(f"^{hostname}\n", timeout)


# ---------- kịch bản ----------

def scenario(run, phone, owner, staff, machine_name, hostname):
    t = step("E1 Đăng nhập tài khoản chủ trên điện thoại")
    login(phone, owner)
    ok(t, owner["username"])

    t = step("E2 Pair máy qua Bluetooth (laptop giả máy, key mới)")
    pairing = run.spawn("pair_machine", "tests/bluetooth_pair/app2machine-pair.py",
                        "--env", str(run.env_file), "--once")
    wait_for(lambda: "chờ APP kết nối" in run.log_text("pair_machine"), 20, "Máy giả không mở Bluetooth")
    open_machines_tab(phone)
    phone.tap("^Bluetooth$", cls="Button")
    phone.wait("^Không thấy máy|^Chọn máy", 40)
    phone.tap("Hiện mọi thiết bị Bluetooth")
    pick_bluetooth_device(phone, hostname)
    phone.wait("ID: fm_", 60)
    wait_process(run, "pair_machine", pairing, 30)
    machine = db_one("SELECT machine_id FROM machines WHERE product_key_hash=?", run.key_hash)
    assert machine, "Server chưa lưu máy vừa pair"
    machine_id = machine["machine_id"]
    role = db_one("SELECT role FROM machine_managers WHERE machine_id=? AND user_id=?",
                  machine_id, owner["id"])
    assert role and role["role"] == "owner", "Người pair chưa thành chủ máy"
    phone.back()
    machine_row(phone, machine_name, ".*Chủ máy")
    ok(t, machine_id)

    t = step("E3 Máy online qua relay, đọc menu, bật/tắt món, xem kho")
    run.spawn("machine_sim", "tests/relay/machine_sim.py", "--env", str(run.env_file))
    wait_for(lambda: machine_online(machine_id), 30,
             "Máy giả không online (chưa poll được), xem machine_sim.log")
    # Chọn máy khi đã online thì app tải luôn menu và kho.
    phone.tap(machine_row(phone, machine_name))
    machine_row(phone, machine_name, "Online", 30)
    phone.tap("^Sản phẩm\nTab")
    tile = phone.wait("Matcha latte", 40)
    switches = [node for node in phone.nodes() if node.cls == "Switch"]
    switch = min(switches, key=lambda node: abs(node.y - tile.y))
    assert not switch.checked, "Matcha latte phải đang tắt"
    phone.tap(switch)
    wait_for(lambda: "cap_nhat_menu" in run.log_text("machine_sim"), 30, "Máy giả không nhận lệnh bật món")

    def matcha_on():
        nodes = phone.nodes()
        tile = phone.find("Matcha latte", nodes=nodes)
        switches = [node for node in nodes if node.cls == "Switch"]
        return tile and min(switches, key=lambda node: abs(node.y - tile.y)).checked
    wait_for(matcha_on, 30, "App không cập nhật trạng thái món sau khi bật")
    phone.tap("^Kho\nTab")
    phone.wait("Sữa tươi", 30)
    phone.wait("0 / 1500 g", 10)
    phone.wait("Bơm 1", 10)
    ok(t, "menu + bật món + kho")

    t = step("E4 Nạp kho qua /app/machine/ingredient/refill: nạp đầy một bình, rồi nạp tất cả")
    row = phone.wait("0 / 1500 g", 10)
    buttons = [node for node in phone.nodes() if node.label == "Nạp đầy"]
    phone.tap(min(buttons, key=lambda node: abs(node.y - row.y)))
    phone.tap("^Nạp$", cls="Button")
    phone.wait("1500 / 1500 g", 30)
    assert "nap_kho" in run.log_text("machine_sim"), "Máy giả không nhận lệnh nạp kho"
    phone.tap("Nạp tất cả")
    phone.tap("^Nạp$", cls="Button")
    phone.wait("2000 / 2000 g", 30)
    phone.wait("1000 / 1000 g", 10)
    ok(t, "một bình + tất cả")

    t = step("E5 Chủ đổi tên máy trên app")
    open_machines_tab(phone)
    open_machine_menu(phone, machine_name)
    phone.tap("^Đổi tên$")
    phone.wait("^Đổi tên máy$", 10)
    machine_name = machine_name + "-R"
    phone.replace_text(0, machine_name)
    phone.tap("^Lưu$", cls="Button")
    machine_row(phone, machine_name, ".*Chủ máy", 30)
    assert db_one("SELECT 1 FROM machines WHERE machine_id=? AND name=?", machine_id, machine_name), \
        "Server chưa lưu tên máy mới"
    ok(t, machine_name)

    t = step("E6 Chia sẻ qua Bluetooth: điện thoại (chủ) → laptop (nhân viên)")
    receiver = run.spawn("share_receive", "tests/bluetooth_pair/app2app_pair.py",
                         "--username", staff["username"], "--timeout", "150",
                         env={"SANDBOX_PASSWORD": staff["password"]})
    wait_for(lambda: "APP2 chờ CHỦ MÁY" in run.log_text("share_receive"), 30, "Laptop không mở Bluetooth nhận")
    open_machines_tab(phone)
    open_machine_menu(phone, machine_name)
    phone.tap("^Chia sẻ cho nhân viên$")
    phone.wait("^Hết hạn sau", 30)
    phone.tap("^Gửi qua Bluetooth$", cls="Button")
    pick_bluetooth_device(phone, hostname)
    phone.wait("^Đã gửi mã cho", 60)
    wait_process(run, "share_receive", receiver, 60)
    assert db_one("SELECT 1 FROM machine_managers WHERE machine_id=? AND user_id=? AND role='manager'",
                  machine_id, staff["id"]), "Nhân viên chưa được giao máy"
    ok(t)

    t = step("E7 Chủ xem danh sách nhân viên và thu hồi quyền")
    phone.back()
    phone.wait(staff['full_name'], 30)
    phone.tap("^Thu hồi quyền$")
    phone.tap("^Thu hồi$", cls="Button")
    phone.wait("^Chưa giao máy cho nhân viên nào", 30)
    assert not db_one("SELECT 1 FROM machine_managers WHERE machine_id=? AND user_id=?",
                      machine_id, staff["id"]), "Server chưa xóa quyền nhân viên"
    ok(t)

    t = step("E8 Chia sẻ qua QR: laptop chụp màn hình điện thoại đọc mã")
    phone.tap("^Tạo mã mới$", cls="Button")
    phone.wait("^Hết hạn sau", 30)
    qr = run.spawn("share_qr", "tests/bluetooth_pair/app2app_pair.py", "--adb",
                   "--username", staff["username"], env={"SANDBOX_PASSWORD": staff["password"]})
    wait_process(run, "share_qr", qr, 60)
    assert db_one("SELECT 1 FROM machine_managers WHERE machine_id=? AND user_id=? AND role='manager'",
                  machine_id, staff["id"]), "Nhận chia sẻ qua QR không ghi quyền"
    with get_connection() as conn:
        conn.execute("DELETE FROM machine_managers WHERE machine_id=? AND user_id=?", (machine_id, staff["id"]))
    ok(t)

    t = step("E9 Đăng xuất xóa phiên trên server")
    phone.back()
    # Chọn theo tooltip riêng, tránh nhầm với menu của từng máy.
    phone.tap("^Tài khoản$")
    phone.tap("^Đăng xuất$")
    phone.wait("^Đăng nhập$", 30, cls="Button")
    wait_for(lambda: not db_one("SELECT 1 FROM app_sessions WHERE user_id=?", owner["id"]), 10,
             "Server vẫn giữ phiên của chủ sau khi đăng xuất")
    ok(t)

    t = step("E10 Nhân viên nhận chia sẻ qua Bluetooth: laptop (chủ) → điện thoại")
    login(phone, staff)
    open_machines_tab(phone)
    phone.tap("^Nhận chia sẻ qua Bluetooth$")
    allow = phone.wait("^(Allow|Cho phép)$", 20)
    phone.tap(allow)
    phone.wait("^Đang chờ chủ máy", 20)
    sender = run.spawn("share_send", "tests/bluetooth_pair/app2app_pair.py", "--send",
                       "--phone", phone.bluetooth_address(), "--machine-id", machine_id,
                       "--username", owner["username"], env={"SANDBOX_PASSWORD": owner["password"]})
    wait_process(run, "share_send", sender, 90)
    phone.wait("^Đã nhận quản lý máy", 30)
    phone.back()
    machine_row(phone, machine_name, ".*Được giao", 30)
    ok(t)

    t = step("E11 Phiên hết hạn giữa chừng thì app quay về màn hình đăng nhập")
    phone.tap("^Sản phẩm\nTab")
    phone.wait("Cà phê sữa", 40)
    with get_connection() as conn:
        conn.execute("DELETE FROM app_sessions WHERE user_id=?", (staff["id"],))
    phone.swipe_down()
    phone.wait("^Đăng nhập$", 30, cls="Button")
    ok(t)

    t = step("E12 Chủ thu hồi quyền thì máy biến mất khỏi app nhân viên sau khi tải lại")
    login(phone, staff)
    open_machines_tab(phone)
    machine_row(phone, machine_name, ".*Được giao", 30)
    with get_connection() as conn:
        conn.execute("DELETE FROM machine_managers WHERE machine_id=? AND user_id=?", (machine_id, staff["id"]))
    phone.swipe_down()
    phone.wait("^Quán chưa có máy nào", 30)
    assert phone.find(f"^{machine_name}\n") is None, "Máy bị thu hồi vẫn còn trong danh sách"
    ok(t)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Test tự động app + máy + server trên điện thoại thật.")
    parser.add_argument("--skip-build", action="store_true", help="không build/cài lại app")
    parser.add_argument("--serial", help="số serial điện thoại khi cắm nhiều máy (adb devices)")
    parser.add_argument("--wifi", action="store_true",
                        help="app gọi server qua Wi-Fi (IP laptop) thay vì qua cáp USB (adb reverse);"
                             " APK build ở chế độ nào thì --skip-build phải dùng cùng chế độ")
    parser.add_argument("--until", help="dừng sau luồng này, vd. E4 (các luồng e2e nối tiếp nhau)")
    args = parser.parse_args()
    global UNTIL
    UNTIL = int(args.until.upper().lstrip("E")) if args.until else None

    run = Run()
    phone = Phone(args.serial)
    started = time.monotonic()
    failed = False
    try:
        t = step("E0 Kiểm tra điện thoại, mạng và server")
        # Keep the phone awake even when this script is invoked without the runner.
        phone.shell("svc", "power", "stayon", "usb")
        phone.shell("input", "keyevent", "224")
        phone.shell("wm", "dismiss-keyguard", check=False)
        if args.wifi:
            phone_ip = phone.wifi_ip()
            assert phone_ip, "Điện thoại chưa bật Wi-Fi (cần cùng mạng với laptop)."
            server_url = f"http://{laptop_ip_for(phone_ip)}:{SERVER_PORT}"
        else:
            # Qua cáp USB: cổng 8000 của điện thoại chuyển về laptop, không phụ thuộc
            # Wi-Fi (router cách ly thiết bị, khác access point...).
            phone_ip = "USB"
            phone.adb("reverse", f"tcp:{SERVER_PORT}", f"tcp:{SERVER_PORT}")
            server_url = f"http://127.0.0.1:{SERVER_PORT}"
        if server_running():
            print("  (dùng server đang chạy sẵn ở cổng", SERVER_PORT, ")")
        else:
            run.spawn("server", "-m", "server.main")
            wait_for(server_running, 20, "Server không khởi động được")
        remove_stale()
        ok(t, f"điện thoại {phone_ip}, server {server_url}")

        if not args.skip_build:
            t = step("E0 Build app với SERVER_URL và cài lên điện thoại")
            build_and_install(run, phone, server_url)
            ok(t)

        # Cài mới thì mất quyền runtime; cấp sẵn để hộp thoại xin quyền không chặn kịch bản.
        for permission in ("BLUETOOTH_SCAN", "BLUETOOTH_CONNECT", "BLUETOOTH_ADVERTISE",
                           "ACCESS_FINE_LOCATION", "CAMERA"):
            phone.shell("pm", "grant", PACKAGE, f"android.permission.{permission}", check=False)

        owner, staff = create_user(run, "owner"), create_user(run, "staff")
        machine_name = f"FlexMix-E2E-{secrets.token_hex(2)}"
        env = (f"MACHINE_NAME={machine_name}\n"
               f"PRODUCT_KEY=fm_{secrets.token_hex(32)}\nSERVER_URL={LOCAL_SERVER}\n")
        run.env_file = run.logs / "machine.env"
        run.env_file.write_text(env, encoding="utf-8")
        key = next(line.split("=", 1)[1] for line in env.splitlines() if line.startswith("PRODUCT_KEY="))
        run.key_hash = sha256_hex(key)
        scenario(run, phone, owner, staff, machine_name, socket.gethostname())
    except StopRun:
        print(f"\n(dừng sau E{UNTIL} theo --until)", flush=True)
    except Exception:
        failed = True
        print("\n✗ LỖI:\n" + traceback.format_exc(), flush=True)
        with contextlib.suppress(Exception):
            phone.screenshot(run.logs / "loi.png")
            (run.logs / "man_hinh_luc_loi.json").write_text(
                json.dumps(phone.labels(), ensure_ascii=False, indent=2), encoding="utf-8")
    finally:
        run.stop_all()
        cleanup_data(run)
        with contextlib.suppress(Exception):
            phone.shell("am", "force-stop", PACKAGE)
            phone.cleanup()
    print(f"\n{'✗ THẤT BẠI' if failed else '✓ TẤT CẢ ĐẠT'} sau {time.monotonic() - started:.0f}s."
          f" Log: {run.logs}", flush=True)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
