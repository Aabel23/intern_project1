"""Read QR codes from the USB scanner and publish the latest to raw_qr.json.

WHAT THIS FILE IS
    Step 1 of the order flow. The store screen shows a QR, the handheld
    scanner reads it, and this writes what it read where order/run_flow.py
    is watching.

THE FLOW OF ONE SCAN
    1.  resolve_port() finds the scanner, preferring the stable
        /dev/serial/by-id/ symlink over /dev/ttyACM0, because ACM numbers
        are handed out in plug order and move if anything else is attached.
    2.  The port is opened with exclusive=True so a second copy cannot
        attach. Without it two readers each get a random half of every code.
    3.  iter_codes() accumulates bytes and cuts them at CR or LF. A burst
        arrives in milliseconds, so anything still buffered after
        PARTIAL_FLUSH_SECONDS of silence is a complete code from a scanner
        with no terminator configured, and is emitted too.
    4.  A code identical to the previous one within DEDUP_WINDOW_SECONDS is
        dropped -- holding a code in the beam makes most scanners fire
        repeatedly, and the customer only ordered once.
    5.  raw_qr.json is replaced with that one code.

THE FILE IT WRITES
    scan/raw_qr.json -- one object holding the most recent code:

        {"qr_code": "000602080200010902000112513",
         "timestamp": "2026-08-07T10:52:03.184+07:00"}

    Each scan overwrites the last. The machine pours one cup at a time and
    order/qr_to_recipe.py builds one recipe from one code, so a history
    here would only ever be read for its final entry.

    The write is atomic: a temporary file in the same directory is renamed
    over the target. A reader polling the file sees the old code or the new
    one, never a half-written document.

THE TWO MODES THIS SCANNER HAS
    The USBScn module enumerates as one of two different USB devices, and
    which one it picks is stored in the scanner, not on the Pi:

        0218:0212  CDC-ACM  -> /dev/ttyACM0 appears. What this file needs.
        0218:0210  HID      -> no serial port at all. The scanner types the
                               code as keystrokes into whatever window has
                               focus, like a keyboard.

    Both report the same serial number, so the device silently swaps
    identity when a configuration barcode is scanned. In HID mode there is
    nothing here to open, which looks exactly like an unplugged cable -- so
    explain_missing_port() checks sysfs and says which case it is.

RUNNING IT
    python3 -m scan.scanner                  # watch forever
    python3 -m scan.scanner --once           # exit after the first code
    python3 -m scan.scanner --list-ports     # show the serial devices
    python3 -m scan.scanner --print-only     # read, but write nothing

    Reading a serial port needs membership of the 'dialout' group. Exit 0
    is a clean stop, 1 the port could not be opened, 2 the file could not
    be written.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import serial
from serial.serialutil import SerialException

from flexmix_debug import trace          # noqa: E402


if __package__ in {None, ""}:
    project_dir = str(Path(__file__).resolve().parent.parent)

    if project_dir not in sys.path:
        sys.path.insert(0, project_dir)

from configuration import machine          # noqa: E402


SCAN_DIR = Path(__file__).resolve().parent

# Absolute on purpose. As a bare "raw_qr.json" the file landed in whatever
# directory the process happened to start in, and no reader could find it.
DEFAULT_OUTPUT_FILE = SCAN_DIR / "raw_qr.json"

# Thiết bị và tốc độ nằm ở configuration/machine.py -- đổi máy quét là sửa
# ở đó. Tên cũ giữ nguyên vì run_flow và test_gui đọc chúng qua module này.
DEFAULT_BAUD_RATE = machine.SCANNER_BAUD_RATE

PORT_GLOB = machine.SCANNER_PORT_GLOB
SCANNER_ID_HINT = machine.SCANNER_ID_HINT    # matched case-insensitively
FALLBACK_PORT = machine.SCANNER_FALLBACK_PORT

# Short, so a partial code is noticed quickly and Ctrl+C stays responsive.
SERIAL_READ_TIMEOUT_SECONDS = 0.2

# A scanner sends a whole code in a few milliseconds. Silence for longer
# than this means the code is finished, even without a CR or LF after it.
PARTIAL_FLUSH_SECONDS = 0.4

DEDUP_WINDOW_SECONDS = 2.0
RECONNECT_DELAY_SECONDS = 2.0

TERMINATORS = (b"\r\n", b"\r")

# Where the kernel lists USB devices, used to tell "unplugged" apart from
# "plugged in, but not presenting a serial port".
USB_DEVICES_GLOB = "/sys/bus/usb/devices/*"
HID_INTERFACE_CLASS = "03"


def now_text() -> str:
    """Local time as ISO 8601 with an offset, as the rest of the project."""
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def list_serial_ports() -> list[str]:
    """Return every serial device that could be the scanner."""
    return sorted(glob.glob(PORT_GLOB)) + sorted(glob.glob("/dev/ttyACM*"))


@trace
def resolve_port(requested: str | None = None) -> str:
    """Work out which device file to open.

    An explicit --port wins. Otherwise prefer the /dev/serial/by-id/ entry
    whose name contains SCANNER_ID_HINT, then any by-id entry, and only
    then FALLBACK_PORT -- by-id names are tied to the device, while ACM
    numbers are handed out in plug order.
    """
    if requested:
        return requested

    by_id = sorted(glob.glob(PORT_GLOB))

    for path in by_id:
        if SCANNER_ID_HINT in os.path.basename(path).lower():
            return path

    return by_id[0] if by_id else FALLBACK_PORT


def _read_sysfs(path: Path) -> str:
    """Return a sysfs attribute's contents, or "" if it cannot be read."""
    try:
        return path.read_text().strip()
    except OSError:
        return ""


