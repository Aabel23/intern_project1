# Phản biện vòng 1 (critic Claude Opus medium) — tóm tắt các mục

Đích: decision-options-2026-10-07.md (DO), design.md (D).

## Chung
- [NÊN SỬA] Mỗi quyết định mở bằng 3–4 dòng lời thường: quyết định là gì, chọn sai thì hậu quả cụ thể
  (vd D1: manifest hết hạn → mọi route có Seal bị chặn, app/máy ngừng; D:87–89, D:231–232), chi phí ước lượng.
  Chú giải PoP, PIV, prehash, Merkle, A1, delegation.
- [NÊN SỬA] Phụ thuộc chéo thiếu: D3-A cần app đã enroll → loại D6-B; D4 cần app enrollment, D4-D cần D3 và
  máy có UI; D2-D (OS clock) làm max_manifest_validity của D1 không enforce được; giới hạn header proxy (D5×D8-A).

## D1
- [NÊN SỬA] Root nằm trong APK/image nên chỉ mạnh bằng khóa ký APK; repo ký release bằng debug key
  (log/SECURITY_NOTES.md SEC-13). Tiên quyết chung: keystore release riêng / Play App Signing + quy trình image máy.
- [GỢI Ý] Thiếu Cloud KMS/HSM ký từ xa (key không xuất được, IAM+MFA, audit); có thể thay D1-D. Thuật toán KMS hỗ trợ: chưa kiểm.
- [GỢI Ý] Manifest ký trước (D:75–76) lưu ở server có thể bị dùng để kéo dài cửa sổ thu hồi.
- [GỢI Ý] YubiKey cần firmware ≥5.7 cho Ed25519 PIV (không nâng được), hoặc dùng P-256.

## D2
- [CHẶN] D2-D không phải lời giải (tự thừa nhận không thỏa gate production) → chuyển thành lộ trình.
  Thiếu phương án HTTPS-Date đa nguồn (header Date từ ≥3 máy chủ uy tín, trung vị, đồng thuận; tiền lệ
  sdwdate Whonix, htpdate Tails). D2 nên là 4 phương án cho app; chrony NTS cho server/máy là nền chung.
- [NÊN SỬA] Roughtime: critic báo đã thành RFC 10049 Experimental 10/2026 (https://www.rfc-editor.org/info/rfc10049),
  hỗ trợ UDP và TCP → sửa nhược điểm "chặn UDP". (Operator CHƯA kiểm lại — cần xác minh.)
- [GỢI Ý] Neo thời gian xác thực + SystemClock.elapsedRealtime(); đối chiếu D:559–562.
- [NÊN SỬA] Nguồn "PR #39010" không ghi trạng thái đã kiểm.

## D3
- [CHẶN] Phương án không loại trừ nhau: TPM (D3-C) là trục lưu khóa. Đưa 4 gói trọn vẹn
  (A BT+xác nhận vật lý; B provision lúc lắp + claim code; D' kiểu RFC 8628: máy tự sinh khóa, hiện mã ngắn trên
  màn hình máy, chủ nhập vào app đã đăng nhập, server bind, rate-limit + hạn ngắn; gói thứ tư).
  TPM / ATECC608 tách thành tùy chọn lưu khóa (chưa kiểm).
- [NÊN SỬA] Tiêu chí chống máy giả/dán đè tem (SEC-16, log/SECURITY_NOTES.md:118–124): B chặn được.
- [NÊN SỬA] Máy có nút/màn hình không là câu hỏi chặn chung, đưa lên đầu D3.
- [GỢI Ý] BlueZ agent DisplayYesNo cho Numeric Comparison nếu máy có màn hình.

## D4
- [NÊN SỬA] Đường admin (C) luôn bắt buộc (máy mất khóa; D:97–100, D:352–353) → gói: C / A+C / B+C / D+C.
- [GỢI Ý] Nhân viên mất máy = thu hồi + share lại qua machine_share, không cần cơ chế mới.

## D5
- [NÊN SỬA] D5-D (tailnet-only) chỉ là pilot; thêm Cloudflare Tunnel (TLS ở edge bên thứ ba = A1 thật, không VPS;
  nhược: phụ thuộc nhà cung cấp, cần domain, giới hạn header/timeout chưa kiểm).
- [NÊN SỬA] Người dùng đã chốt HTTP/1.1: Caddy cần `protocols h1`; edge bên thứ ba có thể không tắt được h2.
- [GỢI Ý] Long-poll 8 s, /app/gui-lenh tới 20 s (SEC-12): timeout proxy chưa kiểm.

## D6
- [CHẶN] D6-D (dual-stack) vi phạm D:59 hoặc trùng B/C. Thay bằng canary theo deployment/audience pilot riêng,
  protected-only, rồi cutover (thỏa D:9–10, D:59, D:179).
- [NÊN SỬA] D6-A thiếu kế hoạch rollback; rollback mở lại plaintext là downgrade, phải được người dùng chấp nhận.

## D8
- [CHẶN] D8-D (machine_no decimal) không có lợi ích → thay bằng POST batch trạng thái nhiều máy (machine_ids[], lọc quyền).
- [NÊN SỬA] machine_list_get.py:4 đã import is_online/last_seen_of → D8-C rẻ; tests/e2e/run_e2e.py:156–162 dùng GET
  status làm health probe → cần probe thay thế.
- [GỢI Ý] Với B/C, mục query GET trong design bị xóa, không chỉ đổi regex.

## Khác
- [GỢI Ý] DO:18 dẫn machine_list_get.py:27–29; thực tế 26–28.

Kết luận vòng 1: CÒN VẤN ĐỀ CHẶN (D2-1, D3-1, D6-1, D8-1).
Ghi chú: mục "Vòng 2 — operator hợp nhất" cuối DO là bản hợp nhất nhanh của operator, chưa được critic kiểm.
