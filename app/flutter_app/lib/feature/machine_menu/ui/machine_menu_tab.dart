import 'package:flutter/material.dart';

import 'package:simple_app/feature/machine_menu/machine_menu_sync.dart';
import 'package:simple_app/shared/ui/app_theme.dart';
import 'package:simple_app/shared/ui/list_widgets.dart';

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
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
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
                    style: const TextStyle(
                      fontSize: 12,
                      color: AppColors.muted,
                    ),
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
