"""Danh tính máy (hợp đồng v2 D1): serial CPU, khóa ký P-256 tự sinh và mã niêm phong S.

Cả hai bí mật được sinh một lần ở trạm xưởng rồi chỉ đọc lại. File hỏng thì dừng,
không bao giờ tự sinh khóa mới thay thế, vì server đã gắn khóa cũ với serial.
"""

import base64
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

P256_ORDER = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
SERIAL_PATTERN = re.compile(r"[0-9a-f]{16}")
KEY_FILE = "machine-key.pem"
SEAL_FILE = "seal-code"
CACHE_FILE = "machine-cache.json"


def b64u(data):
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def decode_b64u(value):
    if not isinstance(value, str):
        raise ValueError("b64u")
    raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    if b64u(raw) != value:
        raise ValueError("b64u")
    return raw


def json_bytes(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def key_id_for(public_key):
    return "mk_" + b64u(hashlib.sha256(public_key).digest())[:22]


@dataclass(frozen=True)
class Identity:
    serial: str
    private_key: ec.EllipticCurvePrivateKey = field(repr=False)
    public_key: bytes
    key_id: str

    def sign(self, message):
        """Chữ ký raw r||s low-s; deterministic (RFC 6979) nên không phụ thuộc entropy lúc khởi động."""
        der = self.private_key.sign(message, ec.ECDSA(hashes.SHA256(), deterministic_signing=True))
        r, s = decode_dss_signature(der)
        if s > P256_ORDER // 2:
            s = P256_ORDER - s
        return r.to_bytes(32, "big") + s.to_bytes(32, "big")


def read_cpu_serial(sources=("/sys/firmware/devicetree/base/serial-number", "/proc/cpuinfo")):
    """Serial 16 hex của Pi; thiếu thì dừng, không thay bằng UUID giả."""
    override = os.environ.get("FLEXMIX_CPU_SERIAL")
    if override:
        candidates = [override]
    else:
        candidates = []
        for source in sources:
            try:
                text = Path(source).read_text(encoding="ascii", errors="ignore")
            except OSError:
                continue
            if source.endswith("cpuinfo"):
                match = re.search(r"^Serial\s*:\s*([0-9a-fA-F]+)\s*$", text, re.MULTILINE)
                if match:
                    candidates.append(match.group(1))
            else:
                candidates.append(text.strip("\x00 \n"))
    for value in candidates:
        value = value.lower()[-16:].rjust(16, "0")
        if SERIAL_PATTERN.fullmatch(value) and value != "0" * 16:
            return value
    raise RuntimeError("Không đọc được serial CPU")


def _write_private(path, data):
    """Ghi atomic, quyền 0600 ngay từ lúc tạo, fsync cả thư mục."""
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(tmp, path)
    dir_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


def _read_private(path):
    if os.stat(path).st_mode & 0o077:
        raise RuntimeError(f"{path.name} phải có quyền 0600")
    return path.read_bytes()


def provision(state_dir, serial=None):
    """Chạy ở trạm xưởng: tạo khóa và S nếu chưa có. Chạy lại không đổi gì."""
    state_dir = Path(state_dir)
    state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    key_path, seal_path = state_dir / KEY_FILE, state_dir / SEAL_FILE
    if not key_path.exists():
        key = ec.generate_private_key(ec.SECP256R1())
        pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                serialization.NoEncryption())
        _write_private(key_path, pem)
    if not seal_path.exists():
        _write_private(seal_path, b64u(os.urandom(32)).encode("ascii"))
    return load_identity(state_dir, serial)


def load_identity(state_dir, serial=None):
    state_dir = Path(state_dir)
    serial = serial or read_cpu_serial()
    try:
        key = serialization.load_pem_private_key(_read_private(state_dir / KEY_FILE), password=None)
    except (OSError, ValueError) as error:
        raise RuntimeError("Khóa máy thiếu hoặc hỏng; cần Operator re-key, không tự sinh lại") from error
    if not isinstance(key, ec.EllipticCurvePrivateKey) or not isinstance(key.curve, ec.SECP256R1):
        raise RuntimeError("Khóa máy không phải P-256")
    public = key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    return Identity(serial, key, public, key_id_for(public))


def load_seal_code(state_dir):
    seal = decode_b64u(_read_private(Path(state_dir) / SEAL_FILE).decode("ascii").strip())
    if len(seal) != 32:
        raise RuntimeError("Mã niêm phong hỏng")
    return seal


def qr_payload(identity, seal):
    return json.dumps({"v": 1, "type": "flexmix-sealed", "serial": identity.serial, "seal_code": b64u(seal)},
                      separators=(",", ":"))


def read_cache(state_dir):
    """Thông tin không bí mật học từ server: machine_id, owned."""
    try:
        value = json.loads((Path(state_dir) / CACHE_FILE).read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def write_cache(state_dir, value):
    path = Path(state_dir) / CACHE_FILE
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value), encoding="utf-8")
    os.replace(tmp, path)


def load_server_trust(path):
    """Khóa công khai server ghim trước khi bán; sai schema thì dừng."""
    trust = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(trust, dict) or set(trust) != {"v", "hpke", "signing"} or trust["v"] != 1:
        raise RuntimeError("server-trust.json sai")
    hpke, signing = trust["hpke"], trust["signing"]
    if hpke.get("kid") != "server-hpke-1" or len(decode_b64u(hpke["public_key"])) != 32:
        raise RuntimeError("server-trust.json sai")
    sign_key = decode_b64u(signing["public_key"])
    if signing.get("kid") != "server-sign-1" or len(sign_key) != 65 or sign_key[0] != 4:
        raise RuntimeError("server-trust.json sai")
    return trust
