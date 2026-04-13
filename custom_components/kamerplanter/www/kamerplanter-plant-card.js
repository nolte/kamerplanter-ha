/**
 * kamerplanter-plant-card
 *
 * Custom Lovelace card for Kamerplanter plant instances and planting runs.
 * Shows phase timeline with Kami SVG illustrations, progress bar,
 * next-phase hint, and transition history table.
 *
 * This card merges the former kamerplanter-phase-card functionality
 * (progress bar, week/day tracking) into a single unified card.
 *
 * Follows: https://developers.home-assistant.io/docs/frontend/custom-ui/custom-card
 *
 * Config:
 *   device_id: string  (required — Kamerplanter plant/run device)
 *   title:     string  (optional — override device name)
 */

/* ================================================================== *
 *  Constants                                                          *
 * ================================================================== */

const KAMI_PHASE_SVG = {
  germination:         "/local/kami/timeline-kami-phase-germination.svg",
  seedling:            "/local/kami/timeline-kami-phase-seedling.svg",
  vegetative:          "/local/kami/timeline-kami-phase-vegetative.svg",
  flowering:           "/local/kami/timeline-kami-phase-flowering.svg",
  ripening:            "/local/kami/timeline-kami-phase-ripening.svg",
  harvest:             "/local/kami/timeline-kami-phase-harvest.svg",
  dormancy:            "/local/kami/timeline-kami-phase-dormancy.svg",
  juvenile:            "/local/kami/timeline-kami-phase-juvenile.svg",
  climbing:            "/local/kami/timeline-kami-phase-climbing.svg",
  mature:              "/local/kami/timeline-kami-phase-mature.svg",
  senescence:          "/local/kami/timeline-kami-phase-senescence.svg",
  flushing:            "/local/kami/timeline-kami-phase-flushing.svg",
  leaf_phase:          "/local/kami/timeline-kami-phase-leaf-phase.svg",
  short_day_induction: "/local/kami/timeline-kami-phase-short-day-induction.svg",
};

const PHASE_LABELS = {
  germination:         "Keimung",
  seedling:            "Sämling",
  vegetative:          "Vegetativ",
  flowering:           "Blüte",
  ripening:            "Reife",
  harvest:             "Ernte",
  dormancy:            "Ruhephase",
  flush:               "Spülphase",
  flushing:            "Spülung",
  drying:              "Trocknung",
  curing:              "Curing",
  leaf_phase:          "Blattphase",
  short_day_induction: "Kurztageinleitung",
  juvenile:            "Juvenil",
  climbing:            "Kletterphase",
  mature:              "Reifephase",
  senescence:          "Seneszenz",
};

const STANDARD_PHASES = [
  "germination", "seedling", "vegetative",
  "flowering", "ripening", "harvest",
];

const CHECK_SVG = '<svg viewBox="0 0 24 24"><path fill="currentColor" d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>';

/* ================================================================== *
 *  Helpers                                                            *
 * ================================================================== */

function escapeHtml(s) {
  const el = document.createElement("span");
  el.textContent = s || "";
  return el.innerHTML;
}

function capitalize(s) {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : "";
}

function phaseLabel(phase) {
  const key = (phase || "").toLowerCase();
  return PHASE_LABELS[key] || capitalize(phase);
}

function fmtDate(iso) {
  if (!iso) return "";
  const p = iso.split("-");
  return p.length >= 3 ? `${p[2]}.${p[1]}.${p[0]}` : iso;
}

function fmtDateShort(iso) {
  if (!iso) return "";
  const p = iso.split("-");
  return p.length >= 3 ? `${p[2]}.${p[1]}.` : iso;
}

function kamiSvg(phase) {
  return KAMI_PHASE_SVG[(phase || "").toLowerCase()] || null;
}

/* ================================================================== *
 *  CSS                                                                *
 * ================================================================== */

