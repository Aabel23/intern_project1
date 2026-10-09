#!/usr/bin/env bash
#
# Cài máy pha chế FlexMix từ đầu.
#
# CÁCH DÙNG
#     ./deploy/install.sh                # xem hướng dẫn
#     ./deploy/install.sh manual         # danh sách việc PHẢI làm tay
#     ./deploy/install.sh all            # chạy tuần tự tất cả phase tự động
#     ./deploy/install.sh <phase>        # chạy lại đúng một phase
#
# TRIẾT LÝ
#     Script làm được đến đâu thì làm đến đó, và DỪNG LẠI ở đúng ba chỗ mà
#     máy không tự quyết được:
#       - reboot bật I2C          -> phải có người bấm
#       - cắm máy in / máy quét   -> phần cứng
#       - khoá đường thoát kiosk  -> phase riêng, phải gõ đúng chữ xác nhận
#
#     Mọi phase đều CHẠY LẠI ĐƯỢC. Chạy hai lần không hỏng gì.
#
#     Ngoại lệ quan trọng nhất: KHOÁ QR. Nếu /etc/flexmix/qrproto.env đã có
#     khoá thì script KHÔNG BAO GIỜ sinh khoá mới đè lên. Sinh khoá mới làm
#     hỏng vĩnh viễn mọi nhãn đã in nhưng chưa quét.

set -euo pipefail

# ---------------------------------------------------------------- hằng số --
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_DIR="/etc/flexmix"
ENV_FILE="$ENV_DIR/qrproto.env"          # ĐÚNG tên mà flexmix-backend.service đọc
KIOSK_DIR="$PROJECT_DIR/deploy/kiosk"
VENV="$PROJECT_DIR/.venv"
PY="$VENV/bin/python3"
RUN_USER="$(id -un)"
DB_NAME="beveragepos"
SUDOERS_FILE="/etc/sudoers.d/flexmix-restart"
# ĐÚNG đường dẫn mà configuration/configuration.py dựng RUNTIME_DIR từ đó.
# Hai nơi khai một đường dẫn là hai nơi sẽ lệch, nên nếu sửa thì sửa cả hai.
RUNTIME_DIR="/var/lib/flexmix"
# Người gác đồng hồ được phép đợi bao lâu. Xem phase_service.
TIME_WAIT_SYNC_TIMEOUT=90

# Mọi phase gọi python theo tên module (qrproto.keys, database.db_core,
# admin_gui.auth) nên thư mục làm việc PHẢI là gốc dự án — kể cả khi người
# dùng gọi script bằng đường dẫn tuyệt đối từ chỗ khác.
cd "$PROJECT_DIR"

PHASES="preflight packages hardware python secrets mysql database account printer runtime service kiosk verify"

# ------------------------------------------------------------------ in ấn --
c_ok()   { printf '  \033[32m✓\033[0m %s\n' "$*"; }
c_warn() { printf '  \033[33m!\033[0m %s\n' "$*"; }
c_err()  { printf '  \033[31m✗\033[0m %s\n' "$*" >&2; }
c_info() { printf '    %s\n' "$*"; }
title()  { printf '\n\033[1m== %s ==\033[0m\n' "$*"; }

die() { c_err "$*"; exit 1; }

# Dừng lại bắt người đọc, dùng cho việc không quay lại được.
confirm() {
    local want="$1" ans
    printf '\n  Gõ \033[1m%s\033[0m để tiếp tục (Enter để bỏ qua): ' "$want"
    read -r ans || true
    [ "$ans" = "$want" ]
}

need_sudo() {
    sudo -n true 2>/dev/null && return 0
    c_info "Cần quyền sudo, sẽ hỏi mật khẩu."
    sudo -v || die "Không có quyền sudo."
}

# Đọc một biến trong $ENV_FILE mà KHÔNG source file.
#
# `set -a; . file` sẽ cho shell diễn giải giá trị: mật khẩu có $ hoặc dấu
# nháy là chạy sai hoặc chạy lệnh. systemd không diễn giải gì cả, nên cách
# đọc ở đây phải giống systemd chứ không giống bash.
env_get() {
    sudo sed -n "s/^[[:space:]]*$1=//p" "$ENV_FILE" 2>/dev/null | head -1
}

# Gọi mysql qua file cấu hình tạm thay vì -p<mật khẩu>.
#
# `mysql -pXXX` in mật khẩu ra `ps aux` cho mọi user trên máy đọc được.
# File tạm chmod 600, xoá ngay sau khi chạy.
mysql_run() {
    local user="$1" pass="$2" sql="$3" rc=0
    local cnf; cnf="$(mktemp)"
    chmod 600 "$cnf"
    # Có dấu nháy kép vì my.cnf coi '#' là chú thích. Dấu " trong mật khẩu
    # đã bị chặn từ lúc ghi ở phase 'secrets'.
    printf '[client]\nuser=%s\npassword="%s"\nhost=%s\nport=%s\n' \
        "$user" "$pass" "${BEVERAGE_DB_HOST:-localhost}" "${BEVERAGE_DB_PORT:-3306}" > "$cnf"
    mysql --defaults-extra-file="$cnf" -e "$sql" >/dev/null 2>&1 || rc=$?
    rm -f "$cnf"
    return "$rc"
}

# ============================================================== 0. PREFLIGHT
# Chỉ ĐỌC, không đổi gì. Chạy trước để biết máy có đúng loại không.
phase_preflight() {
    title "0. Kiểm tra máy (không thay đổi gì)"
    local fail=0

    [ "$RUN_USER" = "root" ] && die "Đừng chạy bằng root. Chạy bằng user thường; script tự gọi sudo."

    local model="?"
    [ -r /proc/device-tree/model ] && model="$(tr -d '\0' < /proc/device-tree/model)"
    c_info "Máy      : $model"
    c_info "Kiến trúc: $(uname -m)"
    c_info "Hệ điều hành: $(. /etc/os-release && echo "$PRETTY_NAME")"
    c_info "User     : $RUN_USER"
    c_info "Mã nguồn : $PROJECT_DIR"

    case "$(uname -m)" in
        aarch64) c_ok "Kiến trúc aarch64" ;;
        *) c_warn "Không phải aarch64 — tài liệu viết cho Raspberry Pi arm64" ;;
    esac

    case "$model" in
        *"Pi 5"*) c_ok "Raspberry Pi 5" ;;
        *) c_warn "Không phải Pi 5 — vẫn chạy được, nhưng số liệu CMA ở tài liệu là đo trên Pi 5" ;;
    esac

    [ -f "$PROJECT_DIR/main.py" ] || { c_err "Không thấy main.py trong $PROJECT_DIR"; fail=1; }
    [ -f "$PROJECT_DIR/requirements.txt" ] || { c_err "Không thấy requirements.txt"; fail=1; }
    [ -d "$KIOSK_DIR" ] || { c_err "Không thấy $KIOSK_DIR"; fail=1; }

    # Đường dẫn ghi cứng trong service file — khác là service sẽ không chạy.
    if grep -q "WorkingDirectory=$PROJECT_DIR" "$KIOSK_DIR/flexmix-backend.service" 2>/dev/null; then
        c_ok "Đường dẫn khớp với flexmix-backend.service"
    else
        c_warn "flexmix-backend.service ghi đường dẫn KHÁC $PROJECT_DIR"
        c_info "Phải sửa 3 dòng User= / WorkingDirectory= / ExecStart= trước khi chạy phase 'service'."
    fi

    printf '\n'
    [ "$fail" = 0 ] && c_ok "Máy sẵn sàng cài" || die "Sửa các lỗi trên trước đã."
}

