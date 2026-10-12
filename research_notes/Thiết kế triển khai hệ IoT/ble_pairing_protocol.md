# BLE claim/provisioning pairing protocol (QR secret S, Android Kotlin ↔ Raspberry Pi Python)

Scope: choose the session protocol for the local BLE claim profile B-03 (`contracts/messages/bt-claim.md`). It must be authenticated by S, a 32-byte CSPRNG secret printed in a QR code on the machine. Also decide whether the R2/Q2 confirm round is needed, give a minimal flow, a security analysis and a test-vector plan.

Research environment note (12/10/2026): the egress proxy blocked rfc-editor.org, datatracker, noiseprotocol.org, docs.espressif.com, developers.google.com and support.apple.com. Primary texts were therefore read from their canonical GitHub sources: the Noise spec repo, the CFRG HPKE draft repo (the source of RFC 9180), the ESP-IDF docs sources, and the Tink and Bouncy Castle source trees. URLs below point to those raw files. The section numbers are those of the published documents.

---

## Q1. Since S is high-entropy (256-bit), is a PAKE needed? Comparison of candidate protocols

### Takeaway
No. A PAKE (SPAKE2+, CPace, OPAQUE, SRP) exists to stop offline dictionary attacks on a low-entropy secret. With a 256-bit uniformly random S there is no dictionary to search, so a symmetric-PSK authenticated key exchange gives the same guarantees with fewer moving parts. The real choice is between HPKE mode_psk (custom session), Noise NNpsk0, and a hand-built ECDH+HKDF+AEAD scheme. Considering the Android library situation as well, the best option is **HPKE mode_psk with a reduced flow** (see Q5). Noise NNpsk0 is the cleaner design on paper, but it has no Android-ready Java library that interoperates with Python. TLS 1.3 external PSK is too heavy for BLE and poorly supported on both platforms.

