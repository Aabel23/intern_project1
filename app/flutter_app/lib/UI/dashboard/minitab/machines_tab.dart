import 'package:flutter/material.dart';

import '../../../feature/machine_share/machine_share.dart';
import '../../../feature/machine_share/machine_share_bluetooth.dart';
import '../../../feature/machine_register/machine_register_bluetooth.dart';
import '../../../feature/machine_register/machine_register_qr.dart';

import '../../app_theme.dart';
import '../dashboard/dashboard_controller.dart';
import '../machine_api.dart';
import '../dashboard/dashboard_widgets.dart';

// Danh sách máy của tài khoản; thêm máy bằng Bluetooth hoặc tem QR.
class MachinesTab extends StatelessWidget {
  const MachinesTab({super.key, required this.controller});
  final DashboardController controller;

  // Sau khi đăng ký hoặc nhận chia sẻ, đọc lại danh sách máy của tài khoản.
  Future<void> _open(BuildContext context, Widget page) async {
    await Navigator.of(context)
        .push(MaterialPageRoute<void>(builder: (_) => page));
    await controller.loadMyMachines();
  }

  void _onMenu(BuildContext context, String id, String value) {
    if (value == 'rename') {
      _rename(context, id);
      return;
    }
    if (value == 'remove') {
      _remove(context, id);
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

  Future<void> _rename(BuildContext context, String id) async {
    final name = await showDialog<String>(
      context: context,
      builder: (_) => _RenameDialog(initial: controller.names[id] ?? ''),
    );
    if (name == null || name.isEmpty || !context.mounted) return;
    try {
      await controller.api.renameMachine(id, name);
      await controller.loadMyMachines();
    } on MachineException catch (error) {
      if (context.mounted) showMessage(context, error.message);
    }
  }

  Future<void> _remove(BuildContext context, String id) async {
    final owner = controller.roles[id] == 'owner';
    final name = controller.names[id] ?? id;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(owner ? 'Gỡ máy khỏi quán?' : 'Bỏ quản lý máy?'),
        content: Text(
          owner
              ? '$name sẽ bị xóa khỏi tài khoản của bạn và của mọi nhân viên. '
                    'Muốn dùng lại phải thêm máy bằng tem QR hoặc Bluetooth.'
              : 'Bạn sẽ không quản lý $name nữa cho tới khi chủ máy chia sẻ lại.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Hủy'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: Text(owner ? 'Gỡ máy' : 'Bỏ quản lý'),
          ),
        ],
      ),
    );
    if (confirmed != true || !context.mounted) return;
    try {
      await controller.api.removeMachine(id);
      await controller.forgetMachine(id);
    } on MachineException catch (error) {
      if (context.mounted) showMessage(context, error.message);
    }
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(
    listenable: controller,
    builder: (context, _) => Padding(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const PageTitle('Máy FlexMix'),
          const PageSubtitle('Chọn máy để các tab nghiệp vụ hiển thị dữ liệu.'),
          if (controller.machinesError != null)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Text(
                controller.machinesError!,
                style: const TextStyle(
                  color: AppColors.orangeText,
                  fontSize: 13,
                ),
              ),
            ),
          if (controller.checking)
            const Padding(
              padding: EdgeInsets.only(top: 12),
              child: LinearProgressIndicator(),
            ),
          const SizedBox(height: 12),
          Expanded(
            child: RefreshIndicator(
              // Đọc lại danh sách máy (máy mới được giao, máy bị thu hồi) và trạng thái.
              onRefresh: controller.loadMyMachines,
              child: controller.machines.isEmpty
                  ? ListView(
                      children: const [ListNotice('Quán chưa có máy nào.')],
                    )
                  : ListView.separated(
                      itemCount: controller.machines.length,
                      separatorBuilder: (_, _) => const SizedBox(height: 10),
                      itemBuilder: (_, index) {
                        final id = controller.machines[index];
                        final online = controller.online[id] == true;
                        final selected = id == controller.machineId;
                        final role = controller.roles[id];
                        return Card(
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(16),
                            side: selected
                                ? const BorderSide(
                                    color: AppColors.green,
                                    width: 2,
                                  )
                                : const BorderSide(color: AppColors.border),
                          ),
                          child: ListTile(
                            contentPadding: const EdgeInsets.fromLTRB(
                              14,
                              6,
                              4,
                              6,
                            ),
                            leading: Container(
                              width: 40,
                              height: 40,
                              decoration: BoxDecoration(
                                color: online
                                    ? AppColors.greenTint
                                    : AppColors.segment,
                                borderRadius: BorderRadius.circular(10),
                              ),
                              child: Icon(
                                online ? Icons.cloud_done : Icons.cloud_off,
                                size: 20,
                                color: online
                                    ? AppColors.green
                                    : AppColors.subtle,
                              ),
                            ),
                            title: Text(
                              controller.names[id] ?? id,
                              style: const TextStyle(
                                fontSize: 14,
                                fontWeight: FontWeight.w600,
                                color: AppColors.ink,
                              ),
                            ),
                            subtitle: Text(
                              [
                                online ? 'Online' : 'Offline',
                                if (role == 'owner') 'Chủ máy',
                                if (role == 'manager') 'Được giao',
                                id,
                              ].join(' · '),
                              style: const TextStyle(
                                fontSize: 12,
                                color: AppColors.muted,
                              ),
                            ),
                            selected: selected,
                            trailing: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                if (selected)
                                  const Icon(
                                    Icons.check_circle,
                                    color: AppColors.green,
                                  ),
                                PopupMenuButton<String>(
                                  onSelected: (value) =>
                                      _onMenu(context, id, value),
                                  itemBuilder: (_) => [
                                    if (role == 'owner')
                                      const PopupMenuItem(
                                        value: 'share',
                                        child: Text('Chia sẻ cho nhân viên'),
                                      ),
                                    if (role == 'owner')
                                      const PopupMenuItem(
                                        value: 'rename',
                                        child: Text('Đổi tên'),
                                      ),
                                    PopupMenuItem(
                                      value: 'remove',
                                      child: Text(
                                        role == 'owner'
                                            ? 'Gỡ khỏi quán'
                                            : 'Bỏ quản lý máy',
                                      ),
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
        ],
      ),
    ),
  );
}

// Hộp thoại đổi tên, điền sẵn tên hiện tại của máy.
class _RenameDialog extends StatefulWidget {
  const _RenameDialog({required this.initial});
  final String initial;

  @override
  State<_RenameDialog> createState() => _RenameDialogState();
}

class _RenameDialogState extends State<_RenameDialog> {
  late final _input = TextEditingController(text: widget.initial);

  @override
  void dispose() {
    _input.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: const Text('Đổi tên máy'),
    content: TextField(
      controller: _input,
      autofocus: true,
      decoration: const InputDecoration(labelText: 'Tên máy'),
      onSubmitted: (_) => Navigator.pop(context, _input.text.trim()),
    ),
    actions: [
      TextButton(
        onPressed: () => Navigator.pop(context),
        child: const Text('Hủy'),
      ),
      FilledButton(
        onPressed: () => Navigator.pop(context, _input.text.trim()),
        child: const Text('Lưu'),
      ),
    ],
  );
}
