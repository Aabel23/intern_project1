"""In lại từng hàm mà máy đi qua trong lúc chạy, để lần theo luồng code.

WHAT THIS FILE IS
    A trace switch for the whole machine. Turn it on and every step the
    runner takes prints itself as it happens -- which function was
    entered, with what, what it gave back, and how long it took. Turn it
    off and the decorators hand back the original functions untouched, so
    the machine runs exactly as it did before.

CÁCH BẬT / TẮT  (đây là "macro" anh yêu cầu)
    Sửa thẳng trong file này:

        FLEXMIX_DEBUG_ON = True     # bật
        FLEXMIX_DEBUG_ON = False    # tắt

    Hoặc bật/tắt từ dòng lệnh mà không phải sửa code:

        FLEXMIX_DEBUG=1 python3 -m order.process_runner
        FLEXMIX_DEBUG=0 python3 -m order.process_runner
        FLEXMIX_DEBUG=0 python3 main.py

    Muốn ghi ra file để đọc lại sau (vẫn in ra màn hình như thường):

        FLEXMIX_DEBUG_FILE=order/debug.log python3 main.py

CÁCH ĐỌC MỘT DÒNG
        [DBG]    12.480s pump-6     |   -> run_pump_for_duration(pump=6, duration_sec=5.57)
        |        |       |          |   |
        |        |       |          |   `- vào hàm, kèm tham số
        |        |       |          `- thụt lề = độ sâu lời gọi
        |        |       `- tên thread (bơm chạy song song thì thấy rõ ở đây)
        |        `- giây kể từ lúc tiến trình khởi động
        `- lọc bằng: python3 main.py | grep DBG

    Ba loại dòng:
        ->  vào hàm
        <-  ra khỏi hàm, kèm giá trị trả về và thời gian chạy
        !!  hàm ném lỗi, kèm loại lỗi và thời gian chạy

DÙNG TRONG CODE
    from flexmix_debug import trace, debug

    @trace                      # in ra mỗi lần hàm này chạy
    def verify_pump_step(...):
        debug("cân đọc được", measured)     # in một dòng bất kỳ

WHY THE DECORATOR DISAPPEARS WHEN IT IS OFF
    trace() returns the function it was given when the switch is off, so
    there is no wrapper, no clock read and no branch on the hot path --
    run_pump_for_duration is called on every pour and reads the load cell
    loop is called ten times a second. "Off" has to mean off.
"""

from __future__ import annotations

import functools
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, TypeVar


# ── CÔNG TẮC DEBUG ──────────────────────────────────────────────────────────
FLEXMIX_DEBUG_ON = True

# Biến môi trường thắng giá trị ở trên, để bật/tắt mà không phải sửa file.
_ENVIRONMENT_SWITCH = os.environ.get("FLEXMIX_DEBUG")

if _ENVIRONMENT_SWITCH is not None:
    FLEXMIX_DEBUG_ON = _ENVIRONMENT_SWITCH.strip().lower() not in {
        "", "0", "off", "false", "no",
    }

# Ghi thêm ra file. Rỗng = chỉ in ra màn hình.
FLEXMIX_DEBUG_FILE = os.environ.get("FLEXMIX_DEBUG_FILE", "")


PREFIX = "[DBG]"
INDENT = "  "
# Một dict công thức dài vài nghìn ký tự sẽ nhấn chìm mọi thứ khác, nên mỗi
# giá trị bị cắt còn đúng một mẩu đủ để nhận ra nó là cái gì.
MAX_VALUE_CHARS = 56

_started_at = time.monotonic()
_write_lock = threading.Lock()
_depth = threading.local()

T = TypeVar("T", bound=Callable[..., Any])


def is_on() -> bool:
    """Cho code khác hỏi xem debug đang bật hay không."""
    return FLEXMIX_DEBUG_ON


# ── ĐỊNH DẠNG ───────────────────────────────────────────────────────────────

