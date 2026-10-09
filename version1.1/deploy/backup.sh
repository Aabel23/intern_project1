#!/usr/bin/env bash
#
# Sao lưu toàn bộ thứ không lấy lại được của một máy FlexMix.
#
#     ./deploy/backup.sh                      # ghi vào ~/flexmix-backup
#     ./deploy/backup.sh --to /media/usb/bk   # ghi vào chỗ khác
#     FLEXMIX_BACKUP_DIR=/media/usb/bk ./deploy/backup.sh
#
# KHÔNG CẦN SUDO. Ba thứ cần sao lưu đều đọc được bằng tài khoản chạy máy:
# mật khẩu MySQL nằm trong /etc/flexmix/qrproto.env (đã cấp quyền đọc),
# /var/lib/flexmix/ do chính user sở hữu, recipe/ nằm trong thư mục dự án.
# Khôi phục thì CẦN sudo — ghi vào /etc và /var khác với đọc từ đó.
#
# ============================================================
# SAO LƯU CÁI GÌ, VÀ VÌ SAO ĐÚNG NHỮNG THỨ NÀY
# ============================================================
#
#   MySQL beveragepos       Không lấy lại được. Vé, công thức, giá, tồn kho,
#                           tài khoản — toàn bộ lịch sử buôn bán.
#
#   /etc/flexmix/qrproto.env  File nhỏ nhất và nguy hiểm nhất. Sinh khoá QR
#                           mới làm HỎNG VĨNH VIỄN mọi nhãn đã in mà chưa
#                           quét. Mất file này là mất luôn khả năng khôi
#                           phục liền mạch — xem README, mục Configuration.
#
#   /etc/flexmix/machine_profile.json
#                           Chỉ có trên máy đi dây khác máy #1 — xem
#                           configuration/machine.py. Mất file này thì máy
#                           khôi phục xong chạy với dây của máy #1: bơm sai,
#                           không lỗi nào báo. Không có file thì bỏ qua.
#
#   /var/lib/flexmix/       Hiệu chuẩn bơm và loadcell. Lấy lại được, nhưng
#                           phải hiệu chuẩn tay nhiều giờ với một cái cân.
#
#   recipe/                 Ảnh món và phim hướng dẫn admin tự upload. Chỉ
#                           lấy lại được nếu ai đó còn giữ file gốc.
#
# KHÔNG sao lưu: mã nguồn (đã ở git), .venv (dựng lại được), log.
#
# ============================================================
# KHÔI PHỤC
# ============================================================
#
# Đủ các bước — kể cả khôi phục sang máy thay thế, nơi THỨ TỰ quyết định
# khoá QR còn hay mất — nằm ở README.md, mục "Backup and restore". Bản ngắn,
# trên chính máy này:
#
#     sudo systemctl stop flexmix-backend
#     CNF=$(mktemp); chmod 600 "$CNF"
#     printf '[client]\nuser=%s\npassword=%s\n' \
#       "$(sed -n 's/^[[:space:]]*BEVERAGE_DB_USER=//p'     /etc/flexmix/qrproto.env | head -1)" \
#       "$(sed -n 's/^[[:space:]]*BEVERAGE_DB_PASSWORD=//p' /etc/flexmix/qrproto.env | head -1)" > "$CNF"
#     mysql --defaults-extra-file="$CNF" beveragepos < db_<ngày>.sql
#     rm -f "$CNF"
#     sudo tar xzf files_<ngày>.tar.gz -C / etc/flexmix var/lib/flexmix
#     tar xzf files_<ngày>.tar.gz -C <thư mục dự án> recipe
#     ./.venv/bin/python3 -m database.main update     # migration mới hơn bản sao lưu
#     sudo systemctl start flexmix-backend
#
# HAI lệnh tar, không phải một. recipe/ nằm trong gói theo đường dẫn tương
# đối với DỰ ÁN, không phải với /. Một lệnh `tar -C /` duy nhất bung ảnh ra
# /recipe — nơi không ai tìm tới — mà vẫn báo thành công.
#
# MỘT BẢN SAO LƯU CHƯA TỪNG KHÔI PHỤC LÀ MỘT PHỎNG ĐOÁN. Thử một lần vào
# database riêng rồi đối chiếu số vé, đừng đợi tới lúc thẻ SD chết.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="/etc/flexmix/qrproto.env"
DB_NAME="beveragepos"

# Giữ bao nhiêu bản. Ba là quy ước đã có trong docs/Kien_Truc_Doi_May.html.
KEEP=3

DEST="${FLEXMIX_BACKUP_DIR:-$HOME/flexmix-backup}"

