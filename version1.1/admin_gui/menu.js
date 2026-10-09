/* ================================================================
   ADMIN-02 · MENU MANAGEMENT
   Availability, price, item metadata, and recipes are written through the
   API. MenuStore keeps a last-known browser cache for rendering and rollback.
   ================================================================ */
if (!AdminAuth.initPage('menu')) { /* redirected to login */ }

/* Tên món và câu lỗi đi vào innerHTML -- showToast() gán thẳng
   t.innerHTML = msg (admin-guard.js:62) -- nên phải escape. Cùng khuôn với
   bin.js / errors.js / report.js / tickets.js. */
const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, c =>
  ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' })[c]);


/* Ids are shown four digits wide, zero-padded: #0001, not #1.

   It is the width the machine already prints a SKU at -- `f"SKU {sku:04d}"`
   in order/qr_to_recipe.py and the same in the qrproto encoders -- so a
   drink's id reads identically on a printed label, in a machine log, and
   here. Matching those is the point: this column exists to be compared
   against them.

   Never truncated. An id past four digits simply gets wider; padding is
   for lining a column up, and a cut id is a different id. */
const id4 = value => String(value ?? '').padStart(4, '0');


let filterCat = 'all';
let query = '';

const $ = id => document.getElementById(id);

/* ---------- icons ----------
   Inline SVG, like everything else on these pages. The star in
   particular has to be two DIFFERENT SHAPES rather than two colours of
   the same one: this column is read by running an eye down forty rows,
   and a filled star against a hollow one separates at that speed where
   amber against grey does not. */
const ICON_STAR_ON =
  '<svg viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" ' +
  'stroke-width="1.6" stroke-linejoin="round" aria-hidden="true" ' +
  'focusable="false"><path d="m12 3.6 2.6 5.3 5.9.9-4.3 4.1 1 5.8-5.2-2.7' +
  '-5.2 2.7 1-5.8L3.5 9.8l5.9-.9Z"/></svg>';
const ICON_STAR_OFF =
  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
  'stroke-width="1.9" stroke-linejoin="round" aria-hidden="true" ' +
  'focusable="false"><path d="m12 3.6 2.6 5.3 5.9.9-4.3 4.1 1 5.8-5.2-2.7' +
  '-5.2 2.7 1-5.8L3.5 9.8l5.9-.9Z"/></svg>';
const ICON_WARN =
  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
  'stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" ' +
  'aria-hidden="true" focusable="false"><path d="M10.3 3.9 1.8 18.1A2 2 0 ' +
  '0 0 3.5 21h17a2 2 0 0 0 1.7-2.9L13.7 3.9a2 2 0 0 0-3.4 0Z"/>' +
  '<path d="M12 9v4M12 17h.01"/></svg>';


/* ---------- filter pills ----------
   Building the row and lighting a pill are two jobs, and they happen at
   different times: the categories change only when the store does, while
   which pill is lit changes on every click. They used to be one job, and
   the row was the half that never ran again -- renderPills() is called at
   load and on a store change, and a click calls render(), which redraws
   the table only. So the filter applied, the subtitle said "· Summer",
   and "Tất cả" stayed lit because that is what the markup had said since
   the page loaded. */
function renderPills() {
  const cats = [{ id: 'all', name: 'Tất cả' }, ...MenuStore.cats().filter(c => c.id !== 'all')];
  $('pills').innerHTML = cats.map(c =>
    `<button type="button" class="pill" data-cat="${c.id}" ` +
    `aria-pressed="false">${c.name.replace(' Menu','')}</button>`
  ).join('');
  syncPills();
}

/* Light the pill the table is actually filtered by.
   Called from render(), so every path that moves filterCat is covered
   rather than only the click that prompted this. The class is set in
   place rather than by rebuilding the row, which keeps the pressed button
   focused for anyone driving the filter from the keyboard.

   aria-pressed carries the same fact to a screen reader, which the colour
   alone never did: the lit pill was invisible to one. */
