import 'package:flutter/material.dart';

import '../../../feature/machine_share/machine_share.dart';
import '../../../feature/machine_share/machine_share_bluetooth.dart';
import '../../../feature/machine_register/machine_register_bluetooth.dart';
import '../../../feature/machine_register/machine_register_qr.dart';

import '../dashboard/dashboard_controller.dart';
import '../dashboard/dashboard_widgets.dart';

// Bluetooth nhận thông tin máy; nhập mã chọn máy làm việc trong phiên này.
class MachinesTab extends StatelessWidget {
  const MachinesTab({super.key, required this.controller});
  final DashboardController controller;

  Future<void> _addById(BuildContext context) async {
    final id = await showDialog<String>(
      context: context,
      builder: (_) => const _MachineIdDialog(),
    );
    if (id == null || id.isEmpty) return;
    await controller.addMachine(id);
  }

  // Sau khi đăng ký hoặc nhận chia sẻ, đọc lại danh sách máy của tài khoản.
  Future<void> _open(BuildContext context, Widget page) async {
    await Navigator.of(context)
        .push(MaterialPageRoute<void>(builder: (_) => page));
    await controller.loadMyMachines();
  }

  void _onMenu(BuildContext context, String id, String value) {
    if (value != 'share') {
      notAvailableYet(context);
      return;
    }
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => DeviceSharePage(
          api: controller.api,
          machineId: id,
          machineName: controller.names[id],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(
    listenable: controller,
    builder: (context, _) => Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const PageTitle('Máy FlexMix'),
          const SizedBox(height: 4),
          const Text('Chọn máy để các tab nghiệp vụ hiển thị dữ liệu.'),
          if (controller.machinesError != null)
            Text(
              controller.machinesError!,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          if (controller.checking)
            const Padding(
              padding: EdgeInsets.only(top: 12),
              child: LinearProgressIndicator(),
            ),
          const SizedBox(height: 12),
          Expanded(
            child: RefreshIndicator(
              onRefresh: controller.refreshStatuses,
              child: controller.machines.isEmpty
                  ? ListView(
                      children: const [ListNotice('Quán chưa có máy nào.')],
                    )
                  : ListView.separated(
                      itemCount: controller.machines.length,
                      separatorBuilder: (_, _) => const SizedBox(height: 8),
                      itemBuilder: (_, index) {
                        final id = controller.machines[index];
                        final online = controller.online[id] == true;
                        final selected = id == controller.machineId;
                        final role = controller.roles[id];
                        return Card(
                          child: ListTile(
                            leading: Icon(
                              online ? Icons.cloud_done : Icons.cloud_off,
                            ),
                            title: Text(controller.names[id] ?? id),
                            subtitle: Text(
                              [
                                online ? 'Online' : 'Offline',
                                if (role == 'owner') 'Chủ máy',
                                if (role == 'manager') 'Được giao',
                                id,
                              ].join(' · '),
                            ),
                            selected: selected,
                            trailing: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                if (selected) const Icon(Icons.check_circle),
                                PopupMenuButton<String>(
                                  onSelected: (value) =>
                                      _onMenu(context, id, value),
                                  itemBuilder: (_) => [
                                    if (role == 'owner')
                                      const PopupMenuItem(
                                        value: 'share',
                                        child: Text('Chia sẻ cho nhân viên'),
                                      ),
                                    const PopupMenuItem(
                                      value: 'rename',
                                      child: Text('Đổi tên'),
                                    ),
                                    const PopupMenuItem(
                                      value: 'remove',
                                      child: Text('Gỡ khỏi quán'),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                            onTap: () => controller.selectMachine(id),
                          ),
                        );
                      },
                    ),
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () => _open(
                    context,
                    MachinePairingPage(
                      serverUrl: controller.api.serverUrl,
                      token: controller.api.token,
                    ),
                  ),
                  icon: const Icon(Icons.bluetooth),
                  label: const Text('Bluetooth'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: FilledButton.icon(
                  onPressed: () => _open(
                    context,
                    MachineQrPage(
                      serverUrl: controller.api.serverUrl,
                      token: controller.api.token,
                    ),
                  ),
                  icon: const Icon(Icons.qr_code_scanner),
                  label: const Text('Quét QR'),
                ),
              ),
            ],
          ),
          TextButton.icon(
            onPressed: () => _open(
              context,
              ShareBluetoothReceivePage(
                serverUrl: controller.api.serverUrl,
                token: controller.api.token,
              ),
            ),
            icon: const Icon(Icons.bluetooth_searching),
            label: const Text('Nhận chia sẻ qua Bluetooth'),
          ),
          TextButton.icon(
            onPressed: controller.checking ? null : () => _addById(context),
            icon: const Icon(Icons.keyboard_outlined),
            label: const Text('Nhập mã máy'),
          ),
        ],
      ),
    ),
  );
}

class _MachineIdDialog extends StatefulWidget {
  const _MachineIdDialog();

  @override
  State<_MachineIdDialog> createState() => _MachineIdDialogState();
}

class _MachineIdDialogState extends State<_MachineIdDialog> {
  final _input = TextEditingController();

  @override
  void dispose() {
    _input.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: const Text('Thêm máy'),
    content: TextField(
      controller: _input,
      autofocus: true,
      autocorrect: false,
      decoration: const InputDecoration(labelText: 'Mã máy'),
      onSubmitted: (_) => Navigator.pop(context, _input.text.trim()),
    ),
    actions: [
      TextButton(
        onPressed: () => Navigator.pop(context),
        child: const Text('Hủy'),
      ),
      FilledButton(
        onPressed: () => Navigator.pop(context, _input.text.trim()),
        child: const Text('Thêm'),
      ),
    ],
  );
}
