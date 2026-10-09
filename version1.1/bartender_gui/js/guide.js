"use strict";

/* ==========================================================================
   FlexMix — bartender guidance screen (auto-run model)
   --------------------------------------------------------------------------
   WHAT THIS FILE IS
     The whole screen. It reads the machine's state and draws it. It never
     decides anything: the machine owns every status, and this file only
     reflects what it finds in the file.

   THE MACHINE OWNS THE TRUTH
     Data source, in priority order:
       1. window.FLEXMIX_RECIPE_SOURCE.read()  <- the simulator, if loaded
       2. GET ../order/current_recipe.json     <- the live machine

     That file is written by order/process_runner.py as it works. Both
     sides speak the statuses in PROCESS_SCHEMA.md:
       pending -> waiting -> running -> done, or failed.

   THE FLOW OF ONE TICK
     1. pollLoop() fetches the file every POLL_INTERVAL_MS (slower while
        the machine is unreachable).
     2. adaptProcess() translates the file into the vocabulary the
        renderer below uses: done->completed, running->processing, and
        gates inferred from a step's shape rather than a type field --
        buttons[] means the panel releases it, sensor{} means a reading
        does, neither means a plain on-screen confirm.
     3. currentStep() picks the step marked running, else the earliest
        unfinished one.
     4. render() draws either the pour meters or, at a human gate, an
        overlay that takes the whole screen so it cannot be missed.

   HOW THE POUR METERS KNOW WHERE THEY ARE
     Each pump carries duration_sec -- the seconds the MACHINE computed
     from that pump's own calibration. The bar is elapsed/duration, so
     the bar and the pump run off one clock and no calibration is
     repeated here. Grams are carried for display only and drive nothing.

     Elapsed is measured from the machine's started_at, but only while
     that stamp is fresh in both directions (see stepStartMs). The
     browser may be on another machine whose clock differs; when it does,
     the meter falls back to this screen's own reading of when the step
     appeared, which measures the pour correctly however far the two
     clocks have drifted.

   WHAT THE SCREEN MAY WRITE
     Almost nothing. Three POSTs, each a request the machine is free to
     refuse, and none of which change a status directly:
       /api/confirm         release the place-the-glass gate
       /api/process/button  light one lamp on a manual step
       /api/process/detect  ask for one cup check, get back {detected}
     The machine performs the action and writes the resulting status
     itself, which is why the screen can never get ahead of the hardware.
   ========================================================================== */

/* ============================================================== CONFIG ==== */

const RECIPE_URL = "../order/current_recipe.json";
const CONFIG_URL = "config/gui_config.json";

/* Populated from configuration/gui_config.json before the first render.
   Everything below falls back to a built-in default when a key is absent,
   so a missing or partial config degrades instead of breaking. */
let CFG = null;
let POLL_INTERVAL_MS = 120;            // fast: the pour meters must feel live
let DOWN_POLL_MS = 1000;               // back off while the machine is unreachable
let STALE_AFTER_MS = 8000;             // a "processing" step that stops updating
let FALLBACK_GRAM_PER_SEC = 10.5;      // overridden by gui_config.json
const PUMP_COUNT = 10;

/* An escape hatch for art that does not follow the naming convention.
   Keys are ingredient_id, plus the gate icon names used by the recipe; an
   entry here wins over anything in images/guide/.
   
   Normally you do not need this: drop a file into images/guide/ using the
   names in that folder's README and it is found without any code change. */
const GUIDE_IMAGES = {
  // 13: "../images/other/pearls.jpg",
  // hand: "../images/other/topping.jpg",
};

const OPEN = new Set([
  "pending",
  "processing",
  "settling",        // finished, held briefly before the next step
  "waiting_confirm", // released by the on-screen button
  "waiting_button",  // released by a physical panel button
  "waiting_sensor",  // released by a machine sensor reading
  "waiting_retry",
]);

/* ================================================================ I18N ==== */

/* localStorage throws a SecurityError on file:// origins and when site data
   is blocked. Reading it unguarded at load time would kill the whole script
   before a single line of UI ran, so every access goes through here. */
const store = {
  get(key) {
    try {
      return localStorage.getItem(key);
    } catch (error) {
      return null;
    }
  },
  set(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch (error) {
      /* private mode or blocked storage: preference just won't persist */
    }
  },
};

let lang = store.get("flexmix.lang") || "vi";

const STR = {
  vi: {
    glassStep: "Trước khi pha",
    glassTitle: "Lấy đúng ly này",
    glassDetail: "Món này được phục vụ trong ly bên cạnh. Lấy ly, đặt lên máy, rồi xác nhận.",
    glassGot: "Đã lấy ly này",
    /* Labels above each prep fact. Short and upper-cased in CSS: they are
       read as column headings, not as sentences. */
    factGlass: "Ly",
    factIce: "Đá",
    factGarnish: "Trang trí",
    factMethod: "Cách dựng ly",
    noOrder: "Đang chờ đơn hàng",
    noOrderDetail: "Quét mã QR của khách để bắt đầu.",
    connecting: "Đang kết nối",
    live: "Đã kết nối",
    sim: "Mô phỏng",
    down: "Mất kết nối",
    stale: "Máy không phản hồi",
    stepOf: (a, b) => `Bước ${a} / ${b}`,
    typePump: "Tự động",
    typeGate: "Cần thao tác",
    typeDone: "Hoàn tất",
    typeRetry: "Lỗi",
    eyebrowAuto: "Máy đang chạy",
    eyebrowDone: "Xong",
    eyebrowWait: "Chờ thao tác",
    pouringNamed: names => `Đang bơm ${names}`,
    listAnd: "và",
    pouringDetail: "Không cần thao tác. Máy sẽ tự dừng khi cần bạn.",
    handsOff: "Không cần thao tác",
    percentDone: n => `${n}%`,
    settling: "Xong bước này",
    waitingStep: "Chờ máy chạy",
    doneTitle: "Đồ uống đã xong",
    doneDetail: "Lấy ly ra và phục vụ khách.",
    retryTitle: "Bơm bị lỗi",
    retryDetail: "Kiểm tra ống và bình chứa, sau đó thử lại.",
    retryBtn: "Thử lại bước này",
    gateBadge: "Cần thao tác",
    startBadge: "Sẵn sàng pha",
    confirm: "Xác nhận",
    waitingBtn: "Đang xử lý...",
    pausingTitle: "Đang dừng máy...",
    pausingDetail: "Máy sẽ dừng khi xong bước hiện tại.",
    pausedTitle: "Máy đã tạm dừng",
    pausedDetail: "Bấm Tiếp tục để pha nốt, hoặc chọn lý do để hủy đơn.",
    thanksBadge: "Hoàn tất",
    thanksTitle: "Cảm ơn quý khách!",
    thanksDetail: name => `${name} đã pha xong. Mời quý khách nhận đồ uống.`,
    returningIn: "Quay lại màn hình đặt món sau",
    seconds: "giây",
    restartBadge: "Khởi động lại",
    restartTitle: "Máy đang khởi động lại",
    restartDetail: "Máy sẽ hoạt động lại sau vài giây. "
      + "Màn hình tự quay về trang đặt món, quý khách không cần làm gì.",
    waitingButton: "Bấm nút topping trên máy sau khi cho vào ly",
    waitingButtonCount: (a, b) => `Đã bấm ${a} / ${b} — còn ${b - a} nút nữa`,
    allButtonsLit: "Đã đủ topping — chờ máy chạy tiếp",
    allButtonsLit: "Đã đủ topping — chờ máy chạy tiếp",
    waitingButtonShort: "Chờ nút trên máy",
    waitingSensor: (a, b) => `Máy đang chờ nhận ly — ${a} / ${b} g`,
    waitingSensorPlain: "Máy đang chờ nhận ly",
    checkCup: "Kiểm tra ly",
    cupSeen: "Đã thấy ly — chờ máy chạy tiếp",
    noCup: (a, b) => `Chưa thấy ly — ${a} / ${b} g. Đặt ly rồi bấm lại.`,
    hwSimNote: "Mô phỏng — bấm vào nút ở trên để giả lập nút cứng.",
    hwTapNote: "Bấm vào nút ở trên sau khi cho topping vào ly.",
    remaining: s => `còn ${s}s`,
    steps: "Quy trình",
    nowPanel: "Đang diễn ra",
    filledPercent: n => `Đã rót ${n}%`,
    filledDone: "Đã rót đầy ly",
    pumpIdle: "Nghỉ",
    pumpRunning: n => `${n} đang chạy`,
    stateWaiting: "Chờ",
    stateRunning: "Đang chạy",
    stateDone: "Xong",
    stateRetry: "Lỗi",
    autoStep: "Tự động",
    manualStep: "Thao tác tay",
    newOrder: "Đơn mới",
    simFail: "Giả lập lỗi",
    noteLabel: "Yêu cầu riêng của khách",
    today: "Hôm nay",
    avgPerCup: "TB mỗi ly",
    lastCup: "Ly gần nhất",
    nowClock: "Bây giờ",
    cups: n => `${n} ly`,
    mode: "Chế độ",
    modeSim: "Mô phỏng",
    modeLive: "Trực tiếp",
    modeOffline: "Mất kết nối",
    nextOrder: "Đơn tiếp theo",
    nextOrderHint: "Máy sẽ chờ quét mã QR tiếp theo.",
    drink: "Món",
    speed: "Tốc độ",
  },
  en: {
    glassStep: "Before pouring",
    glassTitle: "Fetch this glass",
    glassDetail: "This drink is served in the glass beside. Fetch it, set it on the machine, then confirm.",
    glassGot: "Got this glass",
    factGlass: "Glass",
    factIce: "Ice",
    factGarnish: "Garnish",
    factMethod: "Build",
    noOrder: "Waiting for an order",
    noOrderDetail: "Scan the customer's QR code to begin.",
    connecting: "Connecting",
    live: "Connected",
    sim: "Simulation",
    down: "Disconnected",
    stale: "Machine not responding",
    stepOf: (a, b) => `Step ${a} of ${b}`,
    typePump: "Automatic",
    typeGate: "Action needed",
    typeDone: "Complete",
    typeRetry: "Failed",
    eyebrowAuto: "Machine is working",
    eyebrowDone: "Finished",
    eyebrowWait: "Waiting for you",
    pouringNamed: names => `Pouring ${names}`,
    listAnd: "and",
    pouringDetail: "Nothing to do. The machine will stop when it needs you.",
    handsOff: "Hands off",
    percentDone: n => `${n}%`,
    settling: "Step complete",
    waitingStep: "Waiting for machine",
    doneTitle: "Drink is ready",
    doneDetail: "Take the cup and serve.",
    retryTitle: "A pump failed",
    retryDetail: "Check the tube and the bottle, then try again.",
    retryBtn: "Retry this step",
    gateBadge: "Action needed",
    startBadge: "Ready to pour",
    confirm: "Confirm",
    waitingBtn: "Waiting...",
    pausingTitle: "Stopping...",
    pausingDetail: "The machine will stop after the current step.",
    pausedTitle: "Machine paused",
    pausedDetail: "Press Continue to finish the drink, or pick a reason to cancel.",
    thanksBadge: "All done",
    thanksTitle: "Thank you!",
    thanksDetail: name => `${name} is ready. Please take your drink.`,
    returningIn: "Back to the order screen in",
    seconds: "s",
    restartBadge: "Restarting",
    restartTitle: "The machine is restarting",
    restartDetail: "It will be back in a few seconds. This screen returns "
      + "to the order page on its own -- nothing to do.",
    waitingButton: "Press each topping button on the machine as you add it",
    waitingButtonCount: (a, b) => `${a} of ${b} pressed — ${b - a} to go`,
    allButtonsLit: "All toppings added — waiting for the machine",
    allButtonsLit: "All toppings added — waiting for the machine",
    waitingButtonShort: "Waiting for panel buttons",
    waitingSensor: (a, b) => `Waiting for the cup — ${a} / ${b} g`,
    waitingSensorPlain: "Waiting for the cup",
    checkCup: "Check the cup",
    cupSeen: "Cup detected — waiting for the machine",
    noCup: (a, b) => `No cup detected — ${a} / ${b} g. Place it and press again.`,
    hwSimNote: "Simulation — click a button above to fake a hardware press.",
    hwTapNote: "Tap a button above once you have added that topping.",
    remaining: s => `${s}s left`,
    steps: "Process",
    nowPanel: "Happening now",
    filledPercent: n => `${n}% poured`,
    filledDone: "Cup is full",
    pumpIdle: "Idle",
    pumpRunning: n => `${n} running`,
    stateWaiting: "Waiting",
    stateRunning: "Running",
    stateDone: "Done",
    stateRetry: "Failed",
    autoStep: "Automatic",
    manualStep: "Manual",
    newOrder: "New order",
    simFail: "Simulate failure",
    noteLabel: "Customer's special request",
    today: "Today",
    avgPerCup: "Avg per cup",
    lastCup: "Last cup",
    nowClock: "Now",
    cups: n => `${n} cups`,
    mode: "Mode",
    modeSim: "Simulation",
    modeLive: "Live",
    modeOffline: "Offline",
    nextOrder: "Next order",
    nextOrderHint: "The machine will wait for the next QR scan.",
    drink: "Drink",
    speed: "Speed",
  },
};

const t = key => STR[lang][key];
/** Recipe text can be a plain string or a {vi, en} pair. */
const localised = value =>
  value && typeof value === "object" ? value[lang] || value.en || "" : value || "";

/* Recipe files store ingredient names in English. Show Vietnamese when the
   UI is in Vietnamese; anything not listed falls back to the recipe's own
   name, so a new ingredient still displays sensibly. */
const INGREDIENT_VI = {
  1: "Nước", 2: "Trà", 3: "Cà phê", 4: "Siro đào", 5: "Siro dâu",
  6: "Soda", 7: "Đường", 8: "Sữa", 9: "Kem", 10: "Sô-cô-la",
  11: "Dâu", 12: "Đá", 13: "Trân châu",
};

const ingredientName = item => {
  if (!item) return "";
  const id = Number(item.ingredient_id);

  const configured = CFG && CFG.ingredients && CFG.ingredients[String(id)];
  // the process file carries {vi, en} straight on the pump entry
  if (item.ingredient_name && typeof item.ingredient_name === "object") {
    const named = localised(item.ingredient_name);
    if (named) return named;
  }
  if (configured && configured.name && configured.name[lang]) {
    return configured.name[lang];
  }
  if (lang === "vi" && INGREDIENT_VI[id]) return INGREDIENT_VI[id];
  return item.ingredient_name || "";
};

/** Icon for an ingredient, preferring the one named in the config. */
const configuredIcon = id => {
  const spec = CFG && CFG.ingredients && CFG.ingredients[String(id)];
  return spec && ICON[spec.icon] ? ICON[spec.icon] : null;
};

/** "Nước, Trà và Cà phê"  /  "Water, Tea and Coffee" */
function joinNames(names) {
  const list = names.filter(Boolean);
  if (list.length <= 1) return list[0] || "";
  return `${list.slice(0, -1).join(", ")} ${t("listAnd")} ${list[list.length - 1]}`;
}

/* =============================================================== ICONS ==== */

