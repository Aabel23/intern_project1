"""Update and validate the evidence-backed progress for the first-customer roadmap."""

import argparse
import json
from datetime import datetime
from pathlib import Path


HERE = Path(__file__).resolve().parent
PLAN = HERE.parent / "plan.json"
PROGRESS = HERE / "roadmap-progress.json"
GATE_PHASES = {
    "G0": (0,),
    "G1": (1, 2),
    "G2": (3, 4),
    "G3": (5, 6),
    "G4": (7,),
}
STATUSES = {"todo", "doing", "review", "done", "blocked"}


def roadmap_ids():
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    if plan.get("version") != 1:
        raise ValueError("plan.json sai phiên bản")
    phases = next((section.get("phases") for section in plan.get("sections", []) if section.get("id") == "chi-tiet"), None)
    if not isinstance(phases, list):
        raise ValueError("plan.json thiếu danh sách phase")
    ids = [step["id"] for phase in phases for step in phase["steps"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Roadmap có ID bước trùng nhau")
    return ids


def load():
    return json.loads(PROGRESS.read_text(encoding="utf-8"))


def save(data):
    PROGRESS.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate(data):
    ids = roadmap_ids()
    if data.get("version") != 1 or not isinstance(data.get("steps"), dict):
        raise ValueError("Sổ tiến độ sai phiên bản/cấu trúc")
    if set(data["steps"]) != set(ids):
        raise ValueError(f"ID lệch roadmap: thiếu {sorted(set(ids) - set(data['steps']))}; thừa {sorted(set(data['steps']) - set(ids))}")
    if set(data.get("gates", {})) != set(GATE_PHASES):
        raise ValueError("Danh sách cổng G0–G4 không đầy đủ")
    for step_id, row in data["steps"].items():
        status = row.get("status")
        if status not in STATUSES:
            raise ValueError(f"{step_id}: trạng thái không hợp lệ")
        if status != "todo" and (not row.get("owner") or not row.get("updated")):
            raise ValueError(f"{step_id}: thiếu người phụ trách hoặc ngày")
        if status in {"review", "done"} and not row.get("evidence"):
            raise ValueError(f"{step_id}: chờ kiểm/đạt phải có bằng chứng")
        if status == "done" and not row.get("reviewer"):
            raise ValueError(f"{step_id}: đạt phải có người kiểm")
        if status == "done" and row["reviewer"].casefold() == row["owner"].casefold():
            raise ValueError(f"{step_id}: người thực hiện không tự kiểm bước của mình")
        if status == "blocked" and not row.get("note"):
            raise ValueError(f"{step_id}: bị chặn phải ghi nguyên nhân")
    for gate, row in data["gates"].items():
        if row.get("approved"):
            required = [step_id for step_id in ids if int(step_id.split(".")[0]) in GATE_PHASES[gate]]
            if any(data["steps"][step_id]["status"] != "done" for step_id in required):
                raise ValueError(f"{gate}: chưa thể qua khi bước bắt buộc chưa đạt")
            if not row.get("reviewer") or not row.get("evidence") or not row.get("updated"):
                raise ValueError(f"{gate}: thiếu người duyệt, ngày hoặc bằng chứng")
    return len(ids)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="Kiểm sổ và đối chiếu ID trong plan.json")

    step = commands.add_parser("step", help="Cập nhật một bước")
    step.add_argument("id", help="Ví dụ: 1.2")
    step.add_argument("status", choices=sorted(STATUSES))
    step.add_argument("--by", help="Agent/người thực hiện")
    step.add_argument("--evidence", help="Đường dẫn biên bản, commit hoặc kết quả kiểm")
    step.add_argument("--reviewer", help="Người xác nhận bước đạt")
    step.add_argument("--note", help="Vướng mắc hoặc ghi chú ngắn")

    gate = commands.add_parser("gate", help="Duyệt một cổng sau khi user đã chốt")
    gate.add_argument("id", choices=list(GATE_PHASES))
    gate.add_argument("--by", required=True, help="Người duyệt")
    gate.add_argument("--evidence", required=True, help="Biên bản/quyết định duyệt cổng")

    args = parser.parse_args()
    data = load()
    validate(data)
    if args.command == "check":
        print(f"OK: {len(data['steps'])} bước khớp roadmap; dữ liệu và cổng hợp lệ")
        return

    today = datetime.now().astimezone().date().isoformat()
    if args.command == "step":
        if args.id not in data["steps"]:
            parser.error(f"Không có bước {args.id}")
        if args.status != "todo" and not args.by:
            parser.error("Bước đang làm/chờ kiểm/đạt/bị chặn cần --by")
        old = data["steps"][args.id]
        row = {**old, "status": args.status, "owner": args.by or old["owner"], "updated": today}
        if args.evidence is not None:
            row["evidence"] = args.evidence
        if args.reviewer is not None:
            row["reviewer"] = args.reviewer
        if args.note is not None:
            row["note"] = args.note
        data["steps"][args.id] = row
        if args.status != "done":
            phase = int(args.id.split(".")[0])
            for gate_id, phases in GATE_PHASES.items():
                if phase in phases:
                    data["gates"][gate_id]["approved"] = False
    else:
        required = [step_id for step_id in roadmap_ids() if int(step_id.split(".")[0]) in GATE_PHASES[args.id]]
        if any(data["steps"][step_id]["status"] != "done" for step_id in required):
            parser.error(f"{args.id} còn bước chưa đạt")
        data["gates"][args.id] = {
            "approved": True,
            "reviewer": args.by,
            "updated": today,
            "evidence": args.evidence,
        }
    validate(data)
    save(data)
    print(f"Đã cập nhật {args.id}; sổ tiến độ hợp lệ")


if __name__ == "__main__":
    main()
