/**
 * ha-form ready singleton — waits for ha-form which transitively loads
 * ha-selector-entity → ha-entity-picker. No need to load ha-entity-picker
 * directly (UI-NFR-015 §2.2).
 */
const _haFormReady = (async () => {
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
 * Build tank card editor schema (UI-NFR-015 §2.3).
 * Rebuilt on each render so include_entities stays current with hass.states.
 */
function _buildTankSchema(hass) {
  const tankEntities = hass
    ? Object.keys(hass.states).filter(
        (id) => {
          if (!id.startsWith("sensor.")) return false;
          const s = hass.states[id];
          // Primary: attribute check; fallback: entity_id pattern
          return (s && s.attributes && s.attributes.tank_key !== undefined)
              || id.endsWith("_tank_info");
        }
      )
    : [];
  return [
    { name: "title",          label: "Titel (optional)",                        selector: { text: {} } },
    { name: "tank_entity",    label: "Tank (Kamerplanter)",    required: true,   selector: { entity: { include_entities: tankEntities } } },
    { name: "show_ph_tank",   label: "pH im Fass anzeigen",                      selector: { boolean: {} } },
    { name: "show_ph_badge",  label: "pH als Badge anzeigen",                    selector: { boolean: {} } },
    { name: "show_ec_tank",   label: "EC im Fass anzeigen",                      selector: { boolean: {} } },
    { name: "show_ec_badge",  label: "EC als Badge anzeigen",                    selector: { boolean: {} } },
    { name: "show_temp_tank", label: "Temperatur im Fass anzeigen",              selector: { boolean: {} } },
    { name: "show_temp_badge",label: "Temperatur als Badge anzeigen",            selector: { boolean: {} } },
    { name: "ph_entity",      label: "pH-Sensor (optional, \u00fcberschreibt KA)",       selector: { entity: { domain: ["sensor"] } } },
    { name: "ec_entity",      label: "EC-Sensor (optional, \u00fcberschreibt KA)",       selector: { entity: { domain: ["sensor"] } } },
    { name: "temp_entity",    label: "Temperatur-Sensor (optional, \u00fcberschreibt KA)", selector: { entity: { domain: ["sensor"] } } },
  ];
}

/**
 * Kamerplanter Tank Card Editor
 * Uses ha-form + schema — identical pattern to official HA card editors
 * (UI-NFR-015 §2.1). No Shadow DOM (UI-NFR-015 R-022).
 */
class KamerplanterTankCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = {
      tank_entity: "", title: "",
      ph_entity: "", ec_entity: "", temp_entity: "",
      show_ph_tank: true, show_ph_badge: true,
      show_ec_tank: true, show_ec_badge: true,
      show_temp_tank: true, show_temp_badge: true,
      ...config,
    };
    if (this._hass) this._scheduleRender();
  }

  set hass(hass) {
    this._hass = hass;
    this._scheduleRender();
  }

  async _scheduleRender() {
    await _haFormReady;
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
    this._form.schema = _buildTankSchema(this._hass);
    this._form.data = this._config;
    this._form.computeLabel = (schema) => schema.label || schema.name;
  }
}
customElements.define("kamerplanter-tank-card-editor", KamerplanterTankCardEditor);

/**
 * Kamerplanter Tank Card
 */
class KamerplanterTankCard extends HTMLElement {
  constructor() { super(); this.attachShadow({ mode: "open" }); }

  connectedCallback() {
    if (this._config) this._render();
  }

  set hass(hass) {
    const entities = this._getMonitoredEntities();
    const changed = !this._hass || entities.some(
      id => this._hass.states[id] !== hass.states[id]
    );
    this._hass = hass;
    if (changed && this._config) this._render();
  }

  _getMonitoredEntities() {
    if (!this._config) return [];
    const ids = [this._config.tank_entity];
    if (this._config.ph_entity) ids.push(this._config.ph_entity);
    if (this._config.ec_entity) ids.push(this._config.ec_entity);
    if (this._config.temp_entity) ids.push(this._config.temp_entity);
    return ids.filter(Boolean);
  }

  setConfig(config) {
    this._isPreview = !!config.__preview;
    if (!this._isPreview && !config.tank_entity) throw new Error("Please define a tank entity");
    this._config = config;
  }

