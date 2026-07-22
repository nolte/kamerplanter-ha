/**
 * Kamerplanter Houseplant Card — Custom Lovelace Card
 *
 * Compact card for perennial / houseplant instances.
 * Shows: Kami phase visual, watering status (days until/overdue),
 * nutrient plan info with current dosages.
 *
 * Data sources (per-device sensors):
 *   - sensor.kp_{slug}_phase
 *   - sensor.kp_{slug}_days_in_phase
 *   - sensor.kp_{slug}_days_until_watering
 *   - sensor.kp_{slug}_nutrient_plan
 *   - sensor.kp_{slug}_active_channels
 *
 * Configuration:
 *   type: custom:kamerplanter-houseplant-card
 *   device_id: <device>
 *   title: ""                   # optional override
 *   show_watering: true         # watering status section
 *   show_fertilizer: true       # nutrient plan + dosages section
 */

import {
  KamerplanterCardEditor,
  escapeHtml,
  getDeviceName,
  getEntityMap,
  isUnavailableState,
  kamiSvg,
  phaseLabel,
} from "./kamerplanter-card-common.js";

const CARD_VERSION_HP = "1.0.0";

/* ================================================================== *
 *  Styles                                                             *
 * ================================================================== */

const HP_STYLES = `
  :host {
    display: block;
  }
  ha-card {
    padding: 16px;
    overflow: hidden;
  }

  /* --- Header --- */
  .hp-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
  }
  .hp-header__kami {
    width: 56px;
    height: 56px;
    object-fit: contain;
    flex-shrink: 0;
  }
  .hp-header__icon {
    font-size: 40px;
    line-height: 56px;
    flex-shrink: 0;
  }
  .hp-header__text {
    flex: 1;
    min-width: 0;
  }
  .hp-header__name {
    display: block;
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--primary-text-color);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .hp-header__phase {
    display: block;
    font-size: 0.85rem;
    color: var(--secondary-text-color);
    margin-top: 2px;
  }
  .hp-header__days {
    box-sizing: border-box;
    height: 56px;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 0 20px;
    border-radius: 999px;
    background: transparent;
    border: 2px solid var(--primary-color, #4caf50);
    color: var(--primary-color, #4caf50);
    font-size: 1.7rem;
    font-weight: 700;
    line-height: 1;
    white-space: nowrap;
    flex-shrink: 0;
  }
  .hp-header__days small {
    font-size: 1.2rem;
    font-weight: 600;
    opacity: 0.8;
  }

  /* --- Watering section --- */
  .hp-watering {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 12px;
    border-radius: 12px;
    background: var(--card-background-color, var(--ha-card-background, #fff));
    border: 1px solid var(--divider-color, rgba(0,0,0,0.12));
    margin-bottom: 10px;
  }
  .hp-watering__icon {
    --mdc-icon-size: 28px;
    flex-shrink: 0;
  }
  .hp-watering__info {
    flex: 1;
    min-width: 0;
  }
  .hp-watering__label {
    font-size: 0.75rem;
    color: var(--secondary-text-color);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .hp-watering__value {
    font-size: 1rem;
    font-weight: 600;
    color: var(--primary-text-color);
  }
  .hp-watering__detail {
    font-size: 0.8rem;
    color: var(--secondary-text-color);
  }
  .hp-watering--overdue {
    border-color: var(--error-color, #f44336);
    background: color-mix(in srgb, var(--error-color, #f44336) 8%, transparent);
  }
  .hp-watering--overdue .hp-watering__icon {
    color: var(--error-color, #f44336);
  }
  .hp-watering--overdue .hp-watering__value {
    color: var(--error-color, #f44336);
  }
  .hp-watering--today {
    border-color: var(--warning-color, #ff9800);
    background: color-mix(in srgb, var(--warning-color, #ff9800) 8%, transparent);
  }
  .hp-watering--today .hp-watering__icon {
    color: var(--warning-color, #ff9800);
  }
  .hp-watering--ok {
    border-color: var(--success-color, #4caf50);
  }
  .hp-watering--ok .hp-watering__icon {
    color: var(--success-color, #4caf50);
  }

  /* --- Fertilizer section --- */
  .hp-fert {
    padding: 10px 12px;
    border-radius: 12px;
    background: var(--card-background-color, var(--ha-card-background, #fff));
    border: 1px solid var(--divider-color, rgba(0,0,0,0.12));
  }
  .hp-fert__header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
  }
  .hp-fert__icon {
    --mdc-icon-size: 20px;
    color: var(--primary-color, #4caf50);
    flex-shrink: 0;
  }
  .hp-fert__plan-name {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--primary-text-color);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .hp-fert__channels {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .hp-fert__channel {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .hp-fert__channel-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--secondary-text-color);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .hp-fert__dosages {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }
  .hp-fert__dosage {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 8px;
    border-radius: 10px;
    background: color-mix(in srgb, var(--primary-color, #4caf50) 12%, transparent);
    font-size: 0.8rem;
    color: var(--primary-text-color);
  }
  .hp-fert__dosage-ml {
    font-weight: 600;
  }
  .hp-fert__none {
    font-size: 0.85rem;
    color: var(--secondary-text-color);
    font-style: italic;
  }

  /* --- Empty state --- */
  .hp-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 16px;
    color: var(--secondary-text-color);
    text-align: center;
  }
  .hp-empty ha-icon {
    --mdc-icon-size: 40px;
    margin-bottom: 8px;
    opacity: 0.5;
  }
  .hp-error {
    padding: 16px;
    text-align: center;
    color: var(--error-color, #f44336);
    font-size: 0.9rem;
  }
`;

