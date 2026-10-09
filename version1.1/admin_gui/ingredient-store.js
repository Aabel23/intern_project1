/* ================================================================
   INGREDIENT STORE  —  what the stock page reads and writes
   ----------------------------------------------------------------
   The same shape as menu-store.js and for the same reasons: the cache
   below is only what the last GET said, every write goes to the server,
   and the cache is refreshed from what the server accepted rather than
   from what the page hoped for.

   WHY IT IS A SECOND FILE AND NOT A SECTION OF menu-store.js
     The two answer different questions. menu-store.js is the menu -- what
     is for sale, at what price. This is the machine -- what is in the
     bottles and which pump each one is on. The stock page needs the menu
     store as well (the mode chip in the topbar reads it), so merging them
     would only mean the menu page also carrying stock it never draws.

   WHAT IS DERIVED AND THEREFORE NOT WRITTEN HERE
     in_stock and threshold_gram. Both are computed by the database and by
     database/inventory_service.py; the page shows them and never sends
     them. See the ingredients section of admin_gui/serve.py -- the same
     note lives at the other end of these four URLs.
   ================================================================ */
(function (global) {
  const LIST_URL       = '../api/ingredients';
  const REFILL_URL     = '../api/ingredient/refill';
  const REFILL_ALL_URL = '../api/ingredient/refill-all';
  const SAVE_URL   = '../api/ingredient/save';
  const DELETE_URL = '../api/ingredient/delete';

  // Below this share of the container the page calls it low. Only a
  // warning colour: the database's own line is threshold_gram, which is
  // what actually stops a drink being sold.
  const LOW_SHARE = 0.10;

  let ingredients = [];
  let pumps = [];
  let panelCount = 16;
  let defaultMax = 10000;
  let loaded = false;
  const listeners = [];

  /* ---------------------------------------------------------------
     Ô phần cứng ("slot") không còn là số trần.
     ingredient.gpio giờ ghi cả nơi cắm lẫn số: "G26" là chân bơm BCM 26,
     "P01" là ô số 1 trên panel thủ công. Một số 1 đứng một mình không nói
     được nó là chân 1 hay ô 1, nên chữ cái đứng trước chính là phần làm
     cho ô đó đọc được một mình.

     Trang vẫn cho người dùng chọn theo SỐ ("Bơm #3", "Ô số 5") và vẫn gửi
     số trần lên server, nên mọi phép so sánh ở đây phải lấy số bên trong
     ô ra rồi mới so — Number("G26") là NaN, và NaN không bằng cái gì cả.
     --------------------------------------------------------------- */
  function slotNumber(slot) {
    if (slot === null || slot === undefined) return null;

    const text = String(slot).trim();
    if (!text) return null;

    // Cũng nhận số trần, để một database chưa đổi vẫn đọc được.
    const digits = /^[GP]/i.test(text) ? text.slice(1) : text;
    const number = Number(digits);

    return digits !== '' && Number.isFinite(number) ? number : null;
  }

  function notify() {
    listeners.slice().forEach(fn => {
      try { fn(); } catch (error) { console.error('[ingredient-store]', error); }
    });
  }

  /* Same contract as menu-store.js call(): the token goes on every
     request, a 401 sends the browser back to the login screen instead of
     filling the page with toasts, and a failure that arrives as an HTML
     error page is reported by its status rather than as "unknown error". */
  async function call(url, options) {
    let response;

    const settings = { ...(options || {}) };
    settings.headers = {
      ...(settings.headers || {}),
      Authorization: 'Bearer ' + (window.AdminAuth ? AdminAuth.token() : ''),
    };

    try {
      response = await fetch(url, settings);
    } catch (error) {
      throw new Error('Không kết nối được máy chủ.');
    }

    const result = await response.json().catch(() => ({}));

    if (response.status === 401) {
      if (window.AdminAuth) AdminAuth.logout();
      throw new Error(result.error || 'Phiên đăng nhập đã hết hạn.');
    }

    if (!response.ok || !result.ok) {
      throw new Error(result.error || (response.status === 404
        ? 'Máy chủ chưa có ' + url + ' — khởi động lại serve.py (bản đang chạy đã cũ).'
        : 'Máy chủ trả về lỗi ' + response.status + ' từ ' + url + '.'));
    }

    return result;
  }

  const postJson = body => ({
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  /* Lần tải hỏng gần nhất, giữ lại để bảng nói ra được.
     Không có nó thì một lần GET hỏng để bảng đứng nguyên ở "Đang tải từ
     database…" mãi mãi: toast báo lỗi tự tắt sau vài giây, còn onChange
     thì không bao giờ chạy, nên trên màn chỉ còn đúng chữ "đang tải" cho
     một thứ đã ngừng tải từ lâu. */
  let loadError = null;

  async function load() {
    let result;

    try {
      result = await call(LIST_URL, { cache: 'no-store' });
    } catch (error) {
      loadError = error.message;
      notify();
      throw error;
    }

    ingredients = result.ingredients || [];
    pumps = result.pumps || [];
    if (result.panel_count) panelCount = result.panel_count;
    if (result.default_max_gram) defaultMax = result.default_max_gram;
    loaded = true;
    loadError = null;
    notify();
    return result;
  }

  const IngredientStore = {
    isLoaded() { return loaded; },
    loadError() { return loadError; },
    all() { return ingredients; },
    defaultMax() { return defaultMax; },

    /* Chỗ để gắn bình: các bơm 1..10 (kèm chân GPIO của từng bơm) và số
       ô trên panel thủ công. Form chỉ hiện số bơm / số ô; chân GPIO đi
       kèm để gửi lại cho server, vì cột trong database vẫn là chân. */
    pumps() { return pumps; },
    panelCount() { return panelCount; },

    slotNumber,

    /* Nguyên liệu nào đang chiếm một vị trí. Khóa duy nhất trong database
       là (type, gpio), nên cùng một số chỉ đụng nhau trong cùng một loại.
       So bằng SỐ trong ô chứ không so chuỗi: form gửi lên số trần (3),
       còn database trả về ô có tiền tố ("G20"), hai cái đó là một chỗ. */
    holderOf(type, gpio) {
      const number = slotNumber(gpio);
      if (number === null) return null;

      return ingredients.find(row =>
        row.type === type && slotNumber(row.gpio) === number) || null;
    },
    get(id) {
      return ingredients.find(row => Number(row.ingredient_id) === Number(id)) || null;
    },

    refresh() { return load(); },

    /* How full one container is, as the page draws it.
       percent is capped at 100 because a bottle topped past its recorded
       size is a wrong size, not a 130% bottle -- and a bar wider than its
       track just looks broken. `over` says so instead.
       `state` is the colour, and it is NOT three thresholds of the same
       number: 'crit' means the database has stopped selling drinks that
       need this (amount < threshold_gram), which can happen at any
       percentage, while 'low' is only this page's early warning. */
    level(row) {
      const max = Number(row.max_gram) || 0;
      const amount = Number(row.amount) || 0;
      const share = max > 0 ? amount / max : 0;

      return {
        percent: Math.max(0, Math.min(100, Math.round(share * 100))),
        over: max > 0 && amount > max,
        state: !row.in_stock ? 'crit' : (share < LOW_SHARE ? 'low' : 'ok'),
      };
    },

    /* WRITES — all four reload from the server before repainting.
       A refill is not "amount + n" in the browser: the pumps are
       subtracting from the same column while this page is open, so what
       the row now holds is a question only the database can answer. */
    async refill(id, change) {
      const result = await call(REFILL_URL,
        postJson({ ingredient_id: Number(id), ...change }));
      await load();
      return result;
    },

    /* Nạp đầy hàng loạt. `ids` bỏ trống nghĩa là tất cả; truyền mảng id
       khi người dùng bỏ tick vài dòng trong bảng xác nhận.
       Server ghi trong MỘT transaction, nên kết quả trả về là toàn bộ
       hoặc không gì cả — trang không phải đoán xem dòng nào đã kịp ghi. */
    async refillAll(ids) {
      const result = await call(REFILL_ALL_URL,
        postJson(ids ? { only: ids.map(Number) } : {}));
      await load();
      return result;
    },

    async save(record) {
      const result = await call(SAVE_URL, postJson(record));
      await load();
      return result;
    },

    async remove(id) {
      const result = await call(DELETE_URL,
        postJson({ ingredient_id: Number(id) }));
      await load();
      return result;
    },

    onChange(fn) {
      if (typeof fn !== 'function') return;
      listeners.push(fn);
      if (loaded) queueMicrotask(fn);
    },
  };

  global.IngredientStore = IngredientStore;

  load().catch(error => {
    console.error('[ingredient-store]', error);
    if (typeof global.showToast === 'function') {
      global.showToast('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M10.3 3.9 1.8 18.1A2 2 0 0 0 3.5 21h17a2 2 0 0 0 1.7-2.9L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/></svg> ' + error.message, 'warn');
    }
  });
})(window);
