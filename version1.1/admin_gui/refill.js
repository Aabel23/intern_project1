/* ================================================================
   ADMIN-06 · NẠP KHO
   Màn dành riêng cho một việc: sau khi đổ đầy bình thật ngoài máy thì
   nói lại cho database biết trong bình còn bao nhiêu.

   VÌ SAO TÁCH KHỎI TRANG NGUYÊN LIỆU
     Hai việc khác nhau và làm vào hai lúc khác nhau. Trang Nguyên liệu
     là KHAI BÁO — bình này tên gì, cắm ở bơm nào, đầy là bao nhiêu gram;
     làm một lần rồi thôi. Trang này là VẬN HÀNH — hàng về, mười ba cái
     bình vừa được đổ, bấm một nút. Gộp lại thì mỗi lần nạp kho phải đi
     xuyên qua một bảng đầy nút Sửa và Xóa.

   MỘT SỐ NÀY KHÔNG PHẢI DO TRANG NÀY QUYẾT
     Trạng thái (Đủ / Hết) do trigger trong database tính sau khi ghi:
     amount >= threshold_gram. Trang chỉ ghi lượng tồn rồi đọc lại kết
     quả database kết luận — không tự tô màu theo ý mình.
   ================================================================ */
if (!AdminAuth.initPage('refill')) { /* redirected to login */ }

const $ = id => document.getElementById(id);

const esc = value => String(value == null ? '' : value)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

const id4 = value => String(value ?? '').padStart(4, '0');

const gram = value => Number(value || 0).toLocaleString('vi-VN', {
  maximumFractionDigits: 2,
}) + 'g';

/* Cùng bộ icon với trang Nguyên liệu, xét theo thứ tự: "Soda Water" phải
   khớp soda trước khi khớp water. */
const GLYPHS = [
  [/soda|sparkling|có ga/, '&#129380;'],
  [/water|nước lọc/, '&#128167;'],
  [/matcha|green tea|trà|tea/, '&#127861;'],
  [/coffee|espresso|cà phê|ca phe/, '&#9749;'],
  [/milk|sữa tươi/, '&#129371;'],
  [/yogurt|sữa chua/, '&#129379;'],
  [/cream|kem/, '&#127846;'],
  [/choco|cacao|cocoa/, '&#127851;'],
  [/strawberry|dâu/, '&#127827;'],
  [/peach|đào/, '&#127825;'],
  [/mango|xoài/, '&#129389;'],
  [/lemon|lime|chanh/, '&#127819;'],
  [/orange|cam/, '&#127818;'],
  [/sugar|đường|salt|muối/, '&#129474;'],
  [/ice|đá/, '&#129482;'],
  [/pearl|trân châu|boba|topping/, '&#9899;'],
  [/syrup|siro/, '&#127855;'],
];

function glyph(name) {
  const text = String(name || '').toLowerCase();
  const hit = GLYPHS.find(entry => entry[0].test(text));
  return hit ? hit[1] : '&#129524;';
}

let filter = 'all';
let query = '';

/* Những dòng người dùng đã bỏ tick. Giữ kiểu "loại trừ" chứ không giữ
   "danh sách đã chọn": mặc định của màn nạp kho là nạp hết, nên một
   nguyên liệu mới thêm vào phải tự động nằm trong diện được nạp thay vì
   bị bỏ quên chỉ vì nó chưa có trong danh sách cũ. */
const unticked = new Set();

/* Số người dùng tự gõ vào ô "Sau khi nạp", theo ingredient_id. Không gõ
   gì thì dòng đó nạp về đúng mức tối đa. */
const typed = new Map();

const FILTERS = [
  { id: 'all', name: 'Tất cả' },
  { id: 'notfull', name: '&#128993; Chưa đầy' },
  { id: 'out', name: '&#128308; Dưới ngưỡng' },
  { id: 'guess', name: '&#10067; Chưa khai mức tối đa' },
];

