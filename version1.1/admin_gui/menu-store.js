/* ================================================================
   MENU STORE  —  what the admin pages read and write
   ----------------------------------------------------------------
   The pages were written against a `MenuStore` global that did not
   exist in this project. This is it, talking to admin_gui/serve.py.

   TWO KINDS OF STATE, ON PURPOSE
     The menu — drinks, prices, categories, availability — lives in
     MySQL. Nothing here is the truth; the cache below is only what
     the last GET said, kept so the table can paint synchronously.
     Every write goes to the server and the cache is refreshed from
     what the server accepted, never from what the page hoped for.

     The operating mode — which buttons the customer screen offers —
     used to live in this browser's localStorage, and controlled
     nothing: the admin console and the customer screen are different
     browsers, often different devices, so nothing over there could
     ever read it. It moved to the server on 2026-09-07 and is now a
     file the machine actually obeys — see
     configuration/order_mode.py. It is cached here on exactly the same
     terms as the menu above: the cache is what the last GET said, and
     a write is followed by what the server accepted.

   WHY THE PAGES CAN RENDER BEFORE THE FETCH LANDS
     menu.js calls render() on the last line of the file, long before
     any request could return. So cats() and allItems() answer
     immediately with whatever is cached — empty on first paint — and
     the load fires onChange() when it arrives, which is what the
     pages already subscribe to. An empty table for one frame, rather
     than a page that has to be rewritten to await anything.
   ================================================================ */
