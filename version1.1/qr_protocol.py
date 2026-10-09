"""
Cài đặt tham chiếu của QR Code Payload Protocol v1.3.

Cấu trúc payload:
    <SKU:4><COUNT:2><OP1:4><D1:4> ... <OPn:4><Dn:4><CRC:5>

Trong đó mỗi opcode là <INGREDIENT:2><TYPE:2>, 0 <= n <= 12,
và tổng độ dài là 11 + 8n chữ số (tối thiểu 11, tối đa 107).

Phụ thuộc: qrcode[pil] để tạo ảnh QR (cài bằng: pip install "qrcode[pil]").
Các hàm encode/decode và CRC không cần thư viện ngoài.
"""

from dataclasses import dataclass
from typing import Union


# ---------------------------------------------------------------------------
# Hằng số giao thức
# ---------------------------------------------------------------------------
SKU_DIGITS = 4
COUNT_DIGITS = 2
OPCODE_DIGITS = 4
DATA_DIGITS = 4
CRC_DIGITS = 5
PAIR_DIGITS = OPCODE_DIGITS + DATA_DIGITS          # 8
HEADER_DIGITS = SKU_DIGITS + COUNT_DIGITS          # 6
MAX_PAIRS = 12
MIN_LENGTH = HEADER_DIGITS + CRC_DIGITS            # 11
MAX_LENGTH = HEADER_DIGITS + MAX_PAIRS * PAIR_DIGITS + CRC_DIGITS  # 107

INGREDIENT_MIN = 1
INGREDIENT_MAX = 24

TYPE_PERCENTAGE = "01"
TYPE_BOOLEAN = "02"

PERCENTAGE_MAX_RAW = 1000        # tương ứng 100.0%
BOOLEAN_FALSE = "0000"
BOOLEAN_TRUE = "0001"


class ProtocolError(ValueError):
    """Sinh lỗi khi payload vi phạm bất kỳ quy tắc nào của giao thức."""


