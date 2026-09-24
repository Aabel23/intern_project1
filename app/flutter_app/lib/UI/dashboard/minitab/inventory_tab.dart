import 'package:flutter/material.dart';

import '../../../feature/data_sync/ingredients_sync.dart';
import '../dashboard/dashboard_widgets.dart';

// Tab Kho: đồng bộ nguyên liệu từ máy. Lệnh nạp kho là tính năng riêng chưa làm,
// nên nút "Nạp đầy"/"Nạp tất cả" chỉ giữ giao diện.
class InventoryTab extends StatelessWidget {
  const InventoryTab({super.key, required this.inventory});
  final IngredientsSync inventory;

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: Colors.transparent,
    floatingActionButton: FloatingActionButton.extended(
      heroTag: 'refill-all',
      onPressed: () => notAvailableYet(context),
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
                              onPressed: () => notAvailableYet(context),
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
