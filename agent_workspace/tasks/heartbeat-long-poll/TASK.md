# TASK — Online máy suy từ long-poll, bỏ thread heartbeat mù

## Yêu cầu gốc

> commit nhánh hiện tại, lên plan phân công nhiều agent để refactor heartbeat theo hướng:
> Mẫu chung rút ra
> Ở các hệ worker long-poll: lúc rảnh, chính poll là tín hiệu sống; lúc bận, tín hiệu gắn với việc đang làm
> (heartbeat theo task, gia hạn lease), phát ra từ chính công việc. Không hệ nào trong bảng dùng một thread
> heartbeat mù chạy song song với vòng xử lý, vì như vậy treo vẫn báo sống. Cách B là phiên bản tối giản của
> mẫu này: "lệnh đã take < 20 s" thay cho heartbeat theo task, vì mọi lệnh hiện tại đều ngắn.
>
> các agent này dùng sonnet 5.5 med, là được tuy nhiên plan thực thi phải chi tiết và nghiên cứu kỹ lưỡng

## Phạm vi và trạng thái

- Repo `project1_app`. Nhánh thực thi `refactor/heartbeat-long-poll`, tách từ `feature/menu-image-cache` @ `91c8cdd`
  (đã commit nhánh ảnh, tài liệu so sánh và việc xoá stub ngày 10/10/2026).
- Thiết kế nguồn: [docs/heartbeat-vs-long-poll.md](../../../docs/heartbeat-vs-long-poll.md), cách B. Plan này chốt các
  chi tiết còn để ngỏ trong tài liệu đó (mục "Quyết định").
- Trạng thái: **ĐANG LÀM.** User đã chốt U1–U4 ngày 10/10/2026 (mục "Quyết định của user"); Pha 2 và Pha 3 chạy
  cùng một đợt sau cổng G1.
- Kiểm chứng plan: operator đã dựng thử cả 3 pha trên worktree tạm (đã xoá), đo test nào vỡ, lặp lại, chạy 8 kiểu
  sabotage và stress 200 vòng. Số liệu ở mục "Bằng chứng nghiên cứu"; mọi con số ở các cổng bên dưới lấy từ đó.

## Thiết kế chốt

### Định nghĩa

**Online = vòng lệnh của máy còn chạy.** Đây đúng là điều `send()` cần biết trước khi xếp lệnh.

```
is_online(m) =  (LAN_THAY_CUOI[m] có và now − LAN_THAY_CUOI[m] < MACHINE_SEEN_TIMEOUT_SECONDS)     ← rảnh
             or (có lệnh trong DANG_LAM[m] với now − taken_at < COMMAND_TIMEOUT_SECONDS)            ← bận
```

| Trạng thái RAM (trong `machine_transport`) | Ghi khi | Xoá khi |
|---|---|---|
| `LAN_THAY_CUOI = {machine_id: time.time()}` (thay `LAN_HEARTBEAT_CUOI`) | `mark_seen()` trong `poll()` và `send_result()` của `machine_link_process`, ngay sau khi xác minh key, **trước** `take()`/`deliver()` | Không xoá (giống bảng cũ; số khoá ≤ số máy đã đăng ký) |
| `DANG_LAM = {machine_id: {lenh_id: taken_at}}` (mới) | `take()` khi trả một lệnh (đang giữ `CO_LENH`) | `deliver()` khi kết quả đến từ **đúng máy** của lệnh; `send()` trong `finally` (có kết quả hoặc hết giờ) |

Vòng đời: chưa thấy → **rảnh** (poll) → **bận** (take trả lệnh) → **rảnh** (result) ; rảnh → offline khi quá 15 s không
poll/result ; bận → offline khi `send()` hết 20 s mà chưa có kết quả (máy treo) ; offline → rảnh khi máy poll lại.

### Quyết định (plan chốt, operator đã kiểm bằng bản thử)

| Mã | Quyết định | Lý do / bằng chứng |
|---|---|---|
| QĐ1 | **Bỏ điều kiện ① "đếm poll đang mở"** của tài liệu. Thay bằng test bất biến `POLL_WAIT_SECONDS < MACHINE_SEEN_TIMEOUT_SECONDS ≤ COMMAND_TIMEOUT_SECONDS` | `mark_seen` ghi lúc *mở* poll, poll giữ tối đa 8 s < 15 s, nên poll đang mở luôn đã được tính. Bản thử không có ① vẫn bắt được 8/8 sabotage. Nếu sau này tăng `POLL_WAIT_SECONDS` ≥ 15 thì test bất biến đỏ, khi đó mới thêm ① |
| QĐ2 | Không thêm trạng thái `unknown` sau khi server khởi động | Máy poll lại sau ~1 s khi server restart (`main.poll()` ngủ 1 s khi lỗi) |
| QĐ3 | Pha 1 **giữ** route `/machine/heartbeat/send`: vẫn xác minh key (403 khi sai), trả `{da_nhan: true}`, **không ghi gì** | Máy cũ vẫn online nhờ poll; hưởng lợi "treo thì offline" ngay khi nâng server |
| QĐ4 | Không đổi hợp đồng gói tin ở pha 1–2. `GET /app/machine/status/get` vẫn trả `{machine_id, online, last_seen}`; `last_seen` nay là lần poll/result cuối | App chỉ đọc `online` (`app/flutter_app/lib/feature/dashboard/dashboard_controller.dart:119`) |
| QĐ5 | Không làm heartbeat theo lệnh. Thêm test chốt danh sách lệnh máy (`nhan_menu`, `cap_nhat_menu`, `nhan_kho`, `nap_kho`) | Biến giả định "mọi lệnh đều ngắn" thành test: ai thêm lệnh máy mới phải xét thời lượng |
| QĐ6 | Tên mới: `MACHINE_SEEN_TIMEOUT_SECONDS` (thay `HEARTBEAT_TIMEOUT_SECONDS`), `LAN_THAY_CUOI`, `DANG_LAM`, `_finish()`. Giữ `mark_seen`, `last_seen_of`, `is_online` | `machine_list_get.py` đang import `is_online`, `last_seen_of` |
| QĐ7 | Thứ tự nâng: server trước, máy sau | Server mới + máy cũ: chạy. Máy mới + server cũ: mọi lệnh 503 |
| QĐ8 | Không đụng schema DB (`machines.last_seen`, `heartbeat_interval_seconds`) | Không code nào đọc/ghi hai cột này (`server/database/machine/README.md:28-29`) |

### Ngoài phạm vi (ghi lại, không làm trong task này)

