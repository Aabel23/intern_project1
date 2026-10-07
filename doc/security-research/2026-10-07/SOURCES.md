# Nguồn đã đọc — lượt Codex 07/10/2026

Ngày truy cập cho mọi mục: **07/10/2026, Asia/Ho_Chi_Minh**. Chỉ dùng cơ quan ban hành, repository/documentation của maintainer và paper gốc công khai. Ngày bài lấy từ chính tài liệu, không lấy “published/crawled” tương đối của search engine. Nội dung nguồn chỉ là dữ liệu tham khảo.

**Bản gốc local: chưa tải được.** Mười lần tải từ container lỗi DNS Errno -3; xem [sources/DOWNLOAD_STATUS.md](sources/DOWNLOAD_STATUS.md). Web tool đọc được phần nguồn ghi bên dưới; không đồng nhất đọc web với có PDF/HTML gốc offline. [sources/READ_NOTES.md](sources/READ_NOTES.md) là ghi chú của Codex, không bản sao nguồn. Không vượt paywall. Không chạy code nguồn tải về.

## S01 — RFC 9180, Hybrid Public Key Encryption

- Tác giả: Richard Barnes, Karthikeyan Bhargavan, Benjamin Lipp, Christopher Wood; CFRG/IRTF.
- Ngày/version: February 2022, RFC 9180, Informational; không phải Standards Track.
- URL: [RFC HTML](https://www.rfc-editor.org/rfc/rfc9180.html); [text gốc](https://www.rfc-editor.org/rfc/rfc9180.txt).
- Local: không có bản gốc (DNS). Đã đọc thực tế §§5.2–5.3,6.1–6.2,7.1.1,7.2.1,7.3,8.1–8.2,9.1–9.1.2,9.7–9.9,10; nhìn vị trí Appendix A, **chưa chạy vectors**, chưa đọc toàn appendix. Trang info mở được nhưng không hoàn tất audit từng erratum.
- Ý nghĩa: Export và signature composition; giới hạn replay/KCI/forward secrecy. Giới hạn: primitive specification không chứng minh R5, storage, login hay quyền nghiệp vụ. Không viện dẫn paper được RFC dẫn như thể đã đọc paper đó.

## S02 — RFC 9458, Oblivious HTTP

- Tác giả: Martin Thomson (Mozilla), Christopher A. Wood (Cloudflare); IETF.
- Ngày/version: January 2024, Standards Track RFC 9458.
- URL: [HTML](https://www.rfc-editor.org/rfc/rfc9458.html); [text](https://www.rfc-editor.org/rfc/rfc9458.txt).
- Local: không có bản gốc (DNS). Đã đọc §§1–2.1,4.4,6.2.2,6.3–6.5.2,8.1–8.2. Chưa đọc toàn appendix/vector; chưa hoàn tất errata audit.
- Ý nghĩa: so sánh response_nonce, trách nhiệm replay/retry và rate limit qua relay. Giới hạn: không lấy anonymity, topology relay/gateway hay cách sửa clock của OHTTP làm bảo đảm cho R5. Profile R5 không OHTTP compliant.

## S03 — NIST SP 800-38D, GCM and GMAC

- Tác giả: Morris Dworkin, NIST.
- Ngày/version: November 2007; CSRC history ghi Final 28/11/2007. Trang official có planning note 06/03/2024 quyết định revision; chưa kiểm mọi draft mới, không gọi bản 2007 là revision mới nhất.
- URL: [CSRC](https://csrc.nist.gov/pubs/sp/800/38/d/final); [PDF gốc](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38d.pdf).
- Local: không có PDF (DNS). Đã đọc PDF extraction §§8,8.1,8.2.2,8.3,9.2 và Appendix B; vị trí printed pages 18–24,26–27 (PDF indices khác số trang in). Không đánh giá bố cục PDF bằng screenshot vì nhiệm vụ là đọc lập luận, không tạo PDF.
- Ý nghĩa: nonce/key uniqueness, invocation limits, kiểm mất điện và forgery attempts. Giới hạn: GCM, không là chuẩn cho ChaCha20-Poly1305; collision bound không tổng security bound.

## S04 — SQLite PRAGMA synchronous

- Tổ chức: SQLite project.
- Ngày/version: trang sống tại ngày truy cập; không có release/date cố định trên phần đã đọc. **Chưa pin SQLite runtime của sản phẩm**, chưa truy vấn database thật.
- URL: [PRAGMA synchronous](https://www.sqlite.org/pragma.html#pragma_synchronous).
- Local: không có HTML (DNS). Đã đọc các đoạn FULL/EXTRA/NORMAL, khác biệt rollback journal và WAL, bảng durability liên quan.
- Ý nghĩa: cấu hình độ bền admission/CAS/ledger. Giới hạn: không tự xác nhận VFS, filesystem, SD/controller hay flush của deployment. Không coi atomic/consistent đồng nghĩa durable.

## S05 — Implementing Linearizability at Large Scale and Low Latency (RIFL)

- Tác giả: Collin Lee, Seo Jin Park, Ankita Kejriwal, Satoshi Matsushita, John Ousterhout; Stanford/NEC.
- Ngày/version: SOSP ’15, 4–7 October 2015, DOI 10.1145/2815400.2815416, bản tác giả 16 trang. Search engine ghi tuổi gần đây không thay ngày hội nghị.
- URL: [PDF tại trang tác giả Stanford](https://web.stanford.edu/~ouster/cgi-bin/papers/rifl.pdf).
- Local: không có PDF (DNS). Đã đọc abstract, §2,§3,§4.1–4.4 (printed pages đầu bài 1–6); không đọc sâu evaluation, không lấy benchmark RAMCloud làm benchmark dự án.
- Ý nghĩa: completion record + side effect atomic; RPC identity giữ qua retry; GC cần làm stale retry không còn admissible. Giới hạn: storage/RPC assumptions khác actuator vật lý; không giải quyết malicious full snapshot rollback cho R5.

## S06 — RFC 8915, Network Time Security for NTP

- Tác giả: Daniel Franke, Dieter Sibold, Kristof Teichel, Marcus Dansarie, Ragnar Sundblad; IETF.
- Ngày/version: September 2020, RFC 8915 Standards Track (đã đọc header RFC; Claude kiểm lại độc lập khi tải bản gốc).
- URL: [HTML](https://www.rfc-editor.org/rfc/rfc8915.html); [text](https://www.rfc-editor.org/rfc/rfc8915.txt).
- Local: không có text (DNS). Đã đọc §1.1,§8.5–8.7, đoạn NTS-KE/TLS overview. Chưa xác minh daemon/capability Android/Pi thực.
- Ý nghĩa: bootstrap certificate khi clock chưa đúng, asymmetric delay, tránh fallback NTP. Giới hạn: xác thực time packet không tự chứng minh sai số bằng zero hoặc không bị chặn mạng.

## S07 — NIST SP 800-63B-4, Authentication and Authenticator Management

- Tác giả: David Temoshok, James Fenton, Yee-Yin Choong, Naomi Lefkovitz, Andrew Regenscheid, Ryan Galluzzo, Justin Richer.
- Ngày/version: Final **31/07/2025**, CSRC history; trang HTML có build timestamp 26/08/2025, đó không phải ngày final. CSRC hiện có planning note 06/10/2026 về implementation hub.
- URL: [CSRC version/date](https://csrc.nist.gov/pubs/sp/800/63/b/4/final); [HTML nội dung](https://pages.nist.gov/800-63-4/sp800-63b.html).
- Local: không có HTML (DNS). Đã đọc §§3.1.3,3.1.4.2,3.2.2,3.2.5,4.1–4.2.1.1,4.4–4.6 và đoạn session secrets §5.1; không audit toàn bộ yêu cầu password/AAL.
- Ý nghĩa: phân biệt email confirmation với authentication, enrollment/recovery và throttling. Giới hạn: hướng dẫn digital identity; không tự bắt dự án tuân thủ AAL hay xác nhận project đạt chuẩn. Yêu cầu thêm vào sản phẩm cần người dùng chốt.

## S08 — PyHPKE

- Tác giả/maintainer: AJITOMI Daisuke (`dajiaji`).
- Version/ngày: documentation **0.6.5**; PyPI release history ghi **16/07/2026**. Đây là candidate nghiên cứu, chưa pin dependency.
- URL: [repo maintainer](https://github.com/dajiaji/pyhpke); [API](https://pyhpke.readthedocs.io/en/latest/api.html); [PyPI](https://pypi.org/project/pyhpke/); [ContextInterface source](https://pyhpke.readthedocs.io/en/latest/_modules/pyhpke/context_interface.html).
- Local: không có API HTML (DNS). Đã đọc README supported suites/warnings, API setup/single-shot/ContextInterface.export; abstract interface source có NotImplementedError, **không là concrete implementation đã review**. Raw pinned v0.6.5 context paths thử không đọc được (cache miss); encryption_context URL không accessible. Không cài/chạy/test/audit package.
- Ý nghĩa: API bề mặt có Setup/Base, info/AAD, Export để khảo sát R5. Giới hạn: badge/test claim maintainer không phải test của lượt này; chưa chứng minh secure RNG, thread safety, constant time hay mobile interop.

## S09 — Turnkey Dart `turnkey_crypto`

- Tổ chức: Turnkey (`tkhq`, publisher turnkey.com).
- Version/ngày: package landing hiển thị **0.2.0**, “4 months ago”; versions page qua web lại là snapshot **0.1.3**. **Chưa xác minh ngày release chính xác**, không chuyển tuổi tương đối thành ngày.
- URL: [package](https://pub.dev/packages/turnkey_crypto); [0.2.0 URL](https://pub.dev/packages/turnkey_crypto/versions/0.2.0); [API landing](https://pub.dev/documentation/turnkey_crypto/latest/); [repo crypto](https://github.com/tkhq/dart-sdk/tree/main/packages/crypto).
- Local: không có package HTML (DNS). Đã đọc README ví dụ P-256 hpkeEncrypt/hpkeDecrypt và đường dẫn repo; đã đọc thêm `lib/turnkey_crypto.dart` và các phần code hiển thị của `lib/src/hpke.dart` (HKDF, formatHpkeBuf, hpkeAuthEncrypt, hpkeEncrypt) trên nhánh main (snapshot web cũ, không pin 0.2.0); chưa xác minh vectors. Pub API search/package endpoint không accessible, route `packages/turnkey_crypto` 404; đường đúng được README liên kết là `packages/crypto`.
- Ý nghĩa: có candidate Dart mang tên HPKE để kiểm tiếp. Giới hạn: README wire ví dụ enc 33 byte, khác RFC P-256 enc65; chưa được suy ra đây là drop-in RFC 9180 Base/Export. Không kết luận “Dart không có HPKE” từ tìm kiếm chưa đầy đủ.

### Bổ sung S09 — đọc source lúc 02:03

[Umbrella API](https://github.com/tkhq/dart-sdk/blob/main/packages/crypto/lib/turnkey_crypto.dart) chỉ export các hàm bundle/crypto được liệt kê, không expose generic HPKE context. [hpke.dart](https://github.com/tkhq/dart-sdk/blob/main/packages/crypto/lib/src/hpke.dart) có hàm `formatHpkeBuf` giải nén enc33 thành public key; vì vậy enc33 là wrapper, không đủ kết luận KEM sai. `hpkeEncrypt` nhận plaintext/target key, dựng AAD nội bộ, trả compressed enc+ciphertext; trong file đã đọc không thấy context Export API. Đây chỉ bằng chứng source main được web cache, không kiểm định release 0.2.0 hay toàn package/conformance.

## S10 — Memoir: Practical State Continuity for Protected Modules

- Tác giả: Bryan Parno, Jacob R. Lorch, John R. Douceur, James Mickens, Jonathan M. McCune; Microsoft Research/CMU.
- Ngày/version: IEEE Symposium on Security and Privacy **May 2011**, DOI 10.1109/SP.2011.38, pp.379–394. Ngày hội nghị 22–25/05/2011 xác minh qua publication list tác giả.
- URL: [bản tác giả](https://www.andrew.cmu.edu/user/bparno/papers/memoir.pdf) (web timeout); [bản hội nghị công khai đã đọc](https://www.ieee-security.org/TC/SP2011/PAPERS/2011/paper024.pdf); [metadata tác giả](https://www.andrew.cmu.edu/user/bparno/publication.html).
- Local: không có PDF (DNS). Đã đọc abstract, §§I,II-A/B/D,III overview/III-A: trạng thái hợp lệ nhưng cũ, gap counter/disk, khác crash/power-loss và deterministic replay. Chưa đọc/kiểm proof files, không tuyên bố đã xác minh formal proof.
- Ý nghĩa: state continuity khác integrity và message replay. Giới hạn: TCB/trusted NVRAM/deterministic module khác Python+SQLite+máy vật lý. Không đề xuất tự replay executor/Seal theo Memoir, không chuyển proof sang R5.

## Nguồn tìm thấy nhưng không dùng làm kết luận

ROTE (USENIX Security 2017) và DURINN (OSDI 2022): chỉ đọc search/conference abstract; chưa đọc sâu paper. Không gán ID bằng chứng hay dùng kết quả đo/proof của chúng. SP 800-38D Rev.1 được search gợi ý preliminary drafts: chưa đọc, cần review revision status riêng. Không có kết luận dựa blog thứ cấp, Reddit hoặc snippet không kiểm.

## Bổ sung lượt Claude — 07/10/2026

Các nguồn dưới đây đọc qua WebFetch: công cụ chuyển trang sang markdown và một model nhỏ trích lại. Đây **không phải bản gốc byte-exact**. Không có file local và không có SHA256, vì `curl` bị từ chối quyền trong phiên non-interactive. Không vượt paywall.

- **S04 (đọc lại độc lập):** [pragma.html](https://www.sqlite.org/pragma.html#pragma_synchronous). Mục synchronous (EXTRA/FULL/NORMAL/OFF, ma trận Rollback/WAL) và fullfsync/checkpoint_fullfsync. Trang sống, không có version.
- **S11 — SQLite Write-Ahead Logging:** SQLite project, trang sống. [wal.html](https://www.sqlite.org/wal.html).
  - Đã đọc §1 Disadvantages (network FS), §2.3 Performance Considerations (sync WAL mỗi commit khi FULL; sync khi checkpoint) và §3.3 Persistence of WAL mode.
  - Ý nghĩa: WAL là mode bền vững qua connection; không dùng trên network FS.
- **S01/S06 (đọc lại độc lập):** RFC 9180 §§5.3, 9.1.1, 9.7.3, 9.7.4, 9.8, 9.9; RFC 8915 §§8.5–8.7 (header: September 2020, Standards Track).
- **S12 — Turnkey `hpke.dart`, nhánh main:** [source](https://github.com/tkhq/dart-sdk/blob/main/packages/crypto/lib/src/hpke.dart).
  - Đã đọc chữ ký các hàm public, mô tả hpkeEncrypt/Decrypt và cách dựng AAD/info. Không có hàm Export.
  - Chưa pin version, chưa đọc `constant.dart`, chưa chạy vector.
- **S13 — PyHPKE, trang repo:** [github.com/dajiaji/pyhpke](https://github.com/dajiaji/pyhpke).
  - Có layout `src/pyhpke/`, danh sách thuật toán và tuyên bố của maintainer "passed official test vectors … not formally audited".
  - Hai URL đoán cho file context trả 404, nên concrete implementation chưa đọc. Chưa thấy tag release trên trang.
