import 'package:flutter/material.dart';

import 'package:simple_app/feature/machine_share/ui/machine_share_page.dart';
import 'package:simple_app/feature/machine_share/ui/machine_share_bluetooth_page.dart';
import 'package:simple_app/feature/machine_register/ui/machine_register_bluetooth_page.dart';
import 'package:simple_app/feature/dashboard/ui/machine_qr_page.dart';

import 'package:simple_app/shared/ui/app_theme.dart';
import 'package:simple_app/shared/ui/list_widgets.dart';

// Một máy để vẽ thẻ; chưa nối nguồn dữ liệu.
typedef MachineItem = ({String id, String name, bool online, String role});

// Danh sách máy của tài khoản; thêm máy bằng Bluetooth hoặc tem QR.
class MachinesTab extends StatelessWidget {
  const MachinesTab({super.key, this.machines = const [], this.selectedId});
  final List<MachineItem> machines;
  final String? selectedId;

  void _open(BuildContext context, Widget page) =>
      Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => page));

  void _onMenu(BuildContext context, MachineItem machine, String value) {
    if (value == 'rename') {
      showDialog<String>(
        context: context,
        builder: (_) => _RenameDialog(initial: machine.name),
      );
      return;
    }
    if (value == 'remove') {
      _remove(context, machine);
      return;
    }
    _open(
      context,
      DeviceSharePage(machineId: machine.id, machineName: machine.name),
    );
  }

  void _remove(BuildContext context, MachineItem machine) {
    final owner = machine.role == 'owner';
    final name = machine.name;
    showDialog<bool>(
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
  }

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.fromLTRB(20, 8, 20, 12),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const PageTitle('Máy FlexMix'),
        const PageSubtitle('Chọn máy để các tab nghiệp vụ hiển thị dữ liệu.'),
        const SizedBox(height: 12),
        Expanded(
          child: machines.isEmpty
              ? ListView(children: const [ListNotice('Quán chưa có máy nào.')])
              : ListView.separated(
                  itemCount: machines.length,
                  separatorBuilder: (_, _) => const SizedBox(height: 10),
                  itemBuilder: (_, index) {
                    final machine = machines[index];
                    final online = machine.online;
                    final selected = machine.id == selectedId;
                    final role = machine.role;
                    return Card(
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(16),
                        side: selected
                            ? const BorderSide(color: AppColors.green, width: 2)
                            : const BorderSide(color: AppColors.border),
                      ),
                      child: ListTile(
                        contentPadding: const EdgeInsets.fromLTRB(14, 6, 4, 6),
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
                            color: online ? AppColors.green : AppColors.subtle,
                          ),
                        ),
                        title: Text(
                          machine.name,
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
                            machine.id,
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
                                  _onMenu(context, machine, value),
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
                        onTap: () {},
                      ),
                    );
                  },
                ),
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: OutlinedButton.icon(
                onPressed: () => _open(context, const MachinePairingPage()),
                icon: const Icon(Icons.bluetooth),
                label: const Text('Bluetooth'),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: FilledButton.icon(
                onPressed: () => _open(context, const MachineQrPage()),
                icon: const Icon(Icons.qr_code_scanner),
                label: const Text('Quét QR'),
              ),
            ),
          ],
        ),
        TextButton.icon(
          onPressed: () => _open(context, const ShareBluetoothReceivePage()),
          icon: const Icon(Icons.bluetooth_searching),
          label: const Text('Nhận chia sẻ qua Bluetooth'),
        ),
      ],
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
