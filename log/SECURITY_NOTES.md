# Ghi chú bảo mật — androidv0.1

Các kịch bản tấn công vào luồng hiện có. **Chưa sửa mục nào** (cần anh/chị quyết định vì đụng tới
logic/flow). Mục có test: `server/test_security.py` (luồng **X1** trong `.\test.ps1`). Lỗ hổng còn mở
đang là `@unittest.expectedFailure`. Khi sửa xong, test báo "unexpected success": bỏ decorator và
chuyển mục xuống phần "Đã đóng".

Mức: **Cao** = mất quyền điều khiển máy hoặc tài khoản; **TB** = gián đoạn dịch vụ hoặc lộ thông tin;
**Thấp** = cần điều kiện khó hoặc tác hại nhỏ.

| Mã | Mức | Tóm tắt | Test |
| --- | --- | --- | --- |
| SEC-01 | Cao | Toàn bộ HTTP không mã hóa: mật khẩu, token, product key đi dạng rõ | – |
| SEC-02 | Cao | Ai có product key (chụp tem QR) giả được máy, cướp lệnh của chủ và trả kết quả giả | X1 ✔ |
| SEC-03 | TB | Bảng giới hạn IP đầy 1000 thì mọi IP mới bị chặn đăng nhập/đăng ký | X1 ✔ |
| SEC-04 | TB | Lấp đầy 1000 phiên đăng nhập chờ thì người thật bị "Server đang bận" | X1 ✔ |
| SEC-05 | TB | Đăng ký báo "Email/Tên đăng nhập đã tồn tại": dò được ai có tài khoản | X1 ✔ |
| SEC-06 | TB | Gói đồng bộ gzip từ máy không giới hạn kích thước giải nén (bom gzip làm app hết RAM) | X1 ✔ |
| SEC-08 | Thấp | `/machine/trang-thai` không cần đăng nhập | X1 ✔ |
| SEC-09 | Cao | Máy đang ở chế độ pair Bluetooth trao product key cho bất kỳ thiết bị nào kết nối | – |
| SEC-10 | TB | Chia sẻ qua Bluetooth: chủ chọn nhầm thiết bị đặt tên giả thì trao mã mời cho kẻ lạ | – |
| SEC-11 | TB | Nhân viên có mọi quyền lệnh của chủ (đổi giá, đặt lượng kho); server không kiểm giá trị tham số | – |
| SEC-12 | TB | Server không giới hạn số luồng/kết nối; request 1 MB được đọc trước khi kiểm token | – |
| SEC-13 | TB | APK release ký bằng debug key | – |
| SEC-14 | Thấp | Username UNIQUE phân biệt hoa/thường ở DB nhưng kiểm tra không phân biệt: đăng ký song song "An"/"an" | X1 ✔ |
| SEC-15 | Thấp | Phiên 30 ngày không hết hạn khi không dùng; không có "đăng xuất mọi thiết bị" | – |
| SEC-16 | TB | Dán đè tem QR giả: chủ quét và đăng ký nhầm "máy" của kẻ tấn công | – |
| SEC-17 | ? | Tầng database MySQL của máy (`database.*`) không có trong repo: chưa kiểm được SQL injection qua `thamso` | – |
| SEC-18 | Thấp | Server nghe `0.0.0.0` (mọi card mạng, kể cả Tailscale/VPN) | – |
| SEC-19 | TB | Gói Menu base64(zlib) từ máy được app giải nén không giới hạn (bom zlib, như SEC-06) | – |

---

## SEC-01 — Không mã hóa đường truyền (Cao)
- **Kịch bản:** cùng Wi-Fi quán (hoặc Wi-Fi giả mạo), kẻ tấn công bắt gói tới cổng 8000. App gửi
  `password` khi đăng nhập, `token` mỗi request; máy gửi `product_key` mỗi lần hỏi lệnh (long-poll) và mỗi lần trả kết quả.
- **Tác hại:** chiếm tài khoản (token dùng 30 ngày), chiếm máy (xem SEC-02).
- **Hiện trạng:** `usesCleartextTraffic="true"` trong `AndroidManifest.xml`, server `http.server` thuần.
- **Đề xuất:** đặt server sau reverse proxy HTTPS (Caddy/nginx), app bỏ cleartext cho bản phát hành;
  máy gọi `https://`. Không đổi giao thức JSON.

