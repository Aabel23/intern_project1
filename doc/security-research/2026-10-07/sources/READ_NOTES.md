# Ghi chú đọc nguồn của Codex (không phải bản gốc)

Đọc qua web ngày 07/10/2026. Các vị trí dưới đây giúp Claude mở nguồn độc lập; không có original bytes offline.

| ID | Vị trí đọc ưu tiên | Câu hỏi phải trả lời khi review |
|---|---|---|
| S01 | §§5.2–5.3,9.1.1,9.7.3–5,9.8;7.1.1 | Chữ ký bind enc/ct/M; singleton Export response; giả định response key secrecy và PFS |
| S02 | §4.4 và §6.5 (đặc biệt đoạn response_nonce) | Vì sao OHTTP reseal replay khác R5; không bê cách sửa clock dưới A1 |
| S03 | §§8–8.3,9.2;Appendix B | Bounds theo key, mất điện, attempts Open thất bại; tránh dùng birthday estimate làm tổng bound |
| S04 | PRAGMA synchronous: FULL, EXTRA, bảng journal mode | WAL+FULL vs rollback+EXTRA; flush contract còn phụ thuộc media |
| S05 | §3;§4.1–4.4 | Completion/side effect atomic và GC stale retry; giới hạn actuator |
| S06 | §§8.5–8.7 | Chứng thư khi cold boot, delay error, cấm fallback NTP tự động |
| S07 | §§3.1.3,3.2.2,4.1,4.2.1.1,4.5–4.6 | Email confirmation không phải MFA; bind/recovery one-use/notification/quota |
| S08 | API CipherSuite và ContextInterface.export | Concrete implementation + pinned version cần đọc thêm |
| S09 | README và packages/crypto/lib (chưa đọc lib) | Export, info/AAD, RFC enc serialization và vectors còn chưa rõ |
| S10 | §§I,II-D,III overview | Trusted state ngoài rollback domain; không áp proof của paper cho R5 |

Nguồn sơ cấp và ngày/version chi tiết ở ../SOURCES.md. Không có benchmark hoặc test sản phẩm trong lượt này.
