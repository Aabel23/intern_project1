/* ---------------- DATA ----------------
   The menu comes from the database, not from this file. Rebuild it with:

       python3 -m store_gui.sync_menu

   which writes menu-data.js next door and drinks-pos.html loads it first.
   Every drink, price, category, stock flag and per-drink option below is
   whatever that script found. Without it the page still opens, on the small
   fallback menu at the bottom of this block, so a missing generated file is
   visible rather than a blank screen. */
const MENU = (typeof window !== 'undefined' && window.MENU_DATA) || null;

/* Toppings are free. There is no price column for an ingredient, so what
   one cost used to be a table of numbers invented by this screen -- and a
   customer removing a topping they did not want would watch the price
   drop, which made the drink look like a bundle of parts rather than a
   drink. Ticking and unticking now changes what is poured and nothing
   else. If toppings are ever charged for, the price belongs in the
   ingredient table where the rest of the menu lives, not here. */

const FALLBACK_MENU = {
  categories:[{id:'all', name:'All Menu', count:0}],
  drinks:[], toppings:[],
  /* No drinks means nothing to put in either strip, so both are off on
     this fallback rather than headings over blank rows. */
  featured:{enabled:false, title:'', drinkIds:[]},
  bestseller:{enabled:false, title:'', drinkIds:[], sold:{}},
  layout:['featured', 'bestseller', 'grid'],
};

const MENU_SOURCE = MENU || FALLBACK_MENU;

/* One SVG per category slot, cycled by toCats() below.

   These were emoji. An emoji is a picture of a thing drawn by whichever font
   the OS happens to ship: it changes size, weight and style per device, it
   ignores currentColor -- so it stayed full-colour inside the filled pill of
   the active category, where everything else had gone white -- and it cannot
   be given a stroke weight that matches the rest of the page. Drawn icons
   take the pill's colour with it. */
const ICON = (paths)=>'<svg width="20" height="20" viewBox="0 0 24 24" fill="none" '+
  'stroke="currentColor" stroke-width="1.9" stroke-linecap="round" '+
  'stroke-linejoin="round" aria-hidden="true" focusable="false">'+paths+'</svg>';

const ICON_GLASS  = ICON('<path d="M6 8h12l-1.2 11.2a2 2 0 0 1-2 1.8H9.2a2 2 0 0 1-2-1.8Z"/><path d="M6.6 12.4h10.8"/><path d="M12 8V4.6"/><path d="M12 4.6c0-1 .9-1.8 2-1.8"/>');
const ICON_COFFEE = ICON('<path d="M4 9h13v5a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5Z"/><path d="M17 10.5h1.5a2.5 2.5 0 0 1 0 5H17"/><path d="M8 3v2.5M12 2.5V5"/>');
const ICON_TEA    = ICON('<path d="M5.5 7h13l-1.1 12.2a2 2 0 0 1-2 1.8H8.6a2 2 0 0 1-2-1.8Z"/><path d="M9 7 10.5 3h3L15 7"/><circle cx="10" cy="16.5" r="1.1"/><circle cx="13.6" cy="17.4" r="1.1"/>');
const ICON_CAN    = ICON('<rect x="7" y="3" width="10" height="18" rx="3"/><path d="M7 8h10M7 16h10"/>');
const ICON_TAIL   = ICON('<path d="M4 4h16l-8 8Z"/><path d="M12 12v8M8.5 20h7"/><path d="m17 4-2.5 2.5"/>');
const ICON_SHAKE  = ICON('<path d="M6.5 9h11l-1 10.2a2 2 0 0 1-2 1.8h-5a2 2 0 0 1-2-1.8Z"/><path d="M5.5 9c0-3 2.9-5.5 6.5-5.5S18.5 6 18.5 9"/><path d="M14.5 3.2 16.8 1"/>');
const ICON_SUN    = ICON('<circle cx="12" cy="12" r="4.2"/><path d="M12 2v2.4M12 19.6V22M4.2 4.2l1.7 1.7M18.1 18.1l1.7 1.7M2 12h2.4M19.6 12H22M4.2 19.8l1.7-1.7M18.1 5.9l1.7-1.7"/>');
const ICON_STAR   = ICON('<path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1-5.4-2.9-5.4 2.9 1-6.1L3.2 9.5l6.1-.9Z"/>');
const ICON_GRID   = ICON('<rect x="3" y="3" width="7.5" height="7.5" rx="2"/><rect x="13.5" y="3" width="7.5" height="7.5" rx="2"/><rect x="3" y="13.5" width="7.5" height="7.5" rx="2"/><rect x="13.5" y="13.5" width="7.5" height="7.5" rx="2"/>');

/* Cycled as a last resort. Categories are whatever the shop typed into the
   database, so there will always be one this list has never heard of. */
const CAT_ICONS = [ICON_GLASS, ICON_TEA, ICON_CAN, ICON_SHAKE, ICON_TAIL, ICON_COFFEE];

/* Matched on the category's own name first, in both languages the database
   is filled in with. Cycling by row number alone put a coffee cup on
   "Summer", a can on "Tea" and a cocktail glass on "Coffee" -- six icons
   that were decoration pretending to be labels. Anything unmatched still
   falls through to the cycle, so a new category is never iconless. */
const CAT_ICON_RULES = [
  [/all|menu|tất ?cả|toàn/i,                      ICON_GRID],
  [/best|hot|popular|top|favou?rite|bán ?chạy|nổi/i, ICON_STAR],
  [/coffee|cafe|cà ?phê|espresso|latte/i,         ICON_COFFEE],
  [/tea|trà|matcha/i,                             ICON_TEA],
  [/soda|sparkl|fizz|tonic|cola|có ?ga/i,         ICON_CAN],
  [/milk|shake|sữa|yog(h)?urt|sinh ?tố|smoothie/i, ICON_SHAKE],
  [/cocktail|mocktail|mix|signature|đặc ?biệt/i,  ICON_TAIL],
  [/summer|fresh|fruit|juice|ice|trái ?cây|nước ?ép|mùa ?hè|mát/i, ICON_SUN],
];
function catIcon(name, i){
  const hit = CAT_ICON_RULES.find(([re])=>re.test(name || ''));
  return hit ? hit[1] : CAT_ICONS[i % CAT_ICONS.length];
}

/* The two shapes this page works in, derived from whatever menu-data.js
   holds. Written as functions rather than inline maps because they run
   twice: once at load, and again whenever the file is rebuilt -- and a
   second copy of these mappings would drift from the first the day anybody
   added a field. */
function toCats(source){
  return source.categories.map((c,i)=>({
    id:c.id, name:c.name, count:c.count,
    icon:catIcon(c.name, i),
  }));
}

const CATS = toCats(MENU_SOURCE);

/* id is this page's own row number; drinkId is the machine's drink_id and
   becomes the payload's SKU. options are the ingredients this drink's recipe
   actually contains, which is what the detail panel is allowed to offer. */
function toItems(source){
  return source.drinks.map((d,i)=>({
    id:i+1,
    drinkId:d.drinkId,
    name:d.name,
    cat:d.category,
    catIds:(d.categoryIds||[]).map(c=>'c'+c),
    price:d.price,
    emoji:d.emoji,
    image:d.image,
    orderable:d.orderable,
    reason:d.unavailableReason,
    options:d.options||[],
  }));
}

const ITEMS = toItems(MENU_SOURCE);

/* The two strips and the page order, as the admin console set them up.

   WHAT IS DECIDED WHERE
     WHICH drinks are in a strip is decided by store_gui/sync_menu.py, not
     here. Its drinkIds already exclude anything the machine cannot pour,
     and for the bán-chạy strip they are a ranking this page has no way to
     recompute -- the sales are in MySQL and this file never sees it. So
     the page must NOT re-derive either list by filtering ITEMS; that
     would put dead cards back in one and invent the other.

     Whether a strip is drawn, under what heading, and in what order the
     blocks stack, is decided by the operator and travels in the same
     file.

   Defaults for a menu-data.js generated before a strip existed: off. An
   old file cannot have picked any drinks, so the alternative is an empty
   heading over nothing. */
function toStrip(raw, fallbackTitle){
  raw = raw || {};
  return {
    enabled: raw.enabled === true,
    title: raw.title || fallbackTitle,
    drinkIds: Array.isArray(raw.drinkIds) ? raw.drinkIds.slice() : [],
    // Bestseller only; harmless on the featured strip, which never reads
    // it. Kept as one shape so createStrip() has one thing to expect.
    windowDays: Number(raw.windowDays) || 30,
    sold: raw.sold || {},
    // How the strip arranges its cards. Validated in sync_menu.py, and
    // again here for a menu-data.js written before styles existed.
    style: STRIP_STYLES.includes(raw.style) ? raw.style : 'carousel',
    // Only the stacked arrangements read this; see COLUMN_STYLES in
    // store_gui/sync_menu.py. Clamped rather than trusted, because a
    // column count of 0 would collapse the whole strip.
    columns: Math.min(3, Math.max(1, Number(raw.columns) || 1)),
  };
}

/* The arrangements a strip can take. All four draw the SAME cards from
   the same data -- only the container changes -- except `list`, which is
   a row rather than a card and says so below. */
const STRIP_STYLES = ['carousel', 'cinematic', 'board', 'bubble', 'chart'];

/* The two that stack, and so have a column count to answer. The other
   three run sideways and scroll. */
const COLUMN_STYLES = ['board', 'chart'];

const FEATURED = toStrip(MENU_SOURCE.featured, 'Món nổi bật');
const BESTSELLER = toStrip(MENU_SOURCE.bestseller, 'Bán chạy nhất');

/* The order the blocks stack down the page. Repaired rather than trusted:
   sync_menu.py already drops unknown names and guarantees 'grid' is in
   it, but this file also runs against a menu-data.js written by an older
   version, and a layout with no 'grid' would be a store screen with no
   drinks on it. An array, so adoptMenu() can refill it in place. */
const LAYOUT_FALLBACK = ['featured', 'bestseller', 'grid'];

function toLayout(source){
  const wanted = Array.isArray(source.layout) ? source.layout : [];
  const order = wanted.filter(
    (name, i) => LAYOUT_FALLBACK.includes(name) && wanted.indexOf(name) === i);

  LAYOUT_FALLBACK.forEach(name => { if(!order.includes(name)) order.push(name); });
  return order;
}

const LAYOUT = toLayout(MENU_SOURCE);

/* There is no size. The machine pours one glass on one load cell, and
   the recipe's grams are written for that glass -- so Regular, Medium and
   Large poured an identical cup and differed only in what they charged.

   Bringing sizes back means: scaled weights in the QR payload (the
   protocol already carries those, it is how the sugar dial works), a
   per-drink price step rather than a flat one -- the recipes run from 50g
   to 275g, so one surcharge cannot fit them all -- and a capacity check in
   order/qr_to_recipe.py, because nothing in the machine knows how big the
   glass is and 1.5x SO1 is 412g. */

const toppingOptions = item =>
  (item.options||[]).filter(o=>o.kind==='boolean');
const percentOption = item =>
  (item.options||[]).find(o=>o.kind==='percentage') || null;
const pct = value => (Math.round(value*10)/10).toString().replace(/\.0$/,'');

/* A dial opens at 100% -- the amount the recipe already pours -- and a
   topping opens TICKED, because being in the recipe is the statement that
   it belongs in the drink. Unticking is what removes it. An out-of-stock
   topping is never pre-ticked, since it cannot be added.

   sync_menu.py sends those defaults with each option, so this reads them
   rather than assuming; they are just no longer per-ingredient columns. */
function defaultSelection(item){
  const dial = percentOption(item);
  return {
    sugar: dial ? pct(dial.default) : '100',
    toppings: new Set(
      toppingOptions(item).filter(t=>t.default && t.inStock)
                          .map(t=>t.ingredientId)),
    notes:'',
  };
}

/* ---------------- STATE ----------------
   The machine pours one cup at a time, so a bill holds exactly one drink
   and never a quantity. `order` is that drink, or null when the bill is
   empty — deliberately a single object rather than an array of one, so
   there is no shape that could hold two. */
let activeCat = 'all';
let selected = null;          // selected item object
/* WHICH block the selected drink was pressed IN -- 'grid', or a strip's
   section id. Never cleared on its own: selMark() below only consults it
   when `selected` is set, so a leftover value cannot light anything up. */
let selectedIn = null;
let sel = {sugar:'100', toppings:new Set(), notes:''};
let order = null;             // {name,emoji,drinkId,size,sugar,toppingIds,toppings,unit,notes}

/* ---------------- TOPBAR: DATE, CLOCK, MENU FRESHNESS ----------------
   This page is a snapshot. Stock and availability are whatever
   store_gui/sync_menu.py found when it last ran, and nothing here polls
   the database -- so a drink can go out of stock and the screen would
   happily keep selling it. Showing the snapshot's age is what turns that
   from an invisible fault into an obvious one. */
const MENU_STALE_AFTER_MINUTES = 10;

function renderTopbar(){
  const now = new Date();
  setText('today', now.toLocaleDateString(undefined,
    {weekday:'short', day:'numeric', month:'short', year:'numeric'}));
  setText('clockNow', now.toLocaleTimeString(undefined,
    {hour:'2-digit', minute:'2-digit'}));

  const chip = document.getElementById('syncChip');
  const stamp = MENU && MENU.generatedAt ? Date.parse(MENU.generatedAt) : NaN;

  if(!Number.isFinite(stamp)){
    setText('syncAge', 'menu: never synced');
    chip.classList.add('stale');
    return;
  }

  if(menuStale){
    // A rebuild is on disk and this page is still showing the old one,
    // held back until the customer finishes.
    setText('syncAge', 'menu: update ready');
    chip.classList.add('stale');
    return;
  }

  const minutes = Math.max(0, Math.round((now - stamp) / 60000));
  const age = minutes < 1 ? 'just now'
            : minutes < 60 ? minutes + ' min ago'
            : Math.floor(minutes/60) + 'h ' + (minutes%60) + 'm ago';
  setText('syncAge', 'menu: ' + age);
  chip.classList.toggle('stale', minutes >= MENU_STALE_AFTER_MINUTES);
}

function setText(id, value){
  const el = document.getElementById(id);
  if(el) el.textContent = value;
}

/* The glyphs that sit inside buttons and empty states. Same reason as
   CAT_ICONS: these were characters from an emoji font (a printer, a play
   triangle, a QR block), which meant the size and colour of the icon on the
   Print button were decided by the device rather than by this sheet. */
