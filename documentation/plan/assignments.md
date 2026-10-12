# Phân công MVP: skeleton kết nối trước

> **Cập nhật 12/10/2026 (hợp đồng v2):** User duyệt D1–D10 và chọn cách 3 trên `version1.1`. Các slot S-02, S-03, M-01, M-02, M-03, A-02, A-03 đã được code và test tự động; còn I-01 (nghiệm thu thiết bị thật). Trạng thái và việc còn lại: [mvp-fast-path.md](mvp-fast-path.md); hợp đồng: [`v2-decisions.md`](../../contracts/messages/v2-decisions.md). Phần "Cổng chưa mở" bên dưới là lịch sử, D1 đã thay quyết định bind tại chỗ.

**Trạng thái:** lộ trình đã duyệt; C-01/C-02/C-03/C-04 hoàn tất. User chốt cách server kiểm máy thật, TLS + phong bì cloud và HPKE PSK Bluetooth ngày 12/10/2026. C-05 đã lập hợp đồng; S-01/A-01 đã code và qua review nhỏ vòng 2. [Review lớn module tài khoản](account-module-review-2026-10-12.md) đã chạy một lần: hai finding được user ghi nhận và quyết định chưa sửa. Nghiệm thu runtime thật còn thiếu Android, HTTPS pin/cert, Gmail; B-03 Bluetooth còn BLOCKED theo gate kỹ thuật.

**Mốc đầu tiên:** người dùng mới đăng ký qua email/OTP, đăng nhập, quét mã niêm phong và nhận máy thật; app chọn máy, hỏi **trạng thái trực tiếp từ máy** qua server và hiển thị câu trả lời của chính máy. Không dùng tài khoản hoặc máy nạp sẵn, không dùng kết quả giả, không lấy cờ online lưu ở server thay câu trả lời máy. Menu sync làm sau mốc này.

Thứ tự thực thi ngắn gọn và trạng thái mới nhất: [mvp-fast-path.md](mvp-fast-path.md).

## Thứ tự và người giữ việc

| Phase | Module | Vai chính | Phụ thuộc | Mốc xong |
|---|---|---|---|---|
| 0 | Contracts cho skeleton | Operator, 2 researcher, architect, Planner | Lộ trình đã duyệt | Hợp đồng auth, claim, relay và hỏi trạng thái được user chốt; ví dụ gói và bảng tương thích đủ để coder làm theo |
| 1 | Tài khoản | Coder server + coder app | Hợp đồng auth và luồng gửi Gmail | Đăng ký/OTP/đăng nhập thật trên Android; OTP tới đúng email đăng ký |
| 2 | Nhận máy | Coder machine + coder server + coder app | Hợp đồng claim; tài khoản | Máy mới nhận chủ qua mã niêm phong, lên server, có trong danh sách của Owner |
| 3 | Kết nối và hỏi trạng thái | Coder machine + coder server + coder app | Hợp đồng relay/status; nhận máy | App ↔ server ↔ máy ↔ server ↔ app; kết quả trực tiếp, lỗi offline rõ |
| 4 | Nghiệm thu skeleton | Tester tích hợp + Operator | Phase 1–3 | Gửi OTP thật tới hai tài khoản thử nghiệm, xác minh bằng mã user cung cấp; chạy trên điện thoại và máy thật; dọn dữ liệu thử sau khi đạt; lưu bằng chứng |
| 5 | Menu và tắt/bật món | Coder machine + coder app; server relay | Skeleton; hợp đồng menu và lệnh ghi | Menu thật từ MySQL, tắt/bật và đọc lại đúng; chống chạy lặp lệnh ghi |
| 6 | Share, LAN/Bluetooth | Coder ba phía | Hợp đồng quyền và đường tại chỗ; Phase 5 | Share QR/BLE và vận hành dự phòng theo quyền |
| 7 | Nghiệm thu MVP | Tester + Operator | Phase 5–6 | Cả ba đường và hai cách share đạt trên thiết bị thật |

### Phiếu khối contracts