# =============================================================== 1. PACKAGES
phase_packages() {
    title "1. Cài gói hệ thống"
    need_sudo
    sudo apt-get update -qq
    # --no-install-recommends cho nhóm kiosk: tránh kéo cả desktop về.
    sudo apt-get install -y -qq \
        python3-venv python3-dev build-essential \
        mysql-server cups gpiod i2c-tools
    sudo apt-get install -y -qq --no-install-recommends \
        xserver-xorg xinit openbox firefox unclutter curl lightdm
    c_ok "Đã cài gói apt"

    # firefox là gói chuyển tiếp -> snap. Lần đầu tải lâu.
    if command -v firefox >/dev/null 2>&1; then
        c_ok "firefox: $(firefox --version 2>/dev/null || echo 'đã cài')"
    else
        die "Chưa có firefox. KHÔNG được thay bằng Chromium — xem docs sheet '9. Trình duyệt & CMA'."
    fi

    # mysql-server và cups phải sống qua reboot, không chỉ sống lúc này.
    sudo systemctl enable --now mysql cups >/dev/null 2>&1 || true
    c_ok "mysql + cups bật cùng máy"
}

# =============================================================== 2. HARDWARE
# Bật I2C + cấp quyền. CẢ HAI đều cần đăng xuất/reboot mới có hiệu lực.
phase_hardware() {
    title "2. Bật I2C và cấp quyền phần cứng"
    need_sudo
    local cfg=/boot/firmware/config.txt need_reboot=0

    if [ -f "$cfg" ]; then
        if grep -qE '^\s*dtparam=i2c_arm=on' "$cfg"; then
            c_ok "I2C đã bật trong config.txt"
        else
            # Thêm dưới [all] để không rơi vào một bộ lọc model nào đó.
            printf '\n[all]\ndtparam=i2c_arm=on\n' | sudo tee -a "$cfg" >/dev/null
            c_ok "Đã thêm dtparam=i2c_arm=on"
            need_reboot=1
        fi
    else
        c_warn "Không thấy $cfg — bỏ qua bước bật I2C"
    fi

    # i2c = bảng nút · gpio = bơm/cân · dialout = máy quét · lpadmin = máy in
    # Dùng so khớp chuỗi thay vì `| grep -q`: với `set -o pipefail`, grep -q
    # thoát sớm làm lệnh đầu ống nhận SIGPIPE và cả pipeline bị coi là lỗi.
    local missing="" groups_now
    groups_now=" $(id -nG "$RUN_USER") "
    for g in gpio dialout i2c lpadmin; do
        getent group "$g" >/dev/null 2>&1 || continue
        case "$groups_now" in
            *" $g "*) ;;
            *) missing="$missing $g" ;;
        esac
    done
    if [ -n "$missing" ]; then
        sudo usermod -aG "$(echo $missing | tr ' ' ',')" "$RUN_USER"
        c_ok "Đã thêm $RUN_USER vào nhóm:$missing"
        need_reboot=1
    else
        c_ok "User đã đủ nhóm gpio/dialout/i2c/lpadmin"
    fi

    if [ "$need_reboot" = 1 ]; then
        printf '\n'
        c_warn "PHẢI REBOOT rồi mới chạy tiếp các phase sau."
        c_info "sudo reboot"
        c_info "Thiếu bước này: bảng đèn báo 'Permission denied: /dev/i2c-1' lúc boot."
        return 10
    fi
}

# ================================================================= 3. PYTHON
phase_python() {
    title "3. Môi trường Python"
    [ -d "$VENV" ] || python3 -m venv "$VENV"
    "$VENV/bin/pip" install -q --upgrade pip
    "$VENV/bin/pip" install -q -r "$PROJECT_DIR/requirements.txt"
    c_ok "venv sẵn sàng: $VENV"

    "$PY" - <<'PY' || die "Thiếu thư viện — xem log pip ở trên."
import gpiozero, mysql.connector, serial, smbus2, cryptography, qrcode, PIL
print("    đủ gói bắt buộc")
PY

    # Import chính mã nguồn dự án, không chỉ thư viện ngoài: một file
    # thiếu hoặc một lỗi cú pháp phải lộ ra ở đây, không phải lúc service
    # khởi động rồi Restart=always quay vòng vô hạn.
    #
    # qrproto và admin_gui.auth không cần biến môi trường nào; database và
    # store_gui thì có (BEVERAGE_DB_PASSWORD) nên để phase 'database' lo.
    "$PY" - <<'PY' || die "Mã nguồn không import được — xem lỗi ở trên."
import qrproto, admin_gui.auth, qrproto.keys
print("    mã nguồn import được")
PY
}

# ================================================================ 4. SECRETS
# Sinh khoá QR RIÊNG cho máy này và ghi file env.
# KHÔNG BAO GIỜ đè lên khoá đã có.
phase_secrets() {
    title "4. Khoá QR và file cấu hình"
    need_sudo

    if sudo test -f "$ENV_FILE" && sudo grep -qE '^QRPROTO_KEY=[0-9a-fA-F]{64}$' "$ENV_FILE"; then
        c_ok "$ENV_FILE đã có khoá hợp lệ — GIỮ NGUYÊN"
        c_info "Sinh khoá mới sẽ làm hỏng vĩnh viễn mọi nhãn đã in chưa quét."
        return 0
    fi

    c_warn "Chưa có khoá. Sẽ sinh khoá RIÊNG cho máy này."
    c_info "Không bao giờ copy khoá từ máy khác sang."

    [ -x "$PY" ] || die "Chưa có venv — chạy './deploy/install.sh python' trước."

    local key mid dbpass dbpass2
    key="$("$PY" -c 'from qrproto.keys import generate_key; print(generate_key().hex())')"
    [ "${#key}" = 64 ] || die "Khoá sinh ra không đúng 64 ký tự hex."

    printf '\n  Số hiệu máy (QRPROTO_MACHINE_ID, 1-999999) [1]: '
    read -r mid || true; mid="${mid:-1}"
    case "$mid" in
        ''|*[!0-9]*) die "Số hiệu máy phải là số nguyên." ;;
    esac
    { [ "$mid" -ge 1 ] && [ "$mid" -le 999999 ]; } || die "Số hiệu máy phải trong khoảng 1-999999."

    printf '\n  Mật khẩu MySQL root cho máy này.\n'
    c_info "Chưa đặt bao giờ cũng không sao: gõ mật khẩu MỚI ở đây,"
    c_info "phase 'mysql' ngay sau đây sẽ tự đặt nó cho root."
    printf '  Mật khẩu (gõ không hiện): '
    read -rs dbpass || true; printf '\n'
    printf '  Nhập lại: '
    read -rs dbpass2 || true; printf '\n'

    [ -n "$dbpass" ] || die "Phải có mật khẩu MySQL."
    [ "$dbpass" = "$dbpass2" ] || die "Hai lần nhập không khớp."

    # systemd EnvironmentFile bóc dấu nháy và không diễn giải gì khác.
    # Chặn đúng những ký tự làm lệch nghĩa giữa file env, my.cnf và systemd,
    # thay vì để mật khẩu "đúng" mà đăng nhập vẫn hỏng không rõ lý do.
    if printf '%s' "$dbpass" | LC_ALL=C grep -q '[^!-~]'; then
        die "Mật khẩu chỉ dùng ký tự ASCII in được, không khoảng trắng."
    fi
    case "$dbpass" in
        *[\'\"\\]*) die "Mật khẩu không được chứa  '  \"  hoặc  \\" ;;
    esac

    sudo mkdir -p "$ENV_DIR"
    sudo tee "$ENV_FILE" >/dev/null <<EOF
# Sinh bởi deploy/install.sh — $(date -Is)
# Khoá mã hoá QR: RIÊNG của máy này. KHÔNG copy sang máy khác.
QRPROTO_KEY=$key
QRPROTO_MACHINE_ID=$mid

BEVERAGE_DB_HOST=localhost
BEVERAGE_DB_PORT=3306
BEVERAGE_DB_USER=root
BEVERAGE_DB_PASSWORD=$dbpass
BEVERAGE_DB_NAME=$DB_NAME
EOF
    # 640 + nhóm của user chạy máy: chỉ root ghi, chỉ user đó đọc.
    sudo chown "root:$RUN_USER" "$ENV_FILE"
    sudo chmod 640 "$ENV_FILE"
    c_ok "Đã tạo $ENV_FILE (chmod 640, root:$RUN_USER)"
    c_warn "LƯU KHOÁ NÀY RA NGOÀI NGAY — mất là hỏng mọi nhãn chưa quét:"
    printf '      %s\n' "$key"
}

