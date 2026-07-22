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

import {
  KamerplanterCardEditor,
  capitalize,
  escapeAttr,
  escapeHtml,
  getDeviceName,
  getEntityMap,
  kamiSvg,
  pickLang,
  safeNum,
  t,
} from "./kamerplanter-card-common.js";

/* ================================================================== *
 *  Constants                                                          *
 * ================================================================== */

const STANDARD_PHASES = [
  "germination", "seedling", "vegetative",
  "flowering", "ripening", "harvest",
];

const CHECK_SVG = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>';

/* ================================================================== *
 *  i18n (WP-16 — card-local de/en catalogs)                          *
 * ================================================================== */

/**
 * Card-lokaler Uebersetzungskatalog (de/en). Ersetzt alle frueher hart in der
 * Card kodierten deutschen UI-Strings. Uebersetzt via ``t(CATALOG, key, hass)``
 * aus dem gemeinsamen Modul; ``{0}``/``{1}`` sind Positions-Platzhalter.
 *
 * Die Phase-Labels liegen hier zweisprachig vor: das common-Modul liefert nur
 * deutsche Labels via ``phaseLabel()`` — englische HA-Nutzer brauchen englische
 * Phasen-Bezeichnungen, daher der card-lokale Katalog + ``phaseLabelI18n()``.
 */
const CATALOG = {
  de: {
    error_no_device: "Kein Gerät konfiguriert",
    error_not_found: "Gerät nicht gefunden oder keine Entitäten",
    loading: "Wird geladen …",
    default_plant_name: "Pflanze",
    stat_overall_week: "Gesamtwoche",
    stat_phase_week: "Phasenwoche",
    stat_to_harvest: "bis Ernte",
    day_of: "Tag {0} / {1}",
    week_of: "Woche {0} / {1}",
    day_n: "Tag {0}",
    days_remaining_one: "{0} Tag verbleibend",
    days_remaining_other: "{0} Tage verbleibend",
    weeks_remaining_one: "{0} Woche verbleibend",
    weeks_remaining_other: "{0} Wochen verbleibend",
    week_one: "{0} Woche",
    week_other: "{0} Wochen",
    day_one: "{0} Tag",
    day_other: "{0} Tage",
    duration_weeks_days: "{0}, {1}",
    in_this_phase: "{0} in dieser Phase",
    has_begun: "hat begonnen ({0})",
    in_weeks: "in {0}",
    next_phase_label: "Nächste Phase:",
    details_col_phase: "Phase",
    details_col_start: "Start",
    details_col_duration: "Dauer",
    aria_progress: "Phasenfortschritt",
    editor_device: "Pflanze / Planting Run",
    editor_title: "Titel (optional)",
    editor_show_progress: "Fortschrittsbalken anzeigen",
    editor_show_timeline: "Phasen-Timeline anzeigen",
    editor_show_next_hint: "Nächste-Phase-Hinweis anzeigen",
    editor_show_stats: "Wochen- & Ernte-Statistik anzeigen",
    editor_show_details: "Phasen-Historie anzeigen",
    // Phase-Labels (spiegelt PHASE_LABELS im common-Modul in korrektem UTF-8)
    phase_germination: "Keimung",
    phase_seedling: "Sämling",
    phase_vegetative: "Vegetativ",
    phase_flowering: "Blüte",
    phase_ripening: "Reife",
    phase_harvest: "Ernte",
    phase_dormancy: "Ruhephase",
    phase_flush: "Spülphase",
    phase_flushing: "Spülung",
    phase_drying: "Trocknung",
    phase_curing: "Curing",
    phase_leaf_phase: "Blattphase",
    phase_short_day_induction: "Kurztageinleitung",
    phase_juvenile: "Juvenil",
    phase_climbing: "Kletterphase",
    phase_mature: "Reifephase",
    phase_senescence: "Seneszenz",
  },
  en: {
    error_no_device: "No device configured",
    error_not_found: "Device not found or no entities",
    loading: "Loading …",
    default_plant_name: "Plant",
    stat_overall_week: "Overall week",
    stat_phase_week: "Phase week",
    stat_to_harvest: "until harvest",
    day_of: "Day {0} / {1}",
    week_of: "Week {0} / {1}",
    day_n: "Day {0}",
    days_remaining_one: "{0} day remaining",
    days_remaining_other: "{0} days remaining",
    weeks_remaining_one: "{0} week remaining",
    weeks_remaining_other: "{0} weeks remaining",
    week_one: "{0} week",
    week_other: "{0} weeks",
    day_one: "{0} day",
    day_other: "{0} days",
    duration_weeks_days: "{0}, {1}",
    in_this_phase: "{0} in this phase",
    has_begun: "has begun ({0})",
    in_weeks: "in {0}",
    next_phase_label: "Next phase:",
    details_col_phase: "Phase",
    details_col_start: "Start",
    details_col_duration: "Duration",
    aria_progress: "Phase progress",
    editor_device: "Plant / planting run",
    editor_title: "Title (optional)",
    editor_show_progress: "Show progress bar",
    editor_show_timeline: "Show phase timeline",
    editor_show_next_hint: "Show next-phase hint",
    editor_show_stats: "Show week & harvest stats",
    editor_show_details: "Show phase history",
    phase_germination: "Germination",
    phase_seedling: "Seedling",
    phase_vegetative: "Vegetative",
    phase_flowering: "Flowering",
    phase_ripening: "Ripening",
    phase_harvest: "Harvest",
    phase_dormancy: "Dormancy",
    phase_flush: "Flush",
    phase_flushing: "Flushing",
    phase_drying: "Drying",
    phase_curing: "Curing",
    phase_leaf_phase: "Leaf phase",
    phase_short_day_induction: "Short-day induction",
    phase_juvenile: "Juvenile",
    phase_climbing: "Climbing",
    phase_mature: "Mature",
    phase_senescence: "Senescence",
  },
};

