import 'package:flutter/material.dart';

import '../dashboard/dashboard_controller.dart';
import '../dashboard/dashboard_widgets.dart';

// Tab Tổng quan. Doanh thu/đơn hàng chưa có trên server nên chỉ giữ ô hiển thị.
class OverviewTab extends StatelessWidget {
  const OverviewTab({super.key, required this.controller});
  final DashboardController controller;

  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();
    return ListenableBuilder(
      listenable: Listenable.merge([controller, controller.inventory]),
      builder: (context, _) {
        final empty = controller.inventory.ingredients
            .where((i) => !i.inStock)
            .length;
        return ListView(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 28),
          children: [
            Row(
              children: [
                const Expanded(child: PageTitle('Hôm nay')),
                Chip(
                  avatar: const Icon(Icons.calendar_today_outlined, size: 16),
                  label: Text(
                    '${twoDigits(now.day)}/${twoDigits(now.month)}/${now.year}',
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            const Row(
              children: [
                Expanded(
                  child: _Metric(
                    'Doanh thu',
                    '—',
                    'Chưa có dữ liệu',
                    Icons.payments_outlined,
                  ),
                ),
                SizedBox(width: 12),
                Expanded(
                  child: _Metric(
                    'Đơn hàng',
                    '—',
                    'Chưa có dữ liệu',
                    Icons.shopping_bag_outlined,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                const Expanded(
                  child: _Metric(
                    'Giá trị TB',
                    '—',
                    'Chưa có dữ liệu',
                    Icons.trending_up,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _Metric(
                    'Sắp hết',
                    '$empty',
                    empty > 0 ? 'Cần xử lý' : 'Ổn định',
                    Icons.inventory_2_outlined,
                    warning: empty > 0,
                  ),
                ),
              ],
            ),
          ],
        );
      },
    );
  }
}

class _Metric extends StatelessWidget {
  const _Metric(
    this.title,
    this.value,
    this.note,
    this.icon, {
    this.warning = false,
  });
  final String title, value, note;
  final IconData icon;
  final bool warning;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: Theme.of(context).colorScheme.primary),
          const SizedBox(height: 12),
          Text(
            title,
            style: const TextStyle(color: Colors.black54, fontSize: 12),
          ),
          FittedBox(
            child: Text(
              value,
              style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 21),
            ),
          ),
          Text(
            note,
            style: TextStyle(
              color: warning ? Colors.deepOrange : Colors.green.shade700,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    ),
  );
}
