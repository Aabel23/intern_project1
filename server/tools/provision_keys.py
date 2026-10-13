"""Chạy một lần khi dựng server: tạo khóa server và ghi cấu hình công khai cho app + máy.

    python3 server/tools/provision_keys.py --url http://192.168.1.10:8080

- Khóa bí mật (HPKE X25519, ký P-256) nằm ở server/secrets/ quyền 0600, đã gitignore.
  Chép thư mục này lên server; không commit, không gửi qua chat.
- Ghi khóa công khai (server-trust.json) vào flutter_app/assets/ và version1.1/machine/config/,
  và URL vào flutter_app/lib/shared/cloud/server_endpoint.dart. Các file này commit được.
- Chạy lại giữ nguyên khóa cũ (chỉ cập nhật URL), vì đổi khóa làm mọi app/máy đã phát hành hỏng.
"""
import argparse
import base64
import ipaddress
import json
import os
from pathlib import Path
from urllib.parse import urlparse

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, x25519

ROOT = Path(__file__).resolve().parents[2]


def b64u(data):
    return base64.urlsafe_b64encode(data).decode('ascii').rstrip('=')


def private_key(path, generate):
    if path.exists():
        return serialization.load_pem_private_key(path.read_bytes(), password=None)
    key = generate()
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(pem)
    return key


def check_url(url):
    parsed = urlparse(url)
    if (parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.query
            or parsed.fragment or parsed.path not in ('', '/')):
        raise SystemExit('URL phải là HTTPS hoặc HTTP tới IP nội bộ, không path/query.')
    if parsed.scheme == 'http':
        try:
            address = ipaddress.ip_address(parsed.hostname)
        except ValueError:
            raise SystemExit('HTTP chỉ dùng địa chỉ IP nội bộ.') from None
        if address.version != 4 or not (address.is_loopback or any(address in subnet for subnet in (
                ipaddress.ip_network('10.0.0.0/8'), ipaddress.ip_network('172.16.0.0/12'),
                ipaddress.ip_network('192.168.0.0/16')))):
            raise SystemExit('HTTP chỉ dùng địa chỉ IP nội bộ.')
    return url.rstrip('/')


def main(argv=None):
    parser = argparse.ArgumentParser(description='Tạo khóa server và ghi cấu hình công khai cho app và máy.')
    parser.add_argument('--url', required=True, help='URL server: HTTP IP nội bộ hoặc HTTPS')
    parser.add_argument('--secrets', default=str(ROOT / 'server' / 'secrets'))
    args = parser.parse_args(argv)
    url = check_url(args.url)
    secrets = Path(args.secrets)
    secrets.mkdir(mode=0o700, parents=True, exist_ok=True)
    hpke = private_key(secrets / 'server-hpke.pem', x25519.X25519PrivateKey.generate)
    sign = private_key(secrets / 'server-sign.pem', lambda: ec.generate_private_key(ec.SECP256R1()))
    trust = {
        'v': 1,
        'hpke': {'kid': 'server-hpke-1', 'public_key': b64u(hpke.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw))},
        'signing': {'kid': 'server-sign-1', 'public_key': b64u(sign.public_key().public_bytes(
            serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint))},
    }
    text = json.dumps(trust, indent=2) + '\n'
    for target in (secrets / 'server-trust.json', ROOT / 'flutter_app' / 'assets' / 'server-trust.json',
                   ROOT / 'version1.1' / 'machine' / 'config' / 'server-trust.json'):
        target.write_text(text, encoding='utf-8')
    (ROOT / 'flutter_app' / 'lib' / 'shared' / 'cloud' / 'server_endpoint.dart').write_text(
        '// Ghi bởi server/tools/provision_keys.py; --dart-define=FLEXMIX_SERVER_BASE_URL ghi đè khi build.\n'
        f"const defaultServerBaseUrl = '{url}';\n", encoding='utf-8')
    print('Đã ghi server-trust.json cho app và máy, URL app:', url)
    print('Biến môi trường cho server (đường dẫn tuyệt đối trên máy chủ):')
    for name, file in (('SERVER_HPKE_KEY_FILE', 'server-hpke.pem'), ('SERVER_SIGNING_KEY_FILE', 'server-sign.pem'),
                       ('SERVER_TRUST_FILE', 'server-trust.json')):
        print(f'  {name}={(secrets / file).resolve()}')


if __name__ == '__main__':
    main()