const ICON = {
  glass: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M16 12h32l-4 40a4 4 0 0 1-4 4H24a4 4 0 0 1-4-4z"/><path d="M18 32h28" stroke-opacity=".45"/></svg>`,
  water: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M32 8s16 18 16 28a16 16 0 0 1-32 0C16 26 32 8 32 8z"/><path d="M24 38a8 8 0 0 0 8 8" stroke-opacity=".5"/></svg>`,
  tea: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 24h30v14a15 15 0 0 1-30 0z"/><path d="M44 28h5a6 6 0 0 1 0 12h-5"/><path d="M22 16c0-3 3-4 3-7M31 16c0-3 3-4 3-7" stroke-opacity=".55"/><path d="M10 56h40" stroke-opacity=".4"/></svg>`,
  coffee: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 22h30v18a15 15 0 0 1-30 0z"/><path d="M44 26h5a6 6 0 0 1 0 12h-5"/><circle cx="29" cy="32" r="5" stroke-opacity=".45"/><path d="M10 56h40" stroke-opacity=".4"/></svg>`,
  syrup: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M26 8h12v8l6 8v28a4 4 0 0 1-4 4H24a4 4 0 0 1-4-4V24l6-8z"/><path d="M20 34h24" stroke-opacity=".5"/></svg>`,
  soda: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18 14h28l-3 38a4 4 0 0 1-4 4H25a4 4 0 0 1-4-4z"/><circle cx="28" cy="32" r="2.5" stroke-opacity=".6"/><circle cx="37" cy="26" r="2" stroke-opacity=".6"/><circle cx="34" cy="40" r="2.5" stroke-opacity=".6"/></svg>`,
  sugar: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="10" y="20" width="20" height="16" rx="3"/><rect x="32" y="30" width="20" height="16" rx="3"/><path d="M14 26h12M36 36h12" stroke-opacity=".45"/></svg>`,
  milk: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M24 8h16v10l6 10v26a4 4 0 0 1-4 4H22a4 4 0 0 1-4-4V28l6-10z"/><path d="M18 36h28" stroke-opacity=".5"/></svg>`,
  chocolate: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="14" y="14" width="36" height="36" rx="4"/><path d="M26 14v36M38 14v36M14 26h36M14 38h36" stroke-opacity=".45"/></svg>`,
  strawberry: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M32 20c10 0 16 7 16 15S40 54 32 54 16 43 16 35s6-15 16-15z"/><path d="M24 16h16M32 10v10" stroke-opacity=".6"/><circle cx="27" cy="32" r="1.5"/><circle cx="37" cy="34" r="1.5"/><circle cx="32" cy="42" r="1.5"/></svg>`,
  ice: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M32 8v48M12 20l40 24M52 20L12 44"/><path d="M32 18l-6-6 6-6 6 6zM32 46l-6 6 6 6 6-6z" stroke-opacity=".5"/></svg>`,
  pearls: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="22" cy="24" r="7"/><circle cx="40" cy="30" r="7"/><circle cx="26" cy="42" r="7"/><circle cx="43" cy="46" r="5"/></svg>`,
  cup: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 12h24l-3 26a4 4 0 0 1-4 3h-10a4 4 0 0 1-4-3z"/><path d="M10 50h44a2 2 0 0 1 2 2v4H8v-4a2 2 0 0 1 2-2z"/><path d="M32 41v9" stroke-opacity=".6"/></svg>`,
  hand: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M24 30V14a4 4 0 0 1 8 0v14"/><path d="M32 28V12a4 4 0 0 1 8 0v18"/><path d="M40 30V18a4 4 0 0 1 8 0v22c0 9-6 16-15 16s-15-6-15-14V26a4 4 0 0 1 8 0"/></svg>`,
  check: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="32" cy="32" r="24" stroke-opacity=".35"/><path d="M20 33l9 9 16-18"/></svg>`,
  alert: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M32 10l24 42H8z"/><path d="M32 26v12M32 45v.5"/></svg>`,
  drop: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M32 6v18" stroke-opacity=".5"/><path d="M32 24s12 14 12 22a12 12 0 0 1-24 0c0-8 12-22 12-22z"/></svg>`,
  /* ---- glassware, for the choose-a-glass step ---- */
  g_highball: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 8h22l-2 46a3 3 0 0 1-3 3H26a3 3 0 0 1-3-3z"/><path d="M22 22h20" stroke-opacity=".4"/></svg>`,
  g_rocks: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M17 20h30l-3 32a4 4 0 0 1-4 4H24a4 4 0 0 1-4-4z"/><path d="M19 34h26" stroke-opacity=".4"/></svg>`,
  g_hurricane: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 8h24c0 12-4 14-4 22s4 12-2 16H26c-6-4-2-8-2-16S20 20 20 8z"/><path d="M30 46v8M22 58h20" /></svg>`,
  g_martini: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10 12h44L32 36z"/><path d="M32 36v18M20 56h24"/></svg>`,
  g_coupe: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M13 14h38c0 12-8 20-19 20S13 26 13 14z"/><path d="M32 34v20M21 56h22"/></svg>`,
  g_mug: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 16h30v34a6 6 0 0 1-6 6H20a6 6 0 0 1-6-6z"/><path d="M44 24h6a7 7 0 0 1 0 14h-6"/><path d="M20 26h18" stroke-opacity=".4"/></svg>`,
  /* ---- ice, for the drink_type fact. One drawing per ice code, because
         "cube" and "nugget" are two different things a person fetches from
         two different machines -- a single generic snowflake would make the
         fact worth no more than the word next to it. ---- */
  i_cube: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="10" y="18" width="24" height="24" rx="4"/><rect x="28" y="28" width="24" height="24" rx="4"/><path d="M16 24h12M34 34h12" stroke-opacity=".4"/></svg>`,
  i_nugget: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="12" y="16" width="15" height="12" rx="6"/><rect x="32" y="22" width="15" height="12" rx="6"/><rect x="18" y="34" width="15" height="12" rx="6"/><rect x="36" y="40" width="13" height="11" rx="5.5"/></svg>`,
  i_crushed: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 20l7 5-7 5M28 14l7 5-7 5M42 22l7 5-7 5M18 36l7 5-7 5M32 32l7 5-7 5M40 44l7 5-7 5"/></svg>`,
  i_blend: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8h26l-4 30H22z"/><path d="M16 8h30" stroke-width="3"/><path d="M44 14h5a5 5 0 0 1 0 10h-4"/><path d="M22 38h18v8a6 6 0 0 1-6 6h-6a6 6 0 0 1-6-6z"/><path d="M25 18l12 12M37 18L25 30" stroke-opacity=".55"/></svg>`,
  i_none: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="14" y="18" width="24" height="24" rx="4" stroke-opacity=".45"/><path d="M12 52L52 12"/></svg>`,
  i_hot: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M24 34c0-6 6-8 6-14 0-4-2-6-2-6M36 34c0-6 6-8 6-14 0-4-2-6-2-6" stroke-opacity=".6"/><path d="M14 42h30v6a10 10 0 0 1-10 10H24a10 10 0 0 1-10-10z"/><path d="M44 46h5a6 6 0 0 1 0 12h-5"/></svg>`,
  /* ---- prep-fact chips ---- */
  garnish: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M32 56c0-16 8-28 22-32-2 16-10 26-22 32z"/><path d="M32 56C22 46 14 36 10 24c14 4 20 16 22 32z" stroke-opacity=".55"/><path d="M32 56v-10" stroke-opacity=".4"/></svg>`,
  qr: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="10" y="10" width="16" height="16" rx="2"/><rect x="38" y="10" width="16" height="16" rx="2"/><rect x="10" y="38" width="16" height="16" rx="2"/><path d="M38 38h6v6h-6zM48 38h6M38 48h6v6M50 48v6" stroke-opacity=".7"/></svg>`,
};

const ICON_BY_INGREDIENT = {
  1: ICON.water, 2: ICON.tea, 3: ICON.coffee, 4: ICON.syrup,
  5: ICON.syrup, 6: ICON.soda, 7: ICON.sugar, 8: ICON.milk,
  10: ICON.chocolate, 11: ICON.strawberry, 12: ICON.ice, 13: ICON.pearls,
};

const iconFor = item => {
  if (!item) return ICON.drop;
  return configuredIcon(Number(item.ingredient_id))
    || ICON_BY_INGREDIENT[Number(item.ingredient_id)]
    || ICON.drop;
};

/* ================================================================= DOM ==== */

const el = id => document.getElementById(id);
const ui = {
  drinkName: el("drinkName"), orderId: el("orderId"),
  progressBar: el("progressBar"), progressLabel: el("progressLabel"),
  conn: el("conn"), connLabel: el("connLabel"), langBtn: el("langBtn"),

  nowCard: el("nowCard"), stepChip: el("stepChip"), typeChip: el("typeChip"),
  etaChip: el("etaChip"), guideArt: el("guideArt"), guideCaption: el("guideCaption"),
  drinkPhoto: el("drinkPhoto"),
  nowEyebrow: el("nowEyebrow"), nowAction: el("nowAction"),
  nowDetail: el("nowDetail"), errorLine: el("errorLine"), pourList: el("pourList"),

  glassGate: el("glassGate"),
  glassArt: el("glassArt"),
  glassFacts: el("glassFacts"),
  glassBadge: el("glassBadge"), glassTitle: el("glassTitle"),
  glassDetail: el("glassDetail"),
  glassConfirm: el("glassConfirm"), glassConfirmLabel: el("glassConfirmLabel"),
  glassMethod: el("glassMethod"), glassMethodName: el("glassMethodName"),
  glassMethodDetail: el("glassMethodDetail"),

  railTitle: el("railTitle"), railNote: el("railNote"), railList: el("railList"),
  machineTitle: el("machineTitle"), pumpNote: el("pumpNote"),
  processVisual: el("processVisual"), processCaption: el("processCaption"),

  gate: el("gate"), gateBadge: el("gateBadge"), gateArt: el("gateArt"),
  gateMedia: el("gateMedia"),
  gateStep: el("gateStep"), gateTitle: el("gateTitle"), gateDetail: el("gateDetail"),
  thanks: el("thanks"), thanksBadge: el("thanksBadge"),
  thanksTitle: el("thanksTitle"), thanksDetail: el("thanksDetail"),
  thanksArt: el("thanksArt"), thanksCount: el("thanksCount"),
  cancelBtn: el("cancelBtn"), cancelGate: el("cancelGate"),
  cancelReasons: el("cancelReasons"), cancelNote: el("cancelNote"),
  cancelConfirm: el("cancelConfirm"), cancelBack: el("cancelBack"),
  cancelTitle: el("cancelTitle"), cancelDetail: el("cancelDetail"),
  nowCopy: document.querySelector(".now-copy"),
  gateChecks: el("gateChecks"), gateConfirm: el("gateConfirm"),
  gateConfirmLabel: el("gateConfirmLabel"),
  gateHardware: el("gateHardware"), gateWaitLabel: el("gateWaitLabel"),
  gateButtons: el("gateButtons"), hwSimNote: el("hwSimNote"),

  noteBar: el("noteBar"), noteText: el("noteText"), noteLabel: el("noteLabel"),
  statToday: el("statToday"),
  statAvg: el("statAvg"), statLast: el("statLast"),
  statMode: el("statMode"), statClock: el("statClock"),
  lblToday: el("lblToday"),
  lblAvg: el("lblAvg"), lblLast: el("lblLast"),
  lblMode: el("lblMode"), lblClock: el("lblClock"),
  doneActions: el("doneActions"), nextOrderBtn: el("nextOrderBtn"),
  nextOrderLabel: el("nextOrderLabel"), doneHint: el("doneHint"),
  simbar: el("simbar"), simPanel: el("simPanel"), simToggle: el("simToggle"),
  simDrink: el("simDrink"), simSpeed: el("simSpeed"),
  simStart: el("simStart"), simFail: el("simFail"),
  simDrinkLabel: el("simDrinkLabel"), simSpeedLabel: el("simSpeedLabel"),
};

/* ============================================== PROCESS FILE ADAPTER ====
   order/current_recipe.json uses its own vocabulary (pending / waiting / running /
   done / failed, and step ids like "3a"). Translate it once here so the
   renderer below stays unchanged.
   ======================================================================== */

/** Per-step status, mapped to what the renderer understands. */
function mapStepStatus(step) {
  const status = String(step.status || "pending");
  const type = String(step.type || "pump");

  if (status === "done") return "completed";
  if (status === "failed") return "waiting_retry";
  if (status === "pending") return "pending";

  // waiting / running
  if (type === "pump") return status === "running" ? "processing" : "pending";

  /* manual + detect become gates, inferred from the step's shape.

     A `sensor` block is what makes the machine the one watching. A
     cup-back step no longer carries one -- see build_detect_step() in
     database/export_data.py -- so it lands on the last line here and is
     released by a press, exactly like a manual step. It used to be keyed
     off `type === "detect"` instead, which made the load cell the only
     way past: when the cell read low the step could not be answered at
     all, and the drink had to be cancelled.

     The branch stays for a recipe that does carry a sensor block: an
     order already in flight when this shipped, and the simulator. */
  if (step.sensor) return "waiting_sensor";
  return (step.buttons || []).length ? "waiting_button" : "waiting_confirm";
}

/* Pumps have no status of their own any more — a step's status governs all
   of its pumps. "waiting" means shown but held; "running" means pour. */
function pumpStatusFromStep(step) {
  const status = String(step.status || "pending");
  if (status === "done") return "completed";
  if (status === "failed") return "waiting_retry";
  if (status === "running") return "processing";
  return "pending";
}

/** True when the document is the machine/GUI bridge file. */
const isProcessDoc = doc =>
  Boolean(doc) && String(doc.schema || "").startsWith("flexmix.process/");

/**
 * Is this document an order at all?
 *
 * order/run_flow.py empties current_recipe.json to `{}` when a drink ends,
 * deliberately: clear_order_files() says it stays valid JSON "so the
 * screens read it as 'no order' instead of erroring on a missing file".
 *
 * This screen did not read it that way. `{}` is a truthy object, so it
 * became the current recipe; currentStep() then found no OPEN step and
 * renderNow() takes "no open step" to mean the drink is finished. The
 * result was a full "Đồ uống đã xong" card -- with no drink name, an empty
 * process list and "Bước 0 / 0" -- sitting on the screen announcing the
 * completion of nothing, for as long as the machine sat idle.
 *
 * The test is the steps, not the order_id: a genuinely finished drink has
 * all of its steps with none of them open, and that state must keep
 * rendering as done. A drink with no steps has never existed.
 */
const isAnOrder = doc =>
  Boolean(doc)
  && typeof doc === "object"
  && Array.isArray(doc.steps)
  && doc.steps.length > 0;

function adaptProcess(doc) {
  const steps = (doc.steps || [])
    .slice()
    .sort((a, b) => Number(a.order) - Number(b.order))
    .map(step => {
      const common = {
        awaiting: String(step.status) === "waiting",
        // The file said "running" for this step specifically. Kept raw
        // because the mapping below collapses waiting/running for gates.
        active: String(step.status) === "running",
        step_number: Number(step.order),
        step_label: String(step.step),
        step_type: step.type === "pump" ? "pump" : "manual",
        status: mapStepStatus(step),
        error: step.error || null,
        started_at: step.started_at || null,
        completed_at: step.completed_at || null,
        owner: step.owner || "machine",   // absent => machine
      };

      if (step.type === "pump") {
        return Object.assign(common, {
          pump_step: (step.pumps || []).map(p => ({
            pump: p.pump,
            ingredient_id: p.ingredient_id,
            ingredient_name: p.ingredient_name,
            // Carried for display only. Every meter on this screen is
            // driven by duration_sec, the seconds the machine itself
            // computed, so the bar and the pump share one clock.
            gram: Number(p.gram) || 0,
            duration_sec: p.duration_sec,
            enabled: true,
            status: pumpStatusFromStep(step),
            error: null,
          })),
          panel_ids: (step.pumps || []).map(p => p.pump),
        });
      }

      // manual + detect render through the gate overlay
      const gate = {
        // Keyed off the sensor block, not the type -- see mapStepStatus.
        release: step.sensor
          ? "sensor"
          : ((step.buttons || []).length ? "hardware" : "confirm"),
        icon: step.icon || (step.type === "detect" ? "cup" : "hand"),
        title: step.title,
        detail: step.detail,
        confirm: step.confirm,
        sensor: step.sensor || null,
        // An action step carries a clip. Its release stays "confirm"
        // above -- it has no buttons and no sensor, so the shape already
        // says one on-screen press ends it, exactly as PROCESS_SCHEMA.md
        // describes. media only changes what the card looks like.
        media: step.media || null,
        checks: Array.isArray(step.checks) ? step.checks : null,
        // a hardware button is pressed on the panel, never on screen
        buttons: (step.buttons || []).map(b => ({
          panel: b.panel,
          label: b.label,
          lit: Boolean(b.lit),
        })),
      };

      return Object.assign(common, {
        gate,
        pump_step: [],
        panel_ids: (step.buttons || []).map(b => b.panel),
      });
    });

  // No order-level status here on purpose: it is derivable from the steps
  // (current = first step still open, finished = none open), and a second
  // copy could contradict them.
  return {
    order_id: doc.order_id,
    name: doc.drink_name,
    image: doc.image,
    // {id, name, art} from the drink table, or null when none is set.
    // Same rule as cancelled_at below: this function returns a fixed
    // shape, so a field not named here is silently dropped.
    glass: doc.glass || null,
    // {id, code, name, art, method, detail} from drink_type -- the
    // ice the drink is built on and the way it is assembled. Reference
    // data for the person, exactly like glass: nothing in process_runner
    // reads it, and a drink with none set simply shows one fact fewer.
    drink_type: doc.drink_type || null,
    // Per-drink garnish, overriding nothing: it is the one prep fact that
    // is genuinely about THIS drink rather than about its build method.
    garnish: doc.garnish || null,
    error: doc.error || null,
    // Stamped by order/run_flow.py when somebody cancels. It has to be
    // carried through explicitly: this function returns a fixed shape, so
    // a field not named here is dropped and whatever reads it downstream
    // silently sees undefined rather than failing.
    cancelled_at: doc.cancelled_at || null,
    // Stamped by order/process_runner.py when panel button 14 asks for a
    // restart, a second before the machine goes down. Same rule as
    // cancelled_at: named here or dropped.
    restarting_at: doc.restarting_at || null,
    // What the customer typed in Special Notes. Same rule as
    // cancelled_at: named here or dropped.
    note: doc.note || "",
    options: doc.options || {},
    created_at: doc.created_at,
    updated_at: doc.updated_at,
    completed_at: doc.completed_at || null,
    steps,
  };
}

/* ================================================== RECIPE INTERPRETATION == */

/**
 * The step the screen is showing.
 *
 * A step marked `running` in the file IS the current one, even if an earlier
 * step was left open — the file is the authority on what the machine is
 * doing. Only when nothing is running do we fall back to the earliest step
 * that has not finished.
 */
function currentStep(recipe) {
  if (!recipe || !Array.isArray(recipe.steps)) return null;

  const open = recipe.steps
    .filter(s => s && OPEN.has(String(s.status)))
    .sort((a, b) => Number(a.step_number) - Number(b.step_number));

  if (!open.length) return null;
  return open.find(s => s.active) || open[0];
}

const isGate = step =>
  Boolean(step) && String(step.step_type) !== "pump";

const needsConfirm = step =>
  Boolean(step) && String(step.status) === "waiting_confirm";

/** Waiting for a physical button on the machine — no on-screen action. */
const needsButton = step =>
  Boolean(step) && String(step.status) === "waiting_button";

/** The machine is watching a sensor; the operator just places the cup. */
const needsSensor = step =>
  Boolean(step) && String(step.status) === "waiting_sensor";

/** This step has finished and is being held on screen for a beat. */
const isSettling = step =>
  Boolean(step) && String(step.status) === "settling";

const hasFailed = step =>
  Boolean(step) && String(step.status) === "waiting_retry";

/* A running step may carry no `started_at` yet. Remember when we first saw
   it running so the bars still have a clock. Dropped as soon as the step
   stops running, so re-running it restarts the fill. */
const firstSeenRunning = new Map();

/* Sub-second slack for fetch latency and ordinary clock jitter. Anything
   further into the future than this means the machine's clock and the
   browser's disagree, and the machine's timestamps cannot be compared
   against Date.now() at all. */
const CLOCK_SKEW_TOLERANCE_MS = 250;

/* The machine stamps started_at at the instant it starts a step, and this
   screen polls several times a second, so a step first seen running should
   carry a stamp only milliseconds old. A stamp already seconds old means
   the two clocks disagree --- trusting it would start the meter part way
   along, or straight at 100%. Wide enough to cover the poll interval, the
   machine's own write and the fetch; narrow enough that real skew is
   caught rather than believed. */
const FRESH_START_TOLERANCE_MS = 1500;

function stepStartMs(step) {
  // Keyed by the machine's own start stamp as well as the step, so a new
  // run of the same step number can never reuse the previous run's clock.
  // Keying on the number alone let a stale entry survive --- the cache is
  // read before the freshness checks below, so one left over from an
  // earlier order pinned the meter at 100% for that step forever.
  const key = `${step.step_number}:${step.started_at || ""}`;

  if (String(step.status) !== "processing") {
    firstSeenRunning.delete(key);
    return NaN;
  }

  // Decided once, on first sight of the step running, and reused for the
  // rest of it. Re-deciding every frame would swap clocks mid-pour --- a
  // future-dated stamp stops being future-dated as the browser catches
  // up, and the meter would jump back to zero at that moment.
  if (firstSeenRunning.has(key)) return firstSeenRunning.get(key);

  // Prefer the machine's own timestamp: it is the same instant the pump
  // started. Take it only while it is fresh in both directions --- a
  // stamp in the future, or already seconds old, means the clocks
  // disagree. Falling through to the browser's own reading of when the
  // step appeared measures the pour correctly however far they drift,
  // because the step is seen within one poll of the machine starting it.
  const stamped = Date.parse(step.started_at);
  const age = Date.now() - stamped;
  const usable = (
    Number.isFinite(stamped)
    && age > -CLOCK_SKEW_TOLERANCE_MS
    && age < FRESH_START_TOLERANCE_MS
  );

  // Only one step is ever being clocked, so anything still held is from a
  // step already finished. Dropping it keeps the map from growing by one
  // entry per step per order for as long as the screen stays open.
  firstSeenRunning.clear();

  const start = usable ? stamped : Date.now();
  firstSeenRunning.set(key, start);
  return start;
}

/**
 * How far along one pump is, 0..1.
 *
 * The bridge carries `duration_sec` — the seconds the MACHINE computed from
 * that pump's own calibration — so the bar runs on exactly the same clock
 * the pump does. Pumps differ by ~18% in flow rate, so anything derived
 * from a shared rate here would drift.
 */
function pourProgress(item, step) {
  if (String(item.status) === "completed") return 1;
  if (String(item.status) !== "processing") return 0;

  const duration = Number(item.duration_sec);
  if (!Number.isFinite(duration) || duration <= 0) return 0;

  const started = stepStartMs(step);
  if (!Number.isFinite(started)) return 0;

  // Clamped at both ends. Math.min alone let a start timestamp that was
  // still in the future produce a negative percentage on screen.
  const progress = ((Date.now() - started) / 1000) / duration;
  return Math.max(0, Math.min(1, progress));
}

/** Seconds elapsed on this pump, capped at its duration. */
const elapsedSec = (item, step) =>
  (Number(item.duration_sec) || 0) * pourProgress(item, step);

/** Seconds until every pump in this step is finished. */
function stepEta(step) {
  if (!step || String(step.step_type) !== "pump") return 0;

  const started = stepStartMs(step);
  const elapsed = Number.isFinite(started) ? (Date.now() - started) / 1000 : 0;

  // Pumps run in parallel at different rates, so the step ends with the
  // slowest one.
  const worst = (step.pump_step || []).reduce((max, p) => {
    if (String(p.status) === "completed") return max;
    const duration = Number(p.duration_sec) || 0;
    return Math.max(max, duration - elapsed);
  }, 0);

  return Math.max(0, Math.ceil(worst));
}

/* ============================================================= RENDERING == */

let connection = "connecting";
let latestRecipe = null;

let connClass = "";

function setConnection(state) {
  connection = state;
  const map0 = { live: "is-live", sim: "is-sim", down: "is-down", stale: "is-stale" };
  const next = `conn ${map0[state] || ""}`.trim();
  if (connClass !== next) {
    connClass = next;
    ui.conn.className = next;
  }
  setText(ui.connLabel, t(state === "connecting" ? "connecting" : state));
}

let artKeys = new WeakMap();

/* Where hand-drawn step art lives, and the extensions tried for it.
   See bartender_gui/images/guide/README.md. */
const ART_DIR = "images/guide/";
const ART_EXTENSIONS = ["png", "jpg", "jpeg", "webp"];

/* What a key resolved to last time: a URL, or null for "nothing on disk".
   Without this every render re-probes the network for art that is not
   there, and the poll runs eight times a second. */
const artResolved = new Map();

/**
 * Filenames to try for one key, most specific first.
 *
 *   ingredient-11--hurricane.png   art drawn for this glass
 *   ingredient-11.png              art for any glass
 *   (neither)                      the built-in SVG icon
 *
 * The glass-specific level is the whole point of asking which glass was
 * picked: a drawing of a hand dropping a strawberry into a hurricane glass
 * is wrong on a rocks glass, and only the screen knows which is standing
 * there.
 */
function artCandidates(imageKey) {
  if (imageKey == null) return [];

  const base = artFileKey(imageKey);
  const stems = [];

  // The glass-specific variant, but never for the glass's OWN picture:
  // "glass-martini--martini" asks for a martini glass drawn for a martini
  // glass, which is the same file under a longer name. It cost four 404s
  // on every order and could never have been anything but a miss.
  if (chosenGlass && !/^(?:glass|ice)-/.test(base)) {
    stems.push(`${base}--${chosenGlass}`);
  }

  stems.push(base);

  const urls = [];
  for (const stem of stems) {
    for (const extension of ART_EXTENSIONS) {
      urls.push(`${ART_DIR}${stem}.${extension}`);
    }
  }
  return urls;
}

/**
 * The filename stem for a key, so callers can keep passing what they have.
 *
 * setArt() is called with an ingredient_id (a number) for a pour, a gate
 * icon name for a manual step, and "glass-<id>" for the picker. Prefixing
 * happens here rather than at the three call sites: the folder needs names
 * that cannot collide -- ingredient 12 and a gate called "12" would be the
 * same file otherwise -- and one place to change beats three.
 */
function artFileKey(imageKey) {
  const text = String(imageKey);
  if (/^glass-/.test(text)) return text;
  // "ice-cube", "ice-blend": already namespaced, and drawn the same in
  // every glass, so it passes through like a glass does.
  if (/^ice-/.test(text)) return text;
  if (/^\d+$/.test(text)) return `ingredient-${text}`;
  return `gate-${text}`;
}

/** First URL in the list that actually loads, or null. Answered once per key. */
function resolveArt(imageKey, onFound) {
  // An explicit entry in GUIDE_IMAGES wins: it is how a path outside the
  // convention gets used.
  const declared = imageKey == null ? null : GUIDE_IMAGES[imageKey];
  if (declared) { onFound(declared); return; }

  const cacheKey = `${imageKey}|${chosenGlass || ""}`;
  if (artResolved.has(cacheKey)) {
    const known = artResolved.get(cacheKey);
    if (known) onFound(known);
    return;
  }

  const urls = artCandidates(imageKey);

  const tryNext = index => {
    if (index >= urls.length) {
      artResolved.set(cacheKey, null);   // nothing drawn yet: keep the icon
      return;
    }
    const probe = new Image();
    probe.addEventListener("load", () => {
      artResolved.set(cacheKey, urls[index]);
      onFound(urls[index]);
    });
    probe.addEventListener("error", () => tryNext(index + 1));
    probe.src = urls[index];
  };

  tryNext(0);
}

function setArt(target, iconHtml, imageKey, live) {
  // Replacing innerHTML restarts the halo animation, so only do it when the
  // artwork actually changed. The chosen glass is in the key because it
  // changes which file the same step resolves to.
  const key = `${imageKey}|${chosenGlass}|${iconHtml.length}|${iconHtml.slice(0, 40)}`;
  if (artKeys.get(target) !== key) {
    artKeys.set(target, key);
    target.innerHTML = iconHtml;

    resolveArt(imageKey, src => {
      // The step may have moved on while the image was loading; dropping it
      // in then would show the previous step's picture.
      if (artKeys.get(target) !== key) return;
      const img = new Image();
      img.alt = "";
      img.addEventListener("load", () => {
        if (artKeys.get(target) !== key) return;
        target.innerHTML = "";
        target.appendChild(img);
      });
      img.src = src;
    });
  }

  target.classList.toggle("is-live", Boolean(live));
}

/**
 * Resolve the drink photo.
 * The simulator already stores a page-relative path; menu.json stores
 * "recipe/image/X.webp" relative to the project root, which from gui/html/
 * needs "../" in front.
 */
function drinkImageUrl(recipe) {
  const raw = recipe && recipe.image;
  if (!raw || typeof raw !== "string") return null;
  if (/^(?:https?:|\/|\.\.\/)/.test(raw)) return raw;
  return `../${raw}`;
}

let currentPhotoSrc = null;

/** Show the drink photo on the left; fall back to the pastel state icon. */
function setDrinkPhoto(recipe) {
  const src = drinkImageUrl(recipe);

  if (!src) {
    if (currentPhotoSrc !== null) {
      currentPhotoSrc = null;
      setHidden(ui.drinkPhoto, true);
      ui.drinkPhoto.removeAttribute("src");
    }
    setHidden(ui.guideArt, false);
    return;
  }

  if (src === currentPhotoSrc) return; // don't reload on every poll
  currentPhotoSrc = src;

  const probe = new Image();
  probe.addEventListener("load", () => {
    if (currentPhotoSrc !== src) return; // a newer drink won the race
    ui.drinkPhoto.src = src;
    setHidden(ui.drinkPhoto, false);
    setHidden(ui.guideArt, true);
  });
  probe.addEventListener("error", () => {
    if (currentPhotoSrc !== src) return;
    setHidden(ui.drinkPhoto, true);
    setHidden(ui.guideArt, false);
  });
  probe.src = src;
}

/** Write text only when it changed — avoids needless layout work. */
const setText = (node, text) => {
  if (node && node.textContent !== text) node.textContent = text;
};

/* Assigning .hidden / .className / style on every 120 ms tick generated
   ~150 DOM mutations a second even when nothing changed. Guard them. */
const setHidden = (node, value) => {
  const next = Boolean(value);
  if (node && node.hidden !== next) node.hidden = next;
};
const setWidth = (node, width) => {
  if (node && node.style.width !== width) node.style.width = width;
};
const setData = (node, key, value) => {
  if (node && node.dataset[key] !== value) node.dataset[key] = value;
};

const gram = v => {
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  return Number.isInteger(n) ? String(n) : n.toFixed(1);
};

const escapeHtml = value =>
  String(value).replace(/[&<>"']/g, ch =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[ch]);

/* ---- the main card ---- */

/* The step the card was last drawn for, so the swap animation plays on a
   real change and not on every poll. */
let shownStepKey = null;

/* Restart a CSS animation on an element. Removing the class is not enough
   on its own -- the browser coalesces the remove and the add into one
   frame and nothing replays -- so the layout is read in between to force
   the change to be committed. */
function replayAnimation(element, className) {
  if (!element) return;
  element.classList.remove(className);
  void element.offsetWidth;
  element.classList.add(className);
}

/** Mark a step change so the card visibly turns over. */
function markStepChange(recipe, step) {
  const key = recipe && step
    ? `${recipe.order_id || ""}:${step.step_number}:${step.status}`
    : null;

  if (key === shownStepKey) return;

  const firstDraw = shownStepKey === null;
  shownStepKey = key;

  // The page entrance already animates the whole card on load; playing the
  // swap on top of it would be two animations fighting over the same box.
  if (firstDraw || !key) return;

  replayAnimation(ui.nowCopy, "is-changing");
  replayAnimation(ui.stepChip, "is-changing");
  replayAnimation(ui.pourList, "is-changing");
}

function renderNow(recipe) {
  const step = currentStep(recipe);
  markStepChange(recipe, step);
  setDrinkPhoto(recipe);

  if (!recipe) {
    // No error screen here any more.
    //
    // There used to be one: a full-width "Mất kết nối với máy" with a
    // warning triangle and the name of a JSON file. It was shown to
    // whoever was standing at the machine -- a customer, who can do
    // nothing about a missing file and should not be reading its path.
    // Worse, it was a dead end: the screen sat on it, so a fault looked
    // like a machine that had simply stopped responding for ever.
    //
    // A lost connection IS an ended order. checkDropped() hands the
    // browser back to the store screen, where run_flow has left one
    // message saying what happened and what to do. Until it does, this
    // shows the same calm "waiting for an order" state it shows between
    // customers. sourceProblem is still set for the console, so a
    // malformed recipe is still diagnosable -- just not on the customer's
    // screen.
    setData(ui.nowCard, "mode", "idle");
    setText(ui.stepChip, "—");
    setText(ui.typeChip, t("connecting"));
    setHidden(ui.etaChip, true);
    setText(ui.nowEyebrow, t("eyebrowWait"));
    setText(ui.nowAction, t("noOrder"));
    setText(ui.nowDetail, t("noOrderDetail"));
    setArt(ui.guideArt, ICON.qr, null);
    setText(ui.guideCaption, "");
    setHidden(ui.errorLine, true);
    clearPours();
    return;
  }

  const total = (recipe.steps || []).length;

  if (!step) {
    setData(ui.nowCard, "mode", "done");
    setText(ui.stepChip, t("stepOf")(total, total));
    setText(ui.typeChip, t("typeDone"));
    setHidden(ui.etaChip, true);
    setText(ui.nowEyebrow, t("eyebrowDone"));
    setText(ui.nowAction, t("doneTitle"));
    setText(ui.nowDetail, t("doneDetail"));
    setArt(ui.guideArt, ICON.check, null);
    setText(ui.guideCaption, "");
    setHidden(ui.errorLine, true);
    clearPours();
    return;
  }

  setText(ui.stepChip, t("stepOf")(Number(step.step_number), total));

  // --- failed pump: the gate overlay carries the retry button -------------
  if (hasFailed(step)) {
    setData(ui.nowCard, "mode", "retry");
    setText(ui.typeChip, t("typeRetry"));
    setHidden(ui.etaChip, true);
    setText(ui.nowEyebrow, t("eyebrowWait"));
    setText(ui.nowAction, t("retryTitle"));
    setText(ui.nowDetail, t("retryDetail"));
    setArt(ui.guideArt, ICON.alert, null, true);
    setText(ui.guideCaption, "");
    setHidden(ui.errorLine, false);
    setText(ui.errorLine, step.error || recipe.error || "");
    renderPours(step);
    return;
  }

  setHidden(ui.errorLine, true);

  // A finished step keeps rendering exactly as it was during the settle
  // hold — the heading must not change. Only the chip marks the pause.

  // --- human gate: the overlay carries the instruction --------------------
  if (isGate(step)) {
    setData(ui.nowCard, "mode", "gate");
    setText(ui.typeChip, t("typeGate"));
    setHidden(ui.etaChip, true);
    setText(ui.nowEyebrow, t("eyebrowWait"));
    const gate = step.gate || {};
    setText(ui.nowAction, localised(gate.title) || t("typeGate"));
    setText(ui.nowDetail, localised(gate.detail) || "");
    setArt(ui.guideArt, ICON[gate.icon] || ICON.hand, gate.icon, true);
    setText(ui.guideCaption, needsButton(step) ? t("waitingButtonShort") : "");
    clearPours();
    return;
  }

  // --- automatic pouring --------------------------------------------------
  // The headline names every ingredient in the step and stays fixed for the
  // whole step. Deriving it from the pumps still running would make the text
  // rewrite itself each time one finishes, which reads as a glitch.
  const items = (step.pump_step || []).filter(p => p && p.enabled !== false);
  const lead = items[0];

  setData(ui.nowCard, "mode", "running");
  setText(ui.typeChip, t("typePump"));
  setText(ui.nowEyebrow, t("eyebrowAuto"));
  setText(ui.nowAction, t("pouringNamed")(
    joinNames(items.map(ingredientName)),
  ));
  setText(ui.nowDetail, t("pouringDetail"));
  setArt(ui.guideArt, iconFor(lead), lead && lead.ingredient_id, true);
  setText(ui.guideCaption, t("handsOff"));

  // Same heading throughout; only the chip marks the end-of-step hold.
  setHidden(ui.etaChip, false);
  setText(ui.etaChip, step.awaiting ? t("waitingStep") : isSettling(step)
    ? t("settling")
    : t("remaining")(stepEta(step)));

  renderPours(step);
}

/* ---- live pour meters ---- */

let pourKey = "";

/** Clear the meters and invalidate the key so the next step rebuilds them. */
function clearPours() {
  if (pourKey === "") return;
  pourKey = "";
  ui.pourList.innerHTML = "";
}

/**
 * Build the rows only when the set of pumps changes, then patch the live
 * values. Rebuilding every tick restarted the width transition and
 * re-announced the aria-live region eight times a second.
 */
function renderPours(step) {
  const items = (step.pump_step || []).filter(p => p && p.enabled !== false);

  if (!items.length) {
    if (pourKey !== "") {
      clearPours();
      pourKey = "";
    }
    return;
  }

  // lang is part of the key: ingredient names change with the language.
  const key = `${step.step_number}:${lang}:${items.map(p => p.pump).join(",")}`;
  if (key !== pourKey) {
    pourKey = key;
    ui.pourList.innerHTML = items
      .map(p => `
        <li class="pour" data-pump="${p.pump}">
          <span class="pour-pump">${p.pump}</span>
          <div class="pour-main">
            <div class="pour-top">
              <strong>${escapeHtml(ingredientName(p))}</strong>
              <span class="pour-nums"></span>
            </div>
            <div class="pour-track"><span></span></div>
          </div>
          <span class="pour-state"></span>
        </li>`)
      .join("");
  }

  items.forEach(p => {
    const row = ui.pourList.querySelector(`[data-pump="${p.pump}"]`);
    if (!row) return;

    const status = String(p.status);
    // Pumps share the step's status, but a pump whose own duration has
    // elapsed has visibly finished — say so instead of leaving it "running"
    // while a slower pump in the same step catches up.
    const done = status === "completed" || pourProgress(p, step) >= 1;
    const retry = status === "waiting_retry";

    row.classList.toggle("is-done", done);
    row.classList.toggle("is-retry", retry);
    row.classList.toggle("is-running", status === "processing");

    setText(row.querySelector(".pour-nums"),
      t("percentDone")(Math.round(pourProgress(p, step) * 100)));
    row.querySelector(".pour-track span").style.width =
      `${(pourProgress(p, step) * 100).toFixed(1)}%`;
    setText(row.querySelector(".pour-state"),
      done ? t("stateDone")
        : retry ? t("stateRetry")
          : status === "processing" ? t("stateRunning") : t("stateWaiting"));
  });
}

/* ---- opening and closing the overlay ---- */

/* Matches the 0.42s backdrop fade of gateOut in guide.css -- the longer of
   the two, since the card leaves first. If one changes the other must: too
   short and the overlay disappears mid-animation, too long and it lingers
   as an invisible sheet over the screen. */
const GATE_CLOSE_MS = 420;

let gateCloseTimer = null;

/** Show the overlay, cancelling a close that is still playing. */
function openGate() {
  if (gateCloseTimer !== null) {
    window.clearTimeout(gateCloseTimer);
    gateCloseTimer = null;
  }
  ui.gate.classList.remove("is-closing");
  setHidden(ui.gate, false);
}

/** Fade the overlay away, then take it out of the layout. */
function closeGate() {
  if (ui.gate.hidden) return;        // already gone
  if (gateCloseTimer !== null) return;  // already on its way out

  ui.gate.classList.add("is-closing");

  gateCloseTimer = window.setTimeout(() => {
    gateCloseTimer = null;
    ui.gate.classList.remove("is-closing");
    setHidden(ui.gate, true);
  }, GATE_CLOSE_MS);
}

/* ---- holding the gate across the machine's own pause ---- */

/* How long to keep the overlay up waiting for the machine to start. Longer
   than order/process_runner.py's STEP_DELAY_SECONDS (2s) plus the weighing
   it does first, and short enough that a machine which never starts does
   not leave the screen stuck behind a dead overlay. */
const GATE_HOLD_LIMIT_MS = 12000;

let gateHeldSince = 0;

/** True while the overlay should stay up because nothing has started yet. */
function holdingGate(recipe) {
  if (!confirmBusy) { gateHeldSince = 0; return false; }

  const steps = (recipe && recipe.steps) || [];
  const running = steps.some(s => String(s.status) === "processing");

  if (running) { gateHeldSince = 0; return false; }

  const now = Date.now();
  if (!gateHeldSince) gateHeldSince = now;

  if (now - gateHeldSince > GATE_HOLD_LIMIT_MS) {
    gateHeldSince = 0;
    return false;   // give up rather than trap the operator
  }

  return true;
}

/* ---- the blocking gate overlay ---- */

let gateSignature = "";
let detectMessage = null;   // set when a reading finds no cup

/* ---- the action step's clip ----
   Files live in recipe/media/, written by admin_gui/serve.py. store_gui
   serves PROJECT_DIR, so this page reaches them one directory up. */
const MEDIA_URL_PREFIX = "../recipe/media/";

let shownMediaSrc = "";

/** Put one looping clip in the card, or take the clip away. */
function showMedia(media) {
  const src = media ? String(media.src || "") : "";

  // Rebuilt ONLY when the filename changes. paintGate runs on every poll
  // -- 120 ms -- and re-writing innerHTML would restart the clip each
  // time, so it would never play past its first frame.
  if (src !== shownMediaSrc) {
    shownMediaSrc = src;

    if (!src) {
      ui.gateMedia.innerHTML = "";
    } else {
      const url = MEDIA_URL_PREFIX + encodeURIComponent(src);

      // muted and playsinline are not optional: without both, every
      // browser refuses to autoplay and the card shows a frozen frame.
      // A GIF needs neither, and having no controls anywhere is what
      // lets the two formats behave identically.
      ui.gateMedia.innerHTML = /\.(mp4|webm)$/i.test(src)
        ? `<video src="${url}" autoplay loop muted playsinline></video>`
        : `<img src="${url}" alt="">`;
    }
  }

  setHidden(ui.gateMedia, !src);
  setHidden(ui.gateArt, Boolean(src));
}


/* ========================================================== THE GLASS ======
   Which glass a drink is served in is a property OF the drink, set once in
   the admin GUI and stored on the drink row -- not something whoever is on
   shift decides each time. Two people pouring the same cocktail into
   different glasses is the thing this exists to stop.

   So this screen does not ask. It shows the one right answer, large, and
   waits for someone to acknowledge it. The wait is the point: without it
   the instruction is a label nobody has to have read, and the machine
   starts pouring into whatever is already on the platform.

   A drink with no glass set skips the step entirely. Reference data that
   nobody has filled in yet must never be able to stop a drink being made.

   The chosen glass also picks the artwork for every later step -- see
   artCandidates() -- so the illustrations show the glass actually standing
   on the machine. */

let chosenGlass = null;         // glass `art` key, or null when none is set
let glassSeenFor = null;        // the order_id already acknowledged

const GLASS_STORE_KEY = "flexmix.glass";

/** The glass this drink is served in, or null. */
const glassOf = recipe => (recipe && recipe.glass) || null;

const glassIcon = glass =>
  ICON[`g_${(glass && glass.art) || ""}`] || ICON.glass;

/** Remember the acknowledgement so a reload mid-drink does not re-ask. */
function rememberGlassSeen(orderId, glass) {
  glassSeenFor = orderId;
  chosenGlass = (glass && glass.art) || null;
  store.set(GLASS_STORE_KEY, JSON.stringify({ order: orderId }));
  // Art resolved before the glass was known was resolved for the wrong one.
  artResolved.clear();
  artKeys = new WeakMap();
}

function restoreGlassSeen(orderId, glass) {
  const raw = store.get(GLASS_STORE_KEY);
  if (!raw) return;

  try {
    const saved = JSON.parse(raw);
    if (saved && saved.order === orderId) {
      glassSeenFor = orderId;
      chosenGlass = (glass && glass.art) || null;
    }
  } catch (error) {
    /* a corrupt entry just means showing the glass again */
  }
}

/** True while this order still needs its glass acknowledged. */
function needsGlass(recipe) {
  if (!recipe) return false;

  const orderId = recipe.order_id || null;
  const glass = glassOf(recipe);

  // No glass on this drink: nothing to instruct, so there is no step.
  if (!orderId || !glass) {
    if (!glass) chosenGlass = null;
    return false;
  }

  // hasFailed() takes a step, and "no current step" is how this file says
  // the drink is finished. Neither state has a glass left to fetch.
  const step = currentStep(recipe);
  if (!step || hasFailed(step)) return false;

  if (glassSeenFor !== orderId) {
    glassSeenFor = null;
    chosenGlass = null;
    restoreGlassSeen(orderId, glass);
  }

  // Known even before the acknowledgement, so the picture in the card
  // behind the overlay is already the right glass.
  if (chosenGlass === null) chosenGlass = glass.art || null;

  return glassSeenFor !== orderId;
}

let glassRendered = "";

/* The ice this drink is built on, and how it is assembled. Same shape rule
   as the glass: reference data on the drink row, null until somebody fills
   it in, and never allowed to stop a drink being made. */
const drinkTypeOf = recipe => (recipe && recipe.drink_type) || null;

/* `art` is the one machine key on the row: it names the drawing on disk
   (ice-<art>.png) and, when there is none, the built-in SVG. One column
   rather than two, because a second key holding the same string is a
   second thing to keep in step. A kind with no drawing of its own falls
   back to the generic ice cube. */
const iceIcon = type => ICON[`i_${(type && type.art) || ""}`] || ICON.ice;

/**
 * The prep facts, in the order the work actually happens: pick the glass,
 * fill it with the right ice, finish with the garnish.
 *
 * A fact with nothing behind it is dropped rather than shown empty. This is
 * reference data a bar fills in over months, and "TRANG TRI: --" costs a
 * line of a 600px-tall panel to tell nobody anything.
 */
function serveFacts(recipe) {
  const glass = glassOf(recipe);
  const type = drinkTypeOf(recipe);
  const facts = [];

  if (glass) {
    facts.push({
      label: t("factGlass"),
      value: localised(glass.name) || glass.art || "",
      icon: glassIcon(glass),
    });
  }

  if (type) {
    facts.push({
      label: t("factIce"),
      value: localised(type.name) || type.art || "",
      icon: iceIcon(type),
      art: type.art ? `ice-${type.art}` : null,
    });
  }

  const garnish = localised(recipe.garnish);
  if (garnish) {
    facts.push({ label: t("factGarnish"), value: garnish, icon: ICON.garnish });
  }

  return facts.filter(fact => fact.value);
}

/** One chip: icon tile, small label, the value in the reading weight. */
function factChip(fact) {
  const item = document.createElement("li");
  item.className = "fact";

  const icon = document.createElement("span");
  icon.className = "fact-icon";
  icon.setAttribute("aria-hidden", "true");
  // A drawing on disk wins over the built-in SVG, the same cascade as
  // every other illustration -- but only where the fact names one.
  if (fact.art) {
    setArt(icon, fact.icon, fact.art, false);
  } else {
    icon.innerHTML = fact.icon;
  }

  const body = document.createElement("span");
  body.className = "fact-body";

  const label = document.createElement("span");
  label.className = "fact-label";
  label.textContent = fact.label;

  const value = document.createElement("strong");
  value.className = "fact-value";
  value.textContent = fact.value;

  body.append(label, value);
  item.append(icon, body);
  return item;
}

/* ---------------------------------------------------------------------
   The gate itself. Landscape: the glass on the left is the object to go
   and fetch, everything on the right is what has to be true about it
   before the machine is allowed to pour. Two questions, side by side, so
   neither scrolls the other off the panel.
   --------------------------------------------------------------------- */
function renderGlassGate(recipe) {
  const orderId = recipe.order_id || "";
  const glass = glassOf(recipe);
  const type = drinkTypeOf(recipe);
  const signature = `${orderId}:${glass.id}:${(type && type.id) || ""}:` +
                    `${recipe.garnish || ""}:${lang}`;

  setHidden(ui.glassGate, false);

  if (signature === glassRendered) return;
  glassRendered = signature;

  setText(ui.glassBadge, t("glassStep"));
  setText(ui.glassTitle, t("glassTitle"));
  setText(ui.glassDetail, t("glassDetail"));

  // ---- left: the glass, as large as the card allows ----
  // Same cascade as every other illustration: a photograph of the real
  // glass if one has been added to images/guide/, the drawn icon if not.
  setArt(ui.glassArt, glassIcon(glass), `glass-${glass.art}`, false);

  // ---- right: how it is built, then the facts, then the action ----
  const method = type ? localised(type.method) : "";
  const detail = type ? localised(type.detail) : "";
  setHidden(ui.glassMethod, !(method || detail));
  setText(ui.glassMethodName, method);
  // The dash belongs to the pair, not to either half: with no method name
  // in front of it, a sentence opening on " -- " reads as a typo.
  setText(ui.glassMethodDetail, method && detail ? ` — ${detail}` : detail);

  ui.glassFacts.innerHTML = "";
  for (const fact of serveFacts(recipe)) {
    ui.glassFacts.appendChild(factChip(fact));
  }

  setText(ui.glassConfirmLabel, t("glassGot"));
  // Assigned, not addEventListener: this runs again on every language
  // change and every new order, and a listener added each time would fire
  // the handler once per render the drink had been re-signed.
  ui.glassConfirm.onclick = () => {
    rememberGlassSeen(orderId, glass);
    setHidden(ui.glassGate, true);
    glassRendered = "";
    render(latestRecipe);      // straight on to the machine's first gate
  };
}

function renderGate(recipe) {
  // The glass comes first. Its overlay and the machine's use the same
  // corner of the screen, and a START button under it would be pressable
  // through a step that has not been answered.
  if (needsGlass(recipe)) {
    closeGate();
    renderGlassGate(recipe);
    return;
  }

  setHidden(ui.glassGate, true);

  // The order is over and a farewell card is up. Drawing a gate under it
  // leaves a live-looking START button beside "the machine is restarting",
  // and the poll that arrives during the notice window would otherwise
  // re-open one the moment it was closed.
  if (farewellShown) {
    closeGate();
    return;
  }

  const step = currentStep(recipe);
  const showConfirm = needsConfirm(step);
  const showButton = needsButton(step);
  const showSensor = needsSensor(step);

  /* A new gate gets a fresh button.
     The press that set the spinner was answered by the step it was made
     on -- that step is gone, and holding its spinner over the next one's
     button locks the operator out of a gate the machine is waiting on.
     See confirmBusyStep for the drink this stranded. */
  if (confirmBusy
      && (showConfirm || showButton || showSensor)
      && String(step.step_label) !== confirmBusyStep) {
    setConfirmBusy(false);
  }

  /* A failed step used to raise a gate offering "Thử lại bước này". That
     button cannot work: order/process_runner.py returns False the moment a
     step throws and the process exits, so by the time this card is on
     screen there is no server left to accept the retry -- and no way to
     resume a half-poured drink even if there were.

     A fault is now announced once, on the store screen, after this screen
     hands the browser back. Keeping this card as well meant three popups
     for one problem. hasFailed() is still what ends the order; it just no
     longer draws anything here. */
  const showRetry = false;

  if (!showConfirm && !showButton && !showSensor && !showRetry) {
    // The gate's own condition has cleared -- but the machine may not have
    // started yet. It waits STEP_DELAY_SECONDS between steps, so there is a
    // gap where the step just released is 'done' and the next one is still
    // 'pending'. Dropping the overlay here was the frustrating part: the
    // button vanished the instant it was pressed and the screen sat still
    // for two seconds with nothing to show it had been heard.
    //
    // So the overlay is held, with its arrow still rising, until something
    // is genuinely running. holdingGate() also gives up after a while, so a
    // machine that never starts cannot freeze the screen behind it.
    if (holdingGate(recipe)) return;

    setConfirmBusy(false);
    closeGate();
    gateSignature = "";
    return;
  }

  // A failed step needs its retry button pressable again.
  if (showRetry) setConfirmBusy(false);

  // The LED pattern is part of the signature so the overlay re-renders the
  // moment a topping button latches on.
  const litPattern = ((step.gate || {}).buttons || [])
    .map(b => (b.lit ? "1" : "0"))
    .join("");
  const sensorNow = ((step.gate || {}).sensor || {}).current_gram;
  // step.error is in here because a refused press is the one thing that
  // changes on a gate without changing its status: the machine writes why
  // it said no and goes back to waiting. Left out, the refusal was written
  // to the file and never drawn.
  const signature =
    `${step.step_number}:${step.status}:${litPattern}:${sensorNow}:` +
    `${detectMessage}:${step.error}:${lang}`;
  openGate();
  if (signature === gateSignature) return; // don't rebuild needlessly
  gateSignature = signature;

  const total = (recipe.steps || []).length;
  setText(ui.gateStep, t("stepOf")(Number(step.step_number), total));
  ui.gateChecks.innerHTML = "";

  // Once per paint, before any branch returns: a retry card never shows a
  // clip, and every other gate gets whichever one its step names. Calling
  // it here means no branch below has to remember to clear it.
  showMedia(showRetry ? null : ((step.gate || {}).media || null));

  // --- a pump failed: offer a retry -------------------------------------
  if (showRetry) {
    setData(ui.gate, "kind", "retry");
    setText(ui.gateBadge, t("typeRetry"));
    setText(ui.gateTitle, t("retryTitle"));
    setText(ui.gateDetail, step.error || t("retryDetail"));
    setArt(ui.gateArt, ICON.alert, null, true);
    setHidden(ui.gateHardware, true);
    setHidden(ui.gateConfirm, false);
    setConfirmLabel(t("retryBtn"));
    releaseConfirm();
    return;
  }

  const gate = step.gate || {};
  setText(ui.gateBadge, t("gateBadge"));
  setText(ui.gateTitle, localised(gate.title) || t("typeGate"));
  setText(ui.gateDetail, localised(gate.detail) || "");
  setArt(ui.gateArt, ICON[gate.icon] || ICON.hand, gate.icon, true);

  // --- SENSOR GATE: the machine is watching, nothing to press -----------
  if (showSensor) {
    ui.gate.dataset.kind = "hardware";
    setHidden(ui.gateHardware, false);
    setHidden(ui.hwSimNote, true);
    ui.gateButtons.innerHTML = "";

    const sensor = gate.sensor || {};
    const now = Number(sensor.current_gram) || 0;
    const need = Number(sensor.min_gram) || 0;
    setText(ui.gateWaitLabel, detectMessage || (need
      ? t("waitingSensor")(gram(now), gram(need))
      : t("waitingSensorPlain")));

    // the operator asks the machine to take a reading
    setHidden(ui.gateConfirm, false);
    setConfirmLabel(t("checkCup"));
    releaseConfirm();
    return;
  }

  // --- HARDWARE GATE: no on-screen action, mirror the panel buttons ------
  if (showButton) {
    setData(ui.gate, "kind", "hardware");
    setHidden(ui.gateConfirm, true);
    setHidden(ui.gateHardware, false);

    const buttons = Array.isArray(gate.buttons) ? gate.buttons : [];
    const litCount = buttons.filter(b => b.lit).length;

    // Tell the operator how many are outstanding — and, once none are, that
    // the machine is now the one holding things up.
    setText(ui.gateWaitLabel,
      litCount === 0
        ? t("waitingButton")
        : litCount >= buttons.length
          ? t("allButtonsLit")
          : t("waitingButtonCount")(litCount, buttons.length));

    // `lit` is the only thing the screen writes. A physical press sets it,
    // and so does a tap here; the machine watches for all of them.
    const simMode = SIM_ENABLED && Boolean(window.FLEXMIX_SIM);
    const pressable = true;

    setHidden(ui.hwSimNote, false);
    setText(ui.hwSimNote, simMode ? t("hwSimNote") : t("hwTapNote"));

    ui.gateButtons.innerHTML = buttons
      .map(b => {
        const lit = Boolean(b.lit);
        // A latched button is never clickable again.
        const clickable = pressable && !lit;
        const tag = clickable ? "button" : "div";
        const attrs = clickable ? ' type="button"' : "";
        const cls = [
          "hw-btn",
          lit ? "is-lit" : "is-off",
          clickable ? "is-clickable" : "",
        ]
          .filter(Boolean)
          .join(" ");

        return `
          <${tag}${attrs} class="${cls}" data-panel="${Number(b.panel)}">
            <span class="hw-led" aria-hidden="true"></span>
            <span class="hw-btn-label">${escapeHtml(localised(b.label))}</span>
            <span class="hw-btn-num">${Number(b.panel)}</span>
          </${tag}>`;
      })
      .join("");
    return;
  }

  // --- CONFIRM GATE: the big on-screen button ---------------------------
  // A start gate gets its own green styling so it reads as "begin", not as
  // an interruption partway through a drink.
  const isStart = Boolean(gate.start);
  setData(ui.gate, "kind", isStart ? "start" : "confirm");
  setText(ui.gateBadge, isStart ? t("startBadge") : t("gateBadge"));
  setHidden(ui.gateHardware, true);
  setHidden(ui.gateConfirm, false);

  // --- ACTION GATE: a clip loops while the operator does the thing -----
  // Handled inside the confirm branch rather than beside it, because an
  // action step IS released by the on-screen button: the refusal message
  // below, the label and releaseConfirm() all apply unchanged. Only the
  // card's shape and what fills its left half differ.
  if (gate.media) {
    setData(ui.gate, "kind", "action");

    ui.gateChecks.innerHTML = (gate.checks || [])
      .map(check => `<li>${escapeHtml(localised(check) || "")}</li>`)
      .join("");
  }

  // The machine answered the last press by refusing it -- the start gate
  // does this when the scale was empty -- and went back to waiting on the
  // same gate. Nothing else will hand the button back: onConfirm() locks
  // it for the request and leaves it to the branch above, which only runs
  // once the gate CLEARS. So the operator watched a dead button and a
  // stale "working" label while the machine waited for a press that could
  // no longer be made. Say why, and let them press again.
  if (step.error) {
    setConfirmBusy(false);
    setText(ui.gateDetail, step.error);
  }

  setConfirmLabel(localised(gate.confirm) || t("confirm"));
  releaseConfirm();
}

/* ---- step timeline ---- */

let railKey = "";

function renderRail(recipe) {
  if (!recipe || !Array.isArray(recipe.steps)) {
    ui.railList.innerHTML = "";
    setText(ui.railNote, "—");
    return;
  }

  const step = currentStep(recipe);
  const total = recipe.steps.length;
  const done = recipe.steps.filter(s =>
    ["completed", "skipped"].includes(String(s.status))).length;
  setText(ui.railNote, `${done} / ${total}`);

  ui.railList.innerHTML = recipe.steps
    .map(s => {
      const status = String(s.status);
      const current = step && s.step_number === step.step_number;
      const gate = isGate(s);
      const cls = ["rail-item",
        current ? "is-current" : "",
        status === "completed" ? "is-done" : "",
        status === "skipped" ? "is-skipped" : "",
        status === "waiting_retry" ? "is-retry" : "",
        gate ? "is-gate" : "is-auto"].filter(Boolean).join(" ");

      const label = gate
        ? localised((s.gate || {}).title) || t("manualStep")
        : joinNames(
          (s.pump_step || [])
            .filter(p => p && p.enabled !== false)
            .map(ingredientName),
        );

      return `
        <li class="${cls}">
          <span class="rail-dot"></span>
          <span class="rail-name">${s.step_number}. ${escapeHtml(label)}</span>
          <span class="rail-meta">${gate ? t("manualStep") : t("autoStep")}</span>
        </li>`;
    })
    .join("");

  // The rail is taller than its panel on any drink of more than about four
  // steps, and nothing was scrolling it -- so on a 1366x768 machine the
  // current step sat below the fold and the one thing the list exists to
  // show was the one thing it did not. block:"nearest" only moves the list
  // when the item is actually out of view, so a short recipe never jumps.
  const currentItem = ui.railList.querySelector(".rail-item.is-current");
  if (currentItem && typeof currentItem.scrollIntoView === "function") {
    currentItem.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }
}

/* ---- live process visual ----------------------------------------------
   A small scene that describes what is physically happening: the cup fills
   as the drink progresses, streams animate while pumping, and the scene
   swaps to a hand/cup graphic at a human gate.
   ----------------------------------------------------------------------- */

/** Seconds of pouring done so far, and seconds in total. */
function drinkProgress(recipe) {
  let total = 0;
  let done = 0;

  if (recipe && Array.isArray(recipe.steps)) {
    recipe.steps.forEach(s => {
      if (String(s.step_type) !== "pump") return;
      (s.pump_step || []).forEach(p => {
        if (!p || p.enabled === false) return;
        const duration = Number(p.duration_sec) || 0;
        total += duration;
        done += String(s.status) === "completed" ? duration : elapsedSec(p, s);
      });
    });
  }

  return { done, total };
}

/** Overall fill of the cup, 0..1. */
function cupFill(recipe) {
  const { done, total } = drinkProgress(recipe);
  return total > 0 ? Math.min(1, done / total) : 0;
}

/** The cup scene. `streams` is how many nozzles are actively pouring. */
function cupScene(fill, streams, tone) {
  const top = 58;
  const bottom = 124;
  const height = (bottom - top) * Math.max(0, Math.min(1, fill));
  const y = bottom - height;

  const nozzleXs = [82, 100, 118].slice(0, Math.max(0, Math.min(3, streams)));
  const jets = nozzleXs
    .map(
      (x, i) => `
      <line class="jet" x1="${x}" y1="34" x2="${x}" y2="${y - 2}"
            style="animation-delay:${i * 0.18}s" />`,
    )
    .join("");

  const heads = [82, 100, 118]
    .map(
      x =>
        `<rect x="${x - 7}" y="22" width="14" height="10" rx="3"
               class="${nozzleXs.includes(x) ? "head is-on" : "head"}" />`,
    )
    .join("");

  return `
    <svg viewBox="0 0 200 150" class="scene" data-tone="${tone}">
      <defs>
        <clipPath id="cupClip">
          <path d="M72 58h56l-8 60c0 6-40 6-40 0z" />
        </clipPath>
      </defs>

      <rect x="60" y="14" width="80" height="10" rx="4" class="rail" />
      ${heads}
      ${jets}

      <path d="M72 58h56l-8 60c0 6-40 6-40 0z" class="cup" />
      <g clip-path="url(#cupClip)">
        <rect x="66" y="${y}" width="68" height="${height + 2}" class="liquid" />
        <ellipse cx="100" cy="${y}" rx="30" ry="3.5" class="liquid-top" />
      </g>
      <ellipse cx="100" cy="58" rx="28" ry="4" class="cup-rim" />

      <rect x="56" y="128" width="88" height="8" rx="3" class="scale" />
      <rect x="70" y="136" width="60" height="5" rx="2" class="scale-foot" />
    </svg>`;
}

/** A big single glyph, used for gates and end states. */
const glyphScene = (icon, tone) =>
  `<div class="scene-glyph" data-tone="${tone}">${icon}</div>`;

let sceneKey = "";

/** Swap the scene only when its identity changes, so animations keep running. */
function setScene(key, html) {
  if (key === sceneKey) return;
  sceneKey = key;
  ui.processVisual.innerHTML = html;
}

/** Patch the liquid level and jet length on the existing SVG. */
function paintCup(fill) {
  const svg = ui.processVisual.querySelector(".scene");
  if (!svg) return;

  const TOP = 58;
  const BOTTOM = 124;
  const height = (BOTTOM - TOP) * Math.max(0, Math.min(1, fill));
  const y = BOTTOM - height;

  const liquid = svg.querySelector(".liquid");
  if (liquid) {
    liquid.setAttribute("y", y.toFixed(2));
    liquid.setAttribute("height", (height + 2).toFixed(2));
  }
  const surface = svg.querySelector(".liquid-top");
  if (surface) surface.setAttribute("cy", y.toFixed(2));

  // jets stop at the liquid surface
  svg.querySelectorAll(".jet").forEach(jet => {
    jet.setAttribute("y2", (y - 2).toFixed(2));
  });
}

function renderProcess(recipe) {
  const step = currentStep(recipe);

  if (!recipe) {
    setScene("glyph:idle", glyphScene(ICON.qr, "idle"));
    setText(ui.processCaption, t("noOrder"));
    setText(ui.pumpNote, t("pumpIdle"));
    return;
  }

  if (!step) {
    setScene("cup:done", cupScene(1, 0, "done"));
    paintCup(1);
    setText(ui.processCaption, t("filledDone"));
    setText(ui.pumpNote, t("stateDone"));
    return;
  }

  if (hasFailed(step)) {
    setScene("glyph:retry", glyphScene(ICON.alert, "retry"));
    setText(ui.processCaption, t("retryTitle"));
    setText(ui.pumpNote, t("stateRetry"));
    return;
  }

  // At a gate the machine is idle: show what the human must do.
  if (isGate(step)) {
    const gate = step.gate || {};
    setScene(`glyph:gate:${gate.icon || "hand"}`,
      glyphScene(ICON[gate.icon] || ICON.hand, "gate"));
    setText(ui.processCaption, drinkProgress(recipe).total
      ? t("filledPercent")(Math.round(cupFill(recipe) * 100))
      : "");
    setText(ui.pumpNote, needsButton(step)
      ? t("waitingButtonShort")
      : t("stateWaiting"));
    return;
  }

  // Pouring: one jet per pump actually running.
  const active = (step.pump_step || []).filter(
    p => String(p.status) === "processing",
  );
  const fill = cupFill(recipe);
  setScene(`cup:pour:${active.length}`, cupScene(fill, active.length, "pour"));
  paintCup(fill);
  setText(ui.processCaption, t("filledPercent")(Math.round(fill * 100)));
  setText(ui.pumpNote, active.length
    ? t("pumpRunning")(active.length)
    : t("pumpIdle"));
}

/* ---- status footer ---- */

const pad2 = n => String(n).padStart(2, "0");

/** "mm:ss", or "h:mm:ss" once past an hour. */
function formatDuration(ms) {
  if (!Number.isFinite(ms) || ms < 0) return "—";
  const total = Math.floor(ms / 1000);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return h ? `${h}:${pad2(m)}:${pad2(s)}` : `${m}:${pad2(s)}`;
}

/** Local clock time from an ISO stamp, e.g. "09:15". */
function formatClock(iso) {
  const ms = Date.parse(iso);
  if (!Number.isFinite(ms)) return "—";
  const d = new Date(ms);
  return `${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
}

/* The customer's customisations. These come off the QR code and are shown
   nowhere else on the screen, unlike progress, which the card already covers. */
/* ---- shift totals, kept locally in the browser ---- */

const SHIFT_KEY = "flexmix.shift";
const countedOrders = new Set();

function todayKey() {
  const d = new Date();
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
}

function readShift() {
  try {
    const raw = JSON.parse(store.get(SHIFT_KEY) || "{}");
    if (raw.date === todayKey()) return raw;
  } catch (error) {
    /* corrupt or unavailable storage: start clean */
  }
  return { date: todayKey(), count: 0, totalMs: 0, lastMs: 0 };
}

/** Count a drink once, the first time we see it completed. */
function recordCompletion(recipe) {
  if (!recipe || !recipe.completed_at || !recipe.order_id) return;
  const id = String(recipe.order_id);
  if (countedOrders.has(id)) return;
  // bounded: a long shift must not grow this without limit
  if (countedOrders.size > 500) countedOrders.clear();
  countedOrders.add(id);

  const started = Date.parse(recipe.created_at);
  const ended = Date.parse(recipe.completed_at);
  const took = Number.isFinite(started) && Number.isFinite(ended)
    ? Math.max(0, ended - started)
    : 0;

  const shift = readShift();
  shift.count += 1;
  shift.totalMs += took;
  shift.lastMs = took;
  store.set(SHIFT_KEY, JSON.stringify(shift));
}

/* ---- cancelling an order that is already pouring ----

   Staff press "Hủy đơn", pick a reason, and the machine stops. The reason
   is the point: order/process_runner.py writes it to error_log with
   category 'cancelled', so a week later you can ask how often drinks are
   abandoned and why -- which "cancelled" on its own could never answer.

   A short list rather than a free-text box alone, because free text gets
   filled with "loi" and cannot be counted. The note carries whatever does
   not fit a category.

   The button only appears while there is something to cancel. Offering it
   on a finished or idle screen invites a press that would do nothing and
   teach staff the button is unreliable. */
const CANCEL_REASONS = [
  { id: "khach_doi_y", vi: "Khách đổi ý", en: "Customer changed their mind" },
  { id: "sai_do_uong", vi: "Sai đồ uống", en: "Wrong drink" },
  { id: "may_loi", vi: "Máy có vấn đề", en: "Machine problem" },
  { id: "do_tran", vi: "Đổ / tràn ly", en: "Spill or overflow" },
  { id: "het_nguyen_lieu", vi: "Hết nguyên liệu", en: "Out of ingredient" },
  { id: "khac", vi: "Lý do khác", en: "Other" },
];

let cancelReason = null;
let cancelSending = false;

function buildCancelReasons() {
  const box = ui.cancelReasons;
  if (!box) return;

  box.innerHTML = "";

  CANCEL_REASONS.forEach(reason => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "reason";
    button.dataset.reason = reason.id;
    button.textContent = lang === "en" ? reason.en : reason.vi;
    button.onclick = () => {
      cancelReason = reason.id;
      box.querySelectorAll(".reason").forEach(el =>
        el.classList.toggle("on", el.dataset.reason === reason.id));
      // Only now is there something worth sending.
      ui.cancelConfirm.disabled = false;
    };
    box.appendChild(button);
  });
}