function syncPills() {
  $('pills').querySelectorAll('.pill').forEach(el => {
    const on = el.dataset.cat === filterCat;
    el.classList.toggle('active', on);
    el.setAttribute('aria-pressed', on ? 'true' : 'false');
  });
}

/* ---------- table ---------- */
function catName(catId) {
  const c = MenuStore.cats().find(x => x.id === catId);
  return c ? c.name.replace(' Menu', '') : catId;
}

/* Every category a drink is in, as the "c4001" ids the pills and the
   filter are keyed by. The payload carries `cat`/`catId` as well, but
   those are only ever the FIRST of them -- fine for a one-category drink
   and wrong for the rest, which is what this returns instead. */
function catIdsOf(item) {
  return (item.categoryIds || []).map(id => 'c' + Number(id));
}

/* One tag per category. `it.cat` is the fallback for a drink the payload
   described before categoryIds existed; a drink in nothing at all gets a
   dash rather than an empty cell, so the column never looks like it
   failed to render. */
function catCell(item) {
  const names = catIdsOf(item).map(catName);
  if (!names.length) names.push(item.cat || '—');
  return `<div class="tagwrap">${
    names.map(name => `<span class="tag">${name}</span>`).join('')}</div>`;
}

function saleLabel(item) {
  if (!item.available) return 'Ngừng bán';
  if (!item.ingredientStock) return 'Hết nguyên liệu';
  return 'Đang bán';
}

/* ---------- the star ----------
   Reports the way the rest of this page does: a toast on success, and a
   toast naming the reason on refusal. A control that silently springs
   back is the one failure nobody can diagnose.

   Which drinks are starred is a property of a DRINK, so it is edited
   here. How the strip that shows them is arranged is a property of the
   customer screen, and lives on home.html. */
async function toggleFeatured(id, featured) {
  const it = MenuStore.getItem(id);
  try {
    await MenuStore.setFeatured(id, featured);
    showToast(featured
      ? `${ICON_STAR_ON} <b>${escapeHtml(it.name)}</b> đã lên dải nổi bật`
      : `${ICON_STAR_OFF} <b>${escapeHtml(it.name)}</b> đã rời dải nổi bật`, 'ok');
  } catch (error) {
    showToast(`${ICON_WARN} ${escapeHtml(error.message)}`, 'warn');
  }
}

