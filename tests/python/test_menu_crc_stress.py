"""Chạy: python -m unittest tests.python.test_menu_crc_stress

Bản rút gọn của tests/tools/menu_crc_stress: ~40 vòng đổi menu qua server + vòng lặp máy thật,
CRC luồng thật phải khớp oracle tự tính, cuối cùng khôi phục menu gốc.
"""

import unittest

from tests.tools.menu_crc_stress.harness import Harness
from tests.tools.menu_crc_stress.scenario import run


class MenuCrcStressTest(unittest.TestCase):
    def test_stress_40_vong(self):
        with Harness() as harness:
            stats = run(harness, iterations=40, seed=42, log=lambda *a, **k: None)
        self.assertTrue(stats.ok(), stats.report())


if __name__ == "__main__":
    unittest.main()
