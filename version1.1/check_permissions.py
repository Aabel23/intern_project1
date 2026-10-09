"""In ra ai làm được gì -- mặc định trong code CỘNG tuỳ chỉnh trong database.

Chạy sau mỗi lần sửa ROLE_AREAS / PATH_AREA / AREA_PAGES:

    ./.venv/bin/python3 check_permissions.py

Nó KHÔNG cần server chạy, nên dùng được trước khi restart. Cái nó bắt
được mà mắt thường hay bỏ sót là endpoint quên khai nhóm -- endpoint đó
sẽ bị từ chối với MỌI vai trò, kể cả Chủ.
"""
import admin_gui.serve as s

declared = set(s.GET_PATHS) | set(s.POST_PATHS) | {
    s.IMAGE_UPLOAD_PATH, s.MEDIA_UPLOAD_PATH}
missing = sorted(declared - set(s.PATH_AREA))
stale = sorted(set(s.PATH_AREA) - declared)

if missing:
    print("!! CHƯA PHÂN QUYỀN (mọi vai trò sẽ bị 403):")
    for p in missing:
        print("   ", p)
if stale:
    print("!! PHÂN QUYỀN CHO ENDPOINT KHÔNG TỒN TẠI:")
    for p in stale:
        print("   ", p)
if not missing and not stale:
    print("Mọi endpoint đều đã có nhóm quyền.\n")

# role_areas() đọc database, nên nó hỏng được. Bắt ở đây để công cụ nói
# rõ chuyện gì thay vì bung traceback: người chạy lệnh này thường đang
# kiểm tra phân quyền, và "MySQL không trả lời" là một câu trả lời hữu ích
# cho câu hỏi đó.
try:
    s.permissions.role_areas(s.auth.ROLES[0])
except s.permissions.PermissionReadError as error:
    print(f"!! {error}")
    print("   Không báo cáo được phân quyền thật khi chưa đọc được database.")
    print("   Kiểm tra MySQL rồi chạy lại.")
    raise SystemExit(1)

for role in s.auth.ROLES:
    # role_areas(), not the defaults: this reads the role_permission table
    # too, so it reports what the machine will ACTUALLY do rather than what
    # the source says it would do on a fresh install.
    areas = s.permissions.role_areas(role)
    allowed = sorted(p for p in declared if s.PATH_AREA.get(p) in areas)
    denied = sorted(p for p in declared if s.PATH_AREA.get(p) not in areas)

    default = s.permissions.DEFAULT_ROLE_AREAS.get(role, set())
    mark = "" if (areas - {s.permissions.AREA_SHELL}) == default else "  [đã tuỳ chỉnh]"
    print(f"=== {s.auth.ROLE_LABEL[role]} ({role}) ==={mark}")
    print(f"  nhóm quyền : {', '.join(sorted(areas)) or '(không có)'}")
    print(f"  trang      : {', '.join(s.pages_for_role(role)) or '(không có)'}")
    print(f"  endpoint   : dùng được {len(allowed)}, bị chặn {len(denied)}")
    for p in denied:
        print(f"      chặn  {p}")
    print()
