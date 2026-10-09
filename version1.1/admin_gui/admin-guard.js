/* ================================================================
   ADMIN GUARD  —  session gate + shared shell (sidebar / topbar / toast)
   ----------------------------------------------------------------
   The session is a token the SERVER issued (admin_gui/auth.py), kept in
   sessionStorage so closing the tab ends it. What is here is only the
   carrying of it: the checks below decide which page to show, never who
   is allowed to do anything. That is decided on every request, by the
   server, from the signature on the token.
   ================================================================ */
(function (global) {
  const SESSION_KEY = 'tramrot_admin_session';

  const AdminAuth = {
    SESSION_KEY,
    getSession() {
      try { return JSON.parse(sessionStorage.getItem(SESSION_KEY)); }
      catch { return null; }
    },
    isLoggedIn() {
      const s = this.getSession();
      // An expired token would be refused by the server anyway; checking
      // here means the page goes to the login screen instead of painting
      // an empty table and then explaining itself in a toast.
      return !!(s && s.token && (!s.expires || s.expires * 1000 > Date.now()));
    },
    token() { const s = this.getSession(); return s && s.token; },
    role() { const s = this.getSession(); return (s && s.role) || ''; },
    /* The role is remembered only so the first paint has something to draw
       with. It is NOT what grants anything: the server re-reads it from the
       row on every request, and verifyAccess() below replaces whatever is
       here with the server's answer as soon as the page is up. */
    setSession(user, token, expires, extra) {
      // No role by default -- '' means "not known yet", which the rail
      // reads as "show everything and let the server refuse". Defaulting
      // to a real role here would be this browser deciding what somebody
      // is allowed to see, which is the one thing it must never do.
      const s = Object.assign(
        { user, role: '', role_label: '', display_name: '',
          token, expires, ts: Date.now() },
        extra || {});
      sessionStorage.setItem(SESSION_KEY, JSON.stringify(s));
      return s;
    },
    patchSession(fields) {
      const s = this.getSession();
      if (!s) return null;
      const next = Object.assign(s, fields);
      sessionStorage.setItem(SESSION_KEY, JSON.stringify(next));
      return next;
    },
    logout() {
      sessionStorage.removeItem(SESSION_KEY);
      location.replace('login.html');
    },
  };

  /* ---------- shared toast ---------- */
  global.showToast = function (msg, kind) {
    let t = document.querySelector('.toast');
    if (!t) { t = document.createElement('div'); t.className = 'toast'; document.body.appendChild(t); }
    t.className = 'toast ' + (kind || '');
    t.innerHTML = msg;
    // force reflow so re-triggering the transition works
    void t.offsetWidth;
    t.classList.add('show');
    clearTimeout(t._timer); clearTimeout(t._timer2);
    t._timer = setTimeout(() => {
      // biến mất tại chỗ (mờ dần) thay vì trượt lùi xuống lại
      t.classList.remove('show');
      t.classList.add('hide');
      t._timer2 = setTimeout(() => t.classList.remove('hide'), 260);
    }, 2200);
  };

  /* ---------- shared shell (sidebar + topbar mode chip) ---------- */
  /* Drawn icons, not emoji.

     These were characters from the OS emoji font, which meant the size,
     the weight and the COLOUR of every icon in the rail were decided by
     the device rather than by this app: a red warning triangle and a blue
     package sat beside each other in a rail whose text is one warm grey,
     and none of them could take currentColor -- so the active item's
     white-on-brand treatment stopped at the label and left a full-colour
     pictogram behind. */
  const ICO = paths =>
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
    'stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" ' +
    'aria-hidden="true" focusable="false">' + paths + '</svg>';

  const NAV = [
    { page: 'menu', href: 'menu.html', label: 'Quản lý Menu',
      ico: ICO('<path d="M6 8h12l-1.2 11.2a2 2 0 0 1-2 1.8H9.2a2 2 0 0 1-2-1.8Z"/><path d="M6.6 12.4h10.8"/><path d="M12 8V4.6"/><path d="M12 4.6c0-1 .9-1.8 2-1.8"/>') },
    // Sits under Quản lý Menu because it is the other half of the same
    // question: that page is WHAT the shop sells, this one is how it is
    // arranged on the screen the customer looks at.
    { page: 'home', href: 'home.html', label: 'Trình dựng Trang chủ',
      ico: ICO('<path d="M3.6 10.4 12 3.6l8.4 6.8"/><path d="M5.4 11.8V19a1.6 1.6 0 0 0 1.6 1.6h10a1.6 1.6 0 0 0 1.6-1.6v-7.2"/><path d="M9.2 20.6v-5.2h5.6v5.2"/>') },
    { page: 'ingredients', href: 'ingredients.html', label: 'Quản lý Nguyên liệu',
      ico: ICO('<path d="M9 3h6"/><path d="M10 3v5.2a2 2 0 0 1-.3 1L5.4 17a2 2 0 0 0 1.7 3h9.8a2 2 0 0 0 1.7-3l-4.3-7.8a2 2 0 0 1-.3-1V3"/><path d="M7.2 14h9.6"/>') },
    { page: 'refill', href: 'refill.html', label: 'Nạp kho',
      ico: ICO('<path d="M21 8v8.2a2 2 0 0 1-1 1.7l-7 4a2 2 0 0 1-2 0l-7-4a2 2 0 0 1-1-1.7V7.8a2 2 0 0 1 1-1.7l7-4a2 2 0 0 1 2 0L17 4.6"/><path d="m3.3 7.1 8.7 5 8.7-5"/><path d="M12 21.6V12"/>') },
    { page: 'mode', href: 'mode.html', label: 'Chế độ Vận hành',
      ico: ICO('<path d="M4 6h10M18 6h2M4 12h2M10 12h10M4 18h10M18 18h2"/><circle cx="16" cy="6" r="2"/><circle cx="8" cy="12" r="2"/><circle cx="16" cy="18" r="2"/>') },
    // Beside Chế độ Vận hành because both answer "how is this machine
    // set up to sell", rather than "what does the shop sell".
    { page: 'display', href: 'display.html', label: 'Màn hình',
      ico: ICO('<rect x="2.5" y="4" width="19" height="12.5" rx="2"/><path d="M8.5 20.5h7"/><path d="M12 16.5v4"/>') },
    { page: 'report', href: 'report.html', label: 'Báo cáo',
      ico: ICO('<path d="M3 21h18"/><rect x="4" y="12" width="4" height="7" rx="1"/><rect x="10" y="7" width="4" height="12" rx="1"/><rect x="16" y="9" width="4" height="10" rx="1"/>') },
    { page: 'tickets', href: 'tickets.html', label: 'Vé QR',
      ico: ICO('<rect x="3" y="4" width="7" height="7" rx="1.5"/><rect x="14" y="4" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><path d="M14 14h3.5v3.5H14z"/><path d="M21 14v3.5M14 21h3.5M21 21h-1.5"/>') },
    { page: 'errors', href: 'errors.html', label: 'Nhật ký lỗi',
      ico: ICO('<path d="M10.3 3.9 1.8 18.1A2 2 0 0 0 3.5 21h17a2 2 0 0 0 1.7-2.9L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/>') },
    { page: 'bin', href: 'bin.html', label: 'Thùng rác',
      ico: ICO('<path d="M3 6h18"/><path d="M8 6V4.5A1.5 1.5 0 0 1 9.5 3h5A1.5 1.5 0 0 1 16 4.5V6"/><path d="M5.5 6l1 13.2A2 2 0 0 0 8.5 21h7a2 2 0 0 0 2-1.8L18.5 6"/><path d="M10 11v5M14 11v5"/>') },
    // Last in the rail and in its own section: it is the only page that
    // is about the console rather than about the shop.
    { page: 'users', href: 'users.html', label: 'Người dùng', section: 'Hệ thống',
      ico: ICO('<path d="M16 20v-1.6a3.4 3.4 0 0 0-3.4-3.4H6.4A3.4 3.4 0 0 0 3 18.4V20"/><circle cx="9.5" cy="7.5" r="3.5"/><path d="M21 20v-1.6a3.4 3.4 0 0 0-2.6-3.3"/><path d="M15.5 4.2a3.4 3.4 0 0 1 0 6.6"/>') },
  ];

  const ROLE_LABEL = { owner: 'Chủ', manager: 'Quản lý', staff: 'Nhân viên' };

  const ALL_PAGES = NAV.map(n => n.page);

  /* THIS BROWSER DOES NOT KEEP A COPY OF THE PERMISSION MATRIX.
     It used to -- a FALLBACK_PAGES constant with one line per role, drawn
     on the first paint so the rail would not flicker while whoami was in
     flight. It drifted, exactly the way a second copy does: its `staff`
     list said `report`, the server's did not, so a staff console painted
     "Báo cáo" and removed it a moment later. Worse, the matrix is EDITABLE
     at runtime from the Người dùng page, so any constant here is wrong for
     every shop that has ever customised a role.

     The server now sends `pages` with the login response as well as from
     /api/admin/whoami, and setSession() keeps it. So the first paint uses
     what the server last said about THIS account, not what this file
     guessed about the role's name.

     AN UNKNOWN ACCOUNT STILL SHOWS EVERYTHING, NOT NOTHING.
     When there is no remembered list -- an older backend that sends none --
     the rail shows every item. Hiding is courtesy; the server refuses what
     a role may not reach on every single request. A rail that shows too
     much costs one clear 403; a rail that shows too little silently locks
     an owner out of their own console with nothing on screen to explain
     it, which is what happened when the backend predated whoami. */
  const pagesFor = (session, pages) =>
    (pages && pages.length ? pages : null) ||
    (session && session.pages && session.pages.length ? session.pages : null) ||
    ALL_PAGES;

  /* Only the pages this account may open. An item that would answer 403
     is worse than no item: it teaches people the console is broken. */
  function renderSidebar(active, session, pages) {
    const user = (session && session.user) || '';
    const role = (session && session.role) || '';
    const allowed = pagesFor(session, pages);
    const visible = NAV.filter(n => allowed.includes(n.page));

    const links = visible.map(n =>
      `${n.section ? `<div class="sechead">${n.section}</div>` : ''}
       <a href="${n.href}" class="${n.page === active ? 'active' : ''}">
         <span class="ico">${n.ico}</span> ${n.label}
       </a>`).join('');
    const initial = (user || 'M').charAt(0).toUpperCase();
    return `
      <div class="brand">
        <div class="logo">${ICO('<path d="M6 8h12l-1.2 11.2a2 2 0 0 1-2 1.8H9.2a2 2 0 0 1-2-1.8Z"/><path d="M6.6 12.4h10.8"/><path d="M12 8V4.6"/><path d="M12 4.6c0-1 .9-1.8 2-1.8"/>')}</div>
        <div>
          <div class="bt">TRẠM RÓT</div>
          <div class="bs">Admin Console</div>
        </div>
      </div>
      <nav class="nav">
        <div class="sechead">Vận hành</div>
        ${links}
      </nav>
      <div class="side-foot">
        <div class="userbox">
          <div class="av">${initial}</div>
          <div>
            <div class="un">${(session && session.display_name) || user || '—'}</div>
            <div class="ur">${(session && session.role_label) ||
                              ROLE_LABEL[role] || '<i>chưa rõ quyền</i>'}</div>
          </div>
        </div>
        <button class="logout" id="logoutBtn">${ICO('<path d="M15 17l5-5-5-5"/><path d="M20 12H9"/><path d="M12 20H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h6"/>')} Đăng xuất</button>
      </div>`;
  }

  function refreshModeChip() {
    const chip = document.getElementById('modeChip');
    if (!chip || !global.MenuStore) return;
    const m = MenuStore.modeInfo();
    chip.innerHTML = `<span class="dot"></span><span class="lbl">Chế độ:</span> ${m.emoji} Mode ${m.id} · ${m.short}`;
  }

  /* Called by every protected page. Guards the session, paints the shell,
     wires logout, keeps the mode chip live. */
  AdminAuth.initPage = function (active) {
    if (!AdminAuth.isLoggedIn()) { location.replace('login.html'); return false; }
    paintShell(active, AdminAuth.getSession(), null);
    refreshModeChip();
    if (global.MenuStore) MenuStore.onChange(refreshModeChip);
    // Deliberately not awaited: initPage() is called as `if (!initPage(...))`
    // by every page and turning it async would mean touching all of them.
    // The first paint uses the remembered role and this corrects it.
    verifyAccess(active);
    return true;
  };

  function paintShell(active, session, pages) {
    const mount = document.getElementById('sidebar-mount');
    if (!mount) return;
    mount.innerHTML = renderSidebar(active, session, pages);
    const lo = document.getElementById('logoutBtn');
    if (lo) lo.onclick = () => AdminAuth.logout();
  }

  /* Ask the server who this actually is.

     The role in sessionStorage was written at login and may be twelve
     hours old -- long enough for somebody to have been demoted, switched
     off or deleted. This is not the security boundary (every endpoint
     re-checks), it is what stops the console showing a rail full of
     pages that will now refuse the person looking at them. */
  async function verifyAccess(active) {
    let result = {};
    let status = 0;

    try {
      const response = await fetch('../api/admin/whoami', {
        cache: 'no-store',
        headers: { Authorization: 'Bearer ' + AdminAuth.token() },
      });
      status = response.status;
      result = await response.json().catch(() => ({}));
    } catch {
      // Offline or the server is restarting. Leave the page as it is:
      // throwing somebody out to a login screen they also cannot reach
      // helps nobody.
      return;
    }

    if (status === 401) { AdminAuth.logout(); return; }

    if (status === 404) {
      // The backend predates this endpoint. Said out loud, because the
      // symptom without it is a console that quietly looks like a
      // permissions problem: the rail is drawn from a role nobody could
      // confirm, and the person reads "you are not allowed" into what is
      // actually "the server has not been restarted".
      global.showToast(
        'Máy chủ đang chạy bản cũ — khởi động lại <b>main.py</b> để bật ' +
        'phân quyền.', 'warn');
      return;
    }

    if (!result.ok) {
      global.showToast(
        'Không xác định được quyền của tài khoản: ' +
        (result.error || 'máy chủ không trả lời.'), 'warn');
      return;
    }

    const pages = result.pages || [];

    // pages đi vào session cùng role: lần vẽ đầu của trang KẾ TIẾP đọc
    // chính câu trả lời này, nên không còn khoảnh khắc rail vẽ sai.
    AdminAuth.patchSession({
      user: result.user,
      role: result.role,
      role_label: result.role_label,
      display_name: result.display_name,
      pages: pages,
    });

    paintShell(active, AdminAuth.getSession(), pages);

    if (active && pages.length && !pages.includes(active)) {
      // Reached a page this role may not have -- an old bookmark, or a
      // demotion since the tab was opened. Sent somewhere they CAN use
      // rather than left on a screen whose every request will 403.
      const target = NAV.find(n => pages.includes(n.page));
      global.showToast(
        'Tài khoản của bạn không có quyền mở trang này.', 'warn');
      if (target) setTimeout(() => location.replace(target.href), 900);
    }
  }

  /* Thứ tự thanh bên, lộ ra để login.js chọn trang đích từ danh sách
     server cấp thay vì đoán theo tên vai trò. Chỉ page + href — phần icon
     không ai ngoài file này cần. */
  AdminAuth.NAV_ORDER = NAV.map(n => ({ page: n.page, href: n.href }));

  global.AdminAuth = AdminAuth;

  /* On the login page: if already authenticated, skip straight in. */
  if (document.body && document.body.dataset.page === 'login' && AdminAuth.isLoggedIn()) {
    location.replace('menu.html');
  }
})(window);
