/* ================================================================
   ADMIN-05 · RECYCLE BIN
   Drinks removed from the menu, and the two things you can do with
   them. Deleting is reversible everywhere else in this console; this
   is the one page where it stops being.
   ================================================================ */
if (!AdminAuth.initPage('bin')) throw new Error('redirecting to login');

const $ = id => document.getElementById(id);
const BIN_URL = '../api/drink/bin';

const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g,
  c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);
const money = v => '$' + Number(v || 0).toFixed(2);

async function load() {
  const button = $('reloadBtn');
  button.disabled = true;

  try {
    const response = await fetch(BIN_URL, {
      cache: 'no-store',
      headers: { Authorization: 'Bearer ' + AdminAuth.token() },
    });

    if (response.status === 401) { AdminAuth.logout(); return; }

    const result = await response.json().catch(() => ({}));
    if (!response.ok || !result.ok) {
      throw new Error(result.error || 'Không tải được thùng rác.');
    }
    render(result.drinks || []);
  } catch (error) {
    showToast('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M10.3 3.9 1.8 18.1A2 2 0 0 0 3.5 21h17a2 2 0 0 0 1.7-2.9L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/></svg> ' + error.message, 'warn');
  } finally {
    button.disabled = false;
  }
}

function render(drinks) {
  $('binSub').textContent = drinks.length
    ? `${drinks.length} món`
    : 'Trống — chưa xóa món nào.';

  const list = $('binList');

  if (!drinks.length) {
    list.innerHTML = `<div class="orderempty">Thùng rác đang trống.</div>`;
    return;
  }

  list.innerHTML = drinks.map(d => `
    <div class="orderrow binrow" data-id="${d.id}">
      <div class="thumb">${d.image
        ? `<img src="${escapeHtml(d.image)}" alt="" loading="lazy">`
        : d.emoji}</div>
      <div>
        <div class="oname">${escapeHtml(d.name)}</div>
        <div class="ometa">
          ${money(d.price)} · ${d.recipeRows} dòng công thức${
            d.sold ? ` · đã bán ${d.sold} ly` : ''}
        </div>
      </div>
      <div class="otime">Xóa lúc ${escapeHtml(d.deletedAt || '—')}</div>
      <div class="binacts">
        <button class="btn ghost compact" data-restore="${d.id}">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 3v6h6"/></svg> Khôi phục
        </button>
        <button class="btn danger compact" data-purge="${d.id}">
          Xóa hẳn
        </button>
      </div>
    </div>`).join('');

  list.querySelectorAll('[data-restore]').forEach(el => {
    el.onclick = () => act(el, 'restore', Number(el.dataset.restore), drinks);
  });
  list.querySelectorAll('[data-purge]').forEach(el => {
    el.onclick = () => act(el, 'purge', Number(el.dataset.purge), drinks);
  });
}

async function act(button, kind, id, drinks) {
  const drink = drinks.find(d => d.id === id) || { name: '?' };

  // Only the destructive one asks. Restoring is safe and reversible --
  // making both confirm would teach people to click through the dialog
  // that matters.
  if (kind === 'purge') {
    const ok = confirm(
      `Xóa hẳn "${drink.name}"?\n\n` +
      `• Công thức (${drink.recipeRows} dòng) sẽ mất vĩnh viễn.\n` +
      `• Lịch sử bán hàng vẫn được giữ.\n\n` +
      `Không thể hoàn tác.`);
    if (!ok) return;
  }

  button.disabled = true;

  try {
    const result = kind === 'restore'
      ? await MenuStore.restoreDrink(id)
      : await MenuStore.purgeDrink(id);

    showToast(kind === 'restore'
      ? `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 3v6h6"/></svg> Đã khôi phục <b>${escapeHtml(result.name)}</b> — vào Quản lý Menu để mở bán lại`
      : `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M3 6h18"/><path d="M8 6V4.5A1.5 1.5 0 0 1 9.5 3h5A1.5 1.5 0 0 1 16 4.5V6"/><path d="M5.5 6l1 13.2A2 2 0 0 0 8.5 21h7a2 2 0 0 0 2-1.8L18.5 6"/><path d="M10 11v5M14 11v5"/></svg> Đã xóa hẳn <b>${escapeHtml(result.name)}</b>`,
      kind === 'restore' ? 'ok' : 'warn');
    load();
  } catch (error) {
    showToast('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M10.3 3.9 1.8 18.1A2 2 0 0 0 3.5 21h17a2 2 0 0 0 1.7-2.9L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/></svg> ' + error.message, 'warn');
    button.disabled = false;
  }
}

$('reloadBtn').onclick = load;
load();
