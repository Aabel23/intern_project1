/* ================================================================
   ADMIN-05 · FAULT LOG
   Every fault the machine recorded, newest first, in a date range.

   READ-ONLY, WITH ONE DELIBERATE EXCEPTION
     error_log is the machine's account of what happened to it, and this
     page still never edits a row: the one question it exists to answer
     -- "what went wrong, and had it gone wrong before?" -- stops being
     answerable the first time an inconvenient entry is rewritten.

     What it does now allow is deleting a RANGE. A machine with a flaky
     load cell writes thousands of rows a week, and a log nobody can face
     opening is not evidence either. Three things keep that honest, and
     none of them is optional:

       * it is scoped by the filters above the list -- a date range
         always, plus whatever narrowing is on screen. There is no
         "delete everything" and no button that means it.
       * the count in the dialog comes from the server, not from the
         rows on screen. The list is capped; the filter is not.
       * it needs its own permission (errors_purge, owner-only by
         default). Reading the log and pruning it are not one power.

   WHERE THE FILTERING HAPPENS
     On the server, like the report. The table grows without bound, so
     fetching it all to show one day of it would work fine now and stop
     working the first busy month.
   ================================================================ */
if (!AdminAuth.initPage('errors')) throw new Error('redirecting to login');

const $ = id => document.getElementById(id);
const ERRORS_URL = '../api/errors';
const DELETE_URL = '../api/errors/delete';

/* ---------- arriving from a ticket ----------
   The tickets page links here with ?ticket=<serial>. That serial is the
   tag the machine wrote into the head of each fault's message -- the
   whole link between the two screens, and it needed no column; see HOW A
   FAULT STILL NAMES ITS TICKET in database/error_log.py.

   While it is set the date range is ignored, by the server as well as
   here: a link from a row must show that row's faults, not an empty page
   because the range happened to be "today". The banner is how the user
   knows the list is narrowed, and how they get back out. */
const linkedTicket = new URLSearchParams(location.search).get('ticket') || '';

/* The one description of "what is on screen right now", used to fetch the
   list AND to say what a delete would take. Two copies of this would
   agree today and disagree the first time a filter is added to one of
   them -- and there, the disagreement deletes rows nobody saw listed. */
function activeFilter() {
  return {
    from: $('fromDate').value,
    to: $('toDate').value,
    severity: $('severityFilter').value,
    ...(linkedTicket ? { ticket: linkedTicket } : {}),
  };
}

/* ---------- dates ----------
   yyyy-mm-dd strings throughout, the same as the report: it is what
   <input type="date"> speaks and what the server parses, and building
   Date objects in between drags the tablet's timezone into a question
   about which day the MACHINE recorded a fault on. */
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

/* ---------- fetching ---------- */
async function get() {
  const params = new URLSearchParams(activeFilter());

  const response = await fetch(ERRORS_URL + '?' + params, {
    cache: 'no-store',
    headers: { Authorization: 'Bearer ' + AdminAuth.token() },
  });

  if (response.status === 401) { AdminAuth.logout(); throw new Error('401'); }

  const result = await response.json().catch(() => ({}));

  if (!response.ok || !result.ok) {
    throw new Error(result.error || 'Không tải được nhật ký lỗi.');
  }

  return result;
}

const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, c =>
  ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' })[c]);

/* Severity decides the row's colour. Three levels, and only one of them
   is loud: if every line is red, the red stops meaning anything. */
const SEVERITY_LABEL = { info: 'Thông tin', warning: 'Cảnh báo', error: 'Lỗi' };

/* Same padding as every other id on the console, so a column of them
   lines up and reads as the same kind of thing. */
const id4 = value => String(value ?? '').padStart(4, '0');

/* The ticket this fault happened to, if it named one. A dash is the
   honest answer for the two cases that cannot: a fault from before
   2026-09-07, when the tag did not exist, and one recorded around an
   order rather than inside it -- a code refused before any ticket was
   claimed is the common one. */
function ticketLink(row) {
  if (!row.ticket_serial) return '<span class="dim">—</span>';

  return `<a class="ticketlink" href="tickets.html?serial=${
    encodeURIComponent(row.ticket_serial)}">#${
    escapeHtml(id4(row.ticket_serial))}</a>`;
}

/* Say the list is narrowed, and offer the way back. Without this the page
   looks like the whole log with most of it mysteriously missing.

   Drawn from the server's reading of the parameter, not from the URL: a
   serial the server rejected filtered nothing, and a banner claiming a
   narrowing that is not in force is worse than no banner. */
function showLinkBanner(ticket) {
  const banner = $('linkBanner');
  if (!banner) return;

  banner.hidden = !ticket;

  if (ticket) {
    $('linkBannerText').textContent =
      `Đang xem sự cố của vé #${id4(ticket)}`;
  }
}

