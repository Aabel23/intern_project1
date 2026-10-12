"""Nối transport GATT với ClaimSession: một thiết bị, một phiên, một mảnh indication đang chờ xác nhận."""

from machine.pairing.claim_session import SessionClosed
from machine.pairing.framing import FramingError, Reassembler, fragments


class ClaimLink:
    """Nối GATT với ClaimSession: một thiết bị, một phiên, một gói đang gửi."""

    def __init__(self, new_session):
        self.new_session = new_session
        self.device = None
        self.session = None
        self.reassembler = Reassembler()
        self.outbox = []
        self.mtu = 23
        self.closing = False
        self.tx = None

    def subscribed(self):
        if self.session is not None:
            return
        self.session = self.new_session()
        self.reassembler.clear()
        self._send(self.session.hello_packet)

    def receive(self, device, chunk, mtu):
        if self.session is None:
            return False
        if self.device is None:
            # Khóa phiên vào thiết bị viết đầu tiên; thiết bị khác bị từ chối.
            self.device, self.mtu = device, mtu
        elif device != self.device:
            return False
        if self.closing:
            return False
        try:
            packets = self.reassembler.feed(chunk)
        except FramingError:
            self.reset()
            return False
        for packet in packets:
            try:
                self._send(self.session.handle(packet))
            except SessionClosed as closed:
                if closed.response is not None:
                    self._send(closed.response)
                self.closing = True
        if self.closing and not self.outbox:
            self.reset()
        return True

    def _send(self, packet):
        idle = not self.outbox
        self.outbox.extend(fragments(packet, self.mtu))
        if idle:
            self.tx.indicate(self.outbox[0])

    def confirmed(self):
        if self.outbox:
            self.outbox.pop(0)
        if self.outbox:
            self.tx.indicate(self.outbox[0])
        elif self.closing:
            self.reset()

    def disconnected(self):
        self.reset()

    def reset(self):
        if self.session is not None:
            self.session.close()
        self.device, self.session, self.outbox, self.closing = None, None, [], False
        self.reassembler.clear()
