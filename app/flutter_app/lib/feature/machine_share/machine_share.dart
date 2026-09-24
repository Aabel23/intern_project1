import 'dart:async';

import 'package:flutter/material.dart';
import 'package:qr_flutter/qr_flutter.dart';

import '../../UI/dashboard/machine_api.dart';
import 'machine_share_bluetooth.dart';
import 'machine_share_qr.dart';

// Chủ máy hiện QR mã mời hoặc gửi qua Bluetooth; nhân viên quét QR ở tab Máy
// hoặc mở Nhận chia sẻ qua Bluetooth.
// Mã do server tạo, dùng một lần và hết hạn sau vài phút.
class DeviceSharePage extends StatefulWidget {
  const DeviceSharePage({
    super.key,
    required this.api,
    required this.machineId,
    this.machineName,
  });
  final MachineApi api;
  final String machineId;
  final String? machineName;

  @override
  State<DeviceSharePage> createState() => _DeviceSharePageState();
}

class _DeviceSharePageState extends State<DeviceSharePage> {
  String? qrData;
  DateTime? expiresAt;
  bool busy = false;
  String status = '';
  Timer? ticker;

  @override
  void initState() {
    super.initState();
    createCode();
    // Cập nhật thời gian còn lại mỗi giây.
    ticker = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    ticker?.cancel();
    super.dispose();
  }

  Future<void> createCode() async {
    setState(() {
      busy = true;
      qrData = null;
      status = 'Đang tạo mã chia sẻ…';
    });
    try {
      final result = await widget.api.createShare(widget.machineId);
      final code = result['code'];
      if (code is! String) {
        throw const MachineException('Server không trả mã chia sẻ.');
      }
      final seconds = (result['expires_in'] as num?)?.toInt() ?? 300;
      if (!mounted) return;
      setState(() {
        qrData = encodeShareQr(code);
        expiresAt = DateTime.now().add(Duration(seconds: seconds));
        status = 'Nhân viên mở tab Máy → Quét QR và quét mã này.';
      });
    } on MachineException catch (error) {
      if (mounted) setState(() => status = error.message);
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final left = expiresAt?.difference(DateTime.now());
    final expired = left != null && left.isNegative;
    return Scaffold(
      appBar: AppBar(title: const Text('Chia sẻ máy')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              widget.machineName ?? widget.machineId,
              style: Theme.of(context).textTheme.titleMedium,
            ),
            Text(widget.machineId),
            const SizedBox(height: 16),
            Expanded(
              child: Center(
                child: qrData == null || expired
                    ? Text(expired ? 'Mã đã hết hạn.' : '')
                    : QrImageView(
                        data: qrData!,
                        backgroundColor: Colors.white,
                        size: 260,
                      ),
              ),
            ),
            if (busy) const LinearProgressIndicator(),
            const SizedBox(height: 12),
            Text(status),
            if (left != null && !expired)
              Text(
                'Hết hạn sau ${left.inMinutes}:'
                '${(left.inSeconds % 60).toString().padLeft(2, '0')} · '
                'mỗi mã chỉ dùng cho một người.',
              ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: qrData == null || expired || busy
                  ? null
                  : () => Navigator.of(context).push(
                      MaterialPageRoute<void>(
                        builder: (_) =>
                            ShareBluetoothSendPage(payload: qrData!),
                      ),
                    ),
              icon: const Icon(Icons.bluetooth),
              label: const Text('Gửi qua Bluetooth'),
            ),
            const SizedBox(height: 8),
            FilledButton.icon(
              onPressed: busy ? null : createCode,
              icon: const Icon(Icons.refresh),
              label: const Text('Tạo mã mới'),
            ),
          ],
        ),
      ),
    );
  }
}