1. [C-01 · Đối chiếu quyết định và nguồn](tasks/C-01-contract-boundary.md) — hoàn tất: [bảng đối chiếu](contracts-decision-log.md).
2. [C-02 · Research nhận máy và danh tính](tasks/C-02-claim-research.md) — hoàn tất bằng agent Sol low; kết quả và nguồn lưu trong kho research của dự án.
3. [C-03 · Research relay và trạng thái trực tiếp](tasks/C-03-relay-status-research.md) — hoàn tất bằng agent Sol low; kết quả và nguồn lưu trong kho research của dự án.
4. [C-04 · Architect hợp đồng skeleton](tasks/C-04-contract-architecture.md) — hoàn tất bản [contracts.html](../architect/features/contracts.html), Operator đã đối chiếu quyết định user.
5. [C-05 · Planner khóa hợp đồng và viết phiếu coder](tasks/C-05-contract-planner.md) — hợp đồng cloud/auth đã khóa và phát S-01/A-01; BT/claim chưa phát coder vì gate phiên BLE/Android/Wi-Fi còn chặn.

C-02 và C-03 đã chạy song song; C-04 đã tổng hợp. User chọn đăng ký serial và mã niêm phong trên server trước khi bán, máy tự sinh khóa lần bật đầu, không nạp chứng chỉ xưởng. C-05 không tự quyết thay user. Mọi phiếu coder ở Phase 1–3 chỉ phát sau C-05; không dùng bảng này thay phiếu coder.

## Các slot coder sẽ được Planner phát sau cổng contracts

| Slot | Người ghi chính | Codespace dự kiến | Kết quả phải chứng minh | Chưa được làm trong slot |
|---|---|---|---|---|
| S-01 Server nền + tài khoản | Server | `server/src/`, `server/configuration/routing.py`, migration MySQL | Chủ dự án liên kết Gmail gửi thư; server gửi OTP thật tới đúng email đăng ký; tài khoản chưa xác minh không đăng nhập; phiên đúng hạn đã chốt | Claim, relay, menu |
| A-01 App tài khoản | App | `flutter_app/lib/feature/user_auth/`, `lib/app/`, lớp kết nối cloud | Đăng ký, xác minh, đăng nhập, đăng xuất từ Android thật | Dữ liệu mẫu để báo thành công |
| M-01 Máy: danh tính + nhận wifi | Machine | `version1.1/machine/pairing/`, `machine/config/` | Máy mới dùng mã niêm phong; danh tính bền qua khởi động lại; không lộ `product_key` cũ | Menu, share, OTA |
| S-02 Server nhận máy | Server | `server/src/`, route claim/list | Người quét đầu là Owner; claim lại không sinh Owner thứ hai | Share, chuyển chủ |
| A-02 App nhận/chọn máy | App | `feature/machine_register/`, `feature/dashboard/` | Quét mã, gửi wifi, nhận máy, chọn đúng máy của tài khoản | Nạp máy sẵn, share |
| M-02 Máy kết nối server | Machine | `machine/server_connection/`, `machine/main.py` | Máy tự nối ra, hỏi lệnh, trả kết quả và phục hồi khi mất mạng | LAN/BT vận hành, lệnh menu |
| S-03 Server relay | Server | `server/src/` phần relay | Chỉ chuyển cho đúng máy/người, trả offline/timeout rõ; không bịa kết quả | Cache menu, hàng đợi lệnh thường bền |
| M-03 Máy trả trạng thái | Machine | Handler chỉ đọc mới, đăng ký ở `machine/main.py` | Mỗi lượt hỏi lấy trạng thái hiện tại của máy | Ghi DB, menu sync |
| A-03 App hỏi trạng thái | App | `feature/dashboard/`, lớp kết nối cloud | Thấy câu trả lời của máy; ngắt máy hiện lỗi, không hiện kết quả cũ như mới | Dùng `MACHINE_STATUS_GET` thay lượt relay |
| I-01 Nghiệm thu skeleton | Tester + Operator | Test trong repo và biên bản nghiệm thu | Tự kích hoạt gửi OTP thật cho từng email thử nghiệm; user cung cấp từng mã để xác minh; đăng nhập và kiểm toàn luồng với máy mới, Android, server thật; thử claim trùng và mất mạng; xóa dữ liệu test trong DB khi các ca đạt | Sửa lỗi phát hiện khi chưa bàn hướng xử lý; xóa dữ liệu ngoài hai tài khoản thử nghiệm |

**Ranh giới file chung:** `contracts/` chỉ một người ghi mỗi thời điểm; routing server do slot S giữ, routing máy do slot M giữ. Ba coder có thể làm song song sau khi hợp đồng của phần việc đã chốt. Reviewer nhỏ độc lập so mỗi task với phiếu; reviewer lớn kiểm đúng một lần sau khi cả module xong.

## Cổng chưa mở