# ================================================================== 5. MYSQL
# Làm cho mật khẩu thật của root khớp với mật khẩu đã ghi ở phase 'secrets'.
phase_mysql() {
    title "5. Mật khẩu MySQL root"
    need_sudo
    sudo test -f "$ENV_FILE" || die "Chưa có $ENV_FILE — chạy phase 'secrets' trước."

    local user pass
    user="$(env_get BEVERAGE_DB_USER)"; user="${user:-root}"
    pass="$(env_get BEVERAGE_DB_PASSWORD)"
    [ -n "$pass" ] || die "Không đọc được BEVERAGE_DB_PASSWORD trong $ENV_FILE."

    if mysql_run "$user" "$pass" "SELECT 1;"; then
        c_ok "'$user' đã đăng nhập được bằng mật khẩu trong $ENV_FILE"
        return 0
    fi

    # Ubuntu cài mysql-server với root@localhost dùng auth_socket: `sudo mysql`
    # vào được mà không cần mật khẩu. Đó là cửa duy nhất để đặt mật khẩu lần
    # đầu — và nó đóng lại ngay sau khi đặt xong.
    if ! sudo mysql -e "SELECT 1;" >/dev/null 2>&1; then
        c_err "Không đăng nhập được bằng mật khẩu, mà 'sudo mysql' cũng không vào được."
        c_info "Nghĩa là root đã có một mật khẩu KHÁC cái đang ghi trong $ENV_FILE."
        c_info "Chọn một trong hai:"
        c_info "  a) sửa BEVERAGE_DB_PASSWORD trong $ENV_FILE cho khớp mật khẩu thật"
        c_info "  b) đăng nhập bằng mật khẩu cũ rồi tự ALTER USER sang mật khẩu mới"
        return 1
    fi

    c_warn "root đang dùng auth_socket. Sẽ đặt mật khẩu từ $ENV_FILE."
    c_info "Sau bước này 'sudo mysql' KHÔNG vào được nữa — phải dùng mật khẩu."

    # Truyền mật khẩu qua stdin, không qua -e trên dòng lệnh: dòng lệnh của
    # tiến trình mysql hiện trong `ps aux` cho mọi user đọc.
    printf "ALTER USER '%s'@'localhost' IDENTIFIED WITH mysql_native_password BY '%s';\nFLUSH PRIVILEGES;\n" \
        "$user" "$pass" | sudo mysql \
        || die "ALTER USER thất bại."

    mysql_run "$user" "$pass" "SELECT 1;" \
        || die "Đặt xong mà vẫn không đăng nhập được — kiểm tra lại $ENV_FILE."
    c_ok "Đã đặt mật khẩu cho '$user'@'localhost'"
}

# =============================================================== 6. DATABASE
phase_database() {
    title "6. Cơ sở dữ liệu"
    need_sudo
    sudo test -f "$ENV_FILE" || die "Chưa có $ENV_FILE — chạy phase 'secrets' trước."

    local user pass name
    user="$(env_get BEVERAGE_DB_USER)"; user="${user:-root}"
    pass="$(env_get BEVERAGE_DB_PASSWORD)"
    name="$(env_get BEVERAGE_DB_NAME)"; name="${name:-$DB_NAME}"

    mysql_run "$user" "$pass" \
        "CREATE DATABASE IF NOT EXISTS \`$name\` CHARACTER SET utf8mb4;" \
        || die "Không tạo được database. Chạy phase 'mysql' trước."
    c_ok "Database '$name' sẵn sàng"

    # `database.main update` = apply_database_sql() + check_inventory().
    # Gọi qua CLI thay vì gọi thẳng apply_database_sql: bỏ check_inventory()
    # thì drink.in_stock không được tính lần đầu, và màn hình bán hàng mở ra
    # với mọi món báo hết.
    env BEVERAGE_DB_USER="$user" \
        BEVERAGE_DB_PASSWORD="$pass" \
        BEVERAGE_DB_NAME="$name" \
        "$PY" -m database.main update \
        || die "Áp schema thất bại."
    c_ok "Đã áp schema và tính lại tồn kho"
}

# ================================================================ 7. ACCOUNT
# Tài khoản đăng nhập màn hình quản trị.
#
# configuration/admin_account.json nằm trong .gitignore, nên máy mới clone
# về là KHÔNG có tài khoản nào: mọi endpoint /api/admin/* trả 503 và không
# ai vào được menu để sửa giá.
phase_account() {
    title "7. Tài khoản quản trị"

    if "$PY" -c 'import admin_gui.auth as a; raise SystemExit(0 if a.is_configured() else 1)'; then
        c_ok "Đã có tài khoản admin — GIỮ NGUYÊN"
        c_info "Đổi mật khẩu: $PY -m admin_gui.auth --set-password"
        return 0
    fi

    c_warn "Chưa có tài khoản admin nào. Tạo ngay bây giờ."
    c_info "Tên đăng nhập mặc định: manager. Mật khẩu tối thiểu 8 ký tự."
    local admin_user
    printf '\n  Tên đăng nhập [manager]: '
    read -r admin_user || true; admin_user="${admin_user:-manager}"

    "$PY" -m admin_gui.auth --set-password --user "$admin_user" \
        || die "Chưa tạo được tài khoản admin."
    c_ok "Đã tạo tài khoản '$admin_user' (configuration/admin_account.json, chmod 600)"
}

# ================================================================ 8. PRINTER
# Tạo hàng đợi CUPS đúng tên mà printer/printer_qr.py gọi tới.
#
# Cắm USB thôi chưa đủ: CUPS chỉ tự tạo hàng đợi tạm với tên do nó tự đặt,
# còn mã nguồn gọi `lp -d <PRINTER_NAME>`. Tên không khớp là in không ra.
# Tên hàng đợi CUPS mà mã nguồn gọi tới.
#
# Đọc GIÁ TRỊ bằng Python, không regex vào source. Bản trước dùng
#     sed -n 's/^PRINTER_NAME[[:space:]]*=[[:space:]]*"\(.*\)".*/\1/p'
# trên printer/printer_qr.py, và khi hằng số đó chuyển vào
# configuration/machine.py thì dòng còn lại là `PRINTER_NAME =
# machine.PRINTER_NAME` -- không có dấu nháy, sed trả về RỖNG. Hệ quả:
# phase verify báo "chưa có hàng đợi CUPS tên ''" trên một máy có máy in
# hoàn toàn bình thường, còn phase printer thì die. Hỏi Python thì tên
# hằng số có đổi nhà bao nhiêu lần cũng không ảnh hưởng.
printer_queue_name() {
    [ -x "$PY" ] || return 1
    (cd "$PROJECT_DIR" && "$PY" -c \
        'from configuration.machine import PRINTER_NAME; print(PRINTER_NAME)' \
        2>/dev/null)
}