function render() {
  const all = MenuStore.allItems();

  // stats
  $('stTotal').textContent = all.length;
  $('stIn').textContent  = all.filter(i => !i.soldOut).length;
  $('stOut').textContent = all.filter(i => i.soldOut).length;
  $('stCat').textContent = new Set(all.flatMap(catIdsOf)).size;

  // filtered view
  const list = all.filter(it => {
    const okCat = filterCat === 'all' || catIdsOf(it).includes(filterCat);
    const okQ = !query || it.name.toLowerCase().includes(query) || String(it.sku).includes(query);
    return okCat && okQ;
  });
  $('listSub').textContent = `${list.length} món${filterCat !== 'all' ? ' · ' + catName(filterCat) : ''}`;
  syncPills();

  // How many stars are already spent, worked out once for the whole table
  // rather than per row. When the strip is full every UNSTARRED row is
  // dimmed, which is what makes "why will this one not tick" answerable
  // before it is clicked.
  const featMax = MenuStore.featuredMax();
  const stripFull = all.filter(i => i.featured).length >= featMax;

  const body = $('menuBody');
  if (!list.length) {
    body.innerHTML = `<tr><td colspan="8" style="text-align:center;color:var(--muted);padding:26px">Không có món nào khớp.</td></tr>`;
    return;
  }
  body.innerHTML = list.map(it => `
    <tr class="${it.soldOut ? 'soldout' : ''}" data-id="${it.id}">
      <td class="idcell">${id4(it.id)}</td>
      <td>
        <div class="m-item">
          <div class="m-emoji">${it.imageUrl
            // The real photo when there is one, the drink's glyph when
            // there is not. onerror covers the file being deleted from
            // disk between the menu being read and this row being drawn.
            ? `<img src="${it.imageUrl}" alt="" loading="lazy"
                    onerror="this.replaceWith(Object.assign(
                      document.createElement('span'),
                      {innerHTML:'${it.emoji}'}))">`
            : it.emoji}</div>
          <div><div class="m-name">${escapeHtml(it.name)}</div><div class="m-sku">SKU ${it.sku}</div></div>
        </div>
      </td>
      <td>${catCell(it)}</td>
      <td><input class="priceinput" type="number" step="0.10" min="0" value="${Number(it.price).toFixed(2)}" data-price="${it.id}"></td>
      <td>
        <span class="badge ${it.soldOut ? 'out' : 'in'}">
          <span class="d"></span>${saleLabel(it)}
        </span>
      </td>
      <td style="text-align:center">
        <label class="switch">
          <input type="checkbox" data-toggle="${it.id}" ${it.available ? 'checked' : ''}>
          <span class="slider"></span>
        </label>
      </td>
      <td style="text-align:center">
        <button type="button"
                class="starbtn ${!it.featured && stripFull ? 'full' : ''}"
                data-star="${it.id}" aria-pressed="${!!it.featured}"
                title="${it.featured
                  ? 'Bỏ khỏi dải nổi bật'
                  : stripFull
                    ? `Dải đã đủ ${featMax} món`
                    : 'Đưa lên dải nổi bật'}"
                aria-label="${it.featured
                  ? `Bỏ ${escapeHtml(it.name)} khỏi dải nổi bật`
                  : `Đưa ${escapeHtml(it.name)} lên dải nổi bật`}"
        >${it.featured ? ICON_STAR_ON : ICON_STAR_OFF}</button>
      </td>
      <td>
        <div class="rowacts">
          <button class="iconbtn" data-edit="${it.id}" title="Sửa"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg></button>
          <button class="iconbtn del" data-del="${it.id}" title="Xóa món khỏi menu"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M3 6h18"/><path d="M8 6V4.5A1.5 1.5 0 0 1 9.5 3h5A1.5 1.5 0 0 1 16 4.5V6"/><path d="M5.5 6l1 13.2A2 2 0 0 0 8.5 21h7a2 2 0 0 0 2-1.8L18.5 6"/><path d="M10 11v5M14 11v5"/></svg></button>
        </div>
      </td>
    </tr>`).join('');

  // wire toggles
  body.querySelectorAll('[data-toggle]').forEach(el => el.onchange = async () => {
    const id = Number(el.dataset.toggle);
    const it = MenuStore.getItem(id);
    try {
      await MenuStore.setAvailable(id, el.checked);
      showToast(el.checked ? `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="m4.5 12.5 5 5L19.5 7"/></svg> <b>${escapeHtml(it.name)}</b> đã mở bán` : `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="9"/><path d="m5.6 5.6 12.8 12.8"/></svg> <b>${escapeHtml(it.name)}</b> đã ngừng bán`, el.checked ? 'ok' : 'warn');
    } catch {
      showToast('Không thể cập nhật trạng thái trong database', 'warn');
    }
  });
  // wire price edits
  body.querySelectorAll('[data-price]').forEach(el => {
    el.onchange = async () => {
      try {
        await MenuStore.setPrice(Number(el.dataset.price), el.value);
        showToast('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><rect x="2.5" y="6" width="19" height="12" rx="2.5"/><circle cx="12" cy="12" r="2.6"/><path d="M6 10v4M18 10v4"/></svg> Đã cập nhật giá', 'ok');
      } catch {
        showToast('Không thể cập nhật giá trong database', 'warn');
      }
    };
    el.onclick = e => e.stopPropagation();
  });
  // wire the featured stars. A dimmed one is still clickable on purpose --
  // see .starbtn.full in admin.css: it answers with the reason instead of
  // being a control that does nothing and says nothing.
  body.querySelectorAll('[data-star]').forEach(el => el.onclick = () => {
    const id = Number(el.dataset.star);
    toggleFeatured(id, el.getAttribute('aria-pressed') !== 'true');
  });
  // wire edit / delete
  body.querySelectorAll('[data-edit]').forEach(el => el.onclick = () => openModal(Number(el.dataset.edit)));
  // Deleting is permanent, so the confirmation says exactly what goes and
  // exactly what stays. "Are you sure?" tells nobody anything.
  body.querySelectorAll('[data-del]').forEach(el => el.onclick = async () => {
    const it = MenuStore.getItem(Number(el.dataset.del));
    const ok = confirm(
      `Chuyển món "${it.name}" vào thùng rác?\n\n` +
      `• Món sẽ biến mất khỏi màn hình bán và máy sẽ không pha được.\n` +
      `• Công thức được GIỮ NGUYÊN trong thùng rác — khôi phục lại được.\n` +
      `• Lịch sử bán hàng vẫn đủ trong báo cáo.\n` +
      `• Nhãn QR đã in cho món này sẽ không quét được nữa.`);

    if (!ok) return;

    try {
      const result = await MenuStore.deleteDrink(it.id);
      const extra = result.stranded_tickets
        ? ` · ${result.stranded_tickets} nhãn QR chưa dùng không còn hiệu lực`
        : '';
      showToast(`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M3 6h18"/><path d="M8 6V4.5A1.5 1.5 0 0 1 9.5 3h5A1.5 1.5 0 0 1 16 4.5V6"/><path d="M5.5 6l1 13.2A2 2 0 0 0 8.5 21h7a2 2 0 0 0 2-1.8L18.5 6"/><path d="M10 11v5M14 11v5"/></svg> Đã chuyển <b>${escapeHtml(result.name)}</b> vào ` +
                `<a href="bin.html">thùng rác</a>${extra}`, 'warn');
    } catch (error) {
      showToast('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M10.3 3.9 1.8 18.1A2 2 0 0 0 3.5 21h17a2 2 0 0 0 1.7-2.9L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/></svg> ' + error.message, 'warn');
    }
  });
}

