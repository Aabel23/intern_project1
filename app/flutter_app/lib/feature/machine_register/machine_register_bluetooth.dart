import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../UI/dashboard/machine_api.dart';

String maskKey(String? key) {
  if (key == null || key.isEmpty) return '';
  return key.length <= 4 ? '••••' : '••••${key.substring(key.length - 4)}';
}

class MachinePairingPage extends StatefulWidget {
  const MachinePairingPage({super.key, required this.serverUrl, this.token});
  final String serverUrl;
  final String? token;

  @override
  State<MachinePairingPage> createState() => _MachinePairingPageState();
}

class _MachinePairingPageState extends State<MachinePairingPage> {
  static const channel = MethodChannel('flexmix/bluetooth_pairing');
  List<Map<String, String>> devices = [];
  // Bật để pair với máy thử (vd. laptop chạy sandbox) không đặt tên FlexMix-.
  bool showAll = false;
  Map<String, String>? packet;
  bool busy = false;
  String status = '';

  @override
  void initState() {
    super.initState();
    scan();
  }

  List<Map<String, String>> get shown => showAll
      ? devices
      : devices.where((d) => d['name']!.startsWith('FlexMix-')).toList();

  Future<void> scan() async {
    setState(() {
      busy = true;
      devices = [];
      packet = null;
      status = 'Đang quét máy FlexMix ở gần…';
    });
    try {
      final rows = await channel.invokeListMethod<dynamic>('scan') ?? [];
      if (!mounted) return;
      setState(() {
        devices = rows
            .map((row) => Map<String, String>.from(row as Map))
            .toList();
        status = shown.isEmpty
            ? 'Không thấy máy. Kiểm tra Bluetooth và chế độ pairing trên máy.'
            : 'Chọn máy để nhận thông tin.';
      });
    } on PlatformException catch (error) {
      if (mounted) setState(() => status = error.message ?? 'Không quét được.');
    } on MissingPluginException {
      if (mounted) {
        setState(() => status = 'Tính năng này cần chạy trên Android.');
      }
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> connect(Map<String, String> device) async {
    setState(() {
      busy = true;
      packet = null;
      status =
          'Đang kết nối ${device['name']}… Xác nhận ghép đôi nếu được hỏi.';
    });
    try {
      final answer = await channel.invokeMapMethod<String, String>('connect', {
        'address': device['address'],
      });
      if (!mounted) return;
      setState(() {
        packet = answer;
        status = 'Đã nhận thông tin máy. Đang gửi lên server…';
      });
      if (answer == null) {
        throw const MachineException('Không nhận được gói thông tin máy.');
      }
      final api = MachineApi(widget.serverUrl, token: widget.token);
      final result = await api.registerMachine(answer);
      if (mounted) {
        setState(
          () => status = '${result['message']} · ID: ${result['machine_id']}',
        );
      }
    } on MachineException catch (error) {
      if (mounted) setState(() => status = error.message);
    } on PlatformException catch (error) {
      if (mounted) {
        setState(() => status = error.message ?? 'Kết nối thất bại.');
      }
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> cancel() async {
    try {
      await channel.invokeMethod<void>('cancel');
    } on PlatformException {
      // Màn hình đã đóng, không cập nhật giao diện nữa.
    } on MissingPluginException {
      // Không có Bluetooth native ngoài Android.
    }
  }

  @override
  void dispose() {
    cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Pairing Bluetooth')),
    body: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (busy) const LinearProgressIndicator(),
          const SizedBox(height: 12),
          Text(status),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Hiện mọi thiết bị Bluetooth'),
            subtitle: const Text('Dùng khi thử với máy không tên FlexMix-'),
            value: showAll,
            onChanged: busy ? null : (value) => setState(() => showAll = value),
          ),
          const SizedBox(height: 12),
          Expanded(
            child: packet != null
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
                              'Tên máy: ${packet!['machine_name']}',
                            ),
                            const SizedBox(height: 8),
                            // Product key là mật khẩu của máy với server: chỉ hiện 4 ký tự cuối.
                            Text(
                              'Product key: ${maskKey(packet!['product_key'])}',
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
                          enabled: !busy,
                          onTap: () => connect(device),
                        ),
                    ],
                  ),
          ),
          FilledButton.icon(
            onPressed: busy ? null : scan,
            icon: const Icon(Icons.refresh),
            label: const Text('Quét lại'),
          ),
        ],
      ),
    ),
  );
}