## SEC-02 — Product key trên tem là thông tin xác thực duy nhất của máy (Cao)
- **Kịch bản:** khách ngồi quán chụp tem QR dán trên máy (JSON rõ: `product_key`). Kẻ tấn công giả máy bằng cách
  gọi `/machine/command/poll` bằng key đó (poll cũng làm máy giả được tính là online; route cũ `/machine/heartbeat` đã bỏ). Server giao lệnh của chủ cho ai hỏi trước,
  kẻ tấn công lấy lệnh (máy thật không nhận), trả kết quả giả (menu/kho giả) qua `/machine/tra-ket-qua`.
  Test X1 `test_SEC02_…` chứng minh kẻ giữ key nhận được lệnh `doi_gia_mon` của chủ.
- **Thêm:** máy chưa ai đăng ký thì người đầu tiên quét tem thành chủ (cố ý), nên tem phải được bảo vệ
  tới khi chủ thật quét.
- **Đề xuất (đổi flow):** tách "mã đăng ký trên tem" khỏi "bí mật máy dùng với server": khi đăng ký thành công,
  server cấp cho máy một `machine_secret` mới (qua kênh máy đã có) và từ đó chỉ chấp nhận secret đó
  cho hỏi lệnh/trả kết quả. Tem chỉ còn dùng để nhận quyền chủ. Hoặc tối thiểu: không in key lên tem, chỉ pair
  qua Bluetooth có xác nhận (xem SEC-09).

## SEC-03 — Bảng giới hạn IP dùng chung trần 1000 (TB)
- **Kịch bản:** `too_many_requests` trả `True` cho mọi IP mới khi bảng đã có 1000 IP trong 60 giây.
  Botnet/nhiều IPv6 gửi một request từ 1000 địa chỉ, và không ai đăng nhập/đăng ký mới được trong 60 giây (lặp lại được).
- **Đề xuất:** khi bảng đầy thì bỏ bản ghi cũ nhất (LRU) thay vì chặn IP mới; hoặc gộp IPv6 theo /64.

## SEC-04 — Trần 1000 phiên đăng nhập chờ (TB)
- **Kịch bản:** mỗi `/app/dang-nhap` (kể cả sai mật khẩu) giữ một phiên 60 giây. 34 IP × 30 request/phút
  lấp đầy 1000, người dùng thật nhận "Server đang bận". Phiên sai mật khẩu vẫn chiếm chỗ.
- **Đề xuất:** trả thẳng kết quả sai mật khẩu mà không giữ phiên; hoặc thu hồi phiên ngay khi app đã lấy kết quả.

## SEC-05 — Dò email/username qua đăng ký (TB)
- **Kịch bản:** `/app/dang-ky-nguoi-dung` trả "Email đã tồn tại" hoặc "Tên đăng nhập đã tồn tại" trước khi gửi OTP,
  nên dò được email của chủ quán rồi phishing. Đăng nhập thì đã chống dò (thông báo giống nhau + hash giả).
- **Đề xuất (đổi flow):** với email trùng vẫn trả "Đã gửi mã" và gửi email báo "email này đã có tài khoản";
  username trùng khó giấu, có thể chấp nhận.

## SEC-06 — Bom gzip từ máy (TB)
- **Kịch bản:** `/machine/tra-dong-bo` nhận tới 1 MB nén; server chuyển nguyên cho app với
  `Content-Encoding: gzip`, `HttpClient` của app tự giải nén toàn bộ vào RAM. Kẻ giữ product key (SEC-02)
  gửi ~50 KB nở thành 50 MB+ (hoặc 1 MB nở thành ~1 GB), app chủ máy crash khi mở tab Kho.
- **Đề xuất:** server giải nén thử có giới hạn (vd. 5 MB) trước khi chuyển; hoặc app đọc stream có giới hạn.

