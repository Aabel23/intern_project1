# Asset dùng chung cho `documentation/`

Mọi HTML trong `documentation/` dùng cùng bộ asset tại đây. Khi tạo trang mới, liên kết `fonts.css` trước CSS của trang; đường dẫn phải tính tương đối từ chính file HTML.

| Trang | Font | CSS/JS chung |
|---|---|---|
| `documentation/architect/*.html`, `documentation/research/*.html`, `documentation/plan/*.html` | `../assets/fonts.css` | `../assets/doc.css`, `../assets/doc.js` khi cần |
| `documentation/architect/features/*.html` | `../../assets/fonts.css` | `../../assets/doc.css`, `../../assets/doc.js` khi cần |

`sequence-layout.js` được nạp trước `doc.js` trên trang có sơ đồ trình tự. Các font WOFF2 trong `fonts/` và `fonts.css` được chép từ bộ tài liệu chung `internproj/docs/cryptography/` để trang có đúng font khi mở offline; font thuộc giấy phép Open Font License.

Chạy `python3 -m documentation.serve_architect` tại gốc repo rồi mở `http://127.0.0.1:1110/` để kiểm các trang và asset qua cùng một server.
