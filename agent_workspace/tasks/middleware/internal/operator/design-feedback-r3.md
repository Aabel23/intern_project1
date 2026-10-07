# Codex phản hồi R3

Chấp nhận C1/C2. R4 khóa mọi route có Seal và cleanup khi clock untrusted, mặc định
untrusted sau boot cho tới verified OS time; highwater cập nhật ở cleanup. Không chỉ
writes. Chọn C2(i): bỏ packet time-sync, không exempt timestamp bootstrap; clockskew
transport diagnostic không tin và không tự chỉnh clock. Máy cần capability OS-time
và suspend-inclusive elapsed verified trước rollout.

Thêm synchronous=FULL server/machine + real-media flush gates; seq/head hash peer
frontiers chỉ là detector có điều kiện. Recovery epoch/authority ngoài cả snapshot
domain, manifest epoch explicit. Không claim detector tìm mọi full rollback; mọi
boot/recovery quarantine cần epoch confirmation bên ngoài, live snapshot resume
không supported nếu không có boundary detection. No evidence thì không mở writes.

Phân biệt: những runtime/capability chưa triển khai vẫn là deployment gates, không
assert safety. Proof sketches ở operator/security-obligations.md không phải formal
verification. Đã giữ counterexamples/maths outputs trong operator/.