## SEC-08 — Trạng thái máy công khai (Thấp)
- `/machine/trang-thai?machine_id=` không cần token: lộ online/last_seen (giờ hoạt động của quán).
  machine_id là UUID ngẫu nhiên, khó đoán, nhưng hiện trên AppBar của app. **Đề xuất:** yêu cầu token + quyền quản lý.

## SEC-09 — Pair Bluetooth "Just Works" trao key cho mọi thiết bị (Cao)
- **Kịch bản:** `bluez_server.py` đăng ký agent `NoInputNoOutput`, `RequestConfirmation` luôn chấp nhận;
  profile SPP đăng ký suốt thời gian chạy. Hết 120 giây thì máy không còn *discoverable*, nhưng vẫn
  *connectable*: ai biết MAC (đã quét trước đó) kết nối được và nhận `product_key` bất cứ lúc nào, dẫn tới SEC-02.
- **Đề xuất:** chỉ đăng ký profile khi chủ bấm nút pair trên máy (có thời hạn), hoặc yêu cầu xác nhận mã số
  hiển thị trên màn máy.

## SEC-10 — Chia sẻ Bluetooth chọn thiết bị theo tên (TB)
- **Kịch bản:** chủ bấm "Gửi qua Bluetooth", danh sách hiện mọi thiết bị có tên. Kẻ tấn công đặt tên
  điện thoại giống nhân viên, chủ chọn nhầm thì kẻ đó nhận mã mời và thành nhân viên (tới khi bị thu hồi).
  Ngược lại, màn "Nhận chia sẻ" nhận mã từ bất kỳ ai. Kẻ lạ đẩy mã của máy họ, nhân viên "được giao" một
  máy giả trả dữ liệu giả.
- **Đề xuất:** hiện tên tài khoản người nhận và bắt chủ xác nhận sau khi server ghi quyền; hoặc hai bên so
  một mã 4 số hiện trên cả hai màn hình.

## SEC-11 — Quyền nhân viên và giá trị tham số (TB)
- `QUYEN_LENH` hiện cho `manager` mọi lệnh như chủ (đổi giá, đặt/trừ kho). Server không kiểm giá trị
  (giá âm, gram âm/khổng lồ); tùy tầng MySQL của máy. **Đề xuất:** quyết định lệnh nào chỉ chủ được làm
  (sửa bảng `QUYEN_LENH`), thêm kiểm tra kiểu/khoảng cho `thamso` như đã làm với `/machine/refill`.

## SEC-12 — Tài nguyên server (TB)
- `ThreadingHTTPServer` tạo luồng không giới hạn. Relay đọc body tới 1 MB trước khi kiểm token. Mỗi
  `/app/gui-lenh` giữ luồng tới 20 giây, mỗi `/machine/hoi-lenh` tới 8 giây. Người dùng hợp lệ spam lệnh
  thì hộp thư máy phình ra. **Đề xuất:** giới hạn số request đồng thời, body 64 KB cho route app,
  giới hạn lệnh chờ theo máy/người dùng.

## SEC-13 — APK release ký bằng debug key (TB)
- `android/app/build.gradle.kts` dùng `signingConfigs.getByName("debug")`: ai có debug key mặc định
  (có sẵn trên mọi máy dev) ký được bản cập nhật giả. **Đề xuất:** keystore release riêng, không commit.

## SEC-14 — Username trùng khác hoa/thường (Thấp)
- Kiểm tra trùng dùng `COLLATE NOCASE` nhưng cột `UNIQUE` phân biệt hoa/thường. Hai đăng ký song song
  "An"/"an" đều qua, rồi đăng nhập lấy một trong hai tài khoản tùy thứ tự. **Đề xuất:** index
  `UNIQUE(username COLLATE NOCASE)`.

## SEC-15 — Vòng đời phiên (Thấp)
- Token sống 30 ngày kể cả không dùng; không có đăng xuất mọi thiết bị hay đổi mật khẩu.
  Điện thoại mất thì token còn hiệu lực. **Đề xuất:** hết hạn khi không dùng 7 ngày; API thu hồi mọi phiên.

