/* ================================================================
   ADMIN-02B · HOME BUILDER  —  the customer screen's front page
   ----------------------------------------------------------------
   Three decisions, kept on three cards because they are three different
   things and get changed at different times:

     the ORDER of the blocks        rarely, when the shop rethinks the
                                    screen
     what the featured strip HOLDS  often -- it is a promotion
     how bán-chạy is COUNTED        rarely, and it is a definition rather
                                    than a list

   Nothing here has a Save button. Every control writes on change and
   reports with a toast, the way the rest of this console does.

   WHY THIS IS ITS OWN PAGE AND NOT PART OF menu.html
       Quản lý Menu answers "what does the shop sell, and for how much".
       This answers "how is that arranged on the screen a customer looks
       at". They share MenuStore and nothing else -- an operator setting
       up a promotion is not editing prices, and an operator fixing a
       price is not rebuilding the front page.

       WHICH drinks are in the featured strip is still the star column on
       menu.html: it is a property of a drink and it belongs beside the
       drink. This page shows what that picking produced, and lets a
       drink be taken back out of the strip.
   ================================================================ */

/* Tên món và câu lỗi đi vào innerHTML -- showToast() gán thẳng
   t.innerHTML = msg (admin-guard.js:62) -- nên phải escape. Cùng khuôn với
   bin.js / errors.js / report.js / tickets.js. */
const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, c =>
  ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' })[c]);

if (!AdminAuth.initPage('home')) { /* redirected to login */ }

const $ = id => document.getElementById(id);

/* ---------- icons ----------
   Inline SVG, like everything else on these pages, so every one of them
   takes currentColor and inherits the size of the text it sits in. */
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
const ICON_X =
  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
  'stroke-width="2" stroke-linecap="round" aria-hidden="true" ' +
  'focusable="false"><path d="M18 6 6 18M6 6l12 12"/></svg>';
const ICON_CHECK =
  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
  'stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" ' +
  'aria-hidden="true" focusable="false"><path d="m4.5 12.5 5 5L19.5 7"/></svg>';
const ICON_UP =
  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
  'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" ' +
  'aria-hidden="true" focusable="false"><path d="M12 19V5M6 11l6-6 6 6"/></svg>';
const ICON_DOWN =
  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
  'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" ' +
  'aria-hidden="true" focusable="false"><path d="M12 5v14M6 13l6 6 6-6"/></svg>';
const ICON_WARN =
  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
  'stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" ' +
  'aria-hidden="true" focusable="false"><path d="M10.3 3.9 1.8 18.1A2 2 0 ' +
  '0 0 3.5 21h17a2 2 0 0 0 1.7-2.9L13.7 3.9a2 2 0 0 0-3.4 0Z"/>' +
  '<path d="M12 9v4M12 17h.01"/></svg>';


/* ---------- painting ----------
   All three panels repaint from the store IN PLACE rather than rewriting
   their card's innerHTML. This runs on every MenuStore change, including
   saves made from other controls, and rebuilding the markup underneath a
   heading somebody is halfway through typing would take their text away
   mid-word. Any input with focus is skipped, for the same reason. */

function setUnlessFocused(el, value){
  if(el && document.activeElement !== el) el.value = value;
}

/* ---------- the layout builder ---------- */
const BLOCK_INFO = {
  featured: {
    name: 'Món nổi bật',
    desc: 'Dải món do bạn tự chọn',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="m12 3.6 2.6 5.3 5.9.9-4.3 4.1 1 5.8-5.2-2.7-5.2 2.7 1-5.8L3.5 9.8l5.9-.9Z"/></svg>',
  },
  bestseller: {
    name: 'Bán chạy nhất',
    desc: 'Dải xếp hạng từ đơn đã bán',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M7 3h10v4a5 5 0 0 1-10 0Z"/><path d="M7 5H4.5v1A3.5 3.5 0 0 0 8 9.5"/><path d="M17 5h2.5v1A3.5 3.5 0 0 1 16 9.5"/><path d="M12 12v4M9 20h6M10 16h4l.6 4H9.4Z"/></svg>',
  },
  grid: {
    name: 'Tất cả món',
    desc: 'Lưới toàn bộ menu — không tắt được',
    fixed: true,
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>',
  },
};