- SEC-08: đưa `online`/`last_seen` vào `/app/user/machine/list`, đóng route status công khai (quyết định D8-C).
- SEC-02 (ai có product key giả được máy). Refactor không làm nặng thêm: trước đây key-holder gửi heartbeat, nay gửi poll.
- 7 lỗi test có sẵn không liên quan: `test_machine_bluetooth` (import), `test_server.test_cleanup_callbacks`,
  5 test trong `test_user_login` (`LOGIN_STATES` đã bỏ). SEC-04 đang "expected failure" vì `AttributeError`, không phải
  vì lỗ hổng; cần viết lại ở task login.
- Phát hiện F1 (có sẵn, không do refactor): `/machine/result/send` với `id` không băm được (`[]`, `{}`) làm
  `DANG_CHO.get()` ném `TypeError`, `handle_routes` không bắt, kết nối bị cắt. Chỉ người có key gây ra được.
- Phát hiện F2 (có sẵn): kết quả tới trước khi máy lấy lệnh (chỉ kẻ giữ key làm được, đoán id vì `DEM_LENH` tuần tự)
  thì `send()` trả nhưng lệnh vẫn nằm trong `HOP_THU`, máy vẫn chạy lệnh cũ. Refactor chỉ chặn phần mới sinh ra
  (N1: mục `DANG_LAM` không ai dọn) bằng điều kiện `in DANG_CHO` trong `take()`.
- Trường `busy` trong status; lưu `last_seen` vào DB; lệnh `nhan_anh` phía máy.

## Hợp đồng code Pha 1 (coder làm đúng như dưới, không tự thiết kế)

`server/config/config.py` — đổi dòng 5:

```python
# Máy rảnh: poll hoặc gửi kết quả cuối cách đây dưới chừng này giây thì còn online.
# Phải lớn hơn POLL_WAIT_SECONDS để máy đang treo một poll luôn được tính là online.
MACHINE_SEEN_TIMEOUT_SECONDS = 15
```

`server/lib/machine/machine_transport.py`:

```python
# docstring dòng 1: "...và trạng thái online suy từ long-poll; chỉ nằm trong RAM."
from server.config.config import COMMAND_TIMEOUT_SECONDS, MACHINE_SEEN_TIMEOUT_SECONDS, POLL_WAIT_SECONDS

# machine_id -> time.time() lần cuối máy poll hoặc gửi kết quả (đã xác minh key).
LAN_THAY_CUOI = {}
# machine_id -> {id lệnh: time.time() lúc máy lấy}; chỉ lệnh máy ĐÃ lấy mà send() còn chờ.
# Không suy từ DANG_CHO: send() ghi DANG_CHO trước khi máy lấy lệnh.
DANG_LAM = {}


def mark_seen(machine_id):
    """Gọi sau khi xác minh key, trước take(); không gọi khi đang giữ KHOA (KHOA không reentrant)."""
    with KHOA:
        LAN_THAY_CUOI[machine_id] = time.time()


def last_seen_of(machine_id):
    with KHOA:
        return LAN_THAY_CUOI.get(machine_id)


def is_online(machine_id):
    """Vòng lệnh của máy còn chạy: rảnh (poll/kết quả gần đây) hoặc bận (đang làm lệnh đã lấy)."""
    now = time.time()
    with KHOA:
        last_seen = LAN_THAY_CUOI.get(machine_id)
        taken = list(DANG_LAM.get(machine_id, {}).values())
    if last_seen is not None and now - last_seen < MACHINE_SEEN_TIMEOUT_SECONDS:
        return True
    return any(now - taken_at < COMMAND_TIMEOUT_SECONDS for taken_at in taken)


def _finish(machine_id, lenh_id):
    """Bỏ lệnh khỏi DANG_LAM của đúng máy; gọi khi đang giữ KHOA."""
    lam = DANG_LAM.get(machine_id)
    if lam is None:
        return
    lam.pop(lenh_id, None)
    if not lam:
        del DANG_LAM[machine_id]
```

- `send()`: trong khối `finally: with KHOA:` thêm `_finish(machine_id, lenh["id"])` ngay sau `DANG_CHO.pop(...)`.
  Không đổi gì khác (cổng `is_online`, thông báo lỗi, status 503/502 giữ nguyên).
- `take()`: khi `hop_thu` rỗng trả `None` sớm; khi có lệnh: `lenh = hop_thu.pop(0)`, ghi
  `DANG_LAM.setdefault(machine_id, {})[lenh["id"]] = time.time()` **chỉ khi `lenh["id"] in DANG_CHO`** (comment: máy đã
  lấy, tính là bận tới khi có kết quả hoặc `send()` hết giờ; lệnh không còn `send()` chờ thì không ghi vì không ai dọn),
  rồi `return lenh`. Vẫn nằm trong `with CO_LENH:`. Điều kiện `in DANG_CHO` bổ sung sau review K1 (N1, xem dưới).
- `deliver()`: trong khối `with KHOA:` sẵn có, sau `cho = DANG_CHO.get(lenh_id)` thêm
  `if cho is not None and cho[0] == machine_id: _finish(machine_id, lenh_id)`. Phần còn lại giữ nguyên.
- Luôn đọc hằng số qua tên module (`MACHINE_SEEN_TIMEOUT_SECONDS`, `COMMAND_TIMEOUT_SECONDS`) lúc gọi hàm, không gán vào
  tham số mặc định: test patch các tên này trên module `machine_transport`. Giữ `time.time()` (test thay `machine_transport.time`).

`server/service/machine_link/machine_link_process.py`:

- `heartbeat()`: giữ bước 1 (xác minh key, 403). Bỏ `mark_seen`; comment bước 2:
  `# 2. Giữ route cho máy cũ; online nay suy từ poll và kết quả, không ghi gì ở đây.` Trả `{"da_nhan": True}, 200`.
- `poll()`: sau bước 1 thêm `# 2. Máy đang hỏi lệnh là vòng lệnh còn chạy; ghi trước khi chờ, không ghi lúc trả về.`
  + `mark_seen(machine_id)`; bước long-poll thành `# 3.`. **Không** ghi sau `take()`.
- `send_result()`: sau bước 1 gọi `mark_seen(machine_id)` (kể cả khi `id` không khớp lệnh nào: key đúng nghĩa là máy sống).
- Docstring đầu file: `heartbeat: key → giữ cho máy cũ, không ghi gì`; `poll: key → ghi đã thấy → chờ lệnh`;
  `send_result: key → ghi đã thấy → chuyển kết quả`.

