"""Hai agent tranh luận một đề bài; chỉ giữ kết quả cuối, không lưu lượt trao đổi.

    python agent_workspace/debate.py <đề_bài.md> -o <kết_quả.md> [--a codex] [--b claude] [--rounds 3]

Hai bên đề xuất độc lập, rồi phản biện nhau tới khi cả hai ghi VERDICT: ĐỒNG Ý
hoặc hết số vòng; bên A hợp nhất kết quả theo mẫu RESULT. Lượt trao đổi chỉ nằm
trong RAM; file tạm của CLI bị xóa trong finally, kể cả khi lỗi. Agent chỉ đọc
repo và chạy không lưu phiên (claude --no-session-persistence, codex --ephemeral).
"""

import argparse
import datetime
import glob
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
TIMEOUT_SECONDS = 30 * 60
AGREE = "VERDICT: ĐỒNG Ý"
BLOCK = "VERDICT: CHẶN"

RULES = """Làm việc bằng tiếng Việt trong repo FlexMix (cwd). Đọc AGENTS.md và nguồn liên quan.
Chỉ đọc, không sửa file. Dẫn file:dòng hoặc nguồn web cho mỗi nhận định quan trọng.
Không bịa số đo, phiên bản hay khả năng thư viện; chưa kiểm thì ghi "chưa kiểm".
Ưu tiên phương án tinh gọn, dùng cái đã có; ghi rõ cần cài thêm gì."""

RESULT = """# Kết quả tranh luận: <tiêu đề ngắn>

## Câu hỏi
<1–3 dòng>

## Kết luận
<khuyến nghị cuối, 3–8 dòng>

## Lý do chính
- <lý do, kèm nguồn>

## Phương án đã loại
- <phương án>: <lý do loại, 1 dòng>

## Bất đồng còn lại và điều user cần chốt
- <hoặc "Không có">

## Giả định và phép kiểm chưa làm
- <hoặc "Không có">"""


def codex_bin():
    found = os.environ.get("CODEX_BIN") or shutil.which("codex")
    if found:
        return found
    bundled = sorted(glob.glob(os.path.expanduser("~/.vscode/extensions/openai.chatgpt-*/bin/linux-x86_64/codex")))
    if not bundled:
        raise RuntimeError("Không tìm thấy codex; đặt biến CODEX_BIN")
    return bundled[-1]


def ask(engine, prompt, workdir):
    """Câu trả lời cuối của một agent chỉ đọc; không ghi phiên hay log ra đĩa."""
    if engine == "claude":
        command = ["claude", "-p", "--model", "opus", "--no-session-persistence",
                   "--allowedTools", "Read,Glob,Grep,WebSearch,WebFetch", "--output-format", "text"]
        result = subprocess.run(command, input=prompt, capture_output=True, text=True,
                                cwd=ROOT, timeout=TIMEOUT_SECONDS)
        answer = result.stdout
    else:
        answer_file = Path(workdir) / "answer.md"
        command = [codex_bin(), "exec", "--ephemeral", "-s", "read-only", "-C", str(ROOT),
                   "--skip-git-repo-check", "--color", "never", "-o", str(answer_file), "-"]
        result = subprocess.run(command, input=prompt, capture_output=True, text=True,
                                timeout=TIMEOUT_SECONDS)
        answer = answer_file.read_text(encoding="utf-8") if answer_file.exists() else ""
        answer_file.unlink(missing_ok=True)
    # Không đưa stderr vào lỗi: nó có thể chứa nội dung trao đổi.
    if result.returncode != 0 or not answer.strip():
        raise RuntimeError(f"{engine} không trả lời được (exit {result.returncode})")
    return answer.strip()


def agrees(position):
    return position.splitlines()[-1].strip() == AGREE


def debate(topic, engines, rounds, workdir):
    """(kết quả hợp nhất, đã đồng thuận, số vòng phản biện đã chạy)."""
    brief = f"{RULES}\n\nĐỀ BÀI:\n{topic}"
    # 1. Mỗi bên đề xuất độc lập, chưa thấy bên kia.
    positions = {
        side: ask(engine, f"{brief}\n\nBạn là bên {side}. Đưa đề xuất độc lập: phương án, đánh đổi, "
                          "phản ví dụ đã cân nhắc, giả định và cách kiểm.", workdir)
        for side, engine in engines.items()
    }
    # 2. Phản biện chéo; cả hai đồng ý thì dừng sớm.
    done = 0
    for done in range(1, rounds + 1):
        positions = {
            side: ask(engine, f"{brief}\n\nBạn là bên {side}, vòng phản biện {done}/{rounds}.\n\n"
                              f"LẬP TRƯỜNG CỦA BẠN:\n{positions[side]}\n\n"
                              f"LẬP TRƯỜNG BÊN KIA:\n{positions[other]}\n\n"
                              "Tìm sai sự thật, phản ví dụ, thiếu sót, phương án nặng hơn cần thiết. "
                              "Nhận điểm bên kia đúng và sửa lập trường. Viết lại lập trường đầy đủ, ngắn gọn. "
                              f"Dòng cuối đúng một trong hai: '{AGREE}' nếu không còn bất đồng chặn, "
                              f"hoặc '{BLOCK}'.", workdir)
            for (side, engine), other in zip(engines.items(), ("B", "A"))
        }
        if all(map(agrees, positions.values())):
            break
    agreed = all(map(agrees, positions.values()))
    # 3. Bên A hợp nhất; chỉ bản này được ghi ra file.
    final = ask(engines["A"], f"{brief}\n\nHợp nhất kết quả cuối từ hai lập trường dưới đây. "
                              "Bất đồng chưa giải quyết ghi nguyên vào mục 'Bất đồng còn lại'. "
                              f"Chỉ trả về Markdown theo đúng mẫu:\n\n{RESULT}\n\n"
                              f"BÊN A:\n{positions['A']}\n\nBÊN B:\n{positions['B']}", workdir)
    return final, agreed, done


def main():
    parser = argparse.ArgumentParser(description="Tranh luận hai agent, chỉ ghi kết quả cuối.")
    parser.add_argument("topic", type=Path, help="Markdown: câu hỏi, bối cảnh, ràng buộc, file cần đọc")
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--a", choices=("codex", "claude"), default="codex")
    parser.add_argument("--b", choices=("codex", "claude"), default="claude")
    parser.add_argument("--rounds", type=int, default=3)
    args = parser.parse_args()
    topic = args.topic.read_text(encoding="utf-8")
    stamp = datetime.date.today().isoformat()
    workdir = tempfile.mkdtemp(prefix="debate-")
    try:
        final, agreed, done = debate(topic, {"A": args.a, "B": args.b}, args.rounds, workdir)
        status = "ĐỒNG THUẬN" if agreed else "CÒN BẤT ĐỒNG"
        text = f"{final}\n\n---\n{status} sau {done} vòng phản biện · A={args.a} · B={args.b} · {stamp}.\n"
        code = 0
    except (RuntimeError, OSError, subprocess.SubprocessError) as error:
        text = f"# Kết quả tranh luận: LỖI\n\n{error}\n\nKhông có kết quả hợp nhất · {stamp}.\n"
        code = 1
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text + "Lượt trao đổi không được lưu.\n", encoding="utf-8")
    print(f"{'Xong' if code == 0 else 'Lỗi'}: {args.output}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
