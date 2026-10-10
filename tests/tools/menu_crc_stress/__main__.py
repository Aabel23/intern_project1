"""Chạy: python3 -m tests.tools.menu_crc_stress [--iterations N] [--seed S] [--json PATH]"""

import argparse
import json
import sys

from .harness import Harness
from .scenario import run


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Stress CRC menu máy pha chế (quyền manager).")
    ap.add_argument("--iterations", type=int, default=300, help="số vòng đổi menu (mặc định 300)")
    ap.add_argument("--seed", type=int, default=42, help="seed ngẫu nhiên (mặc định 42)")
    ap.add_argument("--json", metavar="PATH", help="ghi thống kê ra file JSON")
    args = ap.parse_args(argv)
    with Harness() as h:
        stats = run(h, iterations=args.iterations, seed=args.seed)
    print(stats.report())
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(stats.to_dict(), f, ensure_ascii=False, indent=2)
    return 0 if stats.ok() else 1


if __name__ == "__main__":
    sys.exit(main())
