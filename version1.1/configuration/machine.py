"""Everything that differs between two physical FlexMix machines.

WHAT BELONGS HERE, AND WHAT DOES NOT
    Here: anything an installer or an operator would have to change when
    building a second machine, or when a hose, a chip or a printer is
    swapped on this one. Wiring, I2C addresses, ports, device names,
    label size, the two policy numbers a shop might argue about.

    NOT here: constants that are part of how an algorithm works --
    HX711 resync pulse counts, the 0.02s panel poll, the median window
    on the scale. Those are not settings; moving them here would invite
    somebody to "tune" a number whose correct value is a property of the
    chip, not of the shop. They stay next to the code that reasons about
    them.

    The test is simple: would a second machine, built next week from
    this repository, need a different value? If yes it is a setting.

WHY ONE FILE
    These used to be scattered across nine modules -- pump wiring in
    pump_control/, scale pins in loadcell/, I2C addresses in
    panel_control/, four different port numbers in four servers, the
    printer's model name in printer/. Building a second machine meant
    finding all of them, and the only way to know you had was to run out
    of things that broke.

WHY IT IMPORTS NOTHING
    No gpiozero, no smbus2, no database. Reading a setting must not claim
    a GPIO line, open a bus, or need MySQL to be up -- this module is
    read while deciding how to open those things, and on laptops that
    have none of them.

SECRETS ARE NOT HERE
    QRPROTO_KEY and the MySQL password come from the environment, not
    from this file -- see configuration/qrproto_config.py and
    database/config.py. A secret in a tracked file is a secret in every
    clone and every backup. MACHINE_ID lives with the key it is used
    beside, in qrproto_config.py, for the same reason: the two are only
    ever meaningful together.

MỖI MÁY MỘT HỒ SƠ -- /etc/flexmix/machine_profile.json
    Giá trị viết trong file này là của MÁY #1, và là mặc định. Máy đi dây
    khác thì ghi phần khác vào hồ sơ, KHÔNG sửa file này: sửa ở đây là mỗi
    máy một bản fork của repo, và lần phát hành kế tiếp đè mất nó -- nhất
    là khi phát hành thành "checkout tag + đổi symlink", lúc cả thư mục
    mã nguồn bị thay.

    Hồ sơ chỉ cần ghi cái KHÁC. Không có file là máy #1 nguyên trạng.
    Chi tiết, và vì sao hồ sơ hỏng thì từ chối chạy chứ không rơi về mặc
    định, nằm ở mục HỒ SƠ MÁY cuối file.

    Đọc hồ sơ chỉ là đọc một file JSON nhỏ bằng thư viện chuẩn -- vẫn
    không đụng GPIO, bus hay MySQL, nên mục WHY IT IMPORTS NOTHING vẫn
    đúng.

    Xem giá trị đang dùng, và mỗi cái lấy từ đâu:
        ./.venv/bin/python -m configuration.machine
"""

from __future__ import annotations

import difflib
import json
import os
from pathlib import Path


# ==========================================================================
# PUMPS -- which pump is wired to which BCM line
# ==========================================================================
#
# Pump number as printed on the machine's own casing -> the BCM line
# driving that pump's MOSFET. This is the table calib_pump.py is keyed on
# and the one every pour reads.
#
# Two pumps on one line is a typo whose symptom is a pump running when a
# different one was asked for -- a drink that tastes wrong, with nothing
# in any log. It is refused at import instead; see the check below.

PUMP_GPIO: dict[int, int] = {
    1: 26,
    2: 15,
    3: 21,
    4: 20,
    5: 16,
    6: 12,
    7: 13,
    8: 6,
    9: 5,
    10: 14,
}

# Kiểm tra trùng chân và ba giá trị suy ra từ bảng này (PIN_TO_PUMP,
# PUMP_NUMBERS, GPIO_PINS) nằm ở CUỐI file, sau khi hồ sơ máy đã được áp:
# tính ở đây là tính trên dây của máy #1 trong khi máy này có thể đi dây
# khác.

# PWM frequency the pump MOSFETs are driven at.
PUMP_FREQUENCY_HZ = 1000