- **Gmail SMTP cho OTP:** user báo phần mail đã xong ngày 12/10/2026. Server sẽ gửi từ Gmail của chủ dự án qua SMTP với App Password lưu trong cấu hình server. Hai email `nguyenhoanganh15112005@gmail.com` và `23200002@student.hcmus.edu.vn` là **tài khoản nhận thử nghiệm** của skeleton: chỉ gửi OTP cho địa chỉ đang đăng ký trong hai địa chỉ này khi chạy thử, không gửi bản sao OTP của tài khoản khác cho họ. Danh sách thử nghiệm là cấu hình môi trường thử, không là luật sản phẩm vĩnh viễn. Planner đặc tả hành vi khi Gmail không gửi được; I-01 sẽ kiểm OTP thật qua luồng sản phẩm.
- **Nghiệm thu và dọn dữ liệu thử:** user đã cho phép Operator tự gửi OTP qua luồng sản phẩm tới cả hai email thử nghiệm khi hệ thống sẵn sàng, rồi dùng từng OTP do user báo để hoàn thành ca xác minh. Sau khi các ca liên quan đạt, kiểm tra quan hệ dữ liệu và chỉ xóa bản ghi DB do hai tài khoản thử nghiệm tạo ra (tài khoản, OTP, phiên và liên kết máy thử nếu có); ghi biên bản kết quả và phần đã dọn, không ghi lại OTP. Không xóa dữ liệu của tài khoản/máy khác.
- **Đã quyết:** trước khi bán, đăng ký serial và bản kiểm mã niêm phong trên server; mã nằm trong máy và QR niêm phong. Máy tự sinh khóa lần bật đầu; server kiểm máy biết mã đã đăng ký trước khi gắn khóa với serial. Không nạp chứng chỉ xưởng, không PAKE cho mã dài. [Tài liệu kích hoạt cũ](../architect/features/machine-activation.html) còn lệch; [contracts.html](../architect/features/contracts.html) là bản đã đối chiếu để C-05 đặc tả.
- **Đã quyết phạm vi skeleton:** cloud dùng TLS và phong bì mã hóa bên trong trên cả app↔server và máy↔server ngay từ đầu. Máy dùng danh tính khóa tự sinh đã gắn bằng mã niêm phong đăng ký, không chứng chỉ xưởng cũ. LAN/Bluetooth vận hành làm sau; đặc tả không được cho cloud quyền khác với mô hình chung.
- **Đã quyết tài khoản ngày 12/10:** gửi lại OTP cho email chưa đăng ký trả `CHECK_EMAIL` nhưng không gửi thư; đăng ký lại tài khoản chưa xác minh thay mật khẩu; số lần nhập OTP sai không reset khi gửi lại. Đủ 5 lần sai khóa xác minh 15 phút rồi tự mở, vẫn có thể gửi lại mã theo cooldown. Hợp đồng chi tiết ở `contracts/messages/auth.md`.
- **Chưa chốt phiên Bluetooth nhận máy:** [nghiên cứu Noise](../research/ble-noise-feasibility.md) chứng minh Java↔Python nhưng thư viện Java không chạy nguyên trạng trên Android. Architect đã đưa lựa chọn HPKE PSK có profile xác nhận phiên hoặc Noise với adapter Android; M-01/A-02/S-02 còn BLOCKED tới quyết định và gate kỹ thuật.
- Câu hỏi trạng thái phải đi qua relay chung và có câu trả lời từ máy. `MACHINE_STATUS_GET` đang mô tả trạng thái do server suy từ poll, là một thông tin khác.
- Các giá trị chưa chốt (hạn OTP, ngưỡng thử sai, timeout, trường trạng thái, công cụ triển khai) thuộc quyết định kỹ thuật của chu trình contracts. Planner ghi một đề xuất có lý do; user quyết những điểm làm đổi thiết kế hoặc hành vi sản phẩm. Coder không chọn hộ.

## Căn cứ hiện trạng

`server/src/` hiện trống; `server/configuration/routing.py` mới có hằng đường dẫn. App Flutter có form và tab máy nhưng callback đang đưa tới màn kế tiếp mà chưa gọi server. Máy còn gửi `product_key` trong `machine/server_connection/machine_server_request.py` và trả nó qua Bluetooth trong `machine/pairing/machine_bluetooth_pair.py`. Vì vậy bài nghiệm thu skeleton phải quan sát đường kết nối thật, không coi giao diện hiện có là đã triển khai.

Lộ trình trực quan: [mvp-roadmap.html](mvp-roadmap.html).