@trace
def find_usb_scanner() -> dict[str, str] | None:
    """Locate the scanner in sysfs whichever mode it is in.

    Looks at the USB device tree rather than /dev, so the scanner is found
    even when it presents no serial port at all.
    """
    for device_text in sorted(glob.glob(USB_DEVICES_GLOB)):
        device = Path(device_text)
        product = _read_sysfs(device / "product")
        manufacturer = _read_sysfs(device / "manufacturer")

        if SCANNER_ID_HINT not in f"{product} {manufacturer}".lower():
            continue

        driver = ""
        interface_class = ""

        for interface in sorted(device.glob(f"{device.name}:*")):
            interface_class = _read_sysfs(interface / "bInterfaceClass")
            link = interface / "driver"
            if link.is_symlink():
                driver = os.path.basename(os.path.realpath(link))
            break

        return {
            "product": product,
            "usb_id": f"{_read_sysfs(device / 'idVendor')}:"
                      f"{_read_sysfs(device / 'idProduct')}",
            "driver": driver,
            "interface_class": interface_class,
        }

    return None


def explain_missing_port() -> str:
    """Say why there is no serial port to open.

    "No such file or directory" reads as a broken cable, but this scanner
    also produces it whenever it has been switched into HID keyboard mode.
    Those need completely different fixes, so name the one that applies.
    """
    scanner_device = find_usb_scanner()

    if scanner_device is None:
        return (
            "Không tìm thấy máy quét trên cổng USB. "
            "Kiểm tra dây USB, hoặc rút ra cắm lại."
        )

    if scanner_device["interface_class"] == HID_INTERFACE_CLASS:
        return (
            f"Máy quét ĐANG CẮM ({scanner_device['product']}, "
            f"{scanner_device['usb_id']}) nhưng ở chế độ BÀN PHÍM (USB-HID), "
            "nên không có cổng serial nào.\n"
            "[scanner] Ở chế độ này máy quét GÕ mã như bàn phím vào cửa sổ "
            "đang được chọn, thay vì gửi qua /dev/ttyACM*.\n"
            "[scanner] Quét mã cấu hình 'USB COM Port Emulation' "
            "(hoặc 'USB Virtual COM' / 'USB-COM') trong sách hướng dẫn "
            "để chuyển về chế độ serial; USB id sẽ đổi thành 0218:0212."
        )

    return (
        f"Máy quét đang cắm ({scanner_device['product']}, "
        f"{scanner_device['usb_id']}, driver '{scanner_device['driver']}') "
        "nhưng chưa tạo ra cổng serial nào. Thử rút ra cắm lại."
    )