### Cited Findings
- RFC 9180 §5.1.2 / §9.5: in PSK mode "The PSK MUST have at least 32 bytes of entropy and SHOULD be of length `Nh` bytes or longer." S = 32 random bytes = Nh for HKDF-SHA256, so it meets the requirement exactly — [HPKE draft source (RFC 9180)](https://raw.githubusercontent.com/cfrg/draft-irtf-cfrg-hpke/master/draft-irtf-cfrg-hpke.md)
- RFC 9180 §9.5: "HPKE's PSK mechanism is not suitable for use with a low-entropy password as the PSK". An attacker acting as sender knows `shared_secret` and can use any wrong-PSK oracle to run a dictionary attack. Because the AEADs are not key-committing, a partitioning-oracle attack recovers a PSK from |S| = m·k candidates in about m + log k queries. These are low-entropy attacks only, and do not apply to a 2^256 space — [HPKE draft source](https://raw.githubusercontent.com/cfrg/draft-irtf-cfrg-hpke/master/draft-irtf-cfrg-hpke.md)
- Matter PASE uses SPAKE2+ because its secret is an 8-digit setup passcode. A verifier can be precomputed so the device never holds the raw passcode — [Nordic Matter security](https://nrfconnectdocs.nordicsemi.com/addons/ncs-matter/latest/matter/overview/security.html); [Silicon Labs Matter commissioning](https://docs.silabs.com/d/matter-overview-guides/2.5/matter-commissioning)
- HomeKit Pair Setup uses SRP-3072 with an eight-digit setup code, ChaCha20-Poly1305 and HKDF-SHA-512 keys. A low-entropy code again forces a PAKE — [Apple Platform Security (search snippet)](https://support.apple.com/guide/security/sec3a881ccb1/web); [homecore-hap README](https://docs.rs/crate/homecore-hap/latest/source/README.md)
- ESP-IDF names `protocomm_security2` (SRP6a + AES-GCM) "the recommended security version for all production use cases". `security1` (X25519 + PoP + AES-CTR) remains available. The PoP is a per-device secret that the user enters or scans — [ESP-IDF protocomm.rst](https://raw.githubusercontent.com/espressif/esp-idf/master/docs/en/api-reference/provisioning/protocomm.rst); [ESP-IDF provisioning.rst](https://raw.githubusercontent.com/espressif/esp-idf/master/docs/en/api-reference/provisioning/provisioning.rst)
- Noise PSK handshakes: the `psk` token calls `MixKeyAndHash(psk)` with a 32-byte PSK. In PSK handshakes every `e` is followed by `MixKey(e.public_key)`, and the validity rule forbids encrypting after `psk` until the sender has sent its own `e`, so PSK-derived keys are always randomised by a fresh ephemeral (§9.2–9.3). NNpsk0 is `-> psk, e` / `<- e, ee` — [Noise spec source](https://raw.githubusercontent.com/noiseprotocol/noise_spec/master/noise.md)
- Noise §7.7 destination property 2: payloads "encrypted based only on DHs involving the recipient's static key pair … can also be replayed, since there's no ephemeral contribution from the recipient". The repo's own Noise study concluded the same for NNpsk0 M1: it is replayable, so the machine must not act on M1 — [Noise spec source](https://raw.githubusercontent.com/noiseprotocol/noise_spec/master/noise.md); `documentation/research/ble-noise-feasibility.md`
- Early Noise design discussion: replaying an initial PSK message makes encryption of the responder's ephemeral unsafe (key reuse). This was the motivation for `MixKey(e)` in PSK mode — [Trevor Perrin, noise list 2015](https://moderncrypto.org/mail-archive/noise/2015/000429.html)

### Comparison table (synthesised from the findings above; ✔ = property holds)

| Option | Round trips before Wi-Fi creds can be sent | Mutual auth by S | FS vs later S leak (passive) | Android lib status | Python lib status | Fit |
|---|---|---|---|---|---|---|
| **HPKE mode_psk, custom session (current)** | 1 RT after hello (probe), or 0.5 RT if creds go in R1 | ✔ (R1 proves app knows S; Q1 proves machine knows S) | ✔ (KEM secret from two ephemerals) | BC 1.86 lightweight `SetupPSKS`/`setupPSKR` present; vectors pass on JVM | PyHPKE 0.6.5 passes official vectors | **Chosen** |
| Noise NNpsk0 | 1 RT (app M2 can carry creds if machine is initiator) | ✔ | ✔ (`ee`) | No Android-compatible lib verified (java-noise needs API 33/34 JCA; noise-java uses legacy NoisePSK) | `noiseprotocol` 0.3.1, last release 2020 | Cleanest design, blocked by libraries |
| Noise NKpsk0 / XXpsk3 | 1 / 1.5 RT | ✔ plus static keys | ✔ | same as above | same | Static machine key adds nothing: S already authenticates, and the machine signing key is P-256 for cloud |
| ESP security1-style X25519 + (DH ⊕ H(S)) + verify tokens | 2 RT | ✔ (explicit token round) | ✔ | Would need custom HKDF/AEAD composition | Same | Rejected: custom crypto composition, which the profile forbids |
| TLS 1.3 external PSK (psk_dhe_ke) over BLE | 1 RT + record layer | ✔ | ✔ | Platform TLS external-PSK support on Android not verified (gap) | Python `ssl` PSK support not verified for TLS 1.3 (gap) | Rejected: heavy framing over 20-byte MTU, uncertain API support |
| PAKE (SPAKE2+, CPace, OPAQUE) | 1–1.5 RT | ✔ | ✔ | No standard BC/Android API checked; CPace is still an Internet-Draft | Few maintained libs | Unnecessary because S is high-entropy |

### Inferences
- With S uniformly random over 2^256, PAKE resistance to offline guessing adds nothing. The only cost of a non-PAKE design is that a passive eavesdropper who records the session can test a guessed S, which is infeasible. Picking a PAKE would add library risk on both platforms for no security gain.
- HPKE mode_psk and Noise NNpsk0 are structurally almost the same thing: an ephemeral-ephemeral DH (HPKE's DHKEM with a fresh app ephemeral against the machine's per-connection ephemeral `pkR`) with S mixed into HKDF. HPKE has no built-in handshake hash or transport phase, so the profile has to supply transcript binding (`h0`, AAD) and the response direction (exporter) itself. That custom part is what the independent review must cover.
- Matter, HomeKit and ESP sec2 use PAKEs because a human types or reads short codes. DPP uses a public bootstrapping key in the QR. Our QR holds a 256-bit symmetric secret, which is closest to ESP security1 with a strong PoP, but with a standard key schedule in place of XOR-with-SHA256(PoP) and AES-CTR.

### Gaps
- Not verified: whether Conscrypt (Android) or Python's `ssl` exposes TLS 1.3 external-PSK (psk_dhe_ke) APIs suitable for a non-socket BLE transport. TLS was rejected on transport/complexity grounds regardless.
- No maintained CPace/SPAKE2+ Java/Android plus Python pair was evaluated, because a PAKE is not needed.

---

## Q2. Analysis of the existing profile: is R2/Q2 needed? Which attacks are mitigated?

### Takeaway
The reviewer is right: **R2/Q2 is redundant.** After hello→R1→Q1 the two sides already have mutual, fresh authentication by S, bound to this connection's transcript (`h0` contains the machine's fresh `pkR` and `Nm`; R1 contains the app's fresh `enc` and `Nc`; Q1's AAD contains `SHA256(F(R1))`). The machine's need to know that the app accepted Q1 is met just as well by having the **first effectful request (Wi-Fi) carry `session_transcript = h1`**. Removing R2/Q2 removes one HPKE context, one response, one state, two timeouts and one transcript hash, with no loss in any listed property. The profile's other bindings (role labels, `send_id`, stage, request-hash in response AAD) already cover reflection, cross-session splicing and reordering. Relay remains out of scope.

### Cited Findings
- RFC 9180 §9.1 lists "Sender authentication: Proof of sender origin for PSK, Auth, and AuthPSK modes" as a goal. In PSK mode, secrecy holds "if the recipient private key `skR` and the pre-shared key are not both compromised" — [HPKE draft source](https://raw.githubusercontent.com/cfrg/draft-irtf-cfrg-hpke/master/draft-irtf-cfrg-hpke.md)
- RFC 9180 §9.1 non-goals: "no tolerance of message reordering or loss, no downgrade or replay prevention … and no protection against bad ephemeral randomness". §9.7.x: in-order `Open()` gives "a degree of replay protection within a stream … HPKE provides no other replay protection". So replay and freshness must come from the application, which the profile does via the per-connection `pkR`/`Nm`/`h0`/`send_id` — [HPKE draft source](https://raw.githubusercontent.com/cfrg/draft-irtf-cfrg-hpke/master/draft-irtf-cfrg-hpke.md)
- RFC 9180 §9.8 (Bidirectional): responses can use keys from `context.Export(...)`. "HPKE's limitations with regard to sender authentication become limits on recipient authentication in this context." In PSK mode the response therefore authenticates the machine as an S-holder that also derived the same context (it held `skR`) — [HPKE draft source](https://raw.githubusercontent.com/cfrg/draft-irtf-cfrg-hpke/master/draft-irtf-cfrg-hpke.md)
- RFC 9180 §9.7.x Forward Secrecy: HPKE is forward secret with respect to sender compromise in all modes. Here the recipient key `skR` is also per-connection ephemeral and destroyed, so the KEM secret depends only on ephemerals — [HPKE draft source](https://raw.githubusercontent.com/cfrg/draft-irtf-cfrg-hpke/master/draft-irtf-cfrg-hpke.md)
- RFC 9180 §9.1.1 KCI: DHKEM modes are vulnerable to key-compromise impersonation. In PSK-only mode this is moot because S is symmetric: anyone holding S can impersonate either side, by design — [HPKE draft source](https://raw.githubusercontent.com/cfrg/draft-irtf-cfrg-hpke/master/draft-irtf-cfrg-hpke.md)
- RFC 9180 §9.7.x Bad Ephemeral Randomness: weak RNG can cause KEM secret reuse and AEAD key/nonce reuse; mitigation per RFC 8937 — [HPKE draft source](https://raw.githubusercontent.com/cfrg/draft-irtf-cfrg-hpke/master/draft-irtf-cfrg-hpke.md)
- Comparable designs with explicit confirmation: ESP security1/security2 run SessionCmd0/Resp0, then SessionCmd1/Resp1 with verify tokens (sec1: AES-CTR of the peer's pubkey; sec2: SRP M1/M2), and only then send data. Sec2 derives a GCM IV of session_id (8 B) + counter (4 B) — [ESP-IDF provisioning.rst](https://raw.githubusercontent.com/espressif/esp-idf/master/docs/en/api-reference/provisioning/provisioning.rst). Those flows need a separate confirm round because their key-exchange messages carry no authenticated payload. HPKE R1/Q1 do carry authenticated payloads, so R1/Q1 already *are* the confirmation round.
- DPP authentication carries R-auth (hash over nonces and public keys, sent by the responder) and I-auth (same with nonce order swapped, sent by the initiator). Mismatch aborts before credentials are sent — [US patent 10169587 describing DPP 1.0 §6.2.3](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10169587); hostap test hooks mutate "I-nonce, R-capab, R-auth, and I-auth values in Authentication Response/Confirm" — [hostap commit](https://gitea.auro.re/jeltz/hostap/commits/commit/d8b841eba8c85d6542d2c77fafa1eda4659ec66b/src?page=4). (Secondary sources; the DPP spec itself was not retrieved.)

### Step-by-step argument that R2/Q2 adds nothing (inference from the cited properties)
1. **After machine opens R1:** the AEAD tag verifies only if the sender's key schedule used S (psk) and the same `info`, which contains `h0`, which contains this connection's fresh `pkR` and `Nm`. So someone who knows S produced R1 *for this hello*. R1 cannot come from another session (different `pkR` means a different KEM secret, and `info` differs too). This is fresh entity authentication of "an S-holder" to the machine.
2. **After app opens Q1:** the GCM key is `Export("flexmix-bt-response-v1")` of R1's context. Deriving it needs (`skE` app ephemeral or `skR`) **and** S. A fake hello lets an attacker who substituted `pkR` compute the KEM secret, but not S, so Q1 cannot be forged. The AAD includes `SHA256(F(R1))`, so Q1 answers exactly this R1, and the payload echoes `Nc`. This is fresh authentication of "an S-holder holding `skR`" to the app, plus implicit key confirmation of R1.
3. **What R2/Q2 adds:** the machine learns that the app accepted Q1 (h1 agreed), and the app gets another confirmation. The first property also follows from R3 (wifi) carrying `h1`: an S-holder created R3 for this session after seeing Q1. The second property is already given by Q1.
4. **Attacks R2 was meant to stop, re-checked without it:**
   - *Probe replay, same connection:* blocked by stage/`send_id` state. Wi-Fi needs a new HPKE context, which needs S.
   - *Probe replay, other connection:* fails to open (different `pkR`/`h0`).
   - *Attacker drops Q1, then injects wifi:* needs S. Without S it cannot produce any accepted request.
   - *Attacker reorders or duplicates the wifi/claim request:* stage machine plus `send_id` cache plus transcript hash in the payload.
5. Conclusion: delete R2/Q2. Bind Wi-Fi to `h1` (H‖R1‖Q1) and claim to `h2` (H‖R1‖Q1‖R2wifi‖Q2wifi_result).

### Attack-by-attack status of the (reduced) profile
| Threat (gate item 1) | Status | Mechanism |
|---|---|---|
| Fake hello (attacker device / substituted `pkR`, `machine_public_key`) | Mitigated | Attacker lacks S, so Q1 fails. App checks `machine_public_key` in Q1 equals hello's, so a swapped signing key is detected because Q1 is S-authenticated. |
| Replay of R1/Q1 (or R2/Q2) across connections | Mitigated | Fresh `pkR`, `Nm`, `session_id` in `h0`/`info`; fresh `enc` and `Nc` per request; response AAD hashes the request. |
| Replay/reorder within a connection | Mitigated | Stage machine, `send_id` cache, one-shot context, transcript hash in payload. |
| Reflection / role swap | Mitigated | Asymmetric mechanisms: only the app does HPKE seal and only the machine does exporter-GCM. Role strings `"app","machine"` in `info`/AAD; distinct labels `flexmix-bt-claim-v1` vs `flexmix-bt-response-v1`; `type` field. A response cannot be parsed as a request (no `enc`). |
| Splicing two sessions / two apps (UKS-like) | Mitigated for non-S-holders | `session_id` + `h0` bind everything, and one connection is allowed at a time. An attacker *with* S can always claim, which is accepted risk in the profile. |
| Tampered transcript | Mitigated | `h0` in `info`; `F(R)` hash in response AAD; `h1`/`h2` echoed and compared against bytes each side holds. |
| Fake serial / key | Mitigated | `psk_id` and `info`/AAD include `serial`; app rejects a hello whose serial differs from the QR; serial plaintext is not trusted. |
| Valid PSK but wrong stage | Mitigated | Stage in AAD and state machine; terminal close. |
| Relay / distance (attacker forwards BLE to a far-away app) | **Not mitigated** (explicitly out of scope) | Same as Matter PASE / ESP / DPP: only distance bounding would help. |
| Later leak of S + recorded traffic (passive) | Mitigated (Wi-Fi password stays secret) | KEM secret from two ephemerals, both erased. |
| S leaked *before* pairing (active MITM) | Not mitigated | Symmetric-PSK limit; inherent to "QR = authority". |
| Weak Pi RNG | Must mitigate operationally | Use `os.urandom`/`secrets`; HPKE §9.7 bad-randomness note. |
| PSK oracle / partitioning-oracle | Not relevant | S is 256-bit (§9.5 attacks need small candidate sets). The silent-close policy is still fine. |

### Inferences
- The redundancy argument relies on the payload of each later request echoing the transcript hash, and on the machine comparing it against its own stored bytes (already in the profile for `h2`). Moving that check from R2 to R3 keeps the "confirm before effect" invariant: no side effect happens until the machine has seen an S-authenticated request that commits to Q1.
- One optional micro-optimisation: Wi-Fi credentials could be sent in R1 itself (0.5 RT), since confidentiality holds even against a fake hello, which cannot decrypt without S. It is **not** recommended. Keeping probe/Q1 first lets the app (a) catch a wrong machine or QR before asking the user for the Wi-Fi password, and (b) receive `machine_public_key` authenticated before any claim. Wi-Fi is the only sensitive payload, and one RT costs about 100 ms over BLE.

### Gaps
- No machine-checked proof (Tamarin/ProVerif/CryptoVerif) of this specific HPKE composition was found. Formal results exist for HPKE itself (cited in RFC 9180 as ABHKLR20) and for Noise patterns (Noise Explorer), but not for this custom session. The independent review must still be a human review. A small Tamarin/ProVerif model of hello→R1→Q1→R2(wifi,h1) is a reasonable gate addition (inference).
- noiseexplorer.com (formal NNpsk0 grades) could not be fetched (DNS blocked), so its per-message grades are not quoted.

---

## Q3. Library maturity and Android compatibility

### Takeaway
Bouncy Castle's lightweight `org.bouncycastle.crypto.hpke.HPKE` is the only checked Android-viable JVM HPKE that supports **mode_psk**. **Tink Java's HPKE implements only Base and Auth modes**, so Tink cannot replace BC for this profile. PyHPKE 0.6.5 (released 16/07/2026) is current and matches the official vectors. Python Noise (`noiseprotocol` 0.3.1) has not been released since 2020 and has no verified Android counterpart. These facts support keeping HPKE + BC + PyHPKE.

### Cited Findings
- BC `HPKE.java` defines `mode_base=0x00, mode_psk=0x01, mode_auth=0x02, mode_auth_psk=0x03`. Public methods include `SetupPSKS(pkR, info, psk, psk_id)` (capitalised as noted in the profile), `setupPSKR(enc, skR, info, psk, psk_id)`, one-shot `seal/open/sendExport/receiveExport`, and `deriveKeyPair(ikm)`. `setupBaseS` has overloads taking a fixed `kpE` or `ier` for deterministic tests, **but `SetupPSKS` has no such overload**, so BC cannot reproduce a deterministic PSK-mode *sender* vector through the public API — [BC HPKE.java source](https://raw.githubusercontent.com/bcgit/bc-java/main/core/src/main/java/org/bouncycastle/crypto/hpke/HPKE.java) (lines 332–404 at time of fetch)
- Tink Java `HpkeContext` builds contexts only with `HpkeUtil.BASE_MODE` and `HpkeUtil.AUTH_MODE` (`createSenderContext`, `createAuthSenderContext`, `createRecipientContext`, `createAuthRecipientContext`). `HpkeUtil` defines only `BASE_MODE=0x0` and `AUTH_MODE=0x2`, and the key schedule is called with an empty PSK — [Tink HpkeContext.java](https://raw.githubusercontent.com/tink-crypto/tink-java/main/src/main/java/com/google/crypto/tink/hybrid/internal/HpkeContext.java); [Tink HpkeUtil.java](https://raw.githubusercontent.com/tink-crypto/tink-java/main/src/main/java/com/google/crypto/tink/hybrid/internal/HpkeUtil.java)
- PyHPKE: latest 0.6.5 uploaded 2026-07-16; earlier 0.6.x releases date from 2024-11 to 2025-12 (active maintenance) — [PyPI pyhpke JSON](https://pypi.org/pypi/pyhpke/json)
- `noiseprotocol` (Python): latest 0.3.1, uploaded 2020-03-03, no releases since — [PyPI noiseprotocol JSON](https://pypi.org/pypi/noiseprotocol/json)
- Repo evidence: `jchambers/java-noise` interoperates with `noiseprotocol` for NNpsk0 on the JVM, but needs `HexFormat` (API 34), `XECKey`/`NamedParameterSpec` (API 33) and a JCA `X25519` factory. Android Conscrypt registers `XDH`, and its public key does not implement `XECKey`. `rweather/noise-java` uses the legacy NoisePSK prefix — `documentation/research/ble-noise-feasibility.md` (citing [AOSP Conscrypt OpenSSLProvider](https://android.googlesource.com/platform/external/conscrypt/+/refs/heads/android14-release/common/src/main/java/org/conscrypt/OpenSSLProvider.java))
- Repo evidence (reviewer, 12/10/2026): PyHPKE 0.6.5 mode1/KEM32/KDF1/AEAD1 matched enc, 257 ciphertexts and 3 exports from the official vectors. BC 1.86 recipient matched 3 ciphertexts and 3 exports. BC-sender→PyHPKE-recipient and Android runtime are not yet tested — `contracts/messages/bt-claim.md`
- Official HPKE vectors live in the CFRG repo (`test-vectors.json`) and RFC 9180 Appendix A; A.1.2 is the PSK setup for DHKEM(X25519,HKDF-SHA256)/HKDF-SHA256/AES-128-GCM — [HPKE draft source](https://raw.githubusercontent.com/cfrg/draft-irtf-cfrg-hpke/master/draft-irtf-cfrg-hpke.md)

### Inferences
- Because BC's lightweight API does its own X25519 (no JCA provider lookup), it avoids the Conscrypt `XDH`/`XECKey` problem that blocked java-noise. Android runtime evidence is still a required gate (minSdk/targetSdk, R8/ProGuard rules for BC classes, APK size).
- To keep sender-side coverage despite BC's missing deterministic `SetupPSKS`: (a) test BC as a *recipient* against the RFC A.1.2 vector (done); (b) test BC sender → PyHPKE recipient with random ephemerals and compare exporter outputs on both sides; (c) produce deterministic *profile* golden transcripts from the Python side only. The profile already says not to fork crypto.
- Tink is unusable for mode_psk. Switching to Tink would mean Base/Auth mode plus a separate S binding, which is a different, custom design. Not recommended.

### Gaps
- Conscrypt's HPKE API (Android 14+, `android.crypto.hpke`/Conscrypt `HpkeContext`) was not verified for mode_psk support, and it would restrict minSdk anyway.
- Tink Python HPKE source was not inspected separately (assumed to mirror Java's Base/Auth-only scope; unverified).
- BC 1.86 release notes and changes to its HPKE class were not checked beyond the main-branch source.

---

## Q4. How do ESP-IDF, Matter, Wi-Fi DPP and HomeKit handle BLE provisioning sessions? Lessons

### Takeaway
All four establish a session key with explicit mutual proof before delivering network credentials, then put all provisioning data under that session. None defends against relay. Their extra "confirm" messages are needed because their key-exchange messages carry no authenticated application payload. HPKE R1/Q1 do carry one, so the same goal is reached in one round trip.

### Cited Findings
- **ESP-IDF unified provisioning** (BLE or SoftAP, protobuf over protocomm). Security1: client sends `SessionCmd0(cli_pubkey)`; device replies `SessionResp0(dev_pubkey, dev_rand)` with `shared_key = X25519 ^ SHA256(pop)`; client sends `SessionCmd1(cli_verify = AES-CTR(shared_key, dev_pubkey, nonce=dev_rand))`; device verifies and returns `dev_verify`; client verifies. Security2: SRP6a (RFC 5054) with salt/verifier stored on the device, client proof M1 and device proof M2 (`H(A,M,K)`), AES-256-GCM with an IV of session_id (8 B) + counter (4 B). Sec0 "should not be used in production"; sec2 is "recommended … for all production use cases". For BLE, "just-works" pairing may serve as transport security "after assessing its provided level of security" — [ESP-IDF provisioning.rst](https://raw.githubusercontent.com/espressif/esp-idf/master/docs/en/api-reference/provisioning/provisioning.rst); [protocomm.rst](https://raw.githubusercontent.com/espressif/esp-idf/master/docs/en/api-reference/provisioning/protocomm.rst)
- **Matter**: PASE (SPAKE2+, setup passcode from QR/manual code) is used only for commissioning, with only one PASE session at a time. The commissioner then verifies device attestation, installs operational certificates, and moves to CASE (SIGMA with certificates, ephemeral P-256 ECDH) — [Nordic Matter security](https://nrfconnectdocs.nordicsemi.com/addons/ncs-matter/latest/matter/overview/security.html); [matter-crypto crate](https://docs.rs/crate/matter-crypto/0.3.1)
- **Wi-Fi Easy Connect (DPP)**: the QR carries the enrollee's *public* bootstrapping key (optionally from a 32-byte private key). The configurator scans it and starts authentication. Auth Response/Confirm carry R-auth/I-auth hashes over nonces and keys, mismatch aborts before configuration, and only then is the config object (credentials) delivered — [ESP-IDF esp_dpp docs](https://docs.espressif.com/projects/esp-idf/en/v5.5/esp32/api-reference/network/esp_dpp.html); [hostap README-DPP](https://gitea.auro.re/jeltz/hostap/raw/commit/0030590fb3337cd0667775c63c8eef2d39012db3/wpa_supplicant/README-DPP); [US 10169587](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10169587)
- **HomeKit (HAP)**: Pair-Setup M1–M6 uses SRP-3072 with the setup code, then HKDF-SHA-512 (labels like `Pair-Setup-Encrypt-Salt/Info`) and ChaCha20-Poly1305, and exchanges Ed25519 long-term keys. Each session then runs Pair-Verify M1–M4: ephemeral X25519, Ed25519-signed transcript, HKDF (`Pair-Verify-Encrypt-Salt/Info`) — [HAP-python hap_handler.py](https://raw.githubusercontent.com/ikalchev/HAP-python/dev/pyhap/hap_handler.py); [homecore-hap README](https://docs.rs/crate/homecore-hap/latest/source/README.md)

### Lessons applied to Flexmix (inferences)
1. **Separate one-time claim authority from long-term identity**: Matter PASE→CASE, HAP Setup→Verify. Flexmix already does this: S only authorises local claim, and ownership is decided by the server via the machine signing key. Keep BLE claim sessions one-shot and never resume them, as the profile says.
2. **Distinct labels per direction and purpose** (HAP's salt/info pairs, DPP's I-auth vs R-auth nonce order) match the profile's `flexmix-bt-claim-v1` / `flexmix-bt-response-v1` and the role strings. Keep them.
3. **Explicit confirmation before credentials** is universal, but in our design it is provided by Q1, an AEAD-protected response bound to R1. A third message is only needed when the KE messages are unauthenticated (ESP, DPP).
4. **Relay is accepted by everyone.** None of these protocols claims distance bounding. The profile's non-claim is consistent with industry practice.
5. **High-entropy QR secret means no PAKE**: DPP (QR key) does not use a PAKE; Matter and HAP do only because of short numeric codes.
6. ESP's sec1 `X25519 ^ SHA256(pop)` is an example of ad-hoc composition. Replacing it with HPKE's standard labelled key schedule is better practice.

### Gaps
- The DPP 1.x/2.x and Matter core specifications were not retrieved directly (Wi-Fi Alliance/CSA access and proxy limits). DPP details come from patents and hostap.
- Apple's HAP specification was not retrieved. HAP details come from open-source implementations.

---

## Q5. Recommendation: protocol, minimal message flow, KDF labels, failure handling, test-vector plan

### Takeaway
**Keep HPKE RFC 9180 mode_psk** (suite KEM 0x0020 X25519/HKDF-SHA256, KDF 0x0001, AEAD 0x0001 AES-128-GCM; PSK = S; psk_id = `"flexmix-seal-v1:" || serial`) with the profile's fresh-context-per-request and exporter-GCM response. **Drop the probe-confirm round R2/Q2**, giving three request/response pairs: probe → wifi(h1) → claim(h2). This is a minimal change to a profile whose primitives have already been reviewed, it needs no new crypto library, and every gate-1 threat stays covered (Q2 table). Bump the protocol label to `v2` so a mixed old/new deployment fails closed.

### Cited Findings (basis)
- Exporter for the response direction is the RFC-sanctioned pattern — [RFC 9180 §9.8](https://raw.githubusercontent.com/cfrg/draft-irtf-cfrg-hpke/master/draft-irtf-cfrg-hpke.md)
- The application must supply replay protection — [RFC 9180 §9.7](https://raw.githubusercontent.com/cfrg/draft-irtf-cfrg-hpke/master/draft-irtf-cfrg-hpke.md)
- PSK ≥ 32 bytes of entropy — [RFC 9180 §9.5](https://raw.githubusercontent.com/cfrg/draft-irtf-cfrg-hpke/master/draft-irtf-cfrg-hpke.md)
- BC/PyHPKE API availability — [BC HPKE.java](https://raw.githubusercontent.com/bcgit/bc-java/main/core/src/main/java/org/bouncycastle/crypto/hpke/HPKE.java); [PyPI pyhpke](https://pypi.org/pypi/pyhpke/json)

### Recommended flow (design; inference built on cited primitives)

Notation: `F(P)=u32be(len P)||P`, `J()` = compact JSON array, `H()` = SHA-256, `b64u` as in the profile, `‖` = concatenation. GATT framing, MTU fragmentation, timeouts and the generation handle stay unchanged.

```
App (Kotlin/BC)                                   Machine (Python/PyHPKE)
                                                  per connection: (skR,pkR)=X25519 fresh,
                                                  session_id=UUIDv4, Nm=rand32
           <---- M0 HELLO (cleartext) -------------
  H = {pv:2,type:"hello",serial,session_id,machine_nonce:b64u(Nm),
       public_key:b64u(pkR32),machine_public_key:b64u(P256raw65)}
  check serial == QR serial; h0 = H(F(H))
  Nc = rand32
  ---- R1 stage "probe" ------------------------------>
  ctx1 = SetupPSKS(pkR, info, S, psk_id)              ctx1 = SetupPSKR(enc1, skR, info, S, psk_id)
  ct = ctx1.seal(aadR(send_id1,"probe"), body1)       open; on ANY failure: silent close
  body1 = {type:"probe",serial,session_id,machine_nonce,client_nonce}
                                                      store Nc; state=AUTHENTICATED
           <---- Q1 stage "probe" --------------------
                                                      k1 = ctx1.Export("flexmix-bt-response-v2",16)
                                                      ct = AESGCM(k1).enc(nonce12, body, aadQ(R1))
  body = common + {type:"authenticated",machine_public_key}
  check serial/session/Nm/Nc/machine_public_key == H
  h1 = H(F(H)‖F(R1)‖F(Q1))
  ---- R2 stage "wifi" (fresh ctx2, fresh enc) ------->
  body = common + {type:"wifi",session_transcript:h1,ssid,password}
                                                      check h1 vs own bytes, stage, send_id
                                                      → join Wi-Fi + activation
           <---- Q2 "wifi_result" or encrypted error --
  h2 = H(F(H)‖F(R1)‖F(Q1)‖F(R2)‖F(Q2))
  ---- R3 stage "claim" (fresh ctx3) ----------------->
  body = common + {type:"claim",session_transcript:h2,challenge,server_challenge_signature}
           <---- Q3 "claim_proof" ---------------------  then terminal close
```

Envelope (unchanged apart from the version and stage enum):
- Request `R = {pv:2,type:"request",session_id,send_id,stage,enc:b64u(32),ct:b64u(≥16)}`, stage ∈ `probe|wifi|claim`.
- Response `Q = {pv:2,type:"response",session_id,send_id,stage,nonce:b64u(12),ct}`.

KDF / label table:

| Item | Value |
|---|---|
| HPKE mode / suite | mode_psk (0x01); KEM 0x0020; KDF 0x0001; AEAD 0x0001 |
| psk / psk_id | S (32 B raw) / ASCII `flexmix-seal-v1:` + serial |
| HPKE `info` | `J(["flexmix-bt-claim-v2","app","machine",serial,session_id,h0])` |
| Request AAD | `J([2,"flexmix-bt-claim-v2","app","machine",serial,session_id,h0,send_id,stage])` |
| Response key | `ctx.Export("flexmix-bt-response-v2", 16)`, one per request context, used once |
| Response nonce | 12 B CSPRNG (single use of a single-use key; a fixed zero nonce would also be safe, but random keeps the profile unchanged) |
| Response AAD | `J([2,"flexmix-bt-response-v2","machine","app",serial,session_id,h0,send_id,stage,b64u(H(F(R)))])` |
| Transcript | `h0=H(F(H))`, `h1=H(F(H)‖F(R1)‖F(Q1))`, `h2=H(…‖F(R2)‖F(Q2))` |

Failure handling (unchanged in spirit):
- Before R1 opens: any failure (tag, enc, info, AAD, JSON, state) means silent close. The app reports `PAIRING_FAILED`. No distinguishable PSK error.
- After R1 opens: send an encrypted `{type:"error",code}` response under that request's exporter key, then terminal close. No retry within a session, since every retry is a new connection and full handshake.
- Machine accepts only the expected stage, with an unused `send_id`, and the echoed transcript hash must equal its own. Check, insert and transition atomically before any side effect, per the existing generation-handle rules.

What this changes in `bt-claim.md` (for the Planner): remove the stage `confirm`, R2/Q2, the `WAIT_CONFIRM`/`CONFIRMED` states and their 30 s timeout. Redefine h2 over the wifi round. Replace "Wi-Fi/claim carry h2" with "wifi carries h1, claim carries h2". Bump labels to `v2`. The `send_id` cache maximum drops from 4 to 3.

Alternative considered but not chosen: a single HPKE context per session (`ctx.seal` for seq 0, 1, 2, with HPKE's in-order nonce giving replay/reorder protection per §9.7) plus one exporter key with counter nonces. It is slightly simpler at runtime, but it changes the already-reviewed "one context = one message" rule and BC/PyHPKE multi-message state handling, so it is not worth the re-review for an MVP.

### Test-vector plan (gate items 2–4)
1. **Primitive KATs (pinned upstream)**: RFC 9180 A.1.2 (mode_psk, X25519, HKDF-SHA256, AES-128-GCM) from the CFRG `test-vectors.json`, stored with its SHA-256 (the reviewer's download was `61fc662f…3ede6`) and source commit under `tests/fixtures/crypto/`. PyHPKE: full sender (with fixed eph key if the API allows) and recipient. BC: recipient side (open plus exports), since `SetupPSKS` has no deterministic overload.
2. **Cross-library interop (test-only code)**: BC 1.86 `SetupPSKS` → PyHPKE `create_recipient_context` open and export, comparing the 16-byte exporter on both sides. Python AESGCM response → BC `GCMBlockCipher` open. Reverse direction (PyHPKE sender → BC recipient). Run on the JVM and as an Android instrumented test on the real minSdk/targetSdk.
3. **Profile golden transcripts**: Python generator with fixed `skR`, `Nm`, `Nc`, `session_id`, `send_id`, S, serial (and fixed sender eph key if PyHPKE allows; otherwise record random `enc` and verify by opening). Emit H, R1, Q1, R2, Q2, R3, Q3 as exact packet bytes, plus h0/h1/h2. Kotlin must reproduce h0/h1/h2 byte-exact and open every R/Q using the recipient/opener role available to it.
4. **Negative matrix** (each must fail *before* Wi-Fi/sign): flip S; psk_id serial; info field (role swap app↔machine, session_id, h0); AAD stage/send_id; response AAD request hash; nonce; ct/tag bit; `h1` in wifi; `h2` in claim; Nc/Nm echo; `machine_public_key` mismatch between H and Q1; v1 label against a v2 peer.
5. **State/replay tests**: replay R1 in the same connection; replay R1/R2 on a new connection; wifi before probe; claim before wifi_result; duplicate `send_id`; Q from another request; disconnect between Q1 and R2 (no side effect); late Wi-Fi callback with a stale generation.
6. **BLE transport on real Android + Pi**: MTU 23 fragmentation, split length prefix, oversize, indication-confirmation loss, timeouts (as the profile already lists).
7. Optional but recommended: a small Tamarin/ProVerif model of M0–R2 with PSK-holder adversary classes. It turns the "independent session review" into a checkable artefact.

### Gaps
- Whether PyHPKE 0.6.5 `create_sender_context` accepts a caller-supplied ephemeral key (for deterministic sender vectors) was not verified in source during this pass.
- The redundancy argument for R2/Q2 is a reasoned analysis on top of RFC 9180's stated properties, not a published proof for this composition. The gate's independent review (and optionally a formal model) should confirm it.
- No source was found that benchmarks HPKE versus Noise latency over BLE; the claim that one RT is about 100 ms is an engineering estimate, not cited.
