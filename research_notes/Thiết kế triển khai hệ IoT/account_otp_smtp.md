# Account module: email + password + email OTP, sessions, Gmail SMTP (Python stdlib http.server + MySQL, Flutter Android)

Research date: 2026-10-12. Method note: direct WebFetch to owasp.org, nist.gov, google.com was blocked by the sandbox egress proxy. OWASP cheat sheets were read from the official source repo (github.com/OWASP/CheatSheetSeries, shallow clone, last commit 2026-10-08), and NIST SP 800-63B-4 from the official source repo of pages.nist.gov/800-63-4 (github.com/usnistgov/800-63-4). argon2-cffi 25.1.0 defaults were read from the PyPI wheel. Google, Android and provider facts come from web-search summaries of Google help pages plus secondary sources. Those are flagged where they are not primary.

Code reviewed: `server/src/account.py`, `server/src/smtp_mail.py`, `contracts/messages/auth.md`, `documentation/plan/account-module-review-2026-10-12.md`, `flutter_app/android/.../SessionStore.kt`, `AndroidManifest.xml`, `auth_page.dart`.

## Q1. Password hashing: Argon2id vs scrypt vs bcrypt; OWASP parameters; current code

### Takeaway
The current choice is correct and above the OWASP minimum: Argon2id through argon2-cffi 25.1.0 with m=65536 KiB, t=3, p=1, salt 16 B (`account.py:38-39`). Keep it. Add three things: a cap on concurrent hashes (64 MiB per hash on an unbounded thread-per-request server), `check_needs_rehash` on login, and a dummy-hash verify on the "no such user / unverified" login path to remove a timing oracle. The 8-character minimum is below NIST rev4 for single-factor passwords.

