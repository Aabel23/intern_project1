import io
import json
import socket
import threading
import unittest
from unittest.mock import patch

from machine.pairing.bluetooth_pairing import (
    handle_connection,
    receive_message,
)


class PairBluetoothTest(unittest.TestCase):
    def exchange(self, request, ack):
        machine, app = socket.socketpair()
        results = []
        worker = threading.Thread(target=lambda: results.append(handle_connection(machine)))
        worker.start()
        try:
            with app:
                app.settimeout(3)
                with app.makefile("rb") as reader:
                    # Socket là luồng byte: request có thể đến thành nhiều phần.
                    app.sendall(request[:5])
                    app.sendall(request[5:])
                    ready = json.loads(reader.readline())
                    payload = None
                    if ready.get("ok") is True:
                        payload = json.loads(reader.readline())
                        app.sendall(ack)
                    self.assertEqual(reader.read(1), b"")
        finally:
            worker.join(timeout=3)
        self.assertFalse(worker.is_alive())
        return results, ready, payload

    @patch("machine.pairing.bluetooth_pairing.get_product_key", return_value="test-key")
    @patch("machine.pairing.bluetooth_pairing.get_machine_name", return_value="FlexMix-Test")
    def test_complete_pairing(self, *_):
        results, ready, payload = self.exchange(
            b'{"type":"identify"}\n', b'{"type":"ack","ok":true}\n'
        )
        self.assertEqual(results, [True])
        self.assertEqual(ready, {"type": "ready", "ok": True})
        self.assertEqual(payload, {
            "type": "pairing", "machine_name": "FlexMix-Test", "product_key": "test-key"
        })

    def test_wrong_request_does_not_receive_key(self):
        results, ready, payload = self.exchange(b'{"type":"other"}\n', b"")
        self.assertEqual(results, [False])
        self.assertEqual(ready, {"ok": False})
        self.assertIsNone(payload)

    def test_app_rejects_packet(self):
        results, ready, payload = self.exchange(
            b'{"type":"identify"}\n', b'{"type":"ack","ok":false}\n'
        )
        self.assertEqual(results, [False])

    def test_invalid_messages(self):
        for body in (b"", b"{}", b"[]\n", b"bad\n", b"x" * 4097):
            with self.subTest(body_length=len(body)):
                with self.assertRaises(ValueError):
                    receive_message(io.BytesIO(body))


if __name__ == "__main__":
    unittest.main()
