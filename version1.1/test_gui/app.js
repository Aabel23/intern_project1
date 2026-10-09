/* FlexMix manual test screen.

   The server runs one job at a time on a worker thread; this page starts
   jobs and polls /api/status about twice a second. Nothing is pushed, so
   the page can be reloaded mid-job and pick the same job back up -- which
   matters when a prime run takes over a minute and someone bumps the
   tablet. */

const PUMP_COUNT = 10;
const PANEL_COUNT = 16;
const POLL_MS = 500;

/* Names come from the running job's results; until then the grid just
   shows numbers. The page deliberately does not query the database
   itself -- the server already knows the mapping and a second source
   would be one more thing to disagree. */
const pumpEl = document.getElementById('pumps');
const lampEl = document.getElementById('lamps');
const logEl = document.getElementById('log');
const barEl = document.getElementById('barFill');
const pillEl = document.getElementById('statePill');
const stopEl = document.getElementById('stopBtn');
const warnEl = document.getElementById('busyWarn');
const nameEl = document.getElementById('jobName');
const progEl = document.getElementById('progress');
const resultsEl = document.getElementById('results');

let running = false;

/* ---------------- build the grids ---------------- */
for (let n = 1; n <= PUMP_COUNT; n++) {
  const b = document.createElement('button');
  b.className = 'pump';
  b.dataset.pump = String(n);
  b.innerHTML = `<span class="n">${n}</span><span class="name">bơm ${n}</span>`;
  b.onclick = () => start('/api/prime', { pumps: [n] });
  pumpEl.appendChild(b);
}

for (let i = 0; i < PANEL_COUNT; i++) {
  const d = document.createElement('div');
  d.className = 'lamp';
  d.dataset.lamp = String(i);
  d.textContent = i;
  lampEl.appendChild(d);
}

/* ---------------- hold to run ----------------
   The button does not tell the pump to run and then, later, to stop.
   It tells it to run for the next moment, over and over, about three
   times a second. If this page closes, crashes, sleeps or loses the
   network, the messages stop and the machine switches the pump off by
   itself. Nothing has to arrive for the pump to stop; something has to
   keep arriving for it to keep going.

   Sent every HOLD_BEAT_MS, and the machine gives up after 1000 ms, so
   one lost message is survivable. */
const HOLD_BEAT_MS = 300;

const holdEl = document.getElementById('holdPumps');
const holdStateEl = document.getElementById('holdState');
let holdTimer = null;
let holdPump = null;

/* One press, one token. The machine refuses anything carrying a token
   whose press has already ended -- without it, a heartbeat sent a moment
   before the button came up can arrive a moment after the release and
   switch the pump back on for another second. */
let holdToken = '';

function newToken() {
  if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
  return String(Date.now()) + '-' + Math.random().toString(16).slice(2);
}

function holdStatus(text, kind) {
  holdStateEl.textContent = text;
  holdStateEl.className = 'holdstate' + (kind ? ' ' + kind : '');
}

async function beat(pump, token) {
  try {
    const response = await fetch('/api/pump/hold', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pump, token }),
    });
    const result = await response.json().catch(() => ({}));

    // The press ended while this was in flight. Its answer is about a
    // press that no longer exists, so it says nothing on screen.
    if (token !== holdToken) return;

    if (!response.ok || !result.ok) {
      // A 404 comes back as an HTML error page, so there is no message to
      // quote -- and that is the likeliest failure here: a test screen
      // started before this feature existed. Say which, rather than
      // "the machine refused", which sends somebody to look at the pumps.
      throw new Error(result.error || (response.status === 404
        ? 'Máy chủ chưa có tính năng bơm tay — khởi động lại '
          + 'order/run_flow.py (bản đang chạy đã cũ).'
        : 'Máy từ chối bơm (lỗi ' + response.status + ').'));
    }

    holdStatus(`Bơm ${pump} đang chạy — ${result.held}s`, 'on');
  } catch (error) {
    // Stop asking. The machine will switch off on its own a moment
    // later even if this message never gets through.
    endHold();
    holdStatus(error.message, 'bad');
  }
}

function startHold(pump, button) {
  if (holdPump !== null || running) return;

  holdPump = pump;
  holdToken = newToken();
  const token = holdToken;
  button.classList.add('holding');
  beat(pump, token);
  holdTimer = window.setInterval(() => beat(pump, token), HOLD_BEAT_MS);
}

function endHold() {
  if (holdTimer !== null) {
    window.clearInterval(holdTimer);
    holdTimer = null;
  }

  if (holdPump === null) return;

  const pump = holdPump;
  const token = holdToken;
  holdPump = null;
  holdToken = '';
  holdEl.querySelectorAll('.holding').forEach(b => b.classList.remove('holding'));
  holdStatus(`Bơm ${pump} đã dừng.`);

  // Best effort: the watchdog is what actually guarantees the stop.
  // keepalive lets this survive the page being closed.
  fetch('/api/pump/release', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pump, token }),
    keepalive: true,
  }).catch(() => {});
}