/* ================================================================== *
 *  Editor                                                             *
 * ================================================================== */

const HOUSEPLANT_CARD_SCHEMA = [
  { name: "device_id", label: "Pflanze", required: true,
    selector: { device: { integration: "kamerplanter" } } },
  { name: "title",     label: "Titel (optional)",
    selector: { text: {} } },
  { name: "show_watering",   label: "Giess-Status anzeigen",
    selector: { boolean: {} } },
  { name: "show_fertilizer", label: "Duenger-Info anzeigen",
    selector: { boolean: {} } },
];

class KamerplanterHouseplantCardEditor extends KamerplanterCardEditor {
  _defaultConfig() {
    return { device_id: "", title: "", show_watering: true, show_fertilizer: true };
  }

  _schema() {
    return HOUSEPLANT_CARD_SCHEMA;
  }
}
customElements.define("kamerplanter-houseplant-card-editor", KamerplanterHouseplantCardEditor);

/* ================================================================== *
 *  Card                                                               *
 * ================================================================== */

class KamerplanterHouseplantCard extends HTMLElement {

  static get CONFIG_DEFAULTS() {
    return { title: "", show_watering: true, show_fertilizer: true };
  }

  set hass(hass) {
    const prevHass = this._hass;

    // Beim ersten Aufruf die zum konfigurierten Device gehoerenden Entity-IDs
    // sammeln. Solange die Liste leer ist, wird erneut gesammelt, um das
    // Timing der Entity-Registry beim HA-Start abzufangen.
    if ((!this._monitoredEntities || this._monitoredEntities.length === 0) && hass) {
      const deviceId = this._config?.device_id;
      if (deviceId) {
        this._monitoredEntities = Object.values(hass.entities || {})
          .filter((ent) => ent.device_id === deviceId)
          .map((ent) => ent.entity_id);
      }
    }

    this._hass = hass;

    // Change-Detection: nur rendern beim ersten hass, solange noch keine
    // eigenen Entities bekannt sind (Loading-State), oder wenn sich der State
    // einer eigenen Device-Entity geaendert hat. Fremd-State-Changes loesen
    // damit kein Re-Render aus.
    const changed =
      !prevHass ||
      !this._monitoredEntities ||
      this._monitoredEntities.length === 0 ||
      this._monitoredEntities.some(
        (entId) => prevHass.states[entId] !== hass.states[entId],
      );

    if (changed) this._update();
  }

