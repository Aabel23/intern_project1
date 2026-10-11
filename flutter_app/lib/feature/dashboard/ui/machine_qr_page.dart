import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

class MachineQrPage extends StatefulWidget {
  const MachineQrPage({super.key});

  @override
  State<MachineQrPage> createState() => _MachineQrPageState();
}

class _MachineQrPageState extends State<MachineQrPage> {
  bool scanning = true;
  bool busy = false;
  String status = 'Quét tem QR trên máy hoặc QR chia sẻ từ chủ máy.';

  void detect(BarcodeCapture capture) {
    if (!scanning || busy) return;
    String? raw;
    for (final barcode in capture.barcodes) {
      if (barcode.format == BarcodeFormat.qrCode && barcode.rawValue != null) {
        raw = barcode.rawValue;
        break;
      }
    }
    if (raw == null) return;

    setState(() {
      scanning = false;
      status = 'Đã đọc QR.';
    });
  }

  void scanAgain() {
    setState(() {
      scanning = true;
      status = 'Quét tem QR trên máy hoặc QR chia sẻ từ chủ máy.';
    });
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Thêm máy bằng QR')),
    body: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Expanded(
            child: scanning
                // Widget tự quản lý camera khi app tạm dừng hoặc đóng màn hình.
                ? MobileScanner(
                    onDetect: detect,
                    errorBuilder: (context, error) => const Center(
                      child: Text(
                        'Không mở được camera. Hãy cấp quyền Camera trong cài đặt ứng dụng rồi quét lại.',
                      ),
                    ),
                  )
                : const Center(child: Text('Chưa nhận được thông tin máy')),
          ),
          if (busy) const LinearProgressIndicator(),
          const SizedBox(height: 12),
          Text(status),
          const SizedBox(height: 12),
          FilledButton.icon(
            onPressed: busy
                ? null
                : () {
                    // Tạo lại camera sau lỗi quyền hoặc sau một lượt quét.
                    setState(() => scanning = false);
                    WidgetsBinding.instance.addPostFrameCallback((_) {
                      if (mounted) scanAgain();
                    });
                  },
            icon: const Icon(Icons.qr_code_scanner),
            label: const Text('Quét lại'),
          ),
        ],
      ),
    ),
  );
}
