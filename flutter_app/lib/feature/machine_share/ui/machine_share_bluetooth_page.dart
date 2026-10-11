import 'package:flutter/material.dart';

// Chia sẻ máy qua Bluetooth.
// Nhân viên mở màn hình nhận trước (điện thoại hiện cho quét thấy),
// chủ máy quét, chọn điện thoại nhân viên và gửi mã mời.
// Chủ máy: quét điện thoại nhân viên ở gần rồi gửi mã mời.
class ShareBluetoothSendPage extends StatelessWidget {
  const ShareBluetoothSendPage({super.key, this.devices = const []});
  final List<Map<String, String>> devices;

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Gửi qua Bluetooth')),
    body: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text(
            'Nhân viên mở tab Máy → Nhận chia sẻ qua Bluetooth, '
            'sau đó bấm Quét lại ở đây.',
          ),
          const SizedBox(height: 12),
          if (devices.isEmpty)
            const Text(
              'Không thấy thiết bị. Nhân viên cần mở màn hình nhận chia sẻ trước.',
            ),
          const SizedBox(height: 12),
          Expanded(
            child: ListView(
              children: [
                for (final device in devices)
                  ListTile(
                    leading: const Icon(Icons.smartphone),
                    title: Text(device['name']!),
                    subtitle: Text(device['address']!),
                    onTap: () {},
                  ),
              ],
            ),
          ),
          FilledButton.icon(
            onPressed: () {},
            icon: const Icon(Icons.refresh),
            label: const Text('Quét lại'),
          ),
        ],
      ),
    ),
  );
}

// Nhân viên: mở Bluetooth chờ chủ máy gửi mã để nhận máy.
class ShareBluetoothReceivePage extends StatelessWidget {
  const ShareBluetoothReceivePage({super.key});

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Nhận chia sẻ qua Bluetooth')),
    body: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text(
            'Cho phép hiện điện thoại khi được hỏi. Chủ máy mở Chia sẻ máy → '
            'Gửi qua Bluetooth và chọn điện thoại này.',
          ),
          const Spacer(),
          FilledButton.icon(
            onPressed: () {},
            icon: const Icon(Icons.bluetooth_searching),
            label: const Text('Chờ lại'),
          ),
        ],
      ),
    ),
  );
}
