import 'package:flutter/material.dart';

import 'package:simple_app/feature/machines/data/machine_controller.dart';
import 'package:simple_app/feature/machines/ui/relay_view.dart';
import 'package:simple_app/shared/cloud/cloud_error.dart';
import 'package:simple_app/shared/ui/app_theme.dart';
import 'package:simple_app/shared/ui/list_widgets.dart';

// Một món để vẽ thẻ.
typedef Drink = ({
  int id,
  String name,
  num price,
  bool inStock,
  bool available,
});

Drink drinkFromRow(Map<String, Object?> row) => (
  id: row['drink_id'] as int,
  name: row['drink_name'] as String,
  price: row['price'] as num,
  inStock: row['in_stock'] == true || row['in_stock'] == 1,
  available: row['available'] == true || row['available'] == 1,
);

// Tab Sản phẩm: menu thật từ máy (nhan_menu), công tắc bật/tắt bán (cap_nhat_menu).
class ProductsTab extends StatefulWidget {
  const ProductsTab({super.key, required this.controller});
  final MachineController controller;

  @override
  State<ProductsTab> createState() => _ProductsTabState();
}

class _ProductsTabState extends State<ProductsTab> with RelayView {
  @override
  MachineController get controller => widget.controller;
  List<Drink> drinks = const [];
  int? menuVersion;

  @override
  void clearData() {
    drinks = const [];
    menuVersion = null;
  }

  void _apply(Map<String, dynamic> data) {
    final packet = data['packet'];
    if (data['menu_version'] is! int || packet is! String) {
      throw const CloudError('INVALID_RESPONSE');
    }
    menuVersion = data['menu_version'];
    drinks = decodeMenuPacket(packet).map(drinkFromRow).toList();
  }

  @override
  Future<void> load(String machineId) async {
    final mine = generation;
    // menu_version 0 không trùng bản nào nên máy luôn gửi gói đầy đủ.
    final answer = await controller.service.ask(machineId, 'nhan_menu', {
      'menu_version': 0,
    });
    if (!current(mine)) return;
    if (!answer.ok) throw CloudError(answer.errorCode ?? 'COMMAND_FAILED');
    setState(() => _apply(answer.data!));
  }

  Future<void> _toggle(Drink drink, bool value) async {
    final version = menuVersion;
    if (version == null) return;
    final mine = generation;
    final answer = await write('cap_nhat_menu', {
      'menu_version': version,
      'thay_doi': [
        {'drink_id': drink.id, 'available': value},
      ],
    });
    if (answer == null || !answer.ok || !current(mine)) return;
    setState(() => _apply(answer.data!));
    if (answer.data!['status'] == 'conflict' && mounted) {
      showMessage(
        context,
        'Menu trên máy vừa đổi; đã tải bản mới, hãy thử lại.',
      );
    }
  }

  @override
  Widget build(BuildContext context) => RefreshIndicator(
    onRefresh: reload,
    child: ListView(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
      children: [
        const PageTitle('Sản phẩm'),
        const SizedBox(height: 14),
        ?statusNotice(),
        if (statusNotice() == null && drinks.isEmpty)
          const ListNotice('Máy chưa có món nào.'),
        ...drinks.map(
          (p) => Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: Card(
              child: ListTile(
                contentPadding: const EdgeInsets.symmetric(
                  horizontal: 14,
                  vertical: 6,
                ),
                leading: InitialsTile(
                  initialsOf(p.name),
                  background: p.inStock
                      ? AppColors.greenTint
                      : AppColors.orangeTint,
                  foreground: p.inStock
                      ? AppColors.green
                      : AppColors.orangeText,
                ),
                title: Text(
                  p.name,
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: AppColors.ink,
                  ),
                ),
                subtitle: Text.rich(
                  TextSpan(
                    children: [
                      TextSpan(
                        text: money(p.price),
                        style: const TextStyle(
                          fontWeight: FontWeight.w700,
                          color: AppColors.green,
                        ),
                      ),
                      TextSpan(
                        text:
                            ' · '
                            '${p.inStock ? 'Còn nguyên liệu' : 'Thiếu nguyên liệu'}',
                      ),
                    ],
                  ),
                  style: const TextStyle(fontSize: 12, color: AppColors.muted),
                ),
                trailing: Switch(
                  value: p.available,
                  onChanged: busy ? null : (value) => _toggle(p, value),
                ),
              ),
            ),
          ),
        ),
      ],
    ),
  );
}