const ICON_PLUS   = ICON('<path d="M12 5v14M5 12h14"/>');
const ICON_REDO   = ICON('<path d="M21 12a9 9 0 1 1-3-6.7"/><path d="M21 3v6h-6"/>');
const ICON_PRINT  = ICON('<path d="M6 9V3h12v6"/><path d="M6 18H5a2 2 0 0 1-2-2v-4a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2h-1"/><rect x="7" y="14" width="10" height="7" rx="1"/>');
const ICON_PLAY   = ICON('<path d="M7 4.5 19 12 7 19.5Z"/>');
const ICON_CHECK  = ICON('<path d="m4.5 12.5 5 5L19.5 7"/>');
const ICON_CUP    = ICON('<path d="M6 8h12l-1.2 11.2a2 2 0 0 1-2 1.8H9.2a2 2 0 0 1-2-1.8Z"/><path d="M6.6 12.4h10.8"/><path d="M12 8V4.6"/><path d="M12 4.6c0-1 .9-1.8 2-1.8"/>');
const ICON_BILL   = ICON('<path d="M4 2v20l2.5-1.5L9 22l2.5-1.5L14 22l2.5-1.5L19 22V2l-2.5 1.5L14 2l-2.5 1.5L9 2 6.5 3.5Z"/><path d="M8 8h8M8 12h8M8 16h5"/>');
const ICON_WARN   = ICON('<path d="M10.3 3.9 1.8 18.1A2 2 0 0 0 3.5 21h17a2 2 0 0 0 1.7-2.9L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/>');

/* The empty states. Bigger, thinner, and centred in their own disc. */
const ICON_BIG = (paths)=>'<svg width="46" height="46" viewBox="0 0 24 24" fill="none" '+
  'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" '+
  'stroke-linejoin="round" aria-hidden="true" focusable="false">'+paths+'</svg>';
const ICON_BIG_CUP  = ICON_BIG('<path d="M6 8h12l-1.2 11.2a2 2 0 0 1-2 1.8H9.2a2 2 0 0 1-2-1.8Z"/><path d="M6.6 12.4h10.8"/><path d="M12 8V4.6"/><path d="M12 4.6c0-1 .9-1.8 2-1.8"/>');
const ICON_BIG_BILL = ICON_BIG('<path d="M4 2v20l2.5-1.5L9 22l2.5-1.5L14 22l2.5-1.5L19 22V2l-2.5 1.5L14 2l-2.5 1.5L9 2 6.5 3.5Z"/><path d="M8 8h8M8 12h8M8 16h5"/>');

/* ---------------- RENDER: CATS ---------------- */
const catsEl = document.getElementById('cats');
function renderCats(){
  catsEl.innerHTML = CATS.map(c=>`
    <div class="cat ${c.id===activeCat?'active':''}" data-cat="${c.id}">
      <div class="icon">${c.icon}</div>
      <div class="name">${escapeText(c.name)}</div>
      <div class="count">${c.count} Items</div>
    </div>`).join('');
  catsEl.querySelectorAll('.cat').forEach(el=>{
    el.onclick=()=>{
      if(catDrag.moved) return; // ignore the click that follows a drag
      activeCat=el.dataset.cat;renderCats();
      animateHeight(gridEl, renderGrid);
    };
  });
  updateCatSlider();
}

/* ---------------- UTIL: animate an element's height across a content swap ---------------- */
function animateHeight(el, changeFn){
  const startH = el.getBoundingClientRect().height;
  changeFn();

  // Measure the new content's natural height with height:auto — measuring while
  // still pinned to startH is wrong: if the new content is shorter, nothing
  // overflows, so scrollHeight just reports startH back and nothing animates.
  el.style.transition = 'none';
  el.style.height = 'auto';
  const endH = el.getBoundingClientRect().height;

  // Snap back to the old height with no transition (invisible, same frame).
  el.style.height = startH+'px';
  el.style.overflow = 'hidden';
  void el.offsetHeight; // force reflow so startH is committed before re-enabling the transition
  el.style.transition = '';

  requestAnimationFrame(()=>{
    el.style.height = endH+'px';
  });

  el.addEventListener('transitionend', function done(e){
    if(e.propertyName!=='height') return;
    el.style.height = '';
    el.style.overflow = '';
    el.removeEventListener('transitionend', done);
  });
}

/* ---------------- WHICH WAY THE HAND WENT ----------------
   Three scrollers overlap on this page: the category rail and the two
   strips run sideways, and all of them sit inside a column that runs down.
   A press on a featured card is not yet a sideways gesture, and it is not
   yet a downward one either -- so until it has moved far enough to say
   which, no scroller may claim it. Whichever axis the hand commits to
   first owns the drag for the rest of it; the other stays still.

   Without this the strips took every press that landed on them and read
   only its horizontal part, so pulling down on a featured drink moved
   nothing and ended in a click that opened the drink.

   Six pixels: below that a press is a tap with a shaky hand, not a
   direction.

   SIX IS A MOUSE'S NUMBER, AND THIS SCREEN IS A FINGER'S
     A mouse lands where it is put and leaves from where it landed, so six
     pixels of travel really is a decision. A fingertip is a soft contact
     patch a centimetre across: it rolls as it presses, and the point the
     driver reports wanders ten or fifteen pixels through an ordinary tap
     that the customer would swear never moved.

     Measured on this kiosk 2026-09-03: a press with twelve pixels of
     drift produced no drink. The card lit under the finger, the panel
     never came, and nothing was logged, because as far as this code was
     concerned the customer had scrolled. A mouse on the same tile, drift
     zero, opened it every time -- which is why it looked like a fault in
     the touch screen rather than in a threshold.

     Firefox does not take over first: its own pan threshold is wider
     than six pixels, so a tap in between is a scroll to us and a click to
     the browser. Everything in that gap fell down it.

   ONE NUMBER, NOT TWO, BECAUSE THIS BROWSER CANNOT TELL THEM APART
     The obvious repair is a small slop for a mouse and a large one for a
     finger, chosen per gesture from PointerEvent.pointerType. It does not
     work here. Firefox on this machine does not recognise the panel as a
     touch device at all: `(any-pointer: coarse)` is false and finger
     presses arrive as pointerType 'mouse', measured 2026-09-03 by
     watching a twelve-pixel press still be discarded with the two-number
     version in place. A test that cannot see the finger cannot size the
     threshold for it.

     So there is one number and it is the finger's. The cost is that a
     mouse must also travel eighteen pixels before the column starts
     following it, which on a screen meant to be touched is the cheaper of
     the two mistakes: a slightly late scroll, against a drink that will
     not open. */
const DRAG_SLOP = 18;

function dragAxis(dx, dy){
  if(Math.max(Math.abs(dx), Math.abs(dy)) < DRAG_SLOP) return null;
  return Math.abs(dx) >= Math.abs(dy) ? 'x' : 'y';
}

/* ---------------- CATS: DRAG-TO-SCROLL + SLIDER ---------------- */
const catsTrack = document.getElementById('catsTrack');
const catsThumb = document.getElementById('catsThumb');
let catDrag = {down:false, startX:0, startY:0, scrollStart:0, moved:false, axis:null};
let thumbDrag = {down:false, startX:0, startScroll:0};

function updateCatSlider(){
  const trackW = catsTrack.clientWidth;
  const ratio = catsEl.clientWidth / catsEl.scrollWidth;
  if(ratio>=1){ catsTrack.style.visibility='hidden'; return; }
  catsTrack.style.visibility='visible';
  const thumbW = Math.max(30, trackW*ratio);
  const maxScroll = catsEl.scrollWidth - catsEl.clientWidth;
  const maxThumbX = trackW - thumbW;
  const x = maxScroll ? (catsEl.scrollLeft/maxScroll)*maxThumbX : 0;
  catsThumb.style.width = thumbW+'px';
  catsThumb.style.transform = `translateX(${x}px)`;
}

catsEl.addEventListener('pointerdown', e=>{
  // Cleared for EVERY press, including the touches declined below. A
  // .moved left latched true by the last mouse drag goes on swallowing
  // taps for the life of the page, and nothing else ever clears it.
  catDrag.moved=false;
  if(e.pointerType === 'touch') return;   // the browser already pans it
  catDrag.down=true; catDrag.axis=null;
  catDrag.startX=e.pageX; catDrag.startY=e.pageY;
  catDrag.scrollStart=catsEl.scrollLeft;
});
window.addEventListener('pointermove', e=>{
  if(!catDrag.down) return;
  const dx = e.pageX - catDrag.startX, dy = e.pageY - catDrag.startY;
  if(!catDrag.axis){
    catDrag.axis = dragAxis(dx, dy);
    if(!catDrag.axis) return;
    // A committed direction is a drag either way: a pull downwards off a
    // category must not also switch the category on the way past.
    catDrag.moved = true;
    if(catDrag.axis==='x') catsEl.classList.add('dragging');
  }
  if(catDrag.axis!=='x') return;
  catsEl.scrollLeft = catDrag.scrollStart - dx;
});
function endCatDrag(){ catDrag.down=false; catsEl.classList.remove('dragging'); }
window.addEventListener('pointerup', endCatDrag);
window.addEventListener('pointercancel', endCatDrag);
catsEl.addEventListener('scroll', updateCatSlider);

catsThumb.addEventListener('pointerdown', e=>{
  e.stopPropagation();
  thumbDrag.down=true; thumbDrag.startX=e.pageX; thumbDrag.startScroll=catsEl.scrollLeft;
});
window.addEventListener('pointermove', e=>{
  if(!thumbDrag.down) return;
  const trackW = catsTrack.clientWidth;
  const ratio = catsEl.clientWidth/catsEl.scrollWidth;
  const thumbW = Math.max(30, trackW*ratio);
  const maxThumbX = trackW-thumbW;
  const maxScroll = catsEl.scrollWidth - catsEl.clientWidth;
  const dx = e.pageX - thumbDrag.startX;
  catsEl.scrollLeft = thumbDrag.startScroll + (maxThumbX ? (dx/maxThumbX)*maxScroll : 0);
});
window.addEventListener('pointerup', ()=>thumbDrag.down=false);
window.addEventListener('pointercancel', ()=>thumbDrag.down=false);

window.addEventListener('resize', updateCatSlider);

/* ---------------- MENU COLUMN: DRAG-TO-SCROLL ----------------
   Two separate things stopped a pull on the menu from moving it.

   First, the photographs. An <img> is natively draggable: pressing on a
   drink and moving started the browser's own drag-and-drop -- a ghost of
   the picture following the hand, and a pointercancel that ends whatever
   gesture was being read. The strips worked around it card by card. Nothing
   on this page is ever meant to be dragged out of it, so the page opts out
   once, for every photo, instead.

   Second, the column itself. The category rail and both strips are dragged
   by hand; the column they sit in was not, so on anything driven by a
   pointer the only way down the menu was the page dots -- which jump a
   whole screen at a time, and are not the gesture anybody tries first.

   Touch is left alone deliberately: the kiosk's screen pans this column
   natively, with momentum none of this reproduces, and writing scrollTop
   from here as well would move it twice for one finger. */
document.addEventListener('dragstart', e=>{
  if(e.target && e.target.tagName === 'IMG') e.preventDefault();
});

const leftDragEl = document.querySelector('.left');
let menuDrag = {down:false, startX:0, startY:0, scrollStart:0, moved:false, axis:null};

/* Two things inside the column are not the column's to read: a drag in a
   text field is a text selection, and the category slider is a scrollbar
   thumb, where the whole gesture means a position in a track.

   The strips are deliberately NOT on this list. A press that lands on a
   featured card belongs to whichever scroller the hand then moves towards
   -- see dragAxis() -- and it was leaving them out that made a pull
   downwards on the top two rows do nothing but open the drink. */
const OWN_GESTURE = '.catslider, input, textarea';

leftDragEl.addEventListener('pointerdown', e=>{
  // See catsEl above: cleared before the touch bow-out, never after it.
  menuDrag.moved = false;
  if(e.pointerType === 'touch') return;          // the browser already pans it
  if(e.pointerType === 'mouse' && e.button !== 0) return;
  if(e.target.closest && e.target.closest(OWN_GESTURE)) return;
  menuDrag.down = true; menuDrag.axis = null;
  menuDrag.startX = e.pageX; menuDrag.startY = e.pageY;
  menuDrag.scrollStart = leftDragEl.scrollTop;
});
window.addEventListener('pointermove', e=>{
  if(!menuDrag.down) return;
  const dx = e.pageX - menuDrag.startX, dy = e.pageY - menuDrag.startY;
  if(!menuDrag.axis){
    menuDrag.axis = dragAxis(dx, dy);
    if(!menuDrag.axis) return;
    // Either direction counts as a drag: a sideways pull across a menu
    // card is the strip being scrolled, not that drink being chosen.
    menuDrag.moved = true;
    // .left is scroll-behavior:smooth, for the page dots. Left on, every
    // scrollTop written below would be animated towards rather than set,
    // and the menu would trail a whole animation behind the hand. Added
    // only once the column has actually taken the drag.
    if(menuDrag.axis === 'y') leftDragEl.classList.add('dragging');
  }
  if(menuDrag.axis !== 'y') return;
  leftDragEl.scrollTop = menuDrag.scrollStart - dy;
});
/* .moved is not cleared here: the click that ends the drag arrives after
   pointerup, and renderGrid() reads it to tell a scroll from a tap. The
   next pointerdown clears it. */
function endMenuDrag(){
  menuDrag.down = false; leftDragEl.classList.remove('dragging');
}
window.addEventListener('pointerup', endMenuDrag);
window.addEventListener('pointercancel', endMenuDrag);

/* ---------------- RENDER: GRID ---------------- */
const gridEl = document.getElementById('grid');

/* What the menu block calls itself when it claims a selection. The strips
   use their own section id ('featured', 'bestseller'), so every block on
   the page has one name and no two share it. */
