# Review sơ đồ — 06/10/2026

Claude CLI Opus, effort medium (`claude-opus-5-5`) làm coder tài liệu theo yêu cầu
người dùng. Session `f9643823-8bf4-4d38-b577-b3abc4db31e3`. Hai lượt ghi/sửa cuối
is_error=false. Lượt đầu gặp CLI permission ở Bash; operator dừng và chuyển
Read/Edit/Write được allowlist, không yêu cầu người dùng cấp quyền lại.

## Phạm vi

Ba trang HTML tóm tắt; bốn SVG thay mới; CSS sáng/tối/in và JS dialog offline.
Tham chiếu hai manual root và ảnh mẫu. Không sửa manual, code sản phẩm hay design.md.
Phần triển khai middleware vẫn tạm dừng. Tiêu chí ghi trong PHASE_FORMAT.md.

## Feedback và sửa

- Codex kiểm thứ tự phiên/credential trước durable claim và nhánh không thắng
  claim/CAS không được Seal; unknown không tự chạy lại tác động vật lý.
- Claude sửa năm điểm: domain riêng của info/AAD/signature; Tuple envelope thay
  LP nhiều đối số; retry chỉ khi ticket/epoch còn hợp lệ; recheck clock/epoch ở
  CAS; đọc/bootstrap bỏ ledger nghiệp vụ theo policy nhưng giữ attempt/CAS.
- Codex thêm nhãn nhánh đi tiếp, sửa CSS print sau khi thấy một trang gần trống
  do figure quá cao. PDF kiểm lại giữ toàn sơ đồ nhận cùng chú giải trên một trang.

## Kiểm chứng và giới hạn

Playwright trong venv /tmp, Chrome hệ thống, mở file:// trực tiếp: bốn nút zoom và
source hoạt động; Escape đóng, focus trả nút mở; ID SVG không trùng khi clone;
không JavaScript errors; không tràn trang tại 390px. Screenshot sáng/tối/điện
thoại và PDF A4 ở /tmp; operator xem trực tiếp sơ đồ tối và PDF. SVG/source vẫn
đọc được khi JavaScript tắt. Link local và git diff --check được kiểm lại.
Bằng chứng kiểm chức năng: visual-browser-check.json. Không phải kiểm bảo mật
mật mã, benchmark hay nghiệm thu production.