  setConfig(config) {
    // Do NOT gate on a persisted __preview flag: HA stores getStubConfig() as
    // the card's starting config, so a flag would stick and pin the card to the
    // static mock on a real dashboard. A missing device_id is handled at render
    // time (config hint) instead of throwing, so the card-picker gallery — which
    // sets `this.preview` only AFTER setConfig — is never broken.
    this._config = { ...KamerplanterHouseplantCard.CONFIG_DEFAULTS, ...config };
    this._built = false;
    // Monitored-Entity-Liste zuruecksetzen, damit sie fuer das (ggf. neue)
    // device_id beim naechsten hass-Setter neu gesammelt wird.
    this._monitoredEntities = [];
    this._update();
  }

  connectedCallback() {
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    this._update();
  }

  getCardSize() {
    let size = 2; // header
    const c = this._config || {};
    if (c.show_watering !== false) size += 2;
    if (c.show_fertilizer !== false) size += 2;
    return size;
  }

  getGridOptions() {
    let rows = 2;
    const c = this._config || {};
    if (c.show_watering !== false) rows += 2;
    if (c.show_fertilizer !== false) rows += 2;
    // 12-column grid: full width by default, never below half a section.
    return { columns: 12, min_columns: 6, rows, min_rows: 2 };
  }

  static getConfigElement() {
    return document.createElement("kamerplanter-houseplant-card-editor");
  }

  static getStubConfig() {
    return { ...KamerplanterHouseplantCard.CONFIG_DEFAULTS, device_id: "" };
  }

  /* ---- Data helpers --------------------------------------------- */

  _getEntityMap() {
    return getEntityMap(this._hass, this._config.device_id);
  }

  _getDeviceName() {
    return getDeviceName(this._hass, this._config.device_id);
  }

  /* ---- DOM ------------------------------------------------------ */

  _renderPreview() {
    if (!this.shadowRoot) return;
    this._built = false;

    const c = this._config || {};
    const showWatering = c.show_watering !== false;
    const showFertilizer = c.show_fertilizer !== false;

    const wateringHtml = showWatering ? `
        <div class="hp-watering hp-watering--today">
          <ha-icon icon="mdi:watering-can" class="hp-watering__icon"></ha-icon>
          <div class="hp-watering__info">
            <div class="hp-watering__label">Heute giessen!</div>
            <div class="hp-watering__value">Heute faellig</div>
            <div class="hp-watering__detail">Intervall: 5 Tage</div>
          </div>
        </div>
    ` : "";

    const fertilizerHtml = showFertilizer ? `
        <div class="hp-fert">
          <div class="hp-fert__header">
            <ha-icon icon="mdi:bottle-tonic" class="hp-fert__icon"></ha-icon>
            <span class="hp-fert__plan-name">Zimmerpflanzen Universal</span>
          </div>
          <div class="hp-fert__channels">
            <div class="hp-fert__channel">
              <div class="hp-fert__dosages">
                <span class="hp-fert__dosage">NPK 7-3-6 <span class="hp-fert__dosage-ml">2.0 ml/L</span></span>
                <span class="hp-fert__dosage">CalMag <span class="hp-fert__dosage-ml">0.5 ml/L</span></span>
              </div>
            </div>
          </div>
        </div>
    ` : "";

    this.shadowRoot.innerHTML = `
      <style>${HP_STYLES}</style>
      <ha-card>
        <div class="hp-header">
          <span class="hp-header__icon">\uD83C\uDF3F</span>
          <div class="hp-header__text">
            <span class="hp-header__name">Monstera deliciosa</span>
            <span class="hp-header__phase">Vegetativ \u2014 Tag 45</span>
          </div>
          <div class="hp-header__days">45<small>d</small></div>
        </div>
        ${wateringHtml}
        ${fertilizerHtml}
      </ha-card>
    `;
  }

