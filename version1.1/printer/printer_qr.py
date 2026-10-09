"""Render a QR payload to PNG, prepare it for the label printer, and send
it to CUPS as raw TSPL.

CACH HOAT DONG (2 buoc, don gian):
    Buoc 1: Nhan payload (chuoi so da duoc ma hoa san boi qrproto.create()
            -- xem store_gui/serve.py). File nay KHONG ma hoa gi ca; no
            chi ve va in nguyen chuoi duoc dua vao.
    Buoc 2: Ve chuoi do thanh QR roi in ra may in nhan.

    Trươc day file nay tu ma hoa lai payload lan thu hai bang
    encrypt/encrypt.py (module do da bi xoa) -- nhung payload dua vao day
    tu store_gui/serve.py da la mot payload qrproto (protocol v1.4) hoan
    chinh: AES-256-GCM, ky, gan may dich -- mot lop ma hoa thu hai o day
    khong lam gi ngoai lam cho ma quet khong khop voi may quet thuc te.

Ben quet (order/qr_to_recipe.py, qua qrproto.verify()) doc thang chuoi so
nay tu scan/scanner.py -- khong co buoc giai ma rieng nao o giua nua.
"""

import sys
from pathlib import Path
from PIL import Image
import subprocess


if __package__ in {None, ""}:
    project_dir = str(Path(__file__).resolve().parent.parent)

    if project_dir not in sys.path:
        sys.path.insert(0, project_dir)

from configuration import machine          # noqa: E402


# ============================================================
# CONFIGURATION
# ============================================================

# IMPORTANT:
# This must be the CUPS printer name, NOT necessarily
# "Xprinter XP-350BM".
#
# Find it with:
#     lpstat -p -d
#
# Example:
#     PRINTER_NAME = "XP-350BM"
#
# Tên hàng đợi CUPS và khổ nhãn nằm ở configuration/machine.py -- đổi máy
# in hay đổi cuộn nhãn là sửa ở đó, không sửa ở đây.
PRINTER_NAME = machine.PRINTER_NAME

# Label size
LABEL_WIDTH_MM = machine.LABEL_WIDTH_MM
LABEL_HEIGHT_MM = machine.LABEL_HEIGHT_MM
GAP_MM = machine.LABEL_GAP_MM

# 203 DPI ~= 8 dots/mm
LABEL_WIDTH_DOTS = int(LABEL_WIDTH_MM * 8)     # 400
LABEL_HEIGHT_DOTS = int(LABEL_HEIGHT_MM * 8)   # 240

# Margin around image (~1 mm)
MARGIN_DOTS = 8

# Image file
IMAGE_FILE = "order_qr.png"


# ============================================================
# IMAGE PROCESSING
# ============================================================

def load_and_prepare_image(image_path: Path) -> Image.Image:
    """
    Load PNG image, resize to fit label and convert to 1-bit.
    """

    img = Image.open(image_path)

    # Usable print area
    max_w = LABEL_WIDTH_DOTS - 2 * MARGIN_DOTS
    max_h = LABEL_HEIGHT_DOTS - 2 * MARGIN_DOTS

    # Resize while preserving aspect ratio
    img.thumbnail((max_w, max_h), Image.LANCZOS)

    # Convert to 1-bit black/white
    img = img.convert("1")

    return img


# ============================================================
# IMAGE -> TSPL BITMAP
# ============================================================

def image_to_bitmap_data(img: Image.Image) -> tuple[int, int, bytes]:
    """
    Convert 1-bit image to TSPL BITMAP data.

    Returns:
        width_bytes: bitmap width in bytes
        height_dots: bitmap height in dots
        raw_bitmap_data: binary bitmap data
    """

    width, height = img.size

    # 8 pixels = 1 byte
    width_bytes = (width + 7) // 8

    pixels = img.load()
    data = bytearray()

    for y in range(height):

        for x_byte in range(width_bytes):

            byte_val = 0

            for bit in range(8):

                x = x_byte * 8 + bit

                if x < width:

                    pixel = pixels[x, y]

                    # White pixel -> print
                    if pixel != 0:
                        byte_val |= (1 << (7 - bit))

            data.append(byte_val)

    return width_bytes, height, bytes(data)


# ============================================================
# CREATE TSPL COMMAND
# ============================================================

