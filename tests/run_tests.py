"""Chạy các luồng kiểm tra đã đăng ký và cập nhật bảng theo dõi log/FLOWS.md.

Dùng qua test.ps1 ở thư mục androidv0.1 (hoặc gọi thẳng):
    .\\tests\\test.ps1 -List                 # xem danh sách luồng + trạng thái lần chạy cuối
    .\\tests\\test.ps1                       # chạy mọi luồng
    .\\tests\\test.ps1 -Flow S8,F2           # chỉ chạy vài luồng
    .\\tests\\test.ps1 -Flow py              # theo nhóm: py, app, e2e, all
    .\\tests\\test.ps1 -Flow E4 -Note "..."  # e2e nối tiếp nhau: E4 chạy E0..E4

Thêm kịch bản mới: thêm một dòng vào FLOWS bên dưới (và bước "Ex ..." trong
tests/e2e/run_e2e.py nếu là e2e), ghi tiêu chí vào log/TIEU_CHI_TEST.md.
APK tự build lại khi mã app (lib/, android/, pubspec.yaml) khác lần cài trước.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "log"
STATE = LOG / "flows_state.json"
APP = ROOT / "app" / "flutter_app"
PYTHON = sys.executable

# (ID, nhóm, mô tả, cách chạy). py: module unittest; app: lệnh flutter; e2e: bước trong run_e2e.py.
FLOWS = [
    ("S10", "py", "Ranh giới phụ thuộc và trách nhiệm của app", "tests.python.test_app_boundaries"),
    ("S1", "py", "HTTP chung cổng, rate limit, relay, long-poll", "tests.python.test_server"),
    ("S2", "py", "Đăng ký + OTP", "tests.python.test_user_register"),
    ("S3", "py", "Đăng nhập / đăng xuất", "tests.python.test_user_login"),
    ("S4", "py", "Đăng ký máy (chủ đầu tiên)", "tests.python.test_machine_register"),
    ("S5", "py", "Chia sẻ máy, thu hồi nhân viên", "tests.python.test_machine_share"),
    ("S6", "py", "Tab Máy: danh sách, đổi tên, gỡ máy", "tests.python.test_machine_list"),
    ("S7", "py", "Gói pairing Bluetooth của máy", "tests.python.test_machine_bluetooth"),
    ("S8", "py", "Máy thật ↔ relay: lệnh, đồng bộ, nạp kho, chặn lệnh lạ", "tests.python.test_machine_relay"),
    ("S9", "py", "Khởi tạo module: route trùng, khởi động lại giữ dữ liệu", "tests.python.test_server_modules"),
    ("S11", "py", "Ảnh món: kiểm gói, lệnh nhan_anh qua relay", "tests.python.test_machine_menu_image"),
    ("S12", "py", "Stress menu: đổi menu liên tục, CRC luồng thật == oracle, khôi phục", "tests.python.test_menu_crc_stress"),
    ("X1", "py", "Kịch bản tấn công server (lỗ hổng đã biết = expectedFailure, xem SECURITY_NOTES)",
     "tests.python.test_server_security"),
    ("A1", "app", "flutter analyze sạch", "analyze"),
    ("A2", "app", "Static check test Flutter ngoài package app", "analyze-tests"),
    ("F1", "app", "Đăng nhập / đăng ký / OTP (widget)", "../../tests/flutter/auth_page_test.dart"),
    ("F2", "app", "Dashboard: menu, kho, nạp, phiên hết hạn (widget)", "../../tests/flutter/widget_test.dart"),
    ("F3", "app", "Danh sách máy đồng bộ server, máy offline (widget)", "../../tests/flutter/dashboard_controller_test.dart"),
    ("F4", "app", "Chia sẻ QR + xem/thu hồi nhân viên (widget)", "../../tests/flutter/device_share_test.dart"),
    ("F5", "app", "Chia sẻ qua Bluetooth (widget)", "../../tests/flutter/share_bluetooth_test.dart"),
    ("F6", "app", "Đổi tên / gỡ máy (widget)", "../../tests/flutter/machine_manage_test.dart"),
    ("F8", "app", "Gói Menu/Kho sai version không thay dữ liệu hợp lệ", "../../tests/flutter/machine_sync_test.dart"),
    ("F7", "app", "Đăng ký máy QR/Bluetooth (widget)",
     "../../tests/flutter/machine_register_test.dart ../../tests/flutter/machine_qr_test.dart ../../tests/flutter/bluetooth_pairing_test.dart"),
    ("E0", "e2e", "Chuẩn bị: USB reverse, server, build/cài, cấp quyền", None),
    ("E1", "e2e", "Đăng nhập chủ", None),
    ("E2", "e2e", "Pair máy qua Bluetooth", None),
    ("E3", "e2e", "Máy online, menu, bật món, xem kho", None),
    ("E4", "e2e", "Nạp một bình + nạp tất cả", None),
    ("E5", "e2e", "Đổi tên máy", None),
    ("E6", "e2e", "Chia sẻ Bluetooth chủ → nhân viên", None),
    ("E7", "e2e", "Xem + thu hồi nhân viên", None),
    ("E8", "e2e", "Chia sẻ qua QR", None),
    ("E9", "e2e", "Đăng xuất xóa phiên server", None),
    ("E10", "e2e", "Nhân viên nhận chia sẻ Bluetooth", None),
    ("E11", "e2e", "Phiên hết hạn → về đăng nhập", None),
    ("E12", "e2e", "Bị thu hồi → máy biến mất khi tải lại", None),
]
BY_ID = {flow[0]: flow for flow in FLOWS}


def run(cmd, cwd=ROOT, timeout=900):
    started = time.monotonic()
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, timeout=timeout,
                                env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        out = (result.stdout + result.stderr).decode("utf-8", "replace")
        code = result.returncode
    except subprocess.TimeoutExpired as error:
        out = ((error.stdout or b"") + (error.stderr or b"")).decode("utf-8", "replace")
        out += f"\nHẾT THỜI GIAN sau {timeout}s"
        code = -1
    return code, out.replace("\r\n", "\n"), time.monotonic() - started


def prepare_flutter_test_packages():
    """Let IDE/analyzer resolve relocated tests using the app's existing dependencies."""
    source = APP / ".dart_tool" / "package_config.json"
    if not source.exists():
        return
    config = json.loads(source.read_text(encoding="utf-8"))
    for package in config["packages"]:
        package["rootUri"] = urljoin(source.as_uri(), package["rootUri"])
    target = ROOT / "tests" / "flutter" / ".dart_tool" / "package_config.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(config, indent=2), encoding="utf-8")