phase_printer() {
    title "8. Máy in nhãn (CUPS)"

    local want
    want="$(printer_queue_name)"
    [ -n "$want" ] || die "Không đọc được PRINTER_NAME từ configuration/machine.py (venv đã tạo chưa?)."
    c_info "Tên mã nguồn cần: $want"

    if lpstat -p "$want" >/dev/null 2>&1; then
        c_ok "Hàng đợi '$want' đã có"
        return 0
    fi

    local uri
    uri="$(lpinfo -v 2>/dev/null | sed -n 's|^direct \(usb://.*\)|\1|p' | head -1)"
    if [ -z "$uri" ]; then
        c_warn "Chưa thấy máy in USB nào — phần cứng, script không làm thay được."
        c_info "Cắm máy in vào cổng USB rồi chạy lại: ./deploy/install.sh printer"
        return 0
    fi
    c_info "Thiết bị USB: $uri"

    need_sudo
    # -m raw: gửi thẳng byte TSPL xuống máy in, không qua bộ lọc nào.
    # printer_qr.py in bằng `lp -o raw`, và máy in này nói TSPL chứ không
    # nói PostScript — cho CUPS "dịch" giúp là ra một trang trắng.
    sudo lpadmin -p "$want" -E -v "$uri" -m raw \
        || die "lpadmin thất bại — kiểm tra user có trong nhóm lpadmin chưa."
    sudo cupsenable "$want" >/dev/null 2>&1 || true
    sudo cupsaccept "$want" >/dev/null 2>&1 || true
    c_ok "Đã tạo hàng đợi raw '$want'"
    c_info "In thử một nhãn: xem bước 8 trong docs/SETUP_NEW_MACHINE.md"
}

# ================================================================ 9. RUNTIME
phase_runtime() {
    title "9. Thư mục trạng thái của máy"
    need_sudo

    # VÌ SAO HIỆU CHUẨN KHÔNG ĐƯỢC NẰM TRONG THƯ MỤC MÃ NGUỒN
    #     Mấy con số đó là số đo của ĐÚNG cỗ máy này: gram_per_sec của đúng
    #     cái bơm, điểm zero của đúng cái loadcell. Khi chúng còn nằm trong
    #     git, một bản clone mang số của máy khác đi theo — và máy mới rót
    #     sai ngay từ ly đầu, sai im lặng, vì r_squared 0.99999 trông không
    #     có gì đáng ngờ.
    #
    #     Nặng hơn: phát hành là "checkout tag + đổi symlink", tức cả thư
    #     mục mã nguồn bị thay mỗi lần cập nhật. Thứ gì nằm trong đó đều
    #     biến mất cùng lần thay ấy.
    #
    # Chủ sở hữu là $RUN_USER chứ KHÔNG phải root. calib_pump.py và
    # init_loadcell.py chạy dưới quyền người dùng, còn display_mode.write()
    # gọi mkdir() trên thư mục cha. Để root sở hữu là trang Màn hình ném
    # PermissionError đúng lúc bấm Lưu.
    if [ -d "$RUNTIME_DIR" ]; then
        c_ok "$RUNTIME_DIR đã có"
    else
        sudo mkdir -p "$RUNTIME_DIR"
        c_ok "Đã tạo $RUNTIME_DIR"
    fi

    sudo chown "$RUN_USER:$RUN_USER" "$RUNTIME_DIR"
    sudo chmod 755 "$RUNTIME_DIR"
    c_ok "Chủ sở hữu: $RUN_USER"

    # Chuyển nhà cho máy đã chạy từ trước.
    #
    # `cp -n` không bao giờ ghi đè — cùng luật mà phase 'secrets' áp cho
    # khoá QR, chỉ là diễn đạt bằng một cờ thay vì một khối if. Đè lên
    # hiệu chuẩn đang dùng là làm hỏng máy theo cách không ai nhìn thấy.
    #
    # Máy mới clone về không có file nào trong configuration/ (đã gitignore)
    # nên vòng này chạy rỗng, và calib_pump.py sẽ ghi thẳng vào nhà mới.
    local moved=0 name
    for name in calib_loadcell.json pump_calib.json display_mode.json; do
        [ -f "$PROJECT_DIR/configuration/$name" ] || continue

        if [ -f "$RUNTIME_DIR/$name" ]; then
            c_ok "$name đã ở $RUNTIME_DIR (không đè)"
        else
            cp -n "$PROJECT_DIR/configuration/$name" "$RUNTIME_DIR/$name"
            c_ok "Đã chuyển $name"
            moved=1
        fi
    done

    if [ "$moved" = 1 ]; then
        printf '\n'
        c_warn "PHẢI khởi động lại backend thì tiến trình mới đọc nhà mới."
        c_info "runtime_path() chốt đường dẫn MỘT LẦN lúc import, không phải"
        c_info "mỗi lần đọc — xem configuration/configuration.py."
        c_info "  sudo systemctl restart flexmix-backend"
    fi
}


# ================================================================ 10. SERVICE
phase_service() {
    title "10. systemd service"
    need_sudo
    local unit=flexmix-backend.service

    grep -q "WorkingDirectory=$PROJECT_DIR" "$KIOSK_DIR/$unit" \
        || die "$unit ghi đường dẫn khác $PROJECT_DIR — sửa User=/WorkingDirectory=/ExecStart= trước."

    # GIỚI HẠN THỜI GIAN CHỜ ĐỒNG HỒ — làm TRƯỚC khi bật unit dưới đây.
    #
    # systemd-time-wait-sync mặc định TimeoutStartSec=infinity: đợi VĨNH
    # VIỄN. Không có NTP thì time-sync.target không bao giờ đạt, và
    # flexmix-backend khai After=time-sync.target sẽ không bao giờ khởi
    # động. Tiệm mất mạng rồi mất điện một cái = máy nằm im, màn hình
    # trắng, và KHÔNG có gì báo lỗi vì nó không hỏng — nó đang đợi.
    #
    # Hết giờ thì unit này thất bại, time-sync.target vẫn activate, và
    # backend dùng Wants= (phụ thuộc YẾU, không phải Requires=) nên vẫn
    # chạy. Đồng hồ có thể chưa đúng, nhưng tiệm bán được.
    #
    # Đây là đánh đổi có chủ ý: đồng hồ sai làm vé lệch giờ và báo cáo
    # doanh thu hơi lệch. Máy không khởi động thì doanh thu bằng không.
    local dropin=/etc/systemd/system/systemd-time-wait-sync.service.d
    sudo mkdir -p "$dropin"
    printf '# Sinh bởi deploy/install.sh — xem phase_service để biết vì sao.\n[Service]\nTimeoutStartSec=%s\n' \
        "$TIME_WAIT_SYNC_TIMEOUT" | sudo tee "$dropin/timeout.conf" >/dev/null
    c_ok "Giới hạn chờ đồng hồ: ${TIME_WAIT_SYNC_TIMEOUT}s (mặc định là vô hạn)"

    # Nửa thứ hai của chốt NTP. flexmix-backend.service khai
    # After=/Wants=time-sync.target, nhưng target đó được coi là ĐẠT ngay
    # khi một dịch vụ đồng bộ giờ khởi động — không phải khi đồng hồ đã
    # đúng. Unit dưới đây mới là thứ chặn cho tới lúc đồng hồ đúng, và
    # Ubuntu tắt nó mặc định. Thiếu nó thì hai dòng trong unit file trông
    # đúng mà không làm gì cả.
    if sudo systemctl enable --now systemd-time-wait-sync >/dev/null 2>&1; then
        c_ok "systemd-time-wait-sync đã bật (đồng hồ đúng trước khi backend chạy)"
    else
        c_warn "không bật được systemd-time-wait-sync"
        c_info "Máy vừa mất điện sẽ chạy với đồng hồ sai tới khi NTP kéo về."
    fi

    sudo cp "$KIOSK_DIR/$unit" /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable --now "$unit"
    # enable --now không khởi động lại một service đang chạy bản cũ.
    sudo systemctl restart "$unit"
    c_ok "Đã bật $unit"

    # Chờ cổng 8080 lên; service Restart=always nên lỗi cấu hình sẽ lặp vô hạn.
    local i
    for i in $(seq 1 30); do
        curl -sf -o /dev/null "http://localhost:8080/store_gui/drinks-pos.html" && break
        sleep 1
    done
    if curl -sf -o /dev/null "http://localhost:8080/store_gui/drinks-pos.html"; then
        c_ok "Trang bán hàng trả lời trên cổng 8080"
    else
        c_err "Cổng 8080 không trả lời sau 30 giây."
        c_info "journalctl -u $unit --no-pager -n 40"
        return 1
    fi
}

