# SK-01 · Nghiệm thu skeleton LAN trên server và Raspberry Pi

**Trạng thái:** Phiếu hiện hành cho Phase 1–2. Chưa chạy; chỉ phát hành khi baseline và môi trường thử của các bước 1.2–1.6 sẵn sàng. Operator/Tester chỉ kiểm và ghi bằng chứng, không sửa code sản phẩm.

## Mục tiêu và ranh giới

Xác nhận các luồng skeleton v2 chạy qua server LAN/HTTP và Pi thật: tài khoản/OTP, nhận máy theo D1–D4, trạng thái qua relay theo D7–D8, timeout và khởi động lại. Đây là kiểm server/Pi. Nghiệm thu Android thật được chuyển sang bước 6.6 trên bản release. Không coi test giả lập, route hằng hay tài liệu mẫu trong `contracts/http/` là bằng chứng thiết bị.

Pilot dùng HTTP trên LAN theo quyết định G0; lớp phong bì mã hóa, chữ ký và kiểm quyền vẫn phải hoạt động. Không yêu cầu HTTPS Internet cho bước này. Không thêm tính năng hoặc sửa code khi gặp lỗi; ghi bằng chứng và hướng xử lý để user quyết.

## Nguồn hợp đồng và các lệch đã xử lý

`contracts/messages/v2-decisions.md` D1–D10 là chuẩn ưu tiên. `contracts/http/` chỉ chứa ví dụ minh họa body wire/plaintext, không phải fixture mật mã hoặc bằng chứng tương thích. Các tài liệu cũ dưới đây cần đọc như lịch sử khi có mâu thuẫn:

| Chủ đề | Tài liệu skeleton cũ | Căn cứ hiện hành / cách nghiệm thu |
|---|---|---|
| Đường kết nối và thiết bị | I-01 cũ yêu cầu HTTPS thật và gom Android, Pi, server vào một lần nghiệm thu | G0 chọn LAN/HTTP cho pilot; kiểm nền server/Pi ở Phase 1–2; Android thật ở 6.6. |
| Danh tính và nhận máy | I-01 cũ mô tả claim theo quy trình trước D1–D4 | D1–D4 là chuẩn: đăng ký serial/khóa ở xưởng, BLE v2, claim có challenge/proof, owner do server quyết định. Không thử theo flow `activation` cũ. |
| Mật khẩu và phiên | `auth.md` còn ghi mật khẩu tối thiểu 8; I-01 cũ chỉ đối chiếu hạn access/refresh idle | D9 thắng: 15–256 ký tự. D10 thêm thu hồi cả phiên khi refresh token đã dùng bị tái sử dụng và hạn tuyệt đối 90 ngày. Không đổi code trong phiếu nghiệm thu. |
| Relay | I-01 cũ dùng mô tả deadline/luồng relay trước D7–D8 | D7–D8 thắng: poll mới nhất, giới hạn tài nguyên, chống chạy lặp theo `request_id`; đối chiếu cùng ID từ app/server/máy và kết quả đúng máy. |
| Gate Bluetooth | Phiếu cũ mô tả đầy đủ claim thật | B-03 hiện vẫn BLOCKED trong `security-boundary.md`; không coi claim BLE là đạt cho tới khi gate interop/profile và thiết bị được mở. Ghi thành ca blocked nếu chưa đủ điều kiện. |

Các khác biệt trên là đối chiếu tài liệu; không chứng minh code hiện hành đã đáp ứng hợp đồng.

## Điều kiện trước khi chạy

1. Bước 1.1 được review; baseline 1.2 có commit, kết quả test tự động và danh sách lỗi đã biết.
2. Server thử, MySQL thử, trust key và LAN/HTTP được chuẩn bị theo 1.3. OTP thật chỉ gửi tới địa chỉ thử đã được allowlist; không dùng dữ liệu tài khoản của người khác.
3. Pi thử được provision theo D1 và qua kiểm tra 1.5. Ghi serial/machine ID và fingerprint không bí mật; không ghi private key, seal secret, OTP, mật khẩu hay token.
4. Công cụ và cleanup có manifest ID riêng, được review theo 1.6 trước khi tạo dữ liệu.
5. Nếu có bất kỳ dữ liệu/tài khoản/máy không thuộc run thử, dừng nhánh đó; không reset, đổi mật khẩu hoặc xóa hộ.

## Ca nghiệm thu server/Pi

1. Tạo tài khoản thử, nhận OTP thật, xác minh và đăng nhập; phân biệt email chưa xác minh, mã sai/hết hạn/khóa, SMTP lỗi và logout. Không lưu OTP/mật khẩu/token trong log hay biên bản.
2. Chỉ khi B-03 được mở: chạy nhận máy qua QR/BLE theo D1–D4; xác nhận owner duy nhất, account thứ hai bị từ chối, khóa/serial giữ nguyên sau reboot. Nếu B-03 còn BLOCKED, đánh ca này `blocked`, không giả lập thành công.
3. Hỏi trạng thái hai lượt qua relay; đối chiếu `request_id` xuyên app → server → poll → result. Kết quả phải mới từ đúng máy, không lấy cờ online làm câu trả lời.
4. Ngắt máy trước/sau khi request được nhận; thử reconnect, kết quả muộn/trùng/sai máy và restart server khi pending. Xác nhận lỗi hữu hạn và không hiện kết quả cũ thành lượt mới.
5. Ghi từng ca đạt/chưa đạt/blocked, thời gian, commit/build, môi trường và ID dữ liệu thử. Sau khi không còn ca phụ thuộc dữ liệu đó, cleanup đúng manifest trong transaction; đối chiếu DB trước/sau và giữ nguyên identity máy đã provision ngoài run.

## Bằng chứng và tiêu chí hoàn tất

Biên bản đặt tại `documentation/plan/evidence/SK-01-skeleton-acceptance.md` khi bắt đầu chạy. Phân biệt rõ server/Pi thật với test tự động; ghi ca Android chuyển sang 6.6. SK-01 chỉ đạt khi các ca server/Pi đủ điều kiện và cleanup được đối chiếu. Ca B-03 blocked và ca Android đang chờ không được tính đạt hoặc dùng để tuyên bố G1/G2/G3 đã qua.