const ICON_GRIP =
  '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" ' +
  'focusable="false"><circle cx="9" cy="6" r="1.6"/><circle cx="15" cy="6" r="1.6"/>' +
  '<circle cx="9" cy="12" r="1.6"/><circle cx="15" cy="12" r="1.6"/>' +
  '<circle cx="9" cy="18" r="1.6"/><circle cx="15" cy="18" r="1.6"/></svg>';

/* Whether a block is switched on. The grid is never off -- see
   save_layout_order() in admin_gui/serve.py, which refuses a layout
   without it. */
function blockEnabled(id){
  if(id === 'featured') return !!MenuStore.featuredConfig().enabled;
  if(id === 'bestseller') return !!MenuStore.bestsellerConfig().enabled;
  return true;
}

function renderBuilder(){
  const order = MenuStore.layout();
  const on = order.filter(id => blockEnabled(id));

  $('layoutSub').innerHTML =
    'Thứ tự hiện tại: <b>' +
    order.map(id => (BLOCK_INFO[id] || {}).name || id).join('</b> → <b>') +
    '</b>' +
    (on.length < order.length
      ? ` · ${order.length - on.length} khối đang tắt nên không hiện`
      : '');

  $('builder').innerHTML = order.map((id, i) => {
    const info = BLOCK_INFO[id] || {name:id, desc:''};
    const enabled = blockEnabled(id);
    return `
      <div class="bblock ${enabled ? '' : 'off'}" role="listitem"
           draggable="true" data-block="${id}" data-index="${i}">
        <span class="bgrip" aria-hidden="true">${ICON_GRIP}</span>
        <span class="bstep">${i + 1}</span>
        <span class="bic">${info.icon || ''}</span>
        <span class="btxt">
          <span class="bname">${escapeHtml(info.name)}</span>
          <span class="bdesc">${info.desc}${
            enabled ? '' : ' · <b>đang tắt</b>'}</span>
        </span>
        <span class="bmoves">
          <button type="button" class="iconbtn" data-up="${i}" ${i === 0 ? 'disabled' : ''}
                  title="Đưa lên trên" aria-label="Đưa ${escapeHtml(info.name)} lên trên">${ICON_UP}</button>
          <button type="button" class="iconbtn" data-down="${i}" ${i === order.length - 1 ? 'disabled' : ''}
                  title="Đưa xuống dưới" aria-label="Đưa ${escapeHtml(info.name)} xuống dưới">${ICON_DOWN}</button>
        </span>
      </div>`;
  }).join('');

  wireBuilder();
}

/* Reorder by index and send the WHOLE list. The server validates a
   layout as a set, and it could not do that from "move item 2 up". */
async function moveBlock(from, to){
  const order = MenuStore.layout().slice();
  if(to < 0 || to >= order.length || from === to) return;
  order.splice(to, 0, order.splice(from, 1)[0]);

  try {
    await MenuStore.saveLayout(order);
    showToast(`${ICON_CHECK} Đã lưu bố cục màn hình khách`, 'ok');
  } catch (error) {
    // The card has already moved on screen -- the browser did that.
    // Repainting from the untouched cache is what puts it back.
    renderBuilder();
    showToast(`${ICON_WARN} ${escapeHtml(error.message)}`, 'warn');
  }
}

