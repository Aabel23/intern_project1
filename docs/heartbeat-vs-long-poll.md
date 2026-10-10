# Máy pha báo "còn sống" thế nào: heartbeat riêng hay suy ra từ long-poll

> So sánh thiết kế · `project1_app` · nguồn `07a54d0` + nhánh `feature/menu-image-cache` · phân tích 10/10/2026
> Bản HTML có sơ đồ: [heartbeat-vs-long-poll.html](heartbeat-vs-long-poll.html)

Có hai cách để server biết máy online:
- **Cách A** (đang chạy): một thread heartbeat gửi request mỗi 5 s, chạy song song với vòng lệnh.
- **Cách B** (đề xuất): bỏ heartbeat, suy online từ chính vòng long-poll và lệnh máy đang làm.

## 1. Bức tranh toàn cục

Máy nằm sau router, nên chỉ máy gọi lên server được. Máy chạy hai luồng:

| Luồng | File | Việc |
|---|---|---|
| Thread heartbeat | `version1.1/machine/server_connection/machine_server_heartbeat.py` | Gửi `{product_key}` tới `/machine/heartbeat/send` mỗi 5 s, timeout 5 s |
| Vòng lệnh tuần tự | `version1.1/machine/main.py` · `poll()` → `handle_command()` → `reply()` | Long-poll lấy lệnh, chạy, trả kết quả. **Không poll khi đang chạy lệnh** |

Phía server:
- `server/service/machine_link/machine_link_process.py`: `heartbeat`, `poll` và `send_result` đều xác minh `product_key`. Chỉ `heartbeat()` gọi `mark_seen()`.
- `server/lib/machine/machine_transport.py`: `is_online()` trả đúng khi heartbeat cuối cách đây dưới 15 s. `send()` gọi `is_online()` làm cổng chặn: offline thì trả 503, online thì xếp lệnh vào `HOP_THU` và chờ tối đa 20 s.

Điểm nóng: hiện chỉ heartbeat quyết định online, còn đường thực sự nhận lệnh (poll) thì không được tính. Cách B đảo lại.

## 2. Ba tình huống với cách A

1. **Máy rảnh:** máy poll (server giữ ≤ 8 s), heartbeat gọi `mark_seen()`. Đúng.
2. **Lệnh bình thường:** `is_online()` thấy heartbeat dưới 15 s nên cho gửi. Máy chạy lệnh và không poll trong lúc đó, nhưng heartbeat vẫn gửi đều. Heartbeat **có ích**, vì nó lấp khoảng máy không poll.
3. **Vòng lệnh treo** (ví dụ MySQL lock trong `nap_kho`): heartbeat vẫn chạy nên máy vẫn "online". Lệnh tiếp theo vẫn được xếp hàng, chờ 20 s rồi trả 502, và lặp lại mãi. Heartbeat **gây hại**, vì nó báo online cho một máy không còn nhận lệnh.

## 3. Hai phương thức

### 3.1 A · Heartbeat riêng (hiện trạng)

Online nghĩa là **process máy còn sống và có mạng**, không có nghĩa là máy nhận được lệnh. Quyết định chỉ có một câu hỏi: heartbeat cuối dưới 15 s thì online, không thì offline (503).

**Điểm mạnh**
- Đơn giản, đã chạy và có test.
- Không phụ thuộc lệnh dài hay ngắn.
- Tách được "process sống" khỏi "vòng lệnh", nếu sau này cần chẩn đoán.

**Điểm yếu**
- **Báo sai ở ca nguy hiểm nhất:** vòng lệnh treo mà máy vẫn online, mỗi lệnh chờ đủ 20 s rồi 502.
- Thêm khoảng 0,2 req/s mỗi máy, tức 60% lưu lượng lúc rảnh. Mỗi heartbeat tốn một thread server, một lần SHA-256 và một truy vấn SQLite.
- Thêm một thread thường trực trên máy, thêm route, thêm cấu hình phải giữ đồng bộ hai phía.
- Bỏ phí tín hiệu sẵn có: poll đã chứng minh máy sống ít nhất mỗi 8 s.

### 3.2 B · Suy online từ long-poll và lệnh đã lấy (đề xuất)

Online nghĩa là **vòng lệnh của máy đang chạy**, đúng điều `send()` cần biết. `is_online()` hỏi lần lượt ba câu:

