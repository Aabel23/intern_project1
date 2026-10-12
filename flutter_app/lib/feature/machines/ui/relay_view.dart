import 'package:flutter/material.dart';

import 'package:simple_app/feature/machines/data/machine_controller.dart';
import 'package:simple_app/feature/machines/data/machine_service.dart';
import 'package:simple_app/shared/cloud/cloud_error.dart';
import 'package:simple_app/shared/ui/list_widgets.dart';

/// Tải lại khi đổi máy, bỏ kết quả của máy cũ, và gửi lệnh ghi có thể "Thử lại" an toàn:
/// thử lại dùng cùng request_id với retry=true nên máy không chạy lệnh hai lần.
mixin RelayView<T extends StatefulWidget> on State<T> {
  MachineController get controller;
  String? machineId;
  int generation = 0;
  bool busy = false;
  String? error;

  /// Đọc dữ liệu từ máy đang chọn; gọi lại sau mỗi lần đổi máy.
  Future<void> load(String machineId);

  /// Xóa dữ liệu đang hiển thị khi đổi máy.
  void clearData();

  @override
  void initState() {
    super.initState();
    controller.addListener(_selectionChanged);
    WidgetsBinding.instance.addPostFrameCallback((_) => _selectionChanged());
  }

  @override
  void dispose() {
    controller.removeListener(_selectionChanged);
    super.dispose();
  }

  void _selectionChanged() {
    if (!mounted || controller.selectedId == machineId) return;
    setState(() {
      machineId = controller.selectedId;
      generation++;
      error = null;
      clearData();
    });
    reload();
  }

  Future<void> reload() async {
    final id = machineId;
    if (id == null) return;
    final mine = ++generation;
    setState(() {
      busy = true;
      error = null;
    });
    try {
      await load(id);
    } on CloudError catch (e) {
      if (mounted && mine == generation) setState(() => error = e.code);
    } finally {
      if (mounted && mine == generation) setState(() => busy = false);
    }
  }

  bool current(int mine) => mounted && mine == generation;

  /// Gửi một lệnh; trả câu trả lời của máy, hoặc null nếu đã báo lỗi cho người dùng.
  Future<MachineAnswer?> write(
    String instruction,
    Map<String, dynamic> data,
  ) async {
    final id = machineId;
    if (id == null) return null;
    final requestId = newRequestId();
    var retry = false;
    while (true) {
      try {
        final answer = await controller.service.ask(
          id,
          instruction,
          data,
          requestId: requestId,
          retry: retry,
        );
        if (!answer.ok && mounted) {
          showMessage(
            context,
            answer.message ??
                relayMessage(answer.errorCode ?? 'COMMAND_FAILED'),
          );
        }
        return answer;
      } on CloudError catch (e) {
        if (!mounted) return null;
        final uncertain = e.code == 'TIMEOUT' || e.code == 'TRANSPORT_ERROR';
        if (!uncertain) {
          showMessage(context, relayMessage(e.code));
          return null;
        }
        final again = await showDialog<bool>(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('Chưa rõ kết quả'),
            content: const Text(
              'Mạng gián đoạn nên chưa biết máy đã làm chưa. Thử lại sẽ không làm lặp lệnh.',
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context, false),
                child: const Text('Bỏ qua'),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(context, true),
                child: const Text('Thử lại'),
              ),
            ],
          ),
        );
        if (again != true) return null;
        retry = true;
      }
    }
  }

  Widget? statusNotice() {
    if (machineId == null) return const ListNotice('Chưa chọn máy ở tab Máy.');
    if (busy) return const LinearProgressIndicator();
    if (error != null) return ListNotice(relayMessage(error!), error: true);
    return null;
  }
}
