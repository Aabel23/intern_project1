"""Kiểm cấu hình agent mà không đọc bí mật hay kết nối máy bán hàng.

VÌ SAO CÓ TEST NÀY
    Thiếu ID phải dừng rõ ràng; mặc định sang máy 1 có thể gán nhầm server.

CÁCH CHẠY
    python3 -m unittest agent.tests.test_config -v
"""

import tempfile
import unittest
from pathlib import Path

from agent.config import load_config


class ConfigTest(unittest.TestCase):
    def test_requires_explicit_identity_and_pinned_ca(self):
        with tempfile.TemporaryDirectory() as directory:
            ca = Path(directory) / "ca.crt"
            ca.write_text("placeholder")
            base = {"FLEXMIX_AGENT_URL": "https://hub.example:8443",
                    "FLEXMIX_AGENT_CA": str(ca)}
            with self.assertRaises(ValueError):
                load_config(base)
            self.assertEqual(load_config({**base, "QRPROTO_MACHINE_ID": "7"}).machine_id, 7)


if __name__ == "__main__":
    unittest.main()