/** Ask the machine to stop, and open the dialog. */
async function openCancel() {
  cancelReason = null;
  ui.cancelConfirm.disabled = true;
  ui.cancelNote.value = "";
  buildCancelReasons();
  setHidden(ui.cancelGate, false);

  // The request goes out immediately; the machine finishes the step it is
  // on and then holds. The dialog says which of those is true, because
  // "asked to stop" and "stopped" are different, and staff standing at a
  // machine that is still pouring deserve to know which they are seeing.
  try {
    await fetch("../api/pause", { method: "POST" });
  } catch (error) {
    console.warn("[pause] request failed:", error);
  }
}

/** Carry on with the next step. */
async function resumeOrder() {
  try {
    await fetch("../api/resume", { method: "POST" });
  } catch (error) {
    console.warn("[resume] request failed:", error);
  }

  setHidden(ui.cancelGate, true);
}

function closeCancel() {
  setHidden(ui.cancelGate, true);
}

/* The dialog is modal on purpose and has no dismiss. It is opened by
   asking the machine to stop, so closing it without answering would leave
   the machine held with nothing on screen explaining why. The two buttons
   ARE the exits. */
function paintCancelState(recipe) {
  if (ui.cancelGate.hidden) return;

  // Two ways the machine is already stopped, and both should read the same
  // to whoever is standing there:
  //
  //   paused_at   the runner reached the end of a step and is holding
  //   a gate      the current step is waiting for a person -- the cup, a
  //               topping, the start button -- so nothing is pouring
  //
  // Without the second, pressing "Hủy đơn" during a cup check left the
  // dialog saying "will stop after the current step" for ever, about a
  // machine that had already stopped.
  const step = currentStep(recipe);
  const held = Boolean(recipe && recipe.paused_at)
    || Boolean(step && step.step_type !== "pump");
  setText(ui.cancelTitle, t(held ? "pausedTitle" : "pausingTitle"));
  setText(ui.cancelDetail, t(held ? "pausedDetail" : "pausingDetail"));
}