| # | Câu hỏi | Ghi nhận ở đâu | Ghi chú |
|---|---|---|---|
| ① | Có poll đang mở? → online, rảnh | Bộ đếm trong `take()`: tăng khi vào, giảm trong `finally` | Lúc rảnh máy gần như luôn treo một poll |
| ② | poll/result cuối dưới 15 s? → online, rảnh | `mark_seen()` trong `poll()` ngay sau khi xác minh key, và trong `send_result()` | **Không** ghi lúc poll trả về: thời điểm đó là đồng hồ server, máy có thể đã chết trong 8 s chờ |
| ③ | Có lệnh đã take dưới 20 s? → online, bận | Chỉ mục mới `machine_id → lệnh đang chạy`, ghi trong `take()`, xoá khi có kết quả hoặc hết `COMMAND_TIMEOUT` | **Bẫy:** không dùng thẳng `DANG_CHO`, vì `send()` ghi lệnh vào đó *trước khi* máy lấy |

Cả ba đều không → offline (503).

Vòng đời trạng thái:
- `unknown` → `ranh`: khi có `poll()`.
- `ranh` → `ban`: khi `take()` trả lệnh.
- `ban` → `ranh`: khi `send_result()`.
- `ranh` → `offline`: quá 15 s không poll.
- `ban` → `offline`: quá 20 s không có kết quả.
- `offline` → `ranh`: khi máy poll lại.

`unknown` là tuỳ chọn: 15 s đầu sau khi server khởi động, chưa vội báo offline.

**Điểm mạnh**
- **Online trung thực:** vòng lệnh treo thì offline sau tối đa 20 s, lệnh sau nhận 503 ngay.
- Bớt khoảng 62% request lúc rảnh (0,325 → 0,125 req/s mỗi máy; 100 máy bớt khoảng 20 req/s). Máy bớt một thread.
- Phục hồi sau khi server restart trong khoảng 1 s thay vì tối đa 5 s.
- Phân biệt được rảnh và bận, mở đường cho app hiển thị "đang pha".
- Ước lượng bớt khoảng 30 dòng code.

**Điểm yếu**
- Logic phức tạp hơn: ba điều kiện, bộ đếm poll, chỉ mục lệnh, và phải đúng khoá (không gọi `mark_seen` khi đang giữ `CO_LENH`).
- Lệnh dài hơn 20 s sẽ thành offline. Hiện chưa có lệnh như vậy.
- Đổi ngữ nghĩa cổng của `send()`, ảnh hưởng cả 5 tính năng: `nhan_kho`, `nap_kho`, `nhan_menu`, `cap_nhat_menu`, `nhan_anh`.
- Phải nâng server trước, máy sau. Nếu máy mới gặp server cũ, mọi lệnh bị 503.
- Khoảng 13 vị trí test dựa vào heartbeat phải sửa.

## 4. So sánh theo tình huống

| Tình huống | A · Heartbeat riêng | B · Suy từ long-poll |
|---|---|---|
| Máy rảnh | ✅ heartbeat mỗi 5 s | ✅ luôn có poll đang mở |
| Lệnh ≤ 20 s (mọi lệnh hiện có) | ✅ thread riêng vẫn gửi | ✅ nhờ điều kiện ③ |
| Lệnh > 20 s (chưa có) | ✅ online, nhưng app đã nhận 502 | ⚠️ offline, nhất quán với 502; cần heartbeat theo lệnh nếu có lệnh dài hợp lệ |
| Vòng lệnh treo, process còn sống | ❌ online mãi, mọi lệnh 20 s rồi 502 | ✅ offline sau ≤ 20 s, lệnh sau 503 ngay |
| Mất điện / mất mạng | ≤ 15 s | ≤ 15 s khi rảnh, ≤ 20 s khi đang chạy lệnh |
| Mạng chập chờn | Cần 1/3 heartbeat qua được trong 15 s | Poll lỗi thì thử lại sau 1 s; mức nhấp nháy tương đương |
| Server restart | Online lại sau ≤ 5 s | Online lại sau ~1 s |
| Máy cũ + server mới | — | Chạy được. Nếu đã xoá route: máy nhận 404, in log mỗi 5 s, không crash |
| Máy mới + server cũ | — | ❌ mọi lệnh 503, nên bắt buộc nâng server trước |
| Request lúc rảnh / máy | 0,325 req/s | 0,125 req/s (−62%) |
| "Online" nghĩa là | Process sống và có mạng | Vòng lệnh đang chạy |

