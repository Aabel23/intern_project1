/* ================================================================
   ADMIN-06 · QR TICKETS
   One row per drink ordered: what it was, what it cost, and how far
   through the machine it got.

   THE ONE THING THIS PAGE WRITES
     A ticket's status, by hand. Staff need it when the machine and
     reality disagree -- a label lost before it was scanned, a drink
     made and handed over after a fault, a test ticket that should not
     count as a sale.

     The timestamps are never touched. They record what happened to the
     machine; a correction made at a desk did not make a drink get
     scanned at 14:32, and writing one would turn the audit trail into
     a guess. The status says what to believe, the timestamps say what
     was observed, and the two are allowed to disagree.

   WHY IT ASKS FIRST
     'used' is what the report counts as a sale. Changing it changes
     yesterday's takings, so it is not something a stray thumb should
     be able to do on a tablet behind a bar.
   ================================================================ */
if (!AdminAuth.initPage('tickets')) throw new Error('redirecting to login');

const $ = id => document.getElementById(id);
const TICKETS_URL = '../api/tickets';
const STATUS_URL = '../api/ticket/status';
const REPRINT_URL = '../api/ticket/reprint';

/* ---------- dates: identical to the report and the fault log ---------- */
const iso = d => d.toISOString().slice(0, 10);

function localToday() {
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

  if (name === 'today') $('fromDate').value = today;
  else if (name === 'month') $('fromDate').value = today.slice(0, 8) + '01';
  else $('fromDate').value = daysAgo(Number(name) - 1);

  $('toDate').value = today;
  load();
}

const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, c =>
  ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' })[c]);

/* Record ids are shown four digits wide, zero-padded: #0001, not #1.
   Same width the machine already prints SKUs at (`f"{sku:04d}"` in
   qr_to_recipe.py and the qrproto encoders), so one id reads the same
   whether it came off a label, out of a log, or off this screen.

   Fixed width also means a column of them lines up, which is the whole
   reason they are in a monospaced column: #9 above #4213 is a list you
   have to read, #0009 above #4213 is one you can scan.

   Ids past four digits are NOT truncated -- they simply get wider. Padding
   is for alignment, and an id that has outgrown the padding is still an
   id; cutting it would make it a different one. */
const id4 = value => String(value ?? '').padStart(4, '0');

/* What each status means, in the words staff use. 'noqr_err' is the one
   that needs explaining: it is a dead end, not a ticket waiting to be
   redeemed. */
const STATUS_LABEL = {
  unused: 'Chưa dùng',
  in_progress: 'Đang pha',
  used: 'Đã dùng',
  expired: 'Hết hạn',
  noqr_err: 'Lỗi (chạy không quét)',
};

let settable = [];      // the statuses this console may write
let locked = [];        // statuses it refuses to move a ticket out of

/* ---------- arriving from a fault ----------
   The fault log links here with ?serial=<n>, the ticket a fault named.
   While it is set the date range is ignored, by the server as well as
   here -- a link from a fault must land on the ticket that caused it,
   whenever it was sold. */
const linkedSerial = new URLSearchParams(location.search).get('serial') || '';

/* ---------- fetching ---------- */
async function api(url, options) {
  const response = await fetch(url, {
    cache: 'no-store',
    ...options,
    headers: {
      Authorization: 'Bearer ' + AdminAuth.token(),
      ...(options && options.body ? { 'Content-Type': 'application/json' } : {}),
    },
  });

  if (response.status === 401) { AdminAuth.logout(); throw new Error('401'); }

  const result = await response.json().catch(() => ({}));

  if (!response.ok || !result.ok) {
    throw new Error(result.error || 'Không tải được danh sách vé.');
  }

  return result;
}

const load = async () => {
  try {
    render(await api(TICKETS_URL + '?' + new URLSearchParams({
      from: $('fromDate').value,
      to: $('toDate').value,
      status: $('statusFilter').value,
      ...(linkedSerial ? { serial: linkedSerial } : {}),
    })));
  } catch (error) {
    if (String(error.message) === '401') return;
    $('ticketBody').innerHTML = '';
    $('emptyNote').hidden = false;
    $('emptyNote').textContent = error.message;
  }
};

