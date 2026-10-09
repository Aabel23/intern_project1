/* ================================================================
   ADMIN-05 · INGREDIENT STOCK
   Bao nhiêu còn trong từng bình, bình nào nằm trên bơm nào, và nút nạp
   thêm sau khi người pha đổ đầy bình thật.

   HAI SỐ TRÊN MÀN NÀY KHÔNG PHẢI DO TRANG NÀY QUYẾT
     · Trạng thái (Đủ / Hết) do trigger trong database tính:
       amount >= threshold_gram. Trang chỉ hiển thị.
     · Ngưỡng cảnh báo (threshold_gram) do inventory_service tính lại từ
       công thức — 110% lượng dùng nhiều nhất. Sửa tay sẽ bị ghi đè, nên
       ô đó là read-only và có ghi rõ lý do.
   Số duy nhất người dùng được khai là LƯỢNG TỒN, vì chỉ con người mới
   biết cái bình vừa được đổ đầy.
   ================================================================ */
if (!AdminAuth.initPage('ingredients')) { /* redirected to login */ }

/* Four digits, zero-padded, matching the width the machine prints a SKU at
   (`f"{sku:04d}"`). This column exists to be compared against machine logs
   and printed labels, so it has to read the same as they do. Never
   truncated -- an id past four digits just gets wider. */
const id4 = value => String(value ?? '').padStart(4, '0');

let filter = 'all';
let query = '';

const $ = id => document.getElementById(id);

/* Tên nguyên liệu là do người dùng gõ và được nhét thẳng vào innerHTML.
   Một dấu ngoặc kép trong tên là đủ để hỏng cả hàng. */
const esc = value => String(value == null ? '' : value)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

/* ---------- icon cho từng bình ----------
   Xét theo thứ tự: "Soda Water" phải khớp soda trước khi khớp water, và
   "Peach Syrup" phải ra quả đào chứ không phải hũ siro. */
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
  [/grape|nho/, '&#127815;'],
  [/apple|táo/, '&#127822;'],
  [/banana|chuối/, '&#127820;'],
  [/coconut|dừa/, '&#129381;'],
  [/passion|chanh dây/, '&#129389;'],
  [/mint|bạc hà/, '&#127807;'],
  [/caramel/, '&#127854;'],
  [/vanilla|vani/, '&#127804;'],
  [/honey|mật ong/, '&#127855;'],
  [/sugar|đường|salt|muối/, '&#129474;'],
  [/ice|đá/, '&#129482;'],
  [/pearl|trân châu|boba|topping/, '&#9899;'],
  [/syrup|siro/, '&#127855;'],
];
const DEFAULT_GLYPH = '&#129524;';

function glyph(name) {
  const text = String(name || '').toLowerCase();
  const hit = GLYPHS.find(entry => entry[0].test(text));
  return hit ? hit[1] : DEFAULT_GLYPH;
}

/* ---------- số ---------- */
const gram = value => Number(value || 0).toLocaleString('vi-VN', {
  maximumFractionDigits: 2,
}) + 'g';

const DATA_TYPE_LABEL = {
  weight: 'đong theo gram',
  percentage: 'đong theo %',
  boolean: 'bật / tắt',
};

/* ---------- filter pills ---------- */
const FILTERS = [
  { id: 'all', name: 'Tất cả' },
  { id: 'pump', name: 'Bơm (PUMP)' },
  { id: 'manual', name: 'Thủ công' },
  { id: 'low', name: 'Mức thấp' },
  { id: 'refill', name: 'Cần nạp ngay' },
];

function matchesFilter(row) {
  const level = IngredientStore.level(row);
  if (filter === 'pump') return row.type === 'PUMP';
  if (filter === 'manual') return row.type === 'MANUAL';
  if (filter === 'low') return level.state === 'low';
  if (filter === 'refill') return level.state === 'crit';
  return true;
}

function renderPills() {
  $('pills').innerHTML = FILTERS.map(f =>
    `<button class="pill ${f.id === filter ? 'active' : ''}" data-f="${f.id}">${f.name}</button>`
  ).join('');
  $('pills').querySelectorAll('.pill').forEach(el =>
    el.onclick = () => { filter = el.dataset.f; renderPills(); render(); });
}

