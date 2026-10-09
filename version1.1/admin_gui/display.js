/* ================================================================
   ADMIN · MÀN HÌNH
   The resolution the customer panel runs at, and the only setting in
   this console that changes how the shop screen FEELS rather than what
   it says.

   WHY IT IS WORTH A PAGE
     The Pi's GPU composites every frame of a scroll, and that cost is
     close to linear in pixel count. Measured on this machine on
     2026-09-09: at 1920x1200 a swipe down the menu stutters, at 1280x800
     the same swipe is smooth, with no change to the page at all. The
     photographs had already been shrunk and made no difference, because
     decoding was never the bottleneck.

   WHY IT DOES NOT JUST APPLY AND SAVE
     The panel has no keyboard and no mouse. A mode it cannot display is
     a black screen nobody in the shop can undo, and the machine sells
     nothing until somebody arrives with a monitor. So a change is
     applied on probation: the server starts a timer, this page counts it
     down, and only "Giữ chế độ này" makes it permanent. Saying nothing
     reverts -- the correct default, because the most likely reason for
     saying nothing is that there is nothing to read.

     The timer lives on the SERVER, not here. Closing the tab, losing
     wifi, or the phone going to sleep must not be able to strand the
     shop on an unreadable screen.

   THIS PAGE DOES NOT LOAD menu-store.js
     That module pulls the whole drink list on include. Nothing here
     needs it, and a settings page should not wait on the database to
     tell somebody what their screen is doing.
   ================================================================ */
if (!AdminAuth.initPage('display')) { /* redirected to login */ }

const $ = (id) => document.getElementById(id);

let STATE = null;      // last /api/display payload
let PICKED = null;     // the mode the operator has selected, before applying
let TICKER = 0;        // countdown interval id

/* Every request carries the token the server issued at login, the same
   way menu-store.js does it. Kept local rather than borrowed so this
   page has no dependency on that module. */
async function api(path, options) {
  let response;

  const settings = { ...(options || {}) };
  settings.headers = {
    ...(settings.headers || {}),
    Authorization: 'Bearer ' + AdminAuth.token(),
  };

  try {
    response = await fetch(path, settings);
  } catch (error) {
    throw new Error('Không kết nối được máy chủ.');
  }

  const result = await response.json().catch(() => ({}));

  if (response.status === 401) {
    AdminAuth.logout();
    throw new Error(result.error || 'Phiên đăng nhập đã hết hạn.');
  }

  if (!response.ok || !result.ok) {
    throw new Error(result.error || `Máy chủ trả lỗi ${response.status}.`);
  }

  return result;
}

/* The four modes this shop actually chooses between.

   xrandr reports twenty-two, down to 640x350, and a wall of them is a
   worse page than a short list: they are mostly duplicates of each other
   at odd aspect ratios, and nobody picking a kiosk resolution wants to
   compare 1360x768 with 1366x768. These four are one clean 16:9 ladder,
   each roughly a step apart in how much work the GPU does per frame:

       1920x1080   2,073,600 px
       1600x900    1,440,000 px    1.6x lighter than the panel's own mode
       1280x720      921,600 px    2.5x
       1024x768      786,432 px    2.9x

   Anything here that the panel turns out not to accept is dropped rather
   than shown and refused -- the list is a preference, xrandr is the
   authority. Widening it back out is one line. */
const OFFERED = ['1920x1080', '1600x900', '1280x720', '1024x768'];

function offered(modes) {
  return modes
    .filter(m => OFFERED.includes(m.name))
    .sort((a, b) => b.pixels - a.pixels);
}

function paint() {
  if (!STATE) return;

  const { output, current, saved, modes } = STATE;
  const list = offered(modes);

  $('chip').textContent = output ? `${output} · ${current}` : 'Không thấy màn hình';
  $('csub').textContent = saved
    ? `Đã lưu: ${saved} · tự áp lại mỗi lần khởi động máy`
    : 'Chưa lưu lựa chọn nào — máy đang dùng chế độ mặc định của màn hình';

  const box = $('modes');
  box.textContent = '';

  for (const row of list) {
    const card = document.createElement('button');
    card.type = 'button';
    card.className = 'mode' + ((PICKED || current) === row.name ? ' active' : '');
    card.dataset.mode = row.name;

    const tags = [];
    if (row.name === current) tags.push('<span class="tag live">đang chạy</span>');
    if (row.preferred) tags.push('<span class="tag native">gốc màn hình</span>');
    if (row.name === saved) tags.push('<span class="tag saved">đã lưu</span>');

    // "1.6x nhẹ hơn" is the number that actually predicts smoothness --
    // the pixel count is only how it is arrived at.
    const lighter = row.lighter > 1.01
      ? `nhẹ hơn <b>${row.lighter.toFixed(2)}×</b>`
      : 'nhiều việc nhất';

    card.innerHTML = `
      <div class="check">${(PICKED || current) === row.name ? '&#10003;' : ''}</div>
      <div class="tagrow">${tags.join('')}</div>
      <div class="mname">${row.width}×${row.height}</div>
      <div class="mdesc">${row.pixels.toLocaleString('vi-VN')} điểm ảnh<br>${lighter}</div>`;

    card.onclick = () => { PICKED = row.name; paint(); apply(row.name); };
    box.appendChild(card);
  }
}

/* ---------------- PROBATION ---------------- */

function showRevert(seconds) {
  const banner = $('revert');
  banner.classList.remove('gone');

  let left = seconds;
  $('rcount').textContent = left;
  clearInterval(TICKER);

  TICKER = setInterval(() => {
    left -= 1;
    $('rcount').textContent = Math.max(0, left);

    if (left <= 0) {
      clearInterval(TICKER);
      hideRevert();
      // The server has already put the old mode back on its own timer.
      // Re-reading is how this page finds out what actually happened
      // rather than assuming it.
      showToast('Đã tự quay lại chế độ cũ vì không có xác nhận.', 'warn');
      load();
    }
  }, 1000);
}

function hideRevert() {
  clearInterval(TICKER);
  TICKER = 0;
  $('revert').classList.add('gone');
}

async function apply(mode) {
  try {
    const result = await api('/api/display/apply', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode }),
    });

    showRevert(result.revertSeconds);
  } catch (error) {
    PICKED = null;
    showToast(error.message, 'warn');
    load();
  }
}

$('keep').onclick = async () => {
  try {
    await api('/api/display/keep', { method: 'POST' });
    hideRevert();
    PICKED = null;
    showToast('Đã lưu. Chế độ này sẽ tự áp lại mỗi lần khởi động máy.');
    load();
  } catch (error) {
    showToast(error.message, 'warn');
  }
};

/* Re-applying the mode the panel was on before is exactly what the
   server's timer would have done; doing it by hand only makes it happen
   now instead of in fifteen seconds' time. */
$('undo').onclick = async () => {
  if (!STATE) return;

  try {
    await api('/api/display/apply', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: STATE.saved }),
    });
    await api('/api/display/keep', { method: 'POST' });
    hideRevert();
    PICKED = null;
    showToast('Đã quay lại chế độ cũ.');
    load();
  } catch (error) {
    showToast(error.message, 'warn');
    load();
  }
};

async function load() {
  try {
    STATE = await api('/api/display');
    paint();
  } catch (error) {
    $('csub').textContent = error.message;
    showToast(error.message, 'warn');
  }
}

load();
