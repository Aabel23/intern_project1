"""Render an outer payload string as a printable QR symbol.

The payload is entirely digits, so a conforming encoder picks Numeric
mode (3.33 bits/digit) automatically -- no mode is forced here, but
`qrcode` selects it for an all-digit `add_data()` string by default.
Error correction is fixed at level H (30% damage recovery) for label
durability, matching spec section 5.1.
"""

from . import constants as C
from .envelope import validate_outer_structure_and_crc


def make_qr(payload: str, module_size_mm: float = 0.5, dpi: int = 300, fixed_version=None):
    """Render an outer payload string as a QR symbol at error
    correction level H.

    module_size_mm : printed size of one module; sets pixel resolution
    fixed_version  : force a symbol version, or None to auto-size
    Returns a PIL Image.
    """
    import qrcode
    from qrcode.constants import ERROR_CORRECT_H

    # Validate outer structure + OCRC before spending effort on the
    # symbol (stages 1-2; stage 3+ needs the key, which this function
    # does not have -- a caller wanting the full 8-stage check should
    # run api.verify() separately).
    validate_outer_structure_and_crc(payload)

    # Pixels per module, so that one module prints at module_size_mm.
    box_size = max(1, round(module_size_mm / 25.4 * dpi))

    qr = qrcode.QRCode(
        version=fixed_version,          # None => smallest that fits
        error_correction=ERROR_CORRECT_H,
        box_size=box_size,
        border=4,                       # 4-module quiet zone, ISO 18004
    )
    qr.add_data(payload)
    qr.make(fit=fixed_version is None)
    return qr.make_image(fill_color="black", back_color="white")


def minimum_version(payload: str) -> int:
    """Smallest QR symbol version holding this payload at level H,
    from the count implied by the payload's own length (spec section
    2.3 / 5.2). Raises FormatError via validate_outer_structure_and_crc
    if the length is not one this protocol produces."""
    _, _, entry = validate_outer_structure_and_crc(payload)
    return VERSION_FOR_COUNT[entry["n"]]


def symbol_dimensions(version: int, module_size_mm: float = 0.5) -> dict:
    """Printed size of a symbol version, including the 4-module quiet zone."""
    modules = 4 * version + 17
    return {
        "version": version,
        "modules": modules,
        "symbol_mm": modules * module_size_mm,
        "footprint_mm": (modules + 8) * module_size_mm,
    }


# Numeric-mode capacity at level H (spec section 5.2), and the smallest
# version each opcode count needs. Verified against the qrcode
# reference library, not transcribed from a datasheet.
NUMERIC_CAPACITY_LEVEL_H = {
    6: 139, 7: 154, 8: 202, 9: 235, 10: 288,
}

VERSION_FOR_COUNT = {}
for _n in range(C.MAX_PAIRS + 1):
    _outer = C.outer_len(_n)
    for _version, _capacity in sorted(NUMERIC_CAPACITY_LEVEL_H.items()):
        if _outer <= _capacity:
            VERSION_FOR_COUNT[_n] = _version
            break
    else:
        raise RuntimeError(f"qrproto.qr: no known QR version holds {_outer} digits at level H")
