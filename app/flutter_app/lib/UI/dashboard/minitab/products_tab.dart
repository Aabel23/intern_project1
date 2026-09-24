import 'package:flutter/material.dart';

import '../../../feature/data_sync/products_sync.dart';
import '../dashboard/dashboard_widgets.dart';

// Tab Sản phẩm: danh sách món từ máy, công tắc bật/tắt bán.
class ProductsTab extends StatelessWidget {
  const ProductsTab({super.key, required this.products});
  final ProductsSync products;

  Future<void> _toggle(BuildContext context, Drink drink, bool value) async {
    try {
      await products.setAvailable(drink, value);
    } catch (error) {
      if (context.mounted) showMessage(context, 'Không lưu được: $error');
    }
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(
    listenable: products,
    builder: (context, _) => RefreshIndicator(
      onRefresh: products.load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const PageTitle('Sản phẩm'),
          if (products.loading)
            const Padding(
              padding: EdgeInsets.only(top: 12),
              child: LinearProgressIndicator(),
            ),
          const SizedBox(height: 14),
          if (products.error != null)
            ListNotice(products.error!, error: true)
          else if (products.drinks.isEmpty && !products.loading)
            const ListNotice('Máy chưa có món nào.'),
          ...products.drinks.map(
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
