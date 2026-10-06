import 'package:flutter/material.dart';

import 'package:simple_app/shared/ui/app_theme.dart';
import 'package:simple_app/shared/ui/list_widgets.dart';
import 'package:simple_app/feature/orders/demo_orders.dart';

// Tab Đơn hàng: server chưa có lệnh đọc đơn hàng. Khi kShowDemoOrders bật,
// hiện dữ liệu giả (demo_orders.dart) để xem giao diện.
class OrdersTab extends StatefulWidget {
  const OrdersTab({super.key});

  @override
  State<OrdersTab> createState() => _OrdersTabState();
}

class _OrdersTabState extends State<OrdersTab> {
  DemoOrderStatus? _filter;

  @override
  Widget build(BuildContext context) {
    if (!kShowDemoOrders) {
      return ListView(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
        children: const [
          PageTitle('Đơn hàng'),
          SizedBox(height: 16),
          ListNotice('Chưa có dữ liệu đơn hàng.'),
        ],
      );
    }
    int count(DemoOrderStatus s) =>
        demoOrders.where((o) => o.status == s).length;
    final shown = _filter == null
        ? demoOrders
        : demoOrders.where((o) => o.status == _filter).toList();
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
      children: [
        const PageTitle('Đơn hàng'),
        PageSubtitle('Dữ liệu mẫu · ${demoOrders.length} đơn'),
        const SizedBox(height: 14),
        Container(
          padding: const EdgeInsets.all(4),
          decoration: BoxDecoration(
            color: AppColors.segment,
            borderRadius: BorderRadius.circular(14),
          ),
          child: Row(
            children: [
              _segment('Tất cả ${demoOrders.length}', null),
              _segment(
                'Chờ ${count(DemoOrderStatus.waiting)}',
                DemoOrderStatus.waiting,
              ),
              _segment(
                'Xong ${count(DemoOrderStatus.done)}',
                DemoOrderStatus.done,
              ),
              _segment(
                'Huỷ ${count(DemoOrderStatus.cancelled)}',
                DemoOrderStatus.cancelled,
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        for (final order in shown)
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: _OrderCard(order),
          ),
      ],
    );
  }

  Widget _segment(String label, DemoOrderStatus? value) {
    final active = _filter == value;
    return Expanded(
      child: GestureDetector(
        onTap: () => setState(() => _filter = value),
        child: Container(
          height: 38,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: active ? Colors.white : Colors.transparent,
            borderRadius: BorderRadius.circular(10),
            boxShadow: active
                ? const [
                    BoxShadow(
                      color: Color(0x1F1C2420),
                      blurRadius: 3,
                      offset: Offset(0, 1),
                    ),
                  ]
                : null,
          ),
          child: Text(
            label,
            style: TextStyle(
              fontSize: 12,
              fontWeight: active ? FontWeight.w700 : FontWeight.w500,
              color: active ? AppColors.ink : const Color(0xFF4A524D),
            ),
          ),
        ),
      ),
    );
  }
}

class _OrderCard extends StatelessWidget {
  const _OrderCard(this.order);
  final DemoOrder order;

  @override
  Widget build(BuildContext context) {
    final cancelled = order.status == DemoOrderStatus.cancelled;
    final pill = switch (order.status) {
      DemoOrderStatus.done => const StatusPill('Hoàn thành'),
      DemoOrderStatus.waiting => const StatusPill(
        'Chờ pha',
        background: AppColors.orangeTint,
        foreground: AppColors.orangeText,
      ),
      DemoOrderStatus.cancelled => const StatusPill(
        'Đã huỷ',
        background: Color(0xFFEEEAE3),
        foreground: Color(0xFF4A524D),
      ),
    };
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    order.code,
                    style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                pill,
              ],
            ),
            const SizedBox(height: 8),
            Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Expanded(
                  child: Text(
                    '${order.time} · ${order.drink} · ${order.cups} ly · '
                    '${order.payment}',
                    style: const TextStyle(
                      fontSize: 12,
                      color: AppColors.muted,
                    ),
                  ),
                ),
                Text(
                  money(order.total),
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                    color: cancelled ? AppColors.subtle : AppColors.ink,
                    decoration: cancelled ? TextDecoration.lineThrough : null,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
