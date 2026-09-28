// DỮ LIỆU GIẢ để xem giao diện tab Đơn hàng. Server chưa có lệnh đọc đơn hàng.
// Tắt: đặt kShowDemoOrders = false (hoặc xóa file này khi có API thật).
const bool kShowDemoOrders = true;

enum DemoOrderStatus { done, waiting, cancelled }

class DemoOrder {
  const DemoOrder(
    this.code,
    this.time,
    this.drink,
    this.cups,
    this.payment,
    this.total,
    this.status,
  );
  final String code, time, drink, payment;
  final int cups, total;
  final DemoOrderStatus status;
}

const demoOrders = <DemoOrder>[
  DemoOrder(
    '#FM-0132',
    '10:42',
    'Cà phê sữa đá',
    2,
    'Tiền mặt',
    50000,
    DemoOrderStatus.done,
  ),
  DemoOrder(
    '#FM-0131',
    '10:35',
    'Bạc xỉu',
    1,
    'QR',
    28000,
    DemoOrderStatus.waiting,
  ),
  DemoOrder(
    '#FM-0130',
    '10:15',
    'Trà đào cam sả',
    3,
    'QR',
    105000,
    DemoOrderStatus.done,
  ),
  DemoOrder(
    '#FM-0129',
    '09:58',
    'Cà phê đen đá',
    1,
    'Thẻ',
    22000,
    DemoOrderStatus.done,
  ),
  DemoOrder(
    '#FM-0128',
    '09:31',
    'Matcha latte',
    1,
    'Tiền mặt',
    39000,
    DemoOrderStatus.cancelled,
  ),
  DemoOrder(
    '#FM-0127',
    '09:12',
    'Cacao sữa',
    2,
    'QR',
    64000,
    DemoOrderStatus.done,
  ),
  DemoOrder(
    '#FM-0126',
    '08:47',
    'Cà phê sữa đá',
    4,
    'Tiền mặt',
    100000,
    DemoOrderStatus.done,
  ),
  DemoOrder(
    '#FM-0125',
    '08:20',
    'Trà chanh',
    2,
    'QR',
    40000,
    DemoOrderStatus.waiting,
  ),
];
