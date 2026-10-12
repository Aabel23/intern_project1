# Machine identity, activation (device key ↔ serial) and owner claim for Raspberry Pi machines + MySQL claim transaction

Scope note: research done 2026-10-12. Several primary doc hosts (dev.mysql.com, cryptography.io, raspberrypi.com, docs.rainmaker.espressif.com, cheatsheetseries.owasp.org) were unreachable from the research sandbox (DNS/egress policy), so some facts come from search-result snippets of those pages or from secondary sources; this is flagged per item. The pyca/cryptography EC doc was read from its source file on GitHub. Repo facts were read directly from `contracts/messages/claim.md`, `contracts/messages/cloud-protection.md`, `documentation/plan/tasks/S-02-server-claim.md`, `documentation/plan/tasks/M-01-machine-identity-pairing.md`, `server/src/database.py`, `server/requirements.txt`.

## Q0. Verification of the three review issues against the current contracts

### Takeaway
All three issues hold, and issue (1) is worse than "permanent KEY_CONFLICT": because the server accepts any `machine_proof` signed by the bound key, whoever binds first holds the private key and can also complete the owner claim **without ever touching the machine or the BLE session**. Factory-time activation (key generated on the Pi at the factory station, public key registered by the Operator tool, no field bind API) removes issues (1) and (2) together and shrinks the role of the QR secret to "local proof of physical possession for the BLE session".