function wireBuilder(){
  const root = $('builder');

  root.querySelectorAll('[data-up]').forEach(el => el.onclick = () => {
    const i = Number(el.dataset.up); moveBlock(i, i - 1);
  });
  root.querySelectorAll('[data-down]').forEach(el => el.onclick = () => {
    const i = Number(el.dataset.down); moveBlock(i, i + 1);
  });

  /* DRAG TO REORDER
     HTML5 drag events, not pointer maths: this console is a back-office
     tool driven with a mouse, and the browser already does the hit
     testing, the drag image and the cursor. The arrow buttons above are
     what makes the panel usable without a drag at all -- WCAG 2.2 AA
     asks for exactly that, and they are also what a trackpad reaches
     for.

     `dragged` is held rather than read out of dataTransfer on dragover:
     Firefox will not hand the payload back until the drop, so a preview
     that depended on it would show nothing until it was too late. */
  let dragged = null;

  root.querySelectorAll('.bblock').forEach(el => {
    el.ondragstart = e => {
      dragged = Number(el.dataset.index);
      el.classList.add('dragging');
      e.dataTransfer.effectAllowed = 'move';
      // Firefox refuses to start a drag at all without payload set.
      e.dataTransfer.setData('text/plain', el.dataset.block);
    };

    el.ondragend = () => {
      dragged = null;
      root.querySelectorAll('.bblock').forEach(b =>
        b.classList.remove('dragging', 'over-up', 'over-down'));
    };

    el.ondragover = e => {
      if(dragged === null) return;
      e.preventDefault();                 // this is what permits a drop
      e.dataTransfer.dropEffect = 'move';
      const to = Number(el.dataset.index);
      if(to === dragged) return;
      // The line is drawn on the side the card would land, so the
      // operator can see where it goes before letting go.
      el.classList.toggle('over-up', to < dragged);
      el.classList.toggle('over-down', to > dragged);
    };

    el.ondragleave = () => el.classList.remove('over-up', 'over-down');

    el.ondrop = e => {
      e.preventDefault();
      const to = Number(el.dataset.index);
      const from = dragged;
      dragged = null;
      root.querySelectorAll('.bblock').forEach(b =>
        b.classList.remove('dragging', 'over-up', 'over-down'));
      if(from !== null && from !== to) moveBlock(from, to);
    };
  });
}

/* ---------- how a strip is arranged ----------
   Four options, each drawn as a diagram of the arrangement rather than
   named alone: "spotlight" and "grid" are words describing a layout, and
   a layout is the thing words are worst at. The bars are the cards, in
   the shape and proportion they actually take on the store screen.

   Where they come from is in database/migrate_strip_style.sql. */
const STRIP_STYLE_OPTIONS = [
  {
    id:'carousel', name:'Cuộn ngang',
    desc:'Card như ngoài menu, một hàng, vuốt sang để xem tiếp.',
    diag:'<i class="c"></i><i class="c"></i><i class="c"></i>',
  },
  {
    id:'cinematic', name:'Ảnh tràn viền',
    desc:'Bỏ viền và thanh tên trắng — tên với giá nằm đè lên ảnh. Ảnh được cả tấm thay vì chia đôi với cái thanh.',
    diag:'<i class="t"><b></b></i><i class="t"><b></b></i><i class="t"><b></b></i>',
  },
  {
    id:'bubble', name:'Bong bóng tròn',
    desc:'Ảnh cắt tròn, bóng mềm, tên và giá nằm dưới. Thấp nhất trong năm kiểu vì không đóng khung gì cả.',
    diag:'<i class="o"></i><i class="o"></i><i class="o"></i><i class="o"></i>',
  },
  {
    id:'board', name:'Bảng menu quán',
    desc:'Không card. Tên món chữ lớn, dấu chấm nối sang giá. Kiểu duy nhất vẫn đọc tốt khi món chưa có ảnh.',
    diag:'<i class="l"><u></u></i><i class="l"><u></u></i><i class="l"><u></u></i>',
  },
  {
    id:'chart', name:'Số hạng khổng lồ',
    desc:'Số thứ hạng cỡ lớn làm nền, ảnh món đứng đè lên, kèm số ly đã bán. Chỉ dùng được cho Bán chạy.',
    diag:'<i class="n"><s></s></i><i class="n"><s></s></i>',
  },
];

/* `allowed` comes from the server, per module. The chart is only in the
   bán-chạy list -- offering it on the featured strip would be offering a
   setting the server then refuses, which is worse than not offering it. */
function renderStylePicker(host, current, allowed, onPick){
  host.innerHTML = STRIP_STYLE_OPTIONS
    .filter(opt => allowed.includes(opt.id))
    .map(opt => `
    <button type="button" class="styleopt ${opt.id === current ? 'on' : ''}"
            role="radio" aria-checked="${opt.id === current}"
            data-style="${opt.id}">
      <span class="stylediag d-${opt.id}" aria-hidden="true">${opt.diag}</span>
      <span class="stylename">${escapeHtml(opt.name)}</span>
      <span class="styledesc">${opt.desc}</span>
    </button>`).join('');

  host.querySelectorAll('[data-style]').forEach(el =>
    el.onclick = () => onPick(el.dataset.style));
}

