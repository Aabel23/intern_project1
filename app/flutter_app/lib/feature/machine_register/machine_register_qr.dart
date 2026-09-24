import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../../UI/dashboard/machine_api.dart';
import '../machine_share/machine_share_qr.dart';

class MachineQrPage extends StatefulWidget {
  const MachineQrPage({super.key, required this.serverUrl, this.token});
  final String serverUrl;
  final String? token;

  @override
  State<MachineQrPage> createState() => _MachineQrPageState();
}

class _MachineQrPageState extends State<MachineQrPage> {
  bool scanning = true;
  bool busy = false;
  Map<String, String>? packet;
  String status = 'Quét tem QR trên máy hoặc QR chia sẻ từ chủ máy.';

  Future<void> detect(BarcodeCapture capture) async {
    if (!scanning || busy) return;
    String? raw;
    for (final barcode in capture.barcodes) {
      if (barcode.format == BarcodeFormat.qrCode && barcode.rawValue != null) {
        raw = barcode.rawValue;
        break;
      }
    }
    if (raw == null) return;

    // Khóa ngay trước await để một QR không gửi nhiều request liên tiếp.
    setState(() {
      scanning = false;
      busy = true;
      status = 'Đang đọc QR và gửi thông tin lên server…';
    });
    try {
      final data = parseMachineQr(raw);
      final api = MachineApi(widget.serverUrl, token: widget.token);
      if (data['type'] == 'share') {
        final result = await api.acceptShare(data['code']!);
        if (!mounted) return;
        setState(() {
          packet = {'machine_name': '${result['machine_name'] ?? ''}'};
          status =
              '${result['message'] ?? 'Đã nhận quản lý máy'} · ID: ${result['machine_id']}';
        });
        return;
      }
      setState(() => packet = data);
      final result = await api.registerMachine(data);
      if (!mounted) return;
      setState(() {
        status =
            '${result['message'] ?? 'Đăng ký máy thành công'} · ID: ${result['machine_id']}';
      });
    } on FormatException {
      if (mounted) {
        setState(
          () => status = 'QR không hợp lệ. Cần tem QR trên máy hoặc QR chia sẻ từ chủ máy.',
        );
      }
    } on MachineException catch (error) {
      if (mounted) setState(() => status = error.message);
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  void scanAgain() {
    setState(() {
      scanning = true;
      packet = null;
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
                : Center(
                    child: Text(
                      packet?['machine_name'] ?? 'Chưa nhận được thông tin máy',
                    ),
                  ),
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
