/* ================================================================
   ADMIN-04 · REPORT
   How many drinks were sold, what they earned, by drink and by day.

   WHERE THE NUMBERS COME FROM
     GET /api/report, which counts order_ticket rows that reached
     'used' -- one row per drink the machine actually finished. The
     server does the counting; nothing is totalled here, so the page
     and any other reader of that endpoint can never disagree.

   WHAT THE FILTERS DO
     Both go to the server as query parameters. Filtering in the
     browser would mean fetching every ticket ever sold to show one
     day of them, and would quietly stop working the first month the
     shop is busy.
   ================================================================ */
if (!AdminAuth.initPage('report')) throw new Error('redirecting to login');

const $ = id => document.getElementById(id);
const REPORT_URL = '../api/report';
const ORDERS_URL = '../api/report/orders';

let category = 'all';
let latest = null;      // the last report the server sent, for the CSV
let ordersPage = 1;     // which page of the order list is showing

/* ---------- dates ----------
   Kept as yyyy-mm-dd strings, which is what <input type="date"> reads
   and writes and what the server parses. Building Date objects in
   between would drag the browser's timezone into a question about
   which day a sale falls on -- and the answer is the machine's day,
   not the tablet's. */
const iso = d => d.toISOString().slice(0, 10);

function localToday() {
  // toISOString() is UTC, which in Vietnam is yesterday for the first
  // seven hours of every day. Shift by the offset so "today" means the
  // day it is here.
  const now = new Date();
  return iso(new Date(now.getTime() - now.getTimezoneOffset() * 60000));
}

function daysAgo(count) {
  const now = new Date();
  now.setDate(now.getDate() - count);
  return iso(new Date(now.getTime() - now.getTimezoneOffset() * 60000));
}

function applyPreset(name) {
  const today = localToday();

  if (name === 'today') { $('fromDate').value = today; }
  else if (name === 'month') { $('fromDate').value = today.slice(0, 8) + '01'; }
  else { $('fromDate').value = daysAgo(Number(name) - 1); }

  $('toDate').value = today;
  load();
}

/* ---------- ids ----------
   Four digits, zero-padded. It is the width the machine already prints a
   SKU at -- `f"SKU {sku:04d}"` in order/qr_to_recipe.py, and the same in
   the qrproto encoders -- so one drink's id reads identically whether it
   came off a printed label, out of a machine log, or off this screen.

   Never truncated: an id that has outgrown four digits simply gets wider.
   Padding is for lining a column up, and a cut id is a different id. */
const id4 = value => String(value ?? '').padStart(4, '0');

/* ---------- money ---------- */
const money = value => '$' + Number(value || 0).toFixed(2);

/* "Giá bán" is the drink's price on the menu NOW -- the number a customer
   would be charged today, which is what somebody reading this column is
   asking for. It is deliberately not revenue/sold: that average is a
   different fact, and on a drink whose price changed mid-range it is a
   figure nobody ever actually paid.

   currentPrice is 0 for a drink that has since been taken off the menu
   entirely; there is no current price to show, so those fall back to what
   was really charged. */
const sellPrice = d => d.currentPrice || d.averagePrice;

/* Shown on hover, and only when the two disagree -- which is exactly when
   somebody would otherwise wonder why 8 x $5.00 is not $36.00. */
function sellPriceHint(d) {
  if (!d.currentPrice) return 'Món không còn trên menu · giá thực tế đã bán';
  if (Math.abs(d.currentPrice - d.averagePrice) < 0.005) return 'Giá hiện tại trên menu';
  return `Giá hiện tại trên menu · trung bình đã bán ${money(d.averagePrice)}`;
}

/* ---------- fetching ---------- */
const filters = () => ({
  from: $('fromDate').value,
  to: $('toDate').value,
  category,
});

async function get(url, extra) {
  const params = new URLSearchParams({ ...filters(), ...(extra || {}) });
  const response = await fetch(url + '?' + params, {
    cache: 'no-store',
    headers: { Authorization: 'Bearer ' + AdminAuth.token() },
  });

  if (response.status === 401) { AdminAuth.logout(); throw new Error('401'); }

  const result = await response.json().catch(() => ({}));

  if (!response.ok || !result.ok) {
    throw new Error(result.error || 'Không tải được báo cáo.');
  }

  return result;
}

/* Changing a filter resets to page 1. Staying on page 4 of a range that
   now has one page shows an empty list under a summary saying there are
   sales, which reads as a broken report. */
async function load() {
  ordersPage = 1;
  setBusy(true);

  try {
    const [report, orders] = await Promise.all([
      get(REPORT_URL),
      get(ORDERS_URL, { page: 1 }),
    ]);
    latest = report;
    render(report);
    renderOrders(orders);
  } catch (error) {
    if (error.message !== '401') showToast('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M10.3 3.9 1.8 18.1A2 2 0 0 0 3.5 21h17a2 2 0 0 0 1.7-2.9L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/></svg> ' + error.message, 'warn');
  } finally {
    setBusy(false);
  }
}