# ================================================================= 11. KIOSK
# Mở trình duyệt lúc boot + khoá Firefox + chặn snap tự cập nhật.
# KHÔNG bao gồm bước khoá đường thoát (xem phase 'lockdown').
phase_kiosk() {
    title "11. Chế độ kiosk (Firefox)"
    need_sudo

    # --- 10a. autologin vào Openbox ---
    if [ -f /etc/lightdm/lightdm.conf ] \
       && grep -q "autologin-user=$RUN_USER" /etc/lightdm/lightdm.conf 2>/dev/null; then
        c_ok "lightdm đã cấu hình autologin"
    else
        c_warn "Chưa cấu hình autologin trong /etc/lightdm/lightdm.conf"
        c_info "Thêm vào mục [Seat:*]:"
        c_info "  autologin-user=$RUN_USER"
        c_info "  autologin-user-timeout=0"
        c_info "  user-session=openbox"
        c_info "Rồi: sudo systemctl disable gdm3 && sudo systemctl enable lightdm"
    fi

    # --- 10b. autostart mở Firefox ---
    mkdir -p "$HOME/.config/openbox"
    cp "$KIOSK_DIR/kiosk-openbox-autostart.sh" "$HOME/.config/openbox/autostart"
    chmod +x "$HOME/.config/openbox/autostart"
    c_ok "Đã chép autostart (mở firefox --kiosk --private-window)"

    # --- 10c. preferences khoá Firefox ---
    # Hồ sơ chỉ sinh ra sau khi Firefox chạy lần đầu.
    local prof
    prof="$(find "$HOME/snap/firefox/common/.mozilla/firefox" -maxdepth 1 -name '*.default*' -type d 2>/dev/null | head -1)"
    if [ -z "$prof" ]; then
        c_info "Chưa có hồ sơ Firefox, đang tạo (chạy thử 20 giây)..."
        timeout 20 firefox --headless about:blank >/dev/null 2>&1 || true
        prof="$(find "$HOME/snap/firefox/common/.mozilla/firefox" -maxdepth 1 -name '*.default*' -type d 2>/dev/null | head -1)"
    fi
    if [ -n "$prof" ]; then
        cp "$KIOSK_DIR/firefox-kiosk-user.js" "$prof/user.js"
        c_ok "Đã chép user.js vào $(basename "$prof")"
    else
        c_err "Không tạo được hồ sơ Firefox."
        c_info "Mở Firefox bằng tay một lần rồi chạy lại phase này."
        c_info "THIẾU BƯỚC NÀY: khách vuốt cạnh màn hình là lùi trang được."
    fi

    # --- 10d. chặn snap tự cập nhật ---
    # snapd unmount squashfs của Firefox đang chạy -> màn hình chớp tắt giữa giờ bán.
    #
    # `snap refresh --time` in dòng "hold:" chỉ khi CÓ hold. Hỏi thẳng
    # snapd về gói firefox chắc chắn hơn là đọc bảng lịch chung.
    if snap refresh --time 2>/dev/null | grep -qi '^hold:'; then
        c_ok "Firefox đã bị chặn tự cập nhật"
    else
        sudo snap refresh --hold=forever firefox >/dev/null 2>&1 \
            && c_ok "Đã chặn Firefox tự cập nhật (--hold=forever)" \
            || c_warn "Không đặt được hold — chạy tay: sudo snap refresh --hold=forever firefox"
        c_info "Đánh đổi: phải tự 'sudo snap refresh firefox' vài tháng/lần lúc đóng cửa."
    fi
}

