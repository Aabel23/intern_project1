import 'package:flutter/material.dart';

import 'package:simple_app/feature/machines/data/machine_controller.dart';
import 'package:simple_app/feature/machines/data/machine_service.dart';
import 'package:simple_app/shared/cloud/cloud_error.dart';
import 'package:simple_app/shared/ui/app_theme.dart';

/// "Máy trả lời": mỗi lần Làm mới là một câu hỏi mới tới chính máy (machine.status.read).
/// Lỗi hay hết giờ xóa kết quả cũ; không hiện số cũ như thể vừa đọc.
class MachineStatusCard extends StatefulWidget {
  const MachineStatusCard({super.key, required this.controller});
  final MachineController controller;

  @override
  State<MachineStatusCard> createState() => _MachineStatusCardState();
}

class _MachineStatusCardState extends State<MachineStatusCard> {
  String? _machineId;
  int _generation = 0;
  bool _busy = false;
  MachineAnswer? _answer;
  String? _error;

  @override
  void initState() {
    super.initState();
    widget.controller.addListener(_onMachines);
  }

  @override
  void dispose() {
    widget.controller.removeListener(_onMachines);
    super.dispose();
  }

  void _onMachines() {
    if (widget.controller.selectedId != _machineId) {
      setState(() {
        _machineId = widget.controller.selectedId;
        _generation++;
        _answer = null;
        _error = null;
        _busy = false;
      });
    }
  }

  Future<void> _refresh() async {
    final machineId = widget.controller.selectedId;
    if (machineId == null || _busy) return;
    final generation = ++_generation;
    setState(() {
      _busy = true;
      _answer = null;
      _error = null;
    });
    try {
      final answer = await widget.controller.service.ask(
        machineId,
        'machine.status.read',
        {},
      );
      if (!mounted || generation != _generation) return;
      setState(() => answer.ok ? _answer = answer : _error = answer.errorCode);
    } on CloudError catch (e) {
      if (!mounted || generation != _generation) return;
      setState(() => _error = e.code);
    } finally {
      if (mounted && generation == _generation) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final machine = widget.controller.selected;
    final data = _answer?.data;
    final received = _answer == null
        ? null
        : DateTime.fromMillisecondsSinceEpoch(_answer!.receivedAt).toLocal();
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Expanded(
                  child: Text(
                    'Máy trả lời',
                    style: TextStyle(
                      fontWeight: FontWeight.w700,
                      color: AppColors.ink,
                    ),
                  ),
                ),
                TextButton.icon(
                  onPressed: machine == null || _busy ? null : _refresh,
                  icon: const Icon(Icons.refresh),
                  label: const Text('Làm mới'),
                ),
              ],
            ),
            if (machine == null)
              const Text('Chưa chọn máy.')
            else if (_busy)
              const LinearProgressIndicator()
            else if (_error != null)
              Text(
                relayMessage(_error!),
                style: const TextStyle(color: AppColors.orangeText),
              )
            else if (data != null) ...[
              Text('Serial: ${data['serial']}'),
              Text('Phần mềm: ${data['software_version']}'),
              Text('Chạy được: ${data['uptime_seconds']} giây'),
              Text('Lượt đọc: ${data['read_sequence']}'),
              Text(
                'Server nhận lúc ${received!.hour.toString().padLeft(2, '0')}:'
                '${received.minute.toString().padLeft(2, '0')}:'
                '${received.second.toString().padLeft(2, '0')}',
                style: const TextStyle(fontSize: 12, color: AppColors.muted),
              ),
            ] else
              const Text('Bấm Làm mới để hỏi trực tiếp máy.'),
          ],
        ),
      ),
    );
  }
}
