/* ================================================================
   ADMIN-10 · NGƯỜI DÙNG
   Accounts for the console: who exists, what role they hold, and the
   two things that actually get done -- adding somebody, and resetting
   a password.

   NOTHING ON THIS PAGE GRANTS ANYTHING.
     Every button here is a request the server may refuse, and it decides
     from the account row, not from anything sent with the click. The
     table below is a view of that state and a set of ways to ask for it
     to change -- the refusals it renders are the server's sentences, not
     rules re-implemented here.

   WHY THE PAGE ITSELF IS NOT THE GATE
     admin-guard.js hides this page from a role that may not use it, and
     that is courtesy: it saves somebody clicking into a screen that
     would only refuse them. Anyone who reaches the URL anyway gets a
     table full of 403s, which is the correct outcome and the reason the
     hiding is allowed to be only courtesy.
   ================================================================ */
if (!AdminAuth.initPage('users')) throw new Error('redirecting to login');

const $ = id => document.getElementById(id);

const USERS_URL       = '../api/users';
const USER_SAVE_URL   = '../api/user/save';
const USER_PW_URL     = '../api/user/password';
const USER_ROLE_URL   = '../api/user/role';
const USER_ACTIVE_URL = '../api/user/active';
const USER_DELETE_URL = '../api/user/delete';
const MY_PW_URL       = '../api/admin/password';

const esc = value => String(value ?? '').replace(/[&<>"']/g, c =>
  ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' })[c]);

const time = value => value ? esc(String(value).slice(0, 16)) : '—';

const PERMISSIONS_URL      = '../api/permissions';
const PERMISSIONS_SAVE_URL = '../api/permissions/save';

let roles = [];
let minPassword = 8;
let meId = null;
let lastRows = [];

const rowOf = id => lastRows.find(r => r.user_id === Number(id));

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
    // The status travels with the error. A 404 here is not "you did
    // something wrong", it is "this backend predates the endpoint", and
    // only the caller knows how to say that usefully.
    const error = new Error(result.error || 'Không thực hiện được.');
    error.status = response.status;
    throw error;
  }

  return result;
}

const post = (url, body) =>
  api(url, { method: 'POST', body: JSON.stringify(body) });

/* ---------- the permission grid ---------- */
/* Drawn from the server, never from a copy kept here.

   The page used to carry its own hand-written table of who-can-do-what,
   which had to be remembered every time the rules changed -- and a table
   that has to be remembered is a table that is eventually wrong while
   looking authoritative. This asks. */
const ROLE_ORDER = ['owner', 'manager', 'staff'];

let matrix = null;

function renderRoles(data) {
  matrix = data;

  $('roleBody').innerHTML = data.areas.map(area => {
    const cells = ROLE_ORDER.map(role => {
      const held = data.roles[role].areas.includes(area.id);
      const locked = data.roles[role].locked.includes(area.id);

      return `<td>
        <label class="permbox${locked ? ' is-locked' : ''}"
               title="${locked
                 ? 'Bắt buộc — bỏ đi thì không còn ai sửa được phân quyền'
                 : esc(area.label) + ' cho ' + esc(role)}">
          <input type="checkbox" data-role="${role}" data-area="${esc(area.id)}"
                 ${held ? 'checked' : ''} ${locked ? 'disabled' : ''}>
        </label></td>`;
    }).join('');

    // The pages each area unlocks, so a tick is a decision about screens
    // rather than about a word like "catalogue".
    const pages = area.pages.length
      ? `<div class="permpages">${esc(area.pages.join(' · '))}</div>` : '';

    return `<tr><td><b>${esc(area.label)}</b>${pages}</td>${cells}</tr>`;
  }).join('');

  // Say which roles are no longer at their defaults, so "why can staff do
  // that" has an answer on the same screen.
  const changed = ROLE_ORDER.filter(r => data.roles[r].customised);
  const note = $('permNote');
  const old = note.querySelector('.permchanged');
  if (old) old.remove();
  if (changed.length) {
    const line = document.createElement('span');
    line.className = 'permchanged';
    line.innerHTML = '<br>Đã tuỳ chỉnh (khác mặc định): <b>' +
      changed.map(r => esc(ROLE_VI[r] || r)).join(', ') + '</b>';
    note.appendChild(line);
  }
}

const ROLE_VI = { owner: 'Chủ', manager: 'Quản lý', staff: 'Nhân viên' };

/* An empty grid with a toast that fades after two seconds is how this
   page tells somebody nothing at all -- the same silent-failure shape the
   sidebar had. Whatever went wrong gets written INTO the table and stays
   there until it is fixed. */
function permissionsUnavailable(reason, hint) {
  matrix = null;
  $('permReset').disabled = true;
  $('roleBody').innerHTML = `
    <tr><td colspan="4" class="permfail">
      <b>Không tải được phân quyền.</b> ${esc(reason)}
      ${hint ? `<div class="permfail-hint">${hint}</div>` : ''}
    </td></tr>`;
}