/* ---------- bảng ---------- */
function pumpCell(row) {
  /* Số bơm chứ không phải chân GPIO: ngoài máy các bơm được đánh số
     1..10 dọc dàn, và đó là số mà pump_control chạy và pump_calib.json
     lưu. Chân GPIO vẫn hiện trong tooltip cho người đi dây. */
  if (row.pump_no !== null && row.pump_no !== undefined) {
    return `<span class="pumpno" title="Bơm #${row.pump_no} — chân GPIO ${row.gpio}">
      <span class="pi">&#129751;</span>${row.pump_no}</span>`;
  }

  if (row.gpio === null || row.gpio === undefined) {
    return '<span class="pumpno none" title="Chưa gắn vào bơm hay panel nào">—</span>';
  }

  /* Panel thủ công, hoặc một chân không nằm trong bảng bơm. */
  return `<span class="pumpno manual" title="${row.type === 'PUMP'
      ? 'Chân GPIO ' + row.gpio + ' không nằm trong bảng bơm của pump_control'
      : 'Vị trí ' + row.gpio + ' trên panel thủ công'}">
    <span class="pi">${row.type === 'PUMP' ? '&#129751;' : '&#9997;'}</span>${row.gpio}</span>`;
}

function levelCell(row) {
  const level = IngredientStore.level(row);
  const guess = row.max_set ? '' : ' guess';
  const title = row.max_set
    ? `${gram(row.amount)} trên mức tối đa ${gram(row.max_gram)}`
    : `Chưa khai mức tối đa — đang tạm tính trên ${gram(row.max_gram)}`;
  return `<div class="lvl ${level.state}${guess}" title="${esc(title)}">
      <div class="lvlbar">
        <b>${level.percent}%</b>
        <i style="width:${level.percent}%"><b>${level.percent}%</b></i>
      </div>
    </div>`;
}

function statusCell(row) {
  const level = IngredientStore.level(row);
  if (!row.in_stock) {
    return `<span class="badge out" title="Lượng tồn đã xuống dưới ngưỡng ${gram(row.threshold_gram)} — mọi món dùng nguyên liệu này đang bị khóa bán">
      <span class="d"></span>Hết</span>`;
  }
  if (level.state === 'low') {
    return `<span class="badge warn" title="Còn dưới 10% bình — vẫn bán được, nhưng nên chuẩn bị nạp">
      <span class="d"></span>Sắp hết</span>`;
  }
  return '<span class="badge in"><span class="d"></span>Đủ</span>';
}