  getCardSize() { return 5; }
  getGridOptions() { return { columns: 6, min_columns: 3, rows: 5, min_rows: 4 }; }
  static getConfigElement() { return document.createElement("kamerplanter-tank-card-editor"); }
  static getStubConfig() {
    return { __preview: true, tank_entity: "", title: "", ph_entity: "", ec_entity: "", temp_entity: "",
      show_ph_tank: true, show_ph_badge: true, show_ec_tank: true, show_ec_badge: true,
      show_temp_tank: true, show_temp_badge: true };
  }

  _formatDate(isoStr) {
    if (!isoStr) return "\u2014";
    const d = new Date(isoStr);
    return `${String(d.getDate()).padStart(2,"0")}.${String(d.getMonth()+1).padStart(2,"0")}.${d.getFullYear()} ${String(d.getHours()).padStart(2,"0")}:${String(d.getMinutes()).padStart(2,"0")}`;
  }

  _sensorVal(entityId) {
    if (!entityId || !this._hass) return null;
    const s = this._hass.states[entityId];
    if (!s || s.state === "unknown" || s.state === "unavailable") return null;
    return parseFloat(s.state);
  }

  _phColor(v) { if (v==null) return "#999"; if (v<5.5||v>6.5) return "#f44336"; if (v<5.8||v>6.3) return "#ff9800"; return "#4caf50"; }
  _ecColor(v) { return v==null ? "#999" : "#1976d2"; }
  _tempColor(v) { if (v==null) return "#999"; if (v<16||v>26) return "#f44336"; if (v<18||v>24) return "#ff9800"; return "#4caf50"; }

  _buildTankSvg(ph, ec, temp, fillPct, cfg) {
    const showPh = cfg.show_ph_tank !== false && ph != null;
    const showEc = cfg.show_ec_tank !== false && ec != null;
    const showTemp = cfg.show_temp_tank !== false && temp != null;
    const waterY = 180 - (fillPct / 100) * 140;
    let waterFill = "rgba(3, 169, 244, 0.25)", waterLine = "rgba(3, 169, 244, 0.4)";
    if (ph != null) {
      if (ph >= 5.5 && ph <= 6.5) { waterFill = "rgba(76, 175, 80, 0.18)"; waterLine = "rgba(76, 175, 80, 0.35)"; }
      else { waterFill = "rgba(244, 67, 54, 0.15)"; waterLine = "rgba(244, 67, 54, 0.3)"; }
    }
    const wy = waterY;
    const wave1 = `M 30 ${wy} Q 55 ${wy-5} 80 ${wy} Q 105 ${wy+5} 130 ${wy} Q 155 ${wy-5} 180 ${wy} L 180 200 L 30 200 Z`;
    const wave2 = `M 30 ${wy} Q 55 ${wy+5} 80 ${wy} Q 105 ${wy-5} 130 ${wy} Q 155 ${wy+5} 180 ${wy} L 180 200 L 30 200 Z`;
    const labels = [];
    if (showPh) labels.push({ text: `pH ${ph.toFixed(1)}`, color: this._phColor(ph), size: 18, weight: 700 });
    if (showEc) labels.push({ text: `EC ${ec.toFixed(2)} mS`, color: this._ecColor(ec), size: 14, weight: 600 });
    if (showTemp) labels.push({ text: `${temp.toFixed(1)} \u00b0C`, color: this._tempColor(temp), size: 13, weight: 600 });
    let insideLabels = "";
    if (labels.length) {
      const totalH = labels.reduce((s, l) => s + l.size + 4, 0);
      let startY = Math.max(wy + 12, 55);
      if (startY + totalH > 195) startY = 195 - totalH;
      let curY = startY;
      for (const l of labels) { curY += l.size; insideLabels += `<text x="105" y="${curY}" text-anchor="middle" font-size="${l.size}" font-weight="${l.weight}" fill="${l.color}">${l.text}</text>`; curY += 4; }
    }
    return `<svg viewBox="0 0 210 210" xmlns="http://www.w3.org/2000/svg" width="160" height="160">
      <defs><clipPath id="tc"><rect x="32" y="22" width="146" height="176" rx="10" ry="10"/></clipPath></defs>
      <rect x="30" y="20" width="150" height="180" rx="12" ry="12" fill="none" stroke="#bdbdbd" stroke-width="3"/>
      <path d="${wave1}" fill="${waterFill}" stroke="${waterLine}" stroke-width="1" clip-path="url(#tc)">
        <animate attributeName="d" dur="3s" repeatCount="indefinite" values="${wave1};${wave2};${wave1}"/>
      </path>
      <rect x="60" y="12" width="90" height="12" rx="4" ry="4" fill="#e0e0e0" stroke="#bdbdbd" stroke-width="2"/>
      ${insideLabels}
    </svg>`;
  }