/* ---------- the featured strip ---------- */
function renderFeatured(){
  const config = MenuStore.featuredConfig();
  const max = MenuStore.featuredMax();
  const picked = MenuStore.featuredItems();
  const showing = picked.filter(it => !it.soldOut);

  $('featEnabled').checked = !!config.enabled;
  setUnlessFocused($('featTitle'), config.title || '');

  // What the strip is actually doing right now, in one line. Every way it
  // can end up invisible is a setting on this card or the one above, and
  // none of them look like anything from the shop floor.
  $('featSub').innerHTML =
    !config.enabled
      ? `Đang <b>tắt</b> · ${picked.length}/${max} món đã chọn được giữ lại, ` +
        'nhưng dải không hiện trên màn khách'
      : !showing.length
        ? `Đang bật · <b>chưa có món nào hiện</b> — cần ít nhất một món đang bán`
        : `Đang bật · đang hiện <b>${showing.length}</b> món` +
          (picked.length > showing.length
            ? ` (${picked.length - showing.length} món bị giữ lại)` : '');

  renderStylePicker($('featStyle'), config.style, MenuStore.featuredStyles(),
                    style => saveFeaturedConfig({ style }));
  renderColumns('feat', config, columns => saveFeaturedConfig({ columns }));
  renderFeaturedPicked(picked, max);
}

function renderFeaturedPicked(picked, max) {
  if (!picked.length) {
    $('featPicked').innerHTML =
      '<div class="featempty">Chưa chọn món nào. Sang tab ' +
      '<a class="tablink" href="menu.html">Quản lý Menu</a> rồi bấm ngôi ' +
      'sao ở cột <b>“Nổi bật?”</b> để đưa món lên dải này ' +
      `(tối đa ${max} món).</div>`;
    return;
  }

  $('featPicked').innerHTML = picked.map(it => `
    <span class="featchip ${it.soldOut ? 'held' : ''}">
      <span class="cimg">${it.imageUrl
        ? `<img src="${it.imageUrl}" alt="" loading="lazy">` : it.emoji}</span>
      <span class="cname">${escapeHtml(it.name)}</span>
      ${it.soldOut ? '<span class="cwhy">Bị giữ lại</span>' : ''}
      <button type="button" class="cx" data-unfeature="${it.id}"
              title="Bỏ ${escapeHtml(it.name)} khỏi dải nổi bật"
              aria-label="Bỏ ${escapeHtml(it.name)} khỏi dải nổi bật">${ICON_X}</button>
    </span>`).join('') +
    `<span class="csub" style="margin-left:4px">${picked.length}/${max} · ` +
    'chọn thêm ở tab <a class="tablink" href="menu.html">Quản lý Menu</a></span>';

  $('featPicked').querySelectorAll('[data-unfeature]').forEach(el => {
    el.onclick = () => toggleFeatured(Number(el.dataset.unfeature), false);
  });
}

/* ---------- the bán-chạy strip ---------- */
const WINDOW_PRESETS = [
  { days: 7,   label: '1 tuần' },
  { days: 14,  label: '2 tuần' },
  { days: 30,  label: '1 tháng' },
  { days: 90,  label: '3 tháng' },
  { days: 365, label: '1 năm' },
];
const COUNT_PRESETS = [3, 4, 5, 6, 8];
const COLUMN_PRESETS = [1, 2, 3];

/* The column count only does something for the arrangements that stack.
   Shown for those and hidden for the rest -- the value stays in the
   database either way, so switching a strip to board, choosing two, and
   switching back does not lose the two. */