function render() {
  const all = IngredientStore.all();

  $('stTotal').textContent = all.length;
  $('stPump').textContent = all.filter(r => r.type === 'PUMP' && r.gpio !== null).length;
  $('stLow').textContent = all.filter(r => IngredientStore.level(r).state === 'low').length;
  $('stRefill').textContent = all.filter(r => !r.in_stock).length;

  const list = all.filter(row => {
    // Ô phần cứng gõ được cả hai kiểu: nguyên ô ("g26") hoặc chỉ số
    // trong ô ("26"). Người đứng máy nhớ số, người đọc log nhớ cả chữ.
    const slotNo = IngredientStore.slotNumber(row.gpio);
    const okQ = !query
      || row.name.toLowerCase().includes(query)
      || String(row.pump_no == null ? '' : row.pump_no) === query
      || String(row.gpio == null ? '' : row.gpio).toLowerCase() === query
      || String(slotNo === null ? '' : slotNo) === query;
    return matchesFilter(row) && okQ;
  });

  const pill = FILTERS.find(f => f.id === filter);
  $('listSub').textContent = `${list.length} nguyên liệu`
    // The names no longer carry a leading emoji, so there is nothing to
    // strip off before the label can be read as a sentence.
    + (filter === 'all' ? '' : ` · ${pill.name}`);

  const body = $('ingBody');

  if (!list.length) {
    /* Ba trạng thái khác nhau, không phải hai: chưa có gì khớp, đang tải,
       và tải hỏng. Cái thứ ba trước đây đội lốt cái thứ hai — bảng cứ báo
       "đang tải" cho một lần GET đã chết, còn lý do thì nằm trong một cái
       toast đã tự tắt. Lỗi phải ở lại trên màn cho tới khi bấm Tải lại. */
    const failure = IngredientStore.loadError();

    body.innerHTML = `<tr><td colspan="8" style="text-align:center;color:var(--muted);padding:26px">`
      + (failure
        ? `<b style="color:var(--red)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M10.3 3.9 1.8 18.1A2 2 0 0 0 3.5 21h17a2 2 0 0 0 1.7-2.9L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/></svg> Không đọc được nguyên liệu từ database</b>
           <div style="margin-top:8px">${esc(failure)}</div>
           <div style="margin-top:8px;font-size:13px">Sửa xong thì bấm <b><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M21 12a9 9 0 1 1-3-6.7"/><path d="M21 3v6h-6"/></svg> Tải lại DB</b>.</div>`
        : IngredientStore.isLoaded() ? 'Không có nguyên liệu nào khớp.' : 'Đang tải từ database…')
      + `</td></tr>`;
    return;
  }

  body.innerHTML = list.map(row => `
    <tr class="${row.in_stock ? '' : 'soldout'}" data-id="${row.ingredient_id}">
      <td class="idcell">${id4(row.ingredient_id)}</td>
      <td>${pumpCell(row)}</td>
      <td>
        <div class="m-item">
          <div class="m-emoji">${glyph(row.name)}</div>
          <div>
            <div class="m-name">${esc(row.name)}</div>
            <div class="m-sku">${DATA_TYPE_LABEL[row.data_type] || row.data_type}${
              row.used_in ? ` · ${row.used_in} món dùng` : ' · chưa món nào dùng'}</div>
          </div>
        </div>
      </td>
      <td><span class="typetag ${row.type === 'PUMP' ? '' : 'manual'}">${row.type}</span></td>
      <td>${levelCell(row)}</td>
      <td>
        <div class="amt">${gram(row.amount)}
          <small>/ tối đa ${gram(row.max_gram)}${row.max_set ? '' : ' · tạm tính'}</small>
        </div>
      </td>
      <td>${statusCell(row)}</td>
      <td>
        <div class="rowacts">
          <button class="iconbtn" data-edit="${row.ingredient_id}" title="Sửa nguyên liệu"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg></button>
          <button class="iconbtn del" data-del="${row.ingredient_id}" title="Xóa nguyên liệu"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M3 6h18"/><path d="M8 6V4.5A1.5 1.5 0 0 1 9.5 3h5A1.5 1.5 0 0 1 16 4.5V6"/><path d="M5.5 6l1 13.2A2 2 0 0 0 8.5 21h7a2 2 0 0 0 2-1.8L18.5 6"/><path d="M10 11v5M14 11v5"/></svg></button>
          <button class="btn ghost compact" data-refill="${row.ingredient_id}">&#129751; Nạp thêm</button>
        </div>
      </td>
    </tr>`).join('');

  body.querySelectorAll('[data-refill]').forEach(el =>
    el.onclick = () => openRefill(Number(el.dataset.refill)));
  body.querySelectorAll('[data-edit]').forEach(el =>
    el.onclick = () => openEditor(Number(el.dataset.edit)));
  body.querySelectorAll('[data-del]').forEach(el =>
    el.onclick = () => removeIngredient(Number(el.dataset.del)));
}

/* ---------- nạp thêm ---------- */
let refillMode = 'add';

function openRefill(id) {
  const row = IngredientStore.get(id);
  if (!row) return;
  refillMode = 'add';
  $('refillOverlay').classList.add('show');
  paintRefill(row);
}

