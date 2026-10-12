"""Framing, GATT link pacing at MTU 23, and the NetworkManager keyfile Wi-Fi step (no radio needed)."""
from pathlib import Path
import stat
import sys
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "version1.1"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from bt_app_peer import AppPeer
from machine.config import identity as machine_identity
from machine.pairing.claim_link import ClaimLink
from machine.pairing.claim_session import ClaimSession
from machine.pairing.framing import FramingError, Reassembler, fragments
from machine.pairing.wifi_setup import configure_wifi


class FramingTests(unittest.TestCase):
    def test_roundtrip_any_split_and_leftover(self):
        packets = [b"a" * 1, b"b" * 300, b"c" * 8192]
        stream = b"".join(b"".join(fragments(p, 23)) for p in packets)
        for step in (1, 7, 20, 517):
            r = Reassembler(clock=lambda: 0)
            out = []
            for i in range(0, len(stream), step):
                out += r.feed(stream[i:i + step])
            self.assertEqual(out, packets)

    def test_limits_and_timeout(self):
        with self.assertRaises(FramingError): fragments(b"", 23)
        with self.assertRaises(FramingError): fragments(b"x" * 8193, 23)
        with self.assertRaises(FramingError): Reassembler().feed((8193).to_bytes(4, "big"))
        clock = [0]
        r = Reassembler(clock=lambda: clock[0])
        r.feed(b"\x00\x00\x00\x10abc")
        clock[0] = 10.5
        with self.assertRaises(FramingError): r.feed(b"d")


class FakeTx:
    def __init__(self): self.sent = []
    def indicate(self, chunk): self.sent.append(chunk)


class LinkTests(unittest.TestCase):
    def test_full_session_over_mtu23_with_confirm_pacing(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        ident = machine_identity.provision(tmp.name, "00000000abcdef01")
        seal = machine_identity.load_seal_code(tmp.name)
        link = ClaimLink(lambda: ClaimSession(ident, seal, b"\x04" + b"\x00" * 64, lambda s, p: {"ok": True},
                                              lambda: (str(uuid.uuid4()), True)))
        link.tx = FakeTx()
        app = AppPeer(ident.serial, seal)
        inbox = Reassembler()

        def drain():
            packets = []
            while link.outbox:
                # Only one fragment is indicated until the phone confirms it.
                self.assertEqual(link.tx.sent[-1], link.outbox[0])
                packets += inbox.feed(link.outbox[0])
                link.confirmed()
            return packets

        link.subscribed()
        hello, = drain()
        app.accept_hello(hello)
        for chunk in fragments(app.request("probe"), 23):
            self.assertTrue(link.receive("phone-1", chunk, 23))
        self.assertFalse(link.receive("phone-2", b"x", 23))
        reply, = drain()
        self.assertEqual(app.response(reply)["type"], "authenticated")


class WifiTests(unittest.TestCase):
    def test_keyfile_private_and_cleanup_on_failure(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        calls = []

        class Result:
            def __init__(self, code): self.returncode = code

        def runner(*args, timeout=15):
            calls.append(args)
            if args[0] == "connection" and args[1] == "load":
                path = Path(args[2])
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
                self.assertIn("psk=pass-word", path.read_text())
            return Result(0 if "load" in args or ok[0] else 4)

        ok = [True]
        self.assertEqual(configure_wifi("Cafe", "pass-word", runner=runner, keyfile_dir=tmp.name), {"ok": True})
        self.assertTrue(all("pass-word" not in " ".join(c) for c in calls))
        ok[0] = False
        self.assertEqual(configure_wifi("Cafe", "pass-word", runner=runner, keyfile_dir=tmp.name), {"ok": False})
        self.assertEqual(len(list(Path(tmp.name).iterdir())), 1)
        self.assertEqual(calls[-1][:2], ("connection", "delete"))


if __name__ == "__main__":
    unittest.main()
