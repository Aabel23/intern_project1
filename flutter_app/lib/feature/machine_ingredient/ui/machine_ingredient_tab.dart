import 'package:flutter/material.dart';

import 'package:simple_app/feature/machines/data/machine_controller.dart';
import 'package:simple_app/feature/machines/ui/relay_view.dart';
import 'package:simple_app/shared/cloud/cloud_error.dart';
import 'package:simple_app/shared/ui/app_theme.dart';
import 'package:simple_app/shared/ui/list_widgets.dart';

// Một nguyên liệu để vẽ thẻ.
typedef Ingredient = ({
  int id,
  String name,
  int? pumpNumber,
  double amount,
  double maxGram,
  bool inStock,
  bool maxSet,
});

Ingredient ingredientFromMap(Map<String, dynamic> m) => (
  id: m['ingredient_id'] as int,
  name: m['name'] as String,
  pumpNumber: m['pump_no'] as int?,
  amount: (m['amount'] as num).toDouble(),
  maxGram: (m['max_gram'] as num).toDouble(),
  inStock: m['in_stock'] == true,
  maxSet: m['max_set'] == true,
);

// Tab Kho: mức nguyên liệu thật từ máy (nhan_kho), nút "Nạp đầy"/"Nạp tất cả" (nap_kho).
class InventoryTab extends StatefulWidget {
  const InventoryTab({super.key, required this.controller});
  final MachineController controller;

  @override
  State<InventoryTab> createState() => _InventoryTabState();
}

class _InventoryTabState extends State<InventoryTab> with RelayView {
  @override
  MachineController get controller => widget.controller;
  List<Ingredient> ingredients = const [];

  @override
  void clearData() => ingredients = const [];

  @override
  Future<void> load(String machineId) async {
    final mine = generation;
    // version 0 không trùng CRC nào nên máy luôn gửi danh sách đầy đủ.
    final answer = await controller.service.ask(machineId, 'nhan_kho', {
      'version': 0,
    });
    if (!current(mine)) return;
    if (!answer.ok) throw CloudError(answer.errorCode ?? 'COMMAND_FAILED');
    final list = answer.data!['ingredients'];
    if (list is! List) throw const CloudError('INVALID_RESPONSE');
    setState(
      () => ingredients = [
        for (final m in list) ingredientFromMap(Map<String, dynamic>.from(m)),
      ],
    );
  }

  Future<void> _refill(BuildContext context, String what, Object target) async {
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
    if (ok != true || !context.mounted) return;
    final answer = await write('nap_kho', {'target': target, 'value': 'full'});
    if (answer != null && answer.ok) await reload();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: Colors.transparent,
    floatingActionButton: FloatingActionButton.extended(
      heroTag: 'refill-all',
      onPressed: busy || machineId == null
          ? null
          : () => _refill(context, 'tất cả nguyên liệu', 'all'),
      icon: const Icon(Icons.local_shipping_outlined),
      label: const Text('Nạp tất cả'),
    ),
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 96),
      children: [
        const PageTitle('Kho nguyên liệu'),
        const PageSubtitle('Mức nguyên liệu trong máy FlexMix.'),
        const SizedBox(height: 16),
        ?statusNotice(),
        if (statusNotice() == null && ingredients.isEmpty)
          const ListNotice('Máy chưa có nguyên liệu nào.'),
        for (final ingredient in ingredients)
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
                            padding: const EdgeInsets.symmetric(horizontal: 12),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(10),
                            ),
                            textStyle: const TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          onPressed: busy
                              ? null
                              : () => _refill(
                                  context,
                                  ingredient.name,
                                  ingredient.id,
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
  );
}