function fillStatusFilter(values) {
  const select = $('statusFilter');
  const chosen = select.value;
  select.innerHTML = '<option value="">Tất cả</option>' +
    values.map(v => `<option value="${escapeHtml(v)}">${
      escapeHtml(STATUS_LABEL[v] || v)}</option>`).join('');
  if (values.includes(chosen)) select.value = chosen;
}

/* The control for one row's status.

   Three shapes, because there are three situations and collapsing them
   loses the reason:

     locked        no control at all. A failed ticket is a dead end -- no
                   label left to scan -- so reopening it would put a row
                   back in the pool no customer can redeem. Saying why
                   beats a disabled box that looks broken.
     nothing to do only one status is settable and it is already that.
     otherwise     a picker of the settable statuses. */
function statusControl(row) {
  const current = String(row.status);

  if (locked.includes(current)) {
    return '<span class="dim nowrap" title="Vé lỗi là ngõ cụt: không còn nhãn để quét lại">— không đổi được</span>';
  }

  const options = settable.map(s =>
    `<option value="${escapeHtml(s)}" ${s === current ? 'selected' : ''}>${
      escapeHtml(STATUS_LABEL[s] || s)}</option>`).join('');

  return `<select class="statuspick" data-serial="${escapeHtml(row.serial)}"
            data-was="${escapeHtml(current)}"
            data-name="${escapeHtml(row.drink_name || '')}">${
    // A status this console cannot write is still what the row IS, so it
    // is shown -- otherwise the closed picker would read "Chưa dùng" on a
    // ticket that has expired. Shown DISABLED: it is the starting point,
    // not a third thing you may choose, and the server would refuse it.
    settable.includes(current) ? '' :
      `<option value="${escapeHtml(current)}" selected disabled>${
        escapeHtml(STATUS_LABEL[current] || current)} (hiện tại)</option>`
  }${options}</select>`;
}

/* Another COPY of a label, for one that jammed, was lost or smudged.

   OFFERED ONLY ON 'unused'
     Every other status would print paper that cannot work: the machine
     refuses a used ticket, ages out an expired one, and a 'noqr_err' row
     is a dead end. The server refuses those too -- this is the same rule
     said early, so nobody presses a button that was always going to say
     no. A ticket past its 24 hours still reads 'unused' here, and that
     one is caught by the server, which is where the clock lives.

   NO CONFIRM STEP
     It writes nothing. A payload is claimed atomically by its hash, so
     two copies of one label still buy exactly one drink -- whoever scans
     first gets it and the other is refused. The cost of a stray press is
     a piece of paper, which is not worth a modal; the picker beside it
     asks first because THAT one moves yesterday's takings. */
function reprintControl(row) {
  if (String(row.status) !== 'unused') {
    return '<span class="dim">—</span>';
  }

  return `<button type="button" class="btn ghost compact" data-reprint="${
    escapeHtml(row.serial)}">In lại</button>`;
}

/* A ticket's faults, if it had any. They are matched by the tag the
   machine writes into the head of error_log.message -- no column joins
   these two tables; see HOW A FAULT STILL NAMES ITS TICKET in
   database/error_log.py.

   Quiet when there are none: most rows have none, and the ones that do
   should read as an offer, not an alarm. */
function faultLink(row) {
  if (!row.fault_count) return '<span class="dim">—</span>';

  return `<a class="faultlink" href="errors.html?ticket=${
    encodeURIComponent(row.serial)}">${row.fault_count} sự cố &rsaquo;</a>`;
}

/* Say the list is narrowed to one ticket, and offer the way back --
   without it the page looks like the whole list with most of it missing.
   From the server's reading of the parameter, not the URL's: a serial it
   rejected narrowed nothing. */
function showLinkBanner(serial) {
  const banner = $('linkBanner');
  if (!banner) return;

  banner.hidden = !serial;

  if (serial) {
    $('linkBannerText').textContent = `Đang xem vé #${id4(serial)}`;
  }
}

const time = value => value ? escapeHtml(String(value).slice(0, 19)) : '—';