def make_tspl(img: Image.Image) -> bytes:
    """
    Create TSPL command for printing one label.
    """

    width_bytes, height, bitmap_data = image_to_bitmap_data(img)

    img_w, img_h = img.size

    # Center image on label
    x = max(0, (LABEL_WIDTH_DOTS - img_w) // 2)
    y = max(0, (LABEL_HEIGHT_DOTS - img_h) // 2)

    # TSPL header
    header_lines = [
        f"SIZE {LABEL_WIDTH_MM:.1f} mm,{LABEL_HEIGHT_MM:.1f} mm",
        f"GAP {GAP_MM:.1f} mm,0 mm",
        "DIRECTION 1",
        "CLS",
    ]

    header = "\r\n".join(header_lines) + "\r\n"

    # BITMAP command
    #
    # BITMAP x,y,width_bytes,height,mode,
    #
    bitmap_cmd = (
        f"BITMAP {x},{y},{width_bytes},{height},0,"
    )

    # PRINT command
    footer = "\r\nPRINT 1,1\r\n"

    return (
        header.encode("ascii")
        + bitmap_cmd.encode("ascii")
        + bitmap_data
        + footer.encode("ascii")
    )


# ============================================================
# PRINT THROUGH LINUX CUPS
# ============================================================

def print_raw(tspl_data: bytes) -> int:
    """
    Send raw TSPL data to a Linux CUPS printer.

    CUPS must be installed and the printer must already
    be configured.
    """

    try:

        result = subprocess.run(
            [
                "lp",
                "-d",
                PRINTER_NAME,
                "-o",
                "raw",
            ],
            input=tspl_data,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

    except FileNotFoundError:
        raise RuntimeError(
            "Khong tim thay lenh 'lp'. "
            "Hay cai CUPS bang:\n"
            "sudo apt install cups"
        )

    except subprocess.CalledProcessError as error:

        message = error.stderr.decode(
            "utf-8",
            errors="replace"
        ).strip()

        raise RuntimeError(
            f"CUPS khong the in: {message}"
        )

    output = result.stdout.decode(
        "utf-8",
        errors="replace"
    ).strip()

    print(f"CUPS: {output}")

    # Try to extract job ID from:
    #
    # request id is XP-350BM-123 (1 file(s))
    #
    # Return the complete CUPS response if parsing is unnecessary.
    return 0


# ============================================================
# MAIN
# ============================================================

def render_payload_png(payload: str, target: Path) -> Path:
    """Draw one payload as a QR image and save it to `target`.

    Level H, wide border, matching what the store screen's own QR
    (store_gui/serve.py's /api/qr) and qrproto.qr.make_qr() both use --
    all three must agree module for module, or the symbol on screen, the
    symbol on the label, and the symbol the scanner actually sees could
    diverge.
    """
    import qrcode
    from qrcode.constants import ERROR_CORRECT_H

    code = qrcode.QRCode(
        error_correction=ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    code.add_data(payload)
    code.make(fit=True)

    image = code.make_image(fill_color="black", back_color="white")
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target)
    return target


def print_image(image_path: Path, dry_run: bool = False) -> None:
    """Send one PNG to the label printer.

    dry_run does everything except the final handover to CUPS, so the
    pipeline can be exercised without spending a label.
    """
    if not image_path.exists():
        raise FileNotFoundError(f"Khong tim thay file: {image_path}")

    img = load_and_prepare_image(image_path)
    print(f"Anh: {image_path.name} -> {img.size[0]}x{img.size[1]} dots (1-bit)")

    tspl_bytes = make_tspl(img)
    print(f"Tong du lieu TSPL: {len(tspl_bytes)} bytes")

    if dry_run:
        print("--dry-run: khong gui toi may in.")
        return

    print(f"Dang gui toi may in '{PRINTER_NAME}'...")
    print_raw(tspl_bytes)
    print("Da gui lenh in thanh cong.")


def print_payload(payload: str, dry_run: bool = False) -> None:
    """2 buoc: ve QR tu payload da co san -> in.

    `payload` phai la mot chuoi da hoan chinh (qrproto.create() da tao
    xong, ma hoa xong) -- ham nay khong bien doi payload theo bat ky
    cach nao, chi ve va in dung nguyen chuoi duoc dua vao.
    """
    target = Path(__file__).resolve().parent / IMAGE_FILE
    render_payload_png(payload, target)
    print_image(target, dry_run=dry_run)


def main() -> None:

    import argparse

    parser = argparse.ArgumentParser(
        description="Ve mot payload da co san thanh QR roi in ra may in nhan.",
    )
    parser.add_argument(
        "--payload",
        help="Chuoi so (payload hoan chinh) can ve QR va in.",
    )
    parser.add_argument(
        "--image", type=Path,
        help="In file PNG nay thay vi tao tu payload.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Chuan bi du lieu nhung khong gui toi may in.",
    )
    arguments = parser.parse_args()

    try:

        if arguments.payload:
            print_payload(arguments.payload, dry_run=arguments.dry_run)
            return

        # Image is located next to this Python file
        image_path = arguments.image or (
            Path(__file__).resolve().parent / IMAGE_FILE
        )

        if not image_path.exists():

            raise FileNotFoundError(
                f"Khong tim thay file: {image_path}"
            )

        print_image(image_path, dry_run=arguments.dry_run)

    except Exception as error:

        print(f"LOI: {error}")


if __name__ == "__main__":
    main()