while [ $# -gt 0 ]; do
    case "$1" in
        --to)   DEST="${2:?--to cần một đường dẫn}"; shift 2 ;;
        --keep) KEEP="${2:?--keep cần một con số}"; shift 2 ;;
        -h|--help)
            sed -n '2,10p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
            exit 0 ;;
        *) echo "Tham số lạ: $1" >&2; exit 2 ;;
    esac
done

c_ok()   { printf '  \033[32m✓\033[0m %s\n' "$*"; }
c_warn() { printf '  \033[33m!\033[0m %s\n' "$*"; }
c_err()  { printf '  \033[31m✗\033[0m %s\n' "$*" >&2; }
die()    { c_err "$*"; exit 1; }

printf '\n\033[1m== Sao lưu FlexMix ==\033[0m\n'

# ---------------------------------------------------------------- tiền kiểm --
[ -r "$ENV_FILE" ] || die "Không đọc được $ENV_FILE (cần nó để lấy mật khẩu MySQL)."
command -v mysqldump >/dev/null || die "Không có lệnh mysqldump."

mkdir -p "$DEST" || die "Không tạo được thư mục đích: $DEST"
[ -w "$DEST" ] || die "Không ghi được vào $DEST"

# CÙNG Ổ VỚI DỮ LIỆU THÌ NÓI THẲNG RA.
#
# Sao lưu nằm cùng thẻ SD chống được "tôi lỡ tay xoá" và "migration làm hỏng
# dữ liệu". Nó KHÔNG chống được thẻ chết — mà thẻ SD trên Pi hỏng là chuyện
# khi nào, không phải có hay không. Cảnh báo chứ không từ chối: một bản sao
# lưu cùng ổ vẫn hơn không có bản nào.
if [ "$(stat -c %d "$DEST")" = "$(stat -c %d /)" ]; then
    c_warn "$DEST nằm trên CÙNG Ổ với dữ liệu — không chống được thẻ SD chết."
    printf '      Chép ra ngoài sau khi xong, hoặc dùng --to /media/<usb>/...\n'
fi

STAMP="$(date +%Y%m%d_%H%M%S)"
DB_OUT="$DEST/db_$STAMP.sql"
FILES_OUT="$DEST/files_$STAMP.tar.gz"

# ------------------------------------------------------------------- MySQL --
#
# Mật khẩu đi qua file tạm mode 600, KHÔNG lên dòng lệnh: `mysqldump -pXXX`
# in mật khẩu ra `ps aux` cho mọi user trên máy đọc. Cùng kỹ thuật mà
# deploy/install.sh dùng ở mysql_run().
CNF="$(mktemp)"
chmod 600 "$CNF"
trap 'rm -f "$CNF" "$DB_OUT.part" "$FILES_OUT.part"' EXIT

{
    printf '[client]\n'
    printf 'user=%s\n'     "$(sed -n 's/^[[:space:]]*BEVERAGE_DB_USER=//p'     "$ENV_FILE" | head -1)"
    printf 'password=%s\n' "$(sed -n 's/^[[:space:]]*BEVERAGE_DB_PASSWORD=//p' "$ENV_FILE" | head -1)"
} > "$CNF"

# --single-transaction: cả 14 bảng đều InnoDB, nên đây là một bản chụp NHẤT
# QUÁN mà KHÔNG khoá bảng. Thiếu cờ này thì máy không bán được trong lúc
# dump chạy, và một máy pha chế không có giờ nào chắc chắn rảnh.
#
# Ghi ra .part rồi mới đổi tên: một file đứt giữa chừng mang đúng tên thật
# trông y hệt một bản sao lưu tốt, và người ta chỉ phát hiện ra lúc khôi
# phục — đúng lúc không còn đường lui.
mysqldump --defaults-extra-file="$CNF" \
          --single-transaction \
          "$DB_NAME" > "$DB_OUT.part" \
    || die "mysqldump thất bại — không có gì được ghi."

rm -f "$CNF"
mv "$DB_OUT.part" "$DB_OUT"
c_ok "database  → $(basename "$DB_OUT")  ($(du -h "$DB_OUT" | cut -f1))"

# -------------------------------------------------------------------- file --
#
# Liệt kê từng file trong /etc/flexmix, không gói cả thư mục: ở đó còn
# flexmix.env (0600, của root) mà tài khoản này không đọc được — tar sẽ
# hỏng vì một file không chỗ nào trong repo này dùng tới.
ETC_FILES=(etc/flexmix/qrproto.env)

