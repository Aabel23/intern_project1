import 'package:flutter/material.dart';
import 'package:qr_flutter/qr_flutter.dart';

import 'package:simple_app/shared/ui/list_widgets.dart';

import 'package:simple_app/feature/machine_share/ui/machine_share_bluetooth_page.dart';

// Chủ máy hiện QR mã mời hoặc gửi qua Bluetooth; nhân viên quét QR ở tab Máy
// hoặc mở Nhận chia sẻ qua Bluetooth.
// Cuối trang là danh sách nhân viên đang được giao máy để chủ thu hồi quyền.
class DeviceSharePage extends StatefulWidget {
  const DeviceSharePage({
    super.key,
    required this.machineId,
    this.machineName,
    this.qrData,
    this.staff = const [],
  });
  final String machineId;
  final String? machineName;
  final String? qrData;
  final List<Map<String, dynamic>> staff;

  @override
  State<DeviceSharePage> createState() => _DeviceSharePageState();
}

class _DeviceSharePageState extends State<DeviceSharePage> {
  Future<void> revoke(Map<String, dynamic> member) async {
    final name = member['full_name'] ?? member['username'];
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Thu hồi quyền?'),
        content: Text('$name sẽ không quản lý máy này nữa.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Hủy'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Thu hồi'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    notAvailableYet(context);
  }

  void sendBluetooth() {
    Navigator.of(context).push(
      MaterialPageRoute<void>(builder: (_) => const ShareBluetoothSendPage()),
    );
  }

  @override
  Widget build(BuildContext context) {
    final qrData = widget.qrData;
    final staff = widget.staff;
    return Scaffold(
      appBar: AppBar(title: const Text('Chia sẻ máy')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            widget.machineName ?? widget.machineId,
            style: Theme.of(context).textTheme.titleMedium,
          ),
          Text(widget.machineId),
          const SizedBox(height: 16),
          SizedBox(
            height: 260,
            child: Center(
              child: qrData == null
                  ? const Text('Chưa có mã chia sẻ.')
                  : QrImageView(
                      data: qrData,
                      backgroundColor: Colors.white,
                      size: 260,
                    ),
            ),
          ),
          const SizedBox(height: 12),
          const Text('Nhân viên mở tab Máy → Quét QR và quét mã này.'),
          const SizedBox(height: 12),
          OutlinedButton.icon(
            onPressed: sendBluetooth,
            icon: const Icon(Icons.bluetooth),
            label: const Text('Gửi qua Bluetooth'),
          ),
          const SizedBox(height: 8),
          FilledButton.icon(
            onPressed: () => notAvailableYet(context),
            icon: const Icon(Icons.refresh),
            label: const Text('Tạo mã mới'),
          ),
          const Divider(height: 32),
          Text(
            'Nhân viên đang quản lý',
            style: Theme.of(context).textTheme.titleSmall,
          ),
          if (staff.isEmpty) const Text('Chưa giao máy cho nhân viên nào.'),
          for (final member in staff)
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.person_outline),
              title: Text('${member['full_name'] ?? member['username']}'),
              subtitle: Text('${member['username']}'),
              trailing: IconButton(
                tooltip: 'Thu hồi quyền',
                icon: const Icon(Icons.person_remove_outlined),
                onPressed: () => revoke(member),
              ),
            ),
        ],
      ),
    );
  }
}
