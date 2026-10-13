import 'package:simple_app/shared/cloud/cloud_error.dart';

const qrTicketPageSize = 20;

enum QrTicketStatus { unused, inProgress, used, expired, noqrErr }

class QrTicket {
  const QrTicket({
    required this.serial,
    required this.drinkName,
    required this.priceVnd,
    required this.status,
    required this.createdAt,
    required this.scannedAt,
    required this.completedAt,
  });

  final int serial;
  final String? drinkName;
  final String? priceVnd;
  final QrTicketStatus status;
  final String createdAt;
  final String? scannedAt;
  final String? completedAt;

  static final _pricePattern = RegExp(r'^\d{1,8}\.\d{2}$');
  static final _machineTimePattern = RegExp(
    r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?$',
  );

  static QrTicket fromMap(Map<String, dynamic> row) {
    final serial = row['serial'];
    final name = row['drink_name'];
    final price = row['price_vnd'];
    final status = row['status'];
    final created = row['created_at'];
    final scanned = row['scanned_at'];
    final completed = row['completed_at'];
    if (serial is! int ||
        serial <= 0 ||
        (name != null && name is! String) ||
        (price != null &&
            (price is! String || !_pricePattern.hasMatch(price))) ||
        created is! String ||
        !_machineTimePattern.hasMatch(created) ||
        (scanned != null &&
            (scanned is! String || !_machineTimePattern.hasMatch(scanned))) ||
        (completed != null &&
            (completed is! String ||
                !_machineTimePattern.hasMatch(completed)))) {
      throw const CloudError('INVALID_RESPONSE');
    }
    final parsedStatus = switch (status) {
      'unused' => QrTicketStatus.unused,
      'in_progress' => QrTicketStatus.inProgress,
      'used' => QrTicketStatus.used,
      'expired' => QrTicketStatus.expired,
      'noqr_err' => QrTicketStatus.noqrErr,
      _ => null,
    };
    if (parsedStatus == null) throw const CloudError('INVALID_RESPONSE');
    return QrTicket(
      serial: serial,
      drinkName: name,
      priceVnd: price,
      status: parsedStatus,
      createdAt: created,
      scannedAt: scanned,
      completedAt: completed,
    );
  }
}

class QrTicketPage {
  const QrTicketPage(this.tickets, this.nextBeforeSerial);

  final List<QrTicket> tickets;
  final int? nextBeforeSerial;

  static QrTicketPage fromData(Map<String, dynamic> data) {
    final rows = data['tickets'];
    final next = data['next_before_serial'];
    if (rows is! List ||
        rows.length > qrTicketPageSize ||
        (next != null && (next is! int || next <= 0))) {
      throw const CloudError('INVALID_RESPONSE');
    }
    final tickets = <QrTicket>[];
    for (final row in rows) {
      if (row is! Map || row.keys.any((key) => key is! String)) {
        throw const CloudError('INVALID_RESPONSE');
      }
      final ticket = QrTicket.fromMap(Map<String, dynamic>.from(row));
      if (tickets.isNotEmpty && ticket.serial >= tickets.last.serial) {
        throw const CloudError('INVALID_RESPONSE');
      }
      tickets.add(ticket);
    }
    if (next != null &&
        (tickets.length != qrTicketPageSize || next != tickets.last.serial)) {
      throw const CloudError('INVALID_RESPONSE');
    }
    return QrTicketPage(tickets, next);
  }
}