async function loadPermissions() {
  try {
    const data = await api(PERMISSIONS_URL);
    $('permReset').disabled = false;
    renderRoles(data);
  } catch (error) {
    if (String(error.message) === '401') return;

    if (error.status === 404) {
      permissionsUnavailable(
        'Máy chủ đang chạy bản cũ — chưa có endpoint /api/permissions.',
        'Khởi động lại <b>main.py</b> rồi tải lại trang. Phân quyền vẫn ' +
        'đang chạy theo mặc định trong mã nguồn, không có gì hỏng.');
      return;
    }

    permissionsUnavailable(error.message,
      'Thử tải lại trang. Nếu vẫn vậy, xem log của máy chủ.');
  }
}

/* One role per save, not the whole grid.

   Two owners with this page open would otherwise undo each other: the
   second save would carry a form read before the first, and silently put
   back a right that had just been taken away. A save that names one role
   and one set of areas cannot do that to the others. */
$('roleBody').addEventListener('change', async event => {
  const box = event.target.closest('input[type=checkbox][data-role]');
  if (!box || !matrix) return;

  const role = box.dataset.role;
  const wanted = [...$('roleBody')
    .querySelectorAll(`input[data-role="${role}"]`)]
    .filter(el => el.checked)
    .map(el => el.dataset.area);

  const boxes = [...$('roleBody').querySelectorAll('input[data-role]')];
  boxes.forEach(el => { el.disabled = true; });

  try {
    const saved = await post(PERMISSIONS_SAVE_URL, { role, areas: wanted });
    matrix.roles[role].areas = saved.areas;
    matrix.roles[role].customised = true;
    renderRoles(matrix);
    showToast(`Đã lưu quyền cho <b>${esc(ROLE_VI[role] || role)}</b>.`, 'ok');
  } catch (error) {
    // Redraw from the server rather than from what was clicked: a
    // refused change must not leave a tick sitting there claiming it
    // worked.
    await loadPermissions();
    if (String(error.message) !== '401') showToast(esc(error.message), 'warn');
  }
});

$('permReset').onclick = () => matrix && askConfirm(
  'Về mặc định',
  `Xoá mọi tuỳ chỉnh phân quyền: Chủ, Quản lý và Nhân viên trở về đúng bộ
   quyền mặc định trong mã nguồn. Tài khoản và mật khẩu không bị ảnh hưởng.`,
  async () => {
    for (const role of ROLE_ORDER) {
      await post(PERMISSIONS_SAVE_URL,
                 { role, areas: matrix.defaults[role] });
    }
    await loadPermissions();
  });

/* One row's buttons.

   An owner other than yourself gets none of the three. The server
   refuses those anyway -- see _refuse_acting_on_peer() -- and a button
   whose only outcome is a red toast is worse than no button: it reads as
   a thing that is broken rather than a thing that is deliberate. The
   reason is written in the cell instead. */
function actions(row) {
  const isMe = row.user_id === meId;
  const isPeerOwner = row.role === 'owner' && !isMe;

  if (isPeerOwner) {
    return '<span class="dim nowrap" title="Đổi tài khoản Chủ khác bằng lệnh trên máy: python3 -m admin_gui.auth">— dùng lệnh trên máy</span>';
  }

  const bits = [
    `<button type="button" class="btn ghost compact" data-pw="${row.user_id}">Đổi mật khẩu</button>`,
  ];

  // Your own row: the three below would each take away the console you
  // are standing in. The server refuses them; not drawing them saves the
  // press. "Đổi mật khẩu của tôi" in the topbar is the one that is yours.
  if (!isMe) {
    bits.push(
      `<button type="button" class="btn ghost compact" data-role="${row.user_id}">Đổi vai trò</button>`,
      `<button type="button" class="btn ghost compact" data-active="${row.user_id}">${
        row.active ? 'Khoá' : 'Mở khoá'}</button>`,
      `<button type="button" class="btn danger compact" data-del="${row.user_id}">Xoá</button>`);
  } else {
    bits.push('<span class="dim">(tài khoản của bạn)</span>');
  }

  return `<div class="rowacts">${bits.join('')}</div>`;
}

