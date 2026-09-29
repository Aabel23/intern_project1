"""Repeat the existing suites until a timezone-aware deadline, with per-batch logs."""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "tests" / "runs"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--until", required=True, type=datetime.fromisoformat)
    parser.add_argument("--interval", type=int, default=60)
    args = parser.parse_args()
    if args.until.tzinfo is None or args.interval < 1:
        parser.error("--until must include a timezone; --interval must be positive")
    RUNS.mkdir(parents=True, exist_ok=True)
    lock = RUNS / "night_loop.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        parser.error("Another runner owns tests/runs/night_loop.lock; inspect it before restarting")
    with os.fdopen(fd, "w") as stream:
        stream.write(str(os.getpid()))
    folder = RUNS / datetime.now().strftime("%Y%m%d-%H%M%S")
    folder.mkdir()
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    iteration = 0
    try:
        while datetime.now(args.until.tzinfo) < args.until:
            if (RUNS / "claude.takeover").exists():
                print("Claude takeover requested; releasing runner and phone", flush=True)
                break
            remaining = (args.until - datetime.now(args.until.tzinfo)).total_seconds()
            # Leave time for E2E teardown; near the deadline use the shorter suites.
            if remaining < 180:
                time.sleep(min(remaining, 30))
                continue
            iteration += 1
            flows = "all" if remaining >= 1500 else "py,app"
            cmd = [sys.executable, str(ROOT / "tests" / "run_tests.py"), "--flows", flows,
                   "--note", f"overnight round {iteration}"]
            started = datetime.now(args.until.tzinfo)
            output = folder / f"round-{iteration:03d}.log"
            with output.open("w", encoding="utf-8") as log:
                process = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
                try:
                    code = process.wait(timeout=min(remaining, 1200))
                except subprocess.TimeoutExpired:
                    # Only stop the process tree created by this batch.
                    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                   capture_output=True, timeout=30)
                    code = -1
            result = {"round": iteration, "started": started.isoformat(), "flows": flows,
                      "exit_code": code, "log": str(output.relative_to(ROOT))}
            with (folder / "results.jsonl").open("a", encoding="utf-8") as log:
                log.write(json.dumps(result, ensure_ascii=False) + "\n")
            print(json.dumps(result, ensure_ascii=False), flush=True)
            remaining = (args.until - datetime.now(args.until.tzinfo)).total_seconds()
            if remaining > 0:
                time.sleep(min(args.interval, remaining))
    finally:
        lock.unlink(missing_ok=True)
        (folder / "finished.txt").write_text(datetime.now().isoformat(), encoding="utf-8")


if __name__ == "__main__":
    main()
