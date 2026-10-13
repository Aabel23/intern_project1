#!/usr/bin/env python3
"""Ghi log nhiễu / bấm nút trên bảng nút FlexMix (PCF8575 qua I2C) ra file Markdown.

Chạy qua đêm để xem nút 15 (bật/tắt test mode) hay nút 14 (restart backend)
có bị "bấm ma" do nhiễu hay không.

Máy này KHÔNG đọc nút bằng GPIO trực tiếp: nút nằm trên chip PCF8575
(I2C bus 1, địa chỉ 0x20, active-low: bit 0 = đang bấm). Script đọc đúng chip đó.

    python3 button_logger.py                       # ghi vào ./logs/button_log_<ngày giờ>.md
    python3 button_logger.py --mode-file /đường/dẫn/version1.1/test_gui/mode.json
    python3 button_logger.py --fake                # thử trên máy không có Pi

Mặc định CHỈ ĐỌC (không ghi gì vào chip) nên chạy song song với flexmix-backend
được. Nếu muốn chắc chắn không có hai bên cùng đọc bus, dừng backend trước
(sudo systemctl stop flexmix-backend) rồi thêm --init để script tự đặt chip
về trạng thái "nhả hết" (ghi 0xFFFF). Nhớ bật lại backend sau đó.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import signal
import sys
import time
from collections import Counter
from datetime import datetime

# Bản sao từ version1.1/panel_control/panel.py (BUTTON_PIN_MAP): bit vật lý -> vị trí nút.
BUTTON_PIN_MAP = (7, 6, 5, 4, 3, 8, 9, 10, 11, 12, 13, 14, 15, 0, 1, 2)
PANEL_ID_BY_BIT = tuple(BUTTON_PIN_MAP.index(bit) for bit in range(16))
WATCHED = {14: "RESTART backend", 15: "TEST MODE"}   # configuration/machine.py
ALL_HIGH = 0xFFFF
BACKEND_POLL_S = 0.25      # panel_control/button_watch.py POLL_SECONDS
GLITCH_MS = 20.0           # ngắn hơn mức này coi là nhiễu điện
MAX_EVENT_LINES_PER_MIN = 60


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


class I2CReader:
    def __init__(self, bus: int, address: int, init: bool):
        from smbus2 import SMBus, i2c_msg      # cài: pip install smbus2
        self._msg = i2c_msg
        self.bus = SMBus(bus)
        self.address = address
        if init:
            self.bus.i2c_rdwr(i2c_msg.write(address, [0xFF, 0xFF]))

    def read(self) -> int:
        message = self._msg.read(self.address, 2)
        self.bus.i2c_rdwr(message)
        data = list(message)
        return data[0] | (data[1] << 8)

    def close(self):
        self.bus.close()


class FakeReader:
    """Giả lập để thử script: thỉnh thoảng có nhiễu ngắn, bấm thật, và lỗi I2C."""

    def __init__(self):
        self.until = 0.0
        self.word = ALL_HIGH

    def read(self) -> int:
        now = time.monotonic()
        if now >= self.until:
            self.word = ALL_HIGH
            roll = random.random()
            if roll < 0.004:
                bit = random.randrange(16)
                self.word &= ~(1 << bit)
                self.until = now + random.choice([0.002, 0.004, 0.08, 0.6])
            elif roll < 0.0042:
                self.word = 0x0000
                self.until = now + 0.003
            elif roll < 0.0044:
                raise OSError(121, "Remote I/O error (giả lập)")
        return self.word

    def close(self):
        pass


class Log:
    def __init__(self, path: str):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.handle = open(path, "a", encoding="utf-8")
        self.path = path
        self.minute = ""
        self.lines_this_minute = 0
        self.suppressed = 0

    def raw(self, text: str = ""):
        self.handle.write(text + "\n")
        self.handle.flush()
        os.fsync(self.handle.fileno())     # mất điện giữa đêm vẫn còn log

    def event(self, text: str) -> bool:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        if stamp != self.minute:
            self.minute, self.lines_this_minute = stamp, 0
        self.lines_this_minute += 1
        if self.lines_this_minute > MAX_EVENT_LINES_PER_MIN:
            self.suppressed += 1
            return False
        self.raw(text)
        return True

    def close(self):
        self.handle.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--out", help="file .md đầu ra (mặc định logs/button_log_<thời điểm>.md)")
    parser.add_argument("--bus", type=int, default=1)
    parser.add_argument("--addr", type=lambda v: int(v, 0), default=0x20)
    parser.add_argument("--poll-ms", type=float, default=2.0, help="chu kỳ đọc, mặc định 2 ms")
    parser.add_argument("--heartbeat-min", type=float, default=10.0)
    parser.add_argument("--mode-file", help="đường dẫn test_gui/mode.json để ghi lại lúc test mode đổi trạng thái")
    parser.add_argument("--init", action="store_true", help="ghi 0xFFFF lúc mở (chỉ khi đã dừng backend)")
    parser.add_argument("--fake", action="store_true", help="đọc giả lập, để thử script")
    args = parser.parse_args()

    out = args.out or os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs",
                                   f"button_log_{datetime.now():%Y%m%d_%H%M%S}.md")
    log = Log(out)
    reader = FakeReader() if args.fake else I2CReader(args.bus, args.addr, args.init)

    stop = {"flag": False}
    signal.signal(signal.SIGINT, lambda *_: stop.update(flag=True))
    signal.signal(signal.SIGTERM, lambda *_: stop.update(flag=True))

    log.raw(f"# Log nút bấm FlexMix · {datetime.now():%Y-%m-%d %H:%M:%S}")
    log.raw("")
    log.raw(f"- Chip: PCF8575 bus {args.bus} địa chỉ 0x{args.addr:02X}{' (GIẢ LẬP)' if args.fake else ''}; chu kỳ đọc {args.poll_ms:g} ms; "
            f"chế độ {'ghi 0xFFFF lúc mở' if args.init else 'chỉ đọc'}")
    log.raw(f"- Nút theo dõi: 14 = restart backend, 15 = bật/tắt test mode. Backend quét mỗi {BACKEND_POLL_S * 1000:.0f} ms "
            "và đổi trạng thái ngay khi thấy nút 15 ở mức thấp ở một lần quét.")
    log.raw(f"- Phân loại: **NHIỄU** = nút xuống rồi lên trong < {GLITCH_MS:g} ms (đo theo chu kỳ đọc, sai số ± chu kỳ); "
            "**NGẮN** = < 350 ms; **BẤM** = từ 350 ms. Nút 14/15 có ⚠ nghĩa là có thể làm backend đổi trạng thái.")
    log.raw("- `MULTI` = nhiều nút đổi cùng lúc (≥ 4 bit), thường là nhiễu bus / sụt áp / dây I2C, không phải người bấm.")
    log.raw("")
    log.raw("| Thời điểm | Sự kiện | Nút | Thời lượng | Raw (hex) | Ghi chú |")
    log.raw("|---|---|---|---|---|---|")

    period = max(args.poll_ms, 0.5) / 1000.0
    started = time.monotonic()
    last_beat = started
    last_mode_check = started
    mode_open = None
    word = None
    down_at: dict[int, float] = {}
    down_wall: dict[int, str] = {}
    counts = Counter()
    kinds = Counter()
    samples = errors = 0
    max_gap = 0.0
    last_sample = started
    error_streak = 0
    last_error_text = ""

    def label(panel: int) -> str:
        return f"{panel} ({WATCHED[panel]})" if panel in WATCHED else str(panel)

    def check_mode():
        nonlocal mode_open
        if not args.mode_file:
            return
        try:
            with open(args.mode_file, encoding="utf-8") as handle:
                data = json.load(handle)
            value = bool(data.get("open"))
        except (OSError, ValueError):
            return
        if mode_open is None:
            mode_open = value
            log.event(f"| {now_text()} | MODE-FILE | - | - | - | trạng thái test mode lúc bắt đầu: {'BẬT' if value else 'TẮT'} |")
        elif value != mode_open:
            mode_open = value
            log.event(f"| {now_text()} | **TEST MODE {'BẬT' if value else 'TẮT'}** | - | - | - | "
                      f"mode.json đổi (at={data.get('at')}); đối chiếu với dòng nút 15 sát trước đó |")

    try:
        while not stop["flag"]:
            tick = time.monotonic()
            try:
                new = reader.read()
                if error_streak:
                    log.event(f"| {now_text()} | I2C-OK | - | - | - | đọc lại được sau {error_streak} lỗi liên tiếp |")
                    error_streak = 0
            except Exception as error:      # noqa: BLE001
                errors += 1
                error_streak += 1
                text = f"{type(error).__name__}: {error}"
                if error_streak == 1 or text != last_error_text:
                    log.event(f"| {now_text()} | **I2C-LỖI** | - | - | - | {text} |")
                last_error_text = text
                time.sleep(min(0.2 * error_streak, 3.0))
                continue

            samples += 1
            gap = tick - last_sample
            last_sample = tick
            max_gap = max(max_gap, gap)
            if gap > 0.1 and samples > 1:
                log.event(f"| {now_text()} | KẸT-ĐỌC | - | {gap * 1000:.0f} ms | - | "
                          "vòng đọc bị đứng (CPU bận / I2C chậm), có thể bỏ lỡ sự kiện |")

            if word is None:
                held = [PANEL_ID_BY_BIT[b] for b in range(16) if not new & (1 << b)]
                log.event(f"| {now_text()} | BẮT-ĐẦU | - | - | 0x{new:04X} | "
                          f"{'nút đang bị giữ lúc bắt đầu: ' + ', '.join(map(str, held)) if held else 'tất cả nút nhả'} |")
                for b in range(16):
                    if not new & (1 << b):
                        down_at[PANEL_ID_BY_BIT[b]] = tick
                        down_wall[PANEL_ID_BY_BIT[b]] = now_text()
                word = new
            elif new != word:
                changed = word ^ new
                bits = [b for b in range(16) if changed & (1 << b)]
                if len(bits) >= 4:
                    kinds["MULTI"] += 1
                    log.event(f"| {now_text()} | **MULTI** | {','.join(str(PANEL_ID_BY_BIT[b]) for b in bits)} | - | "
                              f"0x{word:04X}→0x{new:04X} | {len(bits)} bit đổi cùng lúc |")
                for b in bits:
                    panel = PANEL_ID_BY_BIT[b]
                    pressed = not new & (1 << b)
                    if len(bits) >= 4:
                        # ghi nhận trạng thái nhưng không thêm dòng riêng cho từng bit
                        if pressed:
                            down_at[panel], down_wall[panel] = tick, now_text()
                        else:
                            down_at.pop(panel, None)
                        continue
                    if pressed:
                        down_at[panel], down_wall[panel] = tick, now_text()
                        counts[panel] += 1
                        log.event(f"| {now_text()} | xuống | {label(panel)} | - | 0x{new:04X} | "
                                  f"{'⚠ ' if panel in WATCHED else ''}bắt đầu mức thấp |")
                    else:
                        started_at = down_at.pop(panel, None)
                        down_wall.pop(panel, None)
                        if started_at is None:
                            continue
                        ms = (tick - started_at) * 1000.0
                        kind = "NHIỄU" if ms < GLITCH_MS else ("NGẮN" if ms < 350 else "BẤM")
                        kinds[kind] += 1
                        if panel in WATCHED:
                            note = ("⚠ nút quan trọng; backend có thể thấy nếu lần quét rơi vào khoảng này (xác suất ≈ "
                                    f"{min(1.0, ms / (BACKEND_POLL_S * 1000)) * 100:.0f}%)")
                        else:
                            note = ""
                        log.event(f"| {now_text()} | lên · **{kind}** | {label(panel)} | {ms:.1f} ms | 0x{new:04X} | {note} |")
                word = new

            if args.mode_file and tick - last_mode_check >= 1.0:
                last_mode_check = tick
                check_mode()

            if tick - last_beat >= args.heartbeat_min * 60:
                last_beat = tick
                log.raw(f"| {now_text()} | ♥ nhịp | - | - | - | chạy {int((tick - started) / 60)} phút; "
                        f"{samples} lần đọc; {errors} lỗi I2C; khoảng cách đọc lớn nhất {max_gap * 1000:.0f} ms; "
                        f"nhiễu/ngắn/bấm/multi = {kinds['NHIỄU']}/{kinds['NGẮN']}/{kinds['BẤM']}/{kinds['MULTI']}; "
                        f"nút 14: {counts[14]}, nút 15: {counts[15]}; bị bỏ bớt dòng (giới hạn {MAX_EVENT_LINES_PER_MIN}/phút): {log.suppressed} |")
                max_gap = 0.0

            remaining = period - (time.monotonic() - tick)
            if remaining > 0:
                time.sleep(remaining)
    finally:
        elapsed = (time.monotonic() - started) / 3600
        log.raw("")
        log.raw(f"## Tóm tắt · dừng lúc {now_text()}")
        log.raw("")
        log.raw(f"- Thời gian chạy: {elapsed:.2f} giờ; {samples} lần đọc; **{errors} lỗi I2C**")
        log.raw(f"- Nhiễu (<{GLITCH_MS:g} ms): **{kinds['NHIỄU']}**; ngắn: {kinds['NGẮN']}; bấm (≥350 ms): {kinds['BẤM']}; multi-bit: **{kinds['MULTI']}**")
        log.raw("- Số lần xuống theo nút: " + (", ".join(f"nút {p}: {c}" for p, c in sorted(counts.items())) or "không có"))
        log.raw(f"- Dòng bị bỏ bớt do giới hạn: {log.suppressed}")
        log.close()
        reader.close()
        print(f"Đã ghi {log.path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