async function sendCancel() {
  if (cancelSending || !cancelReason) return;

  cancelSending = true;
  ui.cancelConfirm.disabled = true;

  try {
    await fetch("../api/cancel", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        reason: cancelReason,
        note: (ui.cancelNote.value || "").trim(),
      }),
    });
  } catch (error) {
    // The runner may already be shutting down, which is the outcome we
    // wanted anyway. Nothing here should hold the screen up: what happens
    // next is decided by the recipe file, as it is for every other ending.
    console.warn("[cancel] request failed:", error);
  }

  cancelSending = false;
  closeCancel();
}

/** Show the cancel button only while a drink is actually being made. */
function updateCancelButton(recipe) {
  if (!ui.cancelBtn) return;

  const live = Boolean(recipe)
    && !recipe.completed_at
    && !recipe.cancelled_at
    && !recipe.error
    && !farewellShown;

  // Hidden while the dialog is open: the machine is already being stopped,
  // and a second press would only re-send the same request.
  setHidden(ui.cancelBtn, !live || !ui.cancelGate.hidden);

  // Only the order actually ending closes the dialog. A pause leaves the
  // recipe live, so this never fights the dialog it opened.
  if (!live) closeCancel();

  paintCancelState(recipe);
}

/* ---- thank you, then back to the store screen ---- */