/* Turning a page fetches ONLY that page and repaints ONLY the list.
   The cards, the per-drink table and the filters are untouched -- they
   describe the whole range, not the ten rows on screen, so re-requesting
   them would be work nobody asked for and a visible flicker.

   The list dims while the request is in flight. Without it a page turn
   over a slow link looks like a button that did nothing, and the second
   press lands on a page the reader never saw. */
async function loadOrders(page) {
  const list = $('orderList');
  list.classList.add('is-loading');

  try {
    const orders = await get(ORDERS_URL, { page });
    ordersPage = orders.page;
    renderOrders(orders);
  } catch (error) {
    if (error.message !== '401') showToast('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M10.3 3.9 1.8 18.1A2 2 0 0 0 3.5 21h17a2 2 0 0 0 1.7-2.9L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/></svg> ' + error.message, 'warn');
  } finally {
    list.classList.remove('is-loading');
  }
}

function setBusy(busy) {
  const button = $('applyBtn');
  button.disabled = busy;
  button.innerHTML = busy ? 'Đang tải…' : '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg> Xem báo cáo';
}

/* ---------- painting ---------- */
const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g,
  c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);

function renderCatPills(categories) {
  const all = [{ id: 'all', name: 'Tất cả' }, ...(categories || [])];
  $('catPills').innerHTML = all.map(c =>
    `<button class="pill ${c.id === category ? 'active' : ''}" data-cat="${c.id}">${escapeHtml(c.name.replace(' Menu', ''))}</button>`
  ).join('');
  $('catPills').querySelectorAll('.pill').forEach(el => {
    el.onclick = () => { category = el.dataset.cat; renderCatPills(categories); load(); };
  });
}

