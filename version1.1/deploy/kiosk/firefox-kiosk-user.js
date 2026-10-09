// Firefox kiosk hardening for the store screen.
//
// WHY THIS FILE EXISTS
//     Chromium took its kiosk rules as command-line flags: --incognito,
//     --disable-pinch, --overscroll-history-navigation=0 and the rest.
//     Firefox has --kiosk and --private-window and nothing else. Every
//     other rule is a preference, and preferences live in a profile.
//
// WHERE IT GOES
//     Into the snap profile as user.js, then restart Firefox:
//
//       cp firefox-kiosk-user.js \
//          ~/snap/firefox/common/.mozilla/firefox/*.default/user.js
//
//     user.js and not prefs.js: Firefox rewrites prefs.js as it runs and
//     would lose anything hand-edited there. user.js is re-applied on
//     every start, so these survive whatever the browser does to itself.
//
// WHY FIREFOX AT ALL
//     Chromium drained this Pi's 320 MB CMA pool to zero every 990
//     seconds and killed its own renderer -- 99 crashes in 29 hours,
//     each exactly 1040 seconds after the last. Firefox on the same
//     machine, same page, same screen ran 83 minutes with CmaFree
//     oscillating between 147 and 207 MB and recovering. See
//     deploy/kiosk/README.md section 8.

// ---- no way out with a finger ----
// Two-finger pinch zoom on the touch screen. Chromium had --disable-pinch.
user_pref("apz.allow_zooming", false);
user_pref("apz.allow_double_tap_zooming", false);

// Swipe in from the screen edge to go back or forward. Chromium had
// --overscroll-history-navigation=0. Empty string means "do nothing".
user_pref("browser.gesture.swipe.left", "");
user_pref("browser.gesture.swipe.right", "");
user_pref("widget.disable-swipe-tracker", true);

// Ctrl+scroll and Ctrl+plus zoom, for the day somebody plugs a keyboard
// in to do maintenance and forgets to unplug it.
user_pref("mousewheel.with_control.action", 0);
user_pref("zoom.maxPercent", 100);
user_pref("zoom.minPercent", 100);

// ---- nothing on top of the menu ----
// The watchdog restarts this browser by design. Without these, the next
// customer is handed a "restore your tabs?" bar across the drinks menu.
user_pref("browser.sessionstore.resume_from_crash", false);
user_pref("browser.sessionstore.max_resumed_crashes", 0);
user_pref("toolkit.startup.max_resumed_crashes", -1);

// First-run tour, welcome page, "make Firefox your default?", and the
// data-collection notice. Every one of them would cover the screen, and
// there is nobody standing there to dismiss it.
user_pref("browser.aboutwelcome.enabled", false);
user_pref("browser.startup.homepage_override.mstone", "ignore");
user_pref("browser.shell.checkDefaultBrowser", false);
user_pref("datareporting.policy.dataSubmissionEnabled", false);
user_pref("datareporting.healthreport.uploadEnabled", false);
user_pref("browser.discovery.enabled", false);

// The "... is now full screen" banner. --kiosk is already full screen;
// the banner is only something for the customer to wonder about.
user_pref("full-screen-api.warning.timeout", 0);
user_pref("full-screen-api.warning.delay", -1);

// ---- nothing remembered between customers ----
// --private-window covers most of this. These are here so a launch that
// forgets that flag still does not start collecting customers' details.
user_pref("signon.rememberSignons", false);
user_pref("browser.formfill.enable", false);

// ---- nothing that reaches out on its own ----
// snapd updates this browser, not Firefox, and an update prompt on a
// kiosk is a dialog nobody will ever click.
user_pref("app.update.auto", false);
user_pref("app.update.enabled", false);
user_pref("extensions.update.enabled", false);

// The page is served from localhost. Safe-browsing lookups go to Google
// on a machine that may have no route out, and only add a timeout to
// every navigation between the store and bartender screens.
user_pref("browser.safebrowsing.malware.enabled", false);
user_pref("browser.safebrowsing.phishing.enabled", false);

// The menu never changes between customers, so let its images come back
// from cache when the watchdog cycles the browser rather than being
// re-fetched every time.
user_pref("browser.cache.disk.enable", true);