const RETURN_SECONDS = 5;

/* Where to go back to. The store screen appends ?back=<its own URL> when it
   sends the browser here, because only it knows which address and port it
   was reached on -- localhost, the LAN address or Tailscale. The fallback
   is this same origin, which is right whenever one server hosts both. */
/* Where the store screen lives on this server. A path rather than a full
   URL, so it works from localhost, the LAN address or Tailscale alike --
   the same reason ?back= carries an address instead of this page assuming
   one. */
const STORE_SCREEN_PATH = "/store_gui/drinks-pos.html";

function storeScreenUrl() {
  const asked = new URLSearchParams(location.search).get("back");
  if (asked) return asked;

  // Set in bartender_gui/config as ui.store_url when this screen might be
  // opened without ?back= -- a bookmark, a kiosk start page.
  if (STORE_URL) return STORE_URL;

  // Last resort: the store screen on this same origin.
  //
  // THIS USED TO RETURN "" AND THAT IS WHY THE SCREEN COULD GET STUCK
  //     The reasoning was that location.origin is process_runner's own
  //     server, which exits with the order -- so leaving for it would land
  //     on a dead address. That was true when the store screen navigated
  //     here by rebuilding the URL around the runner's port. It no longer
  //     does: it hands off on its OWN origin and says so
  //     (store_gui/drinks-pos.js, "Same origin, deliberately"). Every
  //     screen is on one port now.
  //
  //     The old hazard has not vanished entirely -- process_runner still
  //     serves the whole project tree on its port, so a browser pointed
  //     straight at it would be on an origin that dies with the order.
  //     But that origin only exists WHILE a runner does, and
  //     goWhenReachable() probes the target before navigating and waits
  //     up to a minute for it. So the worst case is a wait, not the
  //     browser error page the old comment was avoiding.
  //
  //     What returning "" cost was worse and certain: a screen opened
  //     without ?back= -- a bookmark, a kiosk start page, somebody typing
  //     the address -- sat on "Đang chờ đơn hàng" for ever with no way
  //     out, because the one branch that could have moved it declined to
  //     guess.
  return location.origin + STORE_SCREEN_PATH;
}


