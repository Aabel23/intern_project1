import 'package:flutter/material.dart';

import 'package:simple_app/feature/machine_ingredient/machine_ingredient_sync.dart';
import 'package:simple_app/shared/ui/app_theme.dart';
import 'package:simple_app/shared/ui/list_widgets.dart';

// Tab Kho: đồng bộ nguyên liệu từ máy; "Nạp đầy"/"Nạp tất cả" gửi /app/nap-kho.
class InventoryTab extends StatelessWidget {
  const InventoryTab({super.key, required this.inventory});
  final IngredientsSync inventory;

  Future<void> _refill(BuildContext context, Object target, String what) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Nạp kho'),
        content: Text('Đổ đầy $what tới mức tối đa?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Hủy'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Nạp'),
          ),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await inventory.refill(target);
      if (context.mounted) showMessage(context, 'Đã nạp $what.');
    } catch (error) {
      if (context.mounted) showMessage(context, 'Không nạp được: $error');
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: Colors.transparent,
    floatingActionButton: FloatingActionButton.extended(
      heroTag: 'refill-all',
      onPressed: () => _refill(context, 'all', 'tất cả nguyên liệu'),
      icon: const Icon(Icons.local_shipping_outlined),
      label: const Text('Nạp tất cả'),
    ),
    body: ListenableBuilder(
      listenable: inventory,
      builder: (_, _) => RefreshIndicator(
        onRefresh: inventory.load,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 96),
          children: [
            const PageTitle('Kho nguyên liệu'),
            const PageSubtitle(
              'Kéo xuống để lấy trạng thái mới nhất từ máy FlexMix.',
            ),
            if (inventory.loading)
              const Padding(
                padding: EdgeInsets.only(top: 12),
                child: LinearProgressIndicator(),
              ),
            const SizedBox(height: 16),
            if (inventory.error != null)
              ListNotice(inventory.error!, error: true)
            else if (inventory.ingredients.isEmpty && !inventory.loading)
              const ListNotice('Máy chưa có nguyên liệu nào.'),
            for (final ingredient in inventory.ingredients)
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Card(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(14, 12, 14, 10),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            InitialsTile(
                              initialsOf(ingredient.name),
                              background: ingredient.inStock
                                  ? AppColors.greenTint
                                  : AppColors.orangeTint,
                              foreground: ingredient.inStock
                                  ? AppColors.green
                                  : AppColors.orangeText,
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Text(
                                ingredient.name,
                                style: const TextStyle(
                                  fontWeight: FontWeight.w600,
                                  fontSize: 14,
                                  color: AppColors.ink,
                                ),
                              ),
                            ),
                            if (ingredient.pumpNumber != null)
                              StatusPill(
                                'Bơm ${ingredient.pumpNumber}',
                                background: AppColors.segment,
                                foreground: AppColors.ink,
                              ),
                          ],
                        ),
                        const SizedBox(height: 10),
                        LinearProgressIndicator(
                          value: ingredient.maxGram <= 0
                              ? 0
                              : (ingredient.amount / ingredient.maxGram).clamp(
                                  0,
                                  1,
                                ),
                          color: ingredient.inStock
                              ? AppColors.green
                              : AppColors.orange,
                          minHeight: 8,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                '${ingredient.amount.toStringAsFixed(0)} / '
                                '${ingredient.maxGram.toStringAsFixed(0)} g',
                                style: const TextStyle(
                                  fontSize: 12,
                                  color: AppColors.muted,
                                ),
                              ),
                            ),
                            OutlinedButton(
                              style: OutlinedButton.styleFrom(
                                minimumSize: const Size(44, 36),
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 12,
                                ),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(10),
                                ),
                                textStyle: const TextStyle(
                                  fontSize: 13,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              onPressed: () => _refill(
                                context,
                                ingredient.id,
                                ingredient.name,
                              ),
                              child: const Text('Nạp đầy'),
                            ),
                          ],
                        ),
                        if (!ingredient.maxSet)
                          const Text(
                            'Mức tối đa đang dùng giá trị mặc định.',
                            style: TextStyle(
                              color: AppColors.orangeText,
                              fontSize: 12,
                            ),
                          ),
                      ],
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    ),
  );
}
