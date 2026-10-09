"use strict";

/* ==========================================================================
   FlexMix — bartender guide SIMULATOR (auto-run model)
   --------------------------------------------------------------------------
   Execution model simulated here:

     - step_type "pump"    -> runs AUTOMATICALLY, no human input.
                              Pumps in the same step run in parallel.
     - step_type "manual"  -> STOPS. Waits for the bartender to confirm.
     - step_type "measure" -> STOPS. Waits for the bartender to confirm.

   After a confirm the machine continues automatically until the next gate.

   NOTE: this is NOT what order/current_recipe_executor.py does today — the
   real executor waits for a physical button press on every step, including
   pump steps. See the handover notes at the bottom of this file.
   ========================================================================== */

(function () {
  /* ------------------------------------------------------------------
     Everything below is supplied by configuration/gui_config.json via
     configure(). The defaults here only keep the module usable if the
     config fails to load.
     ------------------------------------------------------------------ */
  var CFG = null;
  var NAME_OF = {};       // ingredient id -> english name
  var PUMP_OF = {};       // ingredient id -> pump number
  var GRAM_PER_SEC = 10.5;
  var STEP_DELAY_MS = 1000;
  var TICK_MS = 100;
  var START_GATE = null;
  var DRINKS = [];

  /** Build the runtime tables from the shared config file. */
  function configure(cfg) {
    CFG = cfg;
    NAME_OF = {};
    PUMP_OF = {};

    Object.keys(cfg.ingredients).forEach(function (id) {
      var spec = cfg.ingredients[id];
      NAME_OF[id] = spec.name.en;
      if (spec.pump !== null && spec.pump !== undefined) PUMP_OF[id] = spec.pump;
    });

    GRAM_PER_SEC = cfg.ui.gram_per_sec_fallback || 10.5;
    STEP_DELAY_MS = cfg.ui.step_delay_ms != null ? cfg.ui.step_delay_ms : 1000;
    speed = cfg.ui.simulation_speed || 3;
    START_GATE = cfg.gates.start;

    // resolve each drink's steps into the shape the engine runs
    DRINKS = cfg.drinks.map(function (d) {
      return {
        drink_id: d.drink_id,
        name: d.name,
        image: d.image ? "../" + d.image : null,
        options: d.options || {},
        steps: d.steps.map(function (st) {
          if (st.type === "gate") return { gate: resolveGate(cfg, st.gate) };
          return {
            pump: st.pours.map(function (x) {
              return { ing: x.ingredient, gram: x.gram };
            })
          };
        })
      };
    });
  }

  /** Expand a gate definition, turning panel ids into labelled buttons. */
  function resolveGate(cfg, name) {
    var gate = JSON.parse(JSON.stringify(cfg.gates[name]));
    if (gate.buttons) {
      gate.buttons = gate.buttons.map(function (panel) {
        var meta = cfg.panel_buttons[String(panel)] || {};
        return { panel: panel, label: meta.label || { vi: String(panel), en: String(panel) } };
      });
    }
    return gate;
  }

  /* ---- state ------------------------------------------------------------ */
  let recipe = null;
  let timer = null;
  let speed = 3;
  let failNextStep = false;

  const now = () => new Date().toISOString().slice(0, 19);

  function buildRecipe(drink) {
    // The start gate always comes first; everything after it renumbers.
    const source = [{ gate: START_GATE }, ...drink.steps];

    const steps = source.map((raw, index) => {
      const stepNumber = index + 1;

      if (raw.gate) {
        // Deep copy: gate definitions are shared between orders, and a
        // hardware gate carries per-order LED state that must start clean.
        const gate = JSON.parse(JSON.stringify(raw.gate));
        (gate.buttons || []).forEach(b => {
          b.lit = false;
        });

        return {
          step_number: stepNumber,
          step_type: "manual",
          gate,
          pump_step: [],
          panel_ids: (gate.buttons || []).map(b => Number(b.panel)),
          status: "pending",
          error: null,
        };
      }

      const items = raw.pump.map(g => ({
        pump: PUMP_OF[g.ing],
        ingredient_id: g.ing,
        ingredient_name: NAME_OF[g.ing],
        base_gram: g.gram,
        gram: g.gram,
        poured_gram: 0,
        enabled: true,
        status: "pending",
        error: null,
      }));

      return {
        step_number: stepNumber,
        step_type: "pump",
        pump_step: items,
        panel_ids: items.map(i => i.pump).sort((a, b) => a - b),
        status: "pending",
        error: null,
      };
    });

    return {
      order_id: Math.random().toString(16).slice(2, 10) + Date.now().toString(16),
      protocol_version: "1.3",
      sku: drink.drink_id,
      drink_id: drink.drink_id,
      name: drink.name,
      image: drink.image,
      source_recipe_file: `recipe/${drink.name}.json`,
      options: drink.options || {},
      status: "running",
      current_step: null,
      error: null,
      created_at: now(),
      updated_at: now(),
      steps,
    };
  }

  /* ---- engine ------------------------------------------------------------ */

  // Every status that means "this step is not finished yet".
  // waiting_confirm MUST be here, otherwise a gate step would be stepped over
  // instead of blocking.
  var OPEN = new Set([
    "pending",
    "processing",
    "settling",          // finished, holding briefly before moving on
    "waiting_confirm",
    "waiting_button",
    "waiting_retry",
  ]);

  function currentStep(r) {
    if (!r) return null;
    return (
      r.steps
        .filter(s => OPEN.has(s.status))
        .sort((a, b) => a.step_number - b.step_number)[0] || null
    );
  }

  /** Begin the current step: pump steps start pouring, gates just wait. */
  function enterStep(step) {
    if (step.step_type === "pump") {
      step.status = "processing";
      step.started_at = now();
      step.pump_step.forEach(p => {
        p.status = "processing";
        p.poured_gram = 0;
      });
      recipe.status = "processing";
      recipe.current_step = step.step_number;
    } else if (String((step.gate || {}).release) === "hardware") {
      // The machine idles until one of the physical panel buttons is pressed.
      step.status = "waiting_button";
      step.panel_ids = (step.gate.buttons || []).map(b => Number(b.panel));
      recipe.status = "waiting_button";
      recipe.current_step = step.step_number;
    } else {
      // The machine idles until the operator confirms on screen.
      step.status = "waiting_confirm";
      recipe.status = "waiting_confirm";
      recipe.current_step = step.step_number;
    }
    recipe.updated_at = now();
  }

  /** Hold a finished step on screen for the settle pause before moving on. */
  function settleStep(step) {
    step.status = "settling";
    step.settle_until = Date.now() + STEP_DELAY_MS;
    recipe.status = "settling";
    recipe.updated_at = now();
  }

  function finishStep(step) {
    step.pump_step.forEach(p => {
      if (p.status === "processing") {
        p.status = "completed";
        p.poured_gram = p.gram;
        p.completed_at = now();
      }
    });
    settleStep(step);
  }

  /** 100 ms tick: advance pours, roll to the next step, stop at gates. */
  function tick() {
    if (!recipe) return;

    let step = currentStep(recipe);

    if (!step) {
      if (recipe.status !== "completed") {
        recipe.status = "completed";
        recipe.completed_at = now();
        recipe.current_step = null;
        recipe.updated_at = now();
      }
      return;
    }

    // A finished step lingers for the settle pause, then closes.
    if (step.status === "settling") {
      if (Date.now() < step.settle_until) return;
      step.status = "completed";
      step.completed_at = now();
      recipe.status = "processing";
      recipe.updated_at = now();
      return;
    }

    if (step.status === "pending") {
      enterStep(step);
      return;
    }

    // A gate blocks until confirm() or pressPanel() releases it.
    if (
      step.status === "waiting_confirm" ||
      step.status === "waiting_button" ||
      step.status === "waiting_retry"
    ) {
      return;
    }

    // A pump step in flight: add the grams delivered this tick.
    if (step.status === "processing" && step.step_type === "pump") {
      const delta = (GRAM_PER_SEC * speed * TICK_MS) / 1000;
      let allDone = true;

      step.pump_step.forEach(p => {
        if (p.status !== "processing") return;
        p.poured_gram = Math.min(p.gram, p.poured_gram + delta);
        if (p.poured_gram >= p.gram - 0.001) {
          p.poured_gram = p.gram;
          p.status = "completed";
          p.completed_at = now();
        } else {
          allDone = false;
        }
      });

      if (failNextStep) {
        failNextStep = false;
        const victim = step.pump_step.find(p => p.status === "processing")
          || step.pump_step[0];
        victim.status = "waiting_retry";
        victim.error = "Pump timeout: no flow detected";
        step.status = "waiting_retry";
        recipe.status = "waiting_retry";
        recipe.error = victim.error;
        recipe.updated_at = now();
        return;
      }

      if (allDone) finishStep(step);
      recipe.updated_at = now();
    }
  }

  function start() {
    if (timer) window.clearInterval(timer);
    timer = window.setInterval(tick, TICK_MS);
  }

  /* ---- public API -------------------------------------------------------- */

  window.FLEXMIX_SIM = {
    configure: configure,
    get drinks() { return DRINKS; },

    newOrder(drinkId) {
      if (!CFG) return null;   // configure() has not run yet
      const drink = DRINKS.find(d => d.drink_id === Number(drinkId)) || DRINKS[0];
      recipe = buildRecipe(drink);
      failNextStep = false;
      start();
      return recipe;
    },

    /** The bartender pressed the big CONFIRM button on screen. */
    confirm() {
      const step = currentStep(recipe);
      if (!step || step.status !== "waiting_confirm") return false;
      settleStep(step);
      return true;
    },

    /**
     * A physical panel button was pressed. On real hardware this arrives from
     * panel_control/panel.py via button_event_queue; here it is faked by
     * clicking a tile in the gate overlay.
     *
     * Each press latches that topping's LED on. Once EVERY LED in the step is
     * lit, the gate releases itself and the machine moves on with no further
     * operator action.
     */
    pressPanel(panelId) {
      const step = currentStep(recipe);
      if (!step || step.status !== "waiting_button") return false;

      const id = Number(panelId);
      const buttons = step.gate.buttons || [];
      const hit = buttons.find(b => Number(b.panel) === id);
      if (!hit || hit.lit) return false; // unknown button, or already latched

      hit.lit = true;
      hit.lit_at = now();
      recipe.updated_at = now();

      if (buttons.every(b => b.lit)) settleStep(step);
      return true;
    },

    /** Retry a failed pump step. */
    retry() {
      const step = currentStep(recipe);
      if (!step || step.status !== "waiting_retry") return false;
      step.pump_step.forEach(p => {
        if (p.status === "waiting_retry") {
          p.status = "processing";
          p.error = null;
        }
      });
      step.status = "processing";
      step.error = null;
      recipe.status = "processing";
      recipe.error = null;
      return true;
    },

    /** Operator tapped "next order": drop the finished drink, go idle. */
    clear() {
      recipe = null;
      if (timer) {
        window.clearInterval(timer);
        timer = null;
      }
    },

    failNext() {
      failNextStep = true;
    },

    setSpeed(value) {
      speed = Number(value) || 1;
    },

    gramPerSec: () => GRAM_PER_SEC * speed,
  };

  // Same contract gui/js/mixing-progress.js already understands.
  window.FLEXMIX_RECIPE_SOURCE = {
    simulated: true,
    read: async () => recipe,
  };
})();

/* ==========================================================================
   HANDOVER — what the Python side needs for this to run on real hardware
   --------------------------------------------------------------------------
   1. order/current_recipe_executor.py must auto-run pump steps instead of
      waiting for a button press. Today execute_current_recipe() blocks on
      button_event_queue for every step.

   2. While a pump step runs, the executor should write progress into
      current_recipe.json so this screen can show live meters. Either:
         a) write pump_step[i].poured_gram as it goes, or
         b) write step.started_at and let the GUI estimate from the calib
            values (this file's GUI already falls back to (b)).

   3. A gate step needs a new status the executor waits on, e.g.
      "waiting_confirm", released by an operator action rather than a pump.

   4. The confirm action needs a transport. Options:
         - POST /api/confirm on gui/api/server.py, which sets an Event, or
         - keep the physical panel button as the confirm, in which case the
           GUI is display-only and needs no write path at all.
   ========================================================================== */