const GRID_SOURCE = 'grid';
function renderGrid(){
  const q = document.getElementById('search').value.trim().toLowerCase();
  const list = ITEMS.filter(it=>{
    const okCat = activeCat==='all' || it.catIds.includes(activeCat);
    const okQ = !q || it.name.toLowerCase().includes(q);
    return okCat && okQ;
  });
  // An unorderable drink is still drawn, so customers can see it exists and
  // why it cannot be had. It simply carries no click handler.
  // The card is the photograph, and the two facts a customer compares -- the
  // price and the category -- are drawn on it rather than queued underneath.
  // The name gets the shelf below to itself, next to a target that says the
  // card opens onto something.
  gridEl.innerHTML = list.map(it=>`
    <div class="item${selMark(it, GRID_SOURCE)} ${it.orderable?'':'out'}"
         data-id="${it.id}" ${it.orderable?'':'aria-disabled="true"'}>
      <div class="thumb">${it.image
        ? `<img src="${escapeText(it.image)}" alt="${escapeText(it.name)}" draggable="false">`
        : it.emoji}
        <span class="tag">${escapeText(it.cat)}</span>
        <span class="price">$${it.price.toFixed(2)}</span>
      </div>
      <div class="row2">
        <span class="iname">${escapeText(it.name)}</span>
        <span class="pick" aria-hidden="true">${ICON_PLUS}</span>
      </div>
      ${it.orderable?'':`<div class="outbadge">${it.reason||'Unavailable'}</div>`}
    </div>`).join('');
  gridEl.querySelectorAll('.item').forEach(el=>{
    const item = ITEMS.find(i=>i.id===Number(el.dataset.id));
    if(!item || !item.orderable) return;   // no handler at all when blocked
    el.onclick=()=>{
      if(menuDrag.moved) return;  // ignore the click that follows a drag
      selectItem(item.id, GRID_SOURCE);
    };
  });
  // How many drinks the menu below is showing. Only ever read while a
  // strip is up -- see renderStrips() -- and at that point nothing is
  // filtered, so this is the whole menu.
  document.getElementById('gcount').textContent = list.length + ' món';

  // The strips sit in the same scroller and change its height, so they
  // are settled before the column is measured.
  renderStrips();
  // Filtering changes how tall the menu is, so the dots are rebuilt from the
  // new height rather than left describing the previous result set.
  buildScrollDots();
}
document.getElementById('search').addEventListener('input',renderGrid);

const gridheadEl = document.getElementById('gridhead');

/* ---------------- RENDER: THE STRIPS ----------------
   Two rows of drinks above or below the menu: the ones the shop PICKED
   (featured) and the ones that actually sold (bestseller). Both are the
   same object with different contents, so they are the same code with
   different contents -- one factory, called twice. A second hand-written
   copy is how two rows of the same cards end up subtly different.

   Everything about them is decided in store_gui/sync_menu.py and arrives
   in menu-data.js: which drinks, in what order, whether to draw at all,
   under what heading, and where in the page. Nothing here decides
   anything; it draws. */

/* A photo, however the drink has one. Every arrangement needs the same
   two answers -- the file, or the glyph -- so it is asked once. */
/* THE CARD THAT WAS PRESSED, AND ONLY THAT ONE
   A drink can be drawn three times on one screen -- in Món nổi bật, in
   Bán chạy nhất, and again in the menu below -- and this used to light
   every copy of it at once, because it matched on the drink alone.
   Pressing one card lit two more in blocks further down the page, which
   reads as the screen having selected three things.

   It went wrong in both directions before that. Originally .selected was
   written only in the grid, so tapping a strip card lit that drink's tile
   somewhere off screen and the card actually pressed showed nothing. The
   repair was to tell every block; this narrows it to the right one.

   The answer is that "selected" is a property of the CARD, not of the
   drink: the highlight says "this is the thing you just touched", and
   only one card was touched. So the block is part of the key. */
function selMark(it, source){
  return (selected && selected.id === it.id && selectedIn === source)
    ? ' selected' : '';
}

function photoMarkup(it){
  return it.image
    ? `<img src="${escapeText(it.image)}" alt="${escapeText(it.name)}" draggable="false">`
    : it.emoji;
}

/* CAROUSEL -- a menu card. The same object as a grid tile, which is the
   point: a drink should not look like a different product for being in a
   strip. */
function cardMarkup(it, i, config, spec){
  return `
    <div class="item fitem${selMark(it, spec.section)}" data-fid="${it.id}">
      <div class="thumb">${photoMarkup(it)}
        ${spec.badge(it, i, config)}
        <span class="price">$${it.price.toFixed(2)}</span>
      </div>
      <div class="row2">
        <span class="iname">${escapeText(it.name)}</span>
        <span class="pick" aria-hidden="true">${ICON_PLUS}</span>
      </div>
    </div>`;
}

/* CINEMATIC -- the photo IS the tile.
   No border and no caption shelf: the name and the price sit on the
   photograph behind a scrim, the way a film poster carries its title.
   The card arrangements all spent a third of their height on a white bar
   under the picture; this gives that third back to the drink. */
function tileMarkup(it, i, config, spec){
  return `
    <div class="ctile${selMark(it, spec.section)}" data-fid="${it.id}">
      ${photoMarkup(it)}
      ${spec.badge(it, i, config)}
      <span class="cmeta">
        <span class="cname">${escapeText(it.name)}</span>
        <span class="cprice">$${it.price.toFixed(2)}</span>
      </span>
      <span class="pick" aria-hidden="true">${ICON_PLUS}</span>
    </div>`;
}

/* BUBBLE -- a round photo with the words underneath.
   Claymorphism: the circle is thick-bordered and double-shadowed so it
   reads as an object sitting on the tray rather than a hole cut in it.
   The shortest of the arrangements, because nothing is boxed. */
function bubbleMarkup(it, i, config, spec){
  return `
    <div class="bub${selMark(it, spec.section)}" data-fid="${it.id}">
      <span class="bimg">${photoMarkup(it)}${spec.badge(it, i, config)}</span>
      <span class="bname">${escapeText(it.name)}</span>
      <span class="bprice">$${it.price.toFixed(2)}</span>
    </div>`;
}

/* BOARD -- a wall menu.
   No card, no tile, no photo doing the work: the NAME does, in display
   type, with leaders running to the price. The one arrangement that is
   about the words, so it is also the one that stays readable when a
   drink has no photograph at all. */
function boardMarkup(it, i, config, spec){
  return `
    <div class="bline${selMark(it, spec.section)}" data-fid="${it.id}">
      <span class="bdot">${photoMarkup(it)}</span>
      <span class="btitle">${escapeText(it.name)}</span>
      <span class="bleader" aria-hidden="true"></span>
      <span class="bprice">$${it.price.toFixed(2)}</span>
      <span class="pick" aria-hidden="true">${ICON_PLUS}</span>
    </div>`;
}

/* CHART -- the rank is the ground the drink stands on.
   Exaggerated Minimalism: the numeral is set enormous and pale, and the
   photograph overlaps it. Bestseller only -- see FEATURED_STYLES in
   store_gui/sync_menu.py for why a featured strip must never be given
   this one. */
function chartMarkup(it, i, config, spec){
  const sold = config.sold && config.sold[String(it.drinkId)];
  return `
    <div class="chrow${selMark(it, spec.section)}" data-fid="${it.id}">
      <span class="chnum" aria-hidden="true">${i + 1}</span>
      <span class="chimg">${photoMarkup(it)}</span>
      <span class="chtxt">
        <span class="chname">${escapeText(it.name)}</span>
        ${sold ? `<span class="chsold">${sold} ly đã bán</span>` : ''}
      </span>
      <span class="chprice">$${it.price.toFixed(2)}</span>
      <span class="pick" aria-hidden="true">${ICON_PLUS}</span>
    </div>`;
}

const STYLE_MARKUP = {
  carousel: cardMarkup,
  cinematic: tileMarkup,
  bubble: bubbleMarkup,
  board: boardMarkup,
  chart: chartMarkup,
};

/* One strip. `spec` names its elements and how a card is badged; the
   returned object is what the page calls to repaint or re-place it.

   The elements are looked up once and never rebuilt, only their card
   list is -- the drag and dot handlers below are bound to the container,
   and rebuilding it on every keystroke would throw them away with it. */
function createStrip(spec){
  const section = document.getElementById(spec.section);
  const stripEl = document.getElementById(spec.strip);
  const titleEl = document.getElementById(spec.title);
  const noteEl  = spec.note ? document.getElementById(spec.note) : null;
  const dotsEl  = document.getElementById(spec.dots);

  if(!section || !stripEl || !dotsEl) return null;

  const drag = {down:false, startX:0, startY:0, scrollStart:0, moved:false, axis:null};

  /* The drinks, in the order sync_menu.py listed them.

     Mapped through ITEMS rather than drawn from the ids alone because a
     card needs the price, the photo and the row id a tap resolves to.
     The orderable check is belt and braces: sync_menu.py has already
     dropped anything unsellable, and if that ever changed, a dead card
     here would be the biggest picture on the screen and would do nothing
     when tapped. */
  function items(config){
    return (config.drinkIds || [])
      .map(drinkId => ITEMS.find(item => item.drinkId === drinkId))
      .filter(item => item && item.orderable);
  }

  function render(config){
    const searching = document.getElementById('search').value.trim() !== '';

    /* A STRIP BELONGS TO THE ARRIVAL VIEW
       Once a customer has typed a search or picked a category they have
       said what they want, and a recommendation stops being help: it is
       a second copy of cards that are already in the result underneath,
       pushing the actual answer down the screen. So the strips show on
       the unfiltered menu and nowhere else. */
    const list = (config.enabled && !searching && activeCat === 'all')
      ? items(config) : [];

    // Nothing to show is not an empty strip: the whole section leaves,
    // heading included. A shop with nothing to put in it gets the plain
    // menu back, not a title over a blank row.
    section.classList.toggle('show', list.length > 0);

    if(!list.length){ stripEl.innerHTML = ''; buildDots(); return list; }

    titleEl.textContent = config.title;
    if(noteEl) noteEl.textContent = spec.note ? spec.noteText(config) : '';

    // The arrangement is a class on the container, so the arrangements
    // share one set of handlers and differ only in markup and rules.
    STRIP_STYLES.forEach(name =>
      stripEl.classList.toggle('lay-' + name, config.style === name));

    /* The column count, for the two arrangements that stack. Set as a
       custom property rather than a class per number: the sheet also
       divides the chart's rank numeral by it, and a calc() can read a
       property where it cannot read a class name.

       Forced to 1 for the sideways arrangements. They keep their stored
       value in the database -- so switching to board, choosing two, and
       switching back does not lose the two -- but a scroller laid out in
       columns is not a thing. */
    stripEl.style.setProperty('--cols',
      COLUMN_STYLES.includes(config.style) ? config.columns : 1);

    const draw = STYLE_MARKUP[config.style] || cardMarkup;
    /* Writing innerHTML sends the row back to its first card. Every tap on
       a drink repaints this strip -- selectItem() -> renderGrid() ->
       renderStrips() -- so choosing the fifth card used to scroll the row
       back to the first one under the customer's hand, and the card that
       had just been marked as chosen was off the screen by the time it was
       marked. The cards are the same cards in the same order, so the
       position is still meaningful afterwards: put it back. */
    const keepLeft = stripEl.scrollLeft;
    stripEl.innerHTML = list.map((it, i)=>draw(it, i, config, spec)).join('');
    stripEl.scrollLeft = keepLeft;

    // The same door as a grid tile: selectItem() is where a drink becomes
    // the thing in the panel, and it does its own orderable check.
    stripEl.querySelectorAll('[data-fid]').forEach(el=>{
      el.onclick = ()=>{
        // A drag across the cards ends in a click on whichever one the
        // finger came up over. Without this, scrolling the strip would
        // open the detail panel every time -- the same guard the category
        // rail carries, for the same reason.
        if(drag.moved) return;
        selectItem(Number(el.dataset.fid), spec.section);
      };
    });

    buildDots();
    return list;
  }

  /* ---- page dots ----
     The menu column's control turned on its side, so the screen has one
     answer for "there is more of this than fits" instead of two that look
     different. Needed at all because every scrollbar on this page is
     hidden: without them a strip whose last card is clipped at the tray
     edge reads as a card that got cut off, not a row that keeps going. */
  function pageCount(){
    const w = stripEl.clientWidth;
    if(!w) return 1;
    // A stray pixel or two of rounding is not another page.
    return Math.max(1, Math.ceil((stripEl.scrollWidth - 2) / w));
  }

  function buildDots(){
    const pages = pageCount();
    dotsEl.classList.toggle('show', pages > 1);

    if(pages <= 1){ dotsEl.innerHTML = ''; return; }

    if(dotsEl.children.length !== pages){
      dotsEl.innerHTML = '';
      for(let i = 0; i < pages; i++){
        const b = document.createElement('button');
        b.type = 'button';
        b.className = 'dot';
        b.setAttribute('role', 'tab');
        b.setAttribute('aria-label', 'Trang ' + (i + 1) + ' trên ' + pages);
        b.onclick = ()=>{
          const max = stripEl.scrollWidth - stripEl.clientWidth;
          stripEl.scrollLeft = Math.min(i * stripEl.clientWidth, max);
        };
        dotsEl.appendChild(b);
      }
    }

    syncDots();
  }

  function syncDots(){
    const dots = dotsEl.children;
    if(!dots.length) return;
    const max = stripEl.scrollWidth - stripEl.clientWidth;
    // Rounding, not flooring: the last page is a partial one, so scrolled
    // to the very end you are nearer its start than the previous page's.
    const page = max > 0
      ? Math.round((stripEl.scrollLeft / max) * (dots.length - 1))
      : 0;

    for(let i = 0; i < dots.length; i++){
      dots[i].classList.toggle('on', i === page);
      dots[i].setAttribute('aria-selected', i === page ? 'true' : 'false');
    }
  }

  /* ---- drag to scroll ----
     The dots say where you are and jump a page at a time; this is how the
     row is moved by hand. Lifted from the category rail, because this
     page should have one answer for a row wider than the screen.

     Note the photos are drawn with draggable="false" and pointer-events
     off: an <img> is natively draggable, and pressing on one used to
     start the browser's own drag-and-drop, which fires pointercancel and
     killed this on the first pixel of movement.

     The strip only takes the drag if the hand went sideways -- see
     dragAxis(). A pull downwards on one of these cards belongs to the
     menu column underneath, which is the scroller the customer is
     actually trying to move. */
  stripEl.addEventListener('pointerdown', e=>{
    // Cleared for EVERY press -- see catsEl.
    drag.moved = false;
    // The bow-out the menu column has always had, which these two
    // scrollers were missing. It matters most here: the strips are what
    // fills the screen a customer walks up to, so on a touch machine
    // almost every tap that was thrown away was thrown away here.
    if(e.pointerType === 'touch') return;   // the browser already pans it
    drag.down = true; drag.axis = null;
    drag.startX = e.pageX; drag.startY = e.pageY;
    drag.scrollStart = stripEl.scrollLeft;
  });
  window.addEventListener('pointermove', e=>{
    if(!drag.down) return;
    const dx = e.pageX - drag.startX, dy = e.pageY - drag.startY;
    if(!drag.axis){
      drag.axis = dragAxis(dx, dy);
      if(!drag.axis) return;
      // Either direction counts as a drag, so the click that ends a pull
      // downwards does not open the card it came up over.
      drag.moved = true;
      if(drag.axis === 'x') stripEl.classList.add('dragging');
    }
    if(drag.axis !== 'x') return;
    stripEl.scrollLeft = drag.scrollStart - dx;
  });
  function endDrag(){
    drag.down = false; stripEl.classList.remove('dragging');
  }
  window.addEventListener('pointerup', endDrag);
  window.addEventListener('pointercancel', endDrag);

  // Scroll fires far faster than the screen repaints; one update a frame.
  let frame = 0;
  stripEl.addEventListener('scroll', ()=>{
    if(frame) return;
    frame = requestAnimationFrame(()=>{ frame = 0; syncDots(); });
  });
  window.addEventListener('resize', buildDots);
  // Card images arrive after this script runs, so the count is taken
  // again once they have landed and the row has its real width.
  window.addEventListener('load', buildDots);

  return {section, render, buildDots};
}