  _renderPreview() {
    if (!this.shadowRoot) return;
    // Build a preview tank SVG with mock values
    const ph = 5.9, ec = 1.42, temp = 21.3, fillPct = 72;
    const waterY = 180 - (fillPct / 100) * 140;
    const wy = waterY;
    const wave1 = `M 30 ${wy} Q 55 ${wy-5} 80 ${wy} Q 105 ${wy+5} 130 ${wy} Q 155 ${wy-5} 180 ${wy} L 180 200 L 30 200 Z`;
    const wave2 = `M 30 ${wy} Q 55 ${wy+5} 80 ${wy} Q 105 ${wy-5} 130 ${wy} Q 155 ${wy+5} 180 ${wy} L 180 200 L 30 200 Z`;
    const tankSvg = `<svg viewBox="0 0 210 210" xmlns="http://www.w3.org/2000/svg" width="140" height="140">
      <defs><clipPath id="tc"><rect x="32" y="22" width="146" height="176" rx="10" ry="10"/></clipPath></defs>
      <rect x="30" y="20" width="150" height="180" rx="12" ry="12" fill="none" stroke="#bdbdbd" stroke-width="3"/>
      <path d="${wave1}" fill="rgba(76, 175, 80, 0.18)" stroke="rgba(76, 175, 80, 0.35)" stroke-width="1" clip-path="url(#tc)">
        <animate attributeName="d" dur="3s" repeatCount="indefinite" values="${wave1};${wave2};${wave1}"/>
      </path>
      <rect x="60" y="12" width="90" height="12" rx="4" ry="4" fill="#e0e0e0" stroke="#bdbdbd" stroke-width="2"/>
      <text x="105" y="${Math.max(wy+24, 55)}" text-anchor="middle" font-size="18" font-weight="700" fill="#4caf50">pH ${ph.toFixed(1)}</text>
      <text x="105" y="${Math.max(wy+42, 73)}" text-anchor="middle" font-size="14" font-weight="600" fill="#1976d2">EC ${ec.toFixed(2)} mS</text>
      <text x="105" y="${Math.max(wy+58, 89)}" text-anchor="middle" font-size="13" font-weight="600" fill="#4caf50">${temp.toFixed(1)} \u00b0C</text>
    </svg>`;
    this.shadowRoot.innerHTML = `<style>
      :host { display: block; overflow: hidden; box-sizing: border-box; } ha-card { padding: 0; overflow: hidden; }
      .card-header { padding: 12px 16px 0; display: flex; align-items: center; justify-content: space-between; }
      .title { font-size: 1.1em; font-weight: 500; }
      .volume-badge { font-size: 0.8em; padding: 2px 10px; border-radius: 10px; background: #03a9f4; color: #fff; font-weight: 600; }
      .card-content { padding: 8px 16px 16px; }
      .tank-container { display: flex; justify-content: center; padding: 4px 0 8px; }
      .badges { display: flex; gap: 8px; justify-content: center; margin-bottom: 12px; }
      .badge { flex: 1; max-width: 110px; text-align: center; padding: 8px 6px; border-radius: 8px; background: #f5f5f5; border: 2px solid #e0e0e0; }
      .badge-label { display: block; font-size: 0.7em; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #757575; margin-bottom: 2px; }
      .badge-value { font-size: 1.2em; font-weight: 700; }
      .badge-value small { font-size: 0.65em; font-weight: 500; color: #757575; }
      .fill-section { padding-top: 10px; border-top: 1px solid #e0e0e0; }
      .fill-row { display: flex; align-items: center; gap: 8px; }
      .fill-icon { flex-shrink: 0; }
      .fill-text { display: flex; flex-direction: column; flex: 1; min-width: 0; }
      .fill-text strong { font-size: 0.85em; font-weight: 600; }
      .fill-date { font-size: 0.78em; color: #757575; }
      .fill-age-badge { font-size: 0.75em; padding: 2px 8px; border-radius: 10px; background: #f5f5f5; color: #757575; white-space: nowrap; flex-shrink: 0; }
      .fill-details-row { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; padding-left: 24px; }
      .fill-detail { font-size: 0.75em; padding: 2px 8px; border-radius: 4px; background: #f5f5f5; }
    </style>
    <ha-card>
      <div class="card-header"><span class="title">N\u00e4hrstoff-Tank</span><span class="volume-badge">50 L</span></div>
      <div class="card-content">
        <div class="tank-container">${tankSvg}</div>
        <div class="badges">
          <div class="badge" style="border-color:#4caf50"><span class="badge-label">pH</span><span class="badge-value" style="color:#4caf50">5.9</span></div>
          <div class="badge" style="border-color:#1976d2"><span class="badge-label">EC</span><span class="badge-value" style="color:#1976d2">1.42<small> mS</small></span></div>
          <div class="badge" style="border-color:#4caf50"><span class="badge-label">Temp</span><span class="badge-value" style="color:#4caf50">21.3<small> \u00b0C</small></span></div>
        </div>
        <div class="fill-section"><div class="fill-row">
          <svg class="fill-icon" width="16" height="16" viewBox="0 0 24 24" fill="#03a9f4"><path d="M12 2c-5.33 4.55-8 8.48-8 11.8 0 4.98 3.8 8.2 8 8.2s8-3.22 8-8.2C20 10.48 17.33 6.55 12 2z"/></svg>
          <span class="fill-text"><strong>Komplettwechsel</strong><span class="fill-date">02.04.2026 14:30</span></span>
          <span class="fill-age-badge">vor 3 Tagen</span>
        </div><div class="fill-details-row"><span class="fill-detail">50 L</span><span class="fill-detail">pH 5.8</span><span class="fill-detail">EC 1.40</span><span class="fill-detail">3 D\u00fcnger</span></div></div>
      </div>
    </ha-card>`;
  }