const CARD_STYLES = `
  /* ---- Host & Card ---- */
  :host {
    display: block;
    overflow: hidden;
    max-width: 100%;
    box-sizing: border-box;
    --kp-marker: 48px;
  }
  ha-card {
    overflow: hidden;
    max-width: 100%;
  }

  /* ---- Header ---- */
  .kp-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 16px 0;
    gap: 12px;
  }
  .kp-header__left {
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 0;
    flex: 1;
  }
  .kp-header__kami {
    width: 48px;
    height: 48px;
    flex-shrink: 0;
    object-fit: contain;
    border-radius: 10px;
  }
  .kp-header__icon {
    font-size: 1.6em;
    flex-shrink: 0;
    line-height: 1;
  }
  .kp-header__text {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }
  .kp-header__name {
    font-size: 1.15em;
    font-weight: 600;
    color: var(--primary-text-color);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .kp-header__plan {
    font-size: 0.78em;
    color: var(--secondary-text-color);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .kp-header__days {
    flex-shrink: 0;
    background: var(--primary-color, #4caf50);
    color: var(--text-primary-color, #fff);
    border-radius: 14px;
    padding: 6px 14px;
    font-size: 1.15em;
    font-weight: 700;
    line-height: 1.2;
  }
  .kp-header__days small {
    font-size: 0.6em;
    font-weight: 400;
    opacity: 0.85;
  }

  /* ---- Content ---- */
  .kp-content {
    padding: 12px 16px 16px;
    overflow: hidden;
    box-sizing: border-box;
  }

  /* ---- Progress bar ---- */
  .kp-progress {
    margin-bottom: 16px;
  }
  .kp-progress__header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 8px;
  }
  .kp-progress__phase {
    font-size: 1.05em;
    font-weight: 600;
    color: var(--primary-text-color);
  }
  .kp-progress__info {
    font-size: 0.9em;
    font-weight: 500;
    color: var(--secondary-text-color);
  }
  .kp-progress__track {
    width: 100%;
    height: 10px;
    background: var(--divider-color, #e0e0e0);
    border-radius: 5px;
    overflow: hidden;
  }
  .kp-progress__fill {
    height: 100%;
    border-radius: 5px;
    background: var(--primary-color, #4caf50);
    transition: width 0.5s ease;
  }
  .kp-progress__fill--indeterminate {
    width: 40%;
    animation: kp-progress-slide 1.8s ease-in-out infinite;
  }
  @keyframes kp-progress-slide {
    0%   { margin-left: 0;   opacity: 0.7; }
    50%  { margin-left: 60%; opacity: 1; }
    100% { margin-left: 0;   opacity: 0.7; }
  }
  .kp-progress__footer {
    display: flex;
    justify-content: space-between;
    margin-top: 6px;
  }
  .kp-progress__pct {
    font-size: 0.85em;
    font-weight: 600;
    color: var(--primary-color, #4caf50);
  }
  .kp-progress__remaining {
    font-size: 0.85em;
    color: var(--secondary-text-color);
  }

  /* ---- Timeline ---- */
  .kp-timeline-wrapper {
    position: relative;
    margin-bottom: 20px;
  }
  .kp-timeline-wrapper::after {
    content: "";
    position: absolute;
    top: 0;
    right: 0;
    width: 32px;
    height: 100%;
    background: linear-gradient(to right, transparent, var(--card-background-color, #fff));
    pointer-events: none;
    opacity: 0;
    transition: opacity 0.3s;
  }
  .kp-timeline-wrapper--scrollable::after {
    opacity: 1;
  }
  .kp-timeline-wrapper--scrolled-end::after {
    opacity: 0;
  }
  .kp-timeline {
    display: flex;
    align-items: flex-start;
    width: 100%;
    box-sizing: border-box;
    overflow-x: auto;
    overflow-y: hidden;
    scrollbar-width: none;       /* Firefox */
    -ms-overflow-style: none;    /* IE/Edge */
  }
  .kp-timeline::-webkit-scrollbar {
    display: none;               /* Chrome/Safari */
  }

  .kp-timeline__connector {
    flex: 1 1 0;
    min-width: 4px;
    height: 3px;
    margin-top: calc(var(--kp-marker) / 2);
    border-radius: 2px;
    background: var(--divider-color, #e0e0e0);
    transition: background 0.3s;
  }
  .kp-timeline__connector--done {
    background: var(--primary-color, #4caf50);
  }
  .kp-timeline__connector--active {
    background: linear-gradient(
      to right,
      var(--accent-color, #ff9800),
      var(--divider-color, #e0e0e0)
    );
  }

  /* ---- Step ---- */
  .kp-step {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    flex: 1 1 0;
    min-width: 0;
  }

  .kp-step__marker {
    width: var(--kp-marker);
    height: var(--kp-marker);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
  }
  .kp-step__marker svg {
    width: 40%;
    height: 40%;
  }
  .kp-step__marker--kami {
    background: none;
    border: none;
    border-radius: 14px;
    overflow: hidden;
  }
  .kp-step__marker--kami img {
    width: 100%;
    height: 100%;
    object-fit: contain;
    border-radius: 14px;
    display: block;
  }

  /* Step states */
  .kp-step--completed .kp-step__marker {
    background: var(--primary-color, #4caf50);
    color: var(--text-primary-color, #fff);
  }
  .kp-step--completed .kp-step__marker--kami {
    background: none;
    box-shadow: 0 0 0 3px var(--primary-color, #4caf50);
  }

  .kp-step--current .kp-step__marker {
    background: var(--accent-color, #ff9800);
    color: var(--text-primary-color, #fff);
    transform: scale(1.08);
    box-shadow: 0 0 0 4px rgba(255, 152, 0, 0.25);
  }
  .kp-step--current .kp-step__marker--kami {
    background: none;
    box-shadow:
      0 0 0 3px var(--accent-color, #ff9800),
      0 0 14px rgba(255, 152, 0, 0.3);
  }

  .kp-step--upcoming .kp-step__marker {
    background: transparent;
    border: 2px solid var(--divider-color, #ccc);
  }
  .kp-step--upcoming .kp-step__marker--kami {
    border: none;
    opacity: 0.35;
    filter: grayscale(80%);
  }

  .kp-step__pulse {
    width: 24%;
    height: 24%;
    border-radius: 50%;
    background: var(--text-primary-color, #fff);
    animation: kp-pulse 2s ease-in-out infinite;
  }
  @keyframes kp-pulse {
    0%, 100% { transform: scale(1); opacity: 1; }
    50% { transform: scale(1.3); opacity: 0.7; }
  }

  .kp-step__body {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1px;
    width: 100%;
  }
  .kp-step__name {
    font-size: max(0.72em, 11px);
    font-weight: 500;
    color: var(--secondary-text-color);
    text-align: center;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .kp-step--current .kp-step__name {
    font-weight: 700;
    color: var(--primary-text-color);
  }
  .kp-step--upcoming .kp-step__name {
    opacity: 0.6;
  }
  .kp-step__date,
  .kp-step__duration {
    font-size: max(0.65em, 10px);
    color: var(--secondary-text-color);
    opacity: 0.7;
  }
  .kp-step--current .kp-step__date {
    opacity: 1;
  }

  /* ---- Next-phase hint ---- */
  .kp-next {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    border-radius: 10px;
    background: var(--secondary-background-color, #f5f5f5);
    font-size: 0.88em;
    color: var(--primary-text-color);
    margin-bottom: 14px;
  }
  .kp-next--active {
    background: rgba(76, 175, 80, 0.12);
    border-left: 3px solid var(--primary-color, #4caf50);
  }
  .kp-next__kami {
    width: 28px;
    height: 28px;
    object-fit: contain;
    flex-shrink: 0;
    opacity: 0.7;
  }
  .kp-next__arrow {
    color: var(--primary-color, #4caf50);
    font-weight: 700;
    font-size: 1.1em;
  }

  /* ---- Detail table ---- */
  .kp-details {
    border-top: 1px solid var(--divider-color, #e0e0e0);
    padding-top: 12px;
  }
  .kp-details__header,
  .kp-details__row {
    display: grid;
    grid-template-columns: 1fr auto auto;
    gap: 8px;
    align-items: center;
  }
  .kp-details__header {
    padding-bottom: 6px;
    font-size: 0.7em;
    font-weight: 600;
    color: var(--secondary-text-color);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .kp-details__header span:nth-child(2),
  .kp-details__header span:nth-child(3) {
    text-align: right;
  }
  .kp-details__row {
    padding: 6px 0;
    font-size: 0.88em;
    border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  }
  .kp-details__row:last-child {
    border-bottom: none;
  }
  .kp-details__row--current {
    font-weight: 600;
    color: var(--primary-text-color);
  }
  .kp-details__phase {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--primary-text-color);
  }
  .kp-details__phase img {
    width: 24px;
    height: 24px;
    object-fit: contain;
    flex-shrink: 0;
    border-radius: 5px;
  }
  .kp-details__row--current .kp-details__phase::before {
    content: "";
    display: inline-block;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--accent-color, #ff9800);
    flex-shrink: 0;
  }
  .kp-details__date,
  .kp-details__days {
    color: var(--secondary-text-color);
    text-align: right;
  }
  .kp-details__date {
    min-width: 72px;
  }
  .kp-details__days {
    min-width: 36px;
  }

  /* ---- Stats row ---- */
  .kp-stats {
    display: flex;
    gap: 10px;
    margin-bottom: 16px;
  }
  .kp-stats__item {
    flex: 1 1 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    padding: 10px 6px;
    border-radius: 10px;
    background: var(--secondary-background-color, #f5f5f5);
  }
  .kp-stats__value {
    font-size: 1.5em;
    font-weight: 700;
    line-height: 1.2;
    color: var(--primary-text-color);
  }
  .kp-stats__unit {
    font-size: 0.55em;
    font-weight: 400;
    opacity: 0.7;
  }
  .kp-stats__label {
    font-size: 0.7em;
    color: var(--secondary-text-color);
    text-align: center;
    line-height: 1.2;
  }
  .kp-stats__item--harvest .kp-stats__value {
    color: var(--primary-color, #4caf50);
  }

  /* ---- Hidden override ---- */
  [hidden] {
    display: none !important;
  }

  /* ---- Empty / Error states ---- */
  .kp-empty {
    padding: 24px 16px;
    text-align: center;
    color: var(--secondary-text-color);
    font-size: 0.95em;
  }
  .kp-error {
    padding: 16px;
    color: var(--error-color, #db4437);
  }
`;