function matchesFilter(row) {
  const level = IngredientStore.level(row);
  if (filter === 'notfull') return level.percent < 100;
  if (filter === 'out') return level.state === 'crit';
  if (filter === 'guess') return !row.max_set;
  return true;
}

function renderPills() {
  $('pills').innerHTML = FILTERS.map(f =>
    `<button class="pill ${f.id === filter ? 'active' : ''}" data-f="${f.id}">${f.name}</button>`
  ).join('');
  $('pills').querySelectorAll('.pill').forEach(el =>
    el.onclick = () => { filter = el.dataset.f; renderPills(); render(); });
}

/* Dòng nào đang được chọn để nạp. */
const isTicked = row => !unticked.has(row.ingredient_id);

/* Lượng sẽ ghi cho một dòng: số gõ tay nếu có, không thì mức tối đa. */
function target(row) {
  const manual = typed.get(row.ingredient_id);
  if (manual === undefined || manual === '') return Number(row.max_gram) || 0;
  const number = Number(manual);
  return Number.isFinite(number) && number >= 0 ? number : Number(row.max_gram) || 0;
}

const isManual = row => {
  const manual = typed.get(row.ingredient_id);
  return manual !== undefined && manual !== '';
};

function visibleRows() {
  return IngredientStore.all().filter(row => {
    const okQ = !query
      || row.name.toLowerCase().includes(query)
      || String(row.gpio == null ? '' : row.gpio).toLowerCase() === query
      || String(row.pump_no == null ? '' : row.pump_no) === query;
    return matchesFilter(row) && okQ;
  });
}

/* ---------- bảng ---------- */
function slotCell(row) {
  if (row.gpio === null || row.gpio === undefined) {
    return '<span class="pumpno none" title="Chưa gắn vào bơm hay panel nào">—</span>';
  }
  if (row.pump_no !== null && row.pump_no !== undefined) {
    return `<span class="pumpno" title="Bơm #${row.pump_no} — ${esc(row.gpio)}">
      <span class="pi">&#129751;</span>${row.pump_no}</span>`;
  }
  return `<span class="pumpno manual" title="${esc(row.gpio)}">
    <span class="pi">${row.type === 'PUMP' ? '&#129751;' : '&#9997;'}</span>${esc(row.gpio)}</span>`;
}