function render(data) {
  roles = data.roles || [];
  minPassword = data.min_password || 8;
  meId = data.me;

  // Kept so a row's button can find the account it belongs to without
  // reading the table's own HTML back out.
  lastRows = data.users || [];

  const rows = lastRows;
  $('countNote').textContent = `${rows.length} tài khoản`;

  $('userBody').innerHTML = rows.map(row => `
    <tr class="${row.active ? '' : 'is-off'}">
      <td class="mono"><b>${esc(row.username)}</b></td>
      <td>${esc(row.display_name) || '<span class="dim">—</span>'}</td>
      <td><span class="tag tag-${esc(row.role)}">${esc(row.role_label)}</span></td>
      <td>${row.active
        ? '<span class="ok-mark">Đang hoạt động</span>'
        : '<span class="dim">Đã khoá</span>'}</td>
      <td class="mono nowrap dim">${time(row.last_login_at)}</td>
      <td class="mono nowrap dim">${time(row.created_at)}</td>
      <td>${actions(row)}</td>
    </tr>`).join('');

  $('emptyNote').hidden = rows.length > 0;
}

const load = async () => {
  try {
    render(await api(USERS_URL));
  } catch (error) {
    if (String(error.message) === '401') return;
    $('userBody').innerHTML = '';
    $('emptyNote').hidden = false;
    $('emptyNote').textContent = error.message;
  }
};

/* ---------- the form ---------- */
/* One modal for four jobs -- add, reset somebody's password, change your
   own, change a role -- because they are the same shape: a short form and
   one button. `mode` says which fields are on it and what Save posts. */
let mode = null;
let target = null;

function closeUser() {
  $('userOverlay').classList.remove('show');
  mode = null;
  target = null;
}

function formError(text) {
  const box = $('fError');
  if (!box) return;
  box.textContent = text || '';
  box.style.display = text ? 'block' : 'none';
}

function roleOptions(current) {
  return roles.map(r =>
    `<option value="${esc(r.id)}" ${r.id === current ? 'selected' : ''}>${
      esc(r.label)} (${esc(r.id)})</option>`).join('');
}

function openUser(nextMode, row) {
  mode = nextMode;
  target = row || null;
  $('userOverlay').classList.add('show');

  const forms = {
    add: {
      title: 'Thêm người dùng',
      sub: 'Tài khoản mới đăng nhập được ngay. Vai trò quyết định trang nào hiện ra.',
      save: 'Tạo tài khoản',
      body: `
        <div class="mfield">
          <label>Tên đăng nhập</label>
          <input id="fUser" maxlength="32" autocomplete="off" spellcheck="false"
                 placeholder="vd. an.nguyen">
        </div>
        <div class="mfield">
          <label>Tên hiển thị <span class="dim">(không bắt buộc)</span></label>
          <input id="fDisplay" maxlength="64" autocomplete="off"
                 placeholder="vd. Nguyễn Văn An">
        </div>
        <div class="mrow">
          <div class="mfield">
            <label>Vai trò</label>
            <select id="fRole">${roleOptions('staff')}</select>
          </div>
          <div class="mfield">
            <label>Mật khẩu</label>
            <input type="password" id="fPass" autocomplete="new-password">
          </div>
        </div>
        <div class="mnote">
          Tên đăng nhập chỉ gồm chữ thường, số, dấu chấm, gạch ngang hoặc
          gạch dưới. Mật khẩu tối thiểu <b>${minPassword}</b> ký tự.
        </div>`,
    },
    password: {
      title: 'Đổi mật khẩu',
      sub: row ? `Đặt mật khẩu mới cho <b>${esc(row.username)}</b>.` : '',
      save: 'Đổi mật khẩu',
      body: `
        <div class="mfield">
          <label>Mật khẩu mới</label>
          <input type="password" id="fPass" autocomplete="new-password">
        </div>
        <div class="mnote">
          Tối thiểu <b>${minPassword}</b> ký tự. Mọi phiên đang mở của tài
          khoản này sẽ bị đăng xuất ngay — đó là mục đích: mật khẩu được đổi
          thường vì có người khác biết nó.
        </div>`,
    },
    mypassword: {
      title: 'Đổi mật khẩu của tôi',
      sub: 'Cần mật khẩu hiện tại, kể cả khi bạn đang đăng nhập.',
      save: 'Đổi mật khẩu',
      body: `
        <div class="mfield">
          <label>Mật khẩu hiện tại</label>
          <input type="password" id="fCurrent" autocomplete="current-password">
        </div>
        <div class="mfield">
          <label>Mật khẩu mới</label>
          <input type="password" id="fPass" autocomplete="new-password">
        </div>
        <div class="mnote">
          Phiên đăng nhập hiện tại cũng sẽ kết thúc, nên bạn sẽ phải đăng
          nhập lại bằng mật khẩu mới.
        </div>`,
    },
    role: {
      title: 'Đổi vai trò',
      sub: row ? `<b>${esc(row.username)}</b> đang là ${esc(row.role_label)}.` : '',
      save: 'Đổi vai trò',
      body: `
        <div class="mfield">
          <label>Vai trò mới</label>
          <select id="fRole">${roleOptions(row && row.role)}</select>
        </div>
        <div class="mnote">
          Có hiệu lực ngay ở lần bấm tiếp theo của họ — không cần đăng nhập lại.
        </div>`,
    },
  };

  const form = forms[nextMode];

  $('userModal').innerHTML = `
    <h3>${esc(form.title)}</h3>
    <div class="msub">${form.sub}</div>
    ${form.body}
    <div class="editor-error" id="fError" style="display:none"></div>
    <div class="modal-acts">
      <button class="btn ghost" id="fCancel">Hủy</button>
      <button class="btn primary" id="fSave">${esc(form.save)}</button>
    </div>`;

  $('fCancel').onclick = closeUser;
  $('fSave').onclick = submit;

  const first = $('fUser') || $('fCurrent') || $('fPass') || $('fRole');
  if (first) first.focus();
}