/**
 * ha-form ready singleton (UI-NFR-015 §2.2).
 */
const _haFormReadyPlant = (async () => {
  if (customElements.get("ha-form")) return;
  await customElements.whenDefined("hui-entities-card");
  const helpers = await window.loadCardHelpers?.();
  if (helpers) {
    const temp = await helpers.createCardElement({ type: "entities", entities: [] });
    if (temp?.constructor?.getConfigElement) await temp.constructor.getConfigElement();
  }
  await customElements.whenDefined("ha-form");
})();

/**
 * Build plant card editor schema.
 * Uses selector: { device: { integration: "kamerplanter" } } to filter
 * to Kamerplanter Plant Instance / Planting Run devices natively.
 */
const PLANT_CARD_SCHEMA = [
  { name: "device_id", label: "Pflanze / Planting Run", required: true,
    selector: { device: { integration: "kamerplanter" } } },
  { name: "title",     label: "Titel (optional)",
    selector: { text: {} } },
  { name: "show_progress",  label: "Fortschrittsbalken anzeigen",
    selector: { boolean: {} } },
  { name: "show_timeline",  label: "Phasen-Timeline anzeigen",
    selector: { boolean: {} } },
  { name: "show_next_hint", label: "Nächste-Phase-Hinweis anzeigen",
    selector: { boolean: {} } },
  { name: "show_stats",     label: "Wochen- & Ernte-Statistik anzeigen",
    selector: { boolean: {} } },
  { name: "show_details",   label: "Phasen-Historie anzeigen",
    selector: { boolean: {} } },
];

/* ================================================================== *
 *  Editor                                                             *
 * ================================================================== */

/**
 * Kamerplanter Plant Card Editor
 * Uses ha-form + schema — identical pattern to official HA card editors
 * (UI-NFR-015 §2.1). No Shadow DOM (UI-NFR-015 R-022).
 */
class KamerplanterPlantCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = {
      device_id: "", title: "",
      show_progress: true, show_timeline: true,
      show_stats: true, show_next_hint: true, show_details: true,
      ...config,
    };
    if (this._hass) this._scheduleRender();
  }

  set hass(hass) {
    this._hass = hass;
    this._scheduleRender();
  }

  async _scheduleRender() {
    await _haFormReadyPlant;
    this._render();
  }

  _render() {
    if (!this._config || !this._hass) return;

    // Create ha-form once; reuse on subsequent renders (UI-NFR-015 R-020)
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.addEventListener("value-changed", (e) => {
        this._config = e.detail.value;
        this.dispatchEvent(new CustomEvent("config-changed", {
          detail: { config: this._config },
          bubbles: true,
          composed: true,
        }));
      });
      this.appendChild(this._form);
    }

    this._form.hass = this._hass;
    this._form.schema = PLANT_CARD_SCHEMA;
    this._form.data = this._config;
    this._form.computeLabel = (schema) => schema.label || schema.name;
  }
}

customElements.define("kamerplanter-plant-card-editor", KamerplanterPlantCardEditor);

/* ================================================================== *
 *  Card                                                               *
 * ================================================================== */

class KamerplanterPlantCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._built = false;
  }

  connectedCallback() {
    if (this._config) this._update();
  }

  /* ---- Lifecycle (HA spec) ---------------------------------------- */

  static get CONFIG_DEFAULTS() {
    return {
      title: "",
      show_progress: true,
      show_timeline: true,
      show_stats: true,
      show_next_hint: true,
      show_details: true,
    };
  }

  setConfig(config) {
    this._isPreview = !!config.__preview;
    if (!this._isPreview && !config.device_id) {
      throw new Error("Bitte ein Device ausw\u00e4hlen");
    }
    this._config = { ...KamerplanterPlantCard.CONFIG_DEFAULTS, ...config };
    this._monitoredEntities = [];
  }

  set hass(hass) {
    // Collect monitored entities on first call
    if (this._monitoredEntities.length === 0 && hass) {
      this._monitoredEntities = Object.keys(hass.states).filter(
        id => id.startsWith("sensor.") || id.startsWith("binary_sensor.")
      );
    }

    // Change-detection: only re-render when own entities changed
    const changed = !this._hass || this._monitoredEntities.some(
      id => this._hass.states[id] !== hass.states[id]
    );
    this._hass = hass;
    if (changed) this._update();
  }

  _handleMoreInfo(entityId) {
    const event = new Event("hass-more-info", { bubbles: true, composed: true });
    event.detail = { entityId };
    this.dispatchEvent(event);
  }

  getCardSize() {
    let size = 2; // header always visible
    const c = this._config || {};
    if (c.show_stats !== false) size += 1;
    if (c.show_progress !== false) size += 2;
    if (c.show_timeline !== false) size += 2;
    if (c.show_next_hint !== false) size += 1;
    if (c.show_details !== false) size += 2;
    return size;
  }

  getGridOptions() {
    // Sections view: 12-column grid, 56px per row + 8px gap
    // Calculate rows from active sections
    let rows = 2; // header
    const c = this._config || {};
    if (c.show_stats !== false) rows += 1;
    if (c.show_progress !== false) rows += 2;
    if (c.show_timeline !== false) rows += 2;
    if (c.show_next_hint !== false) rows += 1;
    if (c.show_details !== false) rows += 2;
    return {
      columns: 12,
      min_columns: 6,
      rows: rows,
      min_rows: 2,
    };
  }

  static getConfigElement() {
    return document.createElement("kamerplanter-plant-card-editor");
  }

  static getStubConfig() {
    return { ...KamerplanterPlantCard.CONFIG_DEFAULTS, __preview: true, device_id: "" };
  }

  /* ---- Data ---------------------------------------------------- */

  /** Collect sensor states keyed by suffix (e.g. "phase", "phase_timeline"). */
  _getEntityMap() {
    const id = this._config.device_id;
    if (!id || !this._hass) return {};

    // Collect all entity_ids for this device to derive the common prefix.
    // Entity IDs follow: sensor.kp_{slug}_{suffix} where slug can contain
    // underscores (e.g. "canna_0321_e02"), so we cannot split with a simple regex.
    // Instead, find the common prefix from all entity_ids of this device.
    const deviceEnts = [];
    for (const ent of Object.values(this._hass.entities || {})) {
      if (ent.device_id !== id) continue;
      const eid = ent.entity_id;
      if (/^(?:sensor|binary_sensor)\.kp_/.test(eid)) {
        deviceEnts.push(ent);
      }
    }

    if (deviceEnts.length === 0) return {};

    // Derive common prefix: strip domain, find longest common prefix of the
    // object_id part (after "sensor." / "binary_sensor.").
    const objectIds = deviceEnts.map((e) => e.entity_id.replace(/^[^.]+\./, ""));
    let prefix = objectIds[0];
    for (let i = 1; i < objectIds.length; i++) {
      while (!objectIds[i].startsWith(prefix)) {
        // Remove last _segment from prefix
        const idx = prefix.lastIndexOf("_");
        if (idx <= 0) { prefix = ""; break; }
        prefix = prefix.substring(0, idx + 1); // keep trailing _
      }
      if (!prefix) break;
    }

    const map = {};
    for (const ent of deviceEnts) {
      const st = this._hass.states[ent.entity_id];
      if (!st) continue;
      const objId = ent.entity_id.replace(/^[^.]+\./, "");
      const suffix = prefix ? objId.substring(prefix.length) : objId;
      if (suffix) map[suffix] = st;
    }
    return map;
  }

  /** Resolve device display name. */
  _getDeviceName() {
    const id = this._config.device_id;
    if (!id || !this._hass) return null;
    const dev = Object.values(this._hass.devices || {}).find((d) => d.id === id);
    return dev ? dev.name_by_user || dev.name : null;
  }

  /** Build ordered phase list from timeline attributes + standard backfill. */
  _buildPhases(tAttrs, currentPhase) {
    const phases = [];
    for (const [key, val] of Object.entries(tAttrs)) {
      if (val && typeof val === "object" && "status" in val) {
        phases.push({ name: key, ...val });
      }
    }

    /* Append upcoming standard phases after the current one */
    const known = new Set(phases.map((p) => p.name.toLowerCase()));
    const cur = (currentPhase || "").toLowerCase();
    let past = false;
    for (const sp of STANDARD_PHASES) {
      if (sp === cur) { past = true; continue; }
      if (past && !known.has(sp)) {
        phases.push({ name: sp, status: "upcoming", started: null, date: null, days: null });
      }
    }
    return phases;
  }

  /* ---- DOM build & update --------------------------------------- */

  _ensureDom() {
    if (this._built) return;

    this.shadowRoot.innerHTML = `
      <style>${CARD_STYLES}</style>
      <ha-card>
        <div class="kp-header">
          <div class="kp-header__left">
            <span id="headerVisual"></span>
            <div class="kp-header__text">
              <span class="kp-header__name" id="plantName"></span>
              <span class="kp-header__plan" id="planBadge"></span>
            </div>
          </div>
          <div class="kp-header__days" id="daysBadge" hidden></div>
        </div>
        <div class="kp-content">
          <div class="kp-stats" id="stats" hidden></div>
          <div class="kp-progress" id="progress" hidden></div>
          <div class="kp-timeline-wrapper" id="timelineWrapper">
            <div class="kp-timeline" id="timeline"></div>
          </div>
          <div class="kp-next" id="nextHint" hidden></div>
          <div class="kp-details" id="details" hidden></div>
        </div>
      </ha-card>
    `;
    this._built = true;
  }

  /** Main update — reads sensors and patches DOM. */
  _renderPreview() {
    this._built = false;
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        ha-card { padding: 0; overflow: hidden; }
        .kp-header { display: flex; align-items: center; padding: 12px 16px; gap: 12px; }
        .kp-header__icon { font-size: 28px; }
        .kp-header__text { flex: 1; display: flex; flex-direction: column; min-width: 0; }
        .kp-header__name { font-size: 1rem; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .kp-header__plan { font-size: 0.75rem; padding: 2px 8px; border-radius: 10px; background: #e8f5e9; color: #2e7d32; font-weight: 600; width: fit-content; margin-top: 2px; }
        .kp-header__days { font-size: 1.3rem; font-weight: 700; color: var(--primary-color, #03a9f4); text-align: center; line-height: 1; }
        .kp-header__days small { font-size: 0.6em; font-weight: 500; }
        .kp-stats { display: flex; gap: 8px; padding: 0 16px 8px; }
        .kp-stats__item { flex: 1; text-align: center; padding: 6px 4px; border-radius: 8px; background: #f5f5f5; }
        .kp-stats__value { display: block; font-size: 1.1rem; font-weight: 700; }
        .kp-stats__value .kp-stats__unit { font-size: 0.7em; font-weight: 500; }
        .kp-stats__label { display: block; font-size: 0.65rem; color: #757575; text-transform: uppercase; letter-spacing: 0.03em; }
        .kp-stats__item--harvest { background: #fff3e0; }
        .kp-progress { padding: 0 16px 12px; }
        .kp-progress__header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
        .kp-progress__phase { font-weight: 600; font-size: 0.9rem; }
        .kp-progress__info { font-size: 0.8rem; color: #757575; }
        .kp-progress__track { height: 8px; border-radius: 4px; background: #e0e0e0; overflow: hidden; }
        .kp-progress__fill { height: 100%; border-radius: 4px; transition: width 0.4s; }
        .kp-progress__footer { display: flex; justify-content: space-between; margin-top: 4px; }
        .kp-progress__pct { font-size: 0.75rem; font-weight: 600; }
        .kp-progress__remain { font-size: 0.75rem; color: #757575; }
        .kp-timeline-wrapper { padding: 0 16px 12px; position: relative; }
        .kp-timeline { display: flex; gap: 0; overflow-x: auto; scrollbar-width: none; padding-bottom: 4px; }
        .kp-timeline::-webkit-scrollbar { display: none; }
        .kp-phase-pill { display: flex; flex-direction: column; align-items: center; gap: 2px; min-width: 60px; padding: 6px 8px; position: relative; }
        .kp-phase-pill__dot { width: 10px; height: 10px; border-radius: 50%; border: 2px solid; }
        .kp-phase-pill__dot--completed { background: var(--dot-color); border-color: var(--dot-color); }
        .kp-phase-pill__dot--current { background: #fff; border-color: var(--dot-color); box-shadow: 0 0 0 3px rgba(76,175,80,0.25); }
        .kp-phase-pill__dot--upcoming { background: #fff; border-color: #bdbdbd; }
        .kp-phase-pill__label { font-size: 0.65rem; text-align: center; white-space: nowrap; }
        .kp-phase-pill__days { font-size: 0.6rem; color: #9e9e9e; }
        .kp-phase-pill__line { position: absolute; top: 11px; left: -50%; right: 50%; height: 2px; z-index: -1; }
      </style>
      <ha-card>
        <div class="kp-header">
          <span class="kp-header__icon">\uD83C\uDF31</span>
          <div class="kp-header__text">
            <span class="kp-header__name">Northern Lights #03</span>
            <span class="kp-header__plan">GH Flora Bloom</span>
          </div>
          <div class="kp-header__days">28<small>d</small></div>
        </div>
        <div class="kp-stats">
          <div class="kp-stats__item"><span class="kp-stats__value">6</span><span class="kp-stats__label">Gesamtwoche</span></div>
          <div class="kp-stats__item"><span class="kp-stats__value">4</span><span class="kp-stats__label">Phasenwoche</span></div>
          <div class="kp-stats__item kp-stats__item--harvest"><span class="kp-stats__value">35<span class="kp-stats__unit">d</span></span><span class="kp-stats__label">bis Ernte</span></div>
        </div>
        <div class="kp-progress">
          <div class="kp-progress__header"><span class="kp-progress__phase">Bl\u00fcte</span><span class="kp-progress__info">Tag 28 / 63</span></div>
          <div class="kp-progress__track"><div class="kp-progress__fill" style="width:44%;background:#e91e63"></div></div>
          <div class="kp-progress__footer"><span class="kp-progress__pct">44%</span><span class="kp-progress__remain">35 Tage verbleibend</span></div>
        </div>
        <div class="kp-timeline-wrapper">
          <div class="kp-timeline">
            <div class="kp-phase-pill"><div class="kp-phase-pill__dot kp-phase-pill__dot--completed" style="--dot-color:#795548"></div><span class="kp-phase-pill__label">Keimung</span><span class="kp-phase-pill__days">5d</span></div>
            <div class="kp-phase-pill"><div class="kp-phase-pill__line" style="background:#8bc34a"></div><div class="kp-phase-pill__dot kp-phase-pill__dot--completed" style="--dot-color:#8bc34a"></div><span class="kp-phase-pill__label">Setzling</span><span class="kp-phase-pill__days">10d</span></div>
            <div class="kp-phase-pill"><div class="kp-phase-pill__line" style="background:#4caf50"></div><div class="kp-phase-pill__dot kp-phase-pill__dot--completed" style="--dot-color:#4caf50"></div><span class="kp-phase-pill__label">Vegetativ</span><span class="kp-phase-pill__days">14d</span></div>
            <div class="kp-phase-pill"><div class="kp-phase-pill__line" style="background:#e91e63"></div><div class="kp-phase-pill__dot kp-phase-pill__dot--current" style="--dot-color:#e91e63"></div><span class="kp-phase-pill__label">Bl\u00fcte</span><span class="kp-phase-pill__days">28d</span></div>
            <div class="kp-phase-pill"><div class="kp-phase-pill__line" style="background:#bdbdbd"></div><div class="kp-phase-pill__dot kp-phase-pill__dot--upcoming" style="--dot-color:#bdbdbd"></div><span class="kp-phase-pill__label">Ernte</span><span class="kp-phase-pill__days">\u2014</span></div>
          </div>
        </div>
      </ha-card>
    `;
  }

  _update() {
    if (!this._config) return;
    if (this._isPreview) {
      this._renderPreview();
      return;
    }
    if (!this._hass || !this._config.device_id) return;

    const ents = this._getEntityMap();

    if (Object.keys(ents).length === 0) {
      this.shadowRoot.innerHTML = `
        <style>${CARD_STYLES}</style>
        <ha-card><div class="kp-error">Device nicht gefunden oder keine Entities</div></ha-card>
      `;
      this._built = false;
      return;
    }

    this._ensureDom();
    const $ = (id) => this.shadowRoot.getElementById(id);

    /* Read sensors */
    const timelineObj  = ents["phase_timeline"];
    const phaseObj     = ents["phase"] || ents["status"];
    const nextPhaseObj = ents["next_phase"];
    const nutrientObj  = ents["nutrient_plan"];
    const daysObj      = ents["days_in_phase"];
    const tAttrs       = timelineObj ? timelineObj.attributes : {};

    const currentPhase = phaseObj?.state
      || tAttrs.current_phase_name
      || (timelineObj ? timelineObj.state : null)
      || "\u2014";
    const nextPhase    = nextPhaseObj?.state;
    const daysInPhase  = tAttrs.days_in_phase ?? daysObj?.state;
    const nutrientPlan = nutrientObj?.state;
    const plantName    = this._config.title || this._getDeviceName() || "Pflanze";

    /* Header */
    const headerSvg = kamiSvg(currentPhase);
    $("headerVisual").innerHTML = headerSvg
      ? `<img class="kp-header__kami" src="${headerSvg}" alt="${escapeHtml(currentPhase)}" />`
      : `<span class="kp-header__icon">\uD83C\uDF31</span>`;

    $("plantName").textContent = plantName;

    const planEl = $("planBadge");
    if (nutrientPlan && nutrientPlan !== "None" && nutrientPlan !== "unknown") {
      planEl.textContent = nutrientPlan;
      planEl.hidden = false;
    } else {
      planEl.hidden = true;
    }

    const daysEl = $("daysBadge");
    if (daysInPhase != null && daysInPhase !== "unknown") {
      daysEl.innerHTML = `${escapeHtml(String(daysInPhase))}<small>d</small>`;
      daysEl.hidden = false;
    } else {
      daysEl.hidden = true;
    }

    /* Stats row */
    const statsEl = $("stats");
    if (this._config.show_stats) {
      const overallWeek = tAttrs.overall_week;
      const phaseWeek = tAttrs.phase_week;
      const daysToHarvest = tAttrs.days_to_harvest;

      if (overallWeek != null || phaseWeek != null || daysToHarvest != null) {
        statsEl.innerHTML = this._renderStats(overallWeek, phaseWeek, daysToHarvest);
        statsEl.hidden = false;
      } else {
        statsEl.hidden = true;
      }
    } else {
      statsEl.hidden = true;
    }

    /* Progress bar */
    const progressEl = $("progress");
    if (this._config.show_progress) {
      const progressHtml = this._renderProgress(tAttrs, currentPhase);
      if (progressHtml) {
        progressEl.innerHTML = progressHtml;
        progressEl.hidden = false;
      } else {
        progressEl.hidden = true;
      }
    } else {
      progressEl.hidden = true;
    }

    /* Timeline */
    const phases = this._buildPhases(tAttrs, currentPhase);
    const timelineEl = $("timeline");
    const wrapperEl = $("timelineWrapper");
    if (this._config.show_timeline) {
      timelineEl.innerHTML = this._renderTimeline(phases);
      wrapperEl.hidden = false;
      this._setupScrollFade(timelineEl, wrapperEl);
    } else {
      timelineEl.innerHTML = "";
      wrapperEl.hidden = true;
    }

    /* Next phase hint */
    const nextEl = $("nextHint");
    if (this._config.show_next_hint) {
      const nextHintHtml = this._renderNextHint(tAttrs, nextPhase);
      if (nextHintHtml) {
        nextEl.innerHTML = nextHintHtml;
        nextEl.className = "kp-next" + (tAttrs.weeks_until_next_phase === 0 ? " kp-next--active" : "");
        nextEl.hidden = false;
      } else {
        nextEl.hidden = true;
      }
    } else {
      nextEl.hidden = true;
    }

    /* Detail table */
    const detailEl = $("details");
    if (this._config.show_details) {
      const recorded = phases.filter((p) => p.status === "completed" || p.status === "current");
      if (recorded.length > 0) {
        detailEl.innerHTML = this._renderDetails(recorded);
        detailEl.hidden = false;
      } else {
        detailEl.hidden = true;
      }
    } else {
      detailEl.hidden = true;
    }
  }

  /* ---- Partial renderers ---------------------------------------- */

  /** Detect timeline overflow and toggle scroll-fade indicator. */
  _setupScrollFade(timelineEl, wrapperEl) {
    requestAnimationFrame(() => {
      const isScrollable = timelineEl.scrollWidth > timelineEl.clientWidth + 2;
      wrapperEl.classList.toggle("kp-timeline-wrapper--scrollable", isScrollable);
      wrapperEl.classList.remove("kp-timeline-wrapper--scrolled-end");

      if (isScrollable && !timelineEl._kpScrollHandler) {
        timelineEl._kpScrollHandler = () => {
          const atEnd = timelineEl.scrollLeft + timelineEl.clientWidth >= timelineEl.scrollWidth - 4;
          wrapperEl.classList.toggle("kp-timeline-wrapper--scrolled-end", atEnd);
        };
        timelineEl.addEventListener("scroll", timelineEl._kpScrollHandler, { passive: true });
      }
    });
  }

  /** Render stats row with 3 KPI tiles. */
  _renderStats(overallWeek, phaseWeek, daysToHarvest) {
    let html = "";

    if (overallWeek != null) {
      html += `
        <div class="kp-stats__item">
          <span class="kp-stats__value">${overallWeek}</span>
          <span class="kp-stats__label">Gesamtwoche</span>
        </div>`;
    }

    if (phaseWeek != null) {
      html += `
        <div class="kp-stats__item">
          <span class="kp-stats__value">${phaseWeek}</span>
          <span class="kp-stats__label">Phasenwoche</span>
        </div>`;
    }

    if (daysToHarvest != null) {
      html += `
        <div class="kp-stats__item kp-stats__item--harvest">
          <span class="kp-stats__value">${daysToHarvest}<span class="kp-stats__unit">d</span></span>
          <span class="kp-stats__label">bis Ernte</span>
        </div>`;
    }

    return html;
  }

  /** Render progress bar if week/day data is available. Returns HTML string or null. */
  _renderProgress(tAttrs, currentPhase) {
    const phaseWeek = tAttrs.phase_week;
    const plannedWeeks = tAttrs.phase_planned_weeks;
    const progressPct = tAttrs.phase_progress_pct;
    const daysInPhase = tAttrs.days_in_phase;
    const typicalDays = tAttrs.typical_duration_days;
    const remainingDays = tAttrs.remaining_days;
    const remainingWeeks = tAttrs.phase_remaining_weeks;

    // Full progress mode: plan-based week/percentage data available
    if (phaseWeek != null && plannedWeeks != null && plannedWeeks > 0) {
      const pct = Math.min(100, progressPct || 0);
      const infoText = daysInPhase != null
        ? `Tag ${daysInPhase} / ${typicalDays || "?"}`
        : `Woche ${phaseWeek} / ${plannedWeeks}`;
      const remainText = remainingDays != null
        ? `${remainingDays} ${remainingDays === 1 ? "Tag" : "Tage"} verbleibend`
        : remainingWeeks != null
          ? `${remainingWeeks} ${remainingWeeks === 1 ? "Woche" : "Wochen"} verbleibend`
          : "";

      return `
        <div class="kp-progress__header">
          <span class="kp-progress__phase">${escapeHtml(phaseLabel(currentPhase))}</span>
          <span class="kp-progress__info">${infoText}</span>
        </div>
        <div class="kp-progress__track">
          <div class="kp-progress__fill" style="width:${pct}%"></div>
        </div>
        <div class="kp-progress__footer">
          <span class="kp-progress__pct">${pct}%</span>
          ${remainText ? `<span class="kp-progress__remaining">${remainText}</span>` : ""}
        </div>
      `;
    }

    // Fallback mode: only days_in_phase available (no plan data)
    if (daysInPhase != null) {
      const weeks = Math.floor(daysInPhase / 7);
      const daysMod = daysInPhase % 7;
      const durationText = weeks > 0
        ? `${weeks} ${weeks === 1 ? "Woche" : "Wochen"}, ${daysMod} ${daysMod === 1 ? "Tag" : "Tage"}`
        : `${daysInPhase} ${daysInPhase === 1 ? "Tag" : "Tage"}`;

      return `
        <div class="kp-progress__header">
          <span class="kp-progress__phase">${escapeHtml(phaseLabel(currentPhase))}</span>
          <span class="kp-progress__info">Tag ${daysInPhase}</span>
        </div>
        <div class="kp-progress__track">
          <div class="kp-progress__fill kp-progress__fill--indeterminate"></div>
        </div>
        <div class="kp-progress__footer">
          <span class="kp-progress__remaining">${durationText} in dieser Phase</span>
        </div>
      `;
    }

    return null;
  }

  /** Render next-phase hint. Returns HTML string or null. */
  _renderNextHint(tAttrs, nextPhase) {
    /* Prefer plan-based next phase with week countdown */
    const nextPlanPhase = tAttrs.next_plan_phase;
    const nextPhaseWeeks = tAttrs.next_plan_phase_weeks;
    const weeksUntilNext = tAttrs.weeks_until_next_phase;

    if (nextPlanPhase != null && weeksUntilNext != null) {
      const label = phaseLabel(nextPlanPhase);
      const nKami = kamiSvg(nextPlanPhase);
      const kamiImg = nKami
        ? `<img class="kp-next__kami" src="${nKami}" alt="" />`
        : `<span class="kp-next__arrow">\u2192</span>`;

      if (weeksUntilNext === 0) {
        return `${kamiImg}<span><strong>${escapeHtml(label)}</strong> hat begonnen (${nextPhaseWeeks} ${nextPhaseWeeks === 1 ? "Woche" : "Wochen"})</span>`;
      }
      return `${kamiImg}<span><strong>${escapeHtml(label)}</strong> in ${weeksUntilNext} ${weeksUntilNext === 1 ? "Woche" : "Wochen"}</span>`;
    }

    /* Fallback: simple next_phase sensor */
    if (nextPhase && nextPhase !== "None" && nextPhase !== "unknown") {
      const label = phaseLabel(nextPhase);
      const nSvg = kamiSvg(nextPhase);
      const visual = nSvg
        ? `<img class="kp-next__kami" src="${nSvg}" alt="" />`
        : `<span class="kp-next__arrow">\u2192</span>`;
      return `${visual}<span>N\u00e4chste Phase: <strong>${escapeHtml(label)}</strong></span>`;
    }

    return null;
  }

  _renderTimeline(phases) {
    if (phases.length === 0) return "";
    let html = "";
    for (let i = 0; i < phases.length; i++) {
      const p = phases[i];
      const state = p.status === "completed" ? "completed"
        : p.status === "current" ? "current"
        : "upcoming";

      /* Connector */
      if (i > 0) {
        const prev = phases[i - 1].status;
        const cls = prev === "completed" ? "kp-timeline__connector--done"
          : prev === "current" ? "kp-timeline__connector--active"
          : "";
        html += `<div class="kp-timeline__connector ${cls}"></div>`;
      }

      /* Marker content */
      const svg = kamiSvg(p.name);
      let marker = "";
      if (svg) {
        marker = `<img src="${svg}" alt="${escapeHtml(p.name)}" />`;
      } else if (state === "completed") {
        marker = CHECK_SVG;
      } else if (state === "current") {
        marker = `<div class="kp-step__pulse"></div>`;
      }

      const dateStr = p.started || p.date || "";

      html += `
        <div class="kp-step kp-step--${state}">
          <div class="kp-step__marker${svg ? " kp-step__marker--kami" : ""}">
            ${marker}
          </div>
          <div class="kp-step__body">
            <span class="kp-step__name">${escapeHtml(phaseLabel(p.name))}</span>
            ${dateStr ? `<span class="kp-step__date">${fmtDateShort(dateStr)}</span>` : ""}
            ${p.days != null ? `<span class="kp-step__duration">${p.days}d</span>` : ""}
          </div>
        </div>
      `;
    }
    return html;
  }

  _renderDetails(recorded) {
    let rows = "";
    for (const p of recorded) {
      const isCur = p.status === "current";
      const svg = kamiSvg(p.name);
      rows += `
        <div class="kp-details__row${isCur ? " kp-details__row--current" : ""}">
          <span class="kp-details__phase">
            ${svg ? `<img src="${svg}" alt="" />` : ""}
            ${escapeHtml(phaseLabel(p.name))}
          </span>
          <span class="kp-details__date">${fmtDate(p.started || p.date || "")}</span>
          <span class="kp-details__days">${p.days != null ? `${p.days}d` : "\u2014"}</span>
        </div>
      `;
    }
    return `
      <div class="kp-details__header">
        <span>Phase</span><span>Start</span><span>Dauer</span>
      </div>
      ${rows}
    `;
  }
}

customElements.define("kamerplanter-plant-card", KamerplanterPlantCard);

/* ================================================================== *
 *  Card Registration                                                  *
 * ================================================================== */

window.customCards = window.customCards || [];
window.customCards.push({
  type: "kamerplanter-plant-card",
  name: "Kamerplanter Pflanze",
  description: "Zeigt Phasen\u00fcberg\u00e4nge, Fortschritt und Historie mit Kami-Illustrationen f\u00fcr Pflanzeninstanzen und Planting Runs",
  preview: true,
  documentationURL: "https://kamerplanter.readthedocs.io/de/latest/guides/home-assistant-integration/",
});