### Cited Findings
- OWASP lists Argon2id first. Its minimum configurations, which are equivalent in defense, are: m=47104 (46 MiB), t=1, p=1; **m=19456 (19 MiB), t=2, p=1**; m=12288, t=3; m=9216, t=4; m=7168, t=5 (all p=1). — [OWASP Password Storage CS](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html) (source repo, lines 112-116)
- OWASP's scrypt fallback is N=2^17 (128 MiB), r=8, p=1, or equivalents (2^16/r8/p2 … 2^13/r8/p10). — same source, lines 126-130
- OWASP says to use bcrypt only for legacy systems, with work factor ≥10 and a 72-byte input limit. Under FIPS-140, use PBKDF2-HMAC-SHA-256 with ≥600,000 iterations. — same source, lines 13-14, 142
- OWASP: "Consider using a pepper … defense in depth". A pepper is stored separately from the DB, ideally in a vault/HSM. Rotating it forces password resets unless you use a post-hashing HMAC (pepper as the HMAC key). — same source, lines 15, 60-77
- argon2-cffi 25.1.0's default profile is `RFC_9106_LOW_MEMORY`: Argon2id, t=3, m=65536 (64 MiB), p=4, salt 16, hash 32. p is reduced to 1 on platforms without threads. The project's settings match that profile except p=1. — argon2-cffi 25.1.0 wheel, `argon2/profiles.py` ([PyPI](https://pypi.org/project/argon2-cffi/25.1.0/))
- argon2-cffi documents `check_needs_rehash()`: "it's best practice to check -- and if necessary rehash -- passwords after each successful authentication" when parameters or library defaults change. — argon2-cffi `_password_hasher.py` docstring ([docs](https://argon2-cffi.readthedocs.io/en/stable/api.html))
- NIST SP 800-63B-4 §3.1.1.2: passwords used as **single-factor** authentication SHALL be ≥15 characters. Passwords used only as part of MFA may be ≥8. Verifiers SHOULD permit a maximum of at least 64 characters. Passwords SHALL be salted (salt ≥32 bits) and hashed with a password hashing scheme. Verifiers SHOULD add a keyed-hash/encryption iteration with a secret key stored separately, preferably in an HSM/TEE. — [NIST SP 800-63B-4](https://pages.nist.gov/800-63-4/sp800-63b.html)
- OWASP Authentication CS: the "quick exit" pattern (return early when the user doesn't exist, hash only when it does) creates a timing discrepancy that enables user enumeration. Run the same work regardless of whether the user exists. — [OWASP Authentication CS](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html) (lines 158-190)
- Current code: `login()` calls `_hasher().verify` **only** when `user is not None and user['verified_at'] is not None` (`account.py:224-226`). Unknown and unverified emails skip the Argon2 cost and return measurably faster, while the response body is the same `AUTH_FAILED`. — code review

### Inferences
- **Keep Argon2id m=64 MiB, t=3, p=1.** It is about 3.4x the OWASP 19 MiB baseline in memory. scrypt (stdlib `hashlib.scrypt`) is an acceptable no-dependency fallback with N=2^17, r=8, p=1, but it is not needed because argon2-cffi is already pinned. Don't use bcrypt: the 72-byte truncation interacts badly with the contract's "no max length" rule.
- **Memory DoS risk:** `ThreadingHTTPServer` spawns one thread per connection without a bound. 20 concurrent register/login requests means about 1.3 GB of Argon2 memory. Wrap hash and verify in a module-level `threading.BoundedSemaphore(N)` with N ≈ CPU cores (2-4). Optionally, when the semaphore can't be acquired within about 2 s, return SERVICE_UNAVAILABLE 503 (needs a planner decision).
- **Timing equalisation:** precompute `DUMMY_HASH = _hasher().hash(secrets.token_urlsafe(32))` at startup. On the unknown/unverified path call `_hasher().verify(DUMMY_HASH, password)` and ignore the result. Register/send already run under the same email lock and take similar SMTP-bound paths, so login is the main remaining oracle.
- **Rehash on login:** after a successful verify, `if ph.check_needs_rehash(h): UPDATE users SET password_hash=…`. This allows future parameter changes without resets.
- **Pepper:** optional. If added, use the post-hash HMAC pattern (store `HMAC(pepper, argon2_hash)` or encrypt the hash) so the pepper can be rotated. Low priority for a skeleton project, since `otp_hash_secret` already shows the secret-in-env pattern.
- **Password length policy:** contract min 8 is NIST-compliant only if the password is one factor of MFA. Email OTP here verifies the address at registration; it is not a second login factor, so login is single-factor. To follow rev4 literally, raise the minimum to 15, or document an accepted deviation. Also consider an upper bound (for example 1024 code points / 4 KiB) to cap hashing input. NIST requires permitting at least 64.

### Gaps
- No measured Argon2 latency on the target server. Benchmark `time ph.hash()` and aim for roughly 100-500 ms, adjusting t accordingly.

## Q2. OTP generation and storage: CSPRNG, HMAC-pepper vs SHA-256, constant-time compare, attempt limiting, email OTP vs magic link

### Takeaway
The implementation already matches OWASP and NIST rev4: `secrets.randbelow(10**6)`, HMAC-SHA256 keyed by a server secret over (email, purpose, generation, otp), `hmac.compare_digest`, single use, 10-minute TTL, new generation on resend, and a persistent per-email failure counter that new generations don't reset. Keyed HMAC is the right choice over plain SHA-256 because a 6-digit space (10^6) is brute-forced instantly from an unkeyed hash. Email OTP for address confirmation is explicitly outside NIST's "email SHALL NOT be used for OOB authentication" ban.

### Cited Findings
- OWASP MFA CS (OTP handling): SHOULD enforce a short TTL, single use, strict attempt limits, and invalidate on success. SHOULD NOT log OTPs or store them in long-term plaintext. RECOMMENDED: CSPRNG, "Consider 8-digit or longer codes where usability allows", and "On resend, generate a new OTP and overwrite the old record". — [OWASP MFA CS](https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html) (lines 63-83)
- OWASP: hashing OTPs is still recommended, but "a database attacker can brute-force any OTP hash quickly" for 6 digits. Its purpose is short-term exposure protection (logs, brief DB exposure), not long-term secrecy. — same source, lines 85-98
- NIST 800-63B-4 OOB (§3.1.3.2): the secret must be completed within **10 minutes**, accepted only once, generated as **≥6 decimal digits** by an approved RBG. If the secret is <64 bits, rate-limit consecutive failures per §3.2.2, and "**Generating a new authentication secret SHALL NOT reset the failed authentication count.**" — [NIST SP 800-63B-4](https://pages.nist.gov/800-63-4/sp800-63b.html)
- NIST §3.2.2: limit consecutive failures on one authenticator to **no more than 100**. "The limit of 100 attempts is an upper bound, and agencies MAY impose lower limits." 100 was chosen to balance guessing against a 6-digit OTP with recovery cost. — same source
- NIST §3.1.3.1: "Email SHALL NOT be used for out-of-band authentication" (password-only mailbox access, interception, DNS rerouting), but "Confirmation codes that are sent to validate email addresses or are issued as recovery codes … are not authentication processes and not affected by the above prohibition." — same source
- NIST look-up/recovery code guidance: issued recovery codes need ≥6 decimal digits from an approved RBG. Short look-up secrets (<112 bits) SHALL be stored salted and hashed with a password-hashing scheme. — same source (applies to look-up secrets, not directly to email confirmation codes)
- Current code: `otp = f'{secrets.randbelow(1000000):06d}'` (`account.py:120`); `_otp_hash = HMAC-SHA256(otp_hash_secret, json[email,'register',generation,otp])` (`:95-96`); `hmac.compare_digest` (`:176`); counter `users.registration_attempts` with lock at 5 failures for 900 s, not reset by resend (contract, `auth.md` §"Quyết định user bổ sung"). — code review

### Inferences
- **HMAC with pepper vs SHA-256:** with SHA-256 alone, a stolen row reveals the OTP after at most 10^6 hashes (milliseconds). With HMAC and a secret that is not in the DB, it can't be reversed without the key. Argon2 on an OTP adds cost but still loses against 10^6 candidates, so HMAC with a separately stored key is the right design. Binding email, purpose and generation into the MAC, as the code does, prevents cross-row or cross-purpose substitution. Keep `otp_hash_secret` ≥32 random bytes in env, separate from DB backups.
- **Guess budget:** 5 failures per 15 minutes gives at most about 480 guesses per day per email, a success probability of about 4.8x10^-4 per day against 10^6. Combined with the 10-minute TTL, that is well within NIST's 100 cap. The lock is auto-expiring rather than requiring "rebind" (NIST disables the authenticator), which is acceptable because this is address confirmation, not authentication. To push risk further at low UX cost: 8 digits (OWASP suggestion), or a daily cap per email (for example 20 failures per 24 h, then require register again).
- **Lockout DoS:** an attacker who knows a victim's pending email can keep it locked. Impact is limited to the unverified registration window and the 15-minute auto-expiry. Acceptable for the skeleton.
- **Email OTP vs magic link:** for a native Flutter Android app, a typed 6-digit code avoids App Links/deep-link verification, works when mail is read on another device, and keeps the token out of URLs (mail scanners and link-prefetchers can consume magic links). A magic link would need ≥128-bit tokens and an intermediate "click to confirm" page to survive scanners. Keep OTP.
- One subtle point: `secrets.randbelow` is unbiased (rejection sampling), so `% 10**6` bias issues don't apply.

### Gaps
- Did not retrieve OWASP's Forgot Password CS text in detail. It isn't needed because the contract explicitly excludes reset password.

## Q3. Session tokens: opaque hashed vs JWT; refresh rotation and reuse detection; idle vs absolute expiry; Android storage

### Takeaway
Opaque 256-bit CSPRNG tokens stored as SHA-256 hashes, with server-side revocation, are the right choice for a single server with MySQL; JWT adds nothing here. Two gaps in the current code: (1) **no refresh-reuse detection.** Rotation overwrites `sessions.refresh_hash`, so a stolen-then-rotated token simply yields SESSION_EXPIRED while the session stays alive for whoever rotated first. (2) **No absolute session lifetime.** Each refresh pushes `refresh_expires_at` 30 days forward, so a session can live forever. On Android the app already uses a custom Android Keystore AES-GCM file store with `allowBackup="false"`, which matches current guidance now that Jetpack Security's EncryptedSharedPreferences is deprecated.

### Cited Findings
- OWASP Session Management CS: storing tokens verbatim is acceptable only in a tightly controlled store. "If read-only disclosure of the store is in your threat model, store a one-way verifier instead" (cites RFC 6819 §4.3.2 token hashes). — [OWASP Session Mgmt CS](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html) (line 89)
- OWASP: "All sessions should implement an absolute timeout, regardless of session activity." Idle timeouts don't help once a session is hijacked, because the attacker can keep it active. Renewal timeouts complement idle and absolute timeouts for long-lived sessions. Expiry must be enforced server-side. — same source, lines 307-341
- OWASP OAuth2 CS: refresh tokens should be sender-constrained (DPoP/mTLS) or use "refresh token rotation (issuing new refresh tokens and invalidating old ones immediately to detect replay attempts)". — [OWASP OAuth2 CS](https://cheatsheetseries.owasp.org/cheatsheets/OAuth2_Cheat_Sheet.html) (lines 15, 75), referencing [RFC 9700 OAuth 2.0 Security BCP](https://www.rfc-editor.org/rfc/rfc9700.html)
- NIST 800-63B-4 reauthentication: AAL1 overall timeout SHOULD be ≤30 days, and an inactivity timeout MAY be applied. AAL2 overall ≤24 h, inactivity ≤1 h. — [NIST SP 800-63B-4](https://pages.nist.gov/800-63-4/sp800-63b.html)
- OWASP Mobile App Security CS: store secrets via Android Keystore, hardware-backed (TEE/StrongBox), falling back to the regular hardware-backed keystore if StrongBox is unavailable. — [OWASP Mobile CS](https://cheatsheetseries.owasp.org/cheatsheets/Mobile_Application_Security_Cheat_Sheet.html) (lines 93, 273-281)
- `EncryptedSharedPreferences` is marked deprecated in androidx.security-crypto 1.1.0, and the reference says to exclude it from backups. — [Android reference](https://developer.android.com/reference/androidx/security/crypto/EncryptedSharedPreferences) (via search summary; secondary write-ups: [Include Security, 2026-08](https://blog.includesecurity.com/2026/08/encryptedsharedpreferences-is-dead-heres-what-you-should-use-instead/), [ProAndroidDev](https://proandroiddev.com/goodbye-encryptedsharedpreferences-a-2026-migration-guide-4b819b4a537a))
- flutter_secure_storage v10 dropped the Jetpack Security backend and auto-migrates to a custom cipher (AES-GCM). It removed the `encryptedSharedPreferences` option, raised minSdk to 24, and says to upgrade to v10 before v11, which removes AES-CBC. — [flutter_secure_storage releases](https://github.com/juliansteenbakker/flutter_secure_storage/releases) (search summary; exact dates not verified)
- Current code: `_issue` creates 32-byte tokens with `secrets.token_bytes`, base64url, stores SHA-256 (`account.py:189-210`). `refresh_session` does `UPDATE sessions SET refresh_hash=new, refresh_expires_at=now+30d` (`:206`) and keeps no record of the old hash. `sessions` has no `created_at`/absolute cap in the contract schema. App: `SessionStore.kt` uses an AndroidKeyStore AES-256-GCM key, AAD "flexmix-session-v1", atomic temp+rename file; manifest `android:allowBackup="false"`. — code review

### Inferences
- **Opaque vs JWT:** keep opaque. JWT is useful when resource servers validate without a DB lookup. Here every access check already joins `access_tokens` to `sessions` (`authenticate_access`), giving instant revocation on logout, which JWT can't do without a denylist. Plain SHA-256 (no HMAC) is fine for 256-bit tokens because they can't be brute-forced.
- **Reuse detection (recommended design):** add `refresh_tokens(hash PK, session_id, issued_at, used_at NULL)` or `sessions.prev_refresh_hash`. On refresh, `SELECT … WHERE hash=? FOR UPDATE`:
  - if the token is current and unused, rotate it and mark it used;
  - if the token is **already used** (an old rotated token), treat it as a replay: `UPDATE sessions SET revoked_at=now` for the whole session, also killing its access tokens through the join, and return SESSION_EXPIRED.

  The contract's "app funnels every 401 into one in-flight refresh" makes false positives rare. The remaining risk is a lost response, where the server rotated but the app never received the new token and retries with the old one. Options: accept it (the user re-logs in), or allow a short grace window (for example 30 s) in which presenting the immediately previous token returns the *same* new pair. That second option needs storing the encrypted new token, which adds complexity, so recommend accept-and-relogin for the skeleton. This needs a planner/contract decision because it changes logout/refresh semantics.
- **Absolute expiry:** add `sessions.created_at` (or `absolute_expires_at`), set `refresh_expires_at = min(now+30d, created_at+ABS)` on rotation, and reject past ABS. NIST AAL1 suggests reauthentication ≤30 days. A mobile-app compromise might be 30-90 days. Recommend a 30-day idle (current) plus 90-day absolute, or 30-day absolute for strict NIST AAL1 alignment.
- **Access token 1 h:** reasonable. Access tokens are DB-checked, so revocation is immediate anyway. Rows accumulate, so add periodic cleanup of expired `access_tokens`/`otp_generations`.
- **Android:** the custom Keystore store is already the post-deprecation recommended pattern, so there is no need to adopt flutter_secure_storage. If the team wants a maintained plugin instead of the MethodChannel, use flutter_secure_storage ≥10 (custom AES-GCM backend). Keep `allowBackup=false`, or add `dataExtractionRules` excluding the session file, because the Keystore key doesn't survive restore and the blob would become undecryptable. The current code handles this by clearing on decrypt failure.

### Gaps
- RFC 9700 text was not fetched (rfc-editor.org blocked). The rotation/replay statement is cited through the OWASP OAuth2 CS, which quotes it.
- Did not verify the official Android "Cryptography" page wording on Jetpack Security deprecation directly. Only the reference page summary and blogs were seen.

## Q4. Atomic login-failure quota (open finding #1), rate limiting options, enumeration resistance

### Takeaway
The bug: `login()` checks `len(events) >= 10` under `state.guard`, releases the lock, runs DB plus Argon2 (about 100 ms+), then appends the failure under a *second* acquisition (`account.py:216-229`), so N concurrent requests can all pass the check. Fix it in-process (the contract says rate counters live in RAM in one process) with **admission reservation**: under one lock, prune, count `failures + in_flight`, reject if ≥ limit, else `in_flight += 1`; after verification, under the lock, `in_flight -= 1` and append a failure if it failed (in `try/finally`). This makes check-and-record atomic and also caps concurrent password verifications per IP, which the review notes as a planner option. Only a multi-process deployment needs a MySQL counter (`INSERT … ON DUPLICATE KEY UPDATE` or a `SELECT … FOR UPDATE` row).

### Cited Findings
- Review finding: with 9 seeded failures, 2 concurrent wrong logins both return AUTH_FAILED and the counter reaches 11 against a limit of 10 per 600 s. Suggested direction: atomic check+append, optionally IP admission. — `documentation/plan/account-module-review-2026-10-12.md` §1
- Contract: "Rate counters có hạn ở RAM một process" (rate counters are bounded, in RAM, single process). — `contracts/messages/auth.md`
- OWASP Authentication CS: lockout design parameters are lockout threshold and observation window. Generic error messages and equal processing time prevent enumeration, and brute-force protection limits enumeration at scale. — [OWASP Authentication CS](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html) (lines 146-194, 271-272)
- NIST §3.2.2 permits additional throttling techniques besides disabling (e.g. increasing wait times, bot challenges, risk-based controls). — [NIST SP 800-63B-4](https://pages.nist.gov/800-63-4/sp800-63b.html) (statement of "Additional techniques MAY be used"; specific list from secondary [oneuptime summary](https://oneuptime.com/blog/post/2026-08-29-how-to-rate-limit-mfa-code-attempts-without-creating-an-account-lockout-dos/view))
- MySQL `INSERT … ON DUPLICATE KEY UPDATE` performs insert-or-update as a single statement under the row/unique-key lock in InnoDB, and is the standard atomic counter upsert. — [MySQL 8.4 Reference: INSERT … ON DUPLICATE KEY UPDATE](https://dev.mysql.com/doc/refman/8.4/en/insert-on-duplicate.html) (not fetched this session; standard documented behaviour)
- `_send_gate` already does check+append in one critical section (`account.py:61-73`), so only login has the split. — code review

### Inferences
- **Recommended in-memory fix** (sliding-window log, as now, plus in-flight reservation):
  ```python
  def _login_admit(deps, ip):
      with deps.state.guard:
          now = deps.monotonic()
          ev = _events(deps, 'login_ip', ip, now, cfg.LOGIN_WINDOW_SECONDS)
          inflight = deps.state.login_inflight.get(ip, 0)
          if len(ev) + inflight >= cfg.LOGIN_FAILURE_LIMIT:
              oldest = ev[0] if ev else now
              raise ApiError('RATE_LIMITED', 429, max(1, math.ceil(oldest + cfg.LOGIN_WINDOW_SECONDS - now)))
          deps.state.login_inflight[ip] = inflight + 1

  def _login_release(deps, ip, failed):
      with deps.state.guard:
          n = deps.state.login_inflight.get(ip, 1) - 1
          if n: deps.state.login_inflight[ip] = n
          else: deps.state.login_inflight.pop(ip, None)
          if failed:
              _events(deps, 'login_ip', ip, deps.monotonic(), cfg.LOGIN_WINDOW_SECONDS).append(deps.monotonic())

  # login(): _login_admit(); failed = True
  # try: ... if valid: failed = False; return _issue(...)
  # finally: _login_release(deps, ip, failed)
  ```
  Behaviour: with 9 failures and 2 concurrent requests, the first is admitted (9+0<10) and the second rejected (9+1≥10), so the counter can't exceed 10. Edge cases:
  - When the rejection is caused only by in-flight requests (ev empty), retry_after falls back to the window. Use `1` instead if `ev` is empty, since in-flight resolves within a second.
  - A DB exception releases the slot without counting a failure; the `finally` is required.
  - It doesn't penalise legitimate success: successes free the slot without appending.
- Sequential correctness is unchanged. The only behaviour change is that once an IP has 9 failures it can have at most 1 concurrent attempt, which is the intended cap.
- **Simpler alternative:** a per-IP `RLock` held across verification, mirroring `_email_lock`, also serialises attempts per IP. But one slow Argon2 run blocks all users behind a shared NAT. Reservation is better.
- **Multi-process/MySQL option** (only if more than one server process is ever run):
  - Fixed window: `INSERT INTO login_failures(ip, window_start, n) VALUES(?, ?, 1) ON DUPLICATE KEY UPDATE n = n + 1`, with the check done as `SELECT n … FOR UPDATE` in the same transaction before verification, or "increment-first then decide" (count the attempt as a failure up front and decrement on success).
  - Sliding window: an events table with `DELETE … WHERE ts < now - 600` plus `COUNT(*)` under a `SELECT … FOR UPDATE` on a per-IP row.

  This costs a DB round-trip per login. Not needed now.
- **Token bucket vs sliding window:** a token bucket (capacity 10, refill 1 per 60 s) is O(1) memory and smooths bursts, but the contract wording ("10 failures/IP/10 min", retry_after = time until the oldest event leaves) maps directly onto the existing sliding-window log. Keep the log. Memory per IP is ≤10 floats. Add periodic pruning of empty deques and email_locks to bound RAM (currently `rate_events`, `email_locks`, `cooldown_until` grow without bound with distinct IPs/emails).
- **Enumeration resistance status:**
  - Register and send return the same CHECK_EMAIL. MAIL_UNAVAILABLE for unknown resend is a documented exception.
  - Verify returns OTP_INVALID for unknown/verified emails.
  - Login returns the same AUTH_FAILED **but differs in timing** (see Q1). Add the dummy verify.
  - A per-IP-only login quota allows distributed credential stuffing against one account. Consider an additional per-email failure counter (for example 20 per hour) with throttling (429), not hard lockout, to avoid victim DoS. That needs a planner decision because RATE_LIMITED on login with a known email is itself a small enumeration signal unless also applied to unknown emails, which it should be (count by normalized email regardless of existence).

### Gaps
- Behind a reverse proxy, `context.ip` must come from a trusted X-Forwarded-For, or all clients share one IP. Not checked in this research.

## Q5. Gmail SMTP: App Password, 587 STARTTLS vs 465, limits, Google 2025-2026 changes, alternatives, timeouts and async

### Takeaway
Gmail with an App Password over smtp.gmail.com:587 and STARTTLS (cert-verified via `ssl.create_default_context()`) still works for personal accounts with 2-Step Verification in 2026, and the code implements it correctly. It is a dev/demo transport only: personal Gmail is capped at about 500 messages per day, Google labels app passwords "not recommended", Workspace dropped password-only LSA access on 2025-05-01, and changing the Google password revokes the app password. For production, move to a transactional provider (Amazon SES is cheapest; Resend, Postmark and Mailgun have small free tiers) with SPF/DKIM/DMARC on an owned domain. Keep the 10 s timeout but note it is per socket operation, not total. Bound SMTP concurrency.

### Cited Findings
- App passwords require 2-Step Verification. An app password is a 16-digit passcode for apps that can't use Sign in with Google. Google says "app passwords aren't recommended and are unnecessary in most cases". The option is unavailable with security-key-only 2SV, some work/school accounts, or Advanced Protection. Changing the Google password revokes app passwords. — [Google Account Help: Sign in with app passwords](https://support.google.com/accounts/answer/185833?hl=en) (via search summary)
- Workspace: "Starting May 1, 2025, Google Workspace accounts no longer support less secure apps" (basic-auth IMAP/SMTP/POP/CalDAV/CardDAV). The earlier March 14, 2025 date was pushed back. For devices and apps Google says to use OAuth or an app password. SMTP relay (smtp-relay.gmail.com) is IP-authenticated. — [Workspace Admin Help: Transition from LSA to OAuth](https://support.google.com/a/answer/14114704?hl=en); [Workspace Updates blog](https://workspaceupdates.googleblog.com/2023/09/winding-down-google-sync-and-less-secure-apps-support.html); [Send email from a printer, scanner, or app](https://support.google.com/a/answer/176600?hl=en)
- Sending limits: Gmail Help says the limit error appears when sending "to a total of more than 500 recipients in a single email and or more than 500 emails sent in a day". Sending usually resumes within 1-24 h. The mail-merge help page states a standard Gmail account's daily limit is 500 and Workspace's is 2,000, with Cc/Bcc counted. — [Gmail Help 22839](https://support.google.com/mail/answer/22839?hl=en); [Gmail Help 12921167](https://support.google.com/mail/answer/12921167?hl=en). A Gmail Community post claims about 100 per rolling 24 h via mail clients (anecdotal, unofficial): [Gmail Community thread](https://support.google.com/mail/thread/251458705/new-gmail-account-sending-limits?hl=en)
- Secondary 2026 guides confirm smtp.gmail.com still accepts 587 (STARTTLS) and 465 (implicit TLS) with app passwords for personal accounts, with OAuth (XOAUTH2) as Google's preferred path. — [Nylas CLI guide](https://cli.nylas.com/guides/gmail-smtp-settings), [Mailer To Go guide](https://resources.mailertogo.com/guide/gmail-smtp-settings-host-port-authentication) (secondary; they disagree on exact LSA dates, so Google's own pages above are authoritative)
- Python smtplib: `SMTP(host, 587, timeout=…)` then `starttls(context=…)` then `ehlo()`, or `SMTP_SSL(host, 465, context=…, timeout=…)`. Using the wrong class for the port fails or hangs. — [Django ticket #17471](https://code.djangoproject.com/ticket/17471), [Django ticket #9575](https://code.djangoproject.com/ticket/9575); [Python smtplib docs](https://docs.python.org/3/library/smtplib.html) (the `timeout` applies to blocking operations such as the connection attempt, i.e. per socket operation)
- RFC 8314 (2018) recommends implicit TLS (port 465) over STARTTLS for submission. — [RFC 8314](https://datatracker.ietf.org/doc/html/rfc8314) (not fetched this session; known RFC content; treat as unverified here)
- Provider free tiers (secondary aggregators, mid-2026, partly conflicting):
  - Resend: 3,000 per month, capped at 100 per day.
  - Mailgun: 100 per day.
  - SendGrid (Twilio): permanent free plan reportedly retired; 60-day trial at 100 per day.
  - Postmark: 100 per month (status as "free plan" vs trial unclear).
  - Amazon SES: $0.10 per 1,000 emails. Conflicting reports on whether new accounts get 3,000 per month for 12 months or only AWS Free Tier credits.

  — [buildmvpfast email API pricing (Jul 2026)](https://www.buildmvpfast.com/api-costs/email), [devtoollab comparison](https://devtoollab.com/blog/best-email-api-providers), [dreamlit SendGrid alternatives](https://dreamlit.ai/blog/best-sendgrid-alternatives), [shipai SendGrid pricing](https://shipai.today/vibe-coding/sendgrid-pricing)
- Current code: `smtplib.SMTP('smtp.gmail.com', 587, timeout=10)`, `ehlo`, `starttls(context=ssl.create_default_context())`, `ehlo`, `login(user, app_password)`, `send_message(to_addrs=[email])`, refused-recipients check. Errors map to MAIL_AUTH/MAIL_SEND logs plus MAIL_UNAVAILABLE 502 with no transcript. `smtp_from == smtp_user` is enforced. The send runs synchronously inside `_email_lock` but outside the DB transaction (`account.py:99-138`, `smtp_mail.py:26-52`). — code review

### Inferences
- **587 vs 465:** both are fine; the current 587 path verifies the cert and hostname before AUTH because `create_default_context()` sets `check_hostname=True` and `CERT_REQUIRED`. The STARTTLS-stripping risk is mitigated because `starttls()` raises if the server doesn't offer it, so smtplib never sends AUTH in cleartext here. Switching to `SMTP_SSL('smtp.gmail.com', 465, context=ctx, timeout=10)` is a one-line change if RFC 8314 alignment is wanted. The contract currently mandates 587, so this would be a contract change.
- **XOAUTH2:** removes the app-password risk (a full-account credential in env) but needs a Google Cloud OAuth client, a stored refresh token, and token refresh code, with no stdlib helper. It isn't worth it for the skeleton. If the app ever goes public, move to a transactional provider instead.
- **Timeout:** `timeout=10` bounds each blocking call, so the connect, greeting, EHLO, STARTTLS handshake, AUTH and DATA steps can each take up to 10 s; the worst case is tens of seconds. To get a true total cap, run the send in a `concurrent.futures.ThreadPoolExecutor(max_workers=2-4)` and call `future.result(timeout=15)`. On timeout, return MAIL_UNAVAILABLE and mark the generation failed. The thread may finish later and deliver an OTP whose generation is "failed", which is harmless because it can't be verified. Also log elapsed time.
- **Async vs contract:** the contract requires a synchronous MAIL_UNAVAILABLE on SMTP failure and "publish active only after SMTP success", so a fire-and-forget outbox would break the wire semantics. The bounded executor gives the HTTP thread a hard deadline while keeping the semantics. A durable outbox with a background worker would need a contract change (always return CHECK_EMAIL).
- **Concurrency/limits:** sending holds the per-email lock (fine) but not a global cap. A bounded executor also prevents a flood of parallel SMTP logins, which Gmail may throttle or flag. The existing per-IP and per-email send gates keep volume far below 500 per day for a demo. Add a global daily counter (for example stop at 400 per day and return MAIL_UNAVAILABLE) so the project account isn't suspended.
- **Deliverability:**
  - Sending From a @gmail.com address through Gmail's own SMTP passes Gmail's SPF and DKIM, so inbox placement for small volume is generally fine.
  - Add `Date` and `Message-ID` headers (`email.utils.formatdate(localtime=False)`, `make_msgid()`), since `EmailMessage` doesn't add them. Gmail typically fills them in, but explicit is safer.
  - Keep plain text and avoid links.
  - Put the code in the subject (e.g. "123456 is your FlexMix code") for usability; this needs a contract decision.
- **Production recommendation:**
  - Amazon SES: lowest cost, needs domain verification and leaving the sandbox.
  - Postmark: strong transactional deliverability reputation, but small free volume.
  - Resend: simple API and 3,000 per month free.

  All support SMTP, so `smtp_mail.py` only needs host, port and credentials changed. You must own a domain and publish SPF, DKIM and DMARC records.

### Gaps
- Could not fetch Google's live help pages (sandbox block). Facts come from search summaries of those pages, some cached copies 1-4 years old, so the current exact wording may differ.
- No primary-source confirmation of 2026 provider free tiers. Aggregators conflict for SES and Postmark, so verify on vendor pricing pages before choosing.
- No official Google statement found on any 2026 plan to remove app passwords for *personal* accounts. Secondary blogs speculate, and none were confirmed.

## Appendix-style notes on the other open finding (kept within Q-structure scope)
- Confirm-password field (finding #2): `auth_page.dart` has controllers only for `_email` and `_password` (lines 25-28). The confirmation `TextFormField` (`key: ValueKey('confirmation')`, about line 285) has no controller, so `_password.clear()` (lines 46, 72, 83) doesn't clear it. Fix: add `final _confirmation = TextEditingController();`, attach it to that field, call `_confirmation.clear()` next to every `_password.clear()` and on the "Sai email? Quay lại" (wrong email? go back) boundary, dispose it in `dispose()`, and add a widget test that enters text, navigates to OTP, taps back, and expects both fields empty. (Code review; no external source needed.)
