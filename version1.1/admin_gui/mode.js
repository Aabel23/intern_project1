/* ================================================================
   ADMIN-03 · OPERATION MODE
   Two switches deciding which buttons the CUSTOMER screen offers once an
   order is on the bill: "Print QR" and "Start on the machine (no scan)".
   The presets are the three useful combinations of them, not a fourth
   thing to keep in step -- MenuStore.mode() derives its id from the
   switches.

   IT IS REAL NOW
     Until 2026-09-07 this page wrote to localStorage and controlled
     nothing: the customer screen is a different browser, often a
     different device, and could never have read it. It writes to the
     server now -- configuration/order_mode.py -- and
     store_gui/drinks-pos.js draws its buttons from it.

     The dry-run switch below is the exception and still controls
     nothing. Real dry-run is the --dry-run flag run_flow is started
     with, which needs a service restart to change. The page says so.

   WHY BOTH OFF IS REFUSED
     By the server, not here, and it comes back as a sentence this page
     shows. An order screen with no button is a shop that cannot sell.
   ================================================================ */
if (!AdminAuth.initPage('mode')) { /* redirected to login */ }

const modesEl = document.getElementById('modes');
const $ = id => document.getElementById(id);

function render() {
  const c = MenuStore.config();
  $('tgStart').checked = c.runDirect;
  $('tgQR').checked = c.printQR;
  $('tgDry').checked = c.dryRun;

  const cur = MenuStore.mode();
  modesEl.innerHTML = Object.values(MenuStore.MODES).map(m => `
    <button class="mode ${m.id === cur ? 'active' : ''}" data-mode="${m.id}">
      <div class="check">${m.id === cur ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="m4.5 12.5 5 5L19.5 7"/></svg>' : ''}</div>
      <div class="ic">${m.emoji}</div>
      <div class="mno">${m.id === '0' ? 'Preset' : 'Mode ' + m.id}</div>
      <div class="mname">${m.name}</div><div class="mdesc">${m.desc}</div>
    </button>`).join('');
  // Same contract as the switches: the server decides, render() repaints
  // from what came back. A preset can never be the both-off combination,
  // so the catch here is for a server that is unreachable rather than one
  // that refuses.
  modesEl.querySelectorAll('.mode').forEach(el => el.onclick = async () => {
    const picked = el.dataset.mode;

    try {
      await MenuStore.setMode(picked);
      showToast(`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="3.2"/><path d="M19.4 14.5a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-2.7 1.1V21a2 2 0 0 1-4 0v-.2a1.6 1.6 0 0 0-2.8-1.1l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.6 1.6 0 0 0-1.1-2.7H3a2 2 0 0 1 0-4h.2A1.6 1.6 0 0 0 4.3 7.4l-.1-.1a2 2 0 0 1 2.8-2.8l.1.1a1.6 1.6 0 0 0 1.8.3H9a1.6 1.6 0 0 0 1-1.5V3a2 2 0 0 1 4 0v.2a1.6 1.6 0 0 0 2.7 1.1l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0-.3 1.8V9a1.6 1.6 0 0 0 1.5 1H21a2 2 0 0 1 0 4h-.2a1.6 1.6 0 0 0-1.4 1Z"/></svg> Đã chọn <b>${MenuStore.MODES[picked].name}</b>`, 'ok');
    } catch (error) {
      showToast('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M10.3 3.9 1.8 18.1A2 2 0 0 0 3.5 21h17a2 2 0 0 0 1.7-2.9L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/></svg> ' + error.message, 'warn');
    }

    render();
  });
}

/* The switch is not the truth -- the server is. So it goes back to
   whatever the server accepted, which is how a refused change (both
   switches off) leaves the toggle showing what the shop actually has
   rather than what the finger just asked for. render() reads the cache,
   and the cache only ever holds what came back. */
const SWITCH_KEY = { tgStart: 'runDirect', tgQR: 'printQR', tgDry: 'dryRun' };

Object.keys(SWITCH_KEY).forEach(id => {
  $(id).onchange = async e => {
    const key = SWITCH_KEY[id];

    // Down while the request is in flight: two toggles racing would have
    // the second one send a body built from a cache the first has not
    // finished updating.
    $(id).disabled = true;

    try {
      await MenuStore.setConfig({ [key]: e.target.checked });
      showToast('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="3.2"/><path d="M19.4 14.5a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-2.7 1.1V21a2 2 0 0 1-4 0v-.2a1.6 1.6 0 0 0-2.8-1.1l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.6 1.6 0 0 0-1.1-2.7H3a2 2 0 0 1 0-4h.2A1.6 1.6 0 0 0 4.3 7.4l-.1-.1a2 2 0 0 1 2.8-2.8l.1.1a1.6 1.6 0 0 0 1.8.3H9a1.6 1.6 0 0 0 1-1.5V3a2 2 0 0 1 4 0v.2a1.6 1.6 0 0 0 2.7 1.1l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0-.3 1.8V9a1.6 1.6 0 0 0 1.5 1H21a2 2 0 0 1 0 4h-.2a1.6 1.6 0 0 0-1.4 1Z"/></svg> Đã cập nhật chế độ vận hành', 'ok');
    } catch (error) {
      // The server's own sentence, shown as it came. The one that matters
      // is the both-off refusal, and it already explains itself better
      // than anything this page could add.
      showToast('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M10.3 3.9 1.8 18.1A2 2 0 0 0 3.5 21h17a2 2 0 0 0 1.7-2.9L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/></svg> ' + error.message, 'warn');
    } finally {
      $(id).disabled = false;
      render();
    }
  };
});

MenuStore.onChange(render);
render();
