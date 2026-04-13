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

const CARD_VERSION_HP = "1.0.0";

/* ================================================================== *
 *  Shared constants                                                   *
 * ================================================================== */

const KAMI_PHASE_SVG_HP = {
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

const PHASE_LABELS_HP = {
  germination:         "Keimung",
  seedling:            "Saemling",
  vegetative:          "Vegetativ",
  flowering:           "Bluete",
  ripening:            "Reife",
  harvest:             "Ernte",
  dormancy:            "Ruhephase",
  flush:               "Spuelphase",
  flushing:            "Spuelung",
  drying:              "Trocknung",
  curing:              "Curing",
  leaf_phase:          "Blattphase",
  short_day_induction: "Kurztageinleitung",
  juvenile:            "Juvenil",
  climbing:            "Kletterphase",
  mature:              "Reifephase",
  senescence:          "Seneszenz",
};

function _hpKamiSvg(phase) {
  return KAMI_PHASE_SVG_HP[(phase || "").toLowerCase()] || null;
}

function _hpPhaseLabel(phase) {
  const key = (phase || "").toLowerCase();
  return PHASE_LABELS_HP[key] || (phase ? phase.charAt(0).toUpperCase() + phase.slice(1) : "—");
}

function _hpEscape(s) {
  const el = document.createElement("span");
  el.textContent = s || "";
  return el.innerHTML;
}

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
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-width: 40px;
    padding: 4px 8px;
    border-radius: 12px;
    background: var(--primary-color, #4caf50);
    color: #fff;
    font-size: 1.1rem;
    font-weight: 700;
    line-height: 1.1;
    flex-shrink: 0;
  }
  .hp-header__days small {
    font-size: 0.6rem;
    font-weight: 400;
    opacity: 0.85;
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
 *  ha-form ready singleton                                            *
 * ================================================================== */

const _haFormReadyHouseplant = (async () => {
  if (customElements.get("ha-form")) return;
  await customElements.whenDefined("hui-entities-card");
  const helpers = await window.loadCardHelpers?.();
  if (helpers) {
    const temp = await helpers.createCardElement({ type: "entities", entities: [] });
    if (temp?.constructor?.getConfigElement) await temp.constructor.getConfigElement();
  }
  await customElements.whenDefined("ha-form");
})();

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

class KamerplanterHouseplantCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = {
      device_id: "", title: "",
      show_watering: true, show_fertilizer: true,
      ...config,
    };
    if (this._hass) this._scheduleRender();
  }

  set hass(hass) {
    this._hass = hass;
    this._scheduleRender();
  }

  async _scheduleRender() {
    await _haFormReadyHouseplant;
    this._render();
  }

  _render() {
    if (!this._config || !this._hass) return;
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
    this._form.schema = HOUSEPLANT_CARD_SCHEMA;
    this._form.data = this._config;
    this._form.computeLabel = (schema) => schema.label || schema.name;
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
    this._hass = hass;
    this._update();
  }

  setConfig(config) {
    this._isPreview = !!config.__preview;
    if (!this._isPreview && !config.device_id) {
      throw new Error("device_id is required");
    }
    this._config = { ...KamerplanterHouseplantCard.CONFIG_DEFAULTS, ...config };
    this._built = false;
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
    return { columns: 12, min_columns: 6, rows, min_rows: 2 };
  }

  static getConfigElement() {
    return document.createElement("kamerplanter-houseplant-card-editor");
  }

  static getStubConfig() {
    return { ...KamerplanterHouseplantCard.CONFIG_DEFAULTS, __preview: true, device_id: "" };
  }

  /* ---- Data helpers --------------------------------------------- */

  _getEntityMap() {
    const id = this._config.device_id;
    if (!id || !this._hass) return {};

    const allDeviceEnts = [];
    for (const ent of Object.values(this._hass.entities || {})) {
      if (ent.device_id !== id) continue;
      if (!/^(?:sensor|binary_sensor)\./.test(ent.entity_id)) continue;
      allDeviceEnts.push(ent);
    }

    const map = {};
    for (const ent of allDeviceEnts) {
      const st = this._hass.states[ent.entity_id];
      if (!st) continue;

      // Try translation_key first (HA 2024.1+)
      if (ent.translation_key) {
        map[ent.translation_key] = st;
        continue;
      }

      // Try unique_id (always ends with _kp_{slug}_{suffix})
      const uid = ent.unique_id || "";
      const parts = uid.split("_kp_");
      if (parts.length >= 2) {
        const rest = parts[parts.length - 1];
        const underIdx = rest.indexOf("_");
        if (underIdx > 0) {
          map[rest.substring(underIdx + 1)] = st;
          continue;
        }
      }

      // Last resort: match entity_id against known suffixes
      const objId = ent.entity_id.replace(/^[^.]+\./, "");
      const KNOWN = ["phase","days_in_phase","days_until_watering","nutrient_plan",
        "active_channels","phase_timeline","next_phase","status","plant_count","needs_attention"];
      for (const s of KNOWN) {
        if (objId.endsWith("_" + s)) { map[s] = st; break; }
      }
    }
    return map;
  }

  _getDeviceName() {
    const id = this._config.device_id;
    if (!id || !this._hass) return null;
    const dev = Object.values(this._hass.devices || {}).find((d) => d.id === id);
    return dev ? dev.name_by_user || dev.name : null;
  }

  /* ---- DOM ------------------------------------------------------ */

  _renderPreview() {
    if (!this.shadowRoot) return;
    this._built = false;
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
        <div class="hp-watering hp-watering--today">
          <ha-icon icon="mdi:watering-can" class="hp-watering__icon"></ha-icon>
          <div class="hp-watering__info">
            <div class="hp-watering__label">Heute giessen!</div>
            <div class="hp-watering__value">Heute faellig</div>
            <div class="hp-watering__detail">Intervall: 5 Tage</div>
          </div>
        </div>
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
      </ha-card>
    `;
  }

  _update() {
    if (!this.shadowRoot) return;
    if (this._isPreview) {
      this._renderPreview();
      return;
    }
    if (!this._hass || !this._config || !this._config.device_id) return;

    const ents = this._getEntityMap();

    if (Object.keys(ents).length === 0) {
      this.shadowRoot.innerHTML = `
        <style>${HP_STYLES}</style>
        <ha-card><div class="hp-error">Device nicht gefunden oder keine Entities</div></ha-card>
      `;
      this._built = false;
      return;
    }

    const phaseObj     = ents["phase"];
    const daysObj      = ents["days_in_phase"];
    const waterObj     = ents["days_until_watering"];
    const nutrientObj  = ents["nutrient_plan"];
    const channelsObj  = ents["active_channels"];

    const currentPhase = phaseObj?.state || "—";
    const daysInPhase  = daysObj?.state;
    const plantName    = this._config.title || this._getDeviceName() || "Pflanze";

    // Build HTML
    const kamiUrl = _hpKamiSvg(currentPhase);
    const kamiHtml = kamiUrl
      ? `<img class="hp-header__kami" src="${kamiUrl}" alt="${_hpEscape(currentPhase)}" />`
      : `<span class="hp-header__icon">\uD83C\uDF31</span>`;

    const phaseText = _hpPhaseLabel(currentPhase);
    const daysText = daysInPhase != null && daysInPhase !== "unknown"
      ? ` \u2014 Tag ${_hpEscape(String(daysInPhase))}`
      : "";

    let html = `
      <style>${HP_STYLES}</style>
      <ha-card>
        <div class="hp-header">
          ${kamiHtml}
          <div class="hp-header__text">
            <span class="hp-header__name">${_hpEscape(plantName)}</span>
            <span class="hp-header__phase">${_hpEscape(phaseText)}${daysText}</span>
          </div>
    `;

    // Days badge (days in phase)
    if (daysInPhase != null && daysInPhase !== "unknown") {
      html += `
          <div class="hp-header__days">
            ${_hpEscape(String(daysInPhase))}<small>d</small>
          </div>
      `;
    }

    html += `</div>`; // close header

    // --- Watering section ---
    if (this._config.show_watering !== false) {
      const rawState = waterObj?.state;
      const daysUntil = rawState != null && rawState !== "unknown" && rawState !== "unavailable"
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
            <div class="hp-watering__value">${_hpEscape(statusValue)}</div>
            ${statusDetail ? `<div class="hp-watering__detail">${_hpEscape(statusDetail)}</div>` : ""}
          </div>
        </div>
      `;
    }

    // --- Fertilizer section ---
    if (this._config.show_fertilizer !== false) {
      const planName = nutrientObj?.state;
      const hasPlan = planName && planName !== "unknown" && planName !== "None";
      const channelAttrs = channelsObj?.attributes || {};
      const channelIds = channelAttrs.channel_ids || [];

      if (hasPlan || channelIds.length > 0) {
        html += `
          <div class="hp-fert">
            <div class="hp-fert__header">
              <ha-icon icon="mdi:bottle-tonic" class="hp-fert__icon"></ha-icon>
              <span class="hp-fert__plan-name">${_hpEscape(hasPlan ? planName : "Duenger")}</span>
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
              html += `<div class="hp-fert__channel-label">${_hpEscape(label)}</div>`;
            }
            html += `<div class="hp-fert__dosages">`;
            for (const [product, ml] of Object.entries(dosages)) {
              html += `
                <span class="hp-fert__dosage">
                  ${_hpEscape(product)} <span class="hp-fert__dosage-ml">${ml} ml/L</span>
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