/* How long the machine must stay unreachable before this screen decides the
   order is gone rather than the network being slow.

   The runner's server IS the order: it is started for one drink and exits
   when that drink ends, so it going away for good means there is nothing
   left to wait for. When it is gone, fetch fails IMMEDIATELY -- the
   connection is refused rather than timing out -- so at DOWN_POLL_MS this
   is several straight refusals, not a slow guess.

   A finished order is safe at any value: farewellShown and the completed_at
   check both settle that before this is consulted. So the only thing this
   guards against is a network gap on a tablet across the room being read as
   a failure. It is deliberately short, because the common case by far is
   the machine really having stopped and a customer waiting in front of a
   screen that will not move. Raise it in bartender_gui/config with
   ui.dropped_after_ms if a wireless screen gives false alarms. */
/* How many polls in a row must fail before this screen calls the order
   dead. Counted in POLLS, not seconds, and the poll stays fast until the
   decision is made -- so this is about a third of a second, not the two
   seconds a wall-clock plus a backed-off poll interval used to take.

   Three rather than one because a single dropped request happens. Three in
   a row, 120 ms apart, does not: the server that answers them IS the order,
   started by process_runner for this drink and gone the moment the drink
   ends, so its silence is the end of the order and not a slow network. */
let DROPPED_AFTER_POLLS = 3;

/* Where to go when this screen has nothing to show. Normally the
   store screen supplies it as ?back=, which is right for whatever
   address that screen was itself reached on. */
let STORE_URL = "";

/* An order that ends WITHOUT a drink draws no card here at all. It goes
   quietly back to the store screen, where order/run_flow.py has left one
   message carrying the same words and the machine's own reason, and where
   it stays up for twenty seconds.

   There used to be a card here as well, and a retry gate above it, so a
   single stuck pump produced three popups in a row saying the same thing.
   One announcement, in the place the customer ends up.

   Zero: the moment this screen knows the order is dead it hands over. It
   used to hold for 1.2s so the departure "felt deliberate" -- but by then
   the customer has already watched the pour finish and the screen sit
   still through a second of settling and a scale reading, and another
   pause on top reads as a machine that has hung.

   Nothing depends on the wait. The store screen's message is polled for,
   not required to be present on arrival, so landing before run_flow has
   written it simply means the popup appears a moment later.

   setTimeout(0) rather than navigating on the spot: it lets the current
   poll finish and the frame paint instead of tearing down the page from
   inside it. */
const FAULT_RETURN_DELAY_MS = 0;

/* Shown once per finished order. Keyed by order_id so a poll every second
   does not restart the countdown, and so the next drink shows it again. */
let thanksFor = null;
let thanksTimer = null;

/* Set as soon as EITHER ending has been shown. The screen is on its way to
   the store page from that moment, and a second box -- a drop noticed just
   after a completion, or the machine going quiet because it exited
   normally -- must not replace the first one under the customer's eyes. */
let farewellShown = false;

/* The last recipe that actually arrived. latestRecipe is set to null the
   moment a poll fails, which is exactly when a dropped order needs to name
   the drink it was making. */
let lastGoodRecipe = null;

/* How many polls in a row have failed. Zero while the machine answers. */
let downPolls = 0;

/* The drink's name, whichever shape the recipe is in.

   adaptProcess() renames drink_name to name, and everything that reaches
   these cards has been through it -- so reading drink_name alone got
   undefined and the thank-you rendered as " is ready. Please take your
   drink." with the name simply missing. Both spellings are accepted
   because the simulator in js/sim.js feeds the un-adapted shape. */
