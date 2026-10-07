# Tình trạng bản gốc local

Ngày truy cập 07/10/2026 Asia/Ho_Chi_Minh. Sáu thử tải urllib.request.urlopen (timeout 25s) đồng thời từ container đều thất bại ngay do DNS: `Temporary failure in name resolution` (Errno -3).

| URL bản gốc | Tệp dự kiến | Kết quả |
|---|---|---|
| https://www.rfc-editor.org/rfc/rfc9180.txt | rfc9180.txt | Không tạo tệp |
| https://www.rfc-editor.org/rfc/rfc9458.txt | rfc9458.txt | Không tạo tệp |
| https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38d.pdf | nist-sp800-38d.pdf | Không tạo tệp |
| https://pages.nist.gov/800-63-4/sp800-63b.html | nist-sp800-63b-4.html | Không tạo tệp |
| https://www.sqlite.org/pragma.html | sqlite-pragma.html | Không tạo tệp |
| https://www.rfc-editor.org/rfc/rfc8915.txt | rfc8915.txt | Không tạo tệp |

Web tool truy cập/đọc được các tài liệu trên và bản PDF tác giả RIFL. Bản đọc qua web không phải bản gốc đã tải về local. Không vượt paywall, không xin mở sandbox/network. Claude có thể tải lại nếu runtime được phép; giữ URL và SHA256 nếu thành công. Những file .md trong sources/ là ghi chú truy cập, không giả mạo nguồn gốc.

## Thử bổ sung cho paper/thư viện

- RIFL: https://web.stanford.edu/~ouster/cgi-bin/papers/rifl.pdf — <urlopen error [Errno -3] Temporary failure in name resolution>
- Memoir-conference: https://www.ieee-security.org/TC/SP2011/PAPERS/2011/paper024.pdf — <urlopen error [Errno -3] Temporary failure in name resolution>
- PyHPKE-API: https://pyhpke.readthedocs.io/en/latest/api.html — <urlopen error [Errno -3] Temporary failure in name resolution>
- Dart-package: https://pub.dev/packages/turnkey_crypto/versions/0.2.0 — <urlopen error [Errno -3] Temporary failure in name resolution>