for (let n = 1; n <= PUMP_COUNT; n++) {
  const b = document.createElement('button');
  b.className = 'pump hold';
  b.dataset.pump = String(n);
  b.innerHTML = `<span class="n">${n}</span><span class="name">giữ để bơm</span>`;

  b.addEventListener('pointerdown', event => {
    event.preventDefault();
    // Keeps the events coming to this button even if the finger slides
    // off it, so releasing anywhere still counts as releasing.
    if (b.setPointerCapture) b.setPointerCapture(event.pointerId);
    startHold(n, b);
  });

  ['pointerup', 'pointercancel', 'pointerleave'].forEach(name =>
    b.addEventListener(name, endHold));

  holdEl.appendChild(b);
}

// Anything that takes this page out of the operator's hands releases:
// switching tab, locking the tablet, closing the window.
['blur', 'pagehide', 'beforeunload'].forEach(name =>
  window.addEventListener(name, endHold));
document.addEventListener('visibilitychange', () => {
  if (document.hidden) endHold();
});

/* ---------------- starting a job ---------------- */
async function start(url, body) {
  if (running) return;

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {}),
    });
    const result = await response.json().catch(() => ({}));

    if (!result.ok) {
      // 409 means the machine is busy with a real order, or another test
      // is still running. Both are worth saying out loud rather than
      // leaving the button looking broken.
      note(result.error || `Không bắt đầu được (HTTP ${response.status}).`);
      return;
    }
  } catch (error) {
    note(String(error.message || error));
    return;
  }

  clearMarks();
  poll();
}

function note(text) {
  logEl.textContent = text + '\n' + logEl.textContent;
}

function clearMarks() {
  document.querySelectorAll('.pump').forEach(p => {
    p.classList.remove('ok', 'bad', 'part', 'active');
  });
  document.querySelectorAll('.lamp').forEach(l => {
    l.classList.remove('on', 'hit', 'miss', 'done');
  });
  resultsEl.hidden = true;
}

document.getElementById('primeAll').onclick = () => start('/api/prime', { pumps: 'all' });
document.getElementById('ledTest').onclick = () => start('/api/panel/leds', {});
document.getElementById('buttonTest').onclick = () => start('/api/panel/buttons', {});
document.getElementById('scaleTest').onclick = () => start('/api/scale', {});
stopEl.onclick = () => fetch('/api/stop', { method: 'POST' });

/* ---------------- reading progress ---------------- */
async function poll() {
  let data;

  try {
    const response = await fetch('/api/status', { cache: 'no-store' });
    data = await response.json();
  } catch (error) {
    pillEl.textContent = 'Mất kết nối';
    pillEl.className = 'pill failed';
    return;                     // the next tick tries again
  }

  render(data);
}

function render(data) {
  running = data.state === 'running';

  pillEl.textContent = running ? 'Đang chạy'
    : data.state === 'failed' ? 'Lỗi'
    : data.state === 'done' ? 'Xong' : 'Sẵn sàng';
  pillEl.className = 'pill' + (running ? ' running'
    : data.state === 'failed' ? ' failed' : '');

  stopEl.disabled = !running;
  setEnabled(!running && !data.busy_reason);

  warnEl.hidden = !data.busy_reason;
  if (data.busy_reason) warnEl.textContent = data.busy_reason;

  nameEl.textContent = data.name ? `Nhật ký — ${data.name}` : 'Nhật ký';
  progEl.textContent = data.total
    ? `${data.finished}/${data.total} · ${data.elapsed}s`
    : (data.elapsed ? `${data.elapsed}s` : '');
  barEl.style.width = data.total
    ? Math.round(100 * data.finished / data.total) + '%' : '0';

  const text = (data.lines || []).join('\n')
    + (data.message ? `\n\n${data.message}` : '');
  if (text.trim()) logEl.textContent = text;
  logEl.scrollTop = logEl.scrollHeight;

  paintPumps(data);
  paintLamps(data);
  paintResults(data);
}

function paintPumps(data) {
  (data.results || []).forEach(r => {
    if (r.pump === undefined) return;
    const el = document.querySelector(`.pump[data-pump="${r.pump}"]`);
    if (!el) return;

    el.classList.remove('active');
    el.classList.add(r.result === 'PRIMED' ? 'ok'
      : r.result === 'PARTIAL' ? 'part' : 'bad');

    // The server knows the ingredient name; show it once it has said so.
    if (r.name && r.name !== '(chua gan)') {
      el.querySelector('.name').textContent = r.name;
    }
  });

  // The one being worked on now: everything reported, plus one.
  if (data.state === 'running' && data.name && data.name.startsWith('prime')) {
    const doneIds = new Set((data.results || []).map(r => r.pump));
    const next = document.querySelector(
      `.pump:not(.ok):not(.bad):not(.part)[data-pump]`);
    if (next && !doneIds.has(Number(next.dataset.pump))) {
      next.classList.add('active');
    }
  }
}