function drinkName(recipe) {
  if (!recipe) return "";
  return recipe.name || recipe.drink_name || "";
}

/** One ending, whichever it is: a card, a countdown, then the store screen. */
function showFarewell({ kind, badge, title, detail, icon, seconds }) {
  if (farewellShown) return;
  farewellShown = true;

  // data-kind picks the card's colour from guide.css: sage for a finished
  // drink, rose for one that stopped.
  ui.thanks.dataset.kind = kind;
  setText(ui.thanksBadge, badge);
  setText(ui.thanksTitle, title);
  setText(ui.thanksDetail, detail);
  setArt(ui.thanksArt, icon, null, true);
  setHidden(ui.thanks, false);

  let left = seconds || RETURN_SECONDS;

  const paint = () => {
    ui.thanksCount.innerHTML =
      `${escapeHtml(t("returningIn"))} <span class="num">${left}</span> ` +
      `${escapeHtml(t("seconds"))}`;
  };

  paint();
  window.clearInterval(thanksTimer);

  thanksTimer = window.setInterval(() => {
    left -= 1;

    if (left > 0) { paint(); return; }

    window.clearInterval(thanksTimer);
    thanksTimer = null;
    goWhenReachable(storeScreenUrl());
  }, 1000);
}

function showThanks(recipe) {
  showFarewell({
    kind: "start",
    badge: t("thanksBadge"),
    title: t("thanksTitle"),
    detail: t("thanksDetail")(drinkName(recipe)),
    icon: ICON.check,
  });
}

/* The machine stamps completed_at when the last step finishes. */
function maybeShowThanks(recipe) {
  if (!recipe || !recipe.completed_at || !recipe.order_id) return;
  const id = String(recipe.order_id);
  if (thanksFor === id) return;
  thanksFor = id;
  showThanks(recipe);
}

/* ---- the order was dropped ----
   Two ways an order ends without a drink, and the screen has to leave on
   both. Before this it simply sat on the half-finished order for ever,
   showing "offline" to a customer with no idea whether to keep waiting.

     1. The runner writes the failure into the recipe and exits. A step
        threw -- a pump, the panel, the load cell -- and document.error
        carries the reason. This is the one that can be described.

     2. The runner is gone without having written anything: killed, the
        flow cancelled with Ctrl+C, the Pi's I2C bus taking the process
        down with it. Nothing says why, so the screen waits for
        DROPPED_AFTER_POLLS failures in a row to be sure, then leaves.

        This is the USUAL path, not the rare one: the server the screen
        polls is process_runner's own, and process_runner exits the moment
        a step fails -- so the error it wrote is normally unreachable by
        the time this screen would read it.

   Both land on the store screen, because that is where the next person can
   actually do something. */
/** Hand the browser back to the store screen, drawing nothing on the way.

    Guarded by farewellShown like the thank-you is, so a fault noticed on
    several polls in a row schedules exactly one departure. */
function leaveForStoreScreen(why) {
  if (farewellShown) return;
  farewellShown = true;

  const target = storeScreenUrl();

  if (!target) {
    // Nothing to go back to, so stay put rather than navigate nowhere.
    // The screen falls back to its idle state, which is at least honest.
    console.warn("[flow] " + why + ", but no store screen to return to. "
      + "Open this page from the store screen, or set ui.store_url.");
    farewellShown = false;      // let a later order decide again
    return;
  }

  console.log("[flow] " + why + " -> " + target);
  window.setTimeout(() => {
    goWhenReachable(target);
  }, FAULT_RETURN_DELAY_MS);
}

/* How often to knock on the store screen's door, and how long to keep
   knocking before going anyway. The service takes RestartSec=3 plus a
   second or two to bind its port, so the limit is many times over what a
   restart needs -- it exists for a ?back= URL that is simply wrong, where
   landing on the browser's error page at least shows what is wrong. */
const STORE_PROBE_MS = 500;
const STORE_WAIT_LIMIT_MS = 60000;

/** Is anything answering at the store screen's address? */
async function storeScreenIsUp(target) {
  // no-cors because the store screen is a different origin (its own port)
  // and its server sends no CORS headers. The response is opaque and its
  // status unreadable, which does not matter: this only has to tell a
  // refused connection from an answered one, and fetch rejects on the
  // former and resolves on the latter.
  const probe = target + (target.includes("?") ? "&" : "?") + "up=" + Date.now();

  try {
    await fetch(probe, { mode: "no-cors", cache: "no-store" });
    return true;
  } catch (error) {
    return false;
  }
}

/**
 * Leave for the store screen, but not before it can answer.
 *
 * The screen used to navigate on a timer. That is fine when the runner
 * alone has died, but panel button 14 restarts the whole service -- the
 * store screen's server with it -- so the browser arrived at an address
 * that was still down and landed on "site can't be reached". A browser
 * error page runs no script, so nothing was left to try again and the
 * screen was stuck there until somebody typed a URL.
 *
 * Waiting costs nothing: this page is already loaded, so it keeps running
 * even though the server it came from is gone.
 */
async function goWhenReachable(target) {
  const deadline = Date.now() + STORE_WAIT_LIMIT_MS;

  while (!(await storeScreenIsUp(target))) {
    if (Date.now() >= deadline) {
      console.warn("[flow] store screen still unreachable after "
        + (STORE_WAIT_LIMIT_MS / 1000) + "s; going anyway: " + target);
      break;
    }

    await wait(STORE_PROBE_MS);
  }

  window.location.href = target;
}

function showDropped(recipe, lost) {
  leaveForStoreScreen(lost ? "lost contact with the machine" : "order failed");
}

/* Somebody cancelled the order -- Ctrl+C on order/run_flow.py, which stamps
   cancelled_at into the recipe and waits ~0.7s before killing the runner
   precisely so this can be seen. Kept apart from a failure because it IS
   apart: nothing is broken, nobody needs to be fetched, and telling a
   customer the machine has a fault when a member of staff simply stopped
   the order sends them to complain about the wrong thing. */
function showCancelled(recipe) {
  // Same treatment: run_flow leaves "Đơn đã bị hủy" on the store screen.
  leaveForStoreScreen("order cancelled");
}

/* Panel button 14 asked for a restart. The machine stamped restarting_at
   and kept serving for a moment so this could be read -- see
   RESTART_NOTICE_SECONDS in order/process_runner.py.

   Worth its own card rather than falling through to "lost contact": that
   one tells a customer something went wrong, and nothing has. The machine
   was asked to restart and is coming back. */
function showRestarting() {
  showFarewell({
    kind: "start",
    badge: t("restartBadge"),
    title: t("restartTitle"),
    detail: t("restartDetail"),
    icon: ICON.hand,
    seconds: RESTART_RETURN_SECONDS,
  });
}

/* Long enough to be read, and it is not a deadline: when the count ends,
   goWhenReachable() waits for the store screen to actually answer before
   the browser moves. */
const RESTART_RETURN_SECONDS = 8;

/* How long the screen may sit with nothing to show before it goes back to
   the store page. Counted in polls, like DROPPED_AFTER_POLLS, and at
   POLL_INTERVAL_MS that is about three seconds.

   Not zero, and not one poll: the store screen hands off the moment
   handoff.json appears, and this page can win the race to its first poll
   by a frame or two. Leaving on the first empty answer would bounce the
   browser straight back off an order that was about to appear. Three
   seconds is far longer than that race and far shorter than a person
   standing in front of a dead-looking screen will wait. */
let IDLE_RETURN_POLLS = 25;

let idlePolls = 0;

/* The screen is up, the server is answering, and there is no order --
   and there never was one on this page. Go back to the store screen.

   WHY "AND THERE NEVER WAS ONE"
       lastGoodRecipe is the guard. An order that ran and then ended is
       somebody else's business entirely: the thank-you, the fault card
       and the cancel notice each say their piece and then leave through
       leaveForStoreScreen() on their own schedule. Firing here as well
       would cut those short.

       What is left is the case that had no owner: this page opened with
       no order to show at all -- a bookmark, a kiosk start page, an
       address somebody typed -- which used to mean sitting on "Đang chờ
       đơn hàng" until a human intervened.

   Only while the poll is actually succeeding. "down" is checkDropped's
   question, and a machine that has gone quiet must not be answered by
   walking away from the screen that says so. */
function checkIdle() {
  if (farewellShown || connection !== "live"
      || latestRecipe || lastGoodRecipe) {
    idlePolls = 0;
    return;
  }

  if (IDLE_RETURN_POLLS <= 0) return;      // parked here on purpose

  idlePolls += 1;

  if (idlePolls >= IDLE_RETURN_POLLS) {
    leaveForStoreScreen("nothing to show and no order has run");
  }
}

function checkDropped() {
  if (farewellShown) return;

  // A finished order is never a dropped one, whatever else is true. The
  // runner exits right after stamping completed_at, so without this the
  // server going quiet would turn a thank-you into a failure notice.
  if (lastGoodRecipe && lastGoodRecipe.completed_at) return;

  // 0. the machine was asked to restart. First, because the stamp arrives
  //    a moment before the server stops answering, and every check below
  //    would otherwise turn a deliberate restart into a fault.
  if ((latestRecipe && latestRecipe.restarting_at)
      || (lastGoodRecipe && lastGoodRecipe.restarting_at)) {
    showRestarting();
    return;
  }

  // 1. somebody cancelled it. Checked before the error below: a cancel
  //    writes both, and "cancelled" is the more useful of the two.
  if (latestRecipe && latestRecipe.cancelled_at) {
    showCancelled(latestRecipe);
    return;
  }

  // 2. the machine said what went wrong
  if (latestRecipe && latestRecipe.error) {
    showDropped(latestRecipe, false);
    return;
  }

  // 3. the machine stopped saying anything at all
  if (downPolls >= DROPPED_AFTER_POLLS) {
    // A cancel that this screen never managed to read -- the runner died
    // before a poll landed. lastGoodRecipe still carries the stamp, so the
    // customer gets the true reason rather than "lost contact".
    if (lastGoodRecipe && lastGoodRecipe.cancelled_at) {
      showCancelled(lastGoodRecipe);
      return;
    }
    showDropped(lastGoodRecipe, true);
  }
}

/**
 * The customer's free-text note, and nothing else.
 *
 * The bar exists only while there is one. Nothing is emptied and left on
 * screen: an amber strip that appears on every order stops being read by
 * the third drink, and then the one order that carries a real request is
 * missed too. Its presence IS the message.
 */
function renderNote(recipe) {
  if (!ui.noteBar) return;

  const note = (recipe && recipe.note) || "";

  if (!note) {
    ui.noteBar.hidden = true;
    return;
  }

  // textContent, not innerHTML: this string was typed by a customer.
  if (ui.noteText.textContent !== note) ui.noteText.textContent = note;
  ui.noteBar.hidden = false;
}

function renderStatus(recipe) {
  renderNote(recipe);

  // --- shift totals ---
  recordCompletion(recipe);
  maybeShowThanks(recipe);
  const shift = readShift();
  setText(ui.statToday, shift.count ? t("cups")(shift.count) : "—");
  setText(ui.statAvg, shift.count
    ? formatDuration(shift.totalMs / shift.count)
    : "—");
  setText(ui.statLast, shift.lastMs ? formatDuration(shift.lastMs) : "—");

  // --- machine ---
  ui.statMode.textContent =
    connection === "sim" ? t("modeSim")
      : connection === "down" ? t("modeOffline")
        : t("modeLive");
  setText(ui.statClock, formatClock(new Date().toISOString()));
}

/* ---- next-order button, shown when the drink is finished ---- */

function renderDoneActions(recipe) {
  const finished = Boolean(recipe) && !currentStep(recipe);
  setHidden(ui.doneActions, !finished);
  if (finished) {
    setText(ui.nextOrderLabel, t("nextOrder"));
    setText(ui.doneHint, t("nextOrderHint"));
  }
}

/**
 * Clear the finished drink and go back to waiting for a scan.
 * In simulation this just drops the recipe. Against real hardware the
 * machine has to be told, otherwise the next poll re-reads the same
 * completed process.json and the done screen returns.
 */
async function onNextOrder() {
  if (window.FLEXMIX_SIM) {
    window.FLEXMIX_SIM.clear();
    latestRecipe = null;
    gateSignature = "";
    render(null);
    return;
  }

  try {
    await fetch("../api/order/ack", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        order_id: latestRecipe && latestRecipe.order_id,
      }),
    });
  } catch (error) {
    /* the next poll shows whether the machine cleared it */
  }
}

/* ---- top bar: drink name, order id, overall progress ---- */

function renderHeader(recipe) {
  if (!recipe) {
    setText(ui.drinkName, "—");
    setText(ui.orderId, t("noOrder"));
    setWidth(ui.progressBar, "0%");
    setText(ui.progressLabel, "— / —");
    return;
  }

  setText(ui.drinkName, recipe.name || "—");
  setText(ui.orderId, recipe.order_id
    ? `#${String(recipe.order_id).slice(0, 8).toUpperCase()}`
    : "—");

  const steps = recipe.steps || [];
  const total = steps.length;
  const done = steps.filter(
    s => ["completed", "skipped"].includes(String(s.status)),
  ).length;

  setWidth(ui.progressBar, total ? `${(done / total) * 100}%` : "0%");
  setText(ui.progressLabel, `${done} / ${total}`);
}

function render(recipe) {
  renderHeader(recipe);
  renderNow(recipe);
  renderGate(recipe);
  renderRail(recipe);
  renderProcess(recipe);
  renderStatus(recipe);
  renderDoneActions(recipe);
}

/* ================================================================ POLL ==== */

/* The simulator is opt-in: add ?sim=1 to the URL. Without it the screen
   reads order/current_recipe.json and never advances anything by itself — it is a
   mirror of whatever the machine wrote. */
const SIM_ENABLED = new URLSearchParams(location.search).has("sim");
const source = SIM_ENABLED ? window.FLEXMIX_RECIPE_SOURCE : null;

let inFlight = false;
let sourceProblem = null;   // "badJson" when the file is unreadable JSON


/**
 * The machine can hang while its HTTP server keeps serving the last
 * process.json with 200 OK. Detect that: a step that claims to be
 * pouring but has stopped updating is not connected, it is stuck.
 */
function isStale(recipe) {
  if (!recipe) return false;
  if (!STALE_AFTER_MS) return false;   // 0 in gui_config disables the check
  const step = currentStep(recipe);
  if (!step || String(step.status) !== "processing") return false;
  const updated = Date.parse(recipe.updated_at);
  return Number.isFinite(updated) && Date.now() - updated > STALE_AFTER_MS;
}