### Cited Findings
- Bind needs only `serial, challenge_id, seal_code, public_key, proof`; proof is signed by the *new* key, so it only proves possession of a key the caller generated itself, not that it is the real Pi — `cloud-protection.md` §"Bootstrap serial → public key" (repo).
- Challenge step is unauthenticated and needs only the serial (`step=challenge, v, serial`); serial is the 16-hex CPU serial, which is not secret (printed by `/proc/cpuinfo` and devicetree to any local user) — `cloud-protection.md` (repo); [bret.dk – Finding your Raspberry Pi serial](https://bret.dk/finding-your-raspberry-pi-serial-number/).
- Different key after bind → `KEY_CONFLICT 409`, no overwrite, and "không thêm quy trình recovery" (no recovery process) — `claim.md`, `cloud-protection.md` (repo). So an attacker who binds first locks the real machine out permanently.
- Claim `complete`: server verifies "proof của key bound" and that `local_session_binding` is inside the machine signature; "Server không trực tiếp kiểm BT transcript … dựa vào máy chỉ ký sau gate phiên bt-claim.md" — `cloud-protection.md`, `claim.md` (repo). An attacker holding the bound key can therefore fabricate any UUIDv4 `local_session_binding` and sign it; the BLE gate is enforced only by honest machine firmware.
- Retry with unknown commit: "Same key bind retry chỉ khi cùng challenge đã commit lưu result durable", and the M-01/B-03 gate says "retry timer/budget, pending-challenge durability/restart và expiry/result recovery cho commit chưa biết chưa được Planner khóa" (BLOCKED) — `cloud-protection.md` §"Activation retry" (repo). If the challenge expires (120 s) and the result is unknown, the device cannot request a new challenge ("Không sinh challenge mới khi chưa xác định bind cũ đã commit") → dead end.
- "Không triển khai gỡ máy/chuyển chủ" (no unbind/transfer) — `claim.md` (repo).

### Inferences
- Attack (1) concretely: anyone who sees the QR between factory and buyer (warehouse, shop, courier, a photo in a listing) runs a script: `challenge(serial)` → `bind(serial, S, attacker_pubkey, proof)` → later `begin`/`complete` with own account and self-signed `machine_proof`. Result: attacker owns the machine in the cloud and holds its identity; the real Pi gets KEY_CONFLICT forever. The contract's accepted risk ("người có cả mã và máy") understates it: attacker needs the code only, not the machine.
- Also, the server DB holds `seal_verifier`; with field bind it is the only gate, so a verifier is security-critical. With factory activation the server does not need S or the verifier at all.

### Gaps
- `bt-claim.md` was not read in detail; whether the BLE PSK is derived from the same S matters for Q3 (it is assumed so).

## Q1. How commercial platforms provision identity and claim ownership; lessons for QR setup codes and anti-hijack

### Takeaway
Every mature platform separates two things: (a) **device identity**, established at the factory or by a credential installed at manufacture (X.509/DAC, TPM, derived per-device key, factory claim cert), and (b) **user ownership**, established by proving local/physical possession (setup passcode over a local PAKE channel, challenge-response through the device, short-lived single-use claim codes). None of them let a printed code alone create the device's cloud identity remotely. The QR/setup code is used locally to authenticate the first channel, not as a cloud credential for identity.

### Cited Findings
- **AWS IoT fleet provisioning by claim**: devices ship with a claim certificate shared by many devices; AWS warns it "could present a larger risk in the event of a compromised claim certificate", recommends a restrictive claim policy (only provisioning topics), protecting claim private keys, CloudWatch monitoring and deactivating a misused claim cert (which does not affect already-provisioned devices) — [AWS: Provisioning devices without certificates](https://docs.aws.amazon.com/iot/latest/developerguide/provision-wo-cert.html); [AWS: Device provisioning](https://docs.aws.amazon.com/iot/latest/developerguide/iot-provision.html).
- AWS also offers **provisioning by trusted user** (the credential is obtained by an authenticated installer app, not embedded in the device) — [AWS provision-wo-cert](https://docs.aws.amazon.com/iot/latest/developerguide/provision-wo-cert.html).
- AWS IoT Lens: the device should send a unique token "such as a serial number or embedded hardware secret" checked against an allow list via a pre-provisioning hook; claim cert should be unique per batch and short-lived — [AWS Well-Architected IoT Lens: Device provisioning](https://docs.aws.amazon.com/wellarchitected/latest/iot-lens/device-provisioning.html).
- **Azure DPS symmetric-key group enrollment**: each device key = HMAC-SHA256(group key, registration ID), derived **off-device** at manufacture so the group key is never on the device; symmetric key attestation is the weakest option vs X.509/TPM — [Microsoft Learn: Symmetric key attestation](https://learn.microsoft.com/en-us/azure/iot-dps/concepts-symmetric-key-attestation).
- **Matter**: setup passcode (27-bit, 1..99999998, 12 trivial values forbidden) in QR/manual code is proof of possession for PASE (SPAKE2+); the device stores only a SPAKE2+ verifier (salt + iterations 1000..100000 + passcode), computed on the factory host, not the passcode itself; salt random per device — [Nordic: Factory provisioning in Matter](https://nrfconnectdocs.nordicsemi.com/addons/ncs-matter/latest/matter/end_product/factory_provisioning.html); [Silicon Labs: Matter provisioning](https://docs.silabs.com/matter/2.8.1/matter-provisioning/matter-provisioning). Note salt length differs between doc versions (16–32 vs ≥32 bytes) — same sources.
- Matter commissioning order: discovery → PASE (passcode) → **device attestation** (Device Attestation Certificate chained to a Product Attestation Authority, factory-provisioned) → network config; PASE is temporary and replaced by operational sessions; only one PASE session at a time — [Silicon Labs: Matter security](https://docs.silabs.com/matter/2.2.2/matter-fundamentals-security); [Nordic: Matter commissioning](https://nrfconnectdocs.nordicsemi.com/ncs/latest/nrf/protocols/matter/overview/commissioning.html).
- **ESP RainMaker**: "claiming" (getting the node's cloud certificate) happens first; user-node mapping comes after. Challenge-response mapping (node signs a cloud challenge relayed by the phone during provisioning) is the recommended method and requires the node to be already claimed; it does not work with self-claiming because the cert is registered after Wi-Fi, while mapping happens before; works with Assisted (host/factory) claiming — [RainMaker FAQ: challenge-response user-node mapping](https://docs.rainmaker.espressif.com/docs/dev/firmware/firmware-faq/prov-wi-fi-claiming-fctry-reset/what-is-challenge-response-based-user-node-mapping-why-is-it-recommended) (snippet only; page not fetchable); [esp_rainmaker changelog 1.7.0](https://components.espressif.com/components/espressif/esp_rainmaker/versions/1.7.0/changelog). Legacy flow timed out if node and app data did not match within 1 minute — [RainMaker user-node mapping](https://docs.rainmaker.espressif.com/docs/product_overview/concepts/user-node-mapping) (snippet).
- **Particle**: claim code is single-use, for one device, valid ~1 hour, retired once accepted; exists because the app does not know the device ID while on the device's setup network — [Particle community: Purpose of claim code](https://community.particle.io/t/purpose-of-claim-code/34441); [Particle docs: Device claiming](https://docs.particle.io/getting-started/cloud/device-claiming/). (Community source; not confirmed in official API docs.)

### Inferences
- The FlexMix design mirrors RainMaker's "self-claiming + challenge-response mapping" problem: identity is created in the field after Wi-Fi, gated only by a code. RainMaker's own guidance is that challenge-response mapping is meaningful only when the identity was established earlier (assisted/factory claiming). Same conclusion here.
- Mapping to FlexMix: Matter DAC ≈ "factory-bound P-256 machine key registered by Operator"; Matter passcode/PASE ≈ "QR seal S used as BLE HPKE PSK"; RainMaker challenge-response ≈ existing `begin/complete` claim. The missing piece is only moving identity creation to the factory.
- Particle/Matter lesson for claim: a claim window should be short and single-use (already: claim_id once, expiry), and should require local proximity (already: BLE session). Add a physical "claim mode" window (e.g. first N minutes after power-on or after a button press) so a stolen QR alone, used at a distance, cannot start claim later.

### Gaps
- Tuya's activation/token pairing internals (pairing token from app → device → cloud) were not researched (no tool budget); I found no primary source to cite.
- Google Home/Matter fabric-level ownership transfer details not researched.

## Q2. Factory-time vs on-site first-boot activation; protecting the key on a Pi without a secure element; Pi CPU serial reliability

### Takeaway
Choose **factory-time activation**: at the provisioning station the Pi (with production SD/eMMC image) generates its P-256 key locally, the Operator CLI reads `serial + public_key` from the Pi over a trusted cable/LAN, and registers `(serial, public_key, key_id)` in one step; the seal S is written to the Pi and printed in the QR but is **not** sent to or stored by the server. Without a secure element the key is only as safe as the SD card (file 0600, root-only); treat SD-card cloning as an accepted MVP risk and plan an optional ATECC608/TPM path. The CPU serial is a good stable *label* but not an authenticator.

### Cited Findings
- AWS/Azure guidance: secret derivation and credential installation should happen off-device / at manufacture (Azure: derive device key off device; AWS: restrictive, short-lived, per-batch claim credentials and allow-list check) — [Azure symmetric key attestation](https://learn.microsoft.com/en-us/azure/iot-dps/concepts-symmetric-key-attestation); [AWS IoT Lens](https://docs.aws.amazon.com/wellarchitected/latest/iot-lens/device-provisioning.html).
- Serial: `/sys/firmware/devicetree/base/serial-number` returns a 16-char value (e.g. `100000000bc0a195` on a Pi 4), same as `Serial` in `/proc/cpuinfo` — [bret.dk](https://bret.dk/finding-your-raspberry-pi-serial-number/); [sleeplessbeastie](https://sleeplessbeastie.eu/2022/03/28/how-to-display-raspberry-pi-serial-number/). The devicetree string may carry a trailing NUL (my inference from common practice; strip it).
- Raspberry Pi OTP: 32-bit rows, 59 rows, readable with `vcgencmd otp_dump`, some values preprogrammed at the factory — [RPi white paper: Using the OTP memory](https://pip-assets.raspberrypi.com/categories/1260-security/documents/RP-003611-WP-2-Using%20the%20One%20time%20programmable%20memory%20on%20Raspberry%20Pi%20single%20board%20computers.pdf) (snippet only). I could not confirm from an official source which OTP row backs the serial on Pi 5.
- Pi firmware exposes a "customer OTP" region on all models and a second ("private key") region only on Pi 5 (bcm2712); a Linux nvmem driver for these was proposed in May 2026 — [LKML patch: nvmem Raspberry Pi OTP](https://lists.infradead.org/pipermail/linux-arm-kernel/2026-May/1131252.html); [LKML patch v2 3/4](https://lists.infradead.org/pipermail/linux-arm-kernel/2026-May/1126214.html).
- `rpi-otp-private-key` reads/writes a 256-bit key in OTP; writing is irreversible — [linuxcommandlibrary: rpi-otp-private-key](https://linuxcommandlibrary.com/man/rpi-otp-private-key) (third-party). `rpi-derive-key` stores a random 256-bit secret in OTP and HKDF-derives device keys, but warns the secret is **not hardware-protected**: anyone in the `video` group or with physical access can read it unless secure boot is enabled — [silitics/rpi-derive-key](https://github.com/silitics/rpi-derive-key); [PyPI rpi-derive-key](https://pypi.org/project/rpi-derive-key).
- AWS: "provisioning claim private keys should be secured at all times, including on the device" — [AWS provision-wo-cert](https://docs.aws.amazon.com/iot/latest/developerguide/provision-wo-cert.html).

### Inferences
Trade-off table (my synthesis):

| Aspect | Factory activation (recommended) | On-site first-boot activation (current) |
|---|---|---|
| QR leak before sale | Can only race the claim, and only within BLE range of the real machine | Remote identity takeover + permanent lockout (Q0) |
| Server secret at rest | Only public keys; no seal verifier needed | `seal_verifier` must be protected; DB leak + serial list → still need S (OK) but verifier is the sole gate |
| Unknown-commit retry in field | Not needed (no field bind) | Needs idempotent bind + durable pending state (issue 2) |
| Factory cost | Station must boot each Pi once with the production image and reach the provisioning DB (or produce a signed CSV import) | Just write S + config onto SD |
| Reflash/SD swap after sale | Needs re-key procedure (Operator/RMA) | Self-heals only if never bound; otherwise KEY_CONFLICT anyway |

- Factory station flow: (1) flash image; (2) boot; `identity.py` reads serial, generates key (if absent), writes `machine_key.pem` 0600 root via temp file + fsync + `os.replace`; (3) station tool reads `{serial, public_key_b64u}` over USB-serial/SSH on an isolated LAN; (4) Operator CLI (DB credentials, never on Pi) inserts `devices(serial, public_key, key_id, status='ACTIVE')` — idempotent on `(serial, public_key)`; (5) station writes S (32 random bytes from station CSPRNG or Pi `secrets.token_bytes`) into the Pi's config 0600 and prints the QR; (6) optional: device signs a "factory attestation" over `(serial, key_id, server pin hash)` that the station verifies before marking ACTIVE.
- If factory activation is truly impossible for MVP, minimum mitigations for field bind: (a) make the QR and S never leave a sealed package (accepted risk documented explicitly as "QR = full takeover"), (b) idempotent bind (Q4), (c) Operator `unbind` (Q4), (d) alert on KEY_CONFLICT. Still strictly weaker.
- Key protection without SE: PKCS8 PEM, 0600, owned by the service user (not world-readable dirs), on root FS; disable SSH password login; no key in backups/images. A cloned SD on another Pi can be detected locally by storing `serial` inside the identity file and refusing to start if `read_cpu_serial()` differs (raises the bar for casual cloning, does not stop root attackers who patch the code). Optional hardening: ATECC608A/B (I²C) or Infineon SLB9670 TPM 2.0 via PKCS#11/tpm2-pkcs11 where the key never leaves the chip; Pi 5 private OTP key + `rpi-derive-key` to encrypt the key file (only meaningful with secure boot).
- Serial: stable and unique enough as an identifier for the MVP but *spoofable* in software (any root process can report another value; a re-flashed SD can be put in any Pi). Server must trust only the **key**, never "serial says so"; serial is a lookup label.

### Gaps
- Whether Pi 5 serial is backed by OTP and its exact uniqueness guarantee: official RPi docs not reachable; no authoritative source confirmed.
- ATECC608/TPM Python integration cost on Pi OS (Bookworm/Trixie) not researched.

## Q3. ECDSA P-256 vs Ed25519 for device keys (Python `cryptography`), signature handling; is a plain SHA-256 verifier OK; constant-time compare

### Takeaway
Keep **ECDSA P-256/SHA-256** (already locked in contracts, required for Android/Kotlin BC, ATECC608 and TPM compatibility). Use `cryptography` ≥ 43 with `deterministic_signing=True` on the Pi to remove nonce-RNG risk, convert DER↔raw r‖s with `decode_dss_signature`/`encode_dss_signature`, enforce low-s. Ed25519 would be simpler but buys little here and breaks secure-element compatibility. A single SHA-256 over a 256-bit CSPRNG secret is sufficient (no Argon2 needed); compare with `hmac.compare_digest`. With factory activation the server can drop the verifier altogether.

### Cited Findings
- pyca `cryptography` ECDSA: `sign()` returns **DER** encoded signature, decodable via `decode_dss_signature`; `verify()` requires a DER signature, buildable with `encode_dss_signature`; `deterministic_signing` (RFC 6979) flag added in 43.0.0, raises `UnsupportedAlgorithm` if OpenSSL lacks support; verification is identical for deterministic and random signatures; `EllipticCurvePublicKey.from_encoded_point(curve, data)` loads SEC1 points; docs advise separate keys for signing and ECDH — [pyca/cryptography ec.rst (source of cryptography.io EC page)](https://github.com/pyca/cryptography/blob/main/docs/hazmat/primitives/asymmetric/ec.rst).
- Ed25519: 64-byte signatures, 32-byte keys, deterministic (no RNG nonce), hash fixed to SHA-512 — [Practical Cryptography for Developers: EdDSA and Ed25519](https://cryptobook.nakov.com/digital-signatures/eddsa-and-ed25519); [draft-josefsson-eddsa-ed25519](https://datatracker.ietf.org/doc/html/draft-josefsson-eddsa-ed25519).
- Fast hashes (incl. SHA-256) are unsuitable for **passwords** because low-entropy inputs can be brute-forced; use Argon2/scrypt/bcrypt/PBKDF2 — [CWE-916 summary](https://shoulder.dev/ja/threats/cwe/CWE-916); [Password::OWASP readme](https://mirrors.edge.kernel.org/CPAN/authors/id/W/WA/WATERKIP/Password-OWASP-0.005.readme). I could not fetch the OWASP cheat sheet itself to quote its high-entropy-token guidance.
- Matter stores only a verifier of the passcode, computed on the host at the factory; uses PBKDF iterations because the passcode is only 27 bits — [Nordic Matter factory provisioning](https://nrfconnectdocs.nordicsemi.com/addons/ncs-matter/latest/matter/end_product/factory_provisioning.html).

### Inferences
- SHA-256 verifier: the slow-hash requirement exists because passwords are guessable. S has 256 bits of entropy from a CSPRNG; brute force of 2^256 preimages is infeasible regardless of hash speed, so domain-separated SHA-256 (as specified, with serial in the input as a per-device "salt") is adequate. Matter needs iterations only because its passcode is 27 bits. Keep `hmac.compare_digest(computed, stored)` (bytes, equal length) for hygiene; also decode/length-check `seal_code` (exactly 32 bytes) before hashing.
- Implementation snippets (pyca):
  - Load public key: `ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), raw65)`; reject if `len(raw65)!=65 or raw65[0]!=0x04` before calling (it also accepts compressed 33-byte points otherwise).
  - Verify raw r‖s: split 32/32, `r,s=int.from_bytes(...)`; reject `r==0 or s==0 or r>=n or s>=n or s>n//2` (low-s); `pub.verify(encode_dss_signature(r,s), msg, ec.ECDSA(hashes.SHA256()))`. n = `0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551`.
  - Sign on Pi: `der=priv.sign(msg, ec.ECDSA(hashes.SHA256(), deterministic_signing=True))`; `r,s=decode_dss_signature(der)`; `if s>n//2: s=n-s`; output `r.to_bytes(32,'big')+s.to_bytes(32,'big')`.
  - Key file: `priv.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())`, written with `os.open(tmp, O_WRONLY|O_CREAT|O_EXCL, 0o600)`, fsync, `os.replace`, fsync dir.
- `key_id` should be derived, e.g. `b64u(SHA256(raw65))[:22]`, so it is deterministic and idempotency-friendly.
- Ed25519 would avoid low-s/DER handling but ATECC608 and Android Keystore hardware support favor P-256; contracts already lock P-256, so no change recommended.

### Gaps
- Exact `cryptography` version available on the target Pi OS image (needs ≥43 for deterministic_signing) not verified; fallback is the default randomized ECDSA, which is safe given the kernel CSPRNG.

## Q4. Idempotent bind, challenge-response with expiry, recovery/transfer of ownership

### Takeaway
Make every write idempotent on its natural key: bind on `(serial, public_key)` (same key → return same `machine_id/key_id` even after challenge expiry; different key → KEY_CONFLICT), claim on `claim_id` (already). Challenges: random 32-byte nonce, durable row, short TTL, single consumption, results stored with the row. Add three recovery paths: owner self-release, physical factory-reset + re-claim with a grace notice, and Operator admin unbind/re-key with audit log.

### Cited Findings
- Particle claim codes: single use, one device, ~1 h validity, retired after acceptance — [Particle community](https://community.particle.io/t/purpose-of-claim-code/34441).
- RainMaker legacy mapping timed out after 1 minute without matching data; later releases added a retry mechanism after mapping failures under load and an on-network challenge-response service to map already-provisioned devices without re-provisioning — [RainMaker user-node mapping](https://docs.rainmaker.espressif.com/docs/product_overview/concepts/user-node-mapping); [esp_rainmaker changelog 1.11.1](https://components.espressif.com/components/espressif/esp_rainmaker/versions/1.11.1/changelog); [changelog 1.8.3](https://components.espressif.com/components/espressif/esp_rainmaker/versions/1.8.3/changelog) (snippets).
- AWS: deactivating a compromised claim credential stops new registrations but not already-provisioned devices — so revocation must be per-device — [AWS provision-wo-cert](https://docs.aws.amazon.com/iot/latest/developerguide/provision-wo-cert.html).

### Inferences
- **Idempotent bind (if field bind is kept, or for the factory tool):** inside one transaction lock `devices WHERE serial=? FOR UPDATE`; if `public_key IS NULL` → set key, key_id, `bound_at`; elif `public_key == request.public_key` → return existing `(id, key_id)` (no state change); else KEY_CONFLICT. Safety: replaying an old bind request with the same key yields the same result and grants nothing new; an attacker cannot use it to change state. Require a fresh proof only for the *first* bind (or always require a fresh challenge, but allow an expired-challenge proof when the stored key equals the request key — the proof still proves possession). This removes the BLOCKED "unknown commit + expired challenge" case: the device simply requests a new challenge and binds again; same key → success.
- Retry on the device: persist `{state: pending_bind, public_key}` (no S, no secrets beyond the key file) so restart resumes; exponential backoff with jitter, e.g. 5 s → 10 min cap, unbounded while state is pending; stop on MACHINE_UNTRUSTED/KEY_CONFLICT.
- **Challenge design:** `nonce = secrets.token_bytes(32)`; `expires_at` from server clock; store `(id UUID, purpose, device_id/serial, nonce, expires_at, consumed_at, result_json)`; consumption `UPDATE … SET consumed_at=NOW(6) WHERE id=? AND consumed_at IS NULL` inside the business transaction; always include purpose + ids + nonce + expiry inside the signed bytes (already done via `J([...])`). Cleanup job deletes expired unconsumed rows after e.g. 24 h; keep consumed ones as audit.
- **Recovery / transfer (minimum viable set):**
  1. *Owner release* (app, authenticated owner): `owner_user_id = NULL` in a transaction + audit row; machine can be re-claimed via normal BLE flow.
  2. *Physical reset + re-claim* (lost owner account, resale): long-press reset on the machine puts it in "claim mode" and the machine signs `J(["flexmix-reset-v1", machine_id, reset_counter, server_time])`; server records `reset_requested_at`, notifies current owner; after a grace period (e.g. 72 h) without owner veto, owner is cleared. Prevents a thief from instantly claiming, while allowing resale. (Pattern derived from consumer device practice; not confirmed from a cited vendor doc.)
  3. *Operator admin unbind/re-key* (RMA, SD reflash, KEY_CONFLICT victim): CLI with DB credentials; sets `public_key=NULL`/new key, clears owner if requested, writes `device_audit(actor, action, reason, old_key_id, new_key_id, at)`. Requires out-of-band proof (purchase record).
- Local reset never changes server owner (keep current rule) — only paths 1–3 do.

### Gaps
- No primary source found describing how RainMaker/Tuya handle re-claim by a new user after factory reset (whether old mapping is auto-removed); the grace-period pattern is a design proposal, not a cited industry standard.

## Q5. MySQL InnoDB transaction for single-owner claim; isolation, locking, deadlock/retry, idempotent replay; Python driver

### Takeaway
Use a short transaction (no network/BLE/crypto inside), lock the `claim_challenges` row and the `devices` row `FOR UPDATE` in a fixed order, then a **conditional** `UPDATE devices SET owner_user_id=? WHERE id=? AND owner_user_id IS NULL` and check `rowcount`. The single `owner_user_id` column itself guarantees "one owner"; the conditional update is race-safe even without the explicit lock, and the explicit lock lets you distinguish "already mine" vs "someone else's" and write the stored result atomically. Run at READ COMMITTED, retry the whole transaction on deadlock 1213 / lock-wait 1205 up to 3 times with jitter. Keep `mysql-connector-python` (already pinned 26.7.0 in `server/requirements.txt`).

### Cited Findings
- MySQL 8.4 locking reads: `SELECT … FOR UPDATE` locks the rows read; `NOWAIT` never waits and fails (ERROR 3572) if the row is locked; `SKIP LOCKED` skips locked rows and returns an inconsistent view, unsuitable for general transactional work — [MySQL 8.4: Locking Reads](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking-reads.html) (via search snippet; page not fetchable).
- MySQL manual: with locking reads, consider READ COMMITTED; access tables/rows in a consistent order to reduce deadlocks; take needed locks early with `SELECT … FOR UPDATE` — [MySQL 5.6: How to minimize and handle deadlocks](https://docs.oracle.com/cd/E17952_01/mysql-5.6-en/innodb-deadlocks-handling.html); [MySQL: Internal locking](https://dev.mysql.com/doc/en/internal-locking.html). (Older manual version; same guidance exists in 8.x as far as I know, not verified.)
- `SELECT … FOR UPDATE` on a non-existent row / empty range can take gap locks and lead to deadlocks on a following INSERT — [MySQL Bug #25847](https://bugs.mysql.com/bug.php?id=25847); [Bug #48911](https://bugs.mysql.com/bug.php?id=48911).
- Retry on 1213 with exponential backoff + jitter — [pulse.support: MySQL deadlock found](https://pulse.support/kb/mysql-deadlock-found) (secondary).
- Repo: `server/src/database.py` opens one connection per transaction, `autocommit=False`, `time_zone='+00:00'`, and converts any `mysql.connector.Error` (incl. deadlock and commit failure) into `ApiError('SERVICE_UNAVAILABLE', 503)` after rollback; `server/requirements.txt` pins `mysql-connector-python==26.7.0`.

### Inferences
**Recommended algorithm for `complete_claim(user_id, claim_id, machine_proof, local_session_binding)`:**
1. Outside any transaction: parse/validate inputs; load claim + device (plain SELECT); verify ECDSA proof against the device's current `public_key` (CPU work outside locks).
2. `SET TRANSACTION ISOLATION LEVEL READ COMMITTED; START TRANSACTION;`
3. `SELECT user_id, device_id, expires_at, consumed_at, result_owner_user_id, verified_key_id FROM claim_challenges WHERE id=%s FOR UPDATE` → not found: CLAIM_EXPIRED/invalid; `user_id != caller` → CLAIM_ACCOUNT_MISMATCH.
4. If `consumed_at IS NOT NULL` → **idempotent replay**: if `result_owner_user_id == caller` return the same machine payload; else return the stored error. Do this *before* the expiry check so a committed-but-lost response is still recoverable after expiry.
5. If `expires_at <= UTC_TIMESTAMP(6)` → CLAIM_EXPIRED (do not consume).
6. `SELECT owner_user_id, key_id FROM devices WHERE id=%s FOR UPDATE`; if `key_id` changed since step 1 (admin re-key) → CLAIM_PROOF_INVALID.
7. `UPDATE devices SET owner_user_id=%s, owned_at=UTC_TIMESTAMP(6) WHERE id=%s AND owner_user_id IS NULL`; rowcount 1 → success; rowcount 0 → owner exists: if it equals caller (owned via another claim) decide per contract (contract says other claim must not reveal old result → return ALREADY_OWNED or treat as success; pick one and document), else ALREADY_OWNED.
8. `UPDATE claim_challenges SET consumed_at=UTC_TIMESTAMP(6), result_code=%s, result_owner_user_id=%s WHERE id=%s AND consumed_at IS NULL` (also consume on ALREADY_OWNED so the claim cannot be retried into a different outcome).
9. COMMIT. Wrap steps 2–9 in `for attempt in range(3)` catching `errno in (1213, 1205)` → rollback, sleep `random.uniform(0.02, 0.1)*2**attempt`, retry; this must happen **before** `database.transaction` turns the error into 503 (add an errno-aware retry helper around it).
10. Commit failure with unknown outcome (connection lost during COMMIT): return 503; client retries with the same `claim_id`; step 4 returns the committed result. This is why the result is stored in the claim row.
- Lock order everywhere: `claim_challenges` → `devices` (or the reverse, but consistent across begin/complete/release/admin). `begin_claim` should not lock devices FOR UPDATE; a plain read of `owner_user_id IS NULL` is a hint only, the real guarantee is step 7.
- rowcount pitfall: MySQL by default reports *changed* rows, not *matched* rows (unless the `FOUND_ROWS` client flag is set); here `owner_user_id` goes NULL→value so changed == matched, but never write "UPDATE … SET owner_user_id=? WHERE id=?" and rely on rowcount (same-value updates report 0). (Driver default not verified against connector docs.)
- Unique constraints: `devices.serial` UNIQUE, `devices.public_key_hash` UNIQUE (one key cannot bind two serials), `devices.key_id` UNIQUE; `claim_challenges.id` PK; FK `owner_user_id → users.id` (ON DELETE RESTRICT, explicit release on account deletion). No "owner table" needed because the column enforces single owner by construction.
- Driver: keep `mysql-connector-python` (official Oracle driver, already used project-wide in `server/` and `version1.1/`); one connection per transaction per thread (connections are not shared across `ThreadingHTTPServer` threads); use parameterized `cursor.execute(sql, params)`; consider `use_pure`/C-extension only if performance matters. PyMySQL (pure Python) or mysqlclient (C, needs libmysqlclient headers) bring no benefit worth a migration for the MVP.

**DDL sketch (MySQL 8, InnoDB, utf8mb4):**
```sql
CREATE TABLE devices (
  id               CHAR(36)     NOT NULL PRIMARY KEY,          -- UUID machine_id
  serial           CHAR(16)     NOT NULL,                      -- lowercase hex, label only
  name             VARCHAR(64)  NOT NULL,
  public_key       VARBINARY(65) NULL,                         -- SEC1 uncompressed
  public_key_sha256 BINARY(32)  NULL,
  key_id           VARCHAR(32)  NULL,
  seal_verifier    BINARY(32)   NULL,                          -- NULL/absent under factory activation
  status           ENUM('REGISTERED','ACTIVE','DISABLED') NOT NULL DEFAULT 'REGISTERED',
  bound_at         DATETIME(6)  NULL,
  owner_user_id    CHAR(36)     NULL,
  owned_at         DATETIME(6)  NULL,
  created_at       DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  UNIQUE KEY uq_devices_serial (serial),
  UNIQUE KEY uq_devices_key_id (key_id),
  UNIQUE KEY uq_devices_pubkey (public_key_sha256),
  KEY ix_devices_owner (owner_user_id),
  CONSTRAINT fk_devices_owner FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE activation_challenges (            -- only needed if field bind is kept
  id            CHAR(36)    NOT NULL PRIMARY KEY,
  device_id     CHAR(36)    NOT NULL,
  nonce         BINARY(32)  NOT NULL,
  expires_at    DATETIME(6) NOT NULL,
  consumed_at   DATETIME(6) NULL,
  bound_key_id  VARCHAR(32) NULL,
  result_code   VARCHAR(32) NULL,
  KEY ix_act_device (device_id, expires_at),
  CONSTRAINT fk_act_device FOREIGN KEY (device_id) REFERENCES devices(id)
) ENGINE=InnoDB;

CREATE TABLE claim_challenges (
  id                    CHAR(36)    NOT NULL PRIMARY KEY,   -- claim_id
  device_id             CHAR(36)    NOT NULL,
  user_id               CHAR(36)    NOT NULL,
  nonce                 BINARY(32)  NOT NULL,
  expires_at            DATETIME(6) NOT NULL,
  key_id_at_begin       VARCHAR(32) NOT NULL,
  local_session_binding CHAR(36)    NULL,
  consumed_at           DATETIME(6) NULL,
  result_code           VARCHAR(32) NULL,                   -- OK / ALREADY_OWNED
  result_owner_user_id  CHAR(36)    NULL,
  KEY ix_claim_device (device_id),
  KEY ix_claim_user (user_id),
  CONSTRAINT fk_claim_device FOREIGN KEY (device_id) REFERENCES devices(id),
  CONSTRAINT fk_claim_user FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB;

CREATE TABLE device_audit (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  device_id CHAR(36) NOT NULL, actor VARCHAR(64) NOT NULL,
  action ENUM('REGISTER','BIND','CLAIM','RELEASE','RESET_REQUEST','ADMIN_UNBIND','REKEY') NOT NULL,
  old_owner CHAR(36) NULL, new_owner CHAR(36) NULL,
  old_key_id VARCHAR(32) NULL, new_key_id VARCHAR(32) NULL,
  reason VARCHAR(255) NULL, at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  KEY ix_audit_device (device_id, at)
) ENGINE=InnoDB;
```
(Column types for `users.id` must match the existing S-01 schema; adjust CHAR(36)/BINARY(16) accordingly.)

**Pitfalls list:**
- Do not hold the transaction while waiting on BLE/network/HPKE (already a rule); verify signatures before BEGIN.
- Check `consumed_at` before `expires_at`, otherwise a lost response after commit becomes CLAIM_EXPIRED.
- The current `database.transaction` maps deadlocks to 503 — add retry on 1213/1205 or the second of two concurrent claims returns 503 instead of ALREADY_OWNED.
- Avoid `FOR UPDATE` on non-existent rows followed by INSERT (gap-lock deadlocks); look up by PK.
- Use DB time (`UTC_TIMESTAMP(6)`) or one server clock consistently for expiry; connection already sets `time_zone='+00:00'`.
- Store serial normalized (lowercase hex, 16 chars, strip trailing NUL from devicetree).
- Don't log seal codes, nonces, signatures; log claim_id/device_id only.

### Gaps
- Could not fetch current MySQL 8.4 deadlock section or mysql-connector-python docs (host blocked); rowcount/FOUND_ROWS default and errno handling in connector 26.x not verified.
- No benchmark needed at MVP scale; none researched.

## Recommended decision summary (for the report writer)

### Takeaway
1. Move identity creation to the factory: Pi generates P-256 key at the provisioning station; Operator CLI registers `(serial, public_key, key_id)`; remove the public `MACHINE_ACTIVATION_SEND bind` route (or restrict it to the factory network). QR seal S is only the BLE HPKE PSK / local possession proof; server stores no verifier. This closes issue (1) and makes issue (2) moot.
2. Keep idempotent semantics anyway: factory register idempotent on `(serial, public_key)`; claim idempotent on `claim_id` with stored result.
3. Add recovery: owner release, physical reset + grace-period re-claim, Operator unbind/re-key with audit table.
4. Keep ECDSA P-256 + raw r‖s low-s + deterministic signing; SHA-256 verifier (if any) is cryptographically fine for 256-bit S with `hmac.compare_digest`.
5. MySQL: READ COMMITTED, PK-based `FOR UPDATE` in fixed order, conditional owner UPDATE, result stored in claim row, retry on 1213/1205, keep mysql-connector-python.

### Cited Findings
- See Q1–Q5 sources; platform precedent: Matter (factory DAC + local passcode), RainMaker (challenge-response mapping requires prior claiming), AWS (trusted-user/factory credentials preferred over shared claim), Azure (off-device per-device key derivation) — [Silicon Labs Matter security](https://docs.silabs.com/matter/2.2.2/matter-fundamentals-security); [RainMaker changelog 1.7.0](https://components.espressif.com/components/espressif/esp_rainmaker/versions/1.7.0/changelog); [AWS provision-wo-cert](https://docs.aws.amazon.com/iot/latest/developerguide/provision-wo-cert.html); [Azure symmetric key attestation](https://learn.microsoft.com/en-us/azure/iot-dps/concepts-symmetric-key-attestation).

### Inferences
- Residual risk after the change: a person with the QR **and** physical BLE proximity to the powered machine before the buyer can still race the claim (same as Matter/RainMaker). Mitigate with a claim-mode window after power-on/button press and the owner-release/reset recovery path.
- Residual risk without SE: SD-card cloning copies the key; detect duplicates server-side by flagging concurrent polls from two IPs with the same key_id (heuristic) and allow Operator re-key.

### Gaps
- Contract owners (Planner/user) previously accepted the field-bind risk; changing to factory activation requires updating `cloud-protection.md`, `claim.md`, S-02/M-01 tickets and the factory station procedure — not researched here (process, not technical).