function paintRefill(row) {
  const level = IngredientStore.level(row);
  const modal = $('refillModal');

  modal.innerHTML = `
    <h3>${glyph(row.name)} Nạp thêm — ${esc(row.name)}</h3>
    <div class="msub">${row.pump_no !== null && row.pump_no !== undefined
      ? 'Bình trên bơm #' + row.pump_no + ' (GPIO ' + row.gpio + ')'
      : (row.type === 'PUMP' ? 'Bơm' : 'Hộp thủ công') + ' '
        + (row.gpio === null ? '— chưa gán vị trí' : 'ở vị trí ' + row.gpio)}</div>

    <div class="readout">
      <div><div class="rk">Đang còn</div><div class="rv">${gram(row.amount)}</div></div>
      <div><div class="rk">Mức tối đa</div><div class="rv">${gram(row.max_gram)}</div></div>
      <div><div class="rk">Ngưỡng cảnh báo</div><div class="rv">${gram(row.threshold_gram)}</div></div>
    </div>

    <div class="lvl ${level.state}${row.max_set ? '' : ' guess'}" style="margin-bottom:18px">
      <div class="lvlbar">
        <b>${level.percent}%</b>
        <i style="width:${level.percent}%"><b>${level.percent}%</b></i>
      </div>
    </div>

    <button class="btn primary" id="fillBtn" style="width:100%;justify-content:center;padding:13px;margin-bottom:16px">
      &#129751; Đổ đầy bình — đặt lại thành ${gram(row.max_gram)}
    </button>

    <div class="quickrow">
      <button class="chipbtn ${refillMode === 'add' ? 'active' : ''}" data-mode="add">Cộng thêm</button>
      <button class="chipbtn ${refillMode === 'set' ? 'active' : ''}" data-mode="set">Nhập số còn lại thực tế</button>
    </div>

    <div class="mfield">
      <label>${refillMode === 'add' ? 'Nạp thêm bao nhiêu gram?' : 'Cân được bao nhiêu gram?'}</label>
      <input type="number" id="refillAmount" min="0" step="1"
             value="${refillMode === 'add' ? '' : Number(row.amount)}"
             placeholder="${refillMode === 'add' ? 'ví dụ 1000' : 'ví dụ 850'}">
    </div>

    <div class="quickrow">
      ${[100, 250, 500, 1000, 2000].map(n =>
        `<button class="chipbtn" data-quick="${n}">${refillMode === 'add' ? '+' : ''}${n}g</button>`).join('')}
    </div>

    <div class="mnote">
      ${row.max_set ? '' :
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M10.3 3.9 1.8 18.1A2 2 0 0 0 3.5 21h17a2 2 0 0 0 1.7-2.9L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/></svg> Bình này <b>chưa khai mức tối đa</b> nên phần trăm đang tạm tính trên ' +
        gram(row.max_gram) + '. Sửa trong nút <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg> để số này đúng.<br>'}
      Sau khi lưu, database tự đặt lại trạng thái: còn hàng khi lượng tồn ≥ ${gram(row.threshold_gram)}.
      ${row.used_in ? `<b>${row.used_in} món</b> dùng nguyên liệu này sẽ được mở bán lại nếu đủ.` : ''}
    </div>

    <div class="modal-acts">
      <button class="btn ghost" id="refillCancel">Đóng</button>
      <button class="btn primary" id="refillSave">Lưu lượng tồn</button>
    </div>`;

  modal.querySelectorAll('[data-mode]').forEach(el => el.onclick = () => {
    refillMode = el.dataset.mode;
    paintRefill(row);
  });

  modal.querySelectorAll('[data-quick]').forEach(el => el.onclick = () => {
    $('refillAmount').value = el.dataset.quick;
  });

  $('refillCancel').onclick = closeRefill;
  $('fillBtn').onclick = () => sendRefill(row, { fill: true });
  $('refillSave').onclick = () => {
    const typed = $('refillAmount').value.trim();
    if (typed === '') { showToast('Chưa nhập số gram', 'warn'); return; }
    sendRefill(row, refillMode === 'add'
      ? { add_gram: typed } : { set_gram: typed });
  };
}

async function sendRefill(row, change) {
  const save = $('refillSave');
  save.disabled = true;
  try {
    const result = await IngredientStore.refill(row.ingredient_id, change);
    closeRefill();
    showToast(`&#129751; <b>${esc(result.name)}</b> còn ${gram(result.amount)}`
      + (result.in_stock ? '' : ' — vẫn dưới ngưỡng, món liên quan chưa bán được'),
      result.in_stock ? 'ok' : 'warn');
  } catch (error) {
    save.disabled = false;
    showToast('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M10.3 3.9 1.8 18.1A2 2 0 0 0 3.5 21h17a2 2 0 0 0 1.7-2.9L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/></svg> ' + esc(error.message), 'warn');
  }
}

function closeRefill() { $('refillOverlay').classList.remove('show'); }
$('refillOverlay').onclick = e => { if (e.target.id === 'refillOverlay') closeRefill(); };

/* ---------- thêm / sửa ---------- */
/* Danh sách chỗ gắn bình, KHÔNG bắt gõ chân GPIO.
   Ngoài máy các bơm được đánh số 1..10 và panel thủ công đánh số ô; chân
   GPIO chỉ là cách database ghi lại chuyện đó, nên nó nằm trong ngoặc cho
   người đi dây đọc, còn người đứng cầm chai thì chọn "Bơm #3".
   Vị trí đã có bình khác thì bị khóa: database có khóa duy nhất
   (type, gpio) và sẽ từ chối, khóa sẵn ở đây thì đỡ phải bấm Lưu mới biết. */
