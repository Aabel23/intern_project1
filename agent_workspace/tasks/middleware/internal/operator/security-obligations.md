# Lập luận và nghĩa vụ kiểm chứng — không phải formal verification

Ngày 06/10/2026. Đây là proof sketches của operator cho design.md R5, không là
chứng minh primitive, composition hoặc product code. Phải phân biệt một mô hình
đúng với một triển khai đáp ứng mô hình. Các fault tests chưa được chạy.

## LP encoding có cách phân tích duy nhất

Giả định uint32_be có một encoding duy nhất, độ dài byte đúng, số fields cố định,
không chấp nhận trailing bytes. Đọc 4 byte đầu xác định duy nhất l; đúng l byte sau
là field thứ nhất. Áp dụng quy nạp cho phần còn lại. Do đó hai tuple khác fields
không cho cùng byte string, trừ khi encoder/parser không giữ các giả định.
Đây là lý do tránh delimiter text, không là chứng minh parser thực thi đúng.

## Quyền Seal tối đa một lần

Giả định mỗi response identity được map tới một record claim bền, CAS atomic trước
Seal, CLOCK_UNTRUSTED khóa mọi Seal/cleanup, cleanup chỉ theo verified clock,
FULL và stable media giữ commit, record không bị xóa khi packet còn hợp lệ, và
mọi rollback làm epoch cũ không
còn được nhận. Giả sử có hai Seal cho cùng response identity. Seal thứ nhất yêu cầu
CAS false→true đã commit. Seal thứ hai cũng phải CAS false→true nhưng thấy true,
mâu thuẫn. Crash sau CAS chỉ mất availability, không được cấp lại quyền Seal.
Epoch khác bind M vào info nên không là cùng response identity/key schedule.
Lập luận phụ thuộc KDF/hash collision assumptions và durability của storage; không
biến single-shot HPKE thành P(collision)=0 trên toàn fleet.

## Chống gọi executor trùng qua rotation

Giả định stable physical machine identity, command ID ổn định, UNIQUE claim durable
trước gọi executor, claim không bị xóa/namespace đổi bởi credential rotation.
Hai invocation cần hai successful first claims cho cùng key. UNIQUE/atomicity loại
khả năng đó. Machine ledger rollback/mất hoặc thay hardware phá giả định: phải
quarantine/đối soát, không gọi lại dựa trên credential mới.
Không suy ra exactly-once chuyển động vật lý của thiết bị bên ngoài executor.

## Giới hạn bất khả tránh ở tác động vật lý

Hai trace: (a) ghi claimed → crash trước actuator; (b) ghi claimed → actuator →
crash trước ghi result. Nếu không có đối soát actuator, dữ liệu phục hồi đều chỉ
claimed, nên không phân biệt được hai trace. Tự retry thì có thể lặp (b); tự kết
luận done thì sai ở (a). Thiết kế giữ unknown và cần nguồn đối soát độc lập.
Mật mã không làm atomic một actuator và transaction SQLite.

## Bounded storage và lịch sử không giới hạn

Không thể dùng state hữu hạn để nhận mọi ý định mới vô hạn mà luôn nhận biết mọi
ID đã dùng vô hạn còn hợp lệ: theo nguyên lý pigeonhole có hai lịch sử khác nhau
map tới cùng state. Một ID đã chạy trong một lịch sử nhưng chưa chạy trong lịch
sử còn lại không thể được phân loại chính xác chỉ từ state đó.
Thiết kế vì vậy ràng buộc ticket lifetime/epoch, pruning chỉ sau khi old ticket
không thể hợp lệ, giữ unknown đến reconciliation và fail closed khi đạt quota.
Đây là đánh đổi safety/availability, không là “tối ưu tuyệt đối”.

## Bằng chứng định lượng

[design-math-evidence.json](design-math-evidence.json) có phép tính Fraction chính
xác cho birthday bound, union bound nhiều khóa, độ dài base64url và counterexample
replay TTL ngắn. Các input là ví dụ phân tích, không phải threshold production.
Đây không là benchmark và không đánh giá tổng advantage của AEAD/KEM/KDF.

## Những điều vẫn phải chứng minh trên triển khai

- Official primitive vectors và byte-exact Dart/Python.
- Parser equivalence, route mapping, singleton Seal authority, error/response races.
- UNIQUE/CAS/durable commit với crash/clock/full store/restore.
- Enrollment/recovery/provisioning đúng trust model, rotation không reset ledger.
- Parameters admissible theo thực đo và security bound của suite/library.
- Backup/recovery artifact độc lập thật, không chỉ dòng mô tả.
- Không xem review của một model là chứng nhận độc lập hay formal verification.
