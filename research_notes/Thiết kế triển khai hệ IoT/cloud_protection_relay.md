# Cloud protection (TLS + phong bì HPKE) và relay lệnh long-poll / trạng thái online

Scope: application-layer protection between Flutter Android app ↔ Python server ↔ Raspberry Pi, and the MACHINE_COMMAND_SEND / MACHINE_COMMAND_POLL / MACHINE_RESULT_SEND relay with "Kết nối cloud" online state. Baseline read: `contracts/messages/cloud-protection.md`, `contracts/messages/relay-status.md`, `contracts/COMPATIBILITY.md`, `server/src/cloud_protection.py`, `server/src/http.py`.

Method note: in this session the WebFetch tool could not resolve hosts (rfc-editor.org, ietf.org and cryptography.io all failed DNS through the egress proxy). Findings therefore come from (a) web-search result summaries, (b) **local experiments** run in the scratchpad with `cryptography 50.0.2` and `PyHPKE 0.6.5` installed from PyPI, against the official CFRG HPKE `test-vectors.json` downloaded from GitHub, and (c) the repo's own code. Anything recalled from prior knowledge and not re-verified this session is labeled **(prior knowledge, not re-verified)** and kept in Inferences/Gaps, not Cited Findings.

---

## Q1. How does the current design compare to RFC 9458 OHTTP / BHTTP and to the alternatives (TLS-only + pinning, mTLS device keys, JOSE, COSE/OSCORE, Ed25519)? Is the double layer worth it for an MVP; what is the minimal secure alternative?

### Takeaway
The current "TLS + HPKE mode_base request, response key from the HPKE exporter" design is structurally the same as the OHTTP (RFC 9458) encapsulation, minus BHTTP and minus the relay; it is sound and the user has already locked two layers (`User chốt giữ hai lớp`), so keep it. The minimal secure alternative would be TLS 1.3 + SPKI pinning + bearer tokens for the app and a per-request signature (device key + timestamp + nonce) for the machine. The inner layer is worth it only for end-to-end protection past a TLS-terminating proxy and to bind every request to the pinned server key. For an MVP it is extra cost, but it is justifiable and already decided.