## SEC-16 — Dán đè tem QR (TB)
- **Kịch bản:** trước khi chủ đăng ký, kẻ tấn công dán tem QR giả (key do họ tạo) đè lên tem thật. Chủ quét,
  server tạo "máy" với key giả và chủ thành chủ của máy giả. Kẻ tấn công chạy máy giả (như `sandbox/relay/machine_sim.py`)
  trả menu/kho giả và nhận mọi lệnh của chủ. Máy thật vẫn chưa ai đăng ký, nên nếu kẻ tấn công có key thật
  (SEC-09) thì họ thành chủ máy thật. Tương tự với QR chia sẻ: nhân viên quét QR mời của kẻ lạ thì được giao máy giả.
- **Đề xuất:** sau khi đăng ký, app yêu cầu xác nhận máy đang online và tên hiển thị trên màn hình máy trùng
  với app; hoặc key nhà máy có chữ ký để server kiểm (hiện `machine_register_verify` ghi rõ "chưa có danh sách key nhà máy").

## SEC-17 — Tầng database của máy (chưa kiểm được)
- `machine/main.py` truyền `thamso["drink_id"]`, `["price"]`, `["gram"]`… vào `database.admin_functions.*` và
  `database.inventory_service`, nhưng các module này không nằm trong repo này. Cần xem chúng dùng truy vấn tham số
  (`%s`/`?`) chứ không ghép chuỗi. Server hiện chỉ kiểm `thamso` là object (B3), không kiểm kiểu từng giá trị.

## SEC-18 — Nghe mọi card mạng (Thấp)
- `SERVER_HOST = "0.0.0.0"`: laptop có Tailscale và Wi-Fi công cộng ("NartAnh 5G 3" đang là profile *Public*),
  nên server mở cho mọi mạng đó. **Đề xuất:** bind đúng IP LAN của quán, hoặc bật tường lửa chỉ cho LAN.

## SEC-19 — Bom zlib trong gói Menu (TB)
- **Kịch bản:** SEC-06 đã đóng đường gzip, nhưng gói Menu vẫn là `base64(zlib(JSON))` đi nguyên từ máy
  qua `/machine/tra-ket-qua` tới app; `decodeMenuPacket` gọi `ZLibCodec().decode` rồi `utf8.decode` toàn bộ.
  Kẻ giữ product key (SEC-02) trả gói ~0,95 MB (vừa giới hạn body 1 MB) nở thành ~700 MB
  (đo ngày 29/09/2026: zlib 713 430 byte → 700 MiB). App chủ máy hết RAM mỗi lần mở tab Menu.
- **Đề xuất:** app giải nén dạng stream và dừng khi vượt trần (vd. 5 MB), hoặc server/máy giới hạn
  kích thước gói sau giải nén. Cần chọn trần theo số món tối đa của máy.

---

## Đã an toàn (có test X1 giữ không hồi quy)
- Người lạ không gửi lệnh, đồng bộ, nạp kho, xem nhân viên, tạo mã mời, đổi tên, gỡ máy của máy người khác.
- Nhân viên không làm được việc của chủ; "gỡ máy" của nhân viên chỉ bỏ quyền của chính họ.
- Người thứ hai quét tem của máy đã có chủ bị từ chối.
- Mã mời dùng một lần kể cả khi hai người nhận cùng lúc; đăng xuất vô hiệu token.
- Sai mật khẩu và sai username trả thông báo giống nhau; dò mật khẩu bị 429 sau 30 lần/phút/IP.
- Máy khác không trả kết quả thay cho máy này được; JSON lồng sâu trả 400.
- JSON có surrogate lẻ (`\ud800`) hoặc lồng vượt giới hạn parser (route body lớn: Menu, cổng máy)
  trả 400 thay vì rớt kết nối (sửa 29/09/2026 trong `server/lib/http_json.py`).
- Kẻ cùng IP dò mật khẩu tới 429 không chặn được đăng xuất: `/app/dang-xuat` không tính vào
  giới hạn IP (sửa 29/09/2026; trước đó token bị lộ vẫn sống 30 ngày vì app bỏ qua lỗi đăng xuất).
- Lịch sử git không chứa `.env`, database, `machine.env` hay tem QR (đã kiểm tra `git log --all`).
