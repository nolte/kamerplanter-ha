/**
 * ha-form ready singleton (UI-NFR-015 §2.2).
 */
const _haFormReadyMix = (async () => {
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
 * Build mix card editor schema.
 * Uses selector: { entity: { multiple: true } } — renders ha-entities-picker
 * with native Add/Remove/Reorder, no manual list management needed
 * (UI-NFR-015 §2.7).
 */
function _buildMixSchema(hass) {
  const mixEntities = hass
    ? Object.keys(hass.states).filter(
        (id) => id.startsWith("sensor.kp_") && id.endsWith("_mix")
      )
    : [];
  return [
    { name: "title",    label: "Titel",          selector: { text: {} } },
    { name: "entities", label: "Mix-Kan\u00e4le", required: true,
      selector: { entity: { multiple: true, include_entities: mixEntities } } },
  ];
}

/**
 * Kamerplanter Mix Card Editor
 * Uses ha-form + schema — identical pattern to official HA card editors
 * (UI-NFR-015 §2.1). No Shadow DOM (UI-NFR-015 R-022).
 */
class KamerplanterMixCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = { entities: [], title: "", ...config };
    if (this._hass) this._scheduleRender();
  }

  set hass(hass) {
    this._hass = hass;
    this._scheduleRender();
  }

  async _scheduleRender() {
    await _haFormReadyMix;
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
    this._form.schema = _buildMixSchema(this._hass);
    this._form.data = this._config;
    this._form.computeLabel = (schema) => schema.label || schema.name;
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
    this._config = config;
    this._isPreview = !!config.__preview;
    if (!this._isPreview && (!config.entities || !config.entities.length)) {
      throw new Error("Please define at least one entity");
    }
  }

  getCardSize() { return 3; }
  getGridOptions() { return { columns: 6, min_columns: 3, rows: 3, min_rows: 2 }; }
  static getConfigElement() { return document.createElement("kamerplanter-mix-card-editor"); }
  static getStubConfig() { return { __preview: true, entities: [], title: "Mix Rezept" }; }

  _updateDosages(entityId, vol) {
    const stateObj = this._hass.states[entityId];
    if (!stateObj) return;
    const attrs = stateObj.attributes;
    const input = this.shadowRoot.querySelector(`.vol-input[data-entity="${entityId}"]`);
    if (!input) return;
    const channelDiv = input.closest(".channel");
    if (!channelDiv) return;
    const rows = channelDiv.querySelectorAll(".dosage-row");
    const dosages = [];
    for (const [key, val] of Object.entries(attrs)) {
      if (key.endsWith("(ml/L)") && val != null) dosages.push({ name: key.replace(" (ml/L)", ""), mlPerL: val });
    }
    dosages.sort((a, b) => b.mlPerL - a.mlPerL);
    let i = 0;
    for (const d of dosages) {
      if (rows[i]) { const mlEl = rows[i].querySelector(".ml-value"); if (mlEl) mlEl.textContent = `${(d.mlPerL * vol).toFixed(1)} ml`; }
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
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; overflow: hidden; box-sizing: border-box; }
        ha-card { padding: 0; overflow: hidden; }
        .card-header { padding: 12px 16px 0; display: flex; align-items: center; justify-content: space-between; }
        .card-title { font-size: 1.1em; font-weight: 500; }
        .card-content { padding: 8px 16px 16px; }
        .mode-bar { display: flex; border: 1px solid #bdbdbd; border-radius: 8px; overflow: hidden; margin-bottom: 12px; }
        .seg-btn { flex: 1; padding: 6px 0; border: none; background: transparent; font-size: 0.8em; font-weight: 500; color: #757575; cursor: default; border-right: 1px solid #bdbdbd; }
        .seg-btn:last-child { border-right: none; }
        .seg-btn.active { background: #1976d2; color: #fff; font-weight: 600; }
        .channel { margin-bottom: 16px; }
        .channel:last-child { margin-bottom: 0; }
        .channel-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; padding-bottom: 4px; border-bottom: 1px solid #e0e0e0; }
        .channel-name { font-weight: 500; font-size: 0.95em; }
        .channel-badges { display: flex; gap: 4px; }
        .badge { font-size: 0.72em; padding: 2px 8px; border-radius: 10px; font-weight: 600; }
        .badge.week { background: #03a9f4; color: #fff; }
        .badge.vol { background: #e8f5e9; color: #2e7d32; }
        .dosage-list { display: flex; flex-direction: column; gap: 4px; }
        .dosage-row { display: flex; align-items: center; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid #f0f0f0; }
        .dosage-row:last-child { border-bottom: none; }
        .product-name { font-size: 0.9em; }
        .dosage-values { display: flex; align-items: baseline; gap: 6px; white-space: nowrap; }
        .ml-value { font-size: 0.9em; font-weight: 600; }
        .ml-sub { font-size: 0.72em; color: #9e9e9e; }
      </style>
      <ha-card>
        <div class="card-header"><span class="card-title">Mix Rezept</span></div>
        <div class="card-content">
          <div class="mode-bar">
            <button class="seg-btn">ml/L</button>
            <button class="seg-btn active">Tank/Kanne</button>
            <button class="seg-btn">Frei</button>
          </div>
          <div class="channel">
            <div class="channel-header">
              <span class="channel-name">Bluehdaengung Woche 4</span>
              <span class="channel-badges">
                <span class="badge week">W4</span>
                <span class="badge vol">20 L</span>
              </span>
            </div>
            <div class="dosage-list">
              <div class="dosage-row">
                <span class="product-name">Flora Micro</span>
                <span class="dosage-values"><span class="ml-value">30.0 ml</span><span class="ml-sub">1.5 ml/L</span></span>
              </div>
              <div class="dosage-row">
                <span class="product-name">Flora Bloom</span>
                <span class="dosage-values"><span class="ml-value">50.0 ml</span><span class="ml-sub">2.5 ml/L</span></span>
              </div>
              <div class="dosage-row">
                <span class="product-name">CalMag</span>
                <span class="dosage-values"><span class="ml-value">20.0 ml</span><span class="ml-sub">1.0 ml/L</span></span>
              </div>
            </div>
          </div>
        </div>
      </ha-card>`;
  }

  _render() {
    if (!this._config) return;
    if (this._isPreview) {
      this._renderPreview();
      return;
    }
    if (!this._hass) return;
    const title = this._config.title || "Mix Rezept";
    const mode = this._mode;

    let anyKaVol = false;
    for (const eid of this._config.entities) { if (this._channelVol(eid)) { anyKaVol = true; break; } }
    for (const eid of this._config.entities) { if (!(eid in this._customVols)) this._customVols[eid] = this._channelVol(eid) || 10; }

    let channelsHtml = "";
    for (const entityId of this._config.entities) {
      const stateObj = this._hass.states[entityId];
      if (!stateObj) { channelsHtml += `<div class="channel missing">Entity ${entityId} nicht gefunden</div>`; continue; }
      const attrs = stateObj.attributes;
      const channelName = attrs.friendly_name || entityId;
      const currentWeek = attrs.current_week;
      const kaVol = this._channelVol(entityId);
      const customVol = this._customVols[entityId] || 10;
      let effVol = null;
      if (mode === "ka" && kaVol) effVol = kaVol;
      else if (mode === "custom" && customVol > 0) effVol = customVol;

      const dosages = [];
      for (const [key, val] of Object.entries(attrs)) {
        if (key.endsWith("(ml/L)") && val != null) dosages.push({ name: key.replace(" (ml/L)", ""), mlPerL: val });
      }
      dosages.sort((a, b) => b.mlPerL - a.mlPerL);

      channelsHtml += `<div class="channel"><div class="channel-header">`;
      channelsHtml += `<span class="channel-name">${channelName}</span><span class="channel-badges">`;
      if (currentWeek) channelsHtml += `<span class="badge week">W${currentWeek}</span>`;
      if (mode === "custom") {
        channelsHtml += `<span class="vol-input-wrap"><input type="number" class="vol-input" data-entity="${entityId}" value="${customVol}" min="0.1" step="0.5" /><span class="vol-unit">L</span></span>`;
      } else if (effVol) {
        channelsHtml += `<span class="badge vol">${effVol} L</span>`;
      }
      channelsHtml += `</span></div>`;

      if (!dosages.length) {
        channelsHtml += `<div class="empty">Keine Dosierungen</div>`;
      } else {
        channelsHtml += `<div class="dosage-list">`;
        for (const d of dosages) {
          const valHtml = effVol
            ? `<span class="ml-value">${(d.mlPerL * effVol).toFixed(1)} ml</span><span class="ml-sub">${d.mlPerL} ml/L</span>`
            : `<span class="ml-value">${d.mlPerL} ml/L</span>`;
          channelsHtml += `<div class="dosage-row"><span class="product-name">${d.name}</span><span class="dosage-values">${valHtml}</span></div>`;
        }
        channelsHtml += `</div>`;
      }
      channelsHtml += `</div>`;
    }

    const seg = (id, label, active) => `<button class="seg-btn ${active ? "active" : ""}" data-mode="${id}">${label}</button>`;
    let modeBarHtml = `<div class="mode-bar">`;
    modeBarHtml += seg("perL", "ml/L", mode === "perL");
    if (anyKaVol) modeBarHtml += seg("ka", "Tank/Kanne", mode === "ka");
    modeBarHtml += seg("custom", "Frei", mode === "custom");
    modeBarHtml += `</div>`;

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; overflow: hidden; box-sizing: border-box; }
        ha-card { padding: 0; overflow: hidden; }
        .card-header { padding: 12px 16px 0; display: flex; align-items: center; justify-content: space-between; }
        .card-title { font-size: 1.1em; font-weight: 500; }
        .card-content { padding: 8px 16px 16px; }
        .mode-bar { display: flex; border: 1px solid #bdbdbd; border-radius: 8px; overflow: hidden; margin-bottom: 12px; }
        .seg-btn { flex: 1; padding: 6px 0; border: none; background: transparent; font-size: 0.8em; font-weight: 500; color: #757575; cursor: pointer; transition: all 0.15s; border-right: 1px solid #bdbdbd; }
        .seg-btn:last-child { border-right: none; }
        .seg-btn.active { background: #1976d2; color: #fff; font-weight: 600; }
        .seg-btn:not(.active):hover { background: #f5f5f5; }
        .vol-input-wrap { display: inline-flex; align-items: center; gap: 2px; background: #f5f5f5; border: 1px solid #bdbdbd; border-radius: 6px; padding: 1px 6px 1px 2px; }
        .vol-input { width: 52px; padding: 2px 4px; border: none; background: transparent; font-size: 0.82em; font-weight: 600; text-align: right; outline: none; -moz-appearance: textfield; }
        .vol-input::-webkit-outer-spin-button, .vol-input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
        .vol-unit { font-size: 0.75em; color: #757575; font-weight: 500; }
        .channel { margin-bottom: 16px; }
        .channel:last-child { margin-bottom: 0; }
        .channel-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; padding-bottom: 4px; border-bottom: 1px solid #e0e0e0; }
        .channel-name { font-weight: 500; font-size: 0.95em; }
        .channel-badges { display: flex; gap: 4px; }
        .badge { font-size: 0.72em; padding: 2px 8px; border-radius: 10px; font-weight: 600; }
        .badge.week { background: #03a9f4; color: #fff; }
        .badge.vol { background: #e8f5e9; color: #2e7d32; }
        .dosage-list { display: flex; flex-direction: column; gap: 4px; }
        .dosage-row { display: flex; align-items: center; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid #f0f0f0; }
        .dosage-row:last-child { border-bottom: none; }
        .product-name { font-size: 0.9em; }
        .dosage-values { display: flex; align-items: baseline; gap: 6px; white-space: nowrap; }
        .ml-value { font-size: 0.9em; font-weight: 600; }
        .ml-sub { font-size: 0.72em; color: #9e9e9e; }
        .empty { font-size: 0.85em; color: #9e9e9e; font-style: italic; }
        .missing { color: #db4437; font-size: 0.85em; }
      </style>
      <ha-card>
        <div class="card-header"><span class="card-title">${title}</span></div>
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
window.customCards.push({ type: "kamerplanter-mix-card", name: "Kamerplanter Mix Rezept", description: "D\u00fcnger-Dosierungen mit ml/L, Tank/Kanne oder freier Menge", preview: true });