# ================================================================ 12. VERIFY
phase_verify() {
    title "12. Kiểm tra tổng thể"
    local bad=0

    systemctl is-active --quiet flexmix-backend.service \
        && c_ok "backend: active" || { c_err "backend KHÔNG chạy"; bad=1; }

    curl -sf -o /dev/null http://localhost:8080/store_gui/drinks-pos.html \
        && c_ok "cổng 8080 trả lời" || { c_err "cổng 8080 im"; bad=1; }

    # File cấu hình phải có ĐỦ 7 biến. Thiếu mà không ai biết là chuyện đã
    # xảy ra: một máy chỉ có QRPROTO_KEY, 5 biến DB nằm ở <dự án>/.env, và
    # QRPROTO_MACHINE_ID không có ở đâu cả nên lặng lẽ lấy mặc định 1. Máy
    # vẫn bán hàng bình thường, nên không gì báo cho tới lúc dựng máy thứ
    # hai và hai máy cùng mang số 1.
    #
    # ĐỌC ĐƯỢC HAY KHÔNG phải hỏi TRƯỚC. Bản đầu của kiểm tra này grep qua
    # sudo, và khi sudo đòi mật khẩu thì mọi grep đều trượt -- nó báo cả 7
    # biến "THIẾU" trong khi khoá vẫn nằm đó. Một báo cáo sai còn tệ hơn
    # không báo, vì nó dụ người ta đi tạo lại khoá và giết mọi nhãn chưa quét.
    local envcat=""
    if [ -r "$ENV_FILE" ]; then
        envcat="cat"
        c_ok "$RUN_USER đọc được $ENV_FILE"
    elif sudo -n test -r "$ENV_FILE" 2>/dev/null; then
        envcat="sudo cat"
        c_err "$RUN_USER KHÔNG đọc được $ENV_FILE (chỉ root đọc được)"
        c_info "Mọi lệnh chạy tay (calib_pump, database.main, admin_gui.auth)"
        c_info "sẽ không tìm thấy mật khẩu DB. Sửa:"
        c_info "  sudo chown root:$RUN_USER $ENV_FILE && sudo chmod 640 $ENV_FILE"
        c_info "  sudo chmod 755 $ENV_DIR"
        bad=1
    fi

    if [ -z "$envcat" ]; then
        c_warn "Không đọc được $ENV_FILE để kiểm tra (cần sudo)."
        c_info "Chạy lại bằng: sudo ./deploy/install.sh verify"
    else
        local missing="" want
        for want in QRPROTO_KEY QRPROTO_MACHINE_ID BEVERAGE_DB_HOST \
                    BEVERAGE_DB_PORT BEVERAGE_DB_USER BEVERAGE_DB_PASSWORD \
                    BEVERAGE_DB_NAME; do
            $envcat "$ENV_FILE" 2>/dev/null | grep -qE "^${want}=" \
                || missing="$missing $want"
        done

        if [ -z "$missing" ]; then
            c_ok "$ENV_FILE có đủ 7 biến"
        else
            c_err "$ENV_FILE THIẾU:$missing"
            c_info "Thiếu QRPROTO_MACHINE_ID = máy lặng lẽ mang số 1."
            c_info "Thêm tay, hoặc './deploy/install.sh secrets' để tạo lại"
            c_info "— nhưng lệnh đó GIỮ NGUYÊN khoá cũ nếu đã có, nên an toàn."
            bad=1
        fi
    fi

    # Đồng hồ: hai nửa, và nửa thứ hai là cái hay thiếu. Xem comment
    # trong deploy/kiosk/flexmix-backend.service.
    if systemctl is-enabled systemd-time-wait-sync >/dev/null 2>&1; then
        c_ok "systemd-time-wait-sync bật — đồng hồ đúng trước khi backend chạy"
    else
        c_err "systemd-time-wait-sync TẮT — After=time-sync.target không chặn gì"
        c_info "Máy vừa mất điện chạy với đồng hồ sai; Hub sẽ từ chối chữ ký."
        c_info "   ./deploy/install.sh service"
        bad=1
    fi

    # Và giới hạn chờ. Thiếu nó thì máy mất mạng sẽ KHÔNG khởi động nổi
    # backend — tệ hơn hẳn đồng hồ sai.
    if [ -f /etc/systemd/system/systemd-time-wait-sync.service.d/timeout.conf ]; then
        c_ok "chờ đồng hồ có giới hạn (${TIME_WAIT_SYNC_TIMEOUT}s)"
    else
        c_err "chờ đồng hồ KHÔNG giới hạn — mất mạng là backend không khởi động"
        c_info "   ./deploy/install.sh service"
        bad=1
    fi

    # Hiệu chuẩn còn nằm trong thư mục mã nguồn = một lần "checkout tag +
    # đổi symlink" nữa là mất. Chỉ báo lỗi khi file CÒN ở chỗ cũ mà CHƯA có
    # ở chỗ mới: máy chưa hiệu chuẩn bao giờ thì không có file nào cả, và
    # đó không phải lỗi của bước này.
    local unmigrated="" name
    for name in calib_loadcell.json pump_calib.json display_mode.json; do
        [ -f "$PROJECT_DIR/configuration/$name" ] || continue
        [ -f "$RUNTIME_DIR/$name" ] && continue
        unmigrated="$unmigrated $name"
    done

    if [ -n "$unmigrated" ]; then
        c_err "Còn trong thư mục mã nguồn:$unmigrated"
        c_info "Lần phát hành kế tiếp sẽ xoá chúng cùng thư mục checkout."
        c_info "   ./deploy/install.sh runtime"
        bad=1
    elif [ -d "$RUNTIME_DIR" ]; then
        c_ok "hiệu chuẩn nằm ngoài thư mục mã nguồn ($RUNTIME_DIR)"
    else
        c_warn "chưa có $RUNTIME_DIR"
        c_info "   ./deploy/install.sh runtime"
    fi

    # Hồ sơ máy: không có là bình thường -- máy đi dây như máy #1. Có mà
    # hỏng thì backend KHÔNG khởi động, cố ý (configuration/machine.py, mục
    # HỒ SƠ MÁY), nên ở đây phải nói được VÌ SAO chứ không chỉ "backend chết".
    # Đường dẫn hỏi từ Python để chỉ có một nơi giữ nó.
    local profile_out profile_path profile_exists profile_n
    if profile_out="$("$PY" -c 'import configuration.machine as m; print(m.PROFILE_FILE, int(m.PROFILE_FILE.exists()), len(m.PROFILE_KEYS))' 2>&1)"; then
        read -r profile_path profile_exists profile_n <<< "$profile_out"

        if [ "$profile_exists" = 1 ]; then
            c_ok "hồ sơ máy dùng được — $profile_n giá trị khác máy #1 ($profile_path)"
        else
            c_ok "không có hồ sơ máy — đi dây như máy #1"
        fi
    else
        c_err "configuration.machine KHÔNG nạp được — backend sẽ không khởi động:"
        c_info "$(printf '%s\n' "$profile_out" | tail -1)"
        c_info "   ./.venv/bin/python3 -m configuration.machine"
        bad=1
    fi

    # Không có tài khoản admin thì máy vẫn bán được, nhưng không ai sửa
    # được menu hay giá — và lỗi chỉ lộ ra khi đứng trước màn hình đăng nhập.
    if "$PY" -c 'import admin_gui.auth as a; raise SystemExit(0 if a.is_configured() else 1)' 2>/dev/null; then
        c_ok "có tài khoản admin"
    else
        c_err "CHƯA có tài khoản admin — màn hình quản trị trả 503"
        c_info "   ./deploy/install.sh account"
        bad=1
    fi

    local wd_n
    wd_n="$(journalctl -u flexmix-backend --no-pager --since today 2>/dev/null | grep -c '\[watchdog\] on' || true)"
    if [ "${wd_n:-0}" -gt 0 ]; then
        c_ok "watchdog đã bật"
    else
        c_warn "không thấy dòng '[watchdog] on' hôm nay"
        c_info "kiểm tra service có Environment=FLEXMIX_KIOSK_WATCHDOG=1"
    fi

    # gpioinfo in ra tên consumer "lg" khi còn chân bị giữ.
    if command -v gpioinfo >/dev/null 2>&1; then
        local held_n
        held_n="$(gpioinfo gpiochip4 2>/dev/null | grep -c '"lg"' || true)"
        if [ "${held_n:-0}" -gt 0 ]; then
            c_warn "còn chân GPIO bị giữ — có tiến trình cũ chưa thoát"
        else
            c_ok "GPIO sạch"
        fi
    fi

    # Nhóm i2c: máy vẫn chạy khi thiếu, vì systemd-logind cấp ACL lên
    # /dev/i2c-1 lúc phiên đồ hoạ đăng nhập. Nhưng khi đó bảng nút chết
    # trong mấy giây đầu mỗi lần boot, và chết hẳn nếu lightdm không lên.
    case " $(id -nG "$RUN_USER") " in
        *" i2c "*) c_ok "user thuộc nhóm i2c" ;;
        *)
            if getfacl /dev/i2c-1 2>/dev/null | grep -q "^user:$RUN_USER:"; then
                c_warn "bảng nút đang chạy nhờ ACL của phiên đăng nhập, KHÔNG phải nhóm i2c"
                c_info "=> chết mấy giây đầu mỗi lần boot, chết hẳn nếu lightdm không lên"
                c_info "   sudo usermod -aG i2c $RUN_USER   (rồi reboot)"
            else
                c_err "user KHÔNG có quyền /dev/i2c-1 — bảng nút sẽ không hoạt động"
                c_info "   sudo usermod -aG i2c $RUN_USER   (rồi reboot)"
            fi
            ;;
    esac

    # After=mysql.service: thiếu thì backend chạy trước MySQL và vé QR treo
    # của đơn hỏng giữa chừng không được trả lại cho khách.
    local unit_file=/etc/systemd/system/flexmix-backend.service
    if [ -r "$unit_file" ]; then
        if grep -qE '^After=.*mysql' "$unit_file"; then
            c_ok "service chờ mysql trước khi chạy"
        else
            c_warn "service thiếu mysql.service trong dòng After="
            c_info "=> lúc boot: 'Không kiểm tra được vé QR treo: Errno 111'"
            c_info "   vé của đơn hỏng không được trả lại, khách quét lại không được"
        fi
    fi

    if [ -r /proc/meminfo ]; then
        local free; free=$(awk '/^CmaFree/{printf "%.0f", $2/1024}' /proc/meminfo)
        [ -n "$free" ] && c_ok "CmaFree: ${free} MB (Firefox: dao động 150-310 MB là bình thường)"
    fi

    local ffpid; ffpid="$(pgrep -x firefox 2>/dev/null | head -1 || true)"
    if [ -n "$ffpid" ]; then
        c_ok "Firefox đang chạy $(ps -o etimes= -p "$ffpid" | tr -d ' ') giây"
    else
        c_info "Firefox chưa chạy (bình thường nếu chưa vào chế độ kiosk)"
    fi

    if snap refresh --time 2>/dev/null | grep -qi '^hold:'; then
        c_ok "snap đang bị giữ (Firefox không tự cập nhật giữa giờ bán)"
    else
        c_warn "snap KHÔNG bị giữ — Firefox có thể tự cập nhật và chớp màn hình"
        c_info "   sudo snap refresh --hold=forever firefox"
    fi

    # MÁY IN: "CÓ HÀNG ĐỢI" KHÔNG PHẢI LÀ "IN ĐƯỢC"
    #
    # Bản trước chỉ chạy `lpstat -p "$want"` và chấm xanh khi nó thoát 0.
    # Nhưng lệnh đó thoát 0 khi hàng đợi TỒN TẠI -- bật hay tắt nó không
    # quan tâm. Đo được trên chính máy này 16/09/2026: CUPS đã tắt hàng đợi
    # XP-350BM từ 09/09 ("Unplugged or turned off"), ba việc in nằm kẹt từ
    # 09/09, 11/09 và 14/09, không vé nào được quét kể từ đó -- và verify
    # vẫn in ra "máy in 'XP-350BM' sẵn sàng" suốt một tuần.
    #
    # CUPS có HAI trạng thái độc lập, và tổ hợp nguy hiểm nhất là tổ hợp
    # trông bình thường nhất:
    #
    #   bật + nhận việc    -> in được
    #   tắt + TỪ CHỐI việc -> hỏng to tiếng: người bấm In thấy lỗi ngay
    #   tắt + NHẬN việc    -> hỏng IM LẶNG: vé vẫn phát, việc in chất đống,
    #                         khách đứng chờ một tờ nhãn không bao giờ ra
    #
    # LC_ALL=C để CUPS trả lời bằng tiếng Anh: các chuỗi dưới đây được dịch
    # theo locale, và một bản dịch làm grep trượt sẽ đưa ta về đúng chỗ cũ
    # -- báo xanh cho một máy in đã chết.
    local want
    want="$(printer_queue_name)"
    if [ -z "$want" ]; then
        c_warn "không đọc được PRINTER_NAME từ configuration/machine.py"
        c_info "   venv đã tạo chưa? ./deploy/install.sh python"
    elif ! lpstat -p "$want" >/dev/null 2>&1; then
        c_warn "chưa có hàng đợi CUPS tên '$want' (mã nguồn gọi đúng tên này)"
        c_info "   cắm máy in USB rồi: ./deploy/install.sh printer"
    else
        local pstate astate queued
        pstate="$(LC_ALL=C lpstat -p "$want" 2>/dev/null | head -1)"
        astate="$(LC_ALL=C lpstat -a "$want" 2>/dev/null | head -1)"
        queued="$(LC_ALL=C lpstat -o "$want" 2>/dev/null | grep -c . || true)"

        case "$pstate" in
            *disabled*)
                c_err "máy in '$want' BỊ TẮT — nhãn không in ra"
                c_info "   ${pstate#*disabled }"
                case "$astate" in
                    *"not accepting"*) ;;
                    *) c_info "   và nó VẪN NHẬN việc: màn hình bán hàng vẫn"
                       c_info "   mời bấm In, vé vẫn phát, không ai thấy lỗi." ;;
                esac
                c_info "   cắm lại dây rồi: sudo cupsenable $want"
                bad=1
                ;;
            *)
                c_ok "máy in '$want' đang bật"
                ;;
        esac

        case "$astate" in
            *"not accepting"*)
                c_err "máy in '$want' đang TỪ CHỐI việc in"
                c_info "   sudo cupsaccept $want"
                bad=1
                ;;
        esac

        if [ "${queued:-0}" -gt 0 ]; then
            c_err "còn $queued việc in kẹt trong hàng đợi '$want'"
            c_info "   xem:  lpstat -o $want"
            c_info "   huỷ:  cancel -a $want"
            bad=1
        fi
    fi

    ls /dev/serial/by-id/ >/dev/null 2>&1 \
        && c_ok "máy quét: $(ls /dev/serial/by-id/ | head -1)" \
        || c_warn "chưa thấy máy quét ở /dev/serial/by-id/"

    printf '\n'
    [ "$bad" = 0 ] && c_ok "Các mục bắt buộc đều đạt" || c_err "Còn mục hỏng ở trên"
    return "$bad"
}