async function refresh() {
  if (inFlight) return;       // never let requests pile up
  inFlight = true;

  try {
    let recipe;
    if (source && typeof source.read === "function") {
      recipe = await source.read();
      setConnection(source.simulated ? "sim" : "live");
    } else {
      const response = await fetch(`${RECIPE_URL}?t=${Date.now()}`, {
        cache: "no-store",
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      // Parse by hand so a syntax error reads as "malformed file" rather
      // than "lost connection" — those need very different fixes.
      const text = await response.text();
      try {
        recipe = JSON.parse(text);
      } catch (parseError) {
        // Not shown to the customer any more, so it has to be findable
        // here -- "malformed recipe" and "cannot reach the machine" need
        // very different fixes and both now look the same on screen.
        sourceProblem = "badJson";
        console.error("[guide] current_recipe.json is not valid JSON:",
                      parseError);
        throw parseError;
      }

      sourceProblem = null;
      if (isProcessDoc(recipe)) recipe = adaptProcess(recipe);
      setConnection("live");
    }

    if (latestRecipe && recipe && latestRecipe.order_id !== recipe.order_id) {
      firstSeenRunning.clear();   // new order: drop the local start clocks
    }
    latestRecipe = isAnOrder(recipe) ? recipe : null;
    if (latestRecipe) lastGoodRecipe = latestRecipe;
    downPolls = 0;                    // it answered, so it is not gone
    if (connection !== "sim" && isStale(latestRecipe)) setConnection("stale");
  } catch (error) {
    setConnection("down");
    downPolls += 1;
    // latestRecipe is deliberately NOT cleared. Clearing it dropped the
    // screen to "Đang chờ đơn hàng" -- the empty waiting page -- for the
    // moment between the machine going quiet and this screen leaving. The
    // customer saw the machine stop, then an idle screen as though no
    // order had ever existed, then the store page. Holding the last known
    // frame means they see the drink they ordered until the browser moves.
  } finally {
    inFlight = false;
  }

  // FIRST, and never inside the try above. Deciding to leave a dead order
  // must not depend on the screen managing to draw it.
  //
  // This was the other way round and the machine got stuck: render() throws
  // on some recipe, the exception escapes the poll, checkDropped() below it
  // never runs, and the screen freezes on the last frame that rendered --
  // still showing "connected" and a step still pouring, while the file has
  // said "failed" for minutes. The customer waits at a machine that has
  // already given up.
  checkDropped();
  checkIdle();

  updateCancelButton(latestRecipe);

  // Rendered every tick on purpose: the pour meters animate continuously.
  // Guarded because a drawing bug should cost a stale picture, not a
  // machine that will not move on. The message names render() so it is not
  // mistaken for a fetch problem.
  try {
    render(latestRecipe);
  } catch (error) {
    console.error("[guide] render() failed; screen may be stale:", error);
  }
}

/** Self-scheduling poll so the interval can adapt to the connection state. */
function pollLoop() {
  window.setTimeout(async () => {
    await refresh();
    pollLoop();
    // Only back off AFTER the screen has given up on this order. Backing
    // off at the first failure made three failed polls take three seconds
    // instead of a third of one, which was most of the wait the customer
    // saw before the store screen appeared.
  }, downPolls >= DROPPED_AFTER_POLLS ? DOWN_POLL_MS : POLL_INTERVAL_MS);
}

/* ============================================================ CONFIRM ==== */

/* ---- press feedback on the big gate button ----
   Both gates that use it — "BẮT ĐẦU" and "Kiểm tra ly" — hand the request
   over to the machine and then wait. The press animation says the tap
   landed; the busy spinner says the machine is still thinking. Without the
   second one the screen looks frozen and the customer taps again. */

const PRESS_FLASH_MS = 340;     // matches the pressPop keyframes in guide.css
const RIPPLE_LIFETIME_MS = 620; // slightly longer than rippleOut, then removed
const MIN_BUSY_MS = 280;        // so a fast answer still shows as a beat

/** True when the screen has asked for as little animation as possible. */
const reducedMotion = () =>
  Boolean(window.matchMedia) &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const wait = ms => new Promise(resolve => window.setTimeout(resolve, ms));

/**
 * Play the press animation, with a ripple centred on where the finger landed.
 *
 * The class is removed and re-added on a forced reflow so a second tap
 * restarts the animation instead of being swallowed by the running one.
 * A keyboard-activated click reports detail 0 and no useful coordinates, so
 * that ripple starts from the middle of the button.
 */
function flashPress(button, event) {
  if (reducedMotion()) return;

  button.classList.remove("is-pressed");
  void button.offsetWidth;
  button.classList.add("is-pressed");
  window.setTimeout(() => button.classList.remove("is-pressed"), PRESS_FLASH_MS);

  const box = button.getBoundingClientRect();
  const size = Math.max(box.width, box.height) * 2;
  const fromPointer = Boolean(event) && event.detail !== 0;
  const x = fromPointer ? event.clientX - box.left : box.width / 2;
  const y = fromPointer ? event.clientY - box.top : box.height / 2;

  const ripple = document.createElement("span");
  ripple.className = "gate-ripple";
  ripple.style.width = `${size}px`;
  ripple.style.height = `${size}px`;
  ripple.style.left = `${x - size / 2}px`;
  ripple.style.top = `${y - size / 2}px`;
  button.appendChild(ripple);
  window.setTimeout(() => ripple.remove(), RIPPLE_LIFETIME_MS);
}

/** True while a request raised by the gate button is still outstanding. */
let confirmBusy = false;

/* WHICH step the outstanding press belongs to.
   A press is answered by the step it was made on, and by no other. Without
   this the busy state was global and leaked forward: an action step and the
   cup-back step that follows it are two gates in a row, so the screen went
   from one straight to the next without ever passing through the "no gate"
   branch in renderGate() that clears the flag -- holdingGate() deliberately
   holds that branch during the pause between steps, and holds the flag with
   it. The cup-back gate then arrived already busy, which meant
   setConfirmLabel() refused to write its label and releaseConfirm() kept the
   button disabled: "Đặt ly trở lại máy" showed a dead button reading "Đang
   xử lý..." and the only way out of the drink was to cancel it. */
let confirmBusyStep = null;

/** Show the spinner and lock the button out for the length of a request. */
/* The words the button shows when it is NOT working -- "BẮT ĐẦU",
   "Kiểm tra ly", "Thử lại". Remembered so the waiting text can be swapped
   in and the right one put back afterwards. */
let confirmIdleLabel = "";

/** Set the button's resting label. Ignored while it is working. */
function setConfirmLabel(text) {
  confirmIdleLabel = text;
  if (!confirmBusy) setText(ui.gateConfirmLabel, text);
}

function setConfirmBusy(busy, stepLabel) {
  confirmBusy = busy;
  confirmBusyStep = busy ? (stepLabel ?? confirmBusyStep) : null;
  ui.gateConfirm.classList.toggle("is-busy", busy);
  ui.gateConfirm.disabled = busy;
  ui.gateConfirm.setAttribute("aria-busy", busy ? "true" : "false");
  // Say what is happening. Leaving it on "BẮT ĐẦU" while the arrow rose
  // read as though the press had not registered.
  setText(ui.gateConfirmLabel, busy ? t("waitingBtn") : confirmIdleLabel);
}

/**
 * Re-enable the gate button — unless a request is still in flight.
 *
 * renderGate() runs on every poll and would otherwise hand the button back
 * mid-request, letting a second tap start a second cup check.
 */
function releaseConfirm() {
  ui.gateConfirm.disabled = confirmBusy;
}

/**
 * The bartender pressed the big button.
 * In simulation this drives the fake machine. Against real hardware this is
 * where you POST to the machine — see the handover notes in bartender-sim.js.
 */
async function onConfirm(event) {
  const step = currentStep(latestRecipe);
  if (!step) return;
  if (confirmBusy) return;   // a request is already out; ignore the double tap

  flashPress(ui.gateConfirm, event);

  // A detect step asks the machine to read its sensor rather than simply
  // accepting the operator's word for it.
  if (needsSensor(step)) {
    setConfirmBusy(true, String(step.step_label));
    const busyUntil = wait(MIN_BUSY_MS);
    let cupFound = false;
    try {
      const response = await fetch("../api/process/detect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ step: step.step_label }),
      });
      const result = await response.json().catch(() => ({}));

      if (response.ok && result.detected) {
        // The machine closes the step; say so rather than looking frozen.
        cupFound = true;
        detectMessage = t("cupSeen");
      } else if (response.ok) {
        detectMessage = t("noCup")(gram(result.current_gram),
                                   gram(result.min_gram));
      } else {
        detectMessage = result.error || t("waitingSensorPlain");
      }
    } catch (error) {
      detectMessage = String(error.message || error);
    }
    await busyUntil;

    // Cup found: the machine takes it from here, and there is a pause
    // before the next step. Stay in the working state until the gate
    // clears, so the screen never looks idle while the machine is not.
    // Cup not found: hand the button straight back, the operator has to
    // reposition and press again.
    if (!cupFound) setConfirmBusy(false);

    gateSignature = "";
    await refresh();
    return;
  }

  detectMessage = null;

  if (window.FLEXMIX_SIM) {
    if (hasFailed(step)) window.FLEXMIX_SIM.retry();
    else window.FLEXMIX_SIM.confirm();
    gateSignature = "";
    render(latestRecipe);
    return;
  }

  // Live machine: needs a confirm endpoint on gui/api/server.py.
  // Releasing the start gate makes the machine weigh the empty glass, which
  // takes a second or two, so the spinner stays up until the next poll shows
  // whether the step moved on.
  setConfirmBusy(true, String(step.step_label));
  const busyUntil = wait(MIN_BUSY_MS);
  try {
    const response = await fetch("../api/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        order_id: latestRecipe && latestRecipe.order_id,
        step_number: step.step_number,
        action: hasFailed(step) ? "retry" : "confirm",
      }),
    });

    // fetch only rejects on a network fault: a relay that answered "no
    // order is running" (503) or could not reach the runner (502) arrives
    // here as a perfectly resolved promise. Ignoring the status left the
    // button locked on "Đang xử lý..." for a press the machine never got,
    // with cancelling the drink the only way out.
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}));
      console.warn("confirm refused:", detail.error || response.status);
      setConfirmBusy(false);
    }
  } catch (error) {
    // The press never reached the machine, so nothing is coming that
    // could hand the button back. Release it here or the operator is
    // locked out of a gate the machine is still waiting on.
    setConfirmBusy(false);
  }
  await busyUntil;
  gateSignature = "";
  await refresh();

  // Otherwise deliberately NOT cleared here. Releasing this gate makes the machine
  // weigh the cup and then wait STEP_DELAY_SECONDS before the first pour,
  // and the request returns long before any of that. Clearing now put the
  // button back to idle while nothing visible happened for two seconds.
  // renderGate() clears it when the gate actually goes away.
}

ui.gateConfirm.addEventListener("click", onConfirm);
ui.nextOrderBtn.addEventListener("click", onNextOrder);

/**
 * A hardware-gate tile was clicked. This only exists in simulation — on real
 * hardware the press arrives from panel_control/panel.py and this screen just
 * watches the status change.
 */
ui.gateButtons.addEventListener("click", async event => {
  const tile = event.target.closest("[data-panel]");
  if (!tile || tile.tagName !== "BUTTON") return;
  const panel = Number(tile.dataset.panel);

  if (SIM_ENABLED && window.FLEXMIX_SIM) {
    window.FLEXMIX_SIM.pressPanel(panel);
    gateSignature = "";
    render(latestRecipe);
    return;
  }

  // Live: record it in process.json. The step must be GUI-owned; the server
  // refuses anything else.
  const step = currentStep(latestRecipe);
  if (!step) return;

  tile.disabled = true;                  // no double press while in flight
  try {
    const response = await fetch("../api/process/button", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ step: step.step_label, panel }),
    });
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}));
      console.warn("button not recorded:", detail.error || response.status);
      tile.disabled = false;
      return;
    }
  } catch (error) {
    console.warn("button not recorded:", error);
    tile.disabled = false;
    return;
  }

  gateSignature = "";
  await refresh();                       // show it without waiting for the poll
});

/* ============================================================ SIM WIRING == */

function initSim() {
  const sim = window.FLEXMIX_SIM;
  if (!sim) return;

  setHidden(ui.simbar, false);
  ui.simDrink.innerHTML = sim.drinks
    .map(d => `<option value="${d.drink_id}">${escapeHtml(d.name)}</option>`)
    .join("");

  const start = () => {
    sim.setSpeed(ui.simSpeed.value);
    sim.newOrder(ui.simDrink.value);
    gateSignature = "";
  };

  // Collapsed by default so the screen reads as the shipped product.
  ui.simToggle.addEventListener("click", () => {
    const open = ui.simPanel.hidden;
    setHidden(ui.simPanel, !open);
    ui.simToggle.setAttribute("aria-expanded", String(open));
  });

  ui.simStart.addEventListener("click", start);
  ui.simFail.addEventListener("click", () => sim.failNext());
  ui.simSpeed.addEventListener("change", () => sim.setSpeed(ui.simSpeed.value));

  start();
}

/* =============================================================== LANG ==== */

function applyLang() {
  document.documentElement.lang = lang;
  setText(ui.langBtn, lang === "vi" ? "EN" : "VI");
  setText(ui.railTitle, t("steps"));
  setText(ui.machineTitle, t("nowPanel"));
  setText(ui.noteLabel, t("noteLabel"));
  setText(ui.lblToday, t("today"));
  setText(ui.lblAvg, t("avgPerCup"));
  setText(ui.lblLast, t("lastCup"));
  setText(ui.lblMode, t("mode"));
  setText(ui.lblClock, t("nowClock"));
  setText(ui.simStart, t("newOrder"));
  setText(ui.simFail, t("simFail"));
  setText(ui.simDrinkLabel, t("drink"));
  setText(ui.simSpeedLabel, t("speed"));
  gateSignature = "";
  render(latestRecipe);
}

/* Cancel: the button opens the reason dialog, never cancels on its own.
   One tap must not be able to stop a drink -- a reason is required, which
   is also what makes the record worth keeping. */
ui.cancelBtn.addEventListener("click", openCancel);
ui.cancelBack.addEventListener("click", resumeOrder);
ui.cancelConfirm.addEventListener("click", sendCancel);

ui.langBtn.addEventListener("click", () => {
  lang = lang === "vi" ? "en" : "vi";
  store.set("flexmix.lang", lang);
  applyLang();
});

/* =============================================================== BOOT ==== */

/**
 * Load the shared config, apply the parts the guide cares about, and hand
 * it to the simulator. A failure here is not fatal: every consumer falls
 * back to its built-in default.
 */
async function loadConfig() {
  try {
    const response = await fetch(`${CONFIG_URL}?t=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    CFG = await response.json();
  } catch (error) {
    console.warn("gui_config.json unavailable, using built-in defaults:", error);
    return;
  }

  const ui = CFG.ui || {};
  if (ui.poll_interval_ms) POLL_INTERVAL_MS = ui.poll_interval_ms;
  if (ui.down_poll_ms) DOWN_POLL_MS = ui.down_poll_ms;
  if (ui.dropped_after_polls) DROPPED_AFTER_POLLS = ui.dropped_after_polls;
  // 0 turns the idle return off entirely, for a screen deliberately left
  // parked on this page. Tested against undefined rather than falsiness
  // for exactly that reason -- `if (ui.idle_return_polls)` would silently
  // ignore the one value somebody sets on purpose.
  if (ui.idle_return_polls !== undefined) {
    IDLE_RETURN_POLLS = Number(ui.idle_return_polls);
  }
  if (ui.store_url) STORE_URL = ui.store_url;
  if (ui.stale_after_ms) STALE_AFTER_MS = ui.stale_after_ms;
  if (ui.gram_per_sec_fallback) FALLBACK_GRAM_PER_SEC = ui.gram_per_sec_fallback;

  // language: a stored preference always wins over the configured default
  if (!store.get("flexmix.lang") && ui.default_language) {
    lang = ui.default_language;
  }

  if (window.FLEXMIX_SIM && typeof window.FLEXMIX_SIM.configure === "function") {
    window.FLEXMIX_SIM.configure(CFG);
  }
}

/* Keep the kiosk screen awake; the browser will otherwise blank mid-service.
   Re-requested on visibility change because the lock is dropped when hidden. */
let wakeLock = null;
async function keepScreenAwake() {
  try {
    if ("wakeLock" in navigator) {
      wakeLock = await navigator.wakeLock.request("screen");
    }
  } catch (error) {
    /* denied or unsupported: nothing we can do, carry on */
  }
}
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") keepScreenAwake();
});

async function boot() {
  await loadConfig();     // must finish before the first render
  applyLang();
  initSim();
  keepScreenAwake();
  await refresh();
  pollLoop();
}

boot();
