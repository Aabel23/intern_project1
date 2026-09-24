import 'package:flutter/material.dart';

import '../dashboard/dashboard_controller.dart';
import '../dashboard/dashboard_widgets.dart';

// Tab Sản phẩm: danh sách món từ máy, công tắc bật/tắt bán.
class ProductsTab extends StatelessWidget {
  const ProductsTab({super.key, required this.controller});
  final DashboardController controller;

  Future<void> _toggle(BuildContext context, Drink drink, bool value) async {
    try {
      await controller.setDrinkAvailable(drink, value);
    } catch (error) {
      if (context.mounted) showMessage(context, 'Không lưu được: $error');
    }
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(
    listenable: controller,
    builder: (context, _) => RefreshIndicator(
      onRefresh: controller.loadMenu,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const PageTitle('Sản phẩm'),
          if (controller.loadingMenu)
            const Padding(
              padding: EdgeInsets.only(top: 12),
              child: LinearProgressIndicator(),
            ),
          const SizedBox(height: 14),
          if (controller.menuError != null)
            ListNotice(controller.menuError!, error: true)
          else if (controller.drinks.isEmpty && !controller.loadingMenu)
            const ListNotice('Máy chưa có món nào.'),
          ...controller.drinks.map(
            (p) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Card(
                child: ListTile(
                  contentPadding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 8,
                  ),
                  leading: CircleAvatar(
                    child: Text(p.name.isEmpty ? '?' : p.name[0]),
                  ),
                  title: Text(
                    p.name,
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                  subtitle: Text(
                    '${money(p.price)} · '
                    '${p.inStock ? 'Còn nguyên liệu' : 'Thiếu nguyên liệu'}',
                  ),
                  trailing: Switch(
                    value: p.available,
                    onChanged: (v) => _toggle(context, p, v),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    ),
  );
}
