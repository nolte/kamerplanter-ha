import {
  KamerplanterCardEditor,
  escapeAttr,
  escapeHtml,
  isUnavailableState,
  t,
} from "./kamerplanter-card-common.js";

/* ================================================================== *
 *  i18n catalog (WP-16) — card-local de/en labels                     *
 * ================================================================== */

const CATALOG = {
  de: {
    default_title: "Mix Rezept",
    editor_title: "Titel",
    editor_channels: "Mix-Kanäle",
    no_entries: "Keine Einträge konfiguriert",
    no_dosages: "Keine Dosierungen",
    entity_not_found: "Entity {0} nicht gefunden",
    channel_unavailable: "Kanal nicht verfügbar",
    mode_bar_aria: "Anzeigemodus",
    mode_per_l: "ml/L",
    mode_tank_can: "Tank/Kanne",
    mode_custom: "Frei",
    unit_ml: "ml",
    unit_ml_per_l: "ml/L",
    unit_liter: "L",
    volume_aria: "Volumen in Liter",
  },
  en: {
    default_title: "Mix Recipe",
    editor_title: "Title",
    editor_channels: "Mix Channels",
    no_entries: "No entries configured",
    no_dosages: "No dosages",
    entity_not_found: "Entity {0} not found",
    channel_unavailable: "Channel unavailable",
    mode_bar_aria: "Display mode",
    mode_per_l: "ml/L",
    mode_tank_can: "Tank/Can",
    mode_custom: "Custom",
    unit_ml: "ml",
    unit_ml_per_l: "ml/L",
    unit_liter: "L",
    volume_aria: "Volume in liters",
  },
};

/**
 * Format a numeric value for the current HA locale (WP-16). Non-finite values
 * are HTML-escaped so malicious backend payloads cannot inject markup.
 */
function fmtNum(hass, value, maxFrac = 1) {
  const n = Number(value);
  if (!Number.isFinite(n)) return escapeHtml(String(value));
  const locale = hass?.locale?.language || hass?.language || "en";
  try {
    return new Intl.NumberFormat(locale, {
      maximumFractionDigits: maxFrac,
    }).format(n);
  } catch (_e) {
    return String(n);
  }
}

/* ================================================================== *
 *  Styles (shared between preview and live render)                    *
 * ================================================================== */

const MIX_STYLES = `
        :host { display: block; overflow: hidden; box-sizing: border-box; }
        ha-card { padding: 0; overflow: hidden; }
        .card-header { padding: 12px 16px 0; display: flex; align-items: center; justify-content: space-between; }
        .card-title { font-size: 1.1em; font-weight: 500; }
        .card-content { padding: 8px 16px 16px; }
        .mode-bar { display: flex; border: 1px solid var(--divider-color, #bdbdbd); border-radius: 8px; overflow: hidden; margin-bottom: 12px; }
        .seg-btn { flex: 1; padding: 6px 0; border: none; background: transparent; font-size: 0.8em; font-weight: 500; color: var(--secondary-text-color, #757575); cursor: pointer; transition: all 0.15s; border-right: 1px solid var(--divider-color, #bdbdbd); text-decoration: none; }
        .seg-btn:last-child { border-right: none; }
        .seg-btn.active { background: var(--primary-color, #1976d2); color: var(--text-primary-color, #fff); font-weight: 700; text-decoration: underline; text-underline-offset: 3px; }
        .seg-btn:not(.active):hover { background: var(--secondary-background-color, #f5f5f5); }
        .seg-btn:focus-visible { outline: 2px solid var(--primary-color, #1976d2); outline-offset: -2px; }
        .vol-input-wrap { display: inline-flex; align-items: center; gap: 2px; min-height: 40px; background: var(--secondary-background-color, #f5f5f5); border: 1px solid var(--divider-color, #bdbdbd); border-radius: 6px; padding: 1px 6px 1px 2px; }
        .vol-input { width: 52px; padding: 2px 4px; border: none; background: transparent; color: var(--primary-text-color); font-size: 0.82em; font-weight: 600; text-align: right; outline: none; -moz-appearance: textfield; }
        .vol-input::-webkit-outer-spin-button, .vol-input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
        .vol-input:focus-visible { outline: 2px solid var(--primary-color, #1976d2); border-radius: 4px; }
        .vol-unit { font-size: 0.75em; color: var(--secondary-text-color, #757575); font-weight: 500; }
        .channel { margin-bottom: 16px; }
        .channel:last-child { margin-bottom: 0; }
        .channel-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; padding-bottom: 4px; border-bottom: 1px solid var(--divider-color, #e0e0e0); }
        .channel-name { font-weight: 500; font-size: 0.95em; color: var(--primary-text-color); }
        .channel-badges { display: flex; gap: 4px; }
        .badge { font-size: 0.72em; padding: 2px 8px; border-radius: 10px; font-weight: 600; }
        .badge.week { background: var(--secondary-background-color, #03a9f4); color: var(--primary-text-color, #fff); }
        .badge.vol { background: var(--secondary-background-color, #e8f5e9); color: var(--primary-text-color, #2e7d32); }
        .dosage-list { display: flex; flex-direction: column; gap: 4px; }
        .dosage-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 4px 0; border-bottom: 1px solid var(--divider-color, #f0f0f0); }
        .dosage-row:last-child { border-bottom: none; }
        .product-name { flex: 1 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 0.9em; color: var(--primary-text-color); }
        .dosage-values { flex: 0 0 auto; display: flex; align-items: baseline; gap: 6px; white-space: nowrap; }
        .ml-value { font-size: 0.9em; font-weight: 600; color: var(--primary-text-color); }
        .ml-sub { font-size: 0.72em; color: var(--secondary-text-color, #9e9e9e); }
        .empty { font-size: 0.85em; color: var(--secondary-text-color, #9e9e9e); font-style: italic; }
        .missing { color: var(--error-color, #db4437); font-size: 0.85em; }
`;

