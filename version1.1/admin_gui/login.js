/* ================================================================
   ADMIN-01 · LOGIN
   The password is checked by the server, not here. admin_gui/auth.py
   holds a PBKDF2 hash and hands back a signed session token, which
   every admin request then carries. Nothing in this file decides who
   gets in -- it collects two fields and reports what the server said.
   ================================================================ */
const LOGIN_URL = '../api/admin/login';

const form   = document.getElementById('loginForm');
const errBox = document.getElementById('loginErr');
const errMsg = document.getElementById('loginErrMsg');
const btn    = document.getElementById('loginBtn');

/* Trang đầu tiên mà server cấp cho tài khoản này, theo đúng thứ tự thanh
   bên. Trả về '' khi máy chủ không gửi danh sách (bản backend cũ), để nơi
   gọi lùi về cách đoán theo vai trò. */
function landingPage(pages) {
  if (!Array.isArray(pages) || !pages.length) return '';
  const order = (window.AdminAuth && AdminAuth.NAV_ORDER) || [];
  const first = order.find(n => pages.includes(n.page));
  return first ? first.href : '';
}

function showErr(msg) {
  errMsg.textContent = msg;
  errBox.classList.add('show');
  form.animate(
    [{ transform: 'translateX(0)' }, { transform: 'translateX(-8px)' }, { transform: 'translateX(8px)' }, { transform: 'translateX(0)' }],
    { duration: 260, easing: 'ease-in-out' }
  );
}

// show / hide password
document.getElementById('eye').onclick = () => {
  const p = document.getElementById('p');
  p.type = p.type === 'password' ? 'text' : 'password';
};

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  errBox.classList.remove('show');
  const u = document.getElementById('u').value.trim();
  const p = document.getElementById('p').value;
  if (!u || !p) { showErr('Vui lòng nhập đủ tên đăng nhập và mật khẩu.'); return; }

  const idle = btn.innerHTML;
  btn.disabled = true;
  btn.textContent = 'Đang kiểm tra…';

  let result = {};
  let status = 0;
  try {
    const response = await fetch(LOGIN_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user: u, password: p }),
    });
    status = response.status;
    result = await response.json().catch(() => ({}));
    if (!response.ok) result.ok = false;
  } catch {
    result = { ok: false, error: 'Không kết nối được máy chủ.' };
  }

  btn.disabled = false;
  btn.innerHTML = idle;

  if (result.ok && result.token) {
    // The token IS the session. Nothing else in this browser decides
    // anything -- the server re-checks it, and re-reads the role from the
    // account row, on every request.
    // Only what the server actually said. An older backend sends no role
    // at all, and writing `undefined` into the session would be this
    // browser inventing one -- admin-guard.js reads a missing role as
    // "not known yet" and shows everything, which is the safe direction.
    const extra = {};
    if (result.role) {
      extra.role = result.role;
      extra.role_label = result.role_label || '';
      extra.display_name = result.display_name || '';
    }
    // The page list the server just computed for THIS account. Kept so
    // admin-guard.js can draw the rail correctly on its very first paint
    // instead of guessing from the role's name -- see the note above
    // pagesFor() there for what that guessing cost.
    if (Array.isArray(result.pages) && result.pages.length) {
      extra.pages = result.pages;
    }
    AdminAuth.setSession(result.user || u.toLowerCase(), result.token,
                         result.expires, extra);
    // Where to land is read from that same list, in the rail's own order,
    // rather than from the role's name. A shop that edits what `staff` may
    // reach (Người dùng page) would otherwise be sent to a screen that
    // bounces them straight back -- and no constant in this file could
    // have predicted that edit.
    location.replace(landingPage(result.pages) ||
                     (result.role === 'staff' ? 'refill.html' : 'menu.html'));
    return;
  }

  showErr(result.error ||
    (status === 404
      ? 'Máy chủ chưa có API đăng nhập — khởi động lại store_gui/serve.py.'
      : 'Sai tên đăng nhập hoặc mật khẩu.'));
});
