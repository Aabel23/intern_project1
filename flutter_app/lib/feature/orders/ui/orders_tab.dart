import 'package:flutter/material.dart';

import 'package:simple_app/feature/machines/data/machine_controller.dart';
import 'package:simple_app/feature/machines/ui/relay_view.dart';
import 'package:simple_app/feature/orders/data/qr_ticket.dart';
import 'package:simple_app/shared/cloud/cloud_error.dart';
import 'package:simple_app/shared/ui/app_theme.dart';
import 'package:simple_app/shared/ui/list_widgets.dart';

/// Vé QR thật từ MySQL máy. Mỗi vé là một món; không có dữ liệu thanh toán.
class OrdersTab extends StatefulWidget {
  const OrdersTab({super.key, required this.controller});
  final MachineController controller;

  @override
  State<OrdersTab> createState() => _OrdersTabState();
}

class _OrdersTabState extends State<OrdersTab> with RelayView {
  @override
  MachineController get controller => widget.controller;

  List<QrTicket> tickets = const [];
  int? nextBeforeSerial;
  bool loadingMore = false;
  String? pageError;

  @override
  void clearData() {
    tickets = const [];
    nextBeforeSerial = null;
    loadingMore = false;
    pageError = null;
  }

  @override
  Future<void> load(String selectedMachineId) async {
    final mine = generation;
    final answer = await controller.service.ask(
      selectedMachineId,
      'nhan_ve_qr',
      {'before_serial': null, 'limit': qrTicketPageSize},
    );
    if (!current(mine)) return;
    if (!answer.ok) throw CloudError(answer.errorCode ?? 'COMMAND_FAILED');
    final page = QrTicketPage.fromData(answer.data!);
    setState(() {
      tickets = page.tickets;
      nextBeforeSerial = page.nextBeforeSerial;
      pageError = null;
      loadingMore = false;
    });
  }

  Future<void> _loadMore() async {
    final id = machineId;
    final cursor = nextBeforeSerial;
    if (id == null || cursor == null || busy || loadingMore) return;
    final mine = generation;
    setState(() {
      loadingMore = true;
      pageError = null;
    });
    try {
      final answer = await controller.service.ask(id, 'nhan_ve_qr', {
        'before_serial': cursor,
        'limit': qrTicketPageSize,
      });
      if (!current(mine)) return;
      if (!answer.ok) throw CloudError(answer.errorCode ?? 'COMMAND_FAILED');
      final page = QrTicketPage.fromData(answer.data!);
      if (page.tickets.any((ticket) => ticket.serial >= cursor)) {
        throw const CloudError('INVALID_RESPONSE');
      }
      setState(() {
        tickets = [...tickets, ...page.tickets];
        nextBeforeSerial = page.nextBeforeSerial;
      });
    } on CloudError catch (e) {
      if (current(mine)) setState(() => pageError = e.code);
    } finally {
      if (current(mine)) setState(() => loadingMore = false);
    }
  }

  Future<void> _refresh() {
    setState(() {
      loadingMore = false;
      pageError = null;
    });
    return reload();
  }

  @override
  Widget build(BuildContext context) => RefreshIndicator(
    onRefresh: _refresh,
    child: ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
      children: [
        Row(
          children: [
            const Expanded(child: PageTitle('Vé QR')),
            IconButton(
              tooltip: 'Làm mới vé QR',
              onPressed: machineId == null || busy ? null : _refresh,
              icon: const Icon(Icons.refresh),
            ),
          ],
        ),
        const PageSubtitle('Mỗi vé ứng với một món trên máy đã chọn.'),
        const SizedBox(height: 14),
        if (machineId == null)
          const ListNotice('Chưa chọn máy ở tab Máy.')
        else ...[
          if (busy) const LinearProgressIndicator(),
          if (error != null) ListNotice(relayMessage(error!), error: true),
          if (!busy && error == null && tickets.isEmpty)
            const ListNotice('Máy chưa có vé QR nào.'),
          for (final ticket in tickets) _TicketCard(ticket),
          if (pageError != null)
            ListNotice(relayMessage(pageError!), error: true),
          if (loadingMore) const LinearProgressIndicator(),
          if (nextBeforeSerial != null && !loadingMore)
            Center(
              child: TextButton(
                onPressed: busy ? null : _loadMore,
                child: const Text('Xem thêm vé'),
              ),
            ),
        ],
      ],
    ),
  );
}

class _TicketCard extends StatelessWidget {
  const _TicketCard(this.ticket);
  final QrTicket ticket;

  @override
  Widget build(BuildContext context) {
    final status = switch (ticket.status) {
      QrTicketStatus.unused => const StatusPill('Chưa quét'),
      QrTicketStatus.inProgress => const StatusPill(
        'Đang pha',
        background: AppColors.orangeTint,
        foreground: AppColors.orangeText,
      ),
      QrTicketStatus.used => const StatusPill('Đã pha'),
      QrTicketStatus.expired => const StatusPill('Hết hạn'),
      QrTicketStatus.noqrErr => const StatusPill('Pha lỗi, không có QR'),
    };
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      'Vé #${ticket.serial}',
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  status,
                ],
              ),
              const SizedBox(height: 8),
              Text(
                ticket.drinkName ?? 'Tên món chưa được lưu',
                style: const TextStyle(fontSize: 13, color: AppColors.ink),
              ),
              const SizedBox(height: 4),
              Text(
                ticket.priceVnd == null
                    ? 'Giá trên vé chưa được lưu'
                    : 'Giá trên vé: ${ticket.priceVnd} đ',
                style: const TextStyle(fontSize: 13, color: AppColors.muted),
              ),
              const SizedBox(height: 4),
              Text(
                'Phát: ${ticket.createdAt.replaceFirst('T', ' ')} · giờ trên máy',
                style: const TextStyle(fontSize: 12, color: AppColors.muted),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