function positionOptions(type, current, editingId) {
  const slots = type === 'PUMP'
    ? IngredientStore.pumps().map(pump => ({
        value: IngredientStore.slotNumber(pump.gpio),
        label: 'Bơm #' + pump.pump_no, hint: 'GPIO ' + pump.gpio }))
    : Array.from({ length: IngredientStore.panelCount() }, (unused, n) => ({
        value: n, label: 'Ô số ' + n, hint: 'panel thủ công' }));

  /* `current` tới đây có thể là ô đọc từ database ("G26", "P01") hoặc số
     trần vừa chọn trong <select>. Danh sách trên thì luôn là số trần, nên
     mọi phép so phải quy về số bên trong ô — so thẳng chuỗi thì "G26"
     không khớp 26 và vị trí đang lưu sẽ không được chọn sẵn. */
  const currentNo = IngredientStore.slotNumber(current);
  const empty = currentNo === null;

  /* Một chân đã lưu trong database nhưng không nằm trong bảng bơm / panel
     (đi dây tay, hoặc bảng bơm đổi). Vẫn phải hiện ra, nếu không mở form
     sửa tên rồi bấm Lưu là vị trí biến mất. */
  const known = slots.some(slot => slot.value === currentNo);
  if (!empty && !known) {
    slots.push({
      value: currentNo,
      label: (type === 'PUMP' ? 'Chân GPIO ' : 'Ô số ') + currentNo,
      hint: 'ngoài bảng',
    });
  }

  const options = slots.map(slot => {
    const holder = IngredientStore.holderOf(type, slot.value);
    const busy = holder && holder.ingredient_id !== editingId;
    return `<option value="${slot.value}" ${
      slot.value === currentNo ? 'selected' : ''} ${busy ? 'disabled' : ''}>`
      + `${esc(slot.label)} · ${esc(slot.hint)}${busy ? ' — đang là ' + esc(holder.name) : ''}</option>`;
  });

  return `<option value="" ${empty ? 'selected' : ''}>— chưa gắn —</option>` + options.join('');
}

function openEditor(id) {
  const row = id == null ? null : IngredientStore.get(id);
  if (id != null && !row) return;
  const modal = $('ingModal');
  $('ingOverlay').classList.add('show');

  const option = (value, label, current) =>
    `<option value="${value}" ${value === current ? 'selected' : ''}>${label}</option>`;

  modal.innerHTML = `
    <h3>${row ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg> Sửa nguyên liệu' : '＋ Thêm nguyên liệu'}</h3>
    <div class="msub">${row
      ? 'Đổi tên, loại, vị trí bơm và mức tối đa. Lượng tồn nạp bên tab “Nạp kho”.'
      : 'Khai một bình mới cho máy. Sau khi lưu mới đưa được vào công thức.'}</div>

    <div class="mfield">
      <label>Tên nguyên liệu</label>
      <input id="fName" maxlength="100" value="${row ? esc(row.name) : ''}"
             placeholder="ví dụ Peach Syrup">
    </div>

    <div class="mrow">
      <div class="mfield">
        <label>Loại</label>
        <select id="fType">
          ${option('PUMP', 'PUMP — máy tự bơm', row ? row.type : 'PUMP')}
          ${option('MANUAL', 'MANUAL — người pha tự cho', row ? row.type : 'PUMP')}
        </select>
      </div>
      <div class="mfield">
        <label>Cách đong</label>
        <select id="fData">
          ${option('weight', 'weight — theo gram', row ? row.data_type : 'weight')}
          ${option('percentage', 'percentage — theo %', row ? row.data_type : 'weight')}
          ${option('boolean', 'boolean — có / không', row ? row.data_type : 'weight')}
        </select>
      </div>
    </div>

    <div class="mrow">
      <div class="mfield">
        <label id="fPosLabel">Vị trí</label>
        <select id="fGpio"></select>
      </div>
      <div class="mfield">
        <label>Mức tối đa — đầy bình (g)</label>
        <input type="number" id="fCap" min="1" step="1"
               value="${row && row.max_set ? Number(row.max_gram) : ''}"
               placeholder="mặc định ${IngredientStore.defaultMax()}">
      </div>
    </div>

    ${row ? '' : `
    <div class="mfield">
      <label>Lượng tồn ban đầu (g)</label>
      <input type="number" id="fAmount" min="0" step="1" value="0">
    </div>`}

    <div class="mnote">
      <b>Ngưỡng cảnh báo</b>${row ? ' của bình này đang là ' + gram(row.threshold_gram) : ''}
      không sửa ở đây được: hệ thống tự tính bằng 110% lượng dùng nhiều nhất trong các công thức,
      và sẽ ghi đè mọi số gõ tay.
      ${row && row.used_in ? `<br>Đang nằm trong công thức của <b>${row.used_in} món</b>.` : ''}
    </div>

    <div class="editor-error" id="fError" style="display:none"></div>

    <div class="modal-acts">
      <button class="btn ghost" id="fCancel">Hủy</button>
      <button class="btn primary" id="fSave">${row ? 'Lưu thay đổi' : 'Thêm nguyên liệu'}</button>
    </div>`;

  const paintPositions = keep => {
    const type = $('fType').value;
    $('fGpio').innerHTML = positionOptions(type, keep, row ? row.ingredient_id : null);
    $('fPosLabel').textContent = type === 'PUMP'
      ? 'Gắn ở bơm nào?' : 'Ô nào trên panel thủ công?';
  };

  paintPositions(row && row.gpio !== null ? row.gpio : '');
  // Đổi loại thì danh sách chỗ gắn đổi theo; giữ lại số đang chọn nếu
  // loại mới cũng có chỗ đó.
  $('fType').onchange = () => paintPositions($('fGpio').value);

  $('fCancel').onclick = closeEditor;
  $('fSave').onclick = async () => {
    const record = {
      ingredient_id: row ? row.ingredient_id : null,
      name: $('fName').value.trim(),
      type: $('fType').value,
      data_type: $('fData').value,
      gpio: $('fGpio').value.trim(),
      max_gram: $('fCap').value.trim(),
    };
    if (!row) record.amount = $('fAmount').value.trim() || 0;

    const error = $('fError');
    error.style.display = 'none';
    $('fSave').disabled = true;

    try {
      const result = await IngredientStore.save(record);
      closeEditor();
      showToast(`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="m4.5 12.5 5 5L19.5 7"/></svg> Đã lưu <b>${esc(result.name)}</b>`, 'ok');
    } catch (failure) {
      $('fSave').disabled = false;
      error.textContent = failure.message;
      error.style.display = 'block';
    }
  };
}