/**
 * Build mix card editor schema.
 * Uses selector: { entity: { multiple: true } } — renders ha-entities-picker
 * with native Add/Remove/Reorder, no manual list management needed
 * (UI-NFR-015 §2.7). Labels are localized via the card catalog (WP-16).
 */
function _buildMixSchema(hass) {
  const mixEntities = hass
    ? Object.keys(hass.states).filter(
        (id) => id.startsWith("sensor.kp_") && id.endsWith("_mix")
      )
    : [];
  return [
    { name: "title", label: t(CATALOG, "editor_title", hass), selector: { text: {} } },
    { name: "entities", label: t(CATALOG, "editor_channels", hass), required: true,
      selector: { entity: { multiple: true, include_entities: mixEntities } } },
  ];
}

/**
 * Kamerplanter Mix Card Editor — shared ha-form editor base
 * (UI-NFR-015 §2.1). No Shadow DOM (UI-NFR-015 R-022).
 */
class KamerplanterMixCardEditor extends KamerplanterCardEditor {
  _defaultConfig() {
    return { entities: [], title: "" };
  }

  _schema(hass) {
    return _buildMixSchema(hass);
  }
}
customElements.define("kamerplanter-mix-card-editor", KamerplanterMixCardEditor);

/**
 * Kamerplanter Mix Card
 *
 * Three display modes:
 *   "perL"   — ml per Liter (default)
 *   "ka"     — total ml using KA volume (tank / watering can)
 *   "custom" — total ml using user-entered custom volume
 */
class KamerplanterMixCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._mode = "perL";
    this._customVols = {};
  }

  connectedCallback() {
    if (this._config) this._render();
  }

  set hass(hass) {
    const entities = (this._config?.entities || []).filter(Boolean);
    const changed = !this._hass || entities.some(
      id => this._hass.states[id] !== hass.states[id]
    );
    this._hass = hass;
    if (changed && this._config) this._render();
  }

  setConfig(config) {
    // Do NOT gate on a persisted __preview flag: HA stores getStubConfig() as
    // the card's starting config, so a flag would stick and pin the card to the
    // static mock on a real dashboard. Missing entities are handled at render
    // time (config hint) instead of throwing, so the card-picker gallery — which
    // sets `this.preview` only AFTER setConfig — is never broken.
    this._config = config;
  }

  getCardSize() { return 3; }
  getGridOptions() { return { columns: 6, min_columns: 6, rows: 2, min_rows: 1 }; }
  static getConfigElement() { return document.createElement("kamerplanter-mix-card-editor"); }
  static getStubConfig() { return { entities: [], title: "" }; }

  _updateDosages(entityId, vol) {
    const stateObj = this._hass.states[entityId];
    if (!stateObj) return;
    const attrs = stateObj.attributes;
    const sel = window.CSS && CSS.escape ? CSS.escape(entityId) : entityId;
    const input = this.shadowRoot.querySelector(`.vol-input[data-entity="${sel}"]`);
    if (!input) return;
    const channelDiv = input.closest(".channel");
    if (!channelDiv) return;
    const rows = channelDiv.querySelectorAll(".dosage-row");
    const numVol = Number(vol);
    const unitMl = t(CATALOG, "unit_ml", this._hass);
    const dosages = [];
    for (const [key, val] of Object.entries(attrs)) {
      if (key.endsWith("(ml/L)") && val != null) {
        const mlPerL = Number(val);
        if (Number.isFinite(mlPerL)) dosages.push({ name: key.replace(" (ml/L)", ""), mlPerL });
      }
    }
    dosages.sort((a, b) => b.mlPerL - a.mlPerL);
    let i = 0;
    for (const d of dosages) {
      if (rows[i]) { const mlEl = rows[i].querySelector(".ml-value"); if (mlEl) mlEl.textContent = `${fmtNum(this._hass, d.mlPerL * numVol, 1)} ${unitMl}`; }
      i++;
    }
  }

  _channelVol(entityId) {
    if (!entityId || !this._hass) return null;
    const s = this._hass.states[entityId];
    if (!s) return null;
    const v = s.attributes.volume_liters;
    return v && v > 0 ? v : null;
  }

  _renderPreview() {
    if (!this.shadowRoot) return;
    const hass = this._hass;
    const unitMl = escapeHtml(t(CATALOG, "unit_ml", hass));
    const unitMlL = escapeHtml(t(CATALOG, "unit_ml_per_l", hass));
    const unitL = escapeHtml(t(CATALOG, "unit_liter", hass));
    const sample = [
      { name: "Flora Micro", mlPerL: 1.5, ml: 30 },
      { name: "Flora Bloom", mlPerL: 2.5, ml: 50 },
      { name: "CalMag", mlPerL: 1.0, ml: 20 },
    ];
    const seg = (label, active) =>
      `<button class="seg-btn ${active ? "active" : ""}" role="tab" aria-selected="${active ? "true" : "false"}" tabindex="-1">${escapeHtml(label)}</button>`;
    const rowsHtml = sample
      .map(
        (d) =>
          `<div class="dosage-row"><span class="product-name">${escapeHtml(d.name)}</span><span class="dosage-values"><span class="ml-value">${fmtNum(hass, d.ml, 1)} ${unitMl}</span><span class="ml-sub">${fmtNum(hass, d.mlPerL, 2)} ${unitMlL}</span></span></div>`
      )
      .join("");
    this.shadowRoot.innerHTML = `
      <style>${MIX_STYLES}</style>
      <ha-card>
        <div class="card-header"><span class="card-title">${escapeHtml(t(CATALOG, "default_title", hass))}</span></div>
        <div class="card-content">
          <div class="mode-bar" role="tablist" aria-label="${escapeAttr(t(CATALOG, "mode_bar_aria", hass))}">
            ${seg(t(CATALOG, "mode_per_l", hass), false)}
            ${seg(t(CATALOG, "mode_tank_can", hass), true)}
            ${seg(t(CATALOG, "mode_custom", hass), false)}
          </div>
          <div class="channel">
            <div class="channel-header">
              <span class="channel-name">Blühdüngung Woche 4</span>
              <span class="channel-badges">
                <span class="badge week">W4</span>
                <span class="badge vol">${fmtNum(hass, 20)} ${unitL}</span>
              </span>
            </div>
            <div class="dosage-list">${rowsHtml}</div>
          </div>
        </div>
      </ha-card>`;
  }

  _render() {
    if (!this._config) return;
    // `this.preview` is set by HA only when the card is shown in the card-picker
    // gallery. A persisted __preview flag is intentionally ignored so cards that
    // captured the old getStubConfig still recover to live data on reload.
    if (this.preview) {
      this._renderPreview();
      return;
    }
    if (!this._config.entities || !this._config.entities.length) {
      this.shadowRoot.innerHTML = `<ha-card><div style="padding:16px;color:var(--secondary-text-color)">${escapeHtml(t(CATALOG, "no_entries", this._hass))}</div></ha-card>`;
      return;
    }
    if (!this._hass) return;
    const hass = this._hass;
    const title = this._config.title || t(CATALOG, "default_title", hass);
    const mode = this._mode;
    const unitMl = escapeHtml(t(CATALOG, "unit_ml", hass));
    const unitMlL = escapeHtml(t(CATALOG, "unit_ml_per_l", hass));
    const unitL = escapeHtml(t(CATALOG, "unit_liter", hass));

    let anyKaVol = false;
    for (const eid of this._config.entities) { if (this._channelVol(eid)) { anyKaVol = true; break; } }
    for (const eid of this._config.entities) { if (!(eid in this._customVols)) this._customVols[eid] = this._channelVol(eid) || 10; }

    let channelsHtml = "";
    for (const entityId of this._config.entities) {
      const safeId = escapeHtml(entityId);
      const stateObj = this._hass.states[entityId];
      if (!stateObj) { channelsHtml += `<div class="channel missing">${escapeHtml(t(CATALOG, "entity_not_found", hass, safeId))}</div>`; continue; }
      const attrs = stateObj.attributes;
      const channelName = escapeHtml(attrs.friendly_name || entityId);
      // Explizites Handling fuer unavailable/unknown statt stummer leerer Kanaele.
      if (isUnavailableState(stateObj.state)) {
        channelsHtml += `<div class="channel unavailable"><div class="channel-header"><span class="channel-name">${channelName}</span></div><div class="empty">${escapeHtml(t(CATALOG, "channel_unavailable", hass))}</div></div>`;
        continue;
      }
      const week = Number(attrs.current_week);
      const kaVol = this._channelVol(entityId);
      const customVol = Number(this._customVols[entityId]) || 10;
      let effVol = null;
      if (mode === "ka" && kaVol) effVol = Number(kaVol);
      else if (mode === "custom" && customVol > 0) effVol = customVol;

      const dosages = [];
      for (const [key, val] of Object.entries(attrs)) {
        if (key.endsWith("(ml/L)") && val != null) {
          const mlPerL = Number(val);
          if (Number.isFinite(mlPerL)) dosages.push({ name: key.replace(" (ml/L)", ""), mlPerL });
        }
      }
      dosages.sort((a, b) => b.mlPerL - a.mlPerL);

      channelsHtml += `<div class="channel"><div class="channel-header">`;
      channelsHtml += `<span class="channel-name">${channelName}</span><span class="channel-badges">`;
      if (Number.isFinite(week) && week > 0) channelsHtml += `<span class="badge week">W${week}</span>`;
      if (mode === "custom") {
        channelsHtml += `<span class="vol-input-wrap"><input type="number" class="vol-input" aria-label="${escapeAttr(t(CATALOG, "volume_aria", hass))}" data-entity="${escapeAttr(entityId)}" value="${Number(customVol)}" min="0.1" step="0.5" /><span class="vol-unit">${unitL}</span></span>`;
      } else if (effVol) {
        channelsHtml += `<span class="badge vol">${fmtNum(hass, effVol)} ${unitL}</span>`;
      }
      channelsHtml += `</span></div>`;

      if (!dosages.length) {
        channelsHtml += `<div class="empty">${escapeHtml(t(CATALOG, "no_dosages", hass))}</div>`;
      } else {
        channelsHtml += `<div class="dosage-list">`;
        for (const d of dosages) {
          const valHtml = effVol
            ? `<span class="ml-value">${fmtNum(hass, d.mlPerL * effVol, 1)} ${unitMl}</span><span class="ml-sub">${fmtNum(hass, d.mlPerL, 2)} ${unitMlL}</span>`
            : `<span class="ml-value">${fmtNum(hass, d.mlPerL, 2)} ${unitMlL}</span>`;
          channelsHtml += `<div class="dosage-row"><span class="product-name">${escapeHtml(d.name)}</span><span class="dosage-values">${valHtml}</span></div>`;
        }
        channelsHtml += `</div>`;
      }
      channelsHtml += `</div>`;
    }

    const seg = (id, label, active) => `<button class="seg-btn ${active ? "active" : ""}" role="tab" aria-selected="${active ? "true" : "false"}" data-mode="${escapeAttr(id)}">${escapeHtml(label)}</button>`;
    let modeBarHtml = `<div class="mode-bar" role="tablist" aria-label="${escapeAttr(t(CATALOG, "mode_bar_aria", hass))}">`;
    modeBarHtml += seg("perL", t(CATALOG, "mode_per_l", hass), mode === "perL");
    if (anyKaVol) modeBarHtml += seg("ka", t(CATALOG, "mode_tank_can", hass), mode === "ka");
    modeBarHtml += seg("custom", t(CATALOG, "mode_custom", hass), mode === "custom");
    modeBarHtml += `</div>`;

    this.shadowRoot.innerHTML = `
      <style>${MIX_STYLES}</style>
      <ha-card>
        <div class="card-header"><span class="card-title">${escapeHtml(title)}</span></div>
        <div class="card-content">
          ${modeBarHtml}
          ${channelsHtml}
        </div>
      </ha-card>`;

    this.shadowRoot.querySelectorAll(".seg-btn").forEach((btn) => {
      btn.addEventListener("click", () => { this._mode = btn.dataset.mode; this._render(); });
    });
    this.shadowRoot.querySelectorAll(".vol-input").forEach((input) => {
      input.addEventListener("input", (e) => {
        const v = parseFloat(e.target.value);
        const eid = e.target.dataset.entity;
        if (v > 0 && eid) { this._customVols[eid] = v; this._updateDosages(eid, v); }
      });
    });
  }
}

customElements.define("kamerplanter-mix-card", KamerplanterMixCard);
window.customCards = window.customCards || [];
window.customCards.push({ type: "kamerplanter-mix-card", name: "Kamerplanter Mix Rezept", description: "Dünger-Dosierungen mit ml/L, Tank/Kanne oder freier Menge", preview: true });
