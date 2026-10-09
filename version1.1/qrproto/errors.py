"""Exception hierarchy for the QR Payload Protocol v1.4 (+ TYPE 03 gram).

All protocol-level failures raise ``ProtocolError`` or one of its
subclasses (never a bare ``ValueError`` or another stdlib exception),
so callers can catch ``ProtocolError`` to mean "this payload is not
trustworthy" without enumerating every specific cause.

Mapping (matches spec sections 4/8):

- ``FormatError`` -- structural problems: non-digit input, a digit
  length that is not in the outer/inner length table, a bad VER
  field, a count field out of range, count/length disagreement, or a
  BCD pad nibble that is not 0xF.
- ``ChecksumError`` -- OCRC or ICRC mismatch.
- ``CryptoError`` -- AES-256-GCM authentication tag verification
  failure (forged payload, wrong key, or corrupt ciphertext/nonce/tag).
- ``MachineMismatchError`` -- decrypted MID does not equal the
  scanner's configured machine_id (stage 6).
- ``ExpiredError`` -- payload older than max_age_seconds (stage 7).
- ``ClockSkewError`` -- payload timestamped too far in the future
  (stage 7).
- Plain ``ProtocolError`` -- semantic/value failures with no dedicated
  subclass: ingredient range/registry/type, percentage/boolean/weight
  range, duplicate ingredient, SKU/instruction count out of range, or
  MID == 000000 (reserved).
"""


class ProtocolError(ValueError):
    """Base class for any payload that violates the specification."""


class FormatError(ProtocolError):
    """Structural malformation: non-digit input, bad length, bad VER,
    bad count, or a BCD pad nibble other than 0xF."""


class ChecksumError(ProtocolError):
    """Outer (OCRC) or inner (ICRC) checksum mismatch."""


class CryptoError(ProtocolError):
    """AES-256-GCM tag verification failed: forged, wrong key, or
    corrupt ciphertext."""


class MachineMismatchError(ProtocolError):
    """Decrypted machine ID does not match the scanner's configured
    machine_id."""


class ExpiredError(ProtocolError):
    """Payload is older than the configured max_age_seconds."""


class ClockSkewError(ProtocolError):
    """Payload timestamp is further in the future than
    clock_skew_seconds allows."""