# ---------------------------------------------------------------------------
# Checksum: CRC-16/CCITT-FALSE
# ---------------------------------------------------------------------------
def crc16_ccitt(data: bytes) -> int:
    """CRC-16/CCITT-FALSE: poly 0x1021, init 0xFFFF, không đảo bit, không XOR cuối."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def compute_crc(body: str) -> str:
    """Tính checksum 5 chữ số thập phân cho phần thân (body) của payload."""
    return f"{crc16_ccitt(body.encode('ascii')):05d}"


# ---------------------------------------------------------------------------
# Mô hình một cặp hướng dẫn (opcode/data)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Instruction:
    """Một cặp opcode/data.

    ingredient : 1-24, mã nguyên liệu trong cơ sở dữ liệu
    value      : float 0.0-100.0 cho phần trăm, hoặc bool cho cờ yes/no
    """
    ingredient: int
    value: Union[float, bool]

    @property
    def type_code(self) -> str:
        # Kiểm tra bool trước vì trong Python bool là subclass của int
        if isinstance(self.value, bool):
            return TYPE_BOOLEAN
        return TYPE_PERCENTAGE

    def encode(self) -> str:
        if not INGREDIENT_MIN <= self.ingredient <= INGREDIENT_MAX:
            raise ProtocolError(
                f"ingredient {self.ingredient} outside range "
                f"{INGREDIENT_MIN}-{INGREDIENT_MAX}"
            )
        opcode = f"{self.ingredient:02d}{self.type_code}"
        if isinstance(self.value, bool):
            data = BOOLEAN_TRUE if self.value else BOOLEAN_FALSE
        else:
            raw = round(self.value * 10)
            if not 0 <= raw <= PERCENTAGE_MAX_RAW:
                raise ProtocolError(
                    f"percentage {self.value} outside range 0.0-100.0"
                )
            data = f"{raw:04d}"
        return opcode + data


# ---------------------------------------------------------------------------
# Encode
# ---------------------------------------------------------------------------
def encode(sku: int, instructions: list) -> str:
    """Xây dựng chuỗi payload từ SKU và danh sách hướng dẫn."""
    if not 0 <= sku <= 9999:
        raise ProtocolError(f"SKU {sku} outside range 0000-9999")
    if len(instructions) > MAX_PAIRS:
        raise ProtocolError(
            f"{len(instructions)} instructions exceeds maximum {MAX_PAIRS}"
        )

    seen = set()
    for inst in instructions:
        if inst.ingredient in seen:
            raise ProtocolError(f"duplicate ingredient {inst.ingredient:02d}")
        seen.add(inst.ingredient)

    body = f"{sku:04d}{len(instructions):02d}"
    body += "".join(inst.encode() for inst in instructions)
    return body + compute_crc(body)


# ---------------------------------------------------------------------------
# Decode / Validate
# ---------------------------------------------------------------------------
def decode(payload: str, registry: set = None) -> dict:
    """Phân tích và kiểm tra toàn bộ payload.

    Thứ tự kiểm tra theo đặc tả (mục 7): giới hạn độ dài, count,
    khớp count/length, checksum, rồi ngữ nghĩa từng cặp.
    Ném ProtocolError nếu vi phạm bất kỳ quy tắc nào.
    """
    # --- Giai đoạn 1: cấu trúc ---
    if not MIN_LENGTH <= len(payload) <= MAX_LENGTH:
        raise ProtocolError(
            f"length {len(payload)} outside valid range {MIN_LENGTH}-{MAX_LENGTH}"
        )
    if not payload.isdigit():
        raise ProtocolError("payload must contain digits only")

    count = int(payload[SKU_DIGITS:HEADER_DIGITS])
    if count > MAX_PAIRS:
        raise ProtocolError(f"count {count:02d} exceeds maximum {MAX_PAIRS}")

    expected_length = MIN_LENGTH + PAIR_DIGITS * count
    if len(payload) != expected_length:
        raise ProtocolError(
            f"count {count:02d} implies {expected_length} digits, "
            f"got {len(payload)}"
        )

    # --- Giai đoạn 2: checksum ---
    split = HEADER_DIGITS + PAIR_DIGITS * count
    body, checksum = payload[:split], payload[split:]
    expected_crc = compute_crc(body)
    if checksum != expected_crc:
        raise ProtocolError(
            f"CRC mismatch: got {checksum}, expected {expected_crc}"
        )

    # --- Giai đoạn 3: ngữ nghĩa ---
    instructions = []
    seen = set()
    for index in range(count):
        base = HEADER_DIGITS + index * PAIR_DIGITS
        ingredient_s = body[base:base + 2]
        type_code = body[base + 2:base + 4]
        data = body[base + 4:base + 8]
        pair = index + 1

        ingredient = int(ingredient_s)
        if not INGREDIENT_MIN <= ingredient <= INGREDIENT_MAX:
            raise ProtocolError(
                f"pair {pair}: ingredient {ingredient_s} outside range "
                f"{INGREDIENT_MIN:02d}-{INGREDIENT_MAX:02d}"
            )
        if registry is not None and ingredient not in registry:
            raise ProtocolError(f"pair {pair}: ingredient {ingredient_s} not in registry")
        if ingredient in seen:
            raise ProtocolError(f"pair {pair}: duplicate ingredient {ingredient_s}")
        seen.add(ingredient)

        if type_code == TYPE_PERCENTAGE:
            raw = int(data)
            if raw > PERCENTAGE_MAX_RAW:
                raise ProtocolError(
                    f"pair {pair}: percentage {data} exceeds {PERCENTAGE_MAX_RAW}"
                )
            value = raw / 10.0
        elif type_code == TYPE_BOOLEAN:
            if data not in (BOOLEAN_FALSE, BOOLEAN_TRUE):
                raise ProtocolError(
                    f"pair {pair}: boolean must be {BOOLEAN_FALSE} or "
                    f"{BOOLEAN_TRUE}, got {data}"
                )
            value = data == BOOLEAN_TRUE
        else:
            raise ProtocolError(f"pair {pair}: unknown type {type_code}")

        instructions.append(Instruction(ingredient=ingredient, value=value))

    return {
        "sku": int(body[:SKU_DIGITS]),
        "count": count,
        "instructions": instructions,
    }


# ---------------------------------------------------------------------------
# Tạo mã QR
# ---------------------------------------------------------------------------
def make_qr(payload: str, module_size_mm: float = 0.5, dpi: int = 300,
            fixed_version: int = None):
    """Vẽ payload thành mã QR ở mức sửa lỗi H.

    module_size_mm : kích thước in của một module; quyết định độ phân giải
    fixed_version   : ép một phiên bản QR cụ thể, hoặc None để tự chọn nhỏ nhất
    Trả về một đối tượng PIL Image.
    """
    import qrcode
    from qrcode.constants import ERROR_CORRECT_H

    # Từ chối payload sai trước khi tốn công vẽ symbol.
    decode(payload)

    # Số pixel trên mỗi module để in đúng module_size_mm.
    box_size = max(1, round(module_size_mm / 25.4 * dpi))

    qr = qrcode.QRCode(
        version=fixed_version,          # None => tự chọn phiên bản nhỏ nhất vừa đủ
        error_correction=ERROR_CORRECT_H,
        box_size=box_size,
        border=4,                       # vùng trắng 4 module, theo ISO 18004
    )
    qr.add_data(payload)
    qr.make(fit=fixed_version is None)
    return qr.make_image(fill_color="black", back_color="white")


def symbol_dimensions(version: int, module_size_mm: float = 0.5) -> dict:
    """Kích thước vật lý ứng với một phiên bản QR."""
    modules = 4 * version + 17
    return {
        "version": version,
        "modules": modules,
        "symbol_mm": modules * module_size_mm,
        "footprint_mm": (modules + 8) * module_size_mm,
    }


# ---------------------------------------------------------------------------
# Chạy thử: ví dụ mục 8.1 của tài liệu (SKU 0042, 2 hướng dẫn)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    recipe = [
        Instruction(ingredient=7, value=25.0),   # nguyên liệu 07: 25.0%
        Instruction(ingredient=12, value=True),  # nguyên liệu 12: có
    ]

    payload = encode(sku=42, instructions=recipe)
    print("payload:", payload)
    print("length: ", len(payload), "chữ số")

    parsed = decode(payload)
    print("sku:    ", parsed["sku"])
    for inst in parsed["instructions"]:
        print(f"  ingredient {inst.ingredient:02d} -> {inst.value}")

    image = make_qr(payload)
    image.save("qrcode/image/recipe_42.png")
    print("Đã lưu mã QR vào recipe_42.png")
