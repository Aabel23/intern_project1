"""Khung gói BLE: F(P)=u32be(len)||P, 1..8192 byte, phân mảnh theo MTU-3 (bt-claim.md)."""

import struct
import time

MAX_PACKET = 8192
PACKET_TIMEOUT = 10.0


class FramingError(Exception):
    pass


def fragments(packet, mtu):
    if not 0 < len(packet) <= MAX_PACKET:
        raise FramingError("size")
    data = struct.pack(">I", len(packet)) + packet
    size = max(20, min(mtu - 3, 512))
    return [data[i:i + size] for i in range(0, len(data), size)]


class Reassembler:
    """Gom mảnh thành gói; hết 10 s kể từ byte đầu của gói mà chưa đủ thì lỗi (không gia hạn theo mảnh chậm)."""

    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.buffer = b""
        self.started = None

    def feed(self, chunk):
        now = self.clock()
        if self.buffer and now - self.started > PACKET_TIMEOUT:
            raise FramingError("timeout")
        if not self.buffer and chunk:
            self.started = now
        self.buffer += chunk
        packets = []
        while len(self.buffer) >= 4:
            length = struct.unpack(">I", self.buffer[:4])[0]
            if not 0 < length <= MAX_PACKET:
                raise FramingError("length")
            if len(self.buffer) < 4 + length:
                break
            packets.append(self.buffer[4:4 + length])
            self.buffer = self.buffer[4 + length:]
            self.started = now if self.buffer else None
        return packets

    def clear(self):
        self.buffer, self.started = b"", None
