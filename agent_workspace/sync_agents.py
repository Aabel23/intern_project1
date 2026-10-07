"""Đăng ký vai của agent_workspace với Claude Code mà không nhân đôi nguồn chỉnh sửa."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "agent_workspace" / "agents"
TARGET = ROOT / ".claude" / "agents"
NAMES = ("architect", "planner", "coder", "tester", "reviewer", "cybersecurity")


def main() -> int:
    check = sys.argv[1:] == ["--check"]
    if sys.argv[1:] and not check:
        print("Usage: python agent_workspace/sync_agents.py [--check]")
        return 2
    if not check:
        TARGET.mkdir(parents=True, exist_ok=True)
    mismatches = []
    for name in NAMES:
        source = SOURCE / f"{name}.md"
        target = TARGET / source.name
        content = source.read_bytes()
        parts = content.decode("utf-8").split("---", 2)
        if len(parts) != 3 or f"name: {name}" not in parts[1] or "description:" not in parts[1]:
            print(f"Invalid agent frontmatter: {source}")
            return 2
        if not target.is_file() or target.read_bytes() != content:
            mismatches.append(name)
            if not check:
                target.write_bytes(content)
    if mismatches:
        print(("Out of sync: " if check else "Synced: ") + ", ".join(mismatches))
    else:
        print("Agents are in sync.")
    return int(check and bool(mismatches))


if __name__ == "__main__":
    raise SystemExit(main())
