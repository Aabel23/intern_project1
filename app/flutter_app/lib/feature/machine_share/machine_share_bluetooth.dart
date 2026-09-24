import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../UI/dashboard/machine_api.dart';
import 'machine_share_qr.dart';

// Chia sẻ máy qua Bluetooth, cùng giao thức dòng JSON với pairing máy.
// Nhân viên mở màn hình nhận trước (điện thoại hiện cho quét thấy),
// chủ máy quét, chọn điện thoại nhân viên và gửi đúng nội dung của QR chia sẻ.
const _channel = MethodChannel('flexmix/bluetooth_pairing');

String _platformError(PlatformException error, String fallback) =>
    error.message ?? fallback;

// Chủ máy: quét điện thoại nhân viên ở gần rồi gửi mã mời.
class ShareBluetoothSendPage extends StatefulWidget {
  const ShareBluetoothSendPage({super.key, required this.payload});
  // Nội dung đã qua encodeShareQr, giống hệt QR đang hiện.
  final String payload;

  @override
  State<ShareBluetoothSendPage> createState() => _ShareBluetoothSendPageState();
}

class _ShareBluetoothSendPageState extends State<ShareBluetoothSendPage> {
  List<Map<String, String>> devices = [];
  bool busy = false;
  bool sent = false;
  String status = '';

  @override
  void initState() {
    super.initState();
    scan();
  }

  @override
  void dispose() {
    _cancel();
    super.dispose();
  }

  Future<void> scan() async {
    setState(() {
      busy = true;
      devices = [];
      status = 'Đang quét điện thoại ở gần…';
    });
    try {
      final rows = await _channel.invokeListMethod<dynamic>('scan') ?? [];
      if (!mounted) return;
      setState(() {
        devices = rows
            .map((row) => Map<String, String>.from(row as Map))
            .toList();
        status = devices.isEmpty
            ? 'Không thấy thiết bị. Nhân viên cần mở màn hình nhận chia sẻ trước.'
            : 'Chọn điện thoại của nhân viên.';
      });
    } on PlatformException catch (error) {
      if (mounted) {
        setState(() => status = _platformError(error, 'Không quét được.'));
      }
    } on MissingPluginException {
      if (mounted) {
        setState(() => status = 'Tính năng này cần chạy trên Android.');
      }
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> send(Map<String, String> device) async {
    setState(() {
      busy = true;
      status =
          'Đang gửi mã tới ${device['name']}… Xác nhận ghép đôi nếu được hỏi.';
    });
    try {
      await _channel.invokeMethod<void>('sendShare', {
        'address': device['address'],
        'payload': widget.payload,
      });
      if (!mounted) return;
      setState(() {
        sent = true;
        status =
            'Đã gửi mã cho ${device['name']}. '
            'Máy sẽ hiện trong danh sách của nhân viên sau khi server xác nhận.';
      });
    } on PlatformException catch (error) {
      if (mounted) {
        setState(() => status = _platformError(error, 'Gửi thất bại.'));
      }
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

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
          if (busy) const LinearProgressIndicator(),
          const SizedBox(height: 12),
          Text(status),
          const SizedBox(height: 12),
          Expanded(
            child: ListView(
              children: [
                for (final device in devices)
                  ListTile(
                    leading: const Icon(Icons.smartphone),
                    title: Text(device['name']!),
                    subtitle: Text(device['address']!),
                    enabled: !busy && !sent,
                    onTap: () => send(device),
                  ),
              ],
            ),
          ),
          FilledButton.icon(
            onPressed: busy || sent ? null : scan,
            icon: const Icon(Icons.refresh),
            label: const Text('Quét lại'),
          ),
        ],
      ),
    ),
  );
}

// Nhân viên: mở Bluetooth chờ chủ máy gửi mã, rồi gửi mã lên server để nhận máy.
class ShareBluetoothReceivePage extends StatefulWidget {
  const ShareBluetoothReceivePage({
    super.key,
    required this.serverUrl,
    this.token,
  });
  final String serverUrl;
  final String? token;

  @override
  State<ShareBluetoothReceivePage> createState() =>
      _ShareBluetoothReceivePageState();
}

class _ShareBluetoothReceivePageState extends State<ShareBluetoothReceivePage> {
  bool busy = false;
  bool done = false;
  String status = '';

  @override
  void initState() {
    super.initState();
    receive();
  }

  @override
  void dispose() {
    _cancel();
    super.dispose();
  }

  Future<void> receive() async {
    setState(() {
      busy = true;
      status = 'Đang chờ chủ máy gửi mã qua Bluetooth (tối đa 2 phút)…';
    });
    try {
      final raw = await _channel.invokeMethod<String>('receiveShare');
      if (raw == null) throw const FormatException();
      final data = parseMachineQr(raw);
      if (data['type'] != 'share') throw const FormatException();
      if (!mounted) return;
      setState(() => status = 'Đã nhận mã. Đang xác nhận với server…');
      final api = MachineApi(widget.serverUrl, token: widget.token);
      final result = await api.acceptShare(data['code']!);
      if (!mounted) return;
      setState(() {
        done = true;
        status =
            '${result['message'] ?? 'Đã nhận quản lý máy'}: '
            '${result['machine_name'] ?? result['machine_id']}';
      });
    } on FormatException {
      if (mounted) {
        setState(() => status = 'Gói nhận được không phải mã chia sẻ.');
      }
    } on MachineException catch (error) {
      if (mounted) setState(() => status = error.message);
    } on PlatformException catch (error) {
      if (mounted) {
        setState(() => status = _platformError(error, 'Nhận thất bại.'));
      }
    } on MissingPluginException {
      if (mounted) {
        setState(() => status = 'Tính năng này cần chạy trên Android.');
      }
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

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
          const SizedBox(height: 12),
          if (busy) const LinearProgressIndicator(),
          const SizedBox(height: 12),
          Text(status),
          const Spacer(),
          FilledButton.icon(
            onPressed: busy || done ? null : receive,
            icon: const Icon(Icons.bluetooth_searching),
            label: const Text('Chờ lại'),
          ),
        ],
      ),
    ),
  );
}

Future<void> _cancel() async {
  try {
    await _channel.invokeMethod<void>('cancel');
  } on PlatformException {
    // Màn hình đã đóng, không cập nhật giao diện nữa.
  } on MissingPluginException {
    // Không có Bluetooth native ngoài Android.
  }
}