async function submit() {
  const button = $('fSave');
  const idle = button.textContent;
  button.disabled = true;
  button.textContent = 'Đang lưu…';
  formError('');

  try {
    if (mode === 'add') {
      await post(USER_SAVE_URL, {
        username: $('fUser').value.trim(),
        display_name: $('fDisplay').value.trim(),
        role: $('fRole').value,
        password: $('fPass').value,
      });
      showToast('Đã tạo tài khoản.', 'ok');
    } else if (mode === 'password') {
      await post(USER_PW_URL, {
        user_id: target.user_id, password: $('fPass').value,
      });
      showToast('Đã đổi mật khẩu.', 'ok');
    } else if (mode === 'role') {
      await post(USER_ROLE_URL, {
        user_id: target.user_id, role: $('fRole').value,
      });
      showToast('Đã đổi vai trò.', 'ok');
    } else if (mode === 'mypassword') {
      await post(MY_PW_URL, {
        current_password: $('fCurrent').value,
        password: $('fPass').value,
      });
      // The change ended this session on purpose. Say so before the login
      // screen appears, or it reads as having been thrown out.
      closeUser();
      showToast('Đã đổi mật khẩu — vui lòng đăng nhập lại.', 'ok');
      setTimeout(() => AdminAuth.logout(), 1200);
      return;
    }

    closeUser();
    await load();
  } catch (error) {
    if (String(error.message) !== '401') formError(error.message);
  } finally {
    button.disabled = false;
    button.textContent = idle;
  }
}

/* ---------- confirming the two that cannot be undone ---------- */
let pending = null;

function askConfirm(title, detail, run) {
  pending = run;
  $('confirmModal').innerHTML = `
    <h3>${esc(title)}</h3>
    <div class="msub">${detail}</div>
    <div class="modal-acts">
      <button class="btn ghost" id="cNo">Hủy</button>
      <button class="btn danger" id="cYes">${esc(title)}</button>
    </div>`;
  $('confirmOverlay').classList.add('show');
  $('cNo').onclick = closeConfirm;
  $('cYes').onclick = async () => {
    const button = $('cYes');
    button.disabled = true;
    try {
      await pending();
      closeConfirm();
      await load();
    } catch (error) {
      closeConfirm();
      if (String(error.message) !== '401') showToast(esc(error.message), 'warn');
    }
  };
}

function closeConfirm() {
  pending = null;
  $('confirmOverlay').classList.remove('show');
}

/* ---------- wiring ---------- */
$('userBody').addEventListener('click', event => {
  const button = event.target.closest('button[data-pw],button[data-role],' +
                                      'button[data-active],button[data-del]');
  if (!button) return;

  if (button.dataset.pw) return openUser('password', rowOf(button.dataset.pw));
  if (button.dataset.role) return openUser('role', rowOf(button.dataset.role));

  if (button.dataset.active) {
    const row = rowOf(button.dataset.active);
    const on = !row.active;
    return askConfirm(
      on ? 'Mở khoá' : 'Khoá',
      on
        ? `Cho <b>${esc(row.username)}</b> đăng nhập lại.`
        : `<b>${esc(row.username)}</b> sẽ bị đăng xuất ngay và không đăng nhập
           được nữa. Tài khoản vẫn còn, nên các thay đổi họ từng làm vẫn đọc
           được tên.`,
      () => post(USER_ACTIVE_URL, { user_id: row.user_id, active: on }));
  }

  const row = rowOf(button.dataset.del);
  askConfirm('Xoá',
    `Xoá hẳn tài khoản <b>${esc(row.username)}</b>. Không khôi phục được —
     nếu chỉ muốn ngăn họ đăng nhập thì dùng <b>Khoá</b>.`,
    () => post(USER_DELETE_URL, { user_id: row.user_id }));
});

$('addBtn').onclick = () => openUser('add', null);
$('myPwBtn').onclick = () => openUser('mypassword', null);
$('userOverlay').onclick = e => { if (e.target.id === 'userOverlay') closeUser(); };
$('confirmOverlay').onclick = e => { if (e.target.id === 'confirmOverlay') closeConfirm(); };

loadPermissions();
load();
