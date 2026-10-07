# Diễn giải tầng bảo mật — 07/10/2026

Theo yêu cầu người dùng, thêm sơ đồ tầng bảo mật trước khi gửi trong packet-security.html: xác minh khóa qua manifest → chuẩn bị plaintext/M → KEM → KDF → AEAD → chữ ký ngoài → envelope/HTTPS. Mỗi bước ghi mục đích, đầu vào, đầu ra và trạng thái thuật toán chưa chốt.

Đây là diễn giải R5, không đổi kiến trúc hay lựa chọn suite. Nguồn: internal/packet-security/design.md §2–5; RFC 9180 §5–6. Không đưa khóa đối xứng rõ vào envelope; chữ ký bao phủ M/enc/ct sau mã hóa. Bổ sung bảng M và phân biệt băm trong KDF/ledger với mã hóa và xác thực.

Kiểm: parse XML toàn bộ SVG; ID trang không trùng; đo chiều rộng chú thích sơ đồ mới bằng DejaVu Sans 13px nằm trong cột 730px. Chưa kiểm bằng trình duyệt hoặc bản in. Không cập nhật trạng thái nghiệm thu triển khai.

## Bố cục theo manual — 07/10/2026

Người dùng làm rõ chỉ hai sơ đồ dưới trong security, rồi yêu cầu bám sát FexMix_Munual.html: tổng quan khối lớn trước, sau đó đi sâu từng phần. Đã đọc trực tiếp CSS, phần tổng quan, mục lục và thẻ thành phần của mẫu. Trang security tổ chức lại thành tổng quan rộng → mục lục trái / thẻ nội dung phải → phần cần chốt / hồ sơ phản biện. Năm thẻ: ý định+retry, đóng gói bảo mật, phía nhận, chống lặp, response. Mỗi thẻ có Làm gì, nguồn R5 và sơ đồ hoặc các bước/tham số. Giữ nguyên hai sơ đồ kỹ thuật trước trong details. Stylesheet security-manual.css chỉ áp dụng body.security-page; architecture và manual mẫu không sửa.

Kiểm thực tế: Chrome headless render trang desktop 1440px và màn nhỏ 412px; inspect ảnh tổng quan, ảnh vùng thẻ/mục lục và ảnh màn nhỏ. Export A4 ra /tmp/security-manual.pdf (6 trang), render trang 1 và contact sheet trang 2–6 để kiểm bố cục. Các sơ đồ chính nhìn đủ luồng trong PDF; phần kỹ thuật đóng mặc định không bung ra ở bản in. Khi chụp URL có anchor trực tiếp, ảnh headless bị trắng; đã kiểm bằng render trang cao rồi crop đúng vùng, không coi ảnh trắng là bằng chứng đạt. Kiểm parse 7 SVG, ID/neo/tài nguyên offline và cấu trúc main/section/article/details. Không chạy nghiệp vụ hay vector mật mã.

Review độc lập phát hiện nhãn retry ở sơ đồ rút gọn ghi quay lại bước 3, khiến có thể hiểu là bỏ kiểm manifest/clock. Đã sửa thành quay lại bước 2 để khớp caption và R5: mọi retry kiểm lại trust trước khi tạo attempt mới.