const ICON_RANK = ICON('<path d="M7 3h10v4a5 5 0 0 1-10 0Z"/>' +
  '<path d="M7 5H4.5v1A3.5 3.5 0 0 0 8 9.5"/>' +
  '<path d="M17 5h2.5v1A3.5 3.5 0 0 1 16 9.5"/>' +
  '<path d="M12 12v4M9 20h6M10 16h4l.6 4H9.4Z"/>');

const STRIPS = {
  featured: createStrip({
    section:'featured', strip:'fstrip', title:'ftitle', dots:'fdots',
    // The badge replaces the category chip rather than joining it: the
    // category is on the same drink's card in the grid below, and two
    // chips in one corner is the corner lost.
    ranked: false,
    badge: ()=>`<span class="fribbon">${ICON_STAR}<span>Nổi bật</span></span>`,
  }),
  bestseller: createStrip({
    section:'bestseller', strip:'bstrip', title:'btitle', dots:'bdots',
    note:'bnote',
    // The window, said on the screen. "Bán chạy" with no period attached
    // is a claim a customer cannot check and the shop cannot defend --
    // over what, since opening? This is the one fact that makes it true.
    noteText: config => `${config.windowDays} ngày qua`,
    ranked: true,
    // The rank, because that is the whole content of this row. Numbered
    // rather than starred: the strip is ordered, and a badge that did not
    // say which one is first would be throwing that away.
    badge: (item, i)=>`<span class="fribbon rank">#${i + 1}</span>`,
  }),
};

/* Paint both strips, then say whether the menu needs a heading of its
   own. It does exactly when something else is on the page with it: alone,
   the menu IS the page and a label over it would name nothing. */
function renderStrips(){
  const drawn =
    (STRIPS.featured   ? STRIPS.featured.render(FEATURED).length   : 0) +
    (STRIPS.bestseller ? STRIPS.bestseller.render(BESTSELLER).length : 0);

  gridheadEl.classList.toggle('show', drawn > 0);
}

/* Order the blocks down the page, as store_setting says.

   Sections are MOVED, never drawn twice: two copies would both be live,
   both wired, and only one of them can own the id its heading is
   labelled by. The grid's heading travels with the grid, since a label
   parted from the thing it names is worse than no label. */
function placeBlocks(){
  const parent = gridEl.parentNode;
  const nodes = {
    featured:   STRIPS.featured   && STRIPS.featured.section,
    bestseller: STRIPS.bestseller && STRIPS.bestseller.section,
    grid:       gridheadEl,       // the heading, then the grid behind it
  };

  // appendChild on a node already in the parent MOVES it, so walking the
  // wanted order and re-appending each block in turn lands them all in
  // that order however they started.
  LAYOUT.forEach(name=>{
    const node = nodes[name];
    if(!node) return;
    parent.appendChild(node);
    if(name === 'grid') parent.appendChild(gridEl);
  });
}


/* ---------------- SELECT ITEM / ORDER ---------------- */
function selectItem(id, source){
  const item = ITEMS.find(i=>i.id===id);
  // renderGrid() already withholds the click handler, but the block belongs
  // here too: this is the one door into the detail panel, and a drink the
  // machine cannot pour must not become sellable through any other caller.
  if(!item || !item.orderable) return;
  selected = item;
  // Recorded here rather than in the click handlers so the two doors into
  // this function cannot disagree about what a selection is.
  selectedIn = source;
  sel = defaultSelection(item);
  panelMode = 'item';           // a tile always means "configure this drink"
  renderGrid();
  renderDetail();
  openSidebar();
}

const detailEl = document.getElementById('detail');
const addbar = document.getElementById('addbar');
const rtitleEl = document.getElementById('rtitle');
/* The drawer shows one of two things: the drink being configured, or the
   order as it stands. Tapping a tile puts it in 'item'; the floating button
   puts it in 'bill', which is the only way back to an order once the drawer
   has been dismissed. */
let panelMode = 'item';

function renderDetail(){
  if(panelMode === 'bill'){ renderBillPanel(); return; }
  rtitleEl.textContent = 'Item Details';
  detailEl.classList.remove('bill-view');
  if(!selected){
    addbar.style.display='none';
    detailEl.innerHTML = `<div class="empty"><div class="big">${ICON_BIG_CUP}</div>
      <p>No item selected yet. Tap any item on the left to customise it and add it to the bill.</p></div>`;
    document.getElementById('rsub').textContent='Select an item from the menu to view its options';
    return;
  }
  document.getElementById('rsub').textContent = selected.cat + ' · tap options below to customize';
  // Only what this drink's own recipe contains: the payload can drop or
  // scale an ingredient, never add one the recipe lacks.
  const tops = toppingOptions(selected);
  const dial = percentOption(selected);
  detailEl.innerHTML = `
    <div class="hero">
      <div class="pic">${selected.image
        ? `<img src="${escapeText(selected.image)}" alt="">`
        : selected.emoji}</div>
      <div class="htxt">
        <div class="hn">${escapeText(selected.name)}</div>
        <div class="hcat">${escapeText(selected.cat)}</div>
        <div class="hp">$${selected.price.toFixed(2)}</div>
      </div>
    </div>

    ${dial ? `
    <div class="section">
      <div class="lbl">${escapeText(dial.name)} Level</div>
      <div class="sizes">
        ${(dial.choices||[100]).map(v=>`<div class="size ${sel.sugar===pct(v)?'active':''}"
          data-sugar="${pct(v)}">${pct(v)}%</div>`).join('')}
      </div>
    </div>` : ''}

    ${tops.length ? `
    <div class="section">
      <div class="lbl">Add-ons <span class="opt">optional · choose any</span></div>
      ${tops.map(t=>`<div class="topping ${sel.toppings.has(t.ingredientId)?'on':''} ${t.inStock?'':'off'}"
        ${t.inStock?`data-top="${t.ingredientId}"`:''}>
        <div class="lft"><span class="box">${sel.toppings.has(t.ingredientId)?'&#10003;':''}</span>${escapeText(t.name)}${
          t.inStock?'':' <span class="opt">out of stock</span>'}</div></div>`).join('')}
    </div>` : `
    <div class="section">
      <div class="lbl">Add-ons</div>
      <p class="note">This drink has no options — its recipe contains nothing
      the customer can change.</p>
    </div>`}

    <div class="section notes">
      <div class="lbl">Special Notes <span class="opt">optional</span></div>
      <textarea rows="2" id="notes" placeholder="e.g. less sugar, extra ice...">${escapeText(sel.notes)}</textarea>
    </div>
  `;
  addbar.style.display='block';

  // Every option handler goes through editedSelection(), so there is one
  // place that knows the bill on screen no longer matches the panel.
  // wire sugar level
  detailEl.querySelectorAll('[data-sugar]').forEach(el=>el.onclick=()=>{
    sel.sugar=el.dataset.sugar; editedSelection();
  });
  // wire toppings
  detailEl.querySelectorAll('.topping[data-top]').forEach(el=>el.onclick=()=>{
    const t=Number(el.dataset.top);
    sel.toppings.has(t)?sel.toppings.delete(t):sel.toppings.add(t); editedSelection();
  });
  // notes
  const nt=document.getElementById('notes');
  if(nt) nt.oninput=e=>{ sel.notes=e.target.value; collapseStaleBill(); };

  updateAddPrice();
}


/* ---------------- THE DRAWER IN BILL MODE ----------------
   The whole order, spelled out. The strip at the bottom of the drawer shows
   the same drink on one squeezed line; this is the version with room for
   what was actually chosen -- the sugar level, the add-ons, the note -- which
   is the part a customer wants to check before paying for it. */
function renderBillPanel(){
  addbar.style.display = 'none';
  detailEl.classList.add('bill-view');
  rtitleEl.textContent = 'Your Order';
  const sub = document.getElementById('rsub');

  if(!order){
    sub.textContent = 'Nothing on the bill yet';
    detailEl.innerHTML = `<div class="empty"><div class="big">${ICON_BIG_BILL}</div>
      <p>The bill is empty. Tap a drink on the left to start an order.</p></div>`;
    return;
  }

  sub.textContent = 'Check it over, then get the QR code';
  // order carries its own options, so the dial keeps the name the recipe
  // gave it ("Sugar", "Syrup") instead of a generic label.
  const dial = percentOption(order);
  const tops = toppingOptions(order);
  const notes = (order.notes || '').trim();
  const rows = [];
  if(dial) rows.push([dial.name + ' level', order.sugar + '%']);

  detailEl.innerHTML = `
    <div class="hero">
      <div class="pic">${order.image
        ? `<img src="${escapeText(order.image)}" alt="">`
        : order.emoji}</div>
      <div class="htxt">
        <div class="hn">${escapeText(order.name)}</div>
        <div class="hp">$${order.unit.toFixed(2)}</div>
      </div>
    </div>

    ${rows.length ? `
    <div class="section">
      <div class="lbl">How it is made</div>
      <dl class="speclist">
        ${rows.map(([k, v])=>`<dt>${k}</dt><dd>${escapeText(v)}</dd>`).join('')}
      </dl>
    </div>` : ''}

    ${tops.length ? `
    <div class="section">
      <div class="lbl">Add-ons</div>
      ${tops.map(t=>{
        // Every add-on the recipe offers, ticked or not -- the same rows as
        // the panel it was chosen on. A comma-joined string listed only what
        // survived, so "did I take the pearls out?" had no answer here.
        const on = order.toppingIds.includes(t.ingredientId);
        return `<div class="topping read ${on?'on':'gone'}">
          <div class="lft"><span class="box">${on?'&#10003;':''}</span>${escapeText(t.name)}</div>
          ${on?'':'<span class="opt">removed</span>'}
        </div>`;
      }).join('')}
    </div>` : ''}

    ${notes ? `
    <div class="section">
      <div class="lbl">Special notes</div>
      <p class="notequote">${escapeText(notes)}</p>
    </div>` : ''}

    ${(!rows.length && !tops.length) ? `
    <div class="section">
      <div class="lbl">How it is made</div>
      <p class="note">Made to the standard recipe — this drink has no
      options to change.</p>
    </div>` : ''}

    <!-- Pushed to the foot of the drawer. What you owe and the button that
         acts on it belong together, at the edge the thumb already rests on,
         not stranded half-way up with empty panel beneath them. -->
    <div class="billfoot">
      <div class="ordertotal">
        <span>Total</span><span>$${order.unit.toFixed(2)}</span>
      </div>
      <p class="note">Giá đã bao gồm thuế · Tax included</p>
      <!-- "Place Order", not "Order QR Code": a QR is only ONE of the ways
           this order can be fulfilled, and the shop may have that way
           switched off entirely (see applyOrderMode). It is not "Complete
           Order" either -- pressing this completes nothing, it opens the
           "Start this drink" panel where Print or Start is still to be
           chosen, and that panel ends on its own "Done".

           The id and class still say qr. They are historical: renaming
           them means renaming CSS selectors for no gain the customer can
           see, and this comment is cheaper than that churn. -->
      <button class="qrbtn" id="panelqr">${ICON_CHECK} Place Order</button>
      <button class="linkbtn" id="panelclear">Remove this drink</button>
    </div>
  `;

  document.getElementById('panelqr').onclick = ()=>showQR(order.unit);
  document.getElementById('panelclear').onclick = clearOrder;
}

/* Notes and topping names reach the panel as text, so they are escaped
   rather than dropped into the template as markup. */
function escapeText(v){
  return String(v).replace(/[&<>"]/g, c=>(
    {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]
  ));
}

function unitPrice(){
  if(!selected) return 0;
  // The menu price, full stop. Toppings are free and there is no size,
  // so nothing on the panel moves this number.
  return selected.price;
}
/* True when the bill already holds the drink the panel is showing, so
   pressing the button edits that line rather than swapping in a new drink. */
const editingBilledDrink = () =>
  Boolean(order && selected && order.drinkId === selected.drinkId);

function updateAddPrice(){
  document.getElementById('addprice').textContent = '$'+unitPrice().toFixed(2);
  const label = document.getElementById('addlabel');
  if(label){
    label.innerHTML = editingBilledDrink()
      ? ICON_REDO + ' Update Bill'
      : ICON_PLUS + ' Add to Bill';
  }
}

/* The totals on screen were worked out from an earlier configuration, so the
   moment anything changes they are stale. Closing the bill is the cue to
   press the button again instead of reading a number that no longer holds. */
function collapseStaleBill(){
  if(!order) return;
  // Was: collapse the strip, so its stale total could not be read. With the
  // strip gone the only stale figure would be the floating button's, so that
  // is what gets refreshed instead.
  updateBillFab();
}

/* One option changed: redraw the panel and retire the bill's totals. */
function editedSelection(){
  collapseStaleBill();
  renderDetail();
}

/* ---------------- ADD TO BILL ---------------- */
document.getElementById('addbtn').onclick=()=>{
  if(!selected) return;
  // Re-pressing on the drink already in the bill is an edit of that line, so
  // it just overwrites it. Only a DIFFERENT drink is a replacement worth
  // asking about, because the one being discarded may have taken several
  // taps to customise.
  const updating = editingBilledDrink();

  if(order && !updating){
    // askReplace() resolves on a button, so what follows has to wait for it
    // rather than run on. confirm() blocked the thread and let this read as
    // one straight line; the modal cannot, hence the callback.
    askReplace(order, selected, commitToBill);
    return;
  }
  commitToBill();
};

/* Everything after the question: writing the drink onto the bill. Split out
   so the answer to the modal has something to call, and so the no-question
   path stays a single call rather than a copy of this. */