function render() {
  const all = IngredientStore.all();

  $('stTotal').textContent = all.length;
  $('stFull').textContent = all.filter(r => IngredientStore.level(r).percent >= 100).length;
  $('stPartial').textContent = all.filter(r => IngredientStore.level(r).percent < 100).length;
  $('stOut').textContent = all.filter(r => !r.in_stock).length;

  const list = visibleRows();
  const chosen = list.filter(isTicked).length;

  $('listSub').textContent = `${list.length} bình`
    + (filter === 'all' ? '' : ` · ${FILTERS.find(f => f.id === filter).name.replace(/^\S+\s/, '')}`)
    + ` · đã chọn ${chosen}`;

  $('fillSelBtn').textContent = `✓ Nạp đầy ${chosen} mục đã chọn`;
  $('fillSelBtn').disabled = chosen === 0;

  const body = $('refillBody');

  if (!list.length) {
    const failure = IngredientStore.loadError();
    body.innerHTML = `<tr><td colspan="9" style="text-align:center;color:var(--muted);padding:26px">`
      + (failure
        ? `<b style="color:var(--red)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M10.3 3.9 1.8 18.1A2 2 0 0 0 3.5 21h17a2 2 0 0 0 1.7-2.9L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/></svg> Không đọc được nguyên liệu từ database</b>
           <div style="margin-top:8px">${esc(failure)}</div>
           <div style="margin-top:8px;font-size:13px">Sửa xong thì bấm <b><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M21 12a9 9 0 1 1-3-6.7"/><path d="M21 3v6h-6"/></svg> Tải lại DB</b>.</div>`
        : IngredientStore.isLoaded() ? 'Không có nguyên liệu nào khớp.' : 'Đang tải từ database…')
      + `</td></tr>`;
    $('checkAll').checked = false;
    return;
  }

  $('checkAll').checked = chosen === list.length;

  body.innerHTML = list.map(row => {
    const level = IngredientStore.level(row);
    const after = target(row);
    const delta = after - Number(row.amount || 0);

    return `
    <tr class="${row.in_stock ? '' : 'soldout'}" data-id="${row.ingredient_id}">
      <td><input type="checkbox" data-tick="${row.ingredient_id}"
                 ${isTicked(row) ? 'checked' : ''} /></td>
      <td class="idcell">${id4(row.ingredient_id)}</td>
      <td>
        <div class="m-item">
          <div class="m-emoji">${glyph(row.name)}</div>
          <div><div class="m-name">${esc(row.name)}</div>
            <div class="m-sku">${row.type === 'PUMP' ? 'Bơm tự động' : 'Thủ công'}</div></div>
        </div>
      </td>
      <td>${slotCell(row)}</td>
      <td>
        <div class="lvl ${level.state}${row.max_set ? '' : ' guess'}">
          <div class="lvlbar">
            <b>${level.percent}%</b>
            <i style="width:${level.percent}%"><b>${level.percent}%</b></i>
          </div>
        </div>
      </td>
      <td class="amt">${gram(row.amount)}</td>
      <td class="amt">${gram(row.max_gram)}${row.max_set ? ''
        : ' <b title="Chưa khai mức tối đa — đang tạm tính theo mặc định"'
          + ' style="color:var(--orange)">?</b>'}</td>
      <td>
        <input type="number" class="priceinput" data-typed="${row.ingredient_id}"
               min="0" step="1" style="width:120px"
               value="${isManual(row) ? esc(typed.get(row.ingredient_id)) : ''}"
               placeholder="${Number(row.max_gram)}"
               title="Bỏ trống = nạp đầy về mức tối đa. Gõ số để khai lượng thực tế." />
      </td>
      <td style="text-align:right">
        <span class="csub" style="margin-right:10px;color:${delta > 0 ? 'var(--green)'
          : (delta < 0 ? 'var(--orange)' : 'var(--muted)')}">
          ${delta > 0 ? '+' : ''}${delta === 0 ? '—' : gram(delta)}</span>
        <button class="btn compact" data-fill="${row.ingredient_id}">Nạp bình này</button>
      </td>
    </tr>`;
  }).join('');

  body.querySelectorAll('[data-tick]').forEach(el => el.onchange = () => {
    const id = Number(el.dataset.tick);
    if (el.checked) unticked.delete(id); else unticked.add(id);
    render();
  });

  /* Gõ vào ô thì KHÔNG vẽ lại cả bảng — vẽ lại là mất con trỏ giữa lúc
     đang gõ. Chỉ cập nhật con số chênh lệch của đúng dòng đó. */
  body.querySelectorAll('[data-typed]').forEach(el => {
    el.oninput = () => {
      const id = Number(el.dataset.typed);
      const value = el.value.trim();
      if (value === '') typed.delete(id); else typed.set(id, value);

      const row = IngredientStore.get(id);
      const cell = el.closest('tr').querySelector('.csub');
      if (!row || !cell) return;
      const delta = target(row) - Number(row.amount || 0);
      cell.textContent = delta === 0 ? '—' : (delta > 0 ? '+' : '') + gram(delta);
      cell.style.color = delta > 0 ? 'var(--green)'
        : (delta < 0 ? 'var(--orange)' : 'var(--muted)');
    };
  });

  body.querySelectorAll('[data-fill]').forEach(el =>
    el.onclick = () => fillOne(Number(el.dataset.fill)));
}

