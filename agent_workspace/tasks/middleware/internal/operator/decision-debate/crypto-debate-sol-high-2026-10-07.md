# Nghiên cứu và phản biện crypto — 07/10/2026

Người dùng mở rộng sang thuật toán, tham số và key chưa chốt. Hai agent hiện có
`/root/researcher`, `/root/critic` tiếp tục model `gpt-6-sol`, effort `high`.
Hồ sơ này tóm lược tin nhắn collaboration thực, không giả transcript nguyên văn.
Architect read-only; operator ghi Markdown/JSON/HTML, không sửa code/design.md.

## Baseline độc lập

Cả hai đọc design.md và code trước đề xuất phía kia: HPKE Base single-shot,
chữ ký ngoài, Export response và one-Seal/CAS đã quy định; suite/signature/storage
floor/lifetime/hard bounds còn mở. Repo app chưa có crypto package, release debug
signing; SQLite durability deployment chưa kiểm. Không suy mặc định SQLite chỉ
vì code không đặt PRAGMA FULL.

Cả hai xác minh bốn suite RFC9180: X25519/P-256 × AES128GCM/ChaCha20Poly1305,
HKDFSHA256; enc32/65, nonce12/tag16. Key HPKE server độc lập curve ký Android.
Public Pyca cryptography49 HPKE API chỉ encrypt/decrypt/info, chưa AAD/Export cần
cho profile; không đưa vào shortlist đạt. BC/OpenSSL/Rust/PyHPKE có API phù hợp
để nghiên cứu nhưng chưa production gate/audit của composition.

## Trao đổi trực tiếp và sửa

1. C2 ban đầu gộp app/máy ký Ed/P256; critic chỉ ra TPM máy thường hỗ trợ P256,
   chưa có bằng chứng Ed. Researcher sửa bốn gói root/app/máy, máy đều P256;
   app Ed chỉ có điều kiện và không gắn curve HPKE.
2. C4 ban đầu nhảy từ software tới TPM nhiều đầu. Operator yêu cầu mốc nhẹ
   TEE app + file0600 machine/server. Researcher/critic nhận: B phù hợp intern
   nếu inventory fleet TEE P256 đạt; không âm thầm fallback software.
3. Critic yêu cầu matrix app Ed × strict hardware tier: chưa chứng minh TEE/StrongBox
   Ed thì không hợp B/C/D. Operator làm rõ software Ed là library key wrapped
   bằng AES Keystore, private key trong RAM, khác non-exportable Keystore signer.
   Critic đồng ý và chuyển correction cho researcher.
4. Critic phát hiện BC qua Kotlin MethodChannel không phải FFI mà design59–63
   quy định. Researcher nhận: C3-A/B cần user mở fallback, C/D FFI bám design.
5. C5 không ép bốn số TTL/tag/key bits. Critic/operator yêu cầu uncertainty/drift
   bounds có căn cứ, p99 chỉ giúp chọn hard cap, không maximum security guarantee.
   Ticket HMACSHA256/key32 là đề xuất chưa khóa; witness HMACSHA256 đã quy định.
6. Rotation không PFS/reset ledger; retiring khác revoked; response một Seal
   do CAS bền của profile chứ không thư viện context tự bảo đảm.

## Verdict nghiên cứu trước dựng tài liệu

Critic và researcher xác nhận không còn blocker logic C1–C5 với những sửa trên,
đủ trình người dùng chọn. Không phải nghiệm thu triển khai, chưa inventory Android/
Pi/TPM, dependency pin/build, official/interop/negative/fault vectors hay benchmark.

[Hồ sơ hợp nhất](../crypto-options-2026-10-07.md),
[JSON](../crypto-shortlist-sol-high-2026-10-07.json),
HTML tại packet-security.html#crypto-decisions.
Review bản ghi/render sẽ ghi bổ sung, không suy từ verdict nghiên cứu.

## Review bản hợp nhất và sửa cuối

- Critic đọc MD/JSON/HTML phát hiện hai điểm: C4/C5 root offline tuyệt đối mâu thuẫn D1-D Cloud KMS có điều kiện; C4-B ghi P256-only mâu thuẫn matrix Ed/TEE có điều kiện. Operator sửa cả JSON/MD/HTML, critic đọc lại xác nhận hết blocker. Giữ lỗi ở lịch sử này, không xóa để giả verdict vòng đầu đã sạch.
- Verdict cuối: **đạt review shortlist có điều kiện**, không nghiệm thu crypto production. 16 option C1–C4 khớp, C5 keymap/policy không ép bốn số; ticket HMAC32 là đề xuất, witness HMACSHA256 đã quy định. Overhead130/163 và bootstrap trừ64 theo frame đúng.
- Critic xem độc lập ảnh desktop C1/mobile C2/C4 sửa và PDF bảng key page30: không thấy chồng/cắt tại vùng lấy mẫu. Chưa kiểm toàn bộ PDF33 trang.
- Chrome/Playwright mở file://: desktop1440/mobile390 không document overflow; 16 crypto options /44 tổng, 4 C5 tables, no JS error, JavaScript tắt vẫn44 options; Zoom/Source, Escape và focus-return đạt. Link/ID nội bộ không lỗi; parity16IDs/root-exception/TEEconditions đạt. [Evidence](../crypto-ui-evidence-2026-10-07.json).
- Ảnh/PDF /tmp chỉ QA; tài liệu giao user vẫn HTML hiện có. Không chạy test sản phẩm, vector mật mã, benchmark; không sửa design.md hoặc triển khai.

## Bản ghi trao đổi từ log phiên

Bản này vẫn là tóm lược. Bản ghi 86 tin nhắn của lượt D và C nằm tại [transcript](transcript-sol-high-2026-10-07.md), kèm JSONL và hash; 77 bản ghi là nội dung bị runtime Codex mã hóa, không đọc được. Đã đối chiếu thứ tự/hash 86 bản ghi từ ba log thread; không dựng lại lời agent từ bản tóm tắt.