if [ -f /etc/flexmix/machine_profile.json ]; then
    ETC_FILES+=(etc/flexmix/machine_profile.json)
fi

tar czf "$FILES_OUT.part" \
    -C /              "${ETC_FILES[@]}" var/lib/flexmix \
    -C "$PROJECT_DIR" recipe \
    2>/dev/null \
    || die "tar thất bại — không gói được phần file."

mv "$FILES_OUT.part" "$FILES_OUT"
c_ok "file      → $(basename "$FILES_OUT")  ($(du -h "$FILES_OUT" | cut -f1))"

trap - EXIT

# ------------------------------------------------------------------- kiểm --
#
# "Sao lưu không ai kiểm tra là một sao lưu chưa tồn tại"
#                                     -- docs/Kien_Truc_Doi_May.html
#
# mysqldump chỉ ghi dòng cuối này khi nó chạy XONG. Thiếu nó = dump đứt
# giữa chừng, và một file đứt giữa chừng trông y hệt file tốt nếu chỉ nhìn
# kích thước.
# KHÔNG dùng `| grep -q` ở đây. Với `set -o pipefail`, grep -q thoát ngay
# khi khớp, lệnh đầu ống nhận SIGPIPE, và cả pipeline bị tính là thất bại —
# câu kiểm báo hỏng cho một bản sao lưu hoàn toàn tốt. deploy/install.sh
# phase_hardware đã dính đúng cái bẫy này và ghi lại; đây là cùng một cách
# tránh: lấy dữ liệu ra biến rồi so khớp chuỗi.
DONG_CUOI="$(tail -1 "$DB_OUT")"
case "$DONG_CUOI" in
    "-- Dump completed"*) ;;
    *) die "Dump KHÔNG hoàn chỉnh (thiếu dòng '-- Dump completed'). Đừng tin file này." ;;
esac
c_ok "dump hoàn chỉnh"

DANH_SACH="$(tar tzf "$FILES_OUT" 2>/dev/null)" \
    || die "File .tar.gz hỏng, không đọc lại được."

for phai_co in etc/flexmix/qrproto.env var/lib/flexmix/pump_calib.json; do
    case $'\n'"$DANH_SACH"$'\n' in
        *$'\n'"$phai_co"$'\n'*) ;;
        *) die "Gói file thiếu $phai_co" ;;
    esac
done
c_ok "gói file đọc lại được, có đủ khoá QR và hiệu chuẩn"

# So với bản gần nhất trước đó. Một dump 2 KB sau một dump 160 KB là dấu
# hiệu hỏng mà mọi kiểm tra "file có tồn tại không" đều bỏ sót.
TRUOC="$(ls -1t "$DEST"/db_*.sql 2>/dev/null | sed -n 2p || true)"
if [ -n "$TRUOC" ]; then
    MOI=$(stat -c %s "$DB_OUT"); CU=$(stat -c %s "$TRUOC")
    if [ "$MOI" -lt $(( CU / 2 )) ]; then
        c_warn "bản này ($MOI byte) nhỏ hơn nửa bản trước ($CU byte) — kiểm lại"
    else
        c_ok "kích thước hợp lý so với bản trước"
    fi
fi

# ------------------------------------------------------- dọn bản cũ + mốc --
#
# Xoá theo CẶP và chỉ sau khi bản mới đã kiểm xong: xoá trước khi biết bản
# mới có tốt không là tự tay bỏ cái lưới an toàn cuối cùng.
XOA=0
for cu in $(ls -1t "$DEST"/db_*.sql 2>/dev/null | tail -n +$((KEEP + 1))); do
    rm -f "$cu" "${cu/db_/files_}"
    rm -f "${cu%.sql}.tar.gz" 2>/dev/null || true
    XOA=$((XOA + 1))
done
for cu in $(ls -1t "$DEST"/files_*.tar.gz 2>/dev/null | tail -n +$((KEEP + 1))); do
    rm -f "$cu"
done
[ "$XOA" = 0 ] || c_ok "đã xoá $XOA bản cũ (giữ $KEEP bản gần nhất)"

# Mốc cho agent ở P4 đọc "tuổi sao lưu", và cho install.sh verify.
printf '{"at":"%s","db":"%s","files":"%s","dest":"%s"}\n' \
    "$(date -Iseconds)" "$(basename "$DB_OUT")" "$(basename "$FILES_OUT")" "$DEST" \
    > "$DEST/last-backup.json"

printf '\n'
c_ok "Xong. $DEST"
ls -1t "$DEST"/db_*.sql 2>/dev/null | head -"$KEEP" | sed 's|^|      |'