function renderColumns(prefix, config, onPick){
  const applies = MenuStore.columnStyles().includes(config.style);

  [$(prefix + 'ColsLabel'), $(prefix + 'Cols').closest('.numrow')]
    .forEach(el => { if(el) el.hidden = !applies; });

  if(!applies) return;

  setUnlessFocused($(prefix + 'Cols'), config.columns);
  renderPresets($(prefix + 'ColsPresets'), COLUMN_PRESETS, config.columns,
                COLUMN_PRESETS.map(n => n + ' cột'), onPick);
}

function renderBestseller(){
  const config = MenuStore.bestsellerConfig();
  const ranked = (config.drinkIds || []);

  $('bestEnabled').checked = !!config.enabled;
  setUnlessFocused($('bestTitle'), config.title || '');
  setUnlessFocused($('bestWindow'), config.windowDays);
  setUnlessFocused($('bestCount'), config.count);

  $('bestSub').innerHTML =
    !config.enabled
      ? 'Đang <b>tắt</b> · vẫn đếm nhưng dải không hiện trên màn khách'
      : !ranked.length
        ? `Đang bật · <b>chưa món nào bán được trong ${config.windowDays} ngày</b>` +
          ' — nới rộng khoảng thời gian bên dưới'
        : `Đang bật · top <b>${ranked.length}</b> món trong ` +
          `<b>${config.windowDays}</b> ngày qua`;

  renderPresets($('bestWindowPresets'), WINDOW_PRESETS.map(p => p.days),
                config.windowDays, WINDOW_PRESETS.map(p => p.label),
                days => saveBestseller({ windowDays: days }));
  renderPresets($('bestCountPresets'), COUNT_PRESETS, config.count,
                COUNT_PRESETS.map(String),
                count => saveBestseller({ count }));

  renderStylePicker($('bestStyle'), config.style, MenuStore.bestsellerStyles(),
                    style => saveBestseller({ style }));
  renderColumns('best', config, columns => saveBestseller({ columns }));
  renderBestsellerPreview(config);
}

/* Shortcut pills over a number box. They only FILL the box -- it stays
   the truth -- so the two can never show different answers, and a value
   the pills do not offer simply leaves none of them lit. */
function renderPresets(host, values, current, labels, onPick){
  host.innerHTML = values.map((value, i) =>
    `<button type="button" class="preset ${Number(current) === value ? 'on' : ''}"
             data-value="${value}" aria-pressed="${Number(current) === value}"
     >${labels[i]}</button>`).join('');
  host.querySelectorAll('[data-value]').forEach(el =>
    el.onclick = () => onPick(Number(el.dataset.value)));
}

/* The ranking those settings actually produce. This is the whole point of
   the card: the old "Bestseller" category claimed to be this and was not,
   so the replacement has to be checkable without leaving the page. */
function renderBestsellerPreview(config){
  const ids = config.drinkIds || [];
  const sold = config.sold || {};

  if(!ids.length){
    $('bestPreview').innerHTML =
      '<div class="featempty">Chưa có món nào bán được trong ' +
      `<b>${config.windowDays} ngày</b> qua, nên dải sẽ không hiện. ` +
      'Nới rộng khoảng thời gian ở trên để tính xa hơn.</div>';
    return;
  }

  $('bestPreview').innerHTML = ids.map((id, i) => {
    const it = MenuStore.getItem(id);
    const name = it ? it.name : '#' + id;
    return `
      <span class="featchip rankchip">
        <span class="crank">#${i + 1}</span>
        <span class="cimg">${it && it.imageUrl
          ? `<img src="${it.imageUrl}" alt="" loading="lazy">`
          : (it ? it.emoji : '')}</span>
        <span class="cname">${name}</span>
        <span class="csold">${sold[String(id)] || 0} ly</span>
      </span>`;
  }).join('');
}

/* ---------- writes ----------
   Every one of these reports the way the rest of this console does: a
   toast on success, and a toast naming the reason on refusal. A control
   that silently springs back is the one failure nobody can diagnose. */

/* Only ever called with `false` here -- the X on a chip. Putting a drink
   INTO the strip is the star column on menu.html, beside the drink. */
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

async function saveFeaturedConfig(patch) {
  const next = { ...MenuStore.featuredConfig(), ...patch };
  try {
    await MenuStore.saveFeaturedConfig(next);
    showToast(`${ICON_CHECK} Đã lưu module “Món nổi bật”`, 'ok');
  } catch (error) {
    renderFeatured();
    showToast(`${ICON_WARN} ${escapeHtml(error.message)}`, 'warn');
  }
}