## 5. Case study

Hệ của ta là một **worker long-poll**: thiết bị tự đi hỏi việc, làm xong thì báo kết quả.

| Hệ thống | Lấy việc | Báo còn sống | Bài học |
|---|---|---|---|
| **AWS Step Functions** (activity worker) | `GetActivityTask` long-poll ≤ 60 s | `SendTaskHeartbeat` chỉ gửi **khi đang làm task**, theo `HeartbeatSeconds`; không kéo dài `Timeout` tổng | Lúc rảnh, poll là đủ. Heartbeat gắn với task, không gắn với process |
| **Temporal** (activity worker) | Poller long-poll task queue (~60 s) | `RecordHeartbeat()` gọi **từ trong code activity**, có thể kèm tiến độ; huỷ task cũng đi qua heartbeat | Heartbeat phát ra từ chính công việc nên khi treo thì im. Thread riêng như cách A không làm được |
| **GitHub Actions** self-hosted runner | Long-poll ~50 s | Khi chạy job: tác vụ nền gia hạn job lock mỗi phút (theo phân tích của Depot, bên thứ ba) | Rảnh thì poll; bận thì giữ một "lease" gắn với job |
| **Engine.IO / Socket.IO** | Long-polling hoặc WebSocket | Server ping, client pong (25 s / 20 s), **cả trên long-polling** | Ping đi trong cùng kênh dữ liệu. Kênh của họ không có "lệnh đã giao" để suy ra |
| **MQTT** keepalive + LWT | Kết nối liên tục | PINGREQ chỉ gửi khi kênh im; broker cắt sau 1,5 × keepalive và phát Last Will | Mọi lưu lượng đều là dấu hiệu sống |
| **ThingsBoard** | MQTT / HTTP / CoAP | Mọi telemetry, attribute hay RPC đều là "activity"; inactive sau `inactivityTimeout` | Không tách heartbeat thành kênh riêng |
| **Azure IoT Hub** | MQTT / AMQP | Khuyên dùng heartbeat ở tầng ứng dụng thay cho `connectionState` (có thể trễ tới 5 phút) | Heartbeat riêng hợp lý khi kênh sẵn có không báo sống đủ nhanh. Long-poll của ta có (≤ 8 s) |

> **Mẫu chung rút ra.** Ở các hệ worker long-poll:
> - Lúc rảnh, chính poll là tín hiệu sống.
> - Lúc bận, tín hiệu gắn với việc đang làm, phát ra từ chính công việc đó.
>
> Không hệ nào trong bảng dùng một thread heartbeat mù chạy song song với vòng xử lý. Cách B là phiên bản tối giản của mẫu này: "lệnh đã take dưới 20 s" thay cho heartbeat theo task.

## 6. Khuyến nghị

**Chọn B cho `project1_app`.** Lý do chính không phải tiết kiệm tải mà là online sẽ khớp với việc máy nhận được lệnh, đúng câu hỏi `send()` dùng làm cổng chặn.

Triển khai theo ba pha: **server → máy → dọn route**.

1. **Pha 1, chỉ sửa server.**
   - Thêm bộ đếm poll đang mở và chỉ mục lệnh đã take.
   - Gọi `mark_seen()` trong `poll()` (sau khi xác minh key) và trong `send_result()`.
   - Viết lại `is_online()` theo ba điều kiện.
   - **Giữ route heartbeat.** Pha này không đổi hợp đồng gói tin.
2. **Sửa test cùng pha 1.**
   - Các test gọi app trước khi máy poll phải đổi sang "poll trước".
   - SEC-02 và SEC-08 (`expectedFailure`) sẽ **pass giả**, phải viết lại.
   - Harness `menu_crc_stress` đang dùng `self.machine.heartbeat`.
   - Thêm test: lệnh chưa take không làm máy online; vòng treo thì offline sau 20 s; không deadlock khi poll và send chạy song song.
3. **Pha 2, sửa máy** (`version1.1/machine`, cần chủ dự án đồng ý): xoá thread heartbeat và hằng số.
4. **Pha 3:** xoá route `/machine/heartbeat/send` khi log không còn heartbeat từ máy cũ. Cập nhật khoảng 18 file tài liệu nhắc heartbeat.
5. **Đi kèm, độc lập:**
   - Đưa `online`/`last_seen` vào `/app/user/machine/list` rồi đóng route status công khai (SEC-08).
   - Tuỳ chọn: lưu `last_seen` vào DB, tối đa 60 s một lần.