### Cited Findings
- RFC 9458 (Jan 2024, Thomson & Wood) defines Oblivious HTTP: HPKE-encapsulated HTTP messages are forwarded so that the gateway never sees the client IP and the relay never sees plaintext. The gateway encapsulates the response per Section 4.4 — [RFC 9458 (IETF)](https://www.ietf.org/rfc/rfc9458.html), [datatracker](https://datatracker.ietf.org/doc/html/rfc9458)
- The OHTTP response key is derived from the request context's exporter: `secret = context.Export("message/bhttp response", Nk)` with secret length = max(AEAD key length, nonce length) — [Google QUICHE oblivious_http_response.cc](https://quiche.googlesource.com/quiche.git/+/38097a7a48d5f7d0853ec0ece88269c08283c9c7/quiche/oblivious_http/buffers/oblivious_http_response.cc)
- The project's design uses the same pattern: `export("flexmix-response-v1",16)` gives the AES-128 response key, a random 12-byte nonce is used, and the AAD is `J(["flexmix-response-v1",send_id,http_status,route])` — `contracts/messages/cloud-protection.md` §Phản hồi (repo).
- Bouncy Castle's HPKE docs say export-only use (no seal/open) is the intended way to derive a key, through `HPKEContext.export(byte[] exporterContext, int L)` — [BC HPKE package summary](https://downloads.bouncycastle.org/java/docs/bcprov-jdk15to18-javadoc/org/bouncycastle/crypto/hpke/package-summary.html), [BC HPKEContext](https://downloads.bouncycastle.org/java/docs/bcprov-jdk18on-javadoc/org/bouncycastle/crypto/hpke/HPKEContext.html)
- OSCORE's (RFC 8613) built-in replay protection is counter-based: per-sender sequence numbers plus a server replay window, configurable from 1 to 63 with a default of 32 in libcoap. A delayed request is still accepted as fresh unless the RFC 9175 Echo option is used, which costs one extra round trip — [libcoap coap-oscore-conf(5)](https://www.mankier.com/5/coap-oscore-conf), [Krentz & Voigt, NDSS SDIoTSec 2024](https://ndss-symposium.org/wp-content/uploads/sdiotsec2024-3-paper.pdf), [Zephyr OSCORE docs](https://docs.zephyrproject.org/latest/services/connectivity/networking/api/coap_oscore.html)

### Inferences
- **Mapping to OHTTP.** The design follows RFC 9458 §4.4, with these differences:
  1. The request header (`kid`, route, method, receiver, send_id, sent_at_ms, machine_key_id) goes into the AEAD **AAD** of `seal`. OHTTP instead puts its header (key_id, kem_id, kdf_id, aead_id) into the HPKE **info** string after `"message/bhttp request"` **(prior knowledge, not re-verified)**. Both approaches bind the header. AAD is fine here and simpler.
  2. OHTTP derives the response AEAD key and nonce through HKDF from `salt = enc || response_nonce` **(prior knowledge, not re-verified)**. The project uses the exporter output directly as the AES key, with a random 12-byte nonce. This is safe because each exported key encrypts exactly **one** message: a fresh HPKE context per request gives a fresh key, so even a fixed nonce would not reuse a (key, nonce) pair. The random nonce adds margin. OHTTP's salt step mainly guards against a reused or derived context, which the contract already forbids ("Một context cho một request/response duy nhất").
  3. There is no BHTTP: the JSON `{auth,body}` plaintext replaces Binary HTTP. That is acceptable because route and method are bound in the AAD.
  4. There is no relay and no anonymity goal. The inner layer here gives (a) end-to-end confidentiality and integrity to the Python process even if TLS is terminated by a reverse proxy, CDN or corporate MITM CA, (b) implicit server authentication through the pinned HPKE key (`assets/server-trust.json`), so a mis-issued TLS certificate is not enough, and (c) machine-envelope signatures that bind identity to ciphertext.
- **Alternatives, ranked for this project:**
  - *TLS-only + SPKI pinning (app) + device signature on each request (machine):* this is the minimum that is still secure. It is about 30–40% of the code. You lose protection against a TLS-terminating middlebox reading bodies (OTP, seal_code, tokens). Pinning also gives the "mis-issued certificate" protection that the HPKE pin gives today. Use it as the fallback if the Kotlin/Python HPKE cross-vectors block A-01/S-01, but the user has locked "Không TLS-only".
  - *mTLS with device certificates:* the contract explicitly rejects it ("không mTLS/chứng chỉ xưởng"). It also needs a CA and certificate lifecycle on the Pi and does not survive a TLS-terminating proxy. Not recommended.
  - *JOSE (JWE ECDH-ES + A128GCM, JWS ES256/EdDSA):* this is a viable standard. On the server it needs a non-stdlib library (jwcrypto/authlib), and on Android a library such as Nimbus. JWE has no exporter, so OHTTP-style response keying would have to be built separately (for example, a second JWE to a client ephemeral key). JOSE also has a history of algorithm-confusion pitfalls. HPKE plus a fixed suite is smaller and less ambiguous.
  - *COSE / OSCORE (RFC 8613):* designed for CoAP and constrained devices. It relies on pre-shared master secrets, a per-sender sequence number and a replay window, and needs EDHOC to establish keys. It adds no value over HTTPS for a Pi and Flutter, and Python and Dart/Kotlin library maturity is weaker. Not recommended. Its replay model is still instructive (see Q4).
- **Verdict:** keep the two layers (already decided). Do not add BHTTP or an OHTTP relay. Optionally rename the exporter label to the OHTTP style in the spec text only (`flexmix-response-v1` is fine). The important part is that no other export in the protocol reuses that label.

### Gaps
- I could not fetch the RFC 9458 text to quote §4.4 (salt/prk/"key"/"nonce" labels) or §6.5 on replay. Those details are prior knowledge, apart from the export label, which QUICHE confirms.
- No public benchmark was found for HPKE seal/open cost on a Raspberry Pi. X25519 plus AES-GCM is believed negligible at the project's request rates (inference).

---

## Q2. PyHPKE 0.6.5 vs `cryptography` built-in HPKE vs Bouncy Castle on Android; exporter correctness; nonce for the one-shot response key

### Takeaway
`cryptography` added an HPKE module in 47.0.0, but in 50.0.x it is a **single-shot `Suite.encrypt/decrypt(plaintext, key, info)` API with no AAD and no exporter**, so it cannot implement this protocol. Keep **PyHPKE 0.6.5** on the server and the Pi: it passed the official RFC 9180 mode_base vector, including export, in a local run. Use BC `HPKE.setupBaseS/R` + `HPKEContext.seal/open/export` on Android.

### Cited Findings
- `cryptography` 47.0.0 introduced `hazmat.primitives.hpke` (RFC 9180) with `Suite(KEM.X25519, KDF.HKDF_SHA256, AEAD.AES_128_GCM)` and `encrypt`/`decrypt`. It also added hybrid ML-KEM keys (`MLKEM768X25519`, `MLKEM1024P384`), and the changelog notes `KEM.enc_length` "so callers can split the encapsulated key from the ciphertext returned by Suite.encrypt" — [cryptography 47.0 HPKE docs](https://cryptography.io/en/47.0.0/hazmat/primitives/hpke/), [cryptography latest HPKE docs](https://cryptography.io/en/latest/hazmat/primitives/hpke/), [SUSE python-cryptography.changes (downstream)](https://sources.suse.com/SUSE:SLFO:Products:Multi-Linux-Manager:MCP:Main/python-cryptography/d0ba51d69e7de6d0742b48f459437180/python-cryptography.changes)
- **Local experiment (cryptography 50.0.1 system / 50.0.2 venv):**
  - `help(hpke.Suite)` shows only `encrypt(self, /, plaintext, public_key, info=None)` and `decrypt(self, /, ciphertext, private_key, info=None)`. There is no `aad`, no `export`, no context object and no PSK/auth mode.
  - `KEM` = {X25519, P256, P384, P521, MLKEM768, MLKEM1024, MLKEM768_X25519, MLKEM1024_P384}; `KDF` = {HKDF_SHA256/384/512, SHAKE128/256}; `AEAD` = {AES_128_GCM, AES_256_GCM, CHACHA20_POLY1305}.
  - Encrypting 2 bytes gives 50 bytes (= enc32 ‖ ct2 ‖ tag16), so the output is the concatenated one-shot format.
  - (scratchpad run, 2026-10-12)
- **Local experiment (PyHPKE 0.6.5):** `CipherSuite.new(DHKEM_X25519_HKDF_SHA256, HKDF_SHA256, AES128_GCM)` exposes `create_sender_context(pk, info=)` → `(enc, ctx)`, `ctx.seal(pt, aad=)`, `create_recipient_context(enc, sk, info=)`, `ctx.open(ct, aad=)` and `ctx.export(exporter_context, L)`. Sender and recipient exports were equal (scratchpad run).
- **Local experiment: RFC 9180 vector.** Running PyHPKE 0.6.5 on the CFRG `test-vectors.json` entry mode=0, kem_id=32, kdf_id=1, aead_id=1: `open(encryptions[0])` == pt **True**, and `export(exporter_context="", L=32)` == `exported_value` **True**. Values from that entry: `info`=`4f6465206f6e2061204772656369616e2055726e` ("Ode on a Grecian Urn"); `pkRm`=`3948cfe0ad1ddb695d780e59077195da6c56506b027329794ab02bca80815c4d`; `enc` starts `37fda3567bdbd628…`; first export (ctx "", L=32) = `3853fe2b4035195a573ffc53856e77058e15d9ea064de3e59f4961d0095250ee`; export contexts in the vector are `""`, `00`, `"TestContext"`, all with L=32 — [CFRG HPKE test-vectors.json](https://raw.githubusercontent.com/cfrg/draft-irtf-cfrg-hpke/master/test-vectors.json)
- **Local experiment:** in PyHPKE, `export(ctx, 16)` is **not** a prefix of `export(ctx, 32)`, because L enters the labeled HKDF-Expand. A 16-byte exporter fixture cannot be cut down from the 32-byte RFC vectors (scratchpad run).
- Bouncy Castle `HPKEContext` exposes `seal(aad, pt)`, `open(aad, ct)` and `export(exporterContext, L)`. Senders use `setupBaseS` + `getEncapsulation()` and receivers use `setupBaseR(enc, keyPair)`. Static `HPKE.seal/open` cover single messages. The same API appears in the 1.77, 1.81 and 1.85 Javadocs — [BC HPKEContext](https://downloads.bouncycastle.org/java/docs/bcprov-jdk15to18-javadoc/org/bouncycastle/crypto/hpke/HPKEContext.html), [BC HPKE](https://downloads.bouncycastle.org/java/docs/bcprov-jdk18on-javadoc/org/bouncycastle/crypto/hpke/HPKE.html), [BC package summary](https://downloads.bouncycastle.org/java/docs/bcprov-jdk15to18-javadoc/org/bouncycastle/crypto/hpke/package-summary.html)

### Inferences
- **Library choice:**
  - *Server and Pi:* keep PyHPKE 0.6.5, pinned, together with the `cryptography` version it uses as backend. Use `cryptography` directly only for AESGCM on the response, ECDSA/Ed25519 and X25519 key loading. Re-check pyca's HPKE at each major release. If it adds `aad=` and an exporter, you can drop PyHPKE. Until then, PyHPKE is the only option of the two that supports this protocol.
  - *Android:* BC `bcprov-jdk15to18` 1.86 through MethodChannel, as the contract says. Register BC as a library object (`org.bouncycastle.crypto.hpke.HPKE`), **not** as a JCA provider replacing Android's stripped "BC" provider. Call the lightweight API directly to avoid name clashes with the platform's built-in BC copy **(prior knowledge, not re-verified)**. Keep R8/ProGuard rules for `org.bouncycastle.crypto.hpke.**`.
  - Do not implement HPKE in Dart (the contract already says so).
- **Exporter correctness checklist (both sides):**
  1. The client keeps the **sender** context after `seal`. The server's **recipient** context calls `export("flexmix-response-v1", 16)`. The values match only if `info` (`flexmix-cloud-v1`) and `enc` are identical.
  2. Never respond with `ctx.seal` on the recipient side. HPKE base contexts are unidirectional; a recipient can only open. The contract's "không dùng sender context.seal ở hướng ngược" is correct.
  3. Response: `nonce = os.urandom(12)` / `SecureRandom`; `ct = AESGCM(key).encrypt(nonce, pt, AAD_resp)`; send `{pv:1, send_id, status, nonce: b64u(nonce), ct: b64u(ct‖tag)}`. The client checks that `send_id` matches its pending context **before** decrypting, and recomputes the AAD from its own expected `route` and the HTTP status it received. It never takes the route from the response.
  4. Zero the key and drop the context after one open, whether it succeeded or failed (already in the contract).
  5. Fixed-nonce variant: since every key is single-use, a fixed zero nonce would also be safe. Keep the random nonce, though, so that a context-reuse bug does not become catastrophic GCM nonce reuse.
- **Test vectors to put in `tests/fixtures/crypto/`:**
  - (a) The RFC 9180 A.1 base vector above, run through Python **and** Kotlin. Check open of `encryptions[0..n]` with their AADs, then all three `exports` at L=32.
  - (b) A project-specific fixture built from deterministic test-only seeds (`kem.derive_key_pair(seed)` / BC `deriveKeyPair`). Generate it **once** with PyHPKE, cross-check it independently with BC before committing, and record the 16-byte export for `flexmix-response-v1`. The contract requires that expected bytes not come from a self-made oracle, so the second-implementation agreement is the acceptance criterion.
  - (c) Negative tests: flip one byte each in kid, route, send_id, sent_at_ms, enc, ct, tag and sig; wrong info; wrong export label; reuse of a context for a second response.

### Gaps
- I could not open the pyca changelog page to confirm whether a version after 50.0 added AAD or exporter support. The local 50.0.2 API shows neither.
- I did not confirm whether BC 1.86 specifically (versus 1.85) changed anything in `crypto.hpke`. The Android-specific packaging of BC HPKE was not documented in the results.

---

## Q3. ECDSA low-s in Python and Kotlin; is low-s needed? Ed25519 availability

### Takeaway
pyca `cryptography` **accepts high-s** P-256 signatures (verified locally), so a low-s rule must be enforced by hand: the signer normalizes and the verifier rejects. Low-s is defense-in-depth here, not security-critical, because nothing keys on signature bytes. Every signer and verifier is Python (Pi and server), and the Android app never signs or verifies machine envelopes, so **Ed25519 is fully viable** and simpler: pyca rejects non-canonical Ed25519 S (verified). Switch to Ed25519 if S-01/M-01 code is not frozen yet, unless you plan a P-256-only secure element (e.g. ATECC608) on the Pi.

### Cited Findings
- **Local experiment:** with pyca `cryptography` 50.0.2, the P-256 signature `(r, n−s)` (the high-s twin) was accepted by `public_key.verify(..., ec.ECDSA(SHA256()))`, so pyca/OpenSSL does not enforce low-s (scratchpad run).
- **Local experiment:** Ed25519 `verify` rejected a signature whose S was replaced by S+L (`InvalidSignature`), so pyca enforces canonical S for Ed25519 (scratchpad run).
- ECDSA is inherently malleable because (r, −s mod n) also verifies. Bitcoin BIP 146 requires s ≤ n/2, and libsecp256k1 accepts only lower-half s while offering a normalization function — [BIP 146](https://bips.dev/146/)
- Android added the `java.security.interfaces.EdECKey` (RFC 8032 EdDSA) interface in API level 33 — [Android EdECKey reference](https://developer.android.com/reference/kotlin/java/security/interfaces/EdECKey?authuser=0)
- Conscrypt in Android 14 added "limited X25519 support for keys, key agreement, and signatures" — [AOSP Conscrypt module docs](https://source.android.com/docs/core/ota/modular-system/conscrypt?hl=vi)
- Android Keystore's documented example generates P-256 (`secp256r1`) keys with KeyGenParameterSpec (API 23+). The documented key algorithms include EC and XDH; Ed25519 was not found in the results — [KeyGenParameterSpec](https://developer.android.com/reference/kotlin/android/security/keystore/KeyGenParameterSpec), [KeyPairGeneratorSpec](https://developer.android.com/reference/kotlin/android/security/KeyPairGeneratorSpec?authuser=5)
- A Flutter plugin that signs with Ed25519 on Android uses libsodium and stores keys in SharedPreferences rather than KeyStore, an indirect sign that KeyStore Ed25519 is not commonly relied on — [pub.dev asymmetric_crypto_primitives](https://pub.dev/documentation/asymmetric_crypto_primitives/latest/)
- In the contract, the app always sends `sig=null, machine_key_id=null`. Machine signatures (envelope, bind proof, claim-accept) are made by the Pi and verified by the server, and the server's claim signature is verified by the Pi — `cloud-protection.md` (repo).

### Inferences
- **Is low-s needed?** Malleability lets an attacker produce a second valid signature over the **same** bytes. It matters only if signature bytes serve as an identifier or dedup key (the Bitcoin txid case). Here replay dedup uses `(kid, send_id)`, and send_id is inside the signed AAD, so a malleated signature is still caught by the replay cache. Low-s is therefore not required for security. It is cheap, gives one canonical encoding for fixtures, and is already in the contract, so keeping it is fine.
- **Python implementation (P-256):**
  ```
  N = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
  sign: der = sk.sign(msg, ec.ECDSA(SHA256())); r,s = decode_dss_signature(der)
        if s > N//2: s = N - s
        return r.to_bytes(32,'big') + s.to_bytes(32,'big')
  verify: if len(sig)!=64: reject
          r = int.from_bytes(sig[:32]); s = int.from_bytes(sig[32:])
          if not (1 <= r < N and 1 <= s <= N//2): reject       # zero/out-of-range/high-s
          pk.verify(encode_dss_signature(r,s), msg, ec.ECDSA(SHA256()))
  ```
  `server/src/cloud_protection.py` already imports `encode_dss_signature`. Check that `verify_machine_signature` contains the `s <= N//2` check, because pyca will not do it.
- **Kotlin:** the contract has no Kotlin ECDSA path today. If one appears (for example, the app verifying `server-sign-1`), JCA `SHA256withECDSA` and BC `ECDSASigner` return DER or (r, s) **without** normalization **(prior knowledge, not re-verified)**. Decode DER (BC `ASN1Sequence` / `DLSequence`), apply `if (s > N.shiftRight(1)) s = N - s`, and left-pad each value to 32 bytes. `BigInteger.toByteArray()` may emit 33 bytes with a leading 0x00 or fewer than 32, which is a classic pitfall.
- **Ed25519 recommendation:**
  - It is deterministic (no RNG/nonce-reuse risk on a Pi with low early-boot entropy), canonical (no low-s logic), and compact (32-byte public key, 64-byte signature).
  - It is native in pyca (`Ed25519PrivateKey`, raw encoding via `public_bytes(Encoding.Raw, PublicFormat.Raw)`).
  - Android availability does not matter because the app never signs. BC also ships Ed25519 (`Ed25519Signer`) for any API level if needed **(prior knowledge)**.
  - Keep P-256 only if hardware key storage on the Pi is planned (common secure elements like ATECC608 are P-256 only; prior knowledge) or if contracts are frozen.
  - If you switch, change `cloud-protection.md` (public key b64u raw32, sig raw64, no low-s clause), the trust asset `signing.public_key`, and the fixtures.

### Gaps
- Whether Android KeyStore supports hardware-backed Ed25519 at any API level was not confirmed. It does not matter for this design because the app holds no signing key.
- Whether OpenSSL/pyca Ed25519 verify enforces the small-order or cofactored checks (ZIP-215 vs RFC 8032 strict) was not checked beyond the S < L test.

---

## Q4. Replay protection: RAM cache lost on restart, timestamp window, monotonic clock bootstrap; how OHTTP and OSCORE handle it

### Takeaway
The send_id cache plus the ±300 s window is the standard "timestamp + nonce cache" pattern. A 10-minute TTL is correct (it must be ≥ 2 × skew). The one real gap is **restart**: a captured envelope with sent_at in the last 300 s before a crash can be replayed afterwards. Close it cheaply with a **boot floor**: reject `sent_at_ms < server_boot_wall_ms`. OSCORE solves the same problem with sequence numbers and an Echo round-trip after reboot. OHTTP leaves replay to the gateway (Date checks / anti-replay). Business idempotency (request_id/claim_id) is the second line of defense.

### Cited Findings
- OSCORE: sequence numbers prevent replay, and the server keeps a replay window (libcoap: 1–63, default 32). libcoap's "server rebooting Replay Window" option is tied to RFC 8613 Appendix B.1.2 and enabled by default — [Zephyr OSCORE](https://docs.zephyrproject.org/latest/services/connectivity/networking/api/coap_oscore.html), [coap-oscore-conf(5)](https://www.mankier.com/5/coap-oscore-conf)
- Counter-only OSCORE accepts delayed requests as fresh. The Echo option (RFC 9175) lets servers check that a request was created recently, at the cost of an extra round trip — [Krentz & Voigt, NDSS SDIoTSec 2024](https://ndss-symposium.org/wp-content/uploads/sdiotsec2024-3-paper.pdf), [RFC 9175 datatracker](https://datatracker.ietf.org/doc/rfc9175/)
- Repo contract: cache `(kid, send_id)` 10 minutes in RAM with max 10000 entries; when full, reject with RATE_LIMITED without evicting live entries; `|sent_at − server_now| ≤ 300000 ms`; time from the bootstrap route (`sent_at_ms=0` only on bootstrap/challenge/hello); the client computes `server_time_ms + (monotonic_now − receipt)`; refresh every 5 minutes, after a restart, or after INVALID_ENVELOPE — `cloud-protection.md` (repo).
- Python `ThreadingHTTPServer` state is per-process, and the contract accepts "Restart xóa RAM state" — `cloud-protection.md` (repo).

### Inferences
- **The window math is right:** an envelope is acceptable only while `now ∈ [sent_at−300 s, sent_at+300 s]`, a 600 s span, so a 10-minute cache TTL covers every accept window. Prune by `sent_at_ms + 300 s`, i.e. store the expiry with the entry, not the insertion time.
- **The restart gap and its fix (recommended contract change, S-01):** at boot, record `boot_wall_ms = time.time_ns()//1_000_000` and reject any envelope with `sent_at_ms < boot_wall_ms` (same INVALID_ENVELOPE). Legitimate clients compute sent_at from a server-time estimate plus elapsed time, so their next request has sent_at ≥ the real now > boot_wall_ms. A client that bootstrapped before the restart still produces correct times; only requests sealed before the restart fail, and those were in flight anyway. The extra state is one integer, with no persistence. It is analogous to OSCORE's reboot rule (refuse old state, force fresh proof) without the Echo round trip.
- **The server wall clock must be NTP-disciplined.** A backward step of the server clock reopens old windows, and a forward step rejects clients. Use `time.time()` only for sent_at comparison and `time.monotonic()` for every TTL and deadline (cache expiry, pending 15 s, poll 20 s, grace 30 s).
- **Client monotonic sources:**
  - *Pi (Python):* `time.monotonic()` (CLOCK_MONOTONIC). The Pi does not suspend, so this is fine.
  - *Android:* use `SystemClock.elapsedRealtime()`, which counts deep sleep, through the MethodChannel. Dart `Stopwatch` follows the monotonic clock that may stop in doze **(prior knowledge, not re-verified)**. The 5-minute refresh rule limits the damage either way.
  - Roundtrip ≤ 5 s means the offset error is ≤ 2.5 s, which is negligible against 300 s.
- **Order of checks** (contract): size → route/kid/pv → outer signature (if bound) → HPKE open → skew → replay insert → schema → auth → handler. Inserting into the replay cache **after** authentication (signature/AEAD) is important: otherwise unauthenticated junk could fill the 10000 slots. One residual issue: anonymous app envelopes can be minted by anyone holding the public HPKE key, so cache exhaustion is limited only by rate limits. Add a per-IP cap on new anonymous send_ids per minute if RATE_LIMITED from a full cache becomes a DoS vector.
- **Cache sizing:** 10000 entries / 600 s ≈ 16 req/s sustained before RATE_LIMITED. That is fine for the MVP; make the limit configurable in `skeleton.py`.
- **Replay vs retries:** each HTTP retry uses a new send_id, so dedup of business effects relies on request_id/claim_id/challenge_id (already in the contracts). Replay protection stops duplicates of a message; idempotency stops duplicates of an operation. Both are needed.

### Gaps
- I could not quote RFC 9458's replay section (I recall it recommends that gateways bound replay with a Date/time window and anti-replay strategies, citing RFC 8470; not re-verified).
- The exact RFC 8613 Appendix B.1.2 reboot procedure (Echo-based window re-initialization) was not quoted from the RFC.

---

## Q5. Long-poll vs WebSocket vs MQTT vs SSE for command relay to a Pi behind NAT; presence; ThreadingHTTPServer limits; correlation and idempotency

### Takeaway
For one server, stdlib-only, read-only status, **HTTP long-poll is the right MVP choice**. It traverses NAT and proxies, reuses the HPKE envelope as-is, and matches the request/timeout semantics of Azure IoT Hub "direct methods" (offline → immediate error; no reply → 504). The 30 s grace = 1.5 × the 20 s poll mirrors MQTT keep-alive practice. The two concrete risks are (1) the shared 64-slot semaphore, because every online machine permanently holds a slot, and (2) at-most-once delivery, which is fine for `machine.status.read` but **not** for a future "dispense" command without machine-side dedup. MQTT (mosquitto) is the upgrade path, not the MVP.

### Cited Findings
- Azure IoT Hub direct methods "either succeed or fail after the time-out period (default 30 seconds; settable between 5 and 300 seconds)". They are for cases where the device should act only if online. The invoke is an HTTPS POST with `connectTimeoutInSeconds` and `responseTimeoutInSeconds`; 404 = device offline, 504 = no response within timeout. Device side uses MQTT/AMQP (topic `$iothub/methods/POST/{method}/`) — [Azure IoT Hub direct methods devguide](https://learn.microsoft.com/en-my/azUre/iot-hub/iot-hub-devguide-direct-methods), [Azure China devguide](https://docs.azure.cn/es-es/iot-hub/iot-hub-devguide-direct-methods), [C2D guidance](https://learn.microsoft.com/en-us/azure/iot-hub/iot-hub-devguide-c2d-guidance)
- AWS IoT presence: `$aws/events/presence/connected|disconnected/{clientId}` events can arrive out of order or duplicated. A client is disconnected with MQTT_KEEP_ALIVE_TIMEOUT after **1.5×** the keep-alive with no traffic (keep-alive 30–1200 s). A device that silently drops is reported only after that timeout — [AWS IoT lifecycle events](https://docs.aws.amazon.com/iot/latest/developerguide/life-cycle-events.html), [re:Post on missing disconnect](https://www.repost.aws/questions/QU_ER8srIYQRaZNNH9od_Q1g/iot-disconnected-lifecycle-event-is-not-generated-on-device-power-network-loss)
- RFC 6202 (informational, April 2011) documents long polling and streaming: the server holds the request until an event or timeout, then the client immediately re-polls. It has sections on timeouts (5.5), proxies (5.3) and intermediaries (5.6) — [RFC 6202](https://datatracker.ietf.org/doc/html/rfc6202)
- **Local inspection (CPython 3.13):** `class ThreadingHTTPServer(socketserver.ThreadingMixIn, HTTPServer): daemon_threads = True`; `BaseHTTPRequestHandler.timeout` defaults to `None` (no socket timeout); `ThreadingMixIn.block_on_close = True`. The repo sets `request.settimeout(cfg.HTTP_READ_SECONDS)` (`server/src/http.py` lines 57, 70, 128).
- ThreadingMixIn spawns a thread per connection, so deployments should cap concurrency. Slowloris-style slow clients exhaust threaded servers that lack read timeouts — [ThreadingMixIn note](https://zybuluo.com/JunQiu/note/1350528), [LWN on slowloris](https://lwn.net/Articles/338430/)
- Repo timing config: pending 15 s, poll 20 s, machine HTTP 25 s, app relay HTTP 20 s, grace 30 s, terminal cache 60 s, max 1 open poll and 1 pending status per machine — `contracts/COMPATIBILITY.md` (repo).

### Inferences
- **Transport comparison for this project:**

  | Option | NAT/proxy | Fits HPKE envelope | Extra infra | Presence | Verdict |
  |---|---|---|---|---|---|
  | Long-poll (current) | Yes, plain HTTPS | Yes: command inside the encrypted poll response | none | last_poll_at + grace | **MVP** |
  | WebSocket | Usually; some proxies drop idle ones | Needs per-frame envelopes and its own replay design | non-stdlib lib (websockets/asyncio) | connection state + pings | later, only if latency < 1 s matters |
  | SSE | Yes | Server→Pi only; results still go over POST | stdlib possible | stream state | no advantage over long-poll here |
  | MQTT (mosquitto) | Yes (TLS 8883 or WSS 443) | Payload-level HPKE possible, but broker auth/ACLs become a second identity system | broker process, per-device creds, ACLs | LWT + keep-alive 1.5× | production path at fleet scale |

  The contract bans Redis/Flask, so MQTT is out of scope until a multi-server phase.
- **Timeout chain check:** app HTTP 20 s > pending 15 s ✓; machine HTTP 25 s > poll 20 s ✓; grace 30 s ≥ 1.5 × 20 s ✓ (the same rule as AWS keep-alive); pending 15 s < poll 20 s, so a command created between polls is still delivered on the next poll.
  - Define `last_poll_at` as the monotonic time a poll **ended** (response written) or started, whichever is later. With grace 30 s, a machine whose next poll is delayed more than 10 s (e.g. a crypto/clock bootstrap) shows offline.
  - Also add a small machine-side jitter (0–1 s) before re-poll after errors, plus exponential backoff (1→2→4…≤30 s) on transport errors. This avoids thundering herds after a server restart.
- **Implementation sketch (single process, stdlib):**
  ```
  state.lock = threading.Lock()
  state.machines[machine_id] = {cond: Condition(lock), open_poll: token|None, last_poll_end: mono, pending: Pending|None}
  Pending = {request_id, user_id, instruction, data_hash, deadline_mono, delivered: bool, terminal: None|Result, waiters: Condition}

  POLL(machine):                       # after envelope verify
    with lock: m.open_poll = new_token  # newest poll wins: the older waiting poll returns command=null
      notify_all(m.cond)
      end = mono()+20
      while m.open_poll is my_token and not (m.pending and not m.pending.delivered and not expired):
          if not m.cond.wait(end-mono()): break
      cmd = take pending (mark delivered) if present and my_token current
      m.last_poll_end = mono(); if m.open_poll is my_token: m.open_poll=None
    return close_response(opened, {command: cmd with remaining_ms = deadline-mono()})

  SEND(app):
    with lock: check owner/online(open_poll or mono()-last_poll_end<=30)
      existing same (machine,request_id): same user+hash → wait on it; else REQUEST_CONFLICT
      other pending → BUSY; else create Pending(deadline=mono()+15); m.cond.notify_all()
      wait on pending.waiters until terminal or deadline → MACHINE_TIMEOUT
      store terminal in 60 s cache keyed (machine,request_id)
  RESULT(machine): verify identity==pending machine, not terminal, not expired → set terminal, notify waiters
  ```
  - Use a single `Condition` per machine bound to the global lock. Never hold the lock during HPKE or signature work (the contract already requires this).
  - A sweeper thread, or a check on each access, expires pendings at the deadline.
- **"Newest poll wins"** is important behind NAT. When a NAT silently drops a connection, the server-side socket can stay open until the write fails, while the Pi has already opened a new poll. Under a strict "max 1 open poll, reject the second" rule, the new poll would be refused for up to 20 s. Instead, close the older one with `command=null`. A command delivered into a dead socket is lost, which leads to the next point.
- **Delivery semantics:** the server marks a command "delivered" when it writes the poll response, but the Pi may never receive it. That gives at-most-once delivery, and the app sees MACHINE_TIMEOUT after 15 s. This is acceptable for `machine.status.read`, which is idempotent and harmless. For any future actuating command (dispensing a drink, payment):
  1. The machine persists executed `request_id`s and returns the stored result on duplicate delivery.
  2. The server re-offers an undelivered or unacknowledged command on the next poll within the deadline (at-least-once + machine dedup = effectively once).
  3. Never auto-retry a command with a new request_id.
  Write this into relay-status.md before adding instructions other than `machine.status.read`.
- **Correlation and idempotency:** this matches common practice and Azure direct-method semantics.
  - `request_id` is a UUIDv4 per user action and is the idempotency key.
  - `send_id` is per HTTP attempt.
  - The terminal cache (60 s) answers same-id retries with the identical response and `received_at`.
  - `retry:true` + missing record → `REQUEST_GONE` prevents duplicate execution after a restart.
  - Compare `data` via a hash of its canonical serialization when detecting REQUEST_CONFLICT. The contract says object JSON is not canonical, so compare the parsed Python objects or `json.dumps(sort_keys=True, separators=(",",":"))` internally.
- **ThreadingHTTPServer capacity (key risk):**
  - With **one shared semaphore of 64**, each online machine holds a slot almost 100% of the time (20 s polls back to back), and each waiting app request holds one for up to 15 s. Around 50 machines therefore starve logins and bootstraps.
  - Recommendation: separate budgets, e.g. `POLL_SLOTS = max_machines` (configured), `RELAY_WAIT_SLOTS = 32`, and `SHORT_SLOTS = 32`. Acquire **non-blocking** and return `RATE_LIMITED`/503 immediately when a budget is exhausted, rather than queuing threads.
  - Threads are still created per accepted connection (ThreadingMixIn), so the socket read timeout (already present) plus the 64 KiB body cap are the slowloris defenses. Consider `threading.stack_size(512*1024)` to cut per-thread memory on small VMs.
  - `daemon_threads=True` means shutdown kills in-flight long-polls abruptly. That is fine because clients re-poll and the boot floor handles replay.
  - Realistic ceiling for this stdlib design is a few hundred concurrent connections per process (inference, not benchmarked). Beyond that, move to asyncio, an ASGI server or MQTT.
- **Presence UI:** "Kết nối cloud" = open poll or last_poll_end within 30 s, independent of "Máy trả lời". This matches the AWS model in which presence lags reality by up to 1.5× keep-alive. Expect up to ~30 s of a false "online" after power loss; MACHINE_TIMEOUT covers it.

### Gaps
- RFC 6202 §5.5 timeout recommendations and typical carrier-grade NAT idle timeouts could not be quoted (fetch blocked). The 20 s poll is assumed safe because it is well below typical NAT UDP/TCP idle timers (inference).
- No benchmark of `ThreadingHTTPServer` on the target VM was found. Capacity numbers above are reasoning, not measurements.
- No primary source on mosquitto resource use on the server side was gathered, since MQTT is not recommended for the MVP.

---

## Concrete recommendation per sub-block (summary)

| Sub-block | Choice | Change vs current contract? |
|---|---|---|
| Transport | TLS ≥1.2 (prefer 1.3), public CA, hostname check, no redirects | none |
| Inner request | HPKE RFC 9180 base, X25519/HKDF-SHA256/AES-128-GCM, header in AAD, info `flexmix-cloud-v1` | none |
| Python HPKE lib | PyHPKE 0.6.5 (pinned); **not** pyca `hpke` (no AAD/exporter in 50.x) | none; document why |
| Android HPKE | BC `crypto.hpke` lightweight API via MethodChannel; R8 keep rules | none |
| Response | exporter(`flexmix-response-v1`,16) → AES-128-GCM, random 12-byte nonce, AAD binds send_id/status/route | none (OHTTP-equivalent) |
| Machine signature | **Ed25519 recommended** (Pi+server only; canonical; deterministic) unless P-256 secure element is planned; if P-256 kept, the verifier must explicitly reject s > n/2 because pyca accepts high-s | optional change |
| Replay | (kid,send_id) cache with expiry = sent_at+300 s, after auth; **add boot floor `sent_at_ms ≥ boot_wall_ms`**; server NTP; monotonic TTLs; per-IP cap on anonymous inserts | add boot floor |
| Clock bootstrap | as contracted; Android uses `SystemClock.elapsedRealtime()` | clarify Android clock source |
| Relay transport | HTTP long-poll (stdlib), Condition-based wakeups, newest-poll-wins | add newest-poll-wins |
| Presence | open poll or last_poll_end ≤ 30 s (=1.5×poll) | define last_poll_end precisely |
| Capacity | split semaphores (poll / relay-wait / short), non-blocking acquire | change from single 64 |
| Delivery semantics | at-most-once OK for status.read; at-least-once + machine dedup by request_id before any actuating command | note for future |
