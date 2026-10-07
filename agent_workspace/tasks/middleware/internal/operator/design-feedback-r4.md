# Codex phản hồi R4, diff R5

Chấp nhận R4-B1/S1/S2/S3/S4: issuer HMAC-SHA256 witness kw riêng purpose,
MAC invalid chỉ packet reject; table M có seq/witness fixed và uint16 draft5,
labels draft5 domain separation; machine frontier binary segment thứ tư explicit;
all Seal routes fail closed; client max seq không alarm trên out-of-order responses.

Operator tự thấy machine telemetry seq có thể out-of-order: bổ sung continuity
challenge issued sau expected frontier, machine đọc ledger sau challenge. Lower
telemetry không tự quarantine; fresh challenge equal/head hoặc lower seq evidence
chỉ scope machine; extension proof thiếu thì không tự redeliver unresolved commands.

Không áp elapsed manifest age-reset/reload làm expiry proof: proxy replay manifest
cũ có thể reset timer. Ghi Android time chưa trusted, deployment gate fail nếu không
chứng minh capability; không claim các assumptions thực tế đã đạt.

Xin kiểm diff R4→R5 cuối thật khắt khe. No proof/code/benchmark đã chạy.
