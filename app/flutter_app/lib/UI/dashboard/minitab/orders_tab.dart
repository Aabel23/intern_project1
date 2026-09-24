import 'package:flutter/material.dart';

import '../dashboard/dashboard_widgets.dart';

// Tab Đơn hàng: server chưa có lệnh đọc đơn hàng, chỉ giữ giao diện.
class OrdersTab extends StatelessWidget {
  const OrdersTab({super.key});

  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.all(16),
    children: const [
      PageTitle('Đơn hàng'),
      SizedBox(height: 16),
      ListNotice('Chưa có dữ liệu đơn hàng.'),
    ],
  );
}
