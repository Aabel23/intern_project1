import 'package:flutter/material.dart';

String maskKey(String? key) {
  if (key == null || key.isEmpty) return '';
  return key.length <= 4 ? '••••' : '••••${key.substring(key.length - 4)}';
}

class MachinePairingPage extends StatefulWidget {
  const MachinePairingPage({super.key, this.devices = const [], this.packet});
  final List<Map<String, String>> devices;
  final Map<String, String>? packet;

  @override
  State<MachinePairingPage> createState() => _MachinePairingPageState();
}

class _MachinePairingPageState extends State<MachinePairingPage> {
  // Bật để pair với máy thử (vd. laptop chạy sandbox) không đặt tên FlexMix-.
  bool showAll = false;
  String status =
      'Không thấy máy. Kiểm tra Bluetooth và chế độ pairing trên máy.';

  List<Map<String, String>> get shown => showAll
      ? widget.devices
      : widget.devices.where((d) => d['name']!.startsWith('FlexMix-')).toList();

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Pairing Bluetooth')),
    body: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const SizedBox(height: 12),
          Text(status),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Hiện mọi thiết bị Bluetooth'),
            subtitle: const Text('Dùng khi thử với máy không tên FlexMix-'),
            value: showAll,
            onChanged: (value) => setState(() => showAll = value),
          ),
          const SizedBox(height: 12),
          Expanded(
            child: widget.packet != null
                ? SingleChildScrollView(
                    child: Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('Thông tin đã nhận'),
                            const SizedBox(height: 12),
                            SelectableText(
                              'Tên máy: ${widget.packet!['machine_name']}',
                            ),
                            const SizedBox(height: 8),
                            // Product key là mật khẩu của máy với server: chỉ hiện 4 ký tự cuối.
                            Text(
                              'Product key: ${maskKey(widget.packet!['product_key'])}',
                            ),
                          ],
                        ),
                      ),
                    ),
                  )
                : ListView(
                    children: [
                      for (final device in shown)
                        ListTile(
                          leading: const Icon(Icons.bluetooth),
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
