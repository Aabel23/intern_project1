import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../../../shared/cloud/cloud_error.dart';
import '../../machines/data/machine_service.dart';
import '../data/claim_flow.dart';

/// Thêm máy: quét tem niêm phong → phiên Bluetooth → (Wi-Fi nếu máy chưa online) → nhận chủ.
class ClaimPage extends StatefulWidget {
  const ClaimPage({super.key, required this.flow});
  final ClaimFlow flow;

  @override
  State<ClaimPage> createState() => _ClaimPageState();
}

class _ClaimPageState extends State<ClaimPage> {
  bool scanning = true;
  bool busy = false;
  String status = 'Quét tem QR niêm phong trên máy.';

  static const _steps = {
    ClaimStep.permission: 'Đang xin quyền Bluetooth…',
    ClaimStep.connecting: 'Đang tìm và kết nối máy qua Bluetooth…',
    ClaimStep.wifi: 'Máy đang nối Wi-Fi…',
    ClaimStep.server: 'Đang xin server xác nhận…',
    ClaimStep.claiming: 'Máy đang ký xác nhận nhận chủ…',
    ClaimStep.done: 'Đã nhận máy.',
  };

  static String _error(String code) => switch (code) {
    'BLUETOOTH_PERMISSION' => 'Cần quyền Bluetooth để kết nối máy.',
    'BLUETOOTH_OFF' => 'Hãy bật Bluetooth rồi thử lại.',
    'MACHINE_NOT_FOUND' =>
      'Không thấy máy. Đứng gần máy, kiểm tra máy đang bật và chưa có chủ.',
    'PAIRING_FAILED' =>
      'Không xác thực được máy. Kiểm tra đúng tem của máy này.',
    'PAIRING_TIMEOUT' ||
    'PAIRING_TRANSPORT_ERROR' => 'Mất kết nối Bluetooth. Thử lại gần máy hơn.',
    'WIFI_FAILED' => 'Máy không nối được Wi-Fi. Kiểm tra tên và mật khẩu.',
    'MACHINE_UNTRUSTED' => 'Máy chưa được hãng đăng ký.',
    'ALREADY_OWNED' => 'Máy đã có chủ. Chủ cũ cần gỡ máy trước.',
    'CLAIM_EXPIRED' => 'Hết thời gian xác nhận, hãy thử lại.',
    'CANCELLED' => 'Đã hủy.',
    _ => 'Không thể nhận máy ($code).',
  };

  Future<({String ssid, String password})?> _askWifi() =>
      showDialog<({String ssid, String password})>(
        context: context,
        barrierDismissible: false,
        builder: (_) => const _WifiDialog(),
      );

  Future<void> _detect(BarcodeCapture capture) async {
    if (!scanning || busy) return;
    String? raw;
    for (final b in capture.barcodes) {
      if (b.format == BarcodeFormat.qrCode && b.rawValue != null) {
        raw = b.rawValue;
      }
    }
    if (raw == null) return;
    final qr = SealedQr.parse(raw);
    if (qr == null) {
      setState(() => status = 'Đây không phải tem niêm phong FlexMix.');
      return;
    }
    setState(() {
      scanning = false;
      busy = true;
    });
    try {
      final Machine machine = await widget.flow.run(
        qr,
        askWifi: _askWifi,
        onStep: (step) {
          if (mounted) setState(() => status = _steps[step]!);
        },
      );
      if (mounted) Navigator.of(context).pop(machine);
    } on CloudError catch (e) {
      if (mounted) setState(() => status = _error(e.code));
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Thêm máy')),
    body: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Expanded(
            child: scanning
                ? MobileScanner(
                    onDetect: _detect,
                    errorBuilder: (context, error) => const Center(
                      child: Text(
                        'Không mở được camera. Hãy cấp quyền Camera rồi quét lại.',
                      ),
                    ),
                  )
                : const Center(
                    child: Icon(Icons.bluetooth_searching, size: 64),
                  ),
          ),
          if (busy) const LinearProgressIndicator(),
          const SizedBox(height: 12),
          Text(status),
          const SizedBox(height: 12),
          FilledButton.icon(
            onPressed: busy ? null : () => setState(() => scanning = true),
            icon: const Icon(Icons.qr_code_scanner),
            label: const Text('Quét lại'),
          ),
        ],
      ),
    ),
  );
}

class _WifiDialog extends StatefulWidget {
  const _WifiDialog();
  @override
  State<_WifiDialog> createState() => _WifiDialogState();
}

class _WifiDialogState extends State<_WifiDialog> {
  final _ssid = TextEditingController();
  final _password = TextEditingController();

  @override
  void dispose() {
    _ssid.dispose();
    _password.clear();
    _password.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: const Text('Wi-Fi cho máy'),
    content: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        const Text(
          'Máy chưa có mạng. Mật khẩu chỉ gửi tới máy qua Bluetooth đã mã hóa.',
        ),
        TextField(
          controller: _ssid,
          decoration: const InputDecoration(labelText: 'Tên Wi-Fi'),
        ),
        TextField(
          controller: _password,
          obscureText: true,
          decoration: const InputDecoration(labelText: 'Mật khẩu'),
        ),
      ],
    ),
    actions: [
      TextButton(
        onPressed: () => Navigator.pop(context),
        child: const Text('Hủy'),
      ),
      FilledButton(
        onPressed: () {
          final ssid = _ssid.text.trim();
          if (ssid.isEmpty) return;
          Navigator.pop(context, (ssid: ssid, password: _password.text));
        },
        child: const Text('Gửi'),
      ),
    ],
  );
}