function commitToBill(){
  if(!selected) return;
  const topIds = [...sel.toppings];                    // ingredient ids
  const available = toppingOptions(selected);
  const tops = topIds
    .map(id=>(available.find(t=>t.ingredientId===id)||{}).name)
    .filter(Boolean);
  order = {
    name:selected.name, emoji:selected.emoji, image:selected.image,
    drinkId:selected.drinkId,
    sugar:sel.sugar, // raw '0'|'25'|'50'|'75'|'100', for the machine QR code
    toppingIds:topIds, toppings:tops,
    options:selected.options, unit:unitPrice(), notes:sel.notes
  };
  // The panel switches to the order rather than flashing "Added!" on a
  // button: the strip that used to expand underneath is gone, so without
  // this the drink would land somewhere the customer cannot see.
  panelMode = 'bill';
  renderBill();
  renderDetail();
}

/* ---------------- "REPLACE THE DRINK IN THE BILL?" ----------------
   Shows the drink being discarded next to the one taking its place. The
   browser's confirm() could not: it renders at the top of the window in the
   system font, and its OK / Cancel never say which of the two names in the
   sentence each one keeps. */
function askReplace(outgoing, incoming, onYes){
  const face = (el, drink)=>{
    if(drink.image){
      el.innerHTML = '<img alt="">';
      el.firstChild.src = drink.image;
    } else {
      el.textContent = drink.emoji || '\uD83E\uDDCB';
    }
  };
  face(document.getElementById('replaceOutEmoji'), outgoing);
  face(document.getElementById('replaceInEmoji'), incoming);
  // textContent, not innerHTML: drink names come from the database and a
  // stray < in one would otherwise be parsed as markup.
  document.getElementById('replaceOutName').textContent = outgoing.name;
  document.getElementById('replaceInName').textContent  = incoming.name;

  const ov = document.getElementById('replaceoverlay');
  const onEsc = e=>{ if(e.key === 'Escape'){ e.stopPropagation(); close(); } };
  const close = ()=>{
    ov.classList.remove('show');
    document.getElementById('replaceyes').onclick = null;
    document.getElementById('replaceno').onclick  = null;
    // Removed rather than left attached: the box is in the DOM from page
    // load, so a listener per opening would stack up one Esc handler per
    // question the customer was ever asked.
    document.removeEventListener('keydown', onEsc, true);
  };
  document.getElementById('replaceyes').onclick = ()=>{ close(); onYes(); };
  document.getElementById('replaceno').onclick  = close;
  // Clicking the backdrop keeps what is already on the bill -- the safe
  // reading of a dismissal, and the same answer Cancel gave.
  ov.onclick = e=>{ if(e.target === ov) close(); };
  // Capture phase, so Esc closes this box instead of the detail drawer
  // underneath it.
  document.addEventListener('keydown', onEsc, true);
  ov.classList.add('show');
  document.getElementById('replaceyes').focus();
}

/* ---------------- BILL ----------------
   The menu price is what the customer pays. There used to be a 10% tax
   line and a flat $1.00 discount underneath it, both invented by this
   screen: nothing set the discount, nobody could clear it, and the tax
   was added on top of a price that already includes it -- so the total
   on the bill was never the price on the tile, and the QR modal showed
   a third number again. One price, one total, and they agree. */
function renderBill(){
  // Nothing to draw: the order is shown by the panel in bill mode and
  // summarised by the floating button. This keeps the two in step and is
  // still the one call every path uses after the order changes.
  updateBillFab();
  if(panelMode === 'bill') renderDetail();
}

/* Dropping the drink. forgetTicket(): without it, the next customer ordering
   the identical drink would match the held signature and be handed the
   PREVIOUS customer's serial -- a code already spent, or about to be. A
   ticket belongs to one bill, and the bill ends here. */
function clearOrder(){
  order = null;
  forgetTicket();
  renderBill();
  scrollMenuToTop();      // next customer starts at the top of the menu
  reloadIfMenuStale();
}

/* ---------------- QR CODE: ONE SINGLE-USE TICKET PER ORDER ----------------
   This file no longer builds the payload. It sends what the customer picked
   to store_gui/serve.py, which allocates a serial from the order_ticket
   table, encodes the payload with scan/qr_payload.py, and sends the digits
   back.

   WHY IT MOVED OUT OF THE BROWSER
   A single-use code needs a serial only the database can hand out, so the
   payload could not be finished here in any case. Moving the whole encoder
   removes the second implementation of the wire format — the same class of
   split that once had the screen showing a version 5 symbol while the
   printer produced a version 3 for the same order.

   WHAT THIS FILE STILL DECIDES
   Which pairs the order consists of. That is a question about this screen's
   controls, not about the protocol:

     • the dial carries the FINAL WEIGHT, not the percentage. Sugar is 50 g
       in the recipe and the customer picked 25%, so the pair says 13 g and
       the machine never multiplies anything. It is always sent, even at
       100%, because the point of the pair is to state the amount outright.
     • 0% is sent as a boolean "no". A weight of zero cannot say "leave it
       out" — order/qr_to_recipe.py would read it as an amount.
     • every topping the drink offers is sent, including the unticked ones.
       Silence means "leave the recipe alone", so an omitted Milk pair would
       let Milk through on a drink whose recipe has it — the opposite of
       what an unticked box means here.

   A pair can drop or resize an ingredient the recipe already contains. It
   cannot ADD one: qr_to_recipe.py reports such a pair and ignores it. */
/* ORDER_TABLE is gone: this machine has no tables, and "Table 05" on
   the QR modal said nothing true about the order. */
/* Four digits, like every other id on screen and like the SKU the machine
   prints (`f"{sku:04d}"`). Still a placeholder: this screen has no real
   order number to show until the label is printed, and the serial that
   comes back then is the ticket's, not this. */
const ORDER_ID='0005';
const TICKET_URL = '../api/ticket';

/* qrproto (protocol v1.4) has no percentage type, so TYPE_WEIGHT was
   given "01" in its place rather than leaving it unused -- these two
   values must match qrproto/constants.py exactly, not protocol v1.3's
   numbering (where weight was a local extension at "03"). */
const QR_TYPE_WEIGHT = '01';
const QR_TYPE_BOOLEAN = '02';
const QR_BOOLEAN_YES = 1, QR_BOOLEAN_NO = 0;
const QR_WEIGHT_MAX = 9999;   // the 4-digit data field, in whole grams

/* The order as opcode/data pairs, in the units the protocol's data field
   uses. The server turns these into the payload. */
function orderPairs(b){
  const pairs = [];
  const options = b.options || [];
  const dial = options.find(o=>o.kind==='percentage');

  if(dial){
    const grams = Math.round(Number(dial.gram || 0) * Number(b.sugar) / 100);
    if(grams > 0 && grams <= QR_WEIGHT_MAX){
      pairs.push({ingredient:dial.ingredientId, type:QR_TYPE_WEIGHT,
                  data:grams});
    } else if(grams <= 0){
      pairs.push({ingredient:dial.ingredientId, type:QR_TYPE_BOOLEAN,
                  data:QR_BOOLEAN_NO});
    }
  }
  for(const t of options.filter(o=>o.kind==='boolean')){
    pairs.push({ingredient:t.ingredientId, type:QR_TYPE_BOOLEAN,
                data:b.toppingIds.includes(t.ingredientId) ? QR_BOOLEAN_YES : QR_BOOLEAN_NO});
  }
  return pairs;
}

/* ONE PAYLOAD
     ticket   the real, single-use code. Only ever created by pressing
              Print, and it is the one that goes on the label.

   Opening the QR modal used to allocate a serial straight away, so simply
   looking at an order and closing it left an unused ticket in the database
   for a drink nobody bought. A serial is now spent only when a label is
   actually produced.

   There used to be a second payload beside it, `preview`: a throwaway
   encoding carrying serial 000000, fetched on every modal open purely to
   draw a symbol. The modal shows the drink now, so nothing needs encoding
   until Print is pressed. The server still accepts preview:true; this
   screen has no reason to ask for one.

   `signature` records which order the ticket belongs to, so it cannot
   outlive the choices it encodes. Keeping it also means a retry after a
   printer jam reprints the SAME code rather than minting a second one —
   two labels for one order is exactly what the serial prevents. */
let ticket = null;

function orderSignature(b){
  // The note is part of the order's identity. Without it here, editing
  // the note and pressing Print again would reprint the SAME serial --
  // whose row still carries the old text, so the machine would show the
  // bartender a request the customer had already changed.
  return JSON.stringify([b.drinkId, b.sugar, [...b.toppingIds].sort(),
                         b.notes || '']);
}

/* Dropped when the order changes or the bill is cleared. An issued ticket
   stays in the database as 'unused' and expires on its own — it may
   already be on paper, so it is not ours to cancel. */
function forgetTicket(){ ticket = null; }

async function requestPayload(b, wantPreview){
  const response = await fetch(TICKET_URL, {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({
      drink_id: b.drinkId, pairs: orderPairs(b), preview: wantPreview,
      // Cannot go in the QR -- that payload is digits only -- so it is
      // stored against the serial and fetched by the machine when the
      // code is scanned.
      note: b.notes || '',
    }),
  });
  // A failure does not always arrive as JSON. A 404 from an older server
  // that has no /api/ticket comes back as an HTML error page, and reporting
  // that as "could not create the QR code" hides the one fact that explains
  // it — so when there is no message to quote, quote the status instead.
  const result = await response.json().catch(()=>({}));

  if(!response.ok || !result.ok || !result.payload){
    throw new Error(result.error ||
      (response.ok ? 'The server sent back no QR code.'
                   : 'Server error ' + response.status + ' from /api/ticket.' +
                     (response.status === 404
                       ? ' Restart store_gui/serve.py — it is running an older version.'
                       : '')));
  }

  return {serial:result.serial, payload:result.payload,
          signature:orderSignature(b)};
}

/** Encode the order for display. Writes nothing to the database. */
/** Allocate the real single-use code. This is the committing step. */
async function issueTicket(b){
  const signature = orderSignature(b);
  if(ticket && ticket.signature === signature) return ticket;
  ticket = await requestPayload(b, false);
  return ticket;
}

/* The last look at the drink before it is committed: what it is, how it was
   configured, what it costs. Nothing here talks to the server -- the code is
   allocated by the Print button underneath, so this modal opens instantly
   and closing it still costs nothing and leaves nothing behind. */
/* ---------------- HOW THIS SHOP TAKES AN ORDER ----------------
   Two ways to turn a placed order into a drink, and the shop decides in
   the admin console which of them the counter is offered:

     printQR    "Print QR"                        -> the label path
     runDirect  "Start on the machine (no scan)"  -> straight to the machine

   Both on is how the machine has always behaved: print normally, run
   direct when the printer or the scanner lets you down. One off hides
   that button. Both off is refused by the server, so this can never end
   up drawing a modal with nothing to press -- see
   configuration/order_mode.py.

   THE DEFAULT IS BOTH ON, AND IT SURVIVES THE FETCH FAILING
       A shop that cannot reach its own server must not lose the ability
       to sell. So this starts as the old behaviour and only ever narrows
       on a good answer.

   A CHANGE LANDS ON THE NEXT ORDER, NOT THIS ONE
       showQR() draws from the cached value, synchronously, so the modal
       still opens the instant it is asked for -- and it refreshes in the
       background for next time. Re-applying mid-modal would take a button
       out from under the finger already reaching for it. Drift is bounded
       anyway: closeQR() reloads the whole page once a label exists. */
const ORDER_MODE_URL = '../api/order-mode';

let orderMode = { printQR: true, runDirect: true };

function applyOrderMode(){
  document.getElementById('qrprint').hidden = !orderMode.printQR;
  document.getElementById('qrstart').hidden = !orderMode.runDirect;
}

async function loadOrderMode(){
  try{
    const response = await fetch(ORDER_MODE_URL, {cache:'no-store'});
    const result = await response.json();
    // Narrow only on an answer that is actually one. A 404 from a server
    // running an older version parses as JSON with no switches in it, and
    // {undefined, undefined} would hide both buttons.
    if(response.ok && result.ok
       && typeof result.printQR === 'boolean'
       && typeof result.runDirect === 'boolean'){
      orderMode = {printQR: result.printQR, runDirect: result.runDirect};
    }
  }catch(error){
    // Kept quiet and kept as it was. The counter is mid-service and the
    // fallback is the behaviour they already know.
    console.warn('[order-mode] không đọc được, giữ nguyên:', error);
  }
}

function showQR(total){
  if(!order){alert('Add a drink to the bill first.');return;}

  applyOrderMode();
  loadOrderMode();          // for the next order, not this one

  document.getElementById('qrorderid').textContent='Order #'+ORDER_ID;
  document.getElementById('qrtotal').textContent='$'+total.toFixed(2);
  printNote('');

  const pic = document.getElementById('qrpic');
  if(order.image){
    pic.innerHTML = '<img alt="">';
    pic.firstChild.src = order.image;
  } else {
    pic.textContent = order.emoji || '\uD83E\uDDCB';
  }
  document.getElementById('qrname').textContent = order.name;

  // The short form: the dial, then whatever was ticked. The panel behind
  // this modal carries the full list including what was removed -- here it
  // only has to be recognisable as the right drink.
  const dial = percentOption(order);
  const chips = [];
  if(dial) chips.push(dial.name + ' ' + order.sugar + '%');
  order.toppings.forEach(t=>chips.push(t));
  const spec = document.getElementById('qrspec');
  spec.innerHTML = '';
  chips.forEach(text=>{
    const el = document.createElement('span');
    el.className = 'qrchip';
    el.textContent = text;                       // names come from the database
    spec.appendChild(el);
  });

  document.getElementById('overlay').classList.add('show');
}
/* ---------------- PRINTING THE LABEL ----------------
   The browser cannot reach the label printer on the Pi, so the payload is
   posted to store_gui/serve.py, which runs printer/printer_qr.py. The
   digits go over the wire rather than a picture: the printer renders its
   own QR, so what is printed cannot drift from what the machine reads.

   It prints the ticket already on screen. A second copy is the SAME code,
   not a new one: order_ticket.claim() takes a payload atomically by its
   hash, so however many pieces of paper come out, exactly one of them can
   buy a drink. That is what makes "Print another copy" below safe to offer, and
   it is also the line it must not cross -- issuing a new payload would be
   a second live code and a second sale for a drink paid for once. */
const PRINT_URL = '../api/print';

/* How long the modal takes to fade out. Must match the .overlay transition
   in drinks-pos.css — the page waits this long after closing so the reload
   below happens on an empty screen rather than cutting the animation in
   half. A little longer than the CSS on purpose: finishing early is
   invisible, finishing late is a jump. */
const MODAL_CLOSE_MS = 320;

let printing = false;