function render(data) {
  showLinkBanner(data.serial);
  settable = data.settable || [];
  locked = data.locked || [];
  fillStatusFilter(data.statuses || []);

  const rows = data.tickets || [];
  $('countNote').textContent = data.truncated
    ? `${rows.length} vé (đã cắt ở ${data.limit} — thu hẹp khoảng ngày để xem đủ)`
    : `${rows.length} vé`;

  $('ticketBody').innerHTML = rows.map(row => {
    const current = String(row.status);

    return `<tr>
      <td class="mono">#${escapeHtml(id4(row.serial))}</td>
      <td>${escapeHtml(row.drink_name || '—')}</td>
      <td class="mono">${row.price == null ? '—' : '$' + Number(row.price).toFixed(2)}</td>
      <td><span class="tag tag-${escapeHtml(current)}">${
        escapeHtml(STATUS_LABEL[current] || current)}</span></td>
      <td class="mono nowrap dim">${time(row.created_at)}</td>
      <td class="mono nowrap dim">${time(row.scanned_at)}</td>
      <td class="mono nowrap dim">${time(row.completed_at)}</td>
      <td>${escapeHtml(row.note || '')}</td>
      <td class="nowrap">${faultLink(row)}</td>
      <td class="nowrap">${reprintControl(row)}</td>
      <td class="nowrap">${statusControl(row)}</td>
    </tr>`;
  }).join('');

  $('emptyNote').hidden = rows.length > 0;
}

/* ---------- changing a status ---------- */
let pending = null;

function askConfirm(select) {
  pending = {
    select,
    serial: select.dataset.serial,
    from: select.dataset.was,
    to: select.value,
  };

  $('confirmSub').textContent =
    `Vé #${id4(pending.serial)}${pending.select.dataset.name ? ' · ' + pending.select.dataset.name : ''}` +
    ` — từ "${STATUS_LABEL[pending.from] || pending.from}"` +
    ` thành "${STATUS_LABEL[pending.to] || pending.to}".` +
    (pending.to === 'used' || pending.from === 'used'
      ? ' Trạng thái "Đã dùng" là thứ báo cáo doanh thu đếm, nên số liệu sẽ đổi theo.'
      : '');

  $('confirmModal').classList.add('show');
}

function closeConfirm(revert) {
  // Put the dropdown back where it was: without this a cancelled change
  // leaves the row displaying a status the database does not hold.
  if (revert && pending) pending.select.value = pending.from;
  pending = null;
  $('confirmModal').classList.remove('show');
}

$('ticketBody').addEventListener('change', event => {
  const select = event.target.closest('.statuspick');
  if (!select) return;
  if (select.value === select.dataset.was) return;   // back to where it began
  askConfirm(select);
});

$('confirmNo').addEventListener('click', () => closeConfirm(true));

$('confirmYes').addEventListener('click', async () => {
  if (!pending) return;
  const { serial, to } = pending;
  const button = $('confirmYes');
  button.disabled = true;

  try {
    await api(STATUS_URL, {
      method: 'POST',
      body: JSON.stringify({ serial: Number(serial), status: to }),
    });
    closeConfirm(false);
    await load();          // re-read rather than patch the row in place
  } catch (error) {
    if (String(error.message) !== '401') alert(error.message);
    closeConfirm(true);
  } finally {
    button.disabled = false;
  }
});

/* ---------- reprinting a label ---------- */

/* Delegated, like the status picker: the rows are rebuilt on every load
   and per-button handlers would go with them.

   The button is handed back afterwards, success included. A printer that
   ate the first copy will eat the second, and the person standing at it
   is the only one who can see that -- so pressing again is theirs to
   decide, not something to be locked out of. */
$('ticketBody').addEventListener('click', async event => {
  const button = event.target.closest('[data-reprint]');
  if (!button || button.disabled) return;

  const serial = Number(button.dataset.reprint);
  const idle = button.textContent;

  button.disabled = true;
  button.textContent = 'Đang in...';

  try {
    await api(REPRINT_URL, {
      method: 'POST',
      body: JSON.stringify({ serial }),
    });
    button.textContent = 'Đã in ✓';
    // Long enough to read, then back to being a button: a second copy is
    // a legitimate thing to want.
    setTimeout(() => { button.textContent = idle; button.disabled = false; }, 1500);
  } catch (error) {
    button.textContent = idle;
    button.disabled = false;
    if (String(error.message) !== '401') alert(error.message);
  }
});

/* ---------- wiring ---------- */
$('presets').addEventListener('click', event => {
  const button = event.target.closest('[data-preset]');
  if (button) applyPreset(button.dataset.preset);
});

for (const id of ['fromDate', 'toDate', 'statusFilter']) {
  $(id).addEventListener('change', load);
}

applyPreset('7');