def wake_phone():
    adb = shutil.which("adb")
    if adb is None or "\tdevice" not in subprocess.run([adb, "devices"], capture_output=True, text=True).stdout:
        return False
    # Giữ màn hình sáng khi cắm USB và đánh thức nếu đang tắt.
    for args in (["svc", "power", "stayon", "usb"], ["input", "keyevent", "224"], ["wm", "dismiss-keyguard"]):
        subprocess.run([adb, "shell", *args], capture_output=True)
    return True


def app_hash():
    digest = hashlib.sha256()
    files = [APP / "pubspec.yaml", *sorted((APP / "lib").rglob("*")), *sorted((APP / "android" / "app" / "src").rglob("*"))]
    for path in files:
        if path.is_file():
            digest.update(str(path.relative_to(APP)).encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


def load_state():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"flows": {}, "installed_app": None}


def select(spec):
    ids = []
    for part in (spec or "all").split(","):
        part = part.strip()
        if part.lower() == "all":
            ids += [f[0] for f in FLOWS]
        elif part.lower() in ("py", "app", "e2e"):
            ids += [f[0] for f in FLOWS if f[1] == part.lower()]
        elif part.upper() in BY_ID:
            ids.append(part.upper())
        else:
            sys.exit(f"Không có luồng '{part}'. Xem: .\\tests\\test.ps1 -List")
    return list(dict.fromkeys(ids))