  _render() {
    if (this._isPreview) {
      this._renderPreview();
      return;
    }
    if (!this._hass || !this._config) return;
    const cfg = this._config;
    const tankState = this._hass.states[cfg.tank_entity];
    if (!tankState) {
      this.shadowRoot.innerHTML = `<ha-card><div style="padding:16px;color:#f44336">Entity ${cfg.tank_entity} nicht gefunden</div></ha-card>`; return;
    }
    const attrs = tankState.attributes;
    const title = cfg.title || attrs.friendly_name || "Tank";
    const volume = attrs.volume_liters;
    const lastFillAt = attrs.last_fill_at || null;
    const lastFillType = attrs.last_fill_type;
    const lastFillVolume = attrs.last_fill_volume || null;
    const lastFillPh = attrs.last_fill_ph != null ? attrs.last_fill_ph : null;
    const lastFillEc = attrs.last_fill_ec != null ? attrs.last_fill_ec : null;
    const fertCount = attrs.last_fill_fert_count || 0;
    const daysSince = attrs.fill_age_days;
    const ph = this._sensorVal(cfg.ph_entity || attrs.ha_ph_entity_id || "");
    const ec = this._sensorVal(cfg.ec_entity || attrs.ha_ec_entity_id || "");
    const temp = this._sensorVal(cfg.temp_entity || attrs.ha_temp_entity_id || "");
    let fillPct = 70;
    if (volume && lastFillVolume) fillPct = Math.min(100, Math.round((lastFillVolume / volume) * 100));
    const fillTypeLabels = { full_change: "Komplettwechsel", top_up: "Nachf\u00fcllen", adjustment: "Korrektur" };
    const tankSvg = this._buildTankSvg(ph, ec, temp, fillPct, cfg);
    const badges = [];
    if (cfg.show_ph_badge !== false && ph != null) badges.push(`<div class="badge" style="border-color:${this._phColor(ph)}"><span class="badge-label">pH</span><span class="badge-value" style="color:${this._phColor(ph)}">${ph.toFixed(1)}</span></div>`);
    if (cfg.show_ec_badge !== false && ec != null) badges.push(`<div class="badge" style="border-color:${this._ecColor(ec)}"><span class="badge-label">EC</span><span class="badge-value" style="color:${this._ecColor(ec)}">${ec.toFixed(2)}<small> mS</small></span></div>`);
    if (cfg.show_temp_badge !== false && temp != null) badges.push(`<div class="badge" style="border-color:${this._tempColor(temp)}"><span class="badge-label">Temp</span><span class="badge-value" style="color:${this._tempColor(temp)}">${temp.toFixed(1)}<small> \u00b0C</small></span></div>`);
    const badgesHtml = badges.length ? `<div class="badges">${badges.join("")}</div>` : "";
    let fillHtml = "";
    if (lastFillAt) {
      const ageLabel = daysSince === 0 ? "heute" : daysSince === 1 ? "gestern" : `vor ${daysSince} Tagen`;
      let details = "";
      if (lastFillVolume) details += `<span class="fill-detail">${lastFillVolume} L</span>`;
      if (lastFillPh != null) details += `<span class="fill-detail">pH ${lastFillPh}</span>`;
      if (lastFillEc != null) details += `<span class="fill-detail">EC ${lastFillEc}</span>`;
      if (fertCount) details += `<span class="fill-detail">${fertCount} D\u00fcnger</span>`;
      fillHtml = `<div class="fill-section"><div class="fill-row">
        <svg class="fill-icon" width="16" height="16" viewBox="0 0 24 24" fill="#03a9f4"><path d="M12 2c-5.33 4.55-8 8.48-8 11.8 0 4.98 3.8 8.2 8 8.2s8-3.22 8-8.2C20 10.48 17.33 6.55 12 2z"/></svg>
        <span class="fill-text"><strong>${fillTypeLabels[lastFillType] || "Bef\u00fcllung"}</strong><span class="fill-date">${this._formatDate(lastFillAt)}</span></span>
        <span class="fill-age-badge">${ageLabel}</span>
      </div>${details ? `<div class="fill-details-row">${details}</div>` : ""}</div>`;
    } else { fillHtml = `<div class="fill-section"><div class="no-data">Noch keine Bef\u00fcllung erfasst</div></div>`; }
    this.shadowRoot.innerHTML = `<style>
      :host { display: block; overflow: hidden; box-sizing: border-box; } ha-card { padding: 0; overflow: hidden; }
      .card-header { padding: 12px 16px 0; display: flex; align-items: center; justify-content: space-between; }
      .title { font-size: 1.1em; font-weight: 500; }
      .volume-badge { font-size: 0.8em; padding: 2px 10px; border-radius: 10px; background: #03a9f4; color: #fff; font-weight: 600; }
      .card-content { padding: 8px 16px 16px; }
      .tank-container { display: flex; justify-content: center; padding: 4px 0 8px; }
      .badges { display: flex; gap: 8px; justify-content: center; margin-bottom: 12px; }
      .badge { flex: 1; max-width: 110px; text-align: center; padding: 8px 6px; border-radius: 8px; background: #f5f5f5; border: 2px solid #e0e0e0; }
      .badge-label { display: block; font-size: 0.7em; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #757575; margin-bottom: 2px; }
      .badge-value { font-size: 1.2em; font-weight: 700; }
      .badge-value small { font-size: 0.65em; font-weight: 500; color: #757575; }
      .fill-section { padding-top: 10px; border-top: 1px solid #e0e0e0; }
      .fill-row { display: flex; align-items: center; gap: 8px; }
      .fill-icon { flex-shrink: 0; }
      .fill-text { display: flex; flex-direction: column; flex: 1; min-width: 0; }
      .fill-text strong { font-size: 0.85em; font-weight: 600; }
      .fill-date { font-size: 0.78em; color: #757575; }
      .fill-age-badge { font-size: 0.75em; padding: 2px 8px; border-radius: 10px; background: #f5f5f5; color: #757575; white-space: nowrap; flex-shrink: 0; }
      .fill-details-row { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; padding-left: 24px; }
      .fill-detail { font-size: 0.75em; padding: 2px 8px; border-radius: 4px; background: #f5f5f5; }
      .no-data { font-size: 0.85em; color: #757575; font-style: italic; text-align: center; padding: 8px 0; }
    </style>
    <ha-card>
      <div class="card-header"><span class="title">${title}</span>${volume ? `<span class="volume-badge">${volume} L</span>` : ""}</div>
      <div class="card-content"><div class="tank-container">${tankSvg}</div>${badgesHtml}${fillHtml}</div>
    </ha-card>`;
  }
}
customElements.define("kamerplanter-tank-card", KamerplanterTankCard);
window.customCards = window.customCards || [];
window.customCards.push({ type: "kamerplanter-tank-card", name: "Kamerplanter Tank", description: "Tank-Visualisierung mit SVG, pH/EC/Temp direkt aus HA-Sensoren", preview: true });