@trace
def write_scan(path: Path, code: str) -> None:
    """Replace the output file with this one code, atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")

    document = {"qr_code": code, "timestamp": now_text()}

    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(document, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())

    os.replace(temporary, path)


def iter_codes(handle: serial.Serial):
    """Yield each complete QR code the scanner sends.

    pyserial's readline() cannot be used: on a read timeout it returns
    whatever arrived so far, so a code split across two USB packets is
    delivered as two separate codes. Buffering here and cutting only at a
    real terminator avoids that.
    """
    buffer = bytearray()
    last_byte_at = time.monotonic()

    while True:
        chunk = handle.read(max(1, handle.in_waiting))
        now = time.monotonic()

        if chunk:
            buffer.extend(chunk)
            last_byte_at = now

            normalised = bytes(buffer)
            for terminator in TERMINATORS:
                normalised = normalised.replace(terminator, b"\n")

            pieces = normalised.split(b"\n")
            buffer = bytearray(pieces.pop())    # trailing, still incomplete

            for piece in pieces:
                code = piece.decode("utf-8", errors="replace").strip()
                if code:
                    yield code
            continue

        # Nothing arrived. Anything left over is a terminator-less code.
        if buffer and now - last_byte_at >= PARTIAL_FLUSH_SECONDS:
            code = bytes(buffer).decode("utf-8", errors="replace").strip()
            buffer.clear()
            if code:
                yield code


@trace
def scan_forever(
    *,
    port: str,
    baud_rate: int,
    output_path: Path,
    once: bool,
    write_output: bool,
) -> int:
    """Open the scanner and publish codes until stopped. Returns an exit code.

    Reopens the port after a SerialException, because a kiosk has to survive
    the scanner being unplugged. A port that cannot be opened on the very
    first attempt is reported and gives up, since that is almost always a
    wrong path or a missing 'dialout' group rather than a transient fault.
    """
    last_code: str | None = None
    last_code_at = 0.0
    ever_opened = False

    while True:
        try:
            with serial.Serial(
                port,
                baud_rate,
                timeout=SERIAL_READ_TIMEOUT_SECONDS,
                exclusive=True,
            ) as scanner:
                ever_opened = True
                print(f"[scanner] Sẵn sàng quét mã QR trên {port}. "
                      "Bấm Ctrl+C để dừng.", flush=True)

                for code in iter_codes(scanner):
                    now = time.monotonic()

                    if (
                        code == last_code
                        and now - last_code_at < DEDUP_WINDOW_SECONDS
                    ):
                        continue

                    last_code = code
                    last_code_at = now

                    print(f"[scanner] Đã quét: {code}", flush=True)

                    if write_output:
                        try:
                            write_scan(output_path, code)
                        except OSError as error:
                            print(
                                f"[scanner] Không ghi được {output_path}: "
                                f"{error}",
                                file=sys.stderr, flush=True,
                            )
                            return 2

                    if once:
                        return 0

        except SerialException as error:
            if not ever_opened:
                print(
                    f"[scanner] Không mở được cổng {port}: {error}",
                    file=sys.stderr, flush=True,
                )
                available = list_serial_ports()

                if available:
                    print("[scanner] Các cổng đang có: " + ", ".join(available),
                          file=sys.stderr, flush=True)
                else:
                    print(f"[scanner] {explain_missing_port()}",
                          file=sys.stderr, flush=True)
                return 1

            print(
                f"[scanner] Mất kết nối ({error}). Thử lại sau "
                f"{RECONNECT_DELAY_SECONDS:g}s...",
                file=sys.stderr, flush=True,
            )
            time.sleep(RECONNECT_DELAY_SECONDS)

        except KeyboardInterrupt:
            print("\n[scanner] Đã dừng chương trình theo yêu cầu.", flush=True)
            return 0


@trace
def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns a shell-friendly exit code."""
    parser = argparse.ArgumentParser(
        description="Đọc mã QR từ máy quét USB và ghi ra raw_qr.json.",
    )
    parser.add_argument("--port", help="Cổng serial. Mặc định: tự dò.")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD_RATE,
                        help=f"Tốc độ baud (mặc định {DEFAULT_BAUD_RATE}).")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_FILE,
                        help=f"File kết quả (mặc định {DEFAULT_OUTPUT_FILE}).")
    parser.add_argument("--once", action="store_true",
                        help="Thoát ngay sau khi quét được một mã.")
    parser.add_argument("--print-only", action="store_true",
                        help="Chỉ in ra màn hình, không ghi file.")
    parser.add_argument("--list-ports", action="store_true",
                        help="Liệt kê các cổng serial rồi thoát.")
    args = parser.parse_args(argv)

    if args.list_ports:
        ports = list_serial_ports()
        print("\n".join(ports) if ports else "Không tìm thấy cổng serial nào.")
        return 0 if ports else 1

    port = resolve_port(args.port)
    print(f"[scanner] Đang mở cổng {port}...", flush=True)

    return scan_forever(
        port=port,
        baud_rate=args.baud,
        output_path=args.output,
        once=args.once,
        write_output=not args.print_only,
    )


if __name__ == "__main__":
    raise SystemExit(main())
