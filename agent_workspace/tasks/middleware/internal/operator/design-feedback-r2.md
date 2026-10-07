# Codex phản hồi R2, yêu cầu R3

Chấp nhận F1–F4. Đã sửa design.md: claim+Seal-started CAS durable cấp quyền phản hồi;
luồng không thắng claim không ciphertext, restart không reseal; ledger key stable
physical machine/command, không generation; intent deadline+poll local bound;
server-issued immutable operation ticket + recovery_epoch ngoài backup + key đổi,
quarantine và đối soát sau restore. Bổ sung counterexample tests ở §11.

F5: không bắt buộc online intermediate mới; offline signed configs theo cadence,
client hard maxvalidity/overlap, expiry fail closed và freeze bound có clock assumptions.
F6: recovery factors explicit, không auto mật khẩu/OTP→machine-write.
F7: cấm own HPKE assembly, chỉ FFI library prototype nếu được review; không dependency
đạt thì dừng rollout, không fallback crypto/đổi runtime. Review không tự mở coder.
F8–F11: explicit zero sig bootstrap/query/version; highwater+monotonic; quota global
cả bootstrap và reserved lanes; poll/executor deadline budgets.

Phản biện:
1. Invariant seal nên theo (M,enc) / key identity đầy đủ, không enc đơn lẻ vì M đi
   vào HPKE info/key schedule. Implementation still must forbid deliberate enc reuse.
2. RAM replay+watermark có thể là option, nhưng cần proof cả future-clock acceptance,
   record retention và recovery. R3 chọn durable SQLite, không khẳng định duy nhất tối ưu.
3. op_created_at client-signed không chống retry sau backup nếu client có key tự
   sửa time. R3 dùng server ticket (issuer tạo ID), recovery_epoch ngoài rollback;
   không thu hẹp attacker A2 một cách ngầm để đóng F4.
4. Root offline không bắt buộc intermediate online; tradeoff cadence và freeze rõ.

Review R3 thật khắt khe, không xem mục gate là bằng chứng. Tìm counterexample còn
mở trong authority Seal, bootstrap actions, ticket retention, restore artifact,
machine deadlines và key binding. Phân biệt conceptual blocker với vector/device
measurements chưa có. Nếu còn lỗi, nêu trace cụ thể và minimal correction.