# ==========================================================================
# LOAD CELL -- the HX711 amplifier under the glass
# ==========================================================================
#
# Opened in exactly one place, loadcell.open_pins(). Anything else that
# opens them separately drifts on the pull-up and silently brings back the
# "broken wire reads -399.4 g" fault.

LOADCELL_SCK_PIN = 4     # clock, driven by us
LOADCELL_DT_PIN = 18     # data, driven by the chip


# ==========================================================================
# BUTTON PANEL -- two PCF8575 expanders on I2C
# ==========================================================================

PANEL_I2C_BUS = 1
PANEL_I2C_ADDR_LED = 0x21
PANEL_I2C_ADDR_BUTTON = 0x20
PANEL_COUNT = 16

# The two panel buttons that mean something outside an order. Both are
# read only while the machine is idle, except 14 -- see button_watch.py.
PANEL_BUTTON_RESTART = 14      # restarts flexmix-backend.service
PANEL_BUTTON_TEST_MODE = 15    # toggles manual test mode

# How many panel lamps may be lit AT THE SAME TIME.
#
# This is a current limit, not a preference. The PCF8575 is
# quasi-bidirectional: a lamp is lit by driving its pin LOW, so every lit
# lamp SINKS its current through the chip's GND pin. The datasheet allows
# 25 mA on one pin but only about 100 mA through the package.
#
# The LED test used to light all sixteen at once for over a second. At even
# 10 mA a lamp that is 160 mA -- past the absolute maximum -- and the chip
# answered by latching up: it stopped acknowledging its address on the I2C
# bus and stayed that way until somebody unplugged it. Observed on this
# machine on 2026-09-08: i2cdetect showed 0x20 but not 0x21 after every run
# of the lamp test, and 0x21 came back only after a power cycle.
#
# Four is deliberately conservative, chosen without measuring the lamps.
# If you know what one lamp actually draws, raise it: keep
# lamps x current well under 100 mA. Lighting them one at a time is always
# safe, which is what the walk-through part of the test does.
PANEL_MAX_LEDS_ON = 4


# ==========================================================================
# NETWORK PORTS
# ==========================================================================
#
# 8080 is the only port a browser ever needs: every screen is served from
# it. Which network interfaces it is bound to is a separate question, and
# a computed one -- see configuration/net_addresses.py.

STORE_PORT = 8080          # all four screens + the admin API
RUNNER_PORT = 8000         # process_runner, loopback only, only while pouring

# Standalone development ports. main.py opens neither: admin_gui/serve.py
# and test_gui/serve.py listen on these only when run on their own.
ADMIN_STANDALONE_PORT = 8100
TEST_STANDALONE_PORT = 8090


# ==========================================================================
# LABEL PRINTER
# ==========================================================================
#
# PRINTER_NAME is the CUPS queue name -- `lpstat -p` lists what this
# machine actually has. The millimetres are the stock loaded in it; get
# them wrong and the printer either crops the QR or wastes a label.

PRINTER_NAME = "XP-350BM"
LABEL_WIDTH_MM = 50.0
LABEL_HEIGHT_MM = 30.0
LABEL_GAP_MM = 2.0


# ==========================================================================
# BARCODE SCANNER
# ==========================================================================
#
# Found by walking /dev/serial/by-id and matching SCANNER_ID_HINT, so
# replugging into another USB socket does not change anything. The
# fallback is only used when that directory has nothing in it.

SCANNER_BAUD_RATE = 9600
SCANNER_PORT_GLOB = "/dev/serial/by-id/*"
SCANNER_ID_HINT = "usbscn"          # matched case-insensitively
SCANNER_FALLBACK_PORT = "/dev/ttyACM0"


# ==========================================================================
# SHOP POLICY
# ==========================================================================

# How long a printed label stays valid. A ticket older than this is
# expired at the moment somebody tries to scan it, in the same
# transaction as the claim -- see database/order_ticket.py.
TICKET_LIFETIME_HOURS = 24

# How often the machine pulls the menu down from the database.
MENU_SYNC_INTERVAL_MINUTES = 1