# =============================================================== 13. SUDOERS
# TUỲ CHỌN. Cho nút số 14 trên bảng nút khởi động lại backend.
#
# CHỈ có tác dụng khi chạy main.py bằng tay. Dưới systemd luật này KHÔNG
# BAO GIỜ dùng tới: flexmix-backend.service đặt
# CapabilityBoundingSet=CAP_SYS_NICE, nên sudo không thể lên root ("unable
# to change to root gid") -- đo được trên máy thật 08/09/2026. button_watch
# vì thế bỏ qua sudo khi ở dưới systemd và giết MainPID để Restart=always
# dựng lại, không cần quyền gì.
#
# Giữ phase này vì nó vẫn đúng cho máy phát triển, và vì gỡ một file trong
# /etc/sudoers.d đã cài rồi thì rắc rối hơn là để yên.
phase_sudoers() {
    title "13. Cho nút 14 khởi động lại backend (tuỳ chọn)"
    need_sudo

    local rule="$RUN_USER ALL=(root) NOPASSWD: /usr/bin/systemctl restart --no-block flexmix-backend.service"

    if sudo test -f "$SUDOERS_FILE" && sudo grep -qF "$rule" "$SUDOERS_FILE"; then
        c_ok "$SUDOERS_FILE đã đúng"
        return 0
    fi

    # Ghi ra file tạm rồi visudo -c trước khi đặt vào /etc/sudoers.d:
    # một file sudoers hỏng cú pháp làm HỎNG sudo trên toàn máy.
    local tmp; tmp="$(mktemp)"
    printf '%s\n' "$rule" > "$tmp"
    if sudo visudo -c -f "$tmp" >/dev/null 2>&1; then
        sudo install -o root -g root -m 440 "$tmp" "$SUDOERS_FILE"
        c_ok "Đã cài $SUDOERS_FILE (chmod 440)"
    else
        rm -f "$tmp"
        die "Luật sudoers không hợp lệ — không cài, sudo giữ nguyên."
    fi
    rm -f "$tmp"
}