/* ---------- ghi một dòng ---------- */
async function fillOne(id) {
  const row = IngredientStore.get(id);
  if (!row) return;

  /* Gõ tay thì gửi set_gram (lượng thực tế cân được), không gõ thì gửi
     fill để server tự lấy mức tối đa của chính nó — trang không gửi con
     số max lên, vì mức tối đa là chuyện server giữ. */
  const change = isManual(row)
    ? { set_gram: typed.get(id) }
    : { fill: true };

  try {
    const result = await IngredientStore.refill(id, change);
    typed.delete(id);
    showToast(`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M21 8v8.2a2 2 0 0 1-1 1.7l-7 4a2 2 0 0 1-2 0l-7-4a2 2 0 0 1-1-1.7V7.8a2 2 0 0 1 1-1.7l7-4a2 2 0 0 1 2 0L17 4.6"/><path d="m3.3 7.1 8.7 5 8.7-5"/><path d="M12 21.6V12"/></svg> <b>${esc(result.name)}</b> còn ${gram(result.amount)}`
      + (result.in_stock ? '' : ' — vẫn dưới ngưỡng, món liên quan chưa bán được'),
      result.in_stock ? 'ok' : 'warn');
  } catch (error) {
    showToast('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M10.3 3.9 1.8 18.1A2 2 0 0 0 3.5 21h17a2 2 0 0 0 1.7-2.9L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/></svg> ' + esc(error.message), 'warn');
  }
}

/* ---------- ghi hàng loạt ----------
   Hỏi trước khi ghi, và hỏi bằng bảng chứ không bằng một câu: nạp kho là
   thao tác đè lên lượng tồn của nhiều bình cùng lúc, người bấm cần thấy
   đúng dòng nào đổi từ bao nhiêu sang bao nhiêu trước khi đồng ý. */
function askFill(rows, title) {
  if (!rows.length) { showToast('Chưa chọn bình nào', 'warn'); return; }

  const guessed = rows.filter(r => !r.max_set).length;
  const manual = rows.filter(isManual).length;

  $('confirmModal').innerHTML = `
    <h3><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M21 8v8.2a2 2 0 0 1-1 1.7l-7 4a2 2 0 0 1-2 0l-7-4a2 2 0 0 1-1-1.7V7.8a2 2 0 0 1 1-1.7l7-4a2 2 0 0 1 2 0L17 4.6"/><path d="m3.3 7.1 8.7 5 8.7-5"/><path d="M12 21.6V12"/></svg> ${esc(title)}</h3>
    <div class="msub">${rows.length} bình sẽ được ghi lại lượng tồn. Kiểm tra rồi bấm xác nhận.</div>

    <div style="max-height:320px;overflow:auto;margin:14px 0;border:1px solid var(--line);border-radius:12px">
      <table class="tbl">
        <thead><tr>
          <th>Nguyên liệu</th><th style="width:110px">Đang còn</th>
          <th style="width:110px">Sẽ thành</th><th style="width:110px">Chênh lệch</th>
        </tr></thead>
        <tbody>${rows.map(row => {
          const after = target(row);
          const delta = after - Number(row.amount || 0);
          return `<tr>
            <td>${glyph(row.name)} ${esc(row.name)}${row.max_set ? ''
              : ' <b style="color:var(--orange)" title="Chưa khai mức tối đa">?</b>'}
              ${isManual(row) ? ' <span class="tag">gõ tay</span>' : ''}</td>
            <td class="amt">${gram(row.amount)}</td>
            <td class="amt"><b>${gram(after)}</b></td>
            <td class="amt" style="color:${delta > 0 ? 'var(--green)'
              : (delta < 0 ? 'var(--orange)' : 'var(--muted)')}">
              ${delta === 0 ? '—' : (delta > 0 ? '+' : '') + gram(delta)}</td>
          </tr>`;
        }).join('')}</tbody>
      </table>
    </div>

    <div class="mnote">
      ${guessed ? `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M10.3 3.9 1.8 18.1A2 2 0 0 0 3.5 21h17a2 2 0 0 0 1.7-2.9L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/></svg> <b>${guessed} bình chưa khai mức tối đa</b> — những bình đó sẽ được nạp
        theo số mặc định ${gram(IngredientStore.defaultMax())}, tức là nạp theo số đoán.
        Khai mức thật bên <a href="ingredients.html">Quản lý Nguyên liệu</a> rồi quay lại thì con số mới đúng.<br>` : ''}
      ${manual ? `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg> <b>${manual} bình</b> dùng số bạn gõ tay thay vì mức tối đa.<br>` : ''}
      Sau khi ghi, database tự đặt lại trạng thái còn hàng theo ngưỡng cảnh báo của từng bình.
    </div>

    <div class="modal-acts">
      <button class="btn ghost" id="cAbort">Hủy</button>
      <button class="btn primary" id="cGo">Xác nhận nạp ${rows.length} bình</button>
    </div>`;

  $('confirmOverlay').classList.add('show');
  $('cAbort').onclick = closeConfirm;
  $('cGo').onclick = () => doFill(rows);
}