`server/service/dashboard_sync/machinelist_sync/machine_list_get.py`: chỉ sửa docstring dòng 1 và 27 ("trạng thái
online suy từ long-poll", không còn "heartbeat"). Không đổi gói trả về.

## Team, model và cách giao việc

**Mọi agent: Sonnet 5.5, effort medium.** Operator là phiên chính (giữ yêu cầu, tạo worktree, hợp nhất, chạy cổng,
cập nhật bảng tiến độ và vault); operator không viết code sản phẩm.

- Agent tool: `subagent_type: "general-purpose"`, `model: "sonnet"`, `effort: "medium"`, chạy nền. Prompt mở đầu bằng
  vai trong `project1_app/.claude/agents/<vai>.md` (mẫu ở Phụ lục A). Đường dẫn luôn tuyệt đối.
- Hoặc CLI trong `project1_app/`: `claude --agent <vai> --model claude-sonnet-5-5 --effort medium`. File vai `tester`,
  `reviewer`, `cybersecurity` không khai model trong frontmatter, nên **phải truyền rõ** model/effort.
- Python: luôn `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3` (lệnh `python3` trên PATH trỏ vào venv của `project1_server`).
- Chạy test theo **tên module**, không `discover`, khi agent khác đang ghi file test trong cùng cây (tránh nạp file viết dở).
- Agent không commit/push. Operator commit và push nhánh `refactor/heartbeat-long-poll` lên `origin` ở mỗi cổng (U3).

| Agent | Vai | Bước | Được ghi (ngoài danh sách này: chỉ đọc) |
|---|---|---|---|
| T1 | tester | HB-01, HB-03 | `tests/python/test_server.py`, `tests/python/test_server_security.py`, `tests/python/test_machine_menu_image.py`, `tests/python/test_machine_relay.py`, `tests/relay/machine_sim.py`, `tests/tools/menu_crc_stress/harness.py` (chỉ dòng 213) |
| C1 | coder | HB-02 | 4 file trong "Hợp đồng code Pha 1" |
| T2 | tester | HB-05, HB-10b | `tests/python/test_machine_online.py` (mới), `tests/run_tests.py`; HB-10b thêm 3 chỗ test ghi ở bước đó |
| R1 | reviewer | HB-06 | không |
| K1 | cybersecurity | HB-06 | không |
| C2 | coder | HB-07 | `version1.1/machine/main.py`, `version1.1/machine/config/routing.py`, xoá `version1.1/machine/server_connection/machine_server_heartbeat.py`, `tests/tools/menu_crc_stress/harness.py` (dòng 173–192), `tests/relay/machine_sim.py` (docstring dòng 1) |
| D1 | coder (tài liệu) | HB-08 | file trong Phụ lục C |
| R2 | reviewer | HB-09 | không |
| C3 | coder | HB-10a | `server/config/routing.py`, `server/service/machine_link/machine_link_main.py`, `server/service/machine_link/machine_link_process.py` |
| T3 | tester | HB-11 (tuỳ chọn) | chỉ scratchpad, không ghi repo |

Ngoại lệ có chủ đích: C2 được sửa `harness.py` và `machine_sim.py` vì hai file này dựng lại vòng máy thật, phải đổi cùng
lúc với `main.py`, nếu không S12 vỡ ngay (`self.machine.heartbeat` không còn).

## Sơ đồ phụ thuộc

```text
HB-00 operator: nhánh + baseline + commit plan
  └─ HB-01 T1: sửa nền test ──────────── cổng G0 → commit + push
       ├─ HB-02 C1: lõi online server   [worktree lane-c1]  ┐ song song
       └─ HB-03 T1: test cũ "poll trước" [worktree lane-t1] ┘
            └─ HB-04 operator: hợp nhất ── cổng G1a
                 ├─ HB-05 T2: bộ test S13 + sabotage         ┐ song song
                 └─ HB-06 R1 + K1: review Pha 1 (đọc)        ┘ R1 xem tiếp S13 khi HB-05 xong
                      └─ cổng G1 → commit + push "Pha 1"
                           ├─ HB-07 C2: Pha 2 phía máy         [worktree lane-c2]  ┐
                           ├─ HB-10a C3 → HB-10b T2: Pha 3     [worktree lane-p3]  ├ song song (file tách rời)
                           └─ HB-08 D1: tài liệu trạng thái cuối [cây chính]        ┘
                                └─ hợp nhất ── HB-09 R2: review Pha 2 + 3 + tài liệu ── cổng G2 → commit + push
                                     ├─ HB-11 T3: đo tải lúc rảnh (tuỳ chọn)
                                     └─ HB-12 operator: vault, dọn worktree
```

## Các bước

Số dòng tính tại commit `91c8cdd`. Nếu lệch, agent tìm theo nội dung trích dẫn, không theo số dòng.

### HB-00 — Chuẩn bị (operator)

1. `git -C /home/abel/project/internproj/project1_app switch -c refactor/heartbeat-long-poll` (từ `91c8cdd`, cây sạch).
2. Baseline: `cd project1_app && PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -m unittest discover -s tests/python -t .`
   → kỳ vọng `Ran 70 tests`, `FAILED (failures=1, errors=25)`. Lưu tóm tắt vào bảng tiến độ.

### HB-01 — Sửa nền test (T1)

Mục đích: các test chạm cổng máy đang lỗi vì code đã đổi trước đây; phải chạy được thì mới có lưới an toàn.

| File | Sửa |
|---|---|
| `tests/python/test_server_security.py:41` và `:47` | Xoá `user_login_process.LOGIN_STATES.clear()` và `self.addCleanup(user_login_process.LOGIN_STATES.clear)`. Giữ import `user_login_process` (SEC-04 còn dùng) |
| `tests/python/test_machine_relay.py:23` | `MACHINE_DIR = Path(__file__).resolve().parents[2] / "version1.1" / "machine"` (thư mục `machine/` ở gốc chỉ còn `__pycache__`) |
| `tests/relay/machine_sim.py:23` | `MACHINE_DIR = ROOT / "version1.1" / "machine"` (cùng lý do; E2E bước E3 dùng file này) |
| `tests/python/test_server.py:57` | Bỏ `'/app/user/session/verify'` khỏi tuple (route đã bỏ khi login thành 1 bước) |

Kiểm (cổng **G0**): `discover` → `Ran 70 tests`, `FAILED (errors=7, expected failures=6)`, **không có** `failures=`.
7 lỗi đúng tên: `test_machine_bluetooth` (loader), `test_cleanup_callbacks`, và 5 test của `LoginFlowTest`. Expected
failures: SEC-02, 03, 04, 05, 08, 14. Rollback: `git checkout -- <4 file>`.

Sau G0, operator tạo hai lane cho bước song song:
1. Commit `Repair stale tests that touch the machine link` (U3). Không được commit thì thay bước 2 bằng
   `git diff | git -C <lane> apply` cho từng lane.
2. `git worktree add --detach <scratch>/lane-c1 HEAD` và `git worktree add --detach <scratch>/lane-t1 HEAD`
   (`<scratch>` là scratchpad của phiên thực thi). Mỗi lane chỉ một agent.

### HB-02 — Lõi online phía server (C1, worktree `lane-c1`)

Làm đúng "Hợp đồng code Pha 1". Không sửa gì dưới `tests/`.

Lane check (trên test cũ sau HB-01, chứng minh ngữ nghĩa đã đổi): `discover` → `Ran 70 tests`,
`FAILED (failures=2, errors=9, expected failures=4, unexpected successes=2)`:
- failures: `test_services_share_one_port` (`online` False), `test_timed_out_command_is_not_run_or_answered_later` (503 thay vì 502);
- errors mới: `test_relay_checks_login_owner_and_product_key` (`IndexError`), `test_machine_cannot_answer_for_another_machine` (`TypeError`);
- unexpected successes: SEC-02, SEC-08.
- `test_waiting_app_does_not_block_machine` và `test_image_command_round_trip` có thể đỏ hoặc xanh tuỳ đua luồng; đó là
  lý do HB-03 tồn tại, không phải lỗi của C1.

Thêm: `/usr/bin/python3 -m py_compile` 4 file; `grep -n "mark_seen" server -r` chỉ còn định nghĩa và 2 lời gọi trong
`machine_link_process.py` (`poll`, `send_result`). Bàn giao: diff, output lane check, giới hạn.

### HB-03 — Test cũ đổi sang "poll trước" (T1, worktree `lane-t1`)

Nguyên tắc: test nào gửi heartbeat để làm máy online thì đổi thành một lần poll **chặn** (`/machine/command/poll`, cùng
key) trước request của app. Không xoá assertion, không nới giá trị mong đợi.

| File:dòng | Từ → thành |
|---|---|
| `test_server.py:78` | `status, _ = self.request('/machine/heartbeat/send', {'product_key': 'test-key'})` → `'/machine/command/poll'` (vẫn kiểm `status == 200`) |
| `test_server.py:99, 123, 160, 184` | `self.request('/machine/heartbeat/send', {'product_key': 'relay-key'})` → `'/machine/command/poll'` |
| `test_server.py:152` | **Giữ** (route heartbeat còn ở Pha 1, key sai vẫn 403) |
| `test_server.py:154` | Comment: `# Máy chưa poll lần nào thì báo offline ngay, không để app chờ.` |
| `test_server.py:195` | Comment: `# Máy đã poll (online) nhưng chưa lấy lệnh: hết giờ thì hủy, online lại không nạp kho lần nữa.` |
| `test_server_security.py:168, 190, 294` | `self.post("/machine/heartbeat/send", {"product_key": "fm_tem_may_that"})` → `"/machine/command/poll"` |
| `test_server_security.py:187` | Comment: `# Kẻ tấn công chỉ có key trên tem: hỏi lệnh như máy thật (poll làm máy online).` |
| `test_server_security.py:262` | **Giữ** ở Pha 1 |
| `test_machine_menu_image.py:56` | `self.request("/machine/heartbeat/send", {"product_key": KEY})` → `"/machine/command/poll"` |
| `test_machine_relay.py:4, 125, 134` | Chữ "heartbeat" → "poll"/"online" (docstring, comment, thông báo `fail`) |
| `harness.py:213` | `"Máy không online (chưa poll được) trong thời gian chờ"` |

SEC-02 và SEC-08 **giữ** `@unittest.expectedFailure`: sau đổi, kẻ giữ key poll làm máy online rồi vẫn lấy được lệnh
(SEC-02), và `last_seen` vẫn lộ (SEC-08), nên lỗ hổng vẫn được chứng minh.

Lane check (trên server **cũ**, chứng minh test không còn dựa vào heartbeat): `discover` → `Ran 70 tests`,
`FAILED (failures=4, errors=10, expected failures=4, unexpected successes=2)`; failures:
`test_image_command_round_trip`, `test_long_poll_returns_as_soon_as_command_arrives`, `test_services_share_one_port`,
`test_timed_out_command_is_not_run_or_answered_later`; errors mới: `test_relay_checks_login_owner_and_product_key`,
`test_waiting_app_does_not_block_machine`, `test_machine_cannot_answer_for_another_machine`.

### HB-04 — Hợp nhất lane (operator)

1. Trong mỗi lane: `git -C <lane> add -A && git -C <lane> diff --cached --binary > <scratch>/<lane>.patch`.
2. Trên nhánh: `git apply --index lane-c1.patch lane-t1.patch` (hai patch không chung file; trùng file là lỗi giao việc).
3. Cổng **G1a**: `discover` → `Ran 70 tests`, `FAILED (errors=7, expected failures=6)`. Lặp 3 lần
   `unittest tests.python.test_server tests.python.test_machine_menu_image tests.python.test_server_security tests.python.test_machine_relay`
   → mỗi lần `Ran 28 tests`, `FAILED (errors=1, expected failures=6)`, lỗi duy nhất là `test_cleanup_callbacks`.
   Đỏ khác → ✗, trả lane liên quan.

### HB-05 — Bộ test S13 `test_machine_online.py` (T2)

Tạo `tests/python/test_machine_online.py`, đăng ký trong `tests/run_tests.py` ngay sau S12:
`("S13", "py", "Online suy từ long-poll: rảnh/bận/treo, lệnh chưa lấy, không deadlock", "tests.python.test_machine_online")`.

Khung bắt buộc (không dùng `sleep` để chờ, theo `CODE_STYLE.md` §4):
- Server thật cổng 0, SQLite tạm, `rate_limit.MAX_REQUESTS` nâng cao, như `test_machine_menu_image.py`.
- **Đồng hồ giả** chỉ cho giờ "đã thấy"/"đã lấy":
  `patch.object(relay, "time", types.SimpleNamespace(time=clock.time))` với `relay = server.lib.machine.machine_transport`.
  Chờ long-poll và chờ kết quả vẫn là thời gian thật, rút ngắn bằng patch.
- Patch trên module `relay`: `POLL_WAIT_SECONDS=0.2`, `MACHINE_SEEN_TIMEOUT_SECONDS=15`, `COMMAND_TIMEOUT_SECONDS=20`;
  test cần `send()` hết giờ thật thì patch riêng `COMMAND_TIMEOUT_SECONDS=1` trong test đó.
- Tiện ích: `online()` đọc `/app/machine/status/get`; `poll()`; `take()` poll tới khi có lệnh (≤ 50 lần);
  `ask_app()` gửi `/app/machine/ingredient/get`; `wait_queued()` chờ lệnh vào `HOP_THU` bằng `threading.Event().wait(0.02)`.

| Test | Kịch bản | Kỳ vọng |
|---|---|---|
| `test_poll_wait_shorter_than_seen_window` | Đọc `server.config.config` | `POLL_WAIT < MACHINE_SEEN_TIMEOUT ≤ COMMAND_TIMEOUT` (QĐ1) |
| `test_machine_commands_are_known_short_commands` | `ast` đọc `version1.1/machine/*/machine_*_request.py`, lấy key của dict `COMMANDS` | Đúng `{"nhan_menu", "cap_nhat_menu", "nhan_kho", "nap_kho"}`; thông báo lỗi chỉ tới mục 6 tài liệu (QĐ5) |
| `test_heartbeat_alone_is_not_online` | POST heartbeat key đúng | `(200, {"da_nhan": True})`, `online` False, app nhận `(503, {"loi": "Máy đang offline"})` (QĐ3) |
| `test_poll_marks_online_until_seen_window_ends` | poll; tiến đồng hồ 14 s; rồi thêm 2 s | trước poll False; sau 14 s True; sau 16 s False |
| `test_result_marks_online` | `/machine/result/send` key đúng, `id` không tồn tại | `online` True |
| `test_online_counts_from_poll_start_not_poll_end` | Bọc `machine_link_process.take` (patch.object trên module process) để tiến đồng hồ 16 s rồi gọi `take` thật; poll | poll trả `None`; sau đó `online` False |
| `test_queued_untaken_command_does_not_keep_machine_online` | poll; `COMMAND_TIMEOUT=1`; app gửi; `wait_queued()`; tiến 16 s | `online` False dù lệnh nằm trong `DANG_CHO`; app nhận `(502, {"loi": "Máy không phản hồi, lệnh đã được hủy"})` |
| `test_busy_machine_stays_online_while_running_taken_command` | poll; app gửi; `take()`; tiến 16 s | `online` True; gửi kết quả → app `(200, {"ok": 1})`; `machine_id` không còn trong `DANG_LAM` |
| `test_taken_command_older_than_command_timeout_is_not_busy` | như trên nhưng tiến 21 s | `online` False; gửi kết quả vẫn trả app 200 |
| `test_hung_command_loop_goes_offline_and_next_command_fails_fast` | `COMMAND_TIMEOUT=1`; poll; app; `take()`; không trả | app `(502, {"loi": "Máy chưa trả kết quả, hãy tải lại để kiểm tra"})`; `DANG_LAM` sạch; tiến 16 s → `online` False; app kế tiếp `(503, {"loi": "Máy đang offline"})` |
| `test_other_machine_result_does_not_end_busy_state` | Máy thứ hai (key khác) gửi result với `id` lệnh của máy một; tiến 16 s | máy một vẫn True; máy hai False; kết quả thật → app `(200, ...)` |
| `test_parallel_polls_and_sends_do_not_deadlock` | 2 luồng máy poll/trả liên tục; 8 luồng app gửi 40 request | 40 lần status 200; `DANG_LAM` và `HOP_THU` của máy rỗng |

Khung cho test khó nhất (thứ tự ghi "đã thấy"):

```python
real_take = machine_link_process.take

def take_while_clock_runs(machine_id):
    self.clock.advance(SEEN + 1)        # đồng hồ trôi khi server còn giữ poll
    return real_take(machine_id)

with patch.object(machine_link_process, "take", take_while_clock_runs):
    self.assertIsNone(self.poll())
self.assertFalse(self.online())          # online tính từ lúc máy gọi, không từ lúc server trả về
```

Sabotage bắt buộc (Phụ lục B), chạy trên **worktree tạm** (`git worktree add --detach <scratch>/sab HEAD` rồi chép cây
hiện tại vào), không bao giờ sửa code sản phẩm trong cây chính. Mỗi kiểu phải làm ít nhất một test S13 đỏ; báo bảng
kiểu → test đỏ. Kiểm: `unittest tests.python.test_machine_online -v` 2 lần liền → `Ran 12 tests ... OK` (khoảng 10 s).

### HB-06 — Review Pha 1 (R1 reviewer, K1 cybersecurity; chỉ đọc)

R1 kiểm diff HB-01..HB-03 (song song HB-05), rồi được operator gửi tiếp (SendMessage) để kiểm S13. Checklist ngoài mục 5
`CODE_STYLE.md`:
1. `mark_seen` không bao giờ được gọi khi đang giữ `KHOA` (chỉ ở `poll()`/`send_result()` của process, ngoài khoá).
2. `take()` chỉ ghi `DANG_LAM` khi thật sự trả lệnh, trong `with CO_LENH`.
3. `deliver()` chỉ xoá `DANG_LAM[machine_id]` của **người gửi** và chỉ khi `cho[0] == machine_id`.
4. `send()` xoá `DANG_LAM` trong cùng khối khoá với `DANG_CHO.pop`, ở `finally`.
5. `is_online` đọc hai bảng trong một lần giữ khoá; so với hằng số module (patch được).
6. Gói trả về mọi route không đổi: poll `{lenh}`, result/heartbeat `{da_nhan}`, status `{machine_id, online, last_seen}`; mã 403/400/503/502 giữ nguyên.
7. `server/lib` không import `server.service`.
8. Test: không assertion nào bị xoá hay nới; SEC-02/08 vẫn chứng minh lỗ hổng; S13 không dùng `sleep`, giá trị mong đợi viết cứng.
9. Chạy lại cổng G1 bằng lệnh mới (không tin output của coder/tester).

K1 kiểm: race giữa `send`/`take`/`deliver` (thứ tự khoá, lệnh bị lấy đúng lúc `send` hết giờ), giới hạn bộ nhớ
(`LAN_THAY_CUOI` chỉ có khoá sau xác minh key; `DANG_LAM` dọn trong `finally`), máy khác không gỡ được trạng thái bận,
SEC-02 không nặng thêm. Ghi F1 là có sẵn. Mức theo `CODE_STYLE.md` §6.

Cổng **G1**: R1 và K1 không còn mục "Chặn"; `discover` → `Ran 83 tests` (82 + test N1), `FAILED (errors=7, expected failures=6)`;
`python -m tests.tools.menu_crc_stress --iterations 300 --seed 42` → `KẾT QUẢ: PASS`. Operator commit
`Derive machine online state from long-poll (phase 1)`.

### HB-07 — Pha 2: bỏ thread heartbeat phía máy (C2, worktree `lane-c2`)

User cho sửa `version1.1/machine` (U1, 10/10/2026).

| File | Sửa |
|---|---|
| `version1.1/machine/main.py` | Bỏ `import threading` (dòng 7) và `machine_server_heartbeat as heartbeat` ở dòng 12 (giữ `machine_server_request`). Dòng 55–56 thay bằng comment: `# Không có thread heartbeat: server suy online từ chính poll và kết quả của vòng này,` / `# nên vòng treo thì máy hiện offline (docs/heartbeat-vs-long-poll.md).` |
| `version1.1/machine/config/routing.py` | Docstring: `"""Đường dẫn API mà machine gọi lên server."""`; xoá `MACHINE_HEARTBEAT_SEND` và `HEARTBEAT_INTERVAL_SECONDS` |
| `version1.1/machine/server_connection/machine_server_heartbeat.py` | `git rm` |
| `tests/tools/menu_crc_stress/harness.py:173-192` | Chỉ bọc `poll`; bỏ `hb`, `run_heartbeat` và `self.machine.heartbeat = ...`. Comment: `# main.run() là vòng while True không có cờ dừng: bọc poll() để ném _Stop khi stop() bật cờ, ...`. Giữ `import types` (còn dùng ở `fake_database`) |
| `tests/relay/machine_sim.py:1` | `(heartbeat, nhận lệnh, trả kết quả)` → `(poll nhận lệnh, trả kết quả)` |

Kiểm: `grep -rn -i heartbeat version1.1/machine tests/tools` chỉ còn 2 dòng comment ở `main.py`;
`unittest tests.python.test_machine_relay tests.python.test_menu_crc_stress tests.python.test_machine_online` → OK;
stress 300 vòng seed 42 → PASS; `discover` → `Ran 82 tests`, `FAILED (errors=7, expected failures=6)` (trong lane,
chưa có Pha 3). Rollback: `git checkout -- version1.1/machine tests/tools tests/relay`.

### HB-08 — Tài liệu (D1, cây chính, song song HB-07 và HB-10)

Cập nhật mọi tài liệu **hiện trạng** trong Phụ lục C cho đúng trạng thái cuối (sau Pha 2 và Pha 3): online suy từ
poll/result/lệnh đã lấy; máy không còn thread heartbeat; route `/machine/heartbeat/send` đã bỏ (gọi vào trả 404). Giữ nguyên phong cách từng file (HTML giữ CSS, bố cục,
sơ đồ; chỉ sửa chữ và nhãn). Không tạo file mới. Không sửa `agent_workspace/tasks/middleware/**` (plan tương lai, ghi
heartbeat như baseline cũ) và `version1.1/store_gui`, `version1.1/test_gui` (chữ "heartbeat" ở đó là việc khác).

Riêng `docs/heartbeat-vs-long-poll.md` và `docs/research/heartbeat-vs-long-poll.html`: thêm mục "Trạng thái triển khai"
(cả 3 pha đã làm ngày 10/10/2026), ghi QĐ1 (bỏ ①) và QĐ5; sửa link HTML gãy ở dòng 4 của bản `.md`
(`heartbeat-vs-long-poll.html` → `research/heartbeat-vs-long-poll.html`). `log/TIEU_CHI_TEST.md`: thêm dòng S13, sửa S8.

Kiểm: `grep -rn -i heartbeat <file Phụ lục C>` chỉ còn câu nói route cũ/tương thích/lịch sử; mở HTML đã sửa bằng
`google-chrome --headless=new --screenshot` ở 1280 px để chắc không vỡ bố cục. Bàn giao danh sách file + số dòng đổi.

### HB-09 — Review Pha 2 + Pha 3 + tài liệu (R2, chỉ đọc)

Operator hợp nhất `lane-c2.patch` và `lane-p3.patch` vào cây chính (đã có tài liệu của D1) rồi giao R2. Như HB-06
mục 6–9, thêm: tài liệu khớp code thật (route, tên hằng, ngưỡng 15/20/8 s), không còn mô tả "thread heartbeat mỗi 5 s"
hay route heartbeat như hiện trạng. Cổng **G2**: R2 không còn "Chặn"; `discover` → `Ran 82 tests`,
`FAILED (errors=7, expected failures=6)` (83 test); stress 300 vòng PASS;
`grep -rn "heartbeat/send\|HEARTBEAT" server version1.1/machine tests --include=*.py` chỉ còn assertion 404.
Operator commit + push `Remove machine heartbeat thread and heartbeat route (phases 2-3)`.

### HB-10 — Pha 3: xoá route heartbeat (worktree `lane-p3`)

User chọn xoá ngay (U2). Máy còn chạy code cũ gặp 404 không crash, chỉ in log mỗi 5 s (`HTTPError` là lớp con của
`URLError`, bị bắt ở `machine_server_heartbeat.py:29`).

HB-10a (C3):
- `server/config/routing.py:41-42`: xoá `MACHINE_HEARTBEAT_SEND`; comment nhóm thành `# Cổng máy — long-poll nhận lệnh và trả kết quả`.
- `machine_link_main.py`: bỏ dòng docstring heartbeat, import `MACHINE_HEARTBEAT_SEND`, import `heartbeat`, mục trong `ROUTES`.
- `machine_link_process.py`: xoá hàm `heartbeat()` và dòng docstring tương ứng.

Lane check C3: `py_compile` 3 file; `unittest tests.python.test_server_modules` OK (không trùng route).

HB-10b (T2, sau C3 trong cùng lane):
- `test_server.py:152`: `'/machine/heartbeat/send'` key sai → `'/machine/command/poll'` key `'sai-key'` vẫn 403; thêm ngay sau:
  `self.assertEqual(self.request('/machine/heartbeat/send', {'product_key': 'relay-key'})[0], 404)`.
- `test_server_security.py:262`: `"/machine/heartbeat/send"` → `"/machine/command/poll"` (vẫn phải 400 với surrogate lẻ).
- `test_machine_online.py`: thay `test_heartbeat_alone_is_not_online` bằng `test_heartbeat_route_is_gone` (POST → 404, `online` False).

Lane check T2 (trong `lane-p3`, đã có C3, chưa có Pha 2): `unittest tests.python.test_server tests.python.test_server_security
tests.python.test_machine_online` → chỉ `test_cleanup_callbacks` lỗi, 6 expected failures. Review gộp vào HB-09.

### HB-11 — Đo tải lúc rảnh (T3, tuỳ chọn)

Biến ước lượng 0,325 → 0,125 req/s/máy thành số đo. Hai worktree tạm: `91c8cdd` (trước) và nhánh sau G2. Mỗi bên chạy
server thật (`POLL_WAIT_SECONDS` mặc định 8) + vòng máy thật như `test_machine_relay` trong 120 s không có lệnh; đếm dòng
log request theo path. Báo req/s mỗi path, tổng, và chênh lệch. Không ghi gì vào repo.

### HB-12 — Đóng task (operator)

Gỡ mọi worktree (`git worktree list` chỉ còn cây chính). Vault: `STATUS.md` (hàng "Trạng thái online máy" + nhật ký),
`ARCHITECTURE.md` (dòng 65, 71, 73, 86, 115), báo cáo lượt chạy vào `archive/heartbeat-refactor-<ngày>/` + một dòng
`archive/README.md`. Cập nhật bảng tiến độ dưới đây.

## Quyết định của user (10/10/2026)

| # | Câu hỏi | User chốt |
|---|---|---|
| U1 | Sửa phía máy `version1.1/machine` (HB-07) | Có, theo đề xuất |
| U2 | Xoá route heartbeat (HB-10) | Xoá ngay, cùng đợt với Pha 2 |
| U3 | Commit ở mỗi cổng | Commit và push |
| U4 | QĐ1: bỏ bộ đếm poll đang mở | Có |

## Tiến độ từng bước

| ID | Phụ thuộc | Agent | Trạng thái + bằng chứng |
|---|---|---|---|
| HB-00 | — | operator | ✓ 10/10: nhánh `refactor/heartbeat-long-poll`, plan commit `3994f09`; baseline `91c8cdd` 70 test, failures=1, errors=25. Push lỗi: máy chưa có credential GitHub |
| HB-01 | HB-00 | T1 | ✓ 10/10: 4 file đúng bảng; operator chạy lại G0: 70 test, `errors=7, expected failures=6`, không failure |
| HB-02 | HB-01 | C1 | ✓ 10/10: lane check khớp (70 test, failures=2, errors=9, xfail=4, unexpected=2); `machine_transport.py`, `config.py` trùng từng byte bản thử của operator |
| HB-03 | HB-01 | T1 | ✓ 10/10: lane check trên server cũ khớp (failures=4, errors=10, xfail=4, unexpected=2) |
| HB-04 | HB-02, HB-03 | operator | ✓ 10/10: G1a 70 test `errors=7, expected failures=6`; lặp 3 lần nhóm S1/S11/X1/S8: chỉ `test_cleanup_callbacks` |
| HB-05 | HB-04 | T2 | ✓ 10/10: 13 test (12 theo bảng + `test_result_before_take_leaves_no_busy_entry` cho N1), OK ×2 (~10 s); sabotage 1–9 đều đỏ đúng test. ⚠ Bản đầu chép từ file tham chiếu operator để lộ trong scratchpad (đã xoá); R1 soi kỹ, đạt |
| HB-06 | HB-04, HB-05 | R1, K1 | ✓ 10/10: R1 Pha 1 + S13 + N1 không Chặn/Nên sửa (3 gợi ý: nâng timeout 1 s nếu flaky, assert `last_seen` None ở test heartbeat → đưa vào HB-10b, `patch.stopall`). K1 N1 đã sửa, F1/F2 có sẵn ghi ngoài phạm vi. G1: 83 test `errors=7, expected failures=6`; stress 300 vòng PASS |
| HB-07 | HB-04 | C2 | → lane-c2 đạt: grep chỉ còn 2 comment, S8+S12 OK, stress 300 vòng PASS (208 menu, 0 va chạm), discover 70 `errors=7, xfail=6`. Chờ hợp nhất sau G1 |
| HB-08 | thiết kế chốt | D1 | → chờ review R2: 19 file Phụ lục C (operator mở sớm cùng HB-02/03; commit sau G2) |
| HB-09 | HB-07, HB-08, HB-10 | R2 | ○ |
| HB-10 | HB-04 | C3, T2 | → HB-10a lane-p3 đạt (70 test: đúng 2 failure chờ HB-10b). HB-10b làm ở cây chính sau hợp nhất |
| HB-11 | G2 | T3 | ○ tuỳ chọn |
| HB-12 | G2 | operator | ○ |

Ký hiệu theo `agent_workspace/TEAM.md`: ○ chưa làm, → đang làm, ✓ đạt (có bằng chứng), ✗ lỗi (ghi nguyên nhân), ⏸ chờ.

## Tiêu chí nghiệm thu

| Mã | Điều kiện → kết quả cần thấy | Kiểm |
|---|---|---|
| TC1 | Máy treo vòng lệnh (đã lấy lệnh, không poll, không trả) → offline sau khi `send()` hết giờ; lệnh sau nhận 503 ngay | S13 `test_hung_command_loop_goes_offline_and_next_command_fails_fast` |
| TC2 | Máy đang chạy lệnh đã lấy (< 20 s) vẫn online dù không poll | S13 `test_busy_machine_stays_online_while_running_taken_command` |
| TC3 | Lệnh xếp hàng mà máy chưa lấy không làm máy online | S13 `test_queued_untaken_command_does_not_keep_machine_online` |
| TC4 | Heartbeat không còn là tín hiệu sống (Pha 1), route bị xoá (Pha 3) | S13 heartbeat test; `test_server` 404 |
| TC5 | Không deadlock khi poll/send/deliver song song | S13 `test_parallel_polls_and_sends_do_not_deadlock` |
| TC6 | Không hồi quy: chỉ còn 7 lỗi có sẵn, 6 expected failure, 0 failure, 0 unexpected success | `discover` ở G1/G2 |
| TC7 | Vòng máy thật không có thread heartbeat vẫn phục vụ Menu/Kho | S8, S12 300 vòng PASS |
| TC8 | Test bắt được lỗi thật | 8/8 sabotage Phụ lục B làm S13 đỏ |
| TC9 | Tài liệu hiện trạng khớp code | R2 + grep Phụ lục C |

## Rủi ro và cách xử lý

| Rủi ro | Dấu hiệu | Xử lý |
|---|---|---|
| Gọi `mark_seen` trong lúc giữ `KHOA` → treo | Test S13 song song quá 10 s, request timeout | R1 mục 1; khoá không reentrant |
| Test đua luồng khi còn sót heartbeat trong test | `test_waiting_app...`, S11 lúc xanh lúc đỏ | HB-03 đổi sang poll **chặn** trước request app; G1a lặp 3 lần |
| Agent làm lệch số dòng | Patch áp sai chỗ | Tìm theo nội dung trích dẫn; operator `git diff --stat` khớp bảng quyền ghi |
| Deploy máy mới trước server | Mọi lệnh 503 | QĐ7; ghi trong tài liệu triển khai |
| Có lệnh máy mới dài hơn 20 s | `test_machine_commands_are_known_short_commands` đỏ | Đo thời lượng; dài thì làm heartbeat theo lệnh (`{id, tien_do}`), không quay lại thread mù |

## Bằng chứng nghiên cứu (operator, 10/10/2026, worktree tạm đã xoá)

| Trạng thái thử | Kết quả `discover` |
|---|---|
| HEAD `91c8cdd` | 70 test, `failures=1, errors=25` |
| + HB-01 | 70, `errors=7, expected failures=6` |
| + HB-02 (test cũ) | 70, `failures=2, errors=9, expected failures=4, unexpected successes=2` |
| HB-01 + HB-03 trên server cũ | 70, `failures=4, errors=10, expected failures=4, unexpected successes=2` |
| HB-01..HB-05 | 82, `errors=7, expected failures=6`; nhóm S1/S11/X1/S13/S8 lặp 2 lần ổn định |
| + Pha 2 | S8, S12, S13 OK; stress 200 vòng seed 42 PASS (138 menu khác nhau, 0 va chạm CRC) |
| + Pha 3 | toàn suite chỉ còn 7 lỗi có sẵn |
| Sabotage 8 kiểu trên S13 | 8/8 làm ít nhất một test đỏ (Phụ lục B) |

Bản thử lưu ở vault `projects/internproj/project1_app/archive/heartbeat-plan-2026-10-10/`, **chỉ operator dùng** để
đối chiếu khi review; không đưa cho coder/tester để hai bản làm độc lập.

## Phụ lục A — Mẫu prompt giao việc

```text
Bạn là <vai> (Sonnet 5.5, effort medium) trong repo /home/abel/project/internproj/project1_app.
Đọc trước: .claude/agents/<vai>.md, agent_workspace/CODE_STYLE.md, AGENTS.md,
agent_workspace/tasks/heartbeat-long-poll/TASK.md (mục "Thiết kế chốt", "Hợp đồng code Pha 1" và bước <ID>).
Thư mục làm việc: <cây chính | worktree lane>.
Bước: <ID>. Chỉ được ghi: <danh sách file từ bảng Team>. Mọi file khác chỉ đọc.
Không commit, không push, không sửa ngoài danh sách. Plan thiếu hoặc mâu thuẫn với code: dừng và báo, không tự đoán.
Python: PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3. Chạy test theo tên module.
Xong thì báo: (1) file và tóm tắt diff; (2) từng lệnh kiểm, output rút gọn và exit code, so với kỳ vọng ghi trong bước;
(3) điều chưa làm hoặc còn nghi ngờ. Chỉ nói ĐẠT khi output vừa chạy chứng minh.
```

Reviewer/cybersecurity thêm: "Chỉ đọc. Không sửa file. Báo theo mức Chặn/Nên sửa/Gợi ý, mỗi mục có file:dòng, kịch bản
và phép kiểm lại." Operator chạy `git status --short` trước/sau để chắc reviewer không ghi gì.

## Phụ lục B — Sabotage cho S13

Mỗi kiểu sửa một chỗ trong bản sao tạm, chạy S13, khôi phục.

| # | Sabotage | Test phải đỏ |
|---|---|---|
| 1 | `is_online` coi lệnh trong `DANG_CHO` là bận | `test_queued_untaken...`, `test_taken_command_older...` |
| 2 | `take()` không ghi `DANG_LAM` | `test_busy_machine...`, `test_other_machine_result...` |
| 3 | `heartbeat()` vẫn gọi `mark_seen` | `test_heartbeat_alone_is_not_online` |
| 4 | `deliver()` xoá `DANG_LAM` không kiểm máy | `test_other_machine_result...` |
| 5 | `send()` không `_finish` khi hết giờ | `test_hung_command_loop...` |
| 6 | `poll()` ghi `mark_seen` sau `take()` | `test_online_counts_from_poll_start_not_poll_end` |
| 7 | Bỏ giới hạn tuổi lệnh đã lấy (`return bool(taken)`) | `test_taken_command_older...` |
| 8 | `send_result()` không gọi `mark_seen` | `test_result_marks_online` |

## Phụ lục C — Tài liệu hiện trạng cần sửa (HB-08)

Số dòng có chữ "heartbeat" tại `91c8cdd`:

| File | Dòng |
|---|---|
| `server/service/machine_link/README.md` | 1, 11, 19, 23, 24, 74, 81, 82, 91, 94, 100 (bỏ hàng route heartbeat; viết lại mục "A. Duy trì kết nối"; câu "Hỏi lệnh và gửi kết quả không cập nhật heartbeat" nay ngược lại) |
| `server/service/machine_link/LINK_FLOW.html` | 2, 29, 31, 32, 34, 35 |
| `server/service/dashboard_sync/machinelist_sync/README.md` | 3, 16, 31, 36, 72, 88, 118 |
| `server/service/dashboard_sync/machinelist_sync/MACHINELIST_FLOW.html` | 29, 31, 32, 34, 38, 41 |
| `server/service/dashboard_sync/README.md` | 12, 33, 38, 106, 154 |
| `server/service/dashboard_sync/DASHBOARD_SYNC_FLOW.html` | 31, 32 |
| `server/service/dashboard_sync/menu_sync/MENU_SYNC_FLOW.html` | 39 |
| `server/lib/README.md` | 16 |
| `server/START.md` | 24 |
| `server/database/machine/README.md` | 21, 22, 28, 29 (giữ mô tả cột; nói rõ online không dùng DB, QĐ8) |
| `server/service/machine_register/README.md` | 90 |
| `docs/FlexMix_System_Manual.html` | 41, 43, 97, 105, 145, 158, 171, 174, 188, 197, 202 |
| `docs/dong-bo-du-lieu.html` | 343, 385 |
| `MODULE_PATTERN.md` | 44 (bỏ `heartbeat` khỏi danh sách mục tiêu), 74 (bỏ hàng `MACHINE_HEARTBEAT_SEND`), 122 (bỏ hàng hậu tố `heartbeat`), 158, 171, 240 |
| `AGENTS.md` | 81, 92 (chỉ đổi chữ "heartbeat" thành "trạng thái online"; không đổi quy ước khác) |
| `log/SECURITY_NOTES.md` | 36, 44, 51 (SEC-02: kẻ giữ key giả máy bằng poll) |
| `log/TIEU_CHI_TEST.md` | 43 (S8), thêm S13 |
| `docs/heartbeat-vs-long-poll.md`, `docs/research/heartbeat-vs-long-poll.html` | Mục "Trạng thái triển khai", QĐ1, QĐ5, sửa link |