# =============================================================== 14. LOCKDOWN
# TÁCH RIÊNG, KHÔNG nằm trong 'all'. Sau bước này muốn thoát phải SSH.
phase_lockdown() {
    title "14. Khoá đường thoát  ⚠ CHỈ LÀM KHI CHUẨN BỊ GIAO MÁY"
    c_warn "Sau bước này: không còn Alt+F4, Alt+Tab, Ctrl+Alt+F1..F7."
    c_warn "Muốn vào lại máy phải SSH từ máy khác."
    confirm "KHOA" || { c_info "Đã bỏ qua."; return 0; }

    need_sudo
    mkdir -p "$HOME/.config/openbox"
    cp "$KIOSK_DIR/rc.xml" "$HOME/.config/openbox/rc.xml"
    sudo mkdir -p /etc/X11/xorg.conf.d
    sudo cp "$KIOSK_DIR/10-disable-vt-switch.conf" /etc/X11/xorg.conf.d/
    c_ok "Đã khoá phím tắt Openbox và chuyển console"
    c_info "Áp dụng: sudo systemctl restart lightdm"
    printf '\n'
    c_info "Đường thoát để bảo trì (qua SSH):"
    c_info "  pkill -f 'sh .*openbox/autostart'   # tắt vòng lặp tự mở lại"
    c_info "  pkill -f -- --kiosk                 # rồi mới đóng trình duyệt"
}

# ================================================================== MANUAL --
# Toàn bộ việc script KHÔNG làm thay, gom vào một chỗ, theo đúng thứ tự.
phase_manual() {
    cat <<EOF

$(printf '\033[1m== VIỆC PHẢI LÀM BẰNG TAY ==\033[0m')

Script tự làm hết phần còn lại. Năm việc dưới đây thì không — hoặc vì cần
phần cứng, hoặc vì làm sai thì không tự sửa lại được.

  M1. TRƯỚC KHI CHẠY SCRIPT — đưa mã nguồn vào máy
      git clone <repo> $PROJECT_DIR
      (hoặc rsync / USB — miễn là đúng đường dẫn trên)

  M2. GIỮA CHỪNG — reboot sau phase 'hardware'
      Script tự dừng và bảo bạn. Overlay I2C và quyền nhóm chỉ nạp lúc boot.
          sudo reboot
      Xong thì chạy lại:  ./deploy/install.sh all

  M3. TRƯỚC PHASE 'printer' — cắm phần cứng vào cổng USB
      máy in nhãn · máy quét mã · màn hình cảm ứng
      Kiểm tra:  lpinfo -v | grep usb     và     ls /dev/serial/by-id/

  M4. SAU PHASE 'kiosk' — bật tự đăng nhập cho lightdm
      Script chỉ báo thiếu, không tự sửa: sai một dòng ở đây là mất
      đường đăng nhập vào máy.
          sudo nano /etc/lightdm/lightdm.conf
      Trong mục [Seat:*] thêm 3 dòng:
          autologin-user=$RUN_USER
          autologin-user-timeout=0
          user-session=openbox
      Rồi:
          sudo systemctl disable gdm3 2>/dev/null; sudo systemctl enable lightdm

  M5. SAU CÙNG — hai việc chỉ người làm được
      a) Lưu QRPROTO_KEY (phase 'secrets' in ra) vào nơi an toàn NGOÀI máy.
         Mất khoá = hỏng vĩnh viễn mọi nhãn đã in chưa quét.
      b) Chạy thử một đơn thật đầu-cuối: đặt món → in nhãn → quét → pha xong
         → kiểm tra vé chuyển sang 'used'.

Khi cả 5 việc trên xong và './deploy/install.sh verify' sạch, mới giao máy:

      ./deploy/install.sh lockdown

EOF
}

# ==================================================================== chạy --
usage() {
    cat <<EOF
Cài máy pha chế FlexMix.

    ./deploy/install.sh <phase>

PHASE TỰ ĐỘNG (chạy theo đúng thứ tự này):
    preflight   kiểm tra máy, không đổi gì
    packages    apt + snap firefox
    hardware    bật I2C + cấp quyền nhóm      -> CẦN REBOOT sau bước này
    python      venv + requirements.txt + thử import mã nguồn
    secrets     sinh khoá QR + ghi $ENV_FILE  -> hỏi mật khẩu MySQL
    mysql       đặt mật khẩu root cho khớp file env
    database    tạo database + áp schema + tính tồn kho
    account     tạo tài khoản đăng nhập màn hình quản trị
    printer     tạo hàng đợi CUPS raw đúng tên PRINTER_NAME
    runtime     tạo /var/lib/flexmix + chuyển hiệu chuẩn ra khỏi mã nguồn
    service     cài + bật flexmix-backend
    kiosk       autostart + user.js + chặn snap update
    verify      kiểm tra tổng thể

    all         chạy lần lượt tất cả phase trên

PHASE RIÊNG (không nằm trong 'all'):
    manual      in danh sách 5 việc phải làm tay — ĐỌC CÁI NÀY TRƯỚC
    sudoers     cho nút 14 khởi động lại backend (tuỳ chọn)
    lockdown    khoá đường thoát — CHỈ khi chuẩn bị giao máy

CÀI MÁY MỚI, ĐẦY ĐỦ:
    ./deploy/install.sh manual     # đọc trước, làm M1
    ./deploy/install.sh all        # dừng ở chỗ cần reboot (M2)
    sudo reboot
    ./deploy/install.sh all        # chạy nốt
    ./deploy/install.sh sudoers    # tuỳ chọn
    ./deploy/install.sh lockdown   # khi chuẩn bị giao máy
EOF
}

main() {
    local phase="${1:-}"
    case "$phase" in
        ""|-h|--help|help) usage ;;
        all)
            phase_manual
            local p rc
            for p in $PHASES; do
                # KHÔNG dùng `if ! phase; then rc=$?`: với `!`, $? là kết quả
                # của phép phủ định (0/1), không phải mã thoát của phase —
                # tín hiệu "cần reboot" (10) bị nuốt mất và máy mới nào cũng
                # dừng ở phase 'hardware' với thông báo sai.
                set +e
                "phase_$p"
                rc=$?
                set -e

                if [ "$rc" = 10 ]; then
                    printf '\n'
                    c_warn "DỪNG: đây là việc tay M2. Reboot rồi chạy tiếp:"
                    c_info "sudo reboot"
                    c_info "./deploy/install.sh all"
                    exit 0
                fi
                [ "$rc" = 0 ] || die "Phase '$p' thất bại (mã $rc)."
            done
            printf '\n'
            c_ok "Xong phần tự động."
            c_info "Còn lại các việc tay: ./deploy/install.sh manual"
            c_info "Và cuối cùng, khi giao máy: ./deploy/install.sh lockdown"
            ;;
        *)
            # Danh sách tên hợp lệ SUY RA từ $PHASES, không chép lại nó.
            #
            # Bản trước chép tay, và hai danh sách lệch nhau ngay lần đầu có
            # phase mới: 'runtime' nằm trong $PHASES nên `install.sh all`
            # chạy nó, nhưng gọi thẳng `install.sh runtime` thì bị từ chối
            # là "không tồn tại" — một phase chạy được nửa đường, và thông
            # báo lỗi nói sai hẳn nguyên nhân.
            #
            # Ba tên cuối KHÔNG nằm trong $PHASES vì chúng không được chạy
            # trong 'all': đều là việc tay, và 'lockdown' thì không quay lại
            # được. Nhưng gọi thẳng tên thì vẫn phải được.
            case " $PHASES sudoers lockdown manual " in
                *" $phase "*) ;;
                *) die "Phase không tồn tại: $phase  (chạy không tham số để xem hướng dẫn)" ;;
            esac

            set +e
            "phase_$phase"
            rc=$?
            set -e
            # 10 = "cần reboot", là kết quả bình thường của phase 'hardware',
            # không phải lỗi.
            [ "$rc" = 10 ] && exit 0
            exit "$rc"
            ;;
    esac
}

main "$@"