**Khi nào vẫn nên dùng heartbeat**
- Có lệnh dài hợp lệ vượt `COMMAND_TIMEOUT`. Khi đó dùng **heartbeat theo lệnh**: `handle_command` tự gửi `{id, tien_do}`, giống `SendTaskHeartbeat`. Không quay lại thread mù.
- Kênh không báo sống đủ nhanh.
- Cần phân biệt "process sống nhưng vòng treo" để chẩn đoán. Khi đó tách thành trạng thái "treo" riêng, không gộp vào online.

**Khi nào nghĩ tới phương án nặng hơn**
- Chạy nhiều process server: cần Redis (last_seen + pub/sub) hoặc sticky routing.
- Hàng nghìn máy, cần lệnh dưới 1 s hoặc đẩy trạng thái realtime cho app: MQTT broker với keepalive và Last Will.

## 7. Thông số và ghi chú

| Thông số | Giá trị | Nơi khai báo | Dùng cho |
|---|---|---|---|
| `HEARTBEAT_INTERVAL_SECONDS` | 5 s | `version1.1/machine/config/routing.py:7` | Nhịp heartbeat (bỏ ở pha 2) |
| `HEARTBEAT_TIMEOUT_SECONDS` | 15 s | `server/config/config.py:5` | Ngưỡng online; B dùng lại cho ②, nên đổi tên |
| `POLL_WAIT_SECONDS` | 8 s | `server/config/config.py:8` | Thời gian server giữ một poll; phải nhỏ hơn ngưỡng ② |
| `COMMAND_TIMEOUT_SECONDS` | 20 s | `server/config/config.py:6` | Thời gian `send()` chờ kết quả; giới hạn ③ |
| Timeout HTTP heartbeat | 5 s | `machine_server_heartbeat.py` | `urlopen(..., timeout=5)` |
| Nghỉ khi poll lỗi | 1 s | `version1.1/machine/main.py` · `poll()` | Tốc độ phục hồi sau khi server restart |

- ⛔ **Nghiêm trọng:** với cách A, máy có vòng lệnh treo hiện online vô thời hạn. Mọi thao tác trên app chờ 20 s rồi báo "Máy chưa trả kết quả", và người dùng không có cách nào biết máy đã treo.
- ⚠️ Không lấy "có lệnh trong `DANG_CHO`" làm điều kiện online. Nó được ghi trước khi máy lấy lệnh (`machine_transport.py:55-58`).
- ⚠️ Các con số về tải, số dòng code và số vị trí test là ước lượng, chưa đo. Mô tả về GitHub runner lấy từ bên thứ ba.
- Ngoài phạm vi: server đã gửi `nhan_anh` nhưng `COMMANDS` của máy chưa có lệnh này.

## Nguồn tham khảo

- AWS Step Functions: [GetActivityTask](https://docs.aws.amazon.com/step-functions/latest/apireference/API_GetActivityTask.html) · [SendTaskHeartbeat](https://docs.aws.amazon.com/step-functions/latest/apireference/API_SendTaskHeartbeat.html)
- Temporal: [Long-running activity & heartbeats](https://docs.temporal.io/design-patterns/long-running-activity) · [Activity timeouts](https://temporal.io/blog/activity-timeouts)
- GitHub Actions: [Communicating with self-hosted runners](https://docs.github.com/en/enterprise-server@3.13/actions/concepts/runners/communicating-with-self-hosted-runners) · [Depot: runner listener](https://depot.dev/blog/github-actions-runner-architecture-part-1-the-listener)
- Socket.IO: [Engine.IO protocol](https://socket.io/docs/v4/engine-io-protocol/) · [How it works](https://socket.io/docs/v3/how-it-works/)
- MQTT: [HiveMQ: Last Will and Testament](https://www.hivemq.com/mqtt-essentials-part-9-last-will-and-testament) · [EMQX: Will Delay Interval](https://www.emqx.com/blog/use-of-mqtt-will-message)
- [ThingsBoard: Device connectivity status](https://thingsboard.io/docs/user-guide/device-connectivity-status)
- [Azure IoT Hub: Monitor device connection state](https://learn.microsoft.com/azure/iot-hub/monitor-device-connection-state)
- [OWASP API1:2023 BOLA](https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/)