async function saveBestseller(patch) {
  const next = { ...MenuStore.bestsellerConfig(), ...patch };
  try {
    await MenuStore.saveBestsellerConfig(next);
    showToast(`${ICON_CHECK} Đã lưu module “Bán chạy nhất”`, 'ok');
  } catch (error) {
    renderBestseller();
    showToast(`${ICON_WARN} ${escapeHtml(error.message)}`, 'warn');
  }
}

$('featEnabled').onchange = e =>
  saveFeaturedConfig({ enabled: e.target.checked });
$('bestEnabled').onchange = e =>
  saveBestseller({ enabled: e.target.checked });

// On change, not on input: a save per keystroke would be a database write
// and a full menu republish for every letter typed into a heading.
$('featTitle').onchange = e => saveFeaturedConfig({ title: e.target.value });
$('bestTitle').onchange = e => saveBestseller({ title: e.target.value });
$('bestWindow').onchange = e => saveBestseller({ windowDays: e.target.value });
$('bestCount').onchange = e => saveBestseller({ count: e.target.value });
$('featCols').onchange = e => saveFeaturedConfig({ columns: e.target.value });
$('bestCols').onchange = e => saveBestseller({ columns: e.target.value });

function renderStorePanels(){
  renderBuilder();
  renderFeatured();
  renderBestseller();
}

/* ---------- thu gọn / mở lại từng module ----------
   Three cards, and an operator is nearly always here for one of them: a
   promotion goes in the featured card and nothing else on the page is
   touched. Folded, the other two are one line each -- and that line is
   their csub, which already says what the module is doing, so nothing is
   lost by shutting a card that was only being read.

   Nothing is hidden from the form: every input stays in the DOM holding
   its value, and each control still writes on change the way it always
   did. This is a way of looking at the page, not a way of turning part of
   it off. */
const CARDS_KEY = 'admin.home.collapsed';

/* Which cards were shut last time. In localStorage rather than the
   database: it is how one person likes to look at the page on one
   machine, not a setting for the shop. Wrapped, because a browser told to
   block site data throws on the read itself rather than returning null. */
function readShutCards() {
  try { return new Set(JSON.parse(localStorage.getItem(CARDS_KEY)) || []); }
  catch { return new Set(); }
}
function writeShutCards(ids) {
  try { localStorage.setItem(CARDS_KEY, JSON.stringify([...ids])); }
  catch { /* private window, or site data blocked -- the page still works */ }
}

function setCardShut(card, shut) {
  const button = card.querySelector('[data-card-toggle]');
  card.toggleAttribute('data-collapsed', shut);
  button.setAttribute('aria-expanded', String(!shut));
}

const shutAtLoad = readShutCards();
document.querySelectorAll('[data-card-toggle]').forEach(button => {
  // The body's id names the card: it is already there for aria-controls,
  // and it survives an edit to the heading text.
  setCardShut(button.closest('.card'), shutAtLoad.has(button.getAttribute('aria-controls')));
});

document.addEventListener('click', event => {
  const button = event.target.closest('[data-card-toggle]');
  if (!button) return;
  const card = button.closest('.card');
  const id = button.getAttribute('aria-controls');
  const shut = !card.hasAttribute('data-collapsed');
  setCardShut(card, shut);
  const ids = readShutCards();
  ids[shut ? 'add' : 'delete'](id);
  writeShutCards(ids);
});

/* ---------- toolbar ---------- */
$('resetBtn').onclick = () => {
  MenuStore.refresh()
    .then(() => showToast(`${ICON_CHECK} Đã tải lại dữ liệu từ database`, 'ok'))
    .catch(() => showToast(`${ICON_WARN} Không thể tải lại database`, 'warn'));
};

// Repaint on any store change. This covers a price or a star edited in
// another tab: the featured chips and the bán-chạy preview are both
// drawn from drinks, and a stale name on a chip is a wrong answer.
MenuStore.onChange(renderStorePanels);

renderStorePanels();