(function (global) {
  const MENU_URL   = '../api/menu';
  const AVAIL_URL  = '../api/drink/available';
  const PRICE_URL  = '../api/drink/price';
  const EDITOR_URL = '../api/recipe-editor';
  const RECIPE_URL = '../api/recipe';
  const DELETE_URL = '../api/drink/delete';
  const RESTORE_URL = '../api/drink/restore';
  const PURGE_URL = '../api/drink/purge';
  const FEATURED_URL = '../api/drink/featured';
  const FEATURED_CONFIG_URL = '../api/store/featured';
  const BESTSELLER_CONFIG_URL = '../api/store/bestseller';
  const LAYOUT_URL = '../api/store/layout';

  /* Which buttons the customer screen offers. On the SERVER, not in
     localStorage -- see the note at the top of this file. */
  const ORDER_MODE_URL = '../api/order-mode';

  /* The one setting still kept in this browser, because it is the one
     that still controls nothing -- see config(). Kept under its own key
     rather than the old shared one, so a machine upgraded from the
     localStorage era does not carry a stale printQR/autoStart pair
     forward and quietly disagree with the server. */
  const DRY_RUN_KEY = 'tramrot_admin_dryrun';

  /* The admin API is served by BOTH store_gui/serve.py and
     admin_gui/serve.py, so these pages work on either port. This is only
     used to explain a 404, which now means one thing: the server answering
     is running code from before the endpoints existed. */
  const ADMIN_PORT = '8100';

  let drinks = [];
  let categories = [];
  let loaded = false;
  const listeners = [];

  /* The featured strip's settings, and the ceiling on how many drinks
     may be in it. Both come from the server on every load -- the cap in
     particular, because the sentence the operator reads and the number
     the server actually enforces must be the same one. Seeded with what
     the page should show before the first fetch lands rather than left
     undefined, so a render() at file scope has something to draw. */
  let featuredSettings = { enabled: true, title: 'Món nổi bật',
                           drinkIds: [] };
  let featuredCeiling = 6;
  let bestsellerSettings = { enabled: true, title: 'Bán chạy nhất',
                             windowDays: 30, count: 6,
                             drinkIds: [], sold: {} };
  let layoutOrder = ['featured', 'bestseller', 'grid'];
  let layoutBlocks = ['featured', 'bestseller', 'grid'];
  let featuredStyles = ['carousel', 'cinematic', 'board', 'bubble'];
  let bestsellerStyles = ['carousel', 'cinematic', 'board', 'bubble', 'chart'];
  let columnStyles = ['board', 'chart'];
  let columnRange = [1, 3];
  /* The bounds the SERVER enforces, sent with every load rather than
     copied into this file. A browser that disagreed with the server about
     the legal range would refuse a value the database would have taken,
     or offer one it then rejects -- and either way the operator is being
     argued with by two halves of the same console. */
  let windowRange = [1, 365];
  let countRange = [1, 12];

  /* Seeded with the machine's historical behaviour, for the same reason
     featuredSettings above is seeded: a render() at file scope has to
     have something to draw, and the thing it draws before the fetch
     lands must be the safe answer rather than a blank one. Narrowed only
     by a good reply -- see loadOrderMode(). */
  let orderMode = { printQR: true, runDirect: true };

  function notify() {
    // Copied first: a listener that re-renders can subscribe another,
    // and iterating the live array while it grows never ends.
    listeners.slice().forEach(fn => {
      try { fn(); } catch (error) { console.error('[menu-store]', error); }
    });
  }

  /* ---------- talking to the server ----------
     A failure does not always arrive as JSON — a 404 from a server
     started before these endpoints existed is an HTML error page — so
     when there is no message to quote, quote the status. Same rule as
     store_gui/drinks-pos.js, and for the same reason: "could not
     update" hides the one fact that explains it. */
  async function call(url, options) {
    let response;

    // Every admin request carries the token the server issued at login.
    // Without it the server answers 401 -- which is the point: this page
    // being open is not permission, the token is.
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
      // The session is gone -- expired, or the signing secret was
      // replaced. There is nothing this page can do without one, so it
      // goes back to the login screen rather than filling with toasts.
      if (window.AdminAuth) AdminAuth.logout();
      throw new Error(result.error || 'Phiên đăng nhập đã hết hạn.');
    }

    if (!response.ok || !result.ok) {
      throw new Error(result.error || describeFailure(response.status, url));
    }

    return result;
  }

  function describeFailure(status, url) {
    if (status !== 404) {
      return 'Máy chủ trả về lỗi ' + status + ' từ ' + url + '.';
    }

    // Something answered but has no admin API: a server started before
    // these endpoints existed. Name the one serving THIS page, so the
    // right process gets restarted.
    const which = location.port === ADMIN_PORT
      ? 'admin_gui/serve.py' : 'store_gui/serve.py';

    return 'Máy chủ chưa có ' + url + ' — khởi động lại ' + which +
      ' (bản đang chạy đã cũ).';
  }

  /* The server says so when it saved the change but could not rewrite
     the customer screen's copy of the menu. Not an error -- the database
     took it -- but the shop floor is now showing something else, and
     nobody would ever guess that from a green tick. */
  function reportWarning(result) {
    if (result && result.warning && typeof window.showToast === 'function') {
      showToast('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M10.3 3.9 1.8 18.1A2 2 0 0 0 3.5 21h17a2 2 0 0 0 1.7-2.9L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/></svg> ' + result.warning, 'warn');
    }
    return result;
  }

  const postJson = body => ({
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  async function load() {
    const result = await call(MENU_URL, { cache: 'no-store' });
    drinks = result.drinks || [];
    categories = result.categories || [];
    // A server from before the featured endpoints existed answers /api/menu
    // without these two, and the page must still work: keep what we had
    // rather than blanking the panel to undefined.
    if (result.featuredConfig) featuredSettings = result.featuredConfig;
    if (result.featuredMax) featuredCeiling = Number(result.featuredMax);
    if (result.bestsellerConfig) bestsellerSettings = result.bestsellerConfig;
    if (result.layout) layoutOrder = result.layout;
    if (result.layoutBlocks) layoutBlocks = result.layoutBlocks;
    if (result.featuredStyles) featuredStyles = result.featuredStyles;
    if (result.bestsellerStyles) bestsellerStyles = result.bestsellerStyles;
    if (result.columnStyles) columnStyles = result.columnStyles;
    if (result.columnRange) columnRange = result.columnRange;
    if (result.bestsellerWindowRange) windowRange = result.bestsellerWindowRange;
    if (result.bestsellerCountRange) countRange = result.bestsellerCountRange;
    loaded = true;
    notify();
    return result;
  }

  /* The operating mode, on the same terms as load() above: the cache is
     what the last GET said, and onChange() fires when it lands so a page
     already painted from the seed repaints itself.

     Its own request rather than a field on /api/menu, because the
     customer screen reads this endpoint too and must not need a session
     -- and /api/menu does. See ORDER_MODE_PATH in admin_gui/serve.py. */
  async function loadOrderMode() {
    const result = await call(ORDER_MODE_URL, { cache: 'no-store' });

    // Narrow only on an answer that actually carries both switches. A
    // server from before this endpoint existed answers 404, and taking
    // {undefined, undefined} would leave every page claiming the shop
    // sells no way at all.
    if (typeof result.printQR === 'boolean' &&
        typeof result.runDirect === 'boolean') {
      orderMode = { printQR: result.printQR, runDirect: result.runDirect };
      notify();
    }

    return orderMode;
  }

  /* ---------- the menu ---------- */
  const MenuStore = {
    isLoaded() { return loaded; },
    cats() { return categories; },
    allItems() { return drinks; },
    getItem(id) {
      return drinks.find(item => Number(item.id) === Number(id)) || null;
    },

    /* Reloads from the database and repaints. Also the recovery path
       for a page left open while somebody else edited the menu. */
    refresh() { return load(); },
    refreshOrderMode() { return loadOrderMode(); },

    /* WRITES
       No optimistic update. The switch and the price box have already
       moved on screen — the browser did that — so on success the cache
       is corrected and every page repaints from it, and on FAILURE the
       cache is untouched and repainting is what puts the control back
       where it was. Without that notify() the screen would keep showing
       a change the database refused, which is the one state nobody can
       see is wrong. */
    async setAvailable(id, available) {
      try {
        reportWarning(await call(AVAIL_URL,
          postJson({ drink_id: Number(id), available: !!available })));
      } catch (error) {
        notify();
        throw error;
      }
      await load();
    },

    async setPrice(id, price) {
      try {
        reportWarning(await call(PRICE_URL,
          postJson({ drink_id: Number(id), price: String(price).trim() })));
      } catch (error) {
        notify();
        throw error;
      }
      await load();
    },

    /* ---------- the featured strip ----------
       Two writes, because they are two different things: which drinks
       are in the strip is a property of each drink, and whether the
       strip is drawn at all -- and where, and under what heading -- is a
       property of the customer screen. Keeping them apart is what lets
       an operator switch the whole module off for a day without losing
       the six drinks they picked for it. */
    featuredConfig() { return featuredSettings; },
    featuredMax() { return featuredCeiling; },

    /* The drinks currently in the strip, in menu order. Note this is
       every PICKED drink, including ones that cannot be sold right now:
       the admin panel has to show those, because "picked but not
       showing" is exactly the state an operator needs explaining. The
       customer screen holds them back -- see build_menu() in
       store_gui/sync_menu.py. */
    featuredItems() { return drinks.filter(item => item.featured); },

    async setFeatured(id, featured) {
      try {
        reportWarning(await call(FEATURED_URL,
          postJson({ drink_id: Number(id), featured: !!featured })));
      } catch (error) {
        // Same contract as setAvailable: the star has already moved in
        // the browser, so repainting from the untouched cache is what
        // puts it back where the database still has it.
        notify();
        throw error;
      }
      await load();
    },

    /* Sends all three settings every time, not a patch. They are one
       decision -- "how the strip appears" -- and a partial write would
       let a half-applied save leave the strip on with a position nobody
       chose. The server validates and normalises; what comes back is
       what the database now holds. */
    async saveFeaturedConfig(next) {
      const result = await call(FEATURED_CONFIG_URL, postJson({
        enabled: !!next.enabled,
        title: String(next.title == null ? '' : next.title),
        style: String(next.style || ''),
        columns: next.columns,
      }));
      reportWarning(result);
      await load();
      return result;
    },

    /* ---------- the bán-chạy strip ----------
       No per-drink write, because nobody picks these: the whole control
       surface is how far back to count and how many to keep. What the
       strip currently HOLDS comes back with every load, so the panel can
       show the ranking those settings actually produce rather than
       promising one. */
    bestsellerConfig() { return bestsellerSettings; },
    windowRange() { return windowRange; },
    countRange() { return countRange; },

    async saveBestsellerConfig(next) {
      const result = await call(BESTSELLER_CONFIG_URL, postJson({
        enabled: !!next.enabled,
        title: String(next.title == null ? '' : next.title),
        windowDays: next.windowDays,
        count: next.count,
        style: String(next.style || ''),
        columns: next.columns,
      }));
      reportWarning(result);
      await load();
      return result;
    },

    /* ---------- the order of the blocks on the store screen ----------
       Sent whole, never as "move this one up". The server validates the
       list as a set -- every block once, none invented, the menu
       present -- and a patch would make that check impossible: it could
       only ever see the move, not the layout the move produces. */
    layout() { return layoutOrder; },
    layoutBlocks() { return layoutBlocks; },
    featuredStyles() { return featuredStyles; },
    bestsellerStyles() { return bestsellerStyles; },
    columnStyles() { return columnStyles; },
    columnRange() { return columnRange; },

    async saveLayout(order) {
      const result = await call(LAYOUT_URL, postJson({ order }));
      reportWarning(result);
      await load();
      return result;
    },

    /* Moves the drink to the recycle bin. The row, its recipe and its
       categories all stay; every menu query simply stops returning it.
       See bin.html for the other half. */
    async deleteDrink(id) {
      const result = await call(DELETE_URL, postJson({ drink_id: Number(id) }));
      await load();
      return result;
    },

    /* Back onto the menu, switched off. */
    async restoreDrink(id) {
      const result = await call(RESTORE_URL, postJson({ drink_id: Number(id) }));
      await load();
      return result;
    },

    /* The one call in this console that really destroys something. Only
       works on a drink already in the bin. */
    async purgeDrink(id) {
      const result = await call(PURGE_URL, postJson({ drink_id: Number(id) }));
      await load();
      return result;
    },

    /* One drink's recipe, the ingredient list the editor offers, and the
       glasses and build methods it may be served in. editId null means
       "adding a new drink":
       no recipe, just the lists.

       Every field the editor needs has to be named here. This rebuilds the
       response rather than passing it through, so anything left out is
       dropped silently -- which is exactly how the glass picker came to
       render with only "— Chưa đặt —" in it while the API was returning
       all six glasses. */
    async getRecipeEditor(editId) {
      const query = editId == null ? '' : '?drink_id=' + Number(editId);
      const result = await call(EDITOR_URL + query, { cache: 'no-store' });
      return {
        recipes: result.recipes || [],
        ingredients: result.ingredients || [],
        glasses: result.glasses || [],
        drink_types: result.drink_types || [],
      };
    },

    /* Saves the drink and REPLACES its recipe. Safe to replace because
       the editor is shown every ingredient the recipe can hold — see
       editor_payload() in admin_gui/serve.py. */
    async saveRecipe(document) {
      const result = await call(RECIPE_URL, postJson(document));
      await load();
      return result;
    },

    /* Subscribing AFTER the first load has already landed still gets a
       call. The load starts when this file is evaluated and the pages
       subscribe further down their own scripts, so on a fast reply the
       notify() would otherwise fire into an empty listener list and the
       table would sit empty holding data it already had. */
    onChange(fn) {
      if (typeof fn !== 'function') return;
      listeners.push(fn);
      if (loaded) queueMicrotask(fn);
    },

    /* ---------- how the shop takes an order ----------
       Two switches, and they decide which buttons the CUSTOMER screen
       offers once an order is on the bill:

         printQR    "Print QR"                        the label path
         runDirect  "Start on the machine (no scan)"  straight to the machine

       Both on is how the machine has always behaved. One off hides that
       button. Both off is refused by the server, because an order screen
       with nothing to press is a shop that cannot sell -- see
       configuration/order_mode.py.

       THE PRESETS ARE A VIEW, NOT A SECOND SOURCE
           mode() derives its id from the switches rather than storing
           one. A stored mode number and two stored booleans are two
           things that can disagree, and the one that would be wrong is
           whichever the chip in the topbar happened to read. */
    MODES: {
      '1': { id:'1', name:'In QR + Chạy thẳng', short:'QR + Chạy thẳng',
             emoji:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="3.2"/><path d="M19.4 14.5a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-2.7 1.1V21a2 2 0 0 1-4 0v-.2a1.6 1.6 0 0 0-2.8-1.1l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.6 1.6 0 0 0-1.1-2.7H3a2 2 0 0 1 0-4h.2A1.6 1.6 0 0 0 4.3 7.4l-.1-.1a2 2 0 0 1 2.8-2.8l.1.1a1.6 1.6 0 0 0 1.8.3H9a1.6 1.6 0 0 0 1-1.5V3a2 2 0 0 1 4 0v.2a1.6 1.6 0 0 0 2.7 1.1l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0-.3 1.8V9a1.6 1.6 0 0 0 1.5 1H21a2 2 0 0 1 0 4h-.2a1.6 1.6 0 0 0-1.4 1Z"/></svg>',
             desc:'Cả hai nút. Bình thường in nhãn, máy in hỏng thì chạy thẳng.' },
      '3': { id:'3', name:'Chỉ in QR', short:'Chỉ QR',
             emoji:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M6 9V3h12v6"/><path d="M6 18H5a2 2 0 0 1-2-2v-4a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2h-1"/><rect x="7" y="14" width="10" height="7" rx="1"/></svg>',
             desc:'Chỉ in nhãn để quét. Máy in hỏng là phải vào đây đổi chế độ.' },
      '2': { id:'2', name:'Chỉ chạy thẳng', short:'Chạy thẳng',
             emoji:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M7 4.5 19 12 7 19.5Z"/></svg>',
             desc:'Gửi thẳng xuống máy, không in nhãn, không cần quét.' },
    },

    /* Answers from the cache, synchronously, so a render() at file scope
       has something to draw before any request could return -- the same
       contract cats() and allItems() keep. loadOrderMode() fires
       onChange() when the real answer lands.

       dryRun is NOT part of this. It is still browser-local because it
       still controls nothing: the real dry-run is the --dry-run argv flag
       run_flow is started with, which cannot be changed without
       restarting the service. It is returned here so the page that draws
       its switch keeps working, and the page says plainly that it is not
       wired up. */
    config() {
      let dryRun = false;
      try { dryRun = JSON.parse(localStorage.getItem(DRY_RUN_KEY)) === true; }
      catch { dryRun = false; }
      return { ...orderMode, dryRun };
    },

    /* Writes go to the server and the cache is refreshed from what the
       server ACCEPTED, never from what the page asked for -- so a refused
       change leaves the toggles showing the truth rather than the wish.
       Throws on refusal; the page shows the sentence.

       dryRun still goes to localStorage, see config(). */
    async setConfig(patch) {
      if ('dryRun' in patch) {
        try { localStorage.setItem(DRY_RUN_KEY, JSON.stringify(!!patch.dryRun)); }
        catch { /* a browser refusing storage is not worth failing over */ }
      }

      const wanted = { ...orderMode };
      if ('printQR' in patch) wanted.printQR = !!patch.printQR;
      if ('runDirect' in patch) wanted.runDirect = !!patch.runDirect;

      if (wanted.printQR !== orderMode.printQR ||
          wanted.runDirect !== orderMode.runDirect) {
        const result = await call(ORDER_MODE_URL, postJson(wanted));
        orderMode = { printQR: !!result.printQR,
                      runDirect: !!result.runDirect };
      }

      notify();
      return this.config();
    },

    mode() {
      if (orderMode.printQR && orderMode.runDirect) return '1';
      if (orderMode.printQR) return '3';
      return '2';
    },

    setMode(id) {
      const wanted = String(id);
      return this.setConfig({
        printQR:   wanted === '1' || wanted === '3',
        runDirect: wanted === '1' || wanted === '2',
      });
    },

    modeInfo() {
      const current = this.MODES[this.mode()];
      return { ...current, dryRun: this.config().dryRun };
    },
  };

  global.MenuStore = MenuStore;

  /* Start the first load immediately. The failure is reported through
     the same toast the pages use for everything else -- a blank table
     with a silent console error is the worst way to say "the database
     is not reachable". */
  /* Alongside the menu load below, not inside it: a page that only needs
     the mode chip should not wait on the drinks, and a menu that fails to
     load should not leave the chip lying about how the shop sells.
     Reported to the console alone -- the seeded value is the machine's
     historical behaviour, so the screen is still telling the truth about
     a machine nobody has reconfigured. */
  loadOrderMode().catch(error => console.error('[menu-store] order-mode', error));

  load().catch(error => {
    console.error('[menu-store]', error);
    if (typeof global.showToast === 'function') {
      global.showToast('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M10.3 3.9 1.8 18.1A2 2 0 0 0 3.5 21h17a2 2 0 0 0 1.7-2.9L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/></svg> ' + error.message, 'warn');
    }
  });
})(window);