function closeConfirm() { $('confirmOverlay').classList.remove('show'); }
$('confirmOverlay').onclick = e => { if (e.target.id === 'confirmOverlay') closeConfirm(); };

async function doFill(rows) {
  const go = $('cGo');
  go.disabled = true;

  /* Dòng nào gõ tay thì phải đi đường riêng: /refill-all chỉ biết nạp về
     mức tối đa. Gửi những dòng đó trước, từng cái một, rồi mới gọi lượt
     nạp đầy cho phần còn lại. */
  const manual = rows.filter(isManual);
  const toMax = rows.filter(row => !isManual(row));

  try {
    for (const row of manual) {
      await IngredientStore.refill(row.ingredient_id,
        { set_gram: typed.get(row.ingredient_id) });
      typed.delete(row.ingredient_id);
    }

    let result = { count: manual.length, guessed: 0 };

    if (toMax.length) {
      result = await IngredientStore.refillAll(toMax.map(r => r.ingredient_id));
      result.count += manual.length;
    }

    closeConfirm();
    showToast(`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M21 8v8.2a2 2 0 0 1-1 1.7l-7 4a2 2 0 0 1-2 0l-7-4a2 2 0 0 1-1-1.7V7.8a2 2 0 0 1 1-1.7l7-4a2 2 0 0 1 2 0L17 4.6"/><path d="m3.3 7.1 8.7 5 8.7-5"/><path d="M12 21.6V12"/></svg> Đã nạp <b>${result.count} bình</b>`
      + (result.guessed ? ` — ${result.guessed} bình theo mức mặc định` : ''),
      result.guessed ? 'warn' : 'ok');
  } catch (error) {
    go.disabled = false;
    showToast('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M10.3 3.9 1.8 18.1A2 2 0 0 0 3.5 21h17a2 2 0 0 0 1.7-2.9L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/></svg> ' + esc(error.message), 'warn');
  }
}

/* ---------- thanh công cụ ---------- */
$('search').oninput = e => { query = e.target.value.trim().toLowerCase(); render(); };

$('checkAll').onchange = e => {
  const list = visibleRows();
  if (e.target.checked) list.forEach(row => unticked.delete(row.ingredient_id));
  else list.forEach(row => unticked.add(row.ingredient_id));
  render();
};

$('fillAllBtn').onclick = () =>
  askFill(IngredientStore.all(), 'Nạp đầy TẤT CẢ các bình');

$('fillSelBtn').onclick = () =>
  askFill(visibleRows().filter(isTicked), 'Nạp đầy các bình đã chọn');

$('resetBtn').onclick = () => {
  IngredientStore.refresh()
    .then(() => showToast('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M21 12a9 9 0 1 1-3-6.7"/><path d="M21 3v6h-6"/></svg> Đã tải lại dữ liệu từ database', 'ok'))
    .catch(error => showToast('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M10.3 3.9 1.8 18.1A2 2 0 0 0 3.5 21h17a2 2 0 0 0 1.7-2.9L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/></svg> ' + esc(error.message), 'warn'));
};

IngredientStore.onChange(render);

renderPills();
render();