# ==========================================================================
# HỒ SƠ MÁY -- /etc/flexmix/machine_profile.json
# ==========================================================================
#
# Ví dụ, một máy có bơm 3 nối chân 19 và máy in tên khác:
#
#     {
#       "_note": "máy quán Quận 3 -- bơm 3 chuyển sang chân 19 ngày 02/10",
#       "PUMP_GPIO": {"1": 26, "2": 15, "3": 19, "4": 20, "5": 16,
#                     "6": 12, "7": 13, "8": 6, "9": 5, "10": 14},
#       "PRINTER_NAME": "XP-365B"
#     }
#
# PUMP_GPIO ghi CẢ BẢNG, không ghi riêng một bơm: bảng ghi thiếu là máy có
# ít bơm hơn, chứ không phải "các bơm còn lại như máy #1". Số bơm viết
# thành chuỗi vì JSON bắt buộc khoá là chuỗi. Tên bắt đầu bằng "_" bị bỏ
# qua -- JSON không có comment, mà hồ sơ của một máy cụ thể luôn có điều
# đáng ghi lại.
#
# `python -m configuration.machine --json` in ra hồ sơ ĐẦY ĐỦ đang dùng, ở
# đúng định dạng này. Máy mới bắt đầu từ đó, rồi xoá dòng nào giống máy #1.
#
# VÌ SAO HỒ SƠ HỎNG THÌ TỪ CHỐI, KHÔNG RƠI VỀ MẶC ĐỊNH
#     order_mode.py rơi về mặc định khi file hỏng, và ở đó là đúng: mặc
#     định của nó là cách máy vẫn luôn bán. Ở đây mặc định là dây của MỘT
#     MÁY KHÁC. Có hồ sơ nghĩa là đã có người nói "máy này không đi dây như
#     máy #1"; đọc hỏng rồi lặng lẽ dùng dây máy #1 là bơm 3 chạy khi công
#     thức gọi bơm 5 -- ly sai vị, không log nào. Đúng cái lỗi mà kiểm tra
#     trùng chân bên dưới tồn tại để chặn.
#
#     Nên: file có mà không đọc được, sai JSON, sai kiểu, hay có tên lạ --
#     ném MachineProfileError lúc import, kèm câu nói rõ chỗ sai. systemd
#     dựng lại tiến trình và journalctl ghi đúng câu đó. Ồn, nhưng không
#     rót sai. Tên lạ bị từ chối cùng lý do: "PRINTR_NAME" mà bỏ qua im lặng
#     là máy chạy với tên máy in của máy #1.
#
# VÌ SAO JSON, VÀ VÌ SAO Ở /etc
#     /etc chứ không phải /var/lib/flexmix: đây là thứ NGƯỜI đặt, không
#     phải số máy tự đo -- cùng ranh giới configuration.py đã vạch. Nằm
#     ngoài checkout nên sống qua mọi lần phát hành.
#
#     JSON chứ không phải .py: dữ liệu thì kiểm được từng trường và không
#     chạy được gì, và chương trình khác -- agent của Hub -- đọc được mà
#     không phải import mã của máy.
#
# FLEXMIX_MACHINE_PROFILE trỏ sang file khác, để thử một hồ sơ trên máy
# phát triển mà không cần root. Máy bán hàng không đặt biến này.

PROFILE_FILE = Path(
    os.environ.get("FLEXMIX_MACHINE_PROFILE", "/etc/flexmix/machine_profile.json")
)


class MachineProfileError(ValueError):
    """Có hồ sơ máy mà không dùng được. Xem mục HỒ SƠ MÁY."""


def _whole(name: str, value, low: int, high: int | None = None) -> int:
    # bool là lớp con của int trong Python: `true` trong JSON sẽ lọt qua
    # isinstance(value, int) và thành chân BCM số 1.
    if isinstance(value, bool) or not isinstance(value, int):
        raise MachineProfileError(f"{name}: cần một số nguyên, file ghi {value!r}")

    if value < low or (high is not None and value > high):
        span = f"từ {low} trở lên" if high is None else f"từ {low} đến {high}"
        raise MachineProfileError(f"{name}: phải {span}, file ghi {value}")

    return value


def _int_from(low: int, high: int | None = None):
    return lambda name, value: _whole(name, value, low, high)


# Pi 4 có BCM 0-27 trên đầu 40 chân.
_bcm = _int_from(0, 27)
_port = _int_from(1, 65535)
_positive = _int_from(1)
_index = _int_from(0)