def short(value: object) -> str:
    """Rút một giá trị thành một mẩu ngắn nhận diện được.

    The recipe document and every step are dicts thousands of characters
    wide. Printed whole they bury the line they are on, so the things
    worth seeing -- which step, how many pumps, is the stop flag set --
    are pulled out and the rest is named by shape only.
    """
    if value is None or isinstance(value, (bool, int)):
        return repr(value)

    if isinstance(value, float):
        return f"{value:.2f}"

    if isinstance(value, threading.Event):
        return "Event(set)" if value.is_set() else "Event(clear)"

    if isinstance(value, dict):
        if "step" in value:
            return f"<step {value['step']} {value.get('type', '?')}>"

        if "drink_name" in value:
            return f"<đơn {value.get('drink_name')}>"

        return f"<dict {len(value)} khoá>"

    if isinstance(value, (bytes, bytearray)):
        # Khoá mã hoá QR đi qua đây dưới dạng bytes. Log có thể bị gửi đi
        # nơi khác, nên chỉ in độ dài, tuyệt đối không in nội dung.
        return f"<{len(value)} bytes>"

    if isinstance(value, Path):
        # Đường dẫn tuyệt đối dài hơn cả dòng debug, mà cái đáng quan tâm
        # chỉ là tên file.
        return f"<{value.name}>"

    if isinstance(value, (list, tuple, set)):
        # (baseline, poured) trả về từ verify_pump_step là thứ đáng xem
        # nhất trong cả file này, nên tuple ngắn toàn số thì in thẳng ra.
        if len(value) <= 4 and all(
            item is None or isinstance(item, (bool, int, float, str))
            for item in value
        ):
            return "(" + ", ".join(short(item) for item in value) + ")"

        return f"<{type(value).__name__} {len(value)} phần tử>"

    text = repr(value)

    if len(text) > MAX_VALUE_CHARS:
        text = text[:MAX_VALUE_CHARS - 3] + "..."

    return text


# Tham số mang tên này thì che giá trị đi, dù nó là kiểu gì.
SECRET_NAMES = frozenset({"key", "secret", "token", "password", "passwd"})


def _arguments(args: tuple, kwargs: dict) -> str:
    """Ghép tham số thành một chuỗi đọc được, che các tham số bí mật."""
    parts = [short(value) for value in args]
    parts += [
        f"{name}=<ẩn>" if name.lower() in SECRET_NAMES else f"{name}={short(value)}"
        for name, value in kwargs.items()
    ]
    return ", ".join(parts)


def _emit(text: str) -> None:
    """In một dòng debug, và ghi ra file nếu có yêu cầu.

    Locked because the pumps of one step each run in their own thread and
    two half-written lines interleaved are worse than no line at all.
    """
    depth = getattr(_depth, "value", 0)
    thread = threading.current_thread().name
    line = (
        f"{PREFIX} {time.monotonic() - _started_at:9.3f}s "
        f"{thread:<12} {INDENT * depth}{text}"
    )

    with _write_lock:
        print(line, file=sys.stdout, flush=True)

        if FLEXMIX_DEBUG_FILE:
            try:
                with open(FLEXMIX_DEBUG_FILE, "a", encoding="utf-8") as log:
                    log.write(line + "\n")
            except OSError:
                # Không ghi được file thì thôi -- debug không bao giờ được
                # phép làm hỏng một đơn đang chạy.
                pass


# ── HAI THỨ DÙNG TRONG CODE ─────────────────────────────────────────────────

def debug(*parts: object) -> None:
    """In một dòng bất kỳ, thụt lề theo đúng độ sâu đang đứng."""
    if not FLEXMIX_DEBUG_ON:
        return

    _emit(" ".join(str(part) for part in parts))


def trace(function: T) -> T:
    """In ra mỗi lần hàm chạy: vào, ra, giá trị trả về, thời gian chạy.

    Returns the function unchanged when the switch is off -- see the
    module docstring for why that matters.
    """
    if not FLEXMIX_DEBUG_ON:
        return function

    name = function.__name__

    @functools.wraps(function)
    def wrapper(*args: object, **kwargs: object) -> object:
        _emit(f"-> {name}({_arguments(args, kwargs)})")

        _depth.value = getattr(_depth, "value", 0) + 1
        started = time.monotonic()

        try:
            result = function(*args, **kwargs)
        except BaseException as error:      # noqa: BLE001 - chỉ in rồi ném tiếp
            elapsed = time.monotonic() - started
            _depth.value -= 1
            _emit(
                f"!! {name} ném {type(error).__name__}: {error} "
                f"({elapsed:.3f}s)"
            )
            raise
        else:
            elapsed = time.monotonic() - started
            _depth.value -= 1
            _emit(f"<- {name} = {short(result)} ({elapsed:.3f}s)")
            return result

    return wrapper       # type: ignore[return-value]


if __name__ == "__main__":
    print(f"FLEXMIX_DEBUG_ON = {FLEXMIX_DEBUG_ON}")
    print(f"FLEXMIX_DEBUG_FILE = {FLEXMIX_DEBUG_FILE or '(chỉ in màn hình)'}")

    @trace
    def vi_du_bom(pump: int, gram: float) -> float:
        debug("đang chạy bơm", pump)
        time.sleep(0.2)
        return gram

    @trace
    def vi_du_buoc(step: dict) -> None:
        vi_du_bom(6, 50.0)
        vi_du_bom(7, 30.0)

    vi_du_buoc({"step": 5, "type": "pump"})
