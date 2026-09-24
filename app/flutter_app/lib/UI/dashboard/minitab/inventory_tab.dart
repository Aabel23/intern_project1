import 'package:flutter/material.dart';

import '../dashboard/dashboard_controller.dart';
import '../dashboard/dashboard_widgets.dart';

// Tab Kho: đọc nguyên liệu từ máy. Server chưa có mức tối đa và lệnh nạp đầy,
// nên nút "Nạp đầy"/"Nạp tất cả" chỉ giữ giao diện.
class InventoryTab extends StatelessWidget {
  const InventoryTab({super.key, required this.controller});
  final DashboardController controller;

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
      listenable: controller,
      builder: (_, _) => RefreshIndicator(
        onRefresh: controller.loadIngredients,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
          children: [
            const PageTitle('Kho nguyên liệu'),
            const SizedBox(height: 4),
            const Text(
              'Kéo xuống để lấy trạng thái mới nhất từ máy FlexMix.',
              style: TextStyle(color: Colors.black54),
            ),
            if (controller.loadingIngredients)
              const Padding(
                padding: EdgeInsets.only(top: 12),
                child: LinearProgressIndicator(),
              ),
            const SizedBox(height: 16),
            if (controller.ingredientError != null)
              ListNotice(controller.ingredientError!, error: true)
            else if (controller.ingredients.isEmpty &&
                !controller.loadingIngredients)
              const ListNotice('Máy chưa có nguyên liệu nào.'),
            for (final ingredient in controller.ingredients)
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          ingredient.name,
                          style: const TextStyle(
                            fontWeight: FontWeight.w800,
                            fontSize: 16,
                          ),
                        ),
                        const SizedBox(height: 10),
                        // Chưa có mức tối đa nên thanh chỉ thể hiện còn/hết hàng.
                        LinearProgressIndicator(
                          value: ingredient.inStock ? 1 : 0,
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
                                '${ingredient.amount.toStringAsFixed(0)} g · '
                                '${ingredient.inStock ? 'Còn hàng' : 'Hết hàng'}',
                              ),
                            ),
                            TextButton(
                              onPressed: () => notAvailableYet(context),
                              child: const Text('Nạp đầy'),
                            ),
                          ],
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
