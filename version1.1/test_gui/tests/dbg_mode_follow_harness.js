// Harness cho test_dbg_mode_follow.py (DBG-01, DBG-02).
//
// VÌ SAO CẮT MÃ THẬT RA CHẠY TRONG node
//   Logic "đi theo mode.json" nằm trong hai script trình duyệt
//   (store_gui/drinks-pos.js, test_gui/app.js). Viết lại nó bằng Python là
//   test mô hình của mình chứ không phải test mã thật. Nên ở đây cắt đúng
//   đoạn mã từ "const TEST_MODE_URL" tới hết hàm poll, chạy trong vm với
//   fetch/location giả. Đổi tên các mốc cắt thì harness báo lỗi rõ ràng.
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.resolve(__dirname, '..', '..');

function cut(file, startMark, endMark) {
  const text = fs.readFileSync(path.join(ROOT, file), 'utf8');
  const a = text.indexOf(startMark);
  const b = text.indexOf(endMark, a);
  if (a < 0 || b < 0) throw new Error(`không tìm thấy mốc cắt trong ${file}`);
  return text.slice(a, b);
}

const STORE_SRC = cut('store_gui/drinks-pos.js', "const TEST_MODE_URL", "pollHandoff();");
const TEST_SRC = cut('test_gui/app.js', "const TEST_MODE_URL", "poll();\npollMode();");

// Trạng thái mode.json dùng chung, như file thật trên đĩa.
const disk = { mode: null };

function page(src, href) {
  const u = new URL(href);
  const events = { navigated: [], notices: [] };
  const ctx = {
    console: { log() {}, error() {} },
    URLSearchParams, encodeURIComponent,
    location: { href, search: u.search, origin: u.origin },
    window: {},
    fetch: async () => ({ ok: true, json: async () => JSON.parse(JSON.stringify(disk.mode)) }),
    navigateWhenReachable: async (target) => { events.navigated.push(target); return true; },
    showScanNotice: (d) => events.notices.push(d),
    note: (m) => events.notices.push(m),
  };
  vm.createContext(ctx);
  vm.runInContext(src, ctx);
  // Gán href ở trang test là "điều hướng": theo dõi bằng setter.
  let cur = href;
  Object.defineProperty(ctx.location, 'href', {
    get: () => cur, set: (v) => { cur = v; events.navigated.push(v); },
  });
  return { ctx, events, poll: (fn) => vm.runInContext(`${fn}()`, ctx) };
}

const STORE_URL = 'http://localhost:8080/store_gui/drinks-pos.html';

async function scenarioStranded() {
  // DBG-01: trang bán hàng thấy BẬT, nhảy sang trang test; trước khi trang
  // test kịp lấy mốc, chế độ đã TẮT (soak ghi False ~5 s sau, hoặc bấm nút
  // 15 hai lần). Trang test lấy mốc = id "TẮT" và không bao giờ quay về.
  disk.mode = { open: false, id: 'm0' };
  const store = page(STORE_SRC, STORE_URL);
  await store.poll('pollTestMode');              // mốc
  disk.mode = { open: true, id: 'm1' };
  await store.poll('pollTestMode');              // nhảy sang test
  const jumped = store.events.navigated.length === 1;

  disk.mode = { open: false, id: 'm2' };         // tắt trước khi trang test lên
  const test = page(TEST_SRC, 'http://localhost:8080/test_gui/index.html?back=' +
                    encodeURIComponent(STORE_URL));
  for (let i = 0; i < 10; i++) await test.poll('pollMode');
  return { jumped, test_page_went_back: test.events.navigated.length > 0 };
}

async function scenarioReloadWhileOpen() {
  // DBG-02: trình duyệt bị watchdog/khởi động lại khi chế độ test đang BẬT.
  // Trang bán hàng lấy mốc = id "BẬT", đứng yên ở menu, không báo gì; mọi
  // /api/start sau đó bị 409.
  disk.mode = { open: true, id: 'm9' };
  const store = page(STORE_SRC, STORE_URL);
  for (let i = 0; i < 10; i++) await store.poll('pollTestMode');
  return {
    store_navigated: store.events.navigated.length > 0,
    store_notices: store.events.notices.length,
  };
}

(async () => {
  const out = {
    stranded: await scenarioStranded(),
    reload_while_open: await scenarioReloadWhileOpen(),
  };
  process.stdout.write(JSON.stringify(out));
})().catch((e) => { process.stderr.write(String(e.stack || e)); process.exit(2); });