/**
 * Localized phase label for the current HA language. Falls back to a
 * capitalized raw code for phases missing from the catalog; em-dash for empty.
 */
function phaseLabelI18n(phase, hass) {
  if (!phase) return "—";
  const key = String(phase).toLowerCase();
  const table = CATALOG[pickLang(hass)] || CATALOG.en;
  return table["phase_" + key] || capitalize(String(phase));
}

/* ================================================================== *
 *  Helpers (locale-aware date formatting)                             *
 * ================================================================== */

/** Parse an ISO date/date-time string into a Date (local midnight for dates). */
function _parseIso(iso) {
  const s = iso.length <= 10 ? `${iso}T00:00:00` : iso;
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? null : d;
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
  /* Collapse the trailing margin of the last *visible* section so the card does
     not reserve empty space below it (issue #64). Sections are toggled via the
     [hidden] attribute, so target the last child that has no following visible
     sibling rather than the last DOM child (which may itself be hidden). */
  .kp-content > *:not([hidden]):not(:has(~ *:not([hidden]))) {
    margin-bottom: 0;
  }

  /* ---- Clickable (more-info) ---- */
  .kp-clickable {
    cursor: pointer;
    border-radius: var(--ha-border-radius-md, 8px);
  }
  .kp-clickable:hover {
    background: var(--divider-color);
  }
  .kp-clickable:focus-visible {
    outline: 2px solid var(--primary-color);
    outline-offset: 2px;
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
    border-bottom: 1px solid var(--divider-color);
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
 * Build plant card editor schema.
 * Uses selector: { device: { integration: "kamerplanter" } } to filter
 * to Kamerplanter Plant Instance / Planting Run devices natively.
 */
function plantCardSchema(hass) {
  return [
    { name: "device_id", label: t(CATALOG, "editor_device", hass), required: true,
      selector: { device: { integration: "kamerplanter" } } },
    { name: "title",     label: t(CATALOG, "editor_title", hass),
      selector: { text: {} } },
    { name: "show_progress",  label: t(CATALOG, "editor_show_progress", hass),
      selector: { boolean: {} } },
    { name: "show_timeline",  label: t(CATALOG, "editor_show_timeline", hass),
      selector: { boolean: {} } },
    { name: "show_next_hint", label: t(CATALOG, "editor_show_next_hint", hass),
      selector: { boolean: {} } },
    { name: "show_stats",     label: t(CATALOG, "editor_show_stats", hass),
      selector: { boolean: {} } },
    { name: "show_details",   label: t(CATALOG, "editor_show_details", hass),
      selector: { boolean: {} } },
  ];
}

/* ================================================================== *
 *  Editor                                                             *
 * ================================================================== */

/**
 * Kamerplanter Plant Card Editor — shared ha-form editor base
 * (UI-NFR-015 §2.1). No Shadow DOM (UI-NFR-015 R-022).
 */
class KamerplanterPlantCardEditor extends KamerplanterCardEditor {
  _defaultConfig() {
    return {
      device_id: "", title: "",
      show_progress: true, show_timeline: true,
      show_stats: true, show_next_hint: true, show_details: true,
    };
  }

  _schema(hass) {
    return plantCardSchema(hass);
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
    // Do NOT gate on a persisted __preview flag: HA stores getStubConfig() as
    // the card's starting config, so a flag would stick and pin the card to the
    // static mock on a real dashboard. A missing device_id is handled at render
    // time (config hint) instead of throwing, so the card-picker gallery \u2014 which
    // sets `this.preview` only AFTER setConfig \u2014 is never broken.
    this._config = { ...KamerplanterPlantCard.CONFIG_DEFAULTS, ...config };
    this._monitoredEntities = [];
    this._coreEntitiesResolved = false;
    this._update();
  }

  set hass(hass) {
    const prevHass = this._hass;
    this._hass = hass;

    // Collect this device's entity_ids. Re-collect as long as the core
    // entities (phase / phase_timeline) are not yet resolvable, to cope with
    // entity-registry population timing right after HA startup.
    if (hass && (this._monitoredEntities.length === 0 || !this._coreEntitiesResolved)) {
      this._collectMonitoredEntities();
    }

    // Change-detection: only re-render when our own entities changed.
    const changed = !prevHass || this._monitoredEntities.some(
      id => prevHass.states[id] !== hass.states[id]
    );
    if (changed) this._update();
  }

  /** Populate `_monitoredEntities` with the entity_ids of the configured device. */
  _collectMonitoredEntities() {
    const deviceId = this._config?.device_id;
    if (!deviceId || !this._hass) {
      this._monitoredEntities = [];
      this._coreEntitiesResolved = false;
      return;
    }
    const ids = [];
    for (const ent of Object.values(this._hass.entities || {})) {
      if (ent.device_id === deviceId) ids.push(ent.entity_id);
    }
    this._monitoredEntities = ids;
    // Consider the core entities resolved once the entity map exposes the
    // phase / status / phase_timeline suffixes for this device.
    const map = this._getEntityMap();
    this._coreEntitiesResolved = !!(
      map["phase"] || map["status"] || map["phase_timeline"]
    );
  }

  _handleMoreInfo(entityId) {
    const event = new Event("hass-more-info", { bubbles: true, composed: true });
    event.detail = { entityId };
    this.dispatchEvent(event);
  }

  /**
   * Wire an element as a keyboard/pointer-accessible more-info trigger.
   * Passing a falsy entityId strips the affordance again.
   */
  _makeMoreInfo(el, entityId) {
    if (!el) return;
    if (!entityId) {
      el.removeAttribute("role");
      el.removeAttribute("tabindex");
      el.classList.remove("kp-clickable");
      el.onclick = null;
      el.onkeydown = null;
      return;
    }
    el.setAttribute("role", "button");
    el.setAttribute("tabindex", "0");
    el.classList.add("kp-clickable");
    el.onclick = () => this._handleMoreInfo(entityId);
    el.onkeydown = (ev) => {
      if (ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        this._handleMoreInfo(entityId);
      }
    };
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
    // Sections-View: content-dependent height, so use rows:"auto" instead of a
    // guessed row count. A fixed rows number sets .fit-rows (fixed height) and
    // taller content overflows the grid cell, pushing the edit-mode overlays
    // into the card. Matches hui-entities-card. getCardSize() is the legacy path.
    return { columns: 12, rows: "auto", min_columns: 6 };
  }

  static getConfigElement() {
    return document.createElement("kamerplanter-plant-card-editor");
  }

  static getStubConfig() {
    return { ...KamerplanterPlantCard.CONFIG_DEFAULTS, device_id: "" };
  }

  /* ---- Data ---------------------------------------------------- */

  /** Collect sensor states keyed by suffix (e.g. "phase", "phase_timeline"). */
  _getEntityMap() {
    return getEntityMap(this._hass, this._config.device_id);
  }

  /** Resolve device display name. */
  _getDeviceName() {
    return getDeviceName(this._hass, this._config.device_id);
  }

  /** BCP-47 locale for Intl date formatting (HA locale wins). */
  _dateLocale() {
    return this._hass?.locale?.language || this._hass?.language || undefined;
  }

  /** Locale-aware full date (falls back to the raw ISO string). */
  _fmtDate(iso) {
    if (!iso) return "";
    const d = _parseIso(iso);
    if (!d) return iso;
    try {
      return new Intl.DateTimeFormat(this._dateLocale(), {
        year: "numeric", month: "2-digit", day: "2-digit",
      }).format(d);
    } catch {
      return iso;
    }
  }

  /** Locale-aware short date (day + month). */
  _fmtDateShort(iso) {
    if (!iso) return "";
    const d = _parseIso(iso);
    if (!d) return iso;
    try {
      return new Intl.DateTimeFormat(this._dateLocale(), {
        month: "2-digit", day: "2-digit",
      }).format(d);
    } catch {
      return iso;
    }
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

    const c = this._config || {};
    const hass = this._hass;
    const statsHtml = c.show_stats !== false ? `
        <div class="kp-stats">
          <div class="kp-stats__item"><span class="kp-stats__value">6</span><span class="kp-stats__label">${escapeHtml(t(CATALOG, "stat_overall_week", hass))}</span></div>
          <div class="kp-stats__item"><span class="kp-stats__value">4</span><span class="kp-stats__label">${escapeHtml(t(CATALOG, "stat_phase_week", hass))}</span></div>
          <div class="kp-stats__item kp-stats__item--harvest"><span class="kp-stats__value">35<span class="kp-stats__unit">d</span></span><span class="kp-stats__label">${escapeHtml(t(CATALOG, "stat_to_harvest", hass))}</span></div>
        </div>
    ` : "";
    const progressHtml = c.show_progress !== false ? `
        <div class="kp-progress">
          <div class="kp-progress__header"><span class="kp-progress__phase">${escapeHtml(phaseLabelI18n("flowering", hass))}</span><span class="kp-progress__info">${escapeHtml(t(CATALOG, "day_of", hass, "28", "63"))}</span></div>
          <div class="kp-progress__track" role="progressbar" aria-label="${escapeAttr(t(CATALOG, "aria_progress", hass))}" aria-valuemin="0" aria-valuemax="100" aria-valuenow="44"><div class="kp-progress__fill" style="width:44%;background:#e91e63"></div></div>
          <div class="kp-progress__footer"><span class="kp-progress__pct">44%</span><span class="kp-progress__remain">${escapeHtml(t(CATALOG, "days_remaining_other", hass, "35"))}</span></div>
        </div>
    ` : "";
    const timelineHtml = c.show_timeline !== false ? `
        <div class="kp-timeline-wrapper">
          <div class="kp-timeline">
            <div class="kp-phase-pill"><div class="kp-phase-pill__dot kp-phase-pill__dot--completed" style="--dot-color:#795548" aria-hidden="true"></div><span class="kp-phase-pill__label">${escapeHtml(phaseLabelI18n("germination", hass))}</span><span class="kp-phase-pill__days">5d</span></div>
            <div class="kp-phase-pill"><div class="kp-phase-pill__line" style="background:#8bc34a"></div><div class="kp-phase-pill__dot kp-phase-pill__dot--completed" style="--dot-color:#8bc34a" aria-hidden="true"></div><span class="kp-phase-pill__label">${escapeHtml(phaseLabelI18n("seedling", hass))}</span><span class="kp-phase-pill__days">10d</span></div>
            <div class="kp-phase-pill"><div class="kp-phase-pill__line" style="background:#4caf50"></div><div class="kp-phase-pill__dot kp-phase-pill__dot--completed" style="--dot-color:#4caf50" aria-hidden="true"></div><span class="kp-phase-pill__label">${escapeHtml(phaseLabelI18n("vegetative", hass))}</span><span class="kp-phase-pill__days">14d</span></div>
            <div class="kp-phase-pill"><div class="kp-phase-pill__line" style="background:#e91e63"></div><div class="kp-phase-pill__dot kp-phase-pill__dot--current" style="--dot-color:#e91e63" aria-hidden="true"></div><span class="kp-phase-pill__label">${escapeHtml(phaseLabelI18n("flowering", hass))}</span><span class="kp-phase-pill__days">28d</span></div>
            <div class="kp-phase-pill"><div class="kp-phase-pill__line" style="background:#bdbdbd"></div><div class="kp-phase-pill__dot kp-phase-pill__dot--upcoming" style="--dot-color:#bdbdbd" aria-hidden="true"></div><span class="kp-phase-pill__label">${escapeHtml(phaseLabelI18n("harvest", hass))}</span><span class="kp-phase-pill__days">—</span></div>
          </div>
        </div>
    ` : "";

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
          <span class="kp-header__icon" aria-hidden="true">\uD83C\uDF31</span>
          <div class="kp-header__text">
            <span class="kp-header__name">Northern Lights #03</span>
            <span class="kp-header__plan">GH Flora Bloom</span>
          </div>
          <div class="kp-header__days">28<small>d</small></div>
        </div>
        ${statsHtml}
        ${progressHtml}
        ${timelineHtml}
      </ha-card>
    `;
  }

  _update() {
    if (!this._config) return;
    // `this.preview` is set by HA only when the card is shown in the card-picker
    // gallery. A persisted __preview flag is intentionally ignored so cards that
    // captured the old getStubConfig still recover to live data on reload.
    if (this.preview) {
      this._renderPreview();
      return;
    }
    if (!this._config.device_id) {
      this.shadowRoot.innerHTML = `
        <style>${CARD_STYLES}</style>
        <ha-card><div class="kp-error">${escapeHtml(t(CATALOG, "error_no_device", this._hass))}</div></ha-card>
      `;
      this._built = false;
      return;
    }
    // Device configured but HA context / states not yet available: show a
    // neutral loading hint instead of an empty card (WP-17).
    if (!this._hass) {
      this.shadowRoot.innerHTML = `
        <style>${CARD_STYLES}</style>
        <ha-card><div class="kp-empty" role="status">${escapeHtml(t(CATALOG, "loading", this._hass))}</div></ha-card>
      `;
      this._built = false;
      return;
    }

    const ents = this._getEntityMap();

    if (Object.keys(ents).length === 0) {
      this.shadowRoot.innerHTML = `
        <style>${CARD_STYLES}</style>
        <ha-card><div class="kp-error">${escapeHtml(t(CATALOG, "error_not_found", this._hass))}</div></ha-card>
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
    const plantName    = this._config.title || this._getDeviceName()
      || t(CATALOG, "default_plant_name", this._hass);

    /* Header */
    const headerSvg = kamiSvg(currentPhase);
    $("headerVisual").innerHTML = headerSvg
      ? `<img class="kp-header__kami" src="${headerSvg}" alt="${escapeAttr(phaseLabelI18n(currentPhase, this._hass))}" />`
      : `<span class="kp-header__icon" aria-hidden="true">\uD83C\uDF31</span>`;

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
    if (this._config.show_stats !== false) {
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
    if (this._config.show_progress !== false) {
      const progressHtml = this._renderProgress(tAttrs, currentPhase);
      if (progressHtml) {
        progressEl.innerHTML = progressHtml;
        progressEl.hidden = false;
        // Click on the phase/progress opens the phase entity's more-info dialog.
        const phaseEntityId = (phaseObj || timelineObj)?.entity_id;
        this._makeMoreInfo(progressEl, phaseEntityId);
      } else {
        progressEl.hidden = true;
        this._makeMoreInfo(progressEl, null);
      }
    } else {
      progressEl.hidden = true;
      this._makeMoreInfo(progressEl, null);
    }

    /* Timeline */
    const phases = this._buildPhases(tAttrs, currentPhase);
    const timelineEl = $("timeline");
    const wrapperEl = $("timelineWrapper");
    if (this._config.show_timeline !== false) {
      timelineEl.innerHTML = this._renderTimeline(phases);
      wrapperEl.hidden = false;
      this._setupScrollFade(timelineEl, wrapperEl);
    } else {
      timelineEl.innerHTML = "";
      wrapperEl.hidden = true;
    }

    /* Next phase hint */
    const nextEl = $("nextHint");
    if (this._config.show_next_hint !== false) {
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
    if (this._config.show_details !== false) {
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
          <span class="kp-stats__value">${safeNum(overallWeek)}</span>
          <span class="kp-stats__label">${escapeHtml(t(CATALOG, "stat_overall_week", this._hass))}</span>
        </div>`;
    }

    if (phaseWeek != null) {
      html += `
        <div class="kp-stats__item">
          <span class="kp-stats__value">${safeNum(phaseWeek)}</span>
          <span class="kp-stats__label">${escapeHtml(t(CATALOG, "stat_phase_week", this._hass))}</span>
        </div>`;
    }

    if (daysToHarvest != null) {
      html += `
        <div class="kp-stats__item kp-stats__item--harvest">
          <span class="kp-stats__value">${safeNum(daysToHarvest)}<span class="kp-stats__unit">d</span></span>
          <span class="kp-stats__label">${escapeHtml(t(CATALOG, "stat_to_harvest", this._hass))}</span>
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

    const ariaLabel = escapeAttr(t(CATALOG, "aria_progress", this._hass));

    // Full progress mode: plan-based week/percentage data available
    if (phaseWeek != null && plannedWeeks != null && plannedWeeks > 0) {
      const pct = Math.min(100, progressPct || 0);
      const infoText = daysInPhase != null
        ? t(CATALOG, "day_of", this._hass, safeNum(daysInPhase), typicalDays ? safeNum(typicalDays) : "?")
        : t(CATALOG, "week_of", this._hass, safeNum(phaseWeek), safeNum(plannedWeeks));
      let remainText = "";
      if (remainingDays != null) {
        remainText = t(CATALOG, remainingDays === 1 ? "days_remaining_one" : "days_remaining_other", this._hass, safeNum(remainingDays));
      } else if (remainingWeeks != null) {
        remainText = t(CATALOG, remainingWeeks === 1 ? "weeks_remaining_one" : "weeks_remaining_other", this._hass, safeNum(remainingWeeks));
      }

      return `
        <div class="kp-progress__header">
          <span class="kp-progress__phase">${escapeHtml(phaseLabelI18n(currentPhase, this._hass))}</span>
          <span class="kp-progress__info">${escapeHtml(infoText)}</span>
        </div>
        <div class="kp-progress__track" role="progressbar" aria-label="${ariaLabel}" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Number(pct)}">
          <div class="kp-progress__fill" style="width:${Number(pct)}%"></div>
        </div>
        <div class="kp-progress__footer">
          <span class="kp-progress__pct">${Number(pct)}%</span>
          ${remainText ? `<span class="kp-progress__remaining">${escapeHtml(remainText)}</span>` : ""}
        </div>
      `;
    }

    // Fallback mode: only days_in_phase available (no plan data)
    if (daysInPhase != null) {
      const weeks = Math.floor(daysInPhase / 7);
      const daysMod = daysInPhase % 7;
      const durationText = weeks > 0
        ? t(CATALOG, "duration_weeks_days", this._hass,
            t(CATALOG, weeks === 1 ? "week_one" : "week_other", this._hass, safeNum(weeks)),
            t(CATALOG, daysMod === 1 ? "day_one" : "day_other", this._hass, safeNum(daysMod)))
        : t(CATALOG, daysInPhase === 1 ? "day_one" : "day_other", this._hass, safeNum(daysInPhase));
      const inPhaseText = t(CATALOG, "in_this_phase", this._hass, durationText);

      return `
        <div class="kp-progress__header">
          <span class="kp-progress__phase">${escapeHtml(phaseLabelI18n(currentPhase, this._hass))}</span>
          <span class="kp-progress__info">${escapeHtml(t(CATALOG, "day_n", this._hass, safeNum(daysInPhase)))}</span>
        </div>
        <div class="kp-progress__track" role="progressbar" aria-label="${ariaLabel}" aria-valuemin="0" aria-valuemax="100" aria-valuetext="${escapeAttr(inPhaseText)}">
          <div class="kp-progress__fill kp-progress__fill--indeterminate"></div>
        </div>
        <div class="kp-progress__footer">
          <span class="kp-progress__remaining">${escapeHtml(inPhaseText)}</span>
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
      const label = phaseLabelI18n(nextPlanPhase, this._hass);
      const nKami = kamiSvg(nextPlanPhase);
      const kamiImg = nKami
        ? `<img class="kp-next__kami" src="${nKami}" alt="" aria-hidden="true" />`
        : `<span class="kp-next__arrow" aria-hidden="true">\u2192</span>`;

      if (weeksUntilNext === 0) {
        const weeksPhrase = t(CATALOG, nextPhaseWeeks === 1 ? "week_one" : "week_other", this._hass, safeNum(nextPhaseWeeks));
        return `${kamiImg}<span><strong>${escapeHtml(label)}</strong> ${escapeHtml(t(CATALOG, "has_begun", this._hass, weeksPhrase))}</span>`;
      }
      const weeksPhrase = t(CATALOG, weeksUntilNext === 1 ? "week_one" : "week_other", this._hass, safeNum(weeksUntilNext));
      return `${kamiImg}<span><strong>${escapeHtml(label)}</strong> ${escapeHtml(t(CATALOG, "in_weeks", this._hass, weeksPhrase))}</span>`;
    }

    /* Fallback: simple next_phase sensor */
    if (nextPhase && nextPhase !== "None" && nextPhase !== "unknown") {
      const label = phaseLabelI18n(nextPhase, this._hass);
      const nSvg = kamiSvg(nextPhase);
      const visual = nSvg
        ? `<img class="kp-next__kami" src="${nSvg}" alt="" aria-hidden="true" />`
        : `<span class="kp-next__arrow" aria-hidden="true">\u2192</span>`;
      return `${visual}<span>${escapeHtml(t(CATALOG, "next_phase_label", this._hass))} <strong>${escapeHtml(label)}</strong></span>`;
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

      /* Marker content — decorative (phase name is shown as adjacent text). */
      const svg = kamiSvg(p.name);
      let marker = "";
      if (svg) {
        marker = `<img src="${svg}" alt="" aria-hidden="true" />`;
      } else if (state === "completed") {
        marker = CHECK_SVG;
      } else if (state === "current") {
        marker = `<div class="kp-step__pulse" aria-hidden="true"></div>`;
      }

      const dateStr = p.started || p.date || "";

      html += `
        <div class="kp-step kp-step--${state}">
          <div class="kp-step__marker${svg ? " kp-step__marker--kami" : ""}">
            ${marker}
          </div>
          <div class="kp-step__body">
            <span class="kp-step__name">${escapeHtml(phaseLabelI18n(p.name, this._hass))}</span>
            ${dateStr ? `<span class="kp-step__date">${escapeHtml(this._fmtDateShort(dateStr))}</span>` : ""}
            ${p.days != null ? `<span class="kp-step__duration">${safeNum(p.days)}d</span>` : ""}
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
            ${svg ? `<img src="${svg}" alt="" aria-hidden="true" />` : ""}
            ${escapeHtml(phaseLabelI18n(p.name, this._hass))}
          </span>
          <span class="kp-details__date">${escapeHtml(this._fmtDate(p.started || p.date || ""))}</span>
          <span class="kp-details__days">${p.days != null ? `${safeNum(p.days)}d` : "\u2014"}</span>
        </div>
      `;
    }
    return `
      <div class="kp-details__header">
        <span>${escapeHtml(t(CATALOG, "details_col_phase", this._hass))}</span><span>${escapeHtml(t(CATALOG, "details_col_start", this._hass))}</span><span>${escapeHtml(t(CATALOG, "details_col_duration", this._hass))}</span>
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