def _i2c_address(name: str, value) -> int:
    # Cho viết "0x21" -- đúng thứ i2cdetect in ra. Bắt người ta tự đổi sang
    # 33 là mời một lần đổi nhầm.
    address = value

    if isinstance(value, str):
        try:
            address = int(value, 0)
        except ValueError:
            address = None

    # 0x03-0x77 là dải địa chỉ 7 bit dùng được; hai đầu dành cho giao thức.
    # Báo lỗi bằng đúng chữ người đó gõ: viết "0x80" mà nhận lại "128" là
    # phải ngồi đổi hệ cơ số mới hiểu mình sai ở đâu.
    if (isinstance(address, bool) or not isinstance(address, int)
            or not 0x03 <= address <= 0x77):
        raise MachineProfileError(
            f"{name}: cần địa chỉ từ \"0x03\" đến \"0x77\", file ghi {value!r}")

    return address


def _millimetres(name: str, value) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MachineProfileError(f"{name}: cần một số (mm), file ghi {value!r}")

    if value < 0:
        raise MachineProfileError(f"{name}: không được âm, file ghi {value}")

    return float(value)


def _text(name: str, value) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MachineProfileError(
            f"{name}: cần một chuỗi không rỗng, file ghi {value!r}")

    return value


def _pump_map(name: str, value) -> dict[int, int]:
    if not isinstance(value, dict) or not value:
        raise MachineProfileError(
            f"{name}: cần một bảng {{\"số bơm\": chân BCM}}, file ghi {value!r}")

    table = {}

    for key, pin in value.items():
        # Chỉ nhận chữ số: int(" 3") và int("+3") đều chạy, và cả hai là
        # dấu của một file gõ tay có vấn đề.
        if not key.isdigit() or int(key) < 1:
            raise MachineProfileError(
                f"{name}: số bơm {key!r} không hợp lệ -- viết \"1\", \"2\"...")

        table[int(key)] = _bcm(f"{name}[{key}]", pin)

    return table


# Tên nào ghi được trong hồ sơ, và kiểm bằng gì. Ba giá trị suy ra
# (PIN_TO_PUMP, PUMP_NUMBERS, GPIO_PINS) cố ý không có ở đây: chúng tính
# từ PUMP_GPIO, cho ghi riêng là cho chúng cãi nhau với nó.
_PROFILE_FIELDS = {
    "PUMP_GPIO": _pump_map,
    "PUMP_FREQUENCY_HZ": _positive,
    "LOADCELL_SCK_PIN": _bcm,
    "LOADCELL_DT_PIN": _bcm,
    "PANEL_I2C_BUS": _index,
    "PANEL_I2C_ADDR_LED": _i2c_address,
    "PANEL_I2C_ADDR_BUTTON": _i2c_address,
    "PANEL_COUNT": _positive,
    "PANEL_BUTTON_RESTART": _index,
    "PANEL_BUTTON_TEST_MODE": _index,
    "PANEL_MAX_LEDS_ON": _positive,
    "STORE_PORT": _port,
    "RUNNER_PORT": _port,
    "ADMIN_STANDALONE_PORT": _port,
    "TEST_STANDALONE_PORT": _port,
    "PRINTER_NAME": _text,
    "LABEL_WIDTH_MM": _millimetres,
    "LABEL_HEIGHT_MM": _millimetres,
    "LABEL_GAP_MM": _millimetres,
    "SCANNER_BAUD_RATE": _positive,
    "SCANNER_PORT_GLOB": _text,
    "SCANNER_ID_HINT": _text,
    "SCANNER_FALLBACK_PORT": _text,
    "TICKET_LIFETIME_HOURS": _positive,
    "MENU_SYNC_INTERVAL_MINUTES": _positive,
}


