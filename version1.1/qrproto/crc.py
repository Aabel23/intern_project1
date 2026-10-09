"""CRC-16/CCITT-FALSE, shared by both trailers (OCRC and ICRC).

Parameters (spec section 6.1): polynomial 0x1021, initial value
0xFFFF, no input or output reflection, no final XOR.

The CRC is computed over the ASCII byte values of the digit string it
covers, not over a binary packing of the field values (spec section
6.2) -- there is no byte-order question, no field-alignment question,
and anyone holding the printed digits can verify the outer CRC by
hand, with no key.
"""

POLY = 0x1021
INIT = 0xFFFF


def crc16_ccitt(data: bytes) -> int:
    """CRC-16/CCITT-FALSE over raw bytes. Returns a 16-bit integer."""
    crc = INIT
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ POLY) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def compute_crc(body: str) -> str:
    """5-digit zero-padded decimal checksum for `body`, a digit string.

    Decimal rather than hex: hex would introduce letters A-F, forcing
    the QR encoder out of Numeric mode for the sake of one saved digit
    (spec section 6.3).
    """
    return f"{crc16_ccitt(body.encode('ascii')):05d}"
