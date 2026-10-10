import 'package:flutter/material.dart';

import 'package:simple_app/feature/machine_menu/machine_menu_image.dart';
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
    listenable: Listenable.merge([products, products.images]),
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
                  leading: _DrinkImage(products.images, p),
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

// Ảnh món từ cache; chưa có hoặc lỗi đọc thì vẽ chữ cái đầu như trước.
class _DrinkImage extends StatelessWidget {
  const _DrinkImage(this.images, this.drink);
  final MenuImageCache images;
  final Drink drink;

  @override
  Widget build(BuildContext context) {
    final initials = InitialsTile(
      initialsOf(drink.name),
      background: drink.inStock ? AppColors.greenTint : AppColors.orangeTint,
      foreground: drink.inStock ? AppColors.green : AppColors.orangeText,
    );
    final file = images.fileOf(drink.id);
    if (file == null) return initials;
    return ClipRRect(
      borderRadius: BorderRadius.circular(10),
      child: Image.file(
        file,
        width: 40,
        height: 40,
        fit: BoxFit.cover,
        cacheWidth: 120,
        errorBuilder: (_, _, _) => initials,
      ),
    );
  }
}