function render(data) {
  showLinkBanner(data.ticket);

  // Courtesy, not the boundary -- /api/errors/delete refuses a role
  // without the area whatever this browser decides to show, and refuses
  // a ticket-scoped delete whatever this browser asks for. Hidden while
  // one ticket is on screen because there is no date range in play then,
  // so there is nothing to scope a delete to.
  $('deleteBtn').hidden = !data.may_delete || Boolean(data.ticket);

  const rows = data.errors || [];
  const body = $('errorBody');

  $('countNote').textContent = data.truncated
    ? `${rows.length} lỗi (đã cắt ở ${data.limit} — thu hẹp khoảng ngày để xem đủ)`
    : `${rows.length} lỗi`;

  body.innerHTML = rows.map(row => {
    const severity = String(row.severity || 'error');

    return `<tr class="sev-${escapeHtml(severity)}">
      <td class="mono nowrap">${escapeHtml(row.created_at || '')}</td>
      <td><span class="tag tag-${escapeHtml(severity)}">${
        escapeHtml(SEVERITY_LABEL[severity] || severity)}</span></td>
      <td class="mono nowrap">${ticketLink(row)}</td>
      <td class="nowrap">${escapeHtml(row.step_label || '—')}${
        row.step_type ? ` <span class="dim">${escapeHtml(row.step_type)}</span>` : ''}</td>
      <td>${escapeHtml(row.drink_name || '—')}</td>
      <td class="logmsg">${escapeHtml(row.message || '')}</td>
    </tr>`;
  }).join('');

  $('emptyNote').hidden = rows.length > 0;
}

async function load() {
  try {
    render(await get());
  } catch (error) {
    if (String(error.message) === '401') return;
    $('errorBody').innerHTML = '';
    $('emptyNote').hidden = false;
    $('emptyNote').textContent = error.message;
  }
}

/* ---------- deleting a range ----------
   Two round trips on purpose. The first asks the server how many rows the
   current filter matches, because the list on screen is capped at the
   server's page limit and "delete the 500 rows you can see" would be a
   lie on any busy week. The second does it.

   The number is not re-checked in between. A machine mid-fault writes
   rows while the dialog is open, and refusing the delete because the
   count moved would make the button unusable on exactly the machine that
   needs it -- so the dialog says what it counted and the toast says what
   was actually removed. */
async function post(body) {
  const response = await fetch(DELETE_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: 'Bearer ' + AdminAuth.token(),
    },
    body: JSON.stringify(body),
  });

  if (response.status === 401) { AdminAuth.logout(); throw new Error('401'); }

  const result = await response.json().catch(() => ({}));

  if (!response.ok || !result.ok) {
    throw new Error(result.error || 'Không xoá được nhật ký lỗi.');
  }

  return result;
}

/* One line per narrowing that is actually set. Listing "Loại: Tất cả"
   would pad the dialog with rows that do not restrict anything, and the
   whole job of this box is to make the restriction unmissable. */
function filterSummary(filter, count) {
  const lines = [
    ['Khoảng ngày', `${escapeHtml(filter.from)} → ${escapeHtml(filter.to)}`],
  ];

  if (filter.severity) {
    lines.push(['Mức', escapeHtml(SEVERITY_LABEL[filter.severity] ||
                                  filter.severity)]);
  }

  return `<dl class="purgesum">${
    lines.map(([term, value]) =>
      `<div><dt>${term}</dt><dd>${value}</dd></div>`).join('')
  }<div class="purgecount"><dt>Sẽ xoá</dt><dd><b>${Number(count)}</b> dòng</dd></div></dl>`;
}

async function askDelete() {
  const button = $('deleteBtn');
  const filter = activeFilter();

  button.disabled = true;

  try {
    const preview = await post({ ...filter, preview: true });

    if (!preview.count) {
      showToast('Không có dòng nào khớp bộ lọc này.', 'warn');
      return;
    }

    openConfirm(filter, preview);
  } catch (error) {
    if (String(error.message) !== '401') showToast(escapeHtml(error.message), 'warn');
  } finally {
    button.disabled = false;
  }
}

function openConfirm(filter, preview) {
  // The server's own reading of the range, not the input values: it is
  // what the delete will use, and a typo'd date should be visible here
  // rather than after the rows are gone.
  const shown = { ...filter, from: preview.from, to: preview.to };

  $('confirmModal').innerHTML = `
    <h3>Xoá nhật ký lỗi</h3>
    <div class="msub">Không hoàn tác được</div>
    ${filterSummary(shown, preview.count)}
    <div class="mnote">
      Chỉ những dòng khớp bộ lọc trên bị xoá — phần còn lại của nhật ký
      giữ nguyên. <b>Không khôi phục lại được.</b>
    </div>
    <div class="modal-acts">
      <button class="btn ghost" id="cNo">Hủy</button>
      <button class="btn danger" id="cYes">Xoá ${Number(preview.count)} dòng</button>
    </div>`;

  $('confirmOverlay').classList.add('show');
  $('cNo').onclick = closeConfirm;
  $('cYes').onclick = () => runDelete(filter);
  $('cNo').focus();
}

async function runDelete(filter) {
  const yes = $('cYes');
  yes.disabled = true;
  yes.textContent = 'Đang xoá…';

  try {
    const result = await post({ ...filter, preview: false });
    closeConfirm();
    showToast(`Đã xoá ${Number(result.deleted)} dòng nhật ký lỗi.`, 'ok');
    await load();
  } catch (error) {
    closeConfirm();
    if (String(error.message) !== '401') showToast(escapeHtml(error.message), 'warn');
  }
}

function closeConfirm() {
  $('confirmOverlay').classList.remove('show');
  $('confirmModal').innerHTML = '';
}

/* ---------- wiring ---------- */
$('presets').addEventListener('click', event => {
  const button = event.target.closest('[data-preset]');
  if (button) applyPreset(button.dataset.preset);
});

for (const id of ['fromDate', 'toDate', 'severityFilter']) {
  $(id).addEventListener('change', load);
}

$('deleteBtn').addEventListener('click', askDelete);
$('confirmOverlay').addEventListener('click', event => {
  if (event.target === $('confirmOverlay')) closeConfirm();
});

applyPreset('7');
