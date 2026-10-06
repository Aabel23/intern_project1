"""Chạy toàn bộ server từ sandbox: python tests/server_module/run_modules.py --port 8001."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from server.config.config import SERVER_HOST, SERVER_PORT  # noqa: E402
from server.main import create_server  # noqa: E402


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Chạy toàn bộ module server.")
    parser.add_argument("--port", type=int, default=SERVER_PORT)
    args = parser.parse_args()
    with create_server((SERVER_HOST, args.port)) as server:
        print(f"Server: http://{SERVER_HOST}:{server.server_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
