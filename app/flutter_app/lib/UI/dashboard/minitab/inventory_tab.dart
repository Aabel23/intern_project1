import 'package:flutter/material.dart';

import '../../../feature/data_sync/ingredients_sync.dart';
import '../dashboard/dashboard_widgets.dart';

// Tab Kho: đồng bộ nguyên liệu từ máy; "Nạp đầy"/"Nạp tất cả" gửi lệnh /machine/refill.
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
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
          children: [
            const PageTitle('Kho nguyên liệu'),
            const SizedBox(height: 4),
            const Text(
              'Kéo xuống để lấy trạng thái mới nhất từ máy FlexMix.',
              style: TextStyle(color: Colors.black54),
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
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                ingredient.name,
                                style: const TextStyle(
                                  fontWeight: FontWeight.w800,
                                  fontSize: 16,
                                ),
                              ),
                            ),
                            if (ingredient.pumpNumber != null)
                              Chip(label: Text('Bơm ${ingredient.pumpNumber}')),
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
                              ? Colors.green
                              : Colors.deepOrange,
                          minHeight: 9,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                '${ingredient.amount.toStringAsFixed(0)} / '
                                '${ingredient.maxGram.toStringAsFixed(0)} g',
                              ),
                            ),
                            TextButton(
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
                              color: Colors.deepOrange,
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
