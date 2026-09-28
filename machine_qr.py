"""Tạo tem QR đăng ký máy cho app (xem app/flutter_app/lib/feature/machine_share/QR.md).

    python machine_qr.py <ten_may> <product_key> [-o file.png]
    python machine_qr.py --from-env [-o file.png]   # đọc machine/config/machine.env
"""
import argparse
import json
import sys

import qrcode


def build_payload(name: str, key: str) -> str:
    # Giới hạn giống parseMachineQr trong app để tem nào in ra cũng quét được.
    name, key = name.strip(), key.strip()
    if not name or len(name) > 150:
        raise ValueError('Tên máy phải có 1-150 ký tự.')
    if not key or len(key) > 1024:
        raise ValueError('Product key phải có 1-1024 ký tự.')
    return json.dumps(
        {'type': 'pairing', 'machine_name': name, 'product_key': key},
        ensure_ascii=False,
    )


def main() -> None:
    # Console Windows mặc định cp1252, không in được tiếng Việt.
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description='Tạo QR đăng ký máy.')
    parser.add_argument('machine_name', nargs='?')
    parser.add_argument('product_key', nargs='?')
    parser.add_argument('--from-env', action='store_true',
                        help='lấy tên và key trong machine.env của máy')
    parser.add_argument('-o', '--output', help='Mặc định: <ten_may>.png')
    args = parser.parse_args()
    if args.from_env:
        from machine.config.env import get_machine_name, get_product_key
        args.machine_name, args.product_key = get_machine_name(), get_product_key()
    elif not args.machine_name or not args.product_key:
        parser.error('cần <ten_may> <product_key> hoặc --from-env')

    payload = build_payload(args.machine_name, args.product_key)
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=4)
    qr.add_data(payload.encode('utf-8'))
    qr.make(fit=True)
    output = args.output or f'{args.machine_name.strip()}.png'
    qr.make_image().save(output)
    print(f'Đã lưu {output}')


if __name__ == '__main__':
    main()
