import 'package:flutter/material.dart';

import 'package:simple_app/shared/ui/app_theme.dart';
import 'package:simple_app/shared/ui/list_widgets.dart';

// Một món để vẽ thẻ; chưa nối nguồn dữ liệu.
typedef Drink = ({String name, int price, bool inStock, bool available});

// Tab Sản phẩm: danh sách món, công tắc bật/tắt bán.
class ProductsTab extends StatelessWidget {
  const ProductsTab({super.key, this.drinks = const []});
  final List<Drink> drinks;

  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
    children: [
      const PageTitle('Sản phẩm'),
      const SizedBox(height: 14),
      if (drinks.isEmpty) const ListNotice('Máy chưa có món nào.'),
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
                foreground: p.inStock ? AppColors.green : AppColors.orangeText,
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
              trailing: Switch(value: p.available, onChanged: (_) {}),
            ),
          ),
        ),
      ),
    ],
  );
}