function closeEditor() { $('ingOverlay').classList.remove('show'); }
$('ingOverlay').onclick = e => { if (e.target.id === 'ingOverlay') closeEditor(); };

/* Xóa hẳn — nguyên liệu không có thùng rác, nên câu hỏi phải nói rõ. */
async function removeIngredient(id) {
  const row = IngredientStore.get(id);
  if (!row) return;

  const ok = confirm(
    `Xóa hẳn nguyên liệu "${row.name}"?\n\n` +
    `• Nguyên liệu KHÔNG có thùng rác — xóa là mất, phải khai lại từ đầu.\n` +
    `• Lượng tồn ${gram(row.amount)} và vị trí ${row.gpio == null ? '(chưa gán)' : row.gpio} bị xóa theo.\n` +
    (row.used_in
      ? `• Đang có ${row.used_in} món dùng nguyên liệu này — hệ thống sẽ TỪ CHỐI xóa.`
      : `• Chưa công thức nào dùng, nên không món nào bị ảnh hưởng.`));

  if (!ok) return;

  try {
    const result = await IngredientStore.remove(id);
    showToast(`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M3 6h18"/><path d="M8 6V4.5A1.5 1.5 0 0 1 9.5 3h5A1.5 1.5 0 0 1 16 4.5V6"/><path d="M5.5 6l1 13.2A2 2 0 0 0 8.5 21h7a2 2 0 0 0 2-1.8L18.5 6"/><path d="M10 11v5M14 11v5"/></svg> Đã xóa <b>${esc(result.name)}</b>`, 'warn');
  } catch (error) {
    showToast('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M10.3 3.9 1.8 18.1A2 2 0 0 0 3.5 21h17a2 2 0 0 0 1.7-2.9L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/></svg> ' + esc(error.message), 'warn');
  }
}

/* ---------- toolbar ---------- */
$('search').oninput = e => { query = e.target.value.trim().toLowerCase(); render(); };
$('addBtn').onclick = () => openEditor(null);
$('resetBtn').onclick = () => {
  IngredientStore.refresh()
    .then(() => showToast('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M21 12a9 9 0 1 1-3-6.7"/><path d="M21 3v6h-6"/></svg> Đã tải lại dữ liệu từ database', 'ok'))
    .catch(error => showToast('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M10.3 3.9 1.8 18.1A2 2 0 0 0 3.5 21h17a2 2 0 0 0 1.7-2.9L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/></svg> ' + esc(error.message), 'warn'));
};

IngredientStore.onChange(render);

renderPills();
render();