def write_table(state):
    lines = ["# Theo dõi luồng kiểm tra", "",
             "Tự sinh bởi `tests/run_tests.py` (chạy qua `test.ps1`). Tiêu chí: `TIEU_CHI_TEST.md`.", "",
             "| ID | Nhóm | Luồng | Trạng thái | Lần chạy cuối | Commit | Thời gian |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    for flow_id, group, description, _ in FLOWS:
        s = state["flows"].get(flow_id, {})
        lines.append(f"| {flow_id} | {group} | {description} | {s.get('status', 'CHƯA CHẠY')} | "
                     f"{s.get('at', '-')} | `{s.get('commit', '-')}` | {s.get('seconds', '-')} |")
    (LOG / "FLOWS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--flows", default="all", help="ID hoặc nhóm, phân cách bằng dấu phẩy")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--build", action="store_true", help="luôn build lại APK trước e2e")
    parser.add_argument("--note", default="")
    args = parser.parse_args()
    LOG.mkdir(exist_ok=True)
    state = load_state()
    if args.list:
        write_table(state)
        for flow_id, group, description, _ in FLOWS:
            s = state["flows"].get(flow_id, {})
            print(f"{flow_id:4} {group:4} {s.get('status', 'CHƯA CHẠY'):10} {s.get('at', '-'):16} {description}")
        return

    ids = select(args.flows)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                                capture_output=True, text=True).stdout.strip())
    commit_label = commit + ("*" if dirty else "")
    results, details = {}, []

    def record(flow_id, status, seconds=None, out=None):
        results[flow_id] = status
        state["flows"][flow_id] = {"status": status, "at": time.strftime("%Y-%m-%d %H:%M"),
                                   "commit": commit_label,
                                   "seconds": f"{seconds:.0f}s" if seconds is not None else "-"}
        mark = {"ĐẠT": "✓", "LỖI": "✗"}.get(status, "-")
        print(f"{mark} {flow_id:4} {status:10} {BY_ID[flow_id][2]}", flush=True)
        if status == "LỖI" and out:
            details.append(f"### ✗ {flow_id} {BY_ID[flow_id][2]}\n\n```\n"
                           + "\n".join(out.splitlines()[-60:]) + "\n```\n")

    flutter = shutil.which("flutter")
    prepare_flutter_test_packages()
    for flow_id in ids:
        _, group, _, target = BY_ID[flow_id]
        if group == "py":
            code, out, s = run([PYTHON, "-m", "unittest", target], timeout=300)
            record(flow_id, "ĐẠT" if code == 0 else "LỖI", s, out)
        elif group == "app":
            if flutter is None:
                record(flow_id, "LỖI", 0, "Không tìm thấy flutter trong PATH")
                continue
            if target in ("analyze", "analyze-tests"):
                cmd = [flutter, "analyze", "--no-pub"]
                if target == "analyze-tests":
                    cmd.append("../../tests/flutter")
            else:
                cmd = [flutter, "test", "--no-pub", *target.split()]
            code, out, s = run(cmd, cwd=APP)
            record(flow_id, "ĐẠT" if code == 0 else "LỖI", s, out)

    e2e_ids = [i for i in ids if BY_ID[i][1] == "e2e"]
    if e2e_ids:
        last = max(int(i[1:]) for i in e2e_ids)
        if not wake_phone():
            for i in e2e_ids:
                record(i, "BỎ QUA")
            print("  (không có điện thoại adb, bỏ qua e2e)")
        else:
            current = app_hash()
            build = args.build or state.get("installed_app") != current
            cmd = [PYTHON, "tests/e2e/run_e2e.py", "--until", f"E{last}"] + ([] if build else ["--skip-build"])
            code, out, s = run(cmd, timeout=1800)
            (LOG / f"{stamp}-e2e.txt").write_text(out, encoding="utf-8")
            if build and "✓" in out.split("E0 Build", 1)[-1][:300]:
                state["installed_app"] = current
            # Mỗi bước in "▶ Ex ..." rồi "  ✓ ..." khi đạt; bước đang chạy lúc lỗi là LỖI.
            steps = re.findall(r"▶ (E\d+) [^\n]*\n(  ✓ ([\d.]+)s)?", out)
            seen = {}
            for step_id, passed, seconds in steps:
                if seen.get(step_id) == "LỖI":
                    continue
                seen[step_id] = "ĐẠT" if passed else "LỖI"
                if passed:
                    seen[step_id + "_s"] = float(seconds)
            failed_at = next((k for k, v in seen.items() if v == "LỖI"), None)
            for number in range(last + 1):
                step_id = f"E{number}"
                if step_id in seen:
                    record(step_id, seen[step_id], seen.get(step_id + "_s"),
                           out if seen[step_id] == "LỖI" else None)
                elif code != 0:
                    record(step_id, "BỎ QUA" if failed_at else "LỖI", None, out if not failed_at else None)

    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    write_table(state)
    failed = [i for i, v in results.items() if v == "LỖI"]
    status = "ĐẠT" if not failed else f"LỖI: {', '.join(failed)}"
    report = [f"# Lần chạy {stamp}", "", f"- Kết quả: **{status}**", f"- Commit: `{commit_label}`",
              f"- Luồng: {', '.join(results)}", f"- Ghi chú: {args.note or '-'}", ""] + details
    (LOG / f"{stamp}.md").write_text("\n".join(report), encoding="utf-8")
    with open(LOG / "HISTORY.md", "a", encoding="utf-8") as history:
        history.write(f"- {stamp} `{commit_label}` {status} — [{args.flows}] {args.note or '-'}\n")
    print(f"\n{status}. Bảng: log/FLOWS.md · chi tiết: log/{stamp}.md", flush=True)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