/* A label has come out for this order, so whichever way the modal is
   closed the screen must reset for the next customer.

   IT DOES NOT CLOSE ITSELF ONCE A LABEL EXISTS
       A countdown is the wrong shape here. The person at the counter is
       looking at the printer, not the screen: they have to see the paper
       come out, read it, hand it over, and only then is the order really
       finished -- and any of those can take longer than a timer is
       willing to wait. A modal that closed on its own mid-check took the
       reprint button away at exactly the moment a jam was noticed.

       So printing hands the modal over to the operator and it stays until
       they say so. Start still closes itself: nothing is on paper, there
       is nothing to check, and the screen is about to be taken to the
       bartender page anyway. */
let printedHere = false;
let copies = 0;

/* The modal is done: both buttons stay down until the handoff takes the
   screen to the bartender page. Only a FAILURE hands a button back,
   because only a failure leaves something to try again.

   Used by Start, which really is the end of this screen's involvement.
   Print keeps its own button -- see its success branch, where the button
   becomes a different action rather than dying. */
function lockQRButtons(){
  document.getElementById('qrprint').disabled = true;
  document.getElementById('qrstart').disabled = true;
}

function printNote(text, kind){
  const note = document.getElementById('qrprintNote');
  note.textContent = text || '';
  note.className = 'printnote' + (kind ? ' ' + kind : '');
  note.hidden = !text;
}

document.getElementById('qrprint').onclick = async () => {
  // `starting` too: the start button resets its own guard before its
  // success branch, so without this Print was pressable during the pause
  // on a drink that had already gone to the machine.
  if(printing || starting || !order) return;

  const button = document.getElementById('qrprint');
  const label = document.getElementById('qrprintLabel');
  const idle = label.innerHTML;

  printing = true;
  button.disabled = true;
  label.innerHTML = ICON_PRINT + ' Printing...';
  printNote('');

  let result = {};
  try{
    // THIS is where the order enters the database. Deliberately here and
    // not when the modal opened: a serial should be spent on a label that
    // exists, not on a customer having a look and changing their mind.
    //
    // Issued before the print rather than after, because the printer needs
    // the digits — and if issuing fails there is nothing to print anyway.
    // A retry after a jam reuses the same ticket, so one order can never
    // put two live codes on paper.
    const issued = await issueTicket(order);

    const response = await fetch(PRINT_URL, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({payload: issued.payload}),
    });
    result = await response.json().catch(()=>({}));
    if(!response.ok) result.ok = false;
  }catch(error){
    result = {ok:false, error:String(error.message || error)};
  }

  if(result.ok){
    copies += 1;
    printedHere = true;

    // The drink is spoken for -- sending it to the machine from here as
    // well would put it through on a label the customer is holding. So
    // this button becomes the way OUT instead of sitting there greyed:
    // the modal now waits to be dismissed, and hunting for the small x in
    // the corner is a poor thing to ask of somebody holding a cup and a
    // receipt. Its click handler reads printedHere and closes.
    //
    // Unhidden as well, for the shop that has turned "Start on the
    // machine" off: in that mode this element is not offered as a way to
    // START an order, but it is still the way to FINISH one, and a
    // print-only counter needs a Done button just as much. The role it is
    // playing is decided by printedHere, which its click handler already
    // reads -- so revealing it here cannot start anything.
    document.getElementById('qrstart').hidden = false;
    document.getElementById('qrstart').disabled = false;
    document.getElementById('qrstartLabel').innerHTML = ICON_CHECK + ' Done';
    // Swaps which of the two reads as the main action -- see the
    // [data-printed] rules in drinks-pos.css.
    document.querySelector('#overlay .modal').dataset.printed = '1';

    // The button comes back, but as a DIFFERENT action. The first copy is
    // done; what is left is the deliberate "another one" for a printer
    // that jammed or ran out. That is the distinction the old code was
    // missing -- it handed back the SAME button mid-close, so a second
    // press was a fumble rather than a decision.
    printing = false;
    button.disabled = false;
    label.innerHTML = ICON_PRINT + ' Print another copy';
    printNote(copies > 1
      ? `Đã in ${copies} bản — bấm Done khi đã đưa nhãn cho khách.`
      : 'Đã gửi máy in — bấm Done khi đã đưa nhãn cho khách.', 'ok');
  }else{
    // Left open on failure. Closing would take the one thing that explains
    // what went wrong off the screen, along with the button to try again.
    printing = false;
    button.disabled = false;
    label.innerHTML = idle;
    printNote(result.error || 'Printing failed.', 'bad');
  }
};

/* ---------------- STARTING WITHOUT A SCAN ----------------
   The normal path is paper: print the label, the customer scans it, the
   machine starts. That path has two single points of failure the shop
   cannot fix at the counter -- a dead scanner, or a printer out of paper --
   and either one strands an order that is otherwise complete.

   This button is the way past both. It issues the SAME real ticket the
   Print button would, then posts the payload to the server, which drops it
   into scan/raw_qr.json in exactly the shape scan/scanner.py writes. From
   there nothing downstream can tell the difference: run_flow.py claims the
   ticket, writes the handoff and the bartender screen opens, so the order
   is recorded, serialised and single-use just like a scanned one.

   It does NOT bypass the ticket, only the beam. Skipping the ticket would
   mean an order in the machine with no serial behind it -- unrepeatable,
   untraceable, and invisible to error_log. */
const START_URL = '../api/start';

let starting = false;

document.getElementById('qrstart').onclick = async () => {
  // Once a label exists this button is relabelled "Done" and is the way
  // out of the modal -- see the print success branch. Checked FIRST and
  // by state, not by the disabled attribute: the drink is already on
  // paper, and starting it here as well would put it through twice.
  if(printedHere){ closeQR(); return; }

  if(starting || printing || !order) return;

  const button = document.getElementById('qrstart');
  const label = document.getElementById('qrstartLabel');
  const idle = label.innerHTML;

  starting = true;
  button.disabled = true;
  label.innerHTML = ICON_PLAY + ' Starting...';
  printNote('');

  let result = {};
  try{
    // Same call the Print button makes, and the same cached ticket: an
    // order printed and then started here goes to the machine on the one
    // serial it already put on paper, not a second live code.
    const issued = await issueTicket(order);

    const response = await fetch(START_URL, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({payload: issued.payload}),
    });
    result = await response.json().catch(()=>({}));

    if(!response.ok){
      result.ok = false;
      // A failure does not always arrive as JSON, and the one that does not
      // is the likeliest failure here: a server started before this endpoint
      // existed answers 404 with an HTML error page, leaving nothing to
      // quote. Reporting that as "could not start the machine" hides the one
      // fact that explains it -- so with no message, quote the status.
      result.error = result.error ||
        'Server error ' + response.status + ' from /api/start.' +
        (response.status === 404
          ? ' Restart store_gui/serve.py — it is running an older version.'
          : '');
    }
  }catch(error){
    result = {ok:false, error:String(error.message || error)};
  }

  if(result.ok){
    // Held, like Print: the drink is with the machine now, and this screen
    // is about to be taken to the bartender page by the handoff poll.
    lockQRButtons();
    label.innerHTML = ICON_CHECK + ' Sent to the machine';
    printNote('Máy đang nhận đơn...');
    // No reload and no navigation from here. run_flow.py has the payload
    // now; when it has the order ready it writes handoff.json and the
    // poll below takes this screen to the bartender page -- the same way
    // it does after a scan. Driving there from this click instead would
    // arrive before the machine was ready.
    startedHere = true;
    setTimeout(closeQR, 900);
  }else{
    // Left open, button re-enabled: a 409 here usually means run_flow is
    // simply not running, which someone can fix and press again.
    starting = false;
    button.disabled = false;
    label.innerHTML = idle;
    printNote(result.error || 'Could not start the machine.', 'bad');
  }
};

/* Take the modal off the screen, and decide nothing else.

   Split out of closeQR() because the handoff path needs exactly this and
   must NOT have the reload below: it is already navigating to the
   bartender screen, and a reload racing that would either cancel the jump
   or fire on a page that has left. */
function dismissQR(){
  printNote('');
  document.getElementById('overlay').classList.remove('show');
}

function closeQR(){
  dismissQR();

  // A label is out of the printer, so this order is finished with however
  // the modal was closed -- the countdown, the X, or a click on the
  // backdrop. The reload is what clears the bill, the selection and the
  // held ticket for the next customer, and it also picks up a menu
  // rebuilt since this page loaded. It does NOT affect the label already
  // printed: that QR's ticket lives in the database, so the code in the
  // customer's hand still works.
  //
  // Start does not reload: run_flow.py has the payload and the handoff
  // poll is about to take this screen to the bartender page.
  if(printedHere) setTimeout(()=>location.reload(), MODAL_CLOSE_MS);
}

document.getElementById('qrclose').onclick=closeQR;
document.getElementById('overlay').onclick=e=>{if(e.target.id==='overlay')closeQR();};

/* ---------------- PICKING UP A REBUILT MENU ----------------
   store_gui/sync_menu.py --interval 5 rewrites menu-data.js from the
   database. This page loaded that file as a <script>, which cannot be
   re-read without reloading, so it watches the file's generatedAt stamp
   and reloads when it changes.

   Reloading is deliberately deferred while a customer is choosing. Wiping
   a half-built order because stock ticked down elsewhere would be worse
   than showing a menu that is a few minutes old, so it waits for the
   screen to go idle -- which it does after every Place Order. */
/* How often to look for a rebuilt menu.

   This was 300ms, which downloaded the whole of menu-data.js -- 20KB and
   growing with the menu -- three times a second and ran a regex over it,
   for ever, on a Pi that is also driving the machine. The file it watches
   is rewritten by store_gui/sync_menu.py at most once a MINUTE, so 300ms
   asked two hundred times more often than the answer could possibly
   change.

   Five seconds is still far quicker than the data moves, and it is the
   difference between 12 requests a minute and 200. */
const MENU_CHECK_MS = 5000;

let menuStale = false;
/* Set while a check is in flight. Without it, a fetch that takes longer
   than the interval does not delay the next tick -- it just runs alongside
   it. On a busy machine that is a pile-up: each round is slower than the
   last, so more of them overlap, so the machine gets busier. The screen
   ends up spending its main thread on fetches it started minutes ago and
   stops responding to taps, which is exactly how this was noticed.

   bartender_gui/js/guide.js has had this guard since it was written, with
   the same comment. This file never got one. */
let menuCheckInFlight = false;

/** True when nobody is part-way through an order. */
const screenIsIdle = () => !order && !selected;

async function checkMenuFreshness(){
  if(!MENU || !MENU.generatedAt) return;
  if(menuCheckInFlight) return;   // never let requests pile up

  menuCheckInFlight = true;

  let text;
  try{
    const response = await fetch('menu-data.js', {cache:'no-store'});
    if(!response.ok) return;
    text = await response.text();
  }catch(error){
    return;                      // the server is unreachable; try later
  }finally{
    menuCheckInFlight = false;
  }

  const found = /"generatedAt":\s*"([^"]+)"/.exec(text);
  if(!found || found[1] === MENU.generatedAt) return;

  menuStale = true;
  renderTopbar();               // say so in the chip straight away

  if(screenIsIdle()) adoptMenu(text);
}

/* Take a rebuilt menu-data.js into the running page.

   WHY THIS IS NOT A RELOAD
     It used to be. menu-data.js arrives as a <script> that assigns
     window.MENU_DATA, and a second <script> would redeclare every const
     this page holds -- so the only way to pick up a new one was to reload
     the whole page.

     Reloading an unattended kiosk has costs that only showed up once the
     menu grew: the browser restores the scroll position, so a screen
     nobody was standing at came back looking at the middle of the list.
     It also throws away the language choice, the search box, and any
     scroll the customer was part-way through.

     The file only ever assigns window.MENU_DATA, so it can be run against
     a FAKE window instead. Nothing it does touches this page's scope, and
     what comes back is just the data.

   WHY THE ARRAYS ARE EMPTIED RATHER THAN REPLACED
     CATS and ITEMS are const, and half the file closes over them. Refilling
     them in place keeps every one of those references pointing at the live
     list -- reassigning would leave the renderers drawing yesterday's menu
     from a binding they captured at load. */
function adoptMenu(text){
  let fresh;

  try{
    const sandbox = {};
    // eslint-disable-next-line no-new-func
    new Function('window', text)(sandbox);
    fresh = sandbox.MENU_DATA;
  }catch(error){
    console.error('[menu] could not read the rebuilt menu:', error);
    return;                     // keep the menu on screen; try again later
  }

  if(!fresh || !Array.isArray(fresh.drinks) || !Array.isArray(fresh.categories)){
    console.error('[menu] rebuilt file has an unexpected shape; keeping the old menu');
    return;
  }

  CATS.length = 0;
  CATS.push(...toCats(fresh));
  ITEMS.length = 0;
  ITEMS.push(...toItems(fresh));
  // Same rule as the two arrays above: these are consts the renderers
  // close over, so their CONTENTS are replaced rather than the bindings.
  // This is how an operator ticking a star, widening the bán-chạy window
  // or reordering the page reaches a kiosk nobody is standing at.
  Object.assign(FEATURED, toStrip(fresh.featured, 'Món nổi bật'));
  Object.assign(BESTSELLER, toStrip(fresh.bestseller, 'Bán chạy nhất'));
  LAYOUT.length = 0;
  LAYOUT.push(...toLayout(fresh));
  placeBlocks();

  // The stamp the freshness check compares against, and the one the topbar
  // chip ages. Mutated, not rebound: MENU is a const pointing at the object.
  MENU.generatedAt = fresh.generatedAt;

  // A drink that has just left the menu must not stay selected, or the
  // detail panel would go on offering something the machine no longer has.
  if(selected && !ITEMS.some(item => item.drinkId === selected.drinkId)){
    selected = null;
    panelMode = 'item';
    closeSidebar();
  }

  menuStale = false;
  activeCat = CATS.some(c => c.id === activeCat) ? activeCat : 'all';

  renderCats();
  renderGrid();
  renderDetail();
  renderTopbar();
  scrollMenuToTop();
  console.log('[menu] picked up a rebuilt menu without reloading');
}

/** Called when an order ends, so a deferred update happens promptly. */
async function reloadIfMenuStale(){
  if(!menuStale || !screenIsIdle()) return;

  try{
    const response = await fetch('menu-data.js', {cache:'no-store'});
    if(response.ok) adoptMenu(await response.text());
  }catch(error){
    /* still unreachable; the interval will try again */
  }
}

window.setInterval(checkMenuFreshness, MENU_CHECK_MS);