/* ---------- add / edit modal ---------- */
async function openModal(editId) {
  const editing = editId != null ? MenuStore.getItem(editId) : null;
  const cats = MenuStore.cats().filter(c => c.id !== 'all');
  $('itemOverlay').classList.add('show');
  $('itemModal').innerHTML = '<div class="msub">Đang tải dữ liệu từ database…</div>';
  try {
    const editorData = await MenuStore.getRecipeEditor(editId);
    AdminRecipeEditor.create($('itemModal'), {
      item:editing,
      categories:cats,
      editorData,
      onCancel:closeModal,
      onSave:async document => {
        const result = await MenuStore.saveRecipe(document);
        closeModal();
        showToast(result.warning ? 'Đã lưu database nhưng chưa xuất được recipe JSON' : '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="m4.5 12.5 5 5L19.5 7"/></svg> Đã lưu món và công thức', result.warning ? 'warn' : 'ok');
      },
    });
  } catch {
    $('itemModal').innerHTML = '<h3>Không thể tải công thức</h3><div class="msub">Kiểm tra kết nối database rồi thử lại.</div><div class="modal-acts"><button class="btn ghost" data-close-load>Lùi lại</button></div>';
    $('itemModal').querySelector('[data-close-load]').onclick = closeModal;
  }
}
function closeModal() { $('itemOverlay').classList.remove('show'); }
$('itemOverlay').onclick = e => { if (e.target.id === 'itemOverlay') closeModal(); };

/* ---------- toolbar ---------- */
$('pills').onclick = e => {
  const pill = e.target.closest('.pill');
  if (!pill) return;
  filterCat = pill.dataset.cat;
  render();
};
$('search').oninput = e => { query = e.target.value.trim().toLowerCase(); render(); };
$('addBtn').onclick = () => openModal(null);
$('resetBtn').onclick = () => {
  MenuStore.refresh()
    .then(() => showToast('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M21 12a9 9 0 1 1-3-6.7"/><path d="M21 3v6h-6"/></svg> Đã tải lại dữ liệu từ database', 'ok'))
    .catch(() => showToast('Không thể tải lại database', 'warn'));
};

// re-render on any store change (covers edits coming from other tabs)
MenuStore.onChange(() => {
  renderPills();
  render();
});

renderPills();
render();