/* The lamp grid.

   It does NOT try to mirror the physical panel in real time, because it
   cannot: the lamps step every 350 ms and this page polls every 500 ms, so
   a faithful mirror would sample a random subset. The first version tried
   anyway -- it added an "on" class and never removed it -- and the grid
   filled up with whichever lamps a poll happened to catch, which looked
   exactly like a panel with half its LEDs stuck on.

   So it shows PROGRESS instead, which is true at any polling rate:
   everything before the counter is done, the one at the counter is the
   lamp lit right now. The real test is what you see on the panel; this
   only tells you how far along it is. */
function paintLamps(data) {
  const lamps = document.querySelectorAll('.lamp');

  if (!data.name || !data.name.startsWith('panel')) return;

  // Rebuilt from scratch every tick, so nothing can accumulate.
  lamps.forEach(el => el.classList.remove('on', 'hit', 'miss', 'done'));

  if (data.name === 'panel-leds') {
    lamps.forEach(el => {
      const id = Number(el.dataset.lamp);

      if (data.state !== 'running') {
        el.classList.add('done');           // the sweep finished
      } else if (id < data.finished) {
        el.classList.add('done');
      } else if (id === data.finished) {
        el.classList.add('on');
      }
    });
    return;
  }

  // The button test: one row per position, plus anything pressed early.
  (data.results || []).forEach(r => {
    if (r.panel === undefined) return;
    const el = document.querySelector(`.lamp[data-lamp="${r.panel}"]`);
    if (el) el.classList.add(r.result === 'OK' ? 'hit' : 'miss');
  });

  (data.pressed || []).forEach(id => {
    const el = document.querySelector(`.lamp[data-lamp="${id}"]`);
    if (el && !el.classList.contains('miss')) el.classList.add('hit');
  });

  if (data.state === 'running') {
    const el = document.querySelector(`.lamp[data-lamp="${data.finished}"]`);
    if (el) el.classList.add('on');
  }
}

function paintResults(data) {
  const rows = data.results || [];

  if (!rows.length || data.state === 'running') {
    resultsEl.hidden = rows.length === 0;
    if (!rows.length) return;
  }

  const isPump = rows[0].pump !== undefined;
  const head = isPump
    ? ['Bơm', 'Nguyên liệu', 'Kết quả', 'Gram', 'Giây', 'Ghi chú']
    : ['Vị trí', 'Kết quả'];

  document.getElementById('resultsHead').innerHTML =
    head.map(h => `<th>${h}</th>`).join('');

  document.getElementById('resultsBody').innerHTML = rows.map(r => {
    const cls = (r.result === 'PRIMED' || r.result === 'OK') ? 'ok'
      : r.result === 'PARTIAL' ? 'part' : 'bad';
    return isPump
      ? `<tr><td>${r.pump}</td><td>${esc(r.name)}</td>` +
        `<td class="${cls}">${esc(r.result)}</td>` +
        `<td>${(r.gram ?? 0).toFixed(1)}</td>` +
        `<td>${(r.seconds ?? 0).toFixed(1)}</td>` +
        `<td>${esc(r.note || '')}</td></tr>`
      : `<tr><td>${r.panel}</td><td class="${cls}">${esc(r.result)}</td></tr>`;
  }).join('');

  resultsEl.hidden = false;
}

const esc = s => String(s ?? '').replace(/[&<>"]/g,
  c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

function setEnabled(on) {
  document.querySelectorAll('.pump, .primary, .secondary, .ghost')
    .forEach(b => { b.disabled = !on; });
}

/* ---------------- PANEL BUTTON 15: LEAVE AGAIN ----------------
   The same flag that brought this page up sends it back when the button is
   pressed a second time. Polled on the same tick as the job status.

   Where "back" is: the store screen appended ?back=<its own URL>, which is
   right for whatever address it was itself reached on. Without it there is
   nothing to guess -- this server's own origin is the test screen, not the
   store -- so the page simply stays put and says so. */
const TEST_MODE_URL = '../test_gui/mode.json';

let modeReady = false;
let modeSeen = null;

function storeScreenUrl(){
  return new URLSearchParams(location.search).get('back') || '';
}

async function pollMode(){
  let data = null;

  try{
    const response = await fetch(TEST_MODE_URL, {cache:'no-store'});
    if(response.ok) data = await response.json();
  }catch(error){
    return;
  }

  const id = (data && data.id) ? data.id : null;

  if(!modeReady){
    modeReady = true;
    modeSeen = id;
    return;
  }

  if(id === null || id === modeSeen) return;

  modeSeen = id;
  if(data.open) return;          // still wanted; nothing to do

  const back = storeScreenUrl();

  if(!back){
    note('Nút bảng đã tắt chế độ test, nhưng trang này không biết quay về '
       + 'đâu (mở từ màn hình bán hàng để có đường về).');
    return;
  }

  console.log('[test] panel button -> ' + back);
  window.location.href = back;
}

poll();
pollMode();
setInterval(() => { poll(); pollMode(); }, POLL_MS);