/* ---------------- HANDOFF TO THE BARTENDER SCREEN ----------------
   order/run_flow.py writes order/handoff.json once the machine is ready and
   its screen is actually listening. This page polls that file and moves
   itself across.

   A file rather than a push, because nothing here can be pushed to: the
   shop screen may be a tablet on the far side of the room, and the Python
   process has no way to reach into its browser.

   The address is rebuilt from THIS page's hostname plus the port in the
   file. Whatever address the shop screen used to reach the store page --
   localhost, the LAN address, Tailscale -- keeps working; a URL baked in by
   the machine would only be right for one of them. */
const HANDOFF_URL = '../order/handoff.json';
const HANDOFF_POLL_MS = 1000;

/* Set when the Start button above hands an order to the machine. The
   confirm box below exists for somebody ELSE's scan landing on a screen
   mid-order; when this screen started the order itself there is nothing to
   ask about and nothing to lose.

   `printedHere` is the other half of that sentence and is read beside this
   one -- printing a label and having it scanned is this screen sending the
   order to the machine just as much, only with a walk to the printer in
   between. */
let startedHere = false;

/* The order_id this page started with, so a handoff left over from the last
   order does not throw a fresh customer straight onto the bartender screen.
   null is a real value here -- it means "no order was running when I
   loaded" -- which is why a separate flag records whether the baseline has
   been taken at all.

   Reading a 404 as "no answer yet" was a bug: with no handoff.json on the
   page's first poll the baseline was never taken, so the first real order
   became the baseline and the page sat there. A 404 IS the answer -- no
   order in progress -- and has to count. */
let handoffReady = false;
let handoffSeen = null;

async function pollHandoff(){
  let data = null;

  try{
    const response = await fetch(HANDOFF_URL, {cache:'no-store'});
    if(response.ok) data = await response.json();
    // any other status means no order is running: a real answer, not a
    // failure, so it still establishes the baseline below
  }catch(error){
    return;   // the server is unreachable -- no answer at all, try again
  }

  const orderId = (data && data.order_id) ? data.order_id : null;

  // order/handoff.json exists for exactly as long as an order does --
  // run_flow writes it when the runner comes up and clear_handoff() removes
  // it when the drink ends, however it ends. So its presence IS "the
  // machine is busy", and this screen was already polling it.
  showBusyBanner(data);

  if(!handoffReady){
    handoffReady = true;
    handoffSeen = orderId;
    return;
  }

  if(orderId === null || orderId === handoffSeen) return;

  handoffSeen = orderId;
  const path = data.gui_path || '/bartender_gui/index.html';
  // Same origin, deliberately. This used to rebuild the address around
  // data.gui_port -- the runner's own server, which exists only while a
  // drink is pouring. A browser that arrived a moment after it closed got
  // "this site can't be reached" and had no way back. Every screen is on
  // one port now, and that port is the one this page is already on.
  const back = encodeURIComponent(location.href.split('?')[0]);
  const target = location.origin + path + '?back=' + back;


  console.log('[handoff] order ' + orderId + ' -> ' + target);

  // Someone is part-way through choosing a drink on this screen. Jumping
  // now would throw their work away with no warning and no way back, so
  // ask. An empty screen has nothing to lose and goes straight across.
  //
  // printedHere counts the same as startedHere, and missing it was a bug:
  // a label printed from this modal and then SCANNED is this screen's own
  // order arriving at the machine, not somebody else's landing on top of
  // it. The box asked whether to discard "your unfinished order" about
  // the very drink that had just started -- and there was nothing
  // unfinished and nothing to lose, because the ticket is spent and the
  // paper is already in the customer's hand.
  //
  // It stays honest after the modal closes: a print reloads the page (see
  // closeQR), so a NEW order built afterwards has printedHere false again
  // and is protected exactly as before.
  if(order && !startedHere && !printedHere){
    askBeforeHandoff(target, data);
    return;
  }

  // Off the screen BEFORE the jump, not left for the navigation to take
  // away with the page. The order it describes is now the machine's, so
  // there is nothing left on it to press -- and if the jump cannot be made
  // (navigateWhenReachable probes first and stays put when the target does
  // not answer) the alternative is a "Done" modal sitting over an order
  // that has already started.
  dismissQR();

  // Cleared before leaving so the ticket cannot follow this screen to the
  // next customer -- the same reason askBeforeHandoff() clears it.
  order = null; selected = null; forgetTicket();
  navigateWhenReachable(target, 'pha chế');   // same tab, replacing this page
}


/* ---------------- NEVER NAVIGATE INTO A DEAD PAGE ----------------
   Once the browser has shown "this site can't be reached", the tab is inert:
   there is no script left to notice, retry, or come back. Whatever put it
   there cannot undo it, so the only place to stop it is before the jump.

   Every target is same-origin now, so this is a request to the server that
   just answered — quick, and it fails fast when it matters. If it does not
   come back OK the page stays exactly where it is and says so, which leaves
   a working screen instead of a dead one. */
async function navigateWhenReachable(target, what){
  try{
    const probe = await fetch(target, {method:'GET', cache:'no-store'});
    if(!probe.ok) throw new Error('HTTP ' + probe.status);
  }catch(error){
    console.error('[nav] ' + what + ' unreachable, staying put: ' + error);
    // kind 'restart': the calm amber box whose sub-line already says the
    // screen will right itself and the customer need do nothing -- which is
    // exactly true here. showScanNotice() writes that line from `kind`, so
    // passing a `sub` of our own would be silently dropped.
    showScanNotice({
      kind: 'restart',
      title: 'Chưa mở được màn hình ' + what,
      message: String(error.message || error),
    });
    return false;
  }
  window.location.href = target;
  return true;
}

/* ---------------- CONFIRM BEFORE LEAVING AN UNFINISHED ORDER ----------------
   The scan has already started the machine — that is not in question here
   and this box cannot stop it. The only thing being decided is what happens
   to the half-built order on THIS screen.

   Going is the choice that keeps the machine attended: the drink now being
   poured has a "place the cup" gate on the bartender screen, and nobody is
   watching it while this page is still up. Staying is offered anyway,
   because a customer who has spent a minute customising a drink should not
   lose it to somebody else's scan without being asked. */
function askBeforeHandoff(target, data){
  const machine = (data && data.drink_name) ? data.drink_name : 'a drink';
  document.getElementById('confirmmsg').textContent =
    'The machine has started making ' + machine + '.';
  document.getElementById('confirmoverlay').classList.add('show');

  document.getElementById('confirmgo').onclick = ()=>{
    document.getElementById('confirmoverlay').classList.remove('show');
    // The order modal can be open underneath this box -- opened, not yet
    // printed, when somebody else's label was scanned. Discarding the
    // order means discarding what that modal is about.
    dismissQR();
    // Cleared before leaving rather than left for the page to forget on
    // reload: forgetTicket() drops the QR issued for this order, so the
    // serial cannot come back attached to whoever uses this screen next.
    order = null; selected = null; forgetTicket();
    navigateWhenReachable(target, 'pha chế');
  };

  document.getElementById('confirmstay').onclick = ()=>{
    document.getElementById('confirmoverlay').classList.remove('show');
    // The order is kept exactly as it was. handoffSeen has already moved
    // on, so this will not ask again for the same drink.
    console.log('[handoff] stayed on the store screen; order kept');
  };
}

/* ---------------- REFUSED SCAN ----------------
   order/run_flow.py writes order/scan_notice.json when a scanned code
   cannot become a drink — already used, expired, from another machine, or
   a drink with no recipe. Before this, that sentence went only to the
   terminal behind the machine, facing away from the person holding the
   label: they scanned, nothing happened, and no screen said why.

   Polled on the same tick as the handoff. Both are one small file read
   from the same server, and one timer keeps their order predictable: a
   notice is only ever written when no handoff follows it, so the page can
   never be navigating away and popping a box at the same moment. */
const NOTICE_URL = '../order/scan_notice.json';

/* How long the box stays up on its own. Long enough to read twice at a
   machine, short enough that the screen is clear for the next customer
   without staff having to touch it. Dismissing it by hand still works. */
const NOTICE_SECONDS = 20;

/* The restart box is the exception. It is not there to be acted on and
   there is nothing to remember from it -- the machine is going down in
   about five seconds and taking this page with it. A counter ticking from
   20 promised a wait far longer than the one actually happening, so it
   counts the restart down instead: it reaches zero at roughly the moment
   the screen goes dark, and if the customer dismisses it early they lose
   nothing. Keep in step with STORE_RESTART_NOTICE_SECONDS in
   order/run_flow.py. */
const RESTART_NOTICE_SECONDS = 5;

/* How recent a notice has to be to survive this page loading.

   The baseline rule below exists so a notice left on disk from yesterday
   does not pop up at whoever walks in this morning. But it was swallowing
   the case it is needed for MOST: an order cancelled at the machine writes
   the notice and then sends the browser here, so the notice is always
   older than the page — and being the first thing seen, it became the
   baseline and was never shown. Anything written in the last minute is
   about the customer standing here now. */
const NOTICE_FRESH_MS = 60000;

/* Same baseline rule as the handoff: a notice left on disk from before
   this page loaded is not news — unless it is fresh, see above. */
let noticeReady = false;
let noticeSeen = null;
let noticeTimer = null;

/* The heading the markup ships with, restored whenever a notice does not
   carry one of its own. Read once, before anything can overwrite it. */
const NOTICE_DEFAULT_TITLE = document.getElementById('scantitle').textContent;
const NOTICE_DEFAULT_SUB = document.getElementById('scansub').textContent;

/* Which notice this screen has already shown, remembered across reloads.

   The notice file stays on disk until the next order clears it, and a page
   reload starts with no memory — so refreshing the store screen popped the
   same fault up again, and again, with no way to make it stop. The id is
   what makes each notice distinct, so remembering the last one dismissed
   is enough: a NEW fault still gets through, the same one does not come
   back. localStorage rather than sessionStorage because a kiosk reload
   opens a new session and would forget immediately. */
const NOTICE_SEEN_KEY = 'flexmix.notice.dismissed';

function noticeAlreadyDismissed(id){
  try{
    return window.localStorage.getItem(NOTICE_SEEN_KEY) === id;
  }catch(error){
    return false;   // private mode or storage disabled: show it, don't crash
  }
}

function rememberNoticeDismissed(id){
  try{
    if(id) window.localStorage.setItem(NOTICE_SEEN_KEY, id);
  }catch(error){ /* nothing to do; it will show once more at worst */ }
}

/* True only while the restart box is up. Panel button 14 takes the machine
   down and this page with it, so that box is the one notice with nothing to
   decide: it is not dismissed, it is outlived. The flag is what stops a tap
   on the backdrop from taking it away, the same reason its button is
   hidden -- see .alertmodal.restarting in drinks-pos.css. */
let noticeIsRestart = false;

function hideScanNotice(){
  noticeIsRestart = false;
  window.clearInterval(noticeTimer);
  noticeTimer = null;
  document.getElementById('scanoverlay').classList.remove('show');
  // Recorded however it closes -- button, backdrop or the countdown --
  // because all three mean the same thing: this one has been seen.
  rememberNoticeDismissed(noticeSeen);
}

function showScanNotice(notice){
  // A cancelled order and a refused QR come through the same box; only the
  // heading tells them apart, so it is reset every time rather than left
  // showing whichever came last.
  document.getElementById('scantitle').textContent =
    notice.title || NOTICE_DEFAULT_TITLE;
  document.getElementById('scanmsg').textContent =
    notice.message || 'Không đọc được mã QR.';

  // A misread is not a fault. The customer has done nothing wrong, the
  // label is probably fine, and the fix is in their hands -- so it gets an
  // amber "try again" box rather than the red one used when a code is
  // genuinely refused or the machine has broken.
  const rescan = notice.kind === 'rescan';

  // Panel button 14. Nothing is broken and nobody has done anything
  // wrong, so it wears the same calm box as a misread rather than the red
  // one -- but its own words: there is nothing to try again, only to wait.
  const restarting = notice.kind === 'restart';

  noticeIsRestart = restarting;
  const alertBox = document.getElementById('scanoverlay')
    .querySelector('.alertmodal');
  alertBox.classList.toggle('rescan', rescan || restarting);
  alertBox.classList.toggle('restarting', restarting);
  document.getElementById('scanicon').innerHTML =
    (rescan || restarting) ? ICON_REDO : ICON_WARN;
  document.getElementById('scansub').textContent = restarting
    ? 'Màn hình sẽ tự sẵn sàng lại, quý khách không cần làm gì.'
    : rescan
      ? 'Đưa mã QR lại gần đầu đọc và quét một lần nữa.'
      : NOTICE_DEFAULT_SUB;

  document.getElementById('scanoverlay').classList.add('show');

  // Restarted from scratch, so a second refusal arriving while the first
  // is still up gets its own full reading time rather than inheriting
  // whatever was left of the last one.
  window.clearInterval(noticeTimer);

  let left = restarting ? RESTART_NOTICE_SECONDS : NOTICE_SECONDS;
  const counter = document.getElementById('scancount');
  counter.textContent = '(' + left + ')';

  noticeTimer = window.setInterval(()=>{
    left -= 1;
    counter.textContent = left > 0 ? '(' + left + ')' : '';

    if(left > 0) return;

    // Every other notice is simply taken down at zero. The restart box
    // hands over instead: the page it is sitting on came from a server
    // that has just stopped, so the box stays up until there is something
    // to come back to.
    if(restarting){
      window.clearInterval(noticeTimer);
      noticeTimer = null;
      reloadWhenMachineIsBack();
      return;
    }

    hideScanNotice();
  }, 1000);
}

/* How often to knock while waiting for the machine, and how long to keep
   knocking. systemd needs about three seconds (RestartSec) plus a moment
   to bind the port, so the limit is many times what a restart takes -- it
   is there so a machine that never comes back does not leave this box up
   for ever. */
const RESTART_PROBE_MS = 500;
const RESTART_WAIT_LIMIT_MS = 60000;

/* Reload, but not one second before there is a page to reload.

   At zero the server this page came from is going down or already gone,
   so reloading on the spot lands on the browser's own error page -- which
   runs no script and cannot pick itself back up. The customer would be
   stuck there until somebody typed a URL. So the box stays on screen, the
   page knocks until the server answers, and only then reloads. */
async function reloadWhenMachineIsBack(){
  const counter = document.getElementById('scancount');
  const deadline = Date.now() + RESTART_WAIT_LIMIT_MS;

  counter.textContent = '';
  document.getElementById('scansub').textContent =
    'Đang chờ máy khởi động lại...';

  for(;;){
    try{
      // Same origin, so a plain fetch is readable. ANY answer means the
      // server is serving again -- 404 included, because startup deletes
      // this very file.
      await fetch(NOTICE_URL + '?up=' + Date.now(), {cache:'no-store'});
      window.location.reload();
      return;
    }catch(error){
      if(Date.now() >= deadline){
        console.warn('[restart] machine still down after '
          + (RESTART_WAIT_LIMIT_MS / 1000) + 's; giving up on the reload');
        hideScanNotice();
        return;
      }
    }

    await new Promise(resolve=>window.setTimeout(resolve, RESTART_PROBE_MS));
  }
}