def _read_profile(path: Path) -> dict:
    """Những gì hồ sơ ghi, đã kiểm và đổi kiểu. {} khi không có file."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as error:
        # Có file mà không đọc được KHÔNG phải "không có file" -- xem mục
        # HỒ SƠ MÁY. Hay gặp nhất: tạo bằng sudo nên chỉ root đọc được.
        raise MachineProfileError(
            f"{path}: có file nhưng không đọc được -- {error}. "
            f"Tài khoản chạy máy phải đọc được: sudo chmod 644 {path}"
        ) from error

    try:
        stored = json.loads(text)
    except ValueError as error:
        raise MachineProfileError(
            f"{path}: không phải JSON hợp lệ -- {error}") from error

    if not isinstance(stored, dict):
        raise MachineProfileError(
            f"{path}: ngoài cùng phải là một object {{...}}")

    fields = {
        name: value for name, value in stored.items()
        if not name.startswith("_")
    }

    for name in fields:
        if name not in _PROFILE_FIELDS:
            guess = difflib.get_close_matches(name, _PROFILE_FIELDS, n=1)
            hint = f" -- có phải {guess[0]}?" if guess else ""

            raise MachineProfileError(f"{path}: không có tên {name!r}{hint}")

    try:
        return {
            name: _PROFILE_FIELDS[name](name, value)
            for name, value in fields.items()
        }
    except MachineProfileError as error:
        raise MachineProfileError(f"{path}: {error}") from None


_profile = _read_profile(PROFILE_FILE)
globals().update(_profile)

# Tên nào đang lấy từ hồ sơ thay vì mặc định -- chỗ máy này khác máy #1.
PROFILE_KEYS: frozenset[str] = frozenset(_profile)

del _profile


# ==========================================================================
# SUY RA TỪ BẢNG BƠM -- tính SAU hồ sơ, trên dây thật của máy này
# ==========================================================================

# Loadcell được tính chung với bơm: trước đây cả hai bảng nằm cùng một file
# mà người sửa nhìn thấy cả hai. Giờ một hồ sơ có thể dời chân loadcell sang
# đúng chân của bơm 1 mà không ai để ý -- và mỗi nhịp clock của HX711 là một
# nhịp bơm.
_lines = list(PUMP_GPIO.values()) + [LOADCELL_SCK_PIN, LOADCELL_DT_PIN]
_duplicate_lines = sorted(pin for pin in set(_lines) if _lines.count(pin) > 1)

if _duplicate_lines:
    raise ValueError(
        f"Chân BCM {_duplicate_lines} bị dùng cho hơn một thiết bị. Mỗi bơm "
        f"và mỗi dây loadcell cần một chân riêng -- kiểm PUMP_GPIO và "
        f"LOADCELL_*_PIN, trong configuration/machine.py và {PROFILE_FILE}."
    )

del _lines, _duplicate_lines

# The inverse, derived rather than written out so it cannot disagree.
# admin_gui/serve.py reads it to label a pin with the pump number a person
# would recognise.
PIN_TO_PUMP: dict[int, int] = {pin: n for n, pin in PUMP_GPIO.items()}

PUMP_NUMBERS: tuple[int, ...] = tuple(sorted(PUMP_GPIO))
GPIO_PINS: tuple[int, ...] = tuple(PUMP_GPIO[n] for n in PUMP_NUMBERS)


def effective_profile() -> dict:
    """Hồ sơ đầy đủ đang dùng, đúng định dạng file hồ sơ.

    Đọc ngược lại được: ghi kết quả này vào PROFILE_FILE thì máy chạy y
    hệt. Đó là cách một máy mới bắt đầu hồ sơ của nó.
    """
    profile = {}

    for name in _PROFILE_FIELDS:
        value = globals()[name]

        if name == "PUMP_GPIO":
            value = {str(n): pin for n, pin in sorted(value.items())}
        elif name.startswith("PANEL_I2C_ADDR_"):
            value = f"0x{value:02x}"

        profile[name] = value

    return profile


if __name__ == "__main__":
    import sys

    if "--json" in sys.argv[1:]:
        print(json.dumps(effective_profile(), ensure_ascii=False, indent=2))
        raise SystemExit(0)

    if PROFILE_FILE.exists():
        print(f"Hồ sơ: {PROFILE_FILE}")
    else:
        print(f"Hồ sơ: {PROFILE_FILE} -- không có, toàn bộ là mặc định máy #1")

    print()

    for name, value in effective_profile().items():
        source = "<- hồ sơ" if name in PROFILE_KEYS else ""
        shown = json.dumps(value, ensure_ascii=False)

        print(f"  {name:<28} {shown:<44} {source}".rstrip())