function render(data) {
  renderCatPills(data.categories);

  $('stSold').textContent = data.totals.sold;
  $('stRevenue').textContent = money(data.totals.revenue);
  $('stAvg').textContent = money(data.totals.average);
  $('stFailed').textContent = data.totals.failed;

  const catName = data.category === 'all'
    ? 'tất cả danh mục'
    : (data.categories.find(c => c.id === data.category) || {}).name || data.category;
  $('rangeSub').textContent =
    `${data.from} → ${data.to} · ${catName} · ${data.totals.drinks} món`;

  // A sale valued at today's price rather than the price it was sold at
  // is an estimate, and the difference has to be visible or the total
  // reads as something it is not.
  const note = $('estimateNote');
  if (data.totals.estimated) {
    note.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M10.3 3.9 1.8 18.1A2 2 0 0 0 3.5 21h17a2 2 0 0 0 1.7-2.9L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/></svg> ${data.totals.estimated} ly được bán trước khi hệ thống lưu giá theo vé, nên doanh thu của những ly đó được tính theo <b>giá hiện tại</b>.`;
    note.hidden = false;
  } else {
    note.hidden = true;
  }

  const body = $('reportBody');

  if (!data.drinks.length) {
    body.innerHTML = `<tr><td colspan="5" style="text-align:center;color:var(--muted);padding:26px">Chưa có ly nào bán ra trong khoảng này.</td></tr>`;
    $('topSub').textContent = '';
    return;
  }

  const top = data.drinks[0];
  $('topSub').innerHTML = `Bán chạy nhất: <b>${escapeHtml(top.name)}</b> (${top.sold} ly)`;

  const most = Math.max(...data.drinks.map(d => d.revenue)) || 1;

  body.innerHTML = data.drinks.map(d => `
    <tr>
      <td>
        <div class="m-item">
          <div class="m-emoji">${d.emoji}</div>
          <div>
            <div class="m-name">${escapeHtml(d.name)}</div>
            <div class="m-sku">SKU ${id4(d.drinkId)}</div>
          </div>
        </div>
      </td>
      <td style="text-align:right"><b>${d.sold}</b></td>
      <td style="text-align:right" title="${sellPriceHint(d)}">${money(sellPrice(d))}</td>
      <td style="text-align:right"><b>${money(d.revenue)}</b>${
        // The ~ belongs on the money that is uncertain, not on the price.
        // The price column is today's figure by definition; the revenue is
        // the one partly worked out from it.
        d.estimated ? ' <span class="est" title="Một phần doanh thu tính theo giá hiện tại">~</span>' : ''}</td>
      <td>
        <div class="sharebar"><span style="width:${Math.round(d.revenue / most * 100)}%"></span></div>
      </td>
    </tr>`).join('');
}

/* ---------- the order list ---------- */
function renderOrders(data) {
  const list = $('orderList');
  const first = (data.page - 1) * data.pageSize + 1;
  const last = Math.min(data.page * data.pageSize, data.total);

  $('ordersSub').textContent = data.total
    ? `${data.total} ly · đang xem ${first}–${last}`
    : 'Chưa có đơn nào trong khoảng này.';

  if (!data.orders.length) {
    list.innerHTML = `<div class="orderempty">Chưa có đơn nào trong khoảng này.</div>`;
    renderPager(data);
    return;
  }

  list.innerHTML = data.orders.map(o => `
    <div class="orderrow">
      <div class="thumb">${
        // A photo when the file is really on disk, the drink's glyph when
        // it is not. The server sends null rather than a path that 404s,
        // so there is no broken-image icon to fall back from.
        o.image
          ? `<img src="${escapeHtml(o.image)}" alt="" loading="lazy">`
          : o.emoji
      }</div>
      <div>
        <div class="oname">${escapeHtml(o.name)}</div>
        <div class="ometa">Vé #${String(o.serial).padStart(4, '0')}</div>
      </div>
      <div class="otime">${escapeHtml(o.completedAt || '—')}</div>
      <div class="oprice">${money(o.price)}${
        o.estimated ? ' <span class="est" title="Tính theo giá hiện tại">~</span>' : ''
      }</div>
    </div>`).join('');

  renderPager(data);
}

/* Which page numbers to draw. Every page while there are few, and a
   window around the current one once there are many -- a hundred-day
   range should not put a hundred buttons on the screen. */
function pageWindow(page, pages) {
  if (pages <= 7) return Array.from({ length: pages }, (_, i) => i + 1);

  const window = new Set([1, pages, page, page - 1, page + 1]);
  const shown = [...window].filter(n => n >= 1 && n <= pages).sort((a, b) => a - b);

  // A gap of more than one page becomes an ellipsis rather than a jump.
  return shown.reduce((out, n, i) => {
    if (i && n - shown[i - 1] > 1) out.push('…');
    out.push(n);
    return out;
  }, []);
}

function renderPager(data) {
  const html = data.pages <= 1 ? '' : `
    <button data-page="${data.page - 1}" ${data.page <= 1 ? 'disabled' : ''}>‹ Trước</button>
    ${pageWindow(data.page, data.pages).map(n => n === '…'
      ? '<span class="pagegap">…</span>'
      : `<button class="pagenum ${n === data.page ? 'active' : ''}" data-page="${n}">${n}</button>`
    ).join('')}
    <button data-page="${data.page + 1}" ${data.page >= data.pages ? 'disabled' : ''}>Sau ›</button>`;

  // Two pagers, one above the list and one below it: after reading ten
  // rows the reader is at the bottom, and sending them back up to turn
  // the page is the whole reason list footers exist.
  ['pager', 'pagerBottom'].forEach(id => {
    const pager = $(id);
    if (!pager) return;
    pager.innerHTML = html;
    pager.querySelectorAll('button[data-page]').forEach(el => {
      el.onclick = () => loadOrders(Number(el.dataset.page));
    });
  });
}

/* ---------- CSV ----------
   Built from the report already on screen, so what downloads is what
   was read. A BOM because this gets opened in Excel, which reads a
   UTF-8 file without one as Latin-1 and turns every Vietnamese name
   into mojibake. */
function toCsv(data) {
  const rows = [
    ['Tu ngay', data.from],
    ['Den ngay', data.to],
    ['Danh muc', data.category],
    [],
    ['Mon', 'SKU', 'So ly', 'Gia hien tai', 'TB da ban', 'Doanh thu'],
    ...data.drinks.map(d => [d.name, d.drinkId, d.sold,
      sellPrice(d).toFixed(2), d.averagePrice.toFixed(2), d.revenue.toFixed(2)]),
    [],
    ['Tong', '', data.totals.sold, '', '', data.totals.revenue.toFixed(2)],
  ];
  return '﻿' + rows.map(r => r.map(cell => {
    const text = String(cell ?? '');
    return /[",\n]/.test(text) ? '"' + text.replace(/"/g, '""') + '"' : text;
  }).join(',')).join('\n');
}

$('csvBtn').onclick = () => {
  if (!latest) return;
  const blob = new Blob([toCsv(latest)], { type: 'text/csv;charset=utf-8' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `bao-cao-${latest.from}_${latest.to}.csv`;
  link.click();
  URL.revokeObjectURL(link.href);
};

/* ---------- wiring ---------- */
$('presets').querySelectorAll('[data-preset]').forEach(el => {
  el.onclick = () => applyPreset(el.dataset.preset);
});
$('applyBtn').onclick = load;
$('fromDate').onchange = load;
$('toDate').onchange = load;

applyPreset('7');