document.getElementById('scanok').onclick = hideScanNotice;
document.getElementById('scanoverlay').onclick = (event)=>{
  // Only the backdrop. A tap that lands on the box itself should not
  // dismiss the thing the customer is still reading.
  // The restart box has no way out on purpose: the machine closes it by
  // coming back and reloading the page.
  if(event.target.id === 'scanoverlay' && !noticeIsRestart) hideScanNotice();
};

async function pollScanNotice(){
  let data = null;

  try{
    const response = await fetch(NOTICE_URL, {cache:'no-store'});
    if(response.ok) data = await response.json();
    // Any other status means there is no notice — a real answer, and it
    // still establishes the baseline below.
  }catch(error){
    return;   // server unreachable: no answer at all, try again
  }

  const id = (data && data.id) ? data.id : null;

  if(!noticeReady){
    noticeReady = true;
    noticeSeen = id;
    // Fresh enough to be about the person in front of this screen — most
    // often an order just cancelled at the machine, which sent the browser
    // straight here. Anything older is history and stays baselined.
    const age = data && data.created_at
      ? Date.now() - Date.parse(data.created_at) : Infinity;
    if(id !== null && age >= 0 && age < NOTICE_FRESH_MS
       && !noticeAlreadyDismissed(id)){
      console.log('[scan] arrived with a fresh notice: ' + data.message);
      showScanNotice(data);
    }
    return;
  }

  if(id === null || id === noticeSeen) return;

  noticeSeen = id;
  console.log('[scan] refused: ' + data.message);
  showScanNotice(data);
}

/* ---------------- PANEL BUTTON 15: OPEN THE TEST SCREEN ----------------
   test_gui/serve.py watches panel button 15 while the machine is idle and
   flips test_gui/mode.json. This page follows it, so an engineer standing
   at the machine can reach the test screen with one press and no keyboard.

   A file and a poll, like the handoff: nothing here can navigate a browser
   that may be a tablet on the other side of the room.

   The `id` changes on every press, so a reload cannot re-obey the last
   instruction — and the baseline rule means a flag left open from earlier
   does not drag a customer onto the test screen when this page loads. */
const TEST_MODE_URL = '../test_gui/mode.json';

let testModeReady = false;
let testModeSeen = null;

async function pollTestMode(){
  let data = null;

  try{
    const response = await fetch(TEST_MODE_URL, {cache:'no-store'});
    if(response.ok) data = await response.json();
  }catch(error){
    return;                      // the test server is not running
  }

  const id = (data && data.id) ? data.id : null;

  if(!testModeReady){
    testModeReady = true;
    testModeSeen = id;
    return;
  }

  if(id === null || id === testModeSeen) return;

  testModeSeen = id;
  if(!data.open) return;         // it was closed, and we are already here

  // Built from THIS page's hostname plus the port in the file, so the jump
  // works from localhost, the LAN address or Tailscale alike. ?back= is
  // how the test screen finds its way home again.
  // Same origin, for the same reason as the bartender handoff above: the
  // test screen is served from this port too, so there is no second address
  // to guess at and nothing to be stranded on.
  const back = encodeURIComponent(location.href.split('?')[0]);
  const target = location.origin +
    (data.path || '/test_gui/index.html') + '?back=' + back;

  console.log('[test] panel button -> ' + target);
  navigateWhenReachable(target, 'test tay');
}

pollHandoff();                       // take the baseline now
pollScanNotice();
pollTestMode();
/* The same guard, for the same reason. Three fetches go out on every tick
   here; a slow round used to start a fourth, fifth and sixth on top of the
   ones still running. */
let statusPollInFlight = false;

window.setInterval(async ()=>{
  if(statusPollInFlight) return;
  statusPollInFlight = true;

  try{
    await Promise.all([pollHandoff(), pollScanNotice(), pollTestMode()]);
  }finally{
    statusPollInFlight = false;
  }
}, HANDOFF_POLL_MS);

/* ---------------- INIT ---------------- */
renderTopbar();
window.setInterval(renderTopbar, 30000);
renderCats();
// Before the first paint: renderGrid() measures the column for the page
// dots, and it must measure the blocks where they are actually going to
// sit, not where the markup happened to declare them.
placeBlocks();
renderGrid();
renderBill();


/* ---------------- DETAIL PANEL: SHOW / HIDE ----------------
   The panel has nothing to say until a drink is picked, so it stays off
   screen and the menu runs the full width. Picking a drink slides it in;
   the x, Esc, or removing the drink from the bill sends it back.

   Closing clears the selection rather than merely hiding the panel: a
   hidden panel still holding a half-configured drink would silently reopen
   with the previous customer's sugar and toppings on it. */
function sidebarOpen(){
  return document.getElementById('app').classList.contains('side-open');
}
function openSidebar(){
  document.getElementById('app').classList.add('side-open');
  updateBillFab();
}
function closeSidebar(){
  document.getElementById('app').classList.remove('side-open');
  panelMode = 'item';
  if(selected){
    selected = null;
    renderGrid();
    renderDetail();
  }
  updateBillFab();
}
function updateBillFab(){
  const fab = document.getElementById('billfab');
  if(!fab) return;
  fab.classList.toggle('show', !sidebarOpen() && !!order);
  document.getElementById('bfTotal').textContent =
    '$' + (order ? order.unit : 0).toFixed(2);
}

document.getElementById('rclose').onclick = closeSidebar;

/* Straight to the bill, not just to the panel: the only reason to press
   this is the drink already added. */
document.getElementById('billfab').onclick = ()=>{
  // The drawer opens ON the order rather than on an empty item panel with
  // the bill strip expanded underneath it -- that strip has one line's room
  // and this button exists to show the order in full.
  panelMode = 'bill';
  renderDetail();
  openSidebar();
};

document.addEventListener('keydown', e=>{
  if(e.key!=='Escape' || !sidebarOpen()) return;
  // A modal is on top and owns Esc; dismissing the panel underneath it
  // would leave the modal floating over a screen that had moved on.
  if(document.querySelector('.overlay.show')) return;
  closeSidebar();
});

updateBillFab();



/* ---------------- THE MACHINE IS ALREADY MAKING SOMETHING ----------------
   An order that has been started holds the machine until it finishes or is
   cancelled -- one glass, one load cell, one drink at a time. A second
   order cannot start on top of it.

   That was invisible from here. A label printed and scanned while an
   earlier drink was still waiting to be collected simply did nothing: the
   scanner read it, the file was written, and run_flow ignored it because
   it was still holding the previous order. Three scans, no reaction, no
   reason given.

   WHY THIS DOES NOT CANCEL THE OLD ORDER BY ITSELF
     Because it cannot know whether that drink is standing finished on the
     platform or half-poured with the pumps running. Cancelling the second
     of those throws away a drink somebody paid for, and it would happen
     silently every time a customer wandered back to this screen. Ending an
     order is a decision with a cup in front of it, so it belongs on the
     bartender screen where the cup is. This says what is happening and
     offers the way there. */
function showBusyBanner(data){
  const bar = document.getElementById('busybar');
  if(!bar) return;

  const name = data && data.drink_name ? data.drink_name : '';
  const busy = Boolean(data && data.order_id);

  /* THE DRINK IS MADE AND THE MACHINE IS STILL TIDYING UP
     The two are not the same state, and this banner used to show only the
     first one. run_flow keeps the handoff for CLEAR_DELAY_SECONDS after
     the runner exits, so that current_recipe.json outlives the bartender
     screen's thank-you countdown -- but that screen hands the browser
     BACK here 5s after the drink finishes, several seconds before the
     handoff goes. The customer arrived holding the drink and was told the
     machine was still pouring it, with a button offering to take them to
     an order that had already ended.

     The file has to stay -- clear_order_files() wipes raw_qr.json at the
     end of the wait, so a label scanned in the meantime is swallowed
     without a word, and this banner is the only thing that stops that
     being a mystery. So it stays up and says the true thing instead:
     wait a moment, then scan again. */
  const finished = busy && Boolean(data.finished);

  bar.classList.toggle('show', busy);
  bar.dataset.state = finished ? 'done' : 'busy';

  if(!busy) return;

  const label = document.getElementById('busytext');
  // Plain strings, like every other operational message on this screen
  // (showScanNotice, the QR modal). This page has no i18n module.
  let wanted;

  if(finished){
    wanted = name
      ? `Đã pha xong "${name}". Máy đang dọn dẹp, vui lòng quét mã sau vài giây.`
      : 'Đơn vừa xong. Máy đang dọn dẹp, vui lòng quét mã sau vài giây.';
  }else{
    wanted = name
      ? `Máy đang pha "${name}". Hoàn tất hoặc hủy đơn đó rồi mới làm món mới.`
      : 'Máy đang bận một đơn. Hoàn tất hoặc hủy đơn đó rồi mới làm món mới.';
  }

  if(label && label.textContent !== wanted) label.textContent = wanted;

  const go = document.getElementById('busygo');

  // Nothing to go and look at once the drink is done: the bartender screen
  // has already sent this browser back, and the recipe it reads is seconds
  // from being cleared. The button would land the customer on an empty
  // screen that immediately returns them here.
  if(go) go.hidden = finished;

  if(go && !go.dataset.wired){
    go.dataset.wired = '1';
    go.onclick = ()=>{
      const back = encodeURIComponent(location.href.split('?')[0]);
      navigateWhenReachable(
        location.origin + '/bartender_gui/index.html?back=' + back,
        'pha chế');
    };
  }
}

/* ---------------- THE SCREEN GOES BACK TO THE TOP ----------------
   This page reloads itself when the menu is rebuilt, which on an idle
   machine happens with nobody in front of it. Chromium restores the scroll
   position across a reload, so a customer who scrolled down to browse and
   then walked away left the NEXT customer looking at the middle of the
   list -- no date, no categories, no search box, and no obvious way back
   up. It looked like the screen had broken.

   It only started showing because the menu grew: with eight drinks there
   was nothing to scroll.

   Two halves. Tell the browser not to restore, and put the column back at
   the top ourselves -- on load, and again whenever the screen falls idle,
   because a kiosk between customers should be showing its first screen. */
try {
  history.scrollRestoration = 'manual';
} catch (error) {
  /* not supported: the explicit reset below still does the work */
}

function scrollMenuToTop(){
  const column = document.querySelector('.left');
  if(!column) return;
  // 'instant': .left is styled scroll-behavior:smooth for the page dots,
  // and a kiosk resetting itself should not be seen gliding upwards.
  column.scrollTo({top:0, behavior:'instant'});
}

scrollMenuToTop();
window.addEventListener('pageshow', scrollMenuToTop);

/* ---------------- MENU PAGE DOTS ----------------
   Replaces the browser's scrollbar on the menu column. A touch screen has no
   pointer to grab a 6px thumb with, and the bar told the customer nothing
   except that more existed somewhere below; dots say how much more, in
   screenfuls, and each one is a target big enough for a finger.

   A "page" here is one visible height of the column. The last page is
   usually a partial one -- scrolling to it lands at the bottom of the range
   rather than one full screen past the second-to-last. */
/* Looked up per call rather than held in a const: renderGrid() runs during
   INIT, above this block, and a const here would still be in its temporal
   dead zone when that first call reaches for it. */
function leftCol(){ return document.querySelector('.left'); }
function dotsBar(){ return document.getElementById('scrolldots'); }

function scrollPageCount(){
  const leftEl = leftCol();
  const h = leftEl.clientHeight;
  if(!h) return 1;
  // A stray pixel or two of rounding is not another page.
  return Math.max(1, Math.ceil((leftEl.scrollHeight - 2) / h));
}

function buildScrollDots(){
  const leftEl = leftCol(), dotsEl = dotsBar();
  if(!leftEl || !dotsEl) return;
  const pages = scrollPageCount();
  dotsEl.classList.toggle('show', pages > 1);
  if(pages <= 1){ dotsEl.innerHTML = ''; return; }
  if(dotsEl.children.length !== pages){
    dotsEl.innerHTML = '';
    for(let i = 0; i < pages; i++){
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'dot';
      b.setAttribute('role', 'tab');
      b.setAttribute('aria-label', 'Menu page ' + (i + 1) + ' of ' + pages);
      b.onclick = ()=>{
        const max = leftEl.scrollHeight - leftEl.clientHeight;
        leftEl.scrollTop = Math.min(i * leftEl.clientHeight, max);
      };
      dotsEl.appendChild(b);
    }
  }
  syncScrollDots();
}

function syncScrollDots(){
  const leftEl = leftCol(), dotsEl = dotsBar();
  if(!leftEl || !dotsEl) return;
  const dots = dotsEl.children;
  if(!dots.length) return;
  const max = leftEl.scrollHeight - leftEl.clientHeight;
  // Rounding, not flooring: the last page is a partial one, so scrolled to
  // the very bottom you are nearer its start than the previous page's.
  const page = max > 0
    ? Math.round((leftEl.scrollTop / max) * (dots.length - 1))
    : 0;
  for(let i = 0; i < dots.length; i++){
    dots[i].classList.toggle('on', i === page);
    dots[i].setAttribute('aria-selected', i === page ? 'true' : 'false');
  }
}

/* The deck is position:sticky, so it is in the flow until the menu has
   scrolled under it -- and a hairline and a shadow on a deck that is still
   sitting in the page would be a rule drawn across the middle of nothing.
   .stuck is what tells it the cards are now passing behind it. */
function syncDeckStuck(){
  const leftEl = leftCol(), deck = document.getElementById('deck');
  if(!leftEl || !deck) return;
  deck.classList.toggle('stuck', leftEl.scrollTop > 4);
}

// Scroll fires far faster than the screen repaints; one update per frame is
// all the dots and the deck can show.
let dotsFrame = 0;
leftCol().addEventListener('scroll', ()=>{
  if(dotsFrame) return;
  dotsFrame = requestAnimationFrame(()=>{
    dotsFrame = 0; syncScrollDots(); syncDeckStuck();
  });
});
window.addEventListener('resize', buildScrollDots);
// Card images arrive after this script runs and each one adds height, so the
// first count is taken again once they have all landed.
window.addEventListener('load', buildScrollDots);

buildScrollDots();

// Which buttons this shop offers, fetched once on load so the FIRST order
// of a session is already right. Every one after it is covered by the
// refresh showQR() fires -- and by closeQR()'s reload once a label exists.
loadOrderMode();