  _update() {
    if (!this.shadowRoot) return;
    // `this.preview` is set by HA only when the card is shown in the card-picker
    // gallery. A persisted __preview flag is intentionally ignored so cards that
    // captured the old getStubConfig still recover to live data on reload.
    if (this.preview) {
      this._renderPreview();
      return;
    }
    if (!this._config || !this._config.device_id) {
      this.shadowRoot.innerHTML = `
        <style>${HP_STYLES}</style>
        <ha-card><div class="hp-error">Kein Gerät konfiguriert</div></ha-card>
      `;
      this._built = false;
      return;
    }
    if (!this._hass) return;

    const ents = this._getEntityMap();

    if (Object.keys(ents).length === 0) {
      // device_id ist gesetzt, aber es liegen noch keine States vor. Das ist
      // typischerweise ein Timing-Problem der Entity-Registry beim HA-Start und
      // kein echter Fehler -> neutraler Ladehinweis statt hp-error.
      this.shadowRoot.innerHTML = `
        <style>${HP_STYLES}</style>
        <ha-card>
          <div class="hp-empty">
            <ha-icon icon="mdi:sprout"></ha-icon>
            <span>Pflanzendaten werden geladen ...</span>
          </div>
        </ha-card>
      `;
      this._built = false;
      return;
    }

    const phaseObj     = ents["phase"];
    const daysObj      = ents["days_in_phase"];
    const waterObj     = ents["days_until_watering"];
    const nutrientObj  = ents["nutrient_plan"];
    const channelsObj  = ents["active_channels"];

    const currentPhase = isUnavailableState(phaseObj?.state) ? null : phaseObj.state;
    const daysInPhase  = daysObj?.state;
    const plantName    = this._config.title || this._getDeviceName() || "Pflanze";

    // Build HTML
    const kamiUrl = kamiSvg(currentPhase);
    const kamiHtml = kamiUrl
      ? `<img class="hp-header__kami" src="${kamiUrl}" alt="${escapeHtml(currentPhase)}" />`
      : `<span class="hp-header__icon">\uD83C\uDF31</span>`;

    const phaseText = phaseLabel(currentPhase);
    const daysText = !isUnavailableState(daysInPhase)
      ? ` \u2014 Tag ${escapeHtml(String(daysInPhase))}`
      : "";

    let html = `
      <style>${HP_STYLES}</style>
      <ha-card>
        <div class="hp-header">
          ${kamiHtml}
          <div class="hp-header__text">
            <span class="hp-header__name">${escapeHtml(plantName)}</span>
            <span class="hp-header__phase">${escapeHtml(phaseText)}${daysText}</span>
          </div>
    `;

    // Days badge (days in phase)
    if (!isUnavailableState(daysInPhase)) {
      html += `
          <div class="hp-header__days">
            ${escapeHtml(String(daysInPhase))}<small>d</small>
          </div>
      `;
    }

    html += `</div>`; // close header

    // --- Watering section ---
    if (this._config.show_watering !== false) {
      const rawState = waterObj?.state;
      const daysUntil = !isUnavailableState(rawState)
        ? parseInt(rawState, 10) : null;
      const attrs = waterObj?.attributes || {};
      const nextDate = attrs.next_watering_date;
      const lastDate = attrs.last_watered;
      const interval = attrs.interval_days;

      let statusClass = "hp-watering--ok";
      let statusIcon = "mdi:watering-can";
      let statusLabel = "Naechstes Giessen";
      let statusValue = "";
      let statusDetail = "";

      if (daysUntil === null || isNaN(daysUntil)) {
        statusValue = "Kein Giessplan";
        statusClass = "";
        statusIcon = "mdi:watering-can-outline";
      } else if (daysUntil < 0) {
        const overdueDays = Math.abs(daysUntil);
        statusClass = "hp-watering--overdue";
        statusIcon = "mdi:alert-circle";
        statusLabel = "Ueberfaellig";
        statusValue = `${overdueDays} ${overdueDays === 1 ? "Tag" : "Tage"} ueberfaellig`;
        if (lastDate) statusDetail = `Zuletzt: ${lastDate}`;
      } else if (daysUntil === 0) {
        statusClass = "hp-watering--today";
        statusIcon = "mdi:watering-can";
        statusLabel = "Heute giessen!";
        statusValue = "Heute faellig";
        if (interval) statusDetail = `Intervall: ${interval} Tage`;
      } else if (daysUntil === 1) {
        statusValue = "Morgen";
        if (nextDate) statusDetail = nextDate;
      } else {
        statusValue = `In ${daysUntil} Tagen`;
        if (nextDate) statusDetail = nextDate;
      }

      html += `
        <div class="hp-watering ${statusClass}">
          <ha-icon icon="${statusIcon}" class="hp-watering__icon"></ha-icon>
          <div class="hp-watering__info">
            <div class="hp-watering__label">${statusLabel}</div>
            <div class="hp-watering__value">${escapeHtml(statusValue)}</div>
            ${statusDetail ? `<div class="hp-watering__detail">${escapeHtml(statusDetail)}</div>` : ""}
          </div>
        </div>
      `;
    }

    // --- Fertilizer section ---
    if (this._config.show_fertilizer !== false) {
      const planName = nutrientObj?.state;
      const hasPlan = planName && !isUnavailableState(planName) && planName !== "None";
      const channelAttrs = channelsObj?.attributes || {};
      const channelIds = channelAttrs.channel_ids || [];

      if (hasPlan || channelIds.length > 0) {
        html += `
          <div class="hp-fert">
            <div class="hp-fert__header">
              <ha-icon icon="mdi:bottle-tonic" class="hp-fert__icon"></ha-icon>
              <span class="hp-fert__plan-name">${escapeHtml(hasPlan ? planName : "Duenger")}</span>
            </div>
            <div class="hp-fert__channels">
        `;

        if (channelIds.length > 0) {
          for (const chId of channelIds) {
            const ch = channelAttrs[chId];
            if (!ch) continue;
            const dosages = ch.dosages || {};
            const label = ch.label || chId;

            html += `<div class="hp-fert__channel">`;
            if (channelIds.length > 1) {
              html += `<div class="hp-fert__channel-label">${escapeHtml(label)}</div>`;
            }
            html += `<div class="hp-fert__dosages">`;
            for (const [product, ml] of Object.entries(dosages)) {
              html += `
                <span class="hp-fert__dosage">
                  ${escapeHtml(product)} <span class="hp-fert__dosage-ml">${escapeHtml(String(ml))} ml/L</span>
                </span>
              `;
            }
            if (Object.keys(dosages).length === 0) {
              html += `<span class="hp-fert__none">Keine Dosierungen</span>`;
            }
            html += `</div></div>`;
          }
        } else if (hasPlan) {
          html += `<span class="hp-fert__none">Keine aktiven Kanaele</span>`;
        }

        html += `</div></div>`;
      }
    }

    html += `</ha-card>`;

    this.shadowRoot.innerHTML = html;
  }
}

customElements.define("kamerplanter-houseplant-card", KamerplanterHouseplantCard);

/* ================================================================== *
 *  Registration                                                       *
 * ================================================================== */

window.customCards = window.customCards || [];
window.customCards.push({
  type: "kamerplanter-houseplant-card",
  name: "Kamerplanter Zimmerpflanze",
  description: "Kompakte Karte fuer mehrjaehrige Pflanzen mit Giess-Status, Phase und Duenger-Info.",
  preview: true,
  documentationURL: "https://kamerplanter.readthedocs.io/de/latest/guides/home-assistant-integration/",
});

console.info(
  `%c KAMERPLANTER-HOUSEPLANT-CARD %c v${CARD_VERSION_HP} `,
  "color: white; background: #2E7D32; font-weight: bold;",
  "color: #2E7D32; background: white; font-weight: bold;"
);
