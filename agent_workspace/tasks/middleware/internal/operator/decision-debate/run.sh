#!/usr/bin/env bash
# Vòng tranh luận researcher/critic bằng Codex GPT Sol high cho decision-options-2026-10-07.md.
set -u
ROOT=/home/abel/project/internproj/intern_project1
DIR=$ROOT/agent_workspace/tasks/middleware/internal/operator/decision-debate
DO=agent_workspace/tasks/middleware/internal/operator/decision-options-2026-10-07.md
C=/usr/lib/chatgpt/resources/codex
RUN=(--search exec -m gpt-6-sol -c model_reasoning_effort=high -C "$ROOT" --skip-git-repo-check)

RULE="YÊU CẦU CAO NHẤT CỦA NGƯỜI DÙNG: tinh gọn, nhẹ, đơn giản. Phương án phải cài thêm nhiều phần mềm/dịch vụ/phần cứng chỉ để chạy lẻ một chức năng là KHÔNG đáng; ưu tiên dùng cái đã có (Python stdlib, thư viện Flutter/Dart sẵn, cấu hình OS sẵn). Nhóm nhỏ/intern. Mỗi phương án phải ghi rõ 'cần cài thêm gì' (số lượng và tên). Người dùng đã chốt HTTP/1.1."
CTX="Repo FlexMix: app Flutter Android (app/flutter_app), server Python tự viết HTTP/1.1 + SQLite một process (server/), máy pha chế chạy Python (machine/). Thiết kế bảo vệ gói tin R5 đề xuất ở agent_workspace/tasks/middleware/internal/packet-security/design.md (D), keys.md. Đọc AGENTS.md. Quyết định cần 4 phương án: D1 root/manifest, D2 nguồn thời gian, D3 enrollment máy, D4 khôi phục mất khóa, D5 topology proxy, D6 thứ tự rollout, D8 định danh máy/GET trạng thái. Người dùng sẽ chọn 1 trong 4 mỗi quyết định. Viết tiếng Việt, không bịa số đo/phiên bản/khả năng thư viện; chưa kiểm thì ghi 'chưa kiểm'."

for N in 2 3 4; do
  P=$((N-1))
  "$C" "${RUN[@]}" -s workspace-write -o "$DIR/researcher-r$N.md" \
"Bạn là RESEARCHER (vòng $N). $CTX
$RULE
Đọc $DO và phản biện mới nhất agent_workspace/tasks/middleware/internal/operator/decision-debate/critique-r$P.md. Nghiên cứu thêm (repo + web nguồn uy tín) và SỬA $DO: thay toàn bộ mục 'Bản chốt' (tạo nếu chưa có, đặt ngay sau tiêu đề file) bằng bản sạch: mỗi quyết định mở bằng 3 dòng lời thường (quyết định là gì, chọn sai thì sao, câu hỏi chặn nếu có), rồi đúng 4 phương án khác nhau thực chất, loại trừ nhau, mỗi phương án: mô tả 2–3 dòng, cần cài thêm gì, ưu, nhược, công sức (thấp/vừa/cao), nguồn; cuối mỗi quyết định: khuyến nghị + tiêu chí chọn. Cuối bản chốt: phụ thuộc chéo. Giữ các vòng cũ phía dưới làm lịch sử; thêm mục 'Thay đổi vòng $N' ghi đã nhận/không nhận ý nào và vì sao. Chỉ sửa file $DO, không sửa file khác. Trả lời cuối: tóm tắt ≤200 từ."
  [ -s "$DIR/researcher-r$N.md" ] || { echo "researcher r$N lỗi, dừng"; exit 1; }
  "$C" "${RUN[@]}" -s read-only -o "$DIR/critique-r$N.md" \
"Bạn là CRITIC độc lập (vòng $N). $CTX
$RULE
Chỉ đọc, không sửa file. Phản biện mục 'Bản chốt' trong $DO (đối chiếu repo, design.md và nguồn web). Kiểm lại các mục ở agent_workspace/tasks/middleware/internal/operator/decision-debate/critique-r$P.md đã được xử lý chưa. Tìm: sai sự thật/nguồn, phương án trùng hoặc không loại trừ nhau, phương án nặng nề trái yêu cầu tinh gọn trong khi có phương án nhẹ hơn tương đương, thiếu phương án rõ ràng tốt hơn, vi phạm design.md không nói rõ, khuyến nghị sai, phụ thuộc chéo thiếu, khó đọc. Mỗi mục: mức [CHẶN]/[NÊN SỬA]/[GỢI Ý], bằng chứng, đề xuất sửa. Dòng cuối cùng phải là đúng một trong hai: 'VERDICT: ĐẠT' (không còn [CHẶN]) hoặc 'VERDICT: CHẶN'."
  [ -s "$DIR/critique-r$N.md" ] || { echo "critic r$N lỗi, dừng"; exit 1; }
  if tail -n 3 "$DIR/critique-r$N.md" | grep -q "VERDICT: ĐẠT"; then echo "DONE round $N: ĐẠT"; exit 0; fi
  echo "round $N: còn CHẶN"
done
echo "Hết 3 vòng, vẫn còn CHẶN"
