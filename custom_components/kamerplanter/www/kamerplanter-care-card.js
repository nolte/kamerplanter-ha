/**
 * Kamerplanter Care Card — Custom Lovelace Card (REQ-030)
 *
 * Displays overdue, today, and upcoming care tasks grouped by urgency.
 * Each row shows plant name + task type. With `interactive: true` every row
 * also renders state-dependent action buttons (▶ start / ✓ complete / ⏭ skip)
 * wired to the kamerplanter.start_task / complete_task / skip_task services.
 * With `interactive: false` (default) the card is read-only (no buttons).
 *
 * Data sources:
 *   - sensor.kamerplanter_tasks_due_today (today + upcoming)
 *   - sensor.kamerplanter_tasks_overdue (overdue tasks)
 *
 * Configuration (in Lovelace YAML):
 *   type: custom:kamerplanter-care-card
 *   title: Pflege-Dashboard         # optional
 *   upcoming_days: 3                # optional, default 3
 *   interactive: true               # optional, default false (read-only)
 */

const CARD_VERSION = "1.1.0";

/**
 * ha-form ready singleton (UI-NFR-015 §2.2).
 */
const _haFormReadyCare = (async () => {
  if (customElements.get("ha-form")) return;
  await customElements.whenDefined("hui-entities-card");
  const helpers = await window.loadCardHelpers?.();
  if (helpers) {
    const temp = await helpers.createCardElement({ type: "entities", entities: [] });
    if (temp?.constructor?.getConfigElement) await temp.constructor.getConfigElement();
  }
  await customElements.whenDefined("ha-form");
})();

/** Care card editor schema (built per-render so the entity picker can be
 *  filtered against the live hass states). */
function careCardSchema(hass) {
  // The card needs the two hub task-aggregate sensors (kamerplanter_tasks_due_today /
  // kamerplanter_tasks_overdue) -- they are the only sensors exposing a `plants` list
  // attribute, which the card renders as the grouped task list. Per-plant IPM
  // sensors (pest pressure, Karenz, days-since-inspection) carry a single
  // value and would leave the card empty, so we steer the entity picker to the
  // aggregate sensors and spell out the default in a helper text.
  const taskSensors = hass
    ? Object.keys(hass.states).filter(
        (eid) =>
          eid.startsWith("sensor.") &&
          Array.isArray(hass.states[eid]?.attributes?.plants),
      )
    : [];
  // Restrict the picker to the aggregate sensors when we can find them;
  // otherwise fall back to all sensors so the field is never empty/unusable.
  const sensorSelector = taskSensors.length
    ? { entity: { include_entities: taskSensors } }
    : { entity: { domain: ["sensor"] } };
  return [
    { name: "title",         label: "Titel",         selector: { text: {} } },
    { name: "upcoming_days", label: "Vorschau Tage", selector: { number: { min: 1, max: 14, step: 1 } } },
    {
      name: "interactive",
      label: "Interaktiv (Aktions-Buttons)",
      helper:
        "Aktiviert pro Aufgabe Start-/Erledigt-/Überspringen-Buttons. Aus (Standard): schreibgeschützte Ansicht ohne Buttons.",
      selector: { boolean: {} },
    },
    {
      name: "entity_due",
      label: "F\u00e4llig-Heute Sensor (optional)",
      helper:
        "Standard: sensor.kamerplanter_tasks_due_today \u2013 Hub-Sensor mit heute & demn\u00e4chst f\u00e4lligen Aufgaben. Leer lassen f\u00fcr den Standard; keine Einzelpflanzen-Sensoren w\u00e4hlen.",
      selector: sensorSelector,
    },
    {
      name: "entity_overdue",
      label: "\u00dcberf\u00e4llig Sensor (optional)",
      helper:
        "Standard: sensor.kamerplanter_tasks_overdue \u2013 Hub-Sensor mit \u00fcberf\u00e4lligen Aufgaben. Leer lassen f\u00fcr den Standard; keine Einzelpflanzen-Sensoren w\u00e4hlen.",
      selector: sensorSelector,
    },
  ];
}

/**
 * Kamerplanter Care Card Editor
 * Uses ha-form + schema — identical pattern to official HA card editors
 * (UI-NFR-015 §2.1). No Shadow DOM (UI-NFR-015 R-022).
 */
class KamerplanterCareCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = {
      title: "Kamerplanter Pflege",
      upcoming_days: 3,
      interactive: false,
      entity_due: "sensor.kamerplanter_tasks_due_today",
      entity_overdue: "sensor.kamerplanter_tasks_overdue",
      ...config,
    };
    if (this._hass) this._scheduleRender();
  }

  set hass(hass) {
    this._hass = hass;
    this._scheduleRender();
  }

  async _scheduleRender() {
    await _haFormReadyCare;
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
    this._form.schema = careCardSchema(this._hass);
    this._form.data = this._config;
    this._form.computeLabel = (schema) => schema.label || schema.name;
    this._form.computeHelper = (schema) => schema.helper || "";
  }
}
customElements.define("kamerplanter-care-card-editor", KamerplanterCareCardEditor);

class KamerplanterCareCard extends HTMLElement {
  static get properties() {
    return {
      hass: {},
      config: {},
    };
  }

  set hass(hass) {
    const oldDue = this._hass?.states[this._config?.entity_due];
    const newDue = hass.states[this._config?.entity_due];
    const oldOverdue = this._hass?.states[this._config?.entity_overdue];
    const newOverdue = hass.states[this._config?.entity_overdue];
    this._hass = hass;

    if (oldDue !== newDue || oldOverdue !== newOverdue || !this._rendered) {
      this._render();
      this._rendered = true;
    }
  }

  setConfig(config) {
    this._config = {
      title: config.title || "Kamerplanter Pflege",
      upcoming_days: config.upcoming_days || 3,
      // Read-only by default so existing dashboards keep the glanceable view.
      // interactive: true opts into per-task start/complete/skip buttons.
      interactive: config.interactive === true,
      entity_due: config.entity_due || "sensor.kamerplanter_tasks_due_today",
      entity_overdue: config.entity_overdue || "sensor.kamerplanter_tasks_overdue",
    };
    this._rendered = false;
    // State-basierter Doppelklick-/Race-Schutz: haelt die task_keys, deren
    // start/complete/skip-Service gerade laeuft. Ueberlebt ein Re-Render (der
    // DOM-`disabled`-Flags verwirft), weil _buildActionButtons ihn abfragt.
    this._pendingActions = this._pendingActions || new Set();
  }

  getCardSize() {
    return 3;
  }

  getGridOptions() {
    // HA sections use a 12-column grid. Keep the task list readable: full
    // width by default, never narrower than half a section.
    return {
      columns: 12,
      rows: 2,
      min_columns: 6,
      min_rows: 1,
      max_rows: 4,
    };
  }

  static getConfigElement() {
    return document.createElement("kamerplanter-care-card-editor");
  }

  static getStubConfig() {
    // Note: do NOT emit __preview here. HA persists getStubConfig as the
    // card's starting config, so a __preview flag would stick and pin the card
    // to the static mock on a real dashboard. The card-picker gallery is
    // detected at render time via the HA-set `preview` element property.
    return {
      title: "Kamerplanter Pflege",
      upcoming_days: 3,
      interactive: false,
    };
  }

  connectedCallback() {
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }
    this._render();
  }

  _getTaskIcon(category) {
    const icons = {
      watering: "mdi:watering-can",
      giessen: "mdi:watering-can",
      fertilizing: "mdi:bottle-tonic",
      duengen: "mdi:bottle-tonic",
      repotting: "mdi:flower-pollen",
      umtopfen: "mdi:flower-pollen",
      pest_check: "mdi:bug",
      schaedlingskontrolle: "mdi:bug",
      pruning: "mdi:content-cut",
      schneiden: "mdi:content-cut",
    };
    const key = (category || "").toLowerCase();
    return icons[key] || "mdi:clipboard-check-outline";
  }

  _buildTaskRows(tasks, colorClass) {
    if (!tasks || tasks.length === 0) return "";
    return tasks
      .map(
        (task) => `
      <div class="task-row ${colorClass}">
        <ha-icon icon="${this._getTaskIcon(task.category)}" class="task-icon"></ha-icon>
        <div class="task-info">
          <span class="plant-name">${this._escapeHtml(task.name || "Unknown")}</span>
          <span class="task-type">${this._escapeHtml(task.category || "Pflege")}</span>
        </div>
        ${this._config.interactive ? this._buildActionButtons(task) : ""}
      </div>
    `
      )
      .join("");
  }

  /**
   * Derive whether a task has already been started. The backend flags a
   * started task via ``started_at`` (a timestamp) or an in-progress status,
   * so the ▶ start button is hidden once either is present.
   */
  _isTaskStarted(task) {
    if (task.started_at) return true;
    const status = String(task.status || "").toLowerCase();
    return status === "in_progress" || status === "started" || status === "active";
  }

  /**
   * State-dependent action buttons for a task row (interactive mode only):
   *   ▶ start   — only while the task has not been started yet
   *   ✓ complete — for not-started and started tasks
   *   ⏭ skip     — for not-started and started tasks (two-tap confirm)
   */
  _buildActionButtons(task) {
    const taskKey = this._escapeAttr(task.task_key || "");
    if (!taskKey) return "";
    // Laeuft fuer diese Aufgabe bereits ein Service-Call, werden die Buttons
    // auch nach einem Re-Render deaktiviert gerendert (State-basierter Schutz).
    const pending = this._pendingActions && this._pendingActions.has(task.task_key);
    const disabledAttr = pending ? "disabled" : "";
    const started = this._isTaskStarted(task);
    const startBtn = started
      ? ""
      : `<button class="action-btn start-btn" data-action="start" data-task-key="${taskKey}" title="Starten" ${disabledAttr}>
           <ha-icon icon="mdi:play" class="btn-icon"></ha-icon>
         </button>`;
    return `
      <div class="task-actions">
        ${startBtn}
        <button class="action-btn complete-btn" data-action="complete" data-task-key="${taskKey}" title="Erledigt" ${disabledAttr}>
          <ha-icon icon="mdi:check" class="btn-icon"></ha-icon>
        </button>
        <button class="action-btn skip-btn" data-action="skip" data-task-key="${taskKey}" title="Überspringen" ${disabledAttr}>
          <ha-icon icon="mdi:skip-next" class="btn-icon"></ha-icon>
        </button>
      </div>
    `;
  }

  _escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  _escapeAttr(str) {
    return String(str).replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  /**
   * Ein Sensor gilt als gestoert, wenn sein State-Objekt fehlt oder HA ihn als
   * `unavailable`/`unknown` meldet. Solche Zustaende duerfen NICHT als
   * "Alles erledigt!" interpretiert werden (False-Positive-Erfolg).
   */
  _isUnavailable(stateObj) {
    return (
      !stateObj ||
      stateObj.state === "unavailable" ||
      stateObj.state === "unknown"
    );
  }

  _renderPreview() {
    if (!this.shadowRoot) return;
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        ha-card { padding: 16px; }
        .header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
        .header-title { font-size: 1.1rem; font-weight: 500; color: var(--primary-text-color); }
        .badge { display: inline-flex; align-items: center; justify-content: center; min-width: 24px; height: 24px; border-radius: 12px; padding: 0 6px; font-size: 0.8rem; font-weight: 600; color: #fff; }
        .badge-overdue { background-color: var(--error-color, #f44336); }
        .badge-due { background-color: var(--warning-color, #ff9800); }
        .section-label { font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; margin: 12px 0 6px 0; }
        .section-overdue .section-label { color: var(--error-color, #f44336); }
        .section-today .section-label { color: var(--warning-color, #ff9800); }
        .task-row { display: flex; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--divider-color, rgba(0,0,0,0.12)); gap: 12px; }
        .task-row:last-child { border-bottom: none; }
        .task-icon { --mdc-icon-size: 20px; color: var(--secondary-text-color); flex-shrink: 0; }
        .overdue .task-icon { color: var(--error-color, #f44336); }
        .today .task-icon { color: var(--warning-color, #ff9800); }
        .task-info { flex: 1; display: flex; flex-direction: column; min-width: 0; }
        .plant-name { font-size: 0.9rem; font-weight: 500; color: var(--primary-text-color); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .task-type { font-size: 0.75rem; color: var(--secondary-text-color); text-transform: capitalize; }
        .task-actions { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }
        .action-btn { display: inline-flex; align-items: center; justify-content: center; width: 34px; height: 34px; min-width: 34px; border-radius: 50%; border: none; cursor: pointer; color: #fff; }
        .start-btn { background-color: var(--primary-color, #03a9f4); }
        .complete-btn { background-color: var(--success-color, #4caf50); }
        .skip-btn { background-color: var(--secondary-background-color, #e0e0e0); }
        .skip-btn .btn-icon { color: var(--secondary-text-color); }
        .btn-icon { --mdc-icon-size: 18px; color: #fff; }
      </style>
      <ha-card>
        <div class="header">
          <span class="header-title">Pflege-Dashboard</span>
          <span class="badge badge-overdue">3</span>
        </div>
        <div class="section-overdue">
          <div class="section-label">Ueberfaellig (1)</div>
          <div class="task-row overdue">
            <ha-icon icon="mdi:watering-can" class="task-icon"></ha-icon>
            <div class="task-info">
              <span class="plant-name">Monstera deliciosa</span>
              <span class="task-type">Giessen</span>
            </div>
            <div class="task-actions">
              <button class="action-btn start-btn"><ha-icon icon="mdi:play" class="btn-icon"></ha-icon></button>
              <button class="action-btn complete-btn"><ha-icon icon="mdi:check" class="btn-icon"></ha-icon></button>
              <button class="action-btn skip-btn"><ha-icon icon="mdi:skip-next" class="btn-icon"></ha-icon></button>
            </div>
          </div>
        </div>
        <div class="section-today">
          <div class="section-label">Heute faellig (2)</div>
          <div class="task-row today">
            <ha-icon icon="mdi:bottle-tonic" class="task-icon"></ha-icon>
            <div class="task-info">
              <span class="plant-name">Basil 'Genovese'</span>
              <span class="task-type">Duengen</span>
            </div>
            <div class="task-actions">
              <button class="action-btn complete-btn"><ha-icon icon="mdi:check" class="btn-icon"></ha-icon></button>
              <button class="action-btn skip-btn"><ha-icon icon="mdi:skip-next" class="btn-icon"></ha-icon></button>
            </div>
          </div>
          <div class="task-row today">
            <ha-icon icon="mdi:bug" class="task-icon"></ha-icon>
            <div class="task-info">
              <span class="plant-name">Tomate 'San Marzano'</span>
              <span class="task-type">Schaedlingskontrolle</span>
            </div>
            <div class="task-actions">
              <button class="action-btn complete-btn"><ha-icon icon="mdi:check" class="btn-icon"></ha-icon></button>
              <button class="action-btn skip-btn"><ha-icon icon="mdi:skip-next" class="btn-icon"></ha-icon></button>
            </div>
          </div>
        </div>
      </ha-card>
    `;
  }

  _render() {
    if (!this.shadowRoot) return;
    // `this.preview` is set by HA only when the card is shown in the card-picker
    // gallery. A persisted __preview flag is intentionally ignored so cards that
    // captured the old getStubConfig still recover to live data on reload.
    if (this.preview) {
      this._renderPreview();
      return;
    }
    if (!this._hass || !this._config) return;

    const overdueState = this._hass.states[this._config.entity_overdue];
    const dueTodayState = this._hass.states[this._config.entity_due];

    // Stoerung (fehlender/unavailable/unknown Sensor) explizit von "wirklich
    // leer" unterscheiden: liefert mindestens ein Aggregat-Sensor keine
    // belastbaren Daten, darf der Erfolgs-Empty-State nicht erscheinen.
    const dataUnavailable =
      this._isUnavailable(overdueState) || this._isUnavailable(dueTodayState);

    const overdueTasks =
      overdueState && overdueState.attributes
        ? overdueState.attributes.plants || []
        : [];
    const dueTodayTasks =
      dueTodayState && dueTodayState.attributes
        ? dueTodayState.attributes.plants || []
        : [];
    const allUpcoming =
      dueTodayState && dueTodayState.attributes
        ? dueTodayState.attributes.upcoming || []
        : [];

    // Limit the "upcoming" list to the configured preview window (by due date).
    const upcomingLimitDate = new Date();
    upcomingLimitDate.setDate(
      upcomingLimitDate.getDate() + (this._config.upcoming_days || 3),
    );
    const upcomingCutoff = upcomingLimitDate.toISOString().slice(0, 10);
    const upcomingTasks = allUpcoming.filter(
      (t) => !t.due_date || t.due_date <= upcomingCutoff,
    );

    const totalCount =
      overdueTasks.length + dueTodayTasks.length + upcomingTasks.length;
    const overdueCount = overdueTasks.length;
    const dueCount = dueTodayTasks.length;

    const hasData = totalCount > 0;

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
        }
        ha-card {
          padding: 16px;
        }
        .header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 12px;
        }
        .header-title {
          font-size: 1.1rem;
          font-weight: 500;
          color: var(--primary-text-color);
        }
        .badge {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          min-width: 24px;
          height: 24px;
          border-radius: 12px;
          padding: 0 6px;
          font-size: 0.8rem;
          font-weight: 600;
          color: #fff;
        }
        .badge-overdue {
          background-color: var(--error-color, #f44336);
        }
        .badge-due {
          background-color: var(--warning-color, #ff9800);
        }
        .badge-ok {
          background-color: var(--success-color, #4caf50);
        }
        .badge-warn {
          background-color: var(--warning-color, #ff9800);
        }
        .section-label {
          font-size: 0.75rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.08em;
          margin: 12px 0 6px 0;
          padding: 0;
        }
        .section-overdue .section-label {
          color: var(--error-color, #f44336);
        }
        .section-today .section-label {
          color: var(--warning-color, #ff9800);
        }
        .section-upcoming .section-label {
          color: var(--info-color, var(--primary-color, #03a9f4));
        }
        .task-row {
          display: flex;
          align-items: center;
          padding: 8px 0;
          border-bottom: 1px solid var(--divider-color, rgba(0,0,0,0.12));
          gap: 12px;
        }
        .task-row:last-child {
          border-bottom: none;
        }
        .task-icon {
          --mdc-icon-size: 20px;
          color: var(--secondary-text-color);
          flex-shrink: 0;
        }
        .overdue .task-icon {
          color: var(--error-color, #f44336);
        }
        .today .task-icon {
          color: var(--warning-color, #ff9800);
        }
        .task-info {
          flex: 1;
          display: flex;
          flex-direction: column;
          min-width: 0;
        }
        .plant-name {
          font-size: 0.9rem;
          font-weight: 500;
          color: var(--primary-text-color);
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .task-type {
          font-size: 0.75rem;
          color: var(--secondary-text-color);
          text-transform: capitalize;
        }
        .task-actions {
          display: flex;
          align-items: center;
          gap: 6px;
          flex-shrink: 0;
        }
        .action-btn {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 34px;
          height: 34px;
          min-width: 34px;
          border-radius: 50%;
          border: none;
          cursor: pointer;
          transition: background-color 0.2s, opacity 0.2s;
          color: #fff;
        }
        .action-btn:hover {
          opacity: 0.85;
        }
        .action-btn:active {
          opacity: 0.7;
        }
        .action-btn:disabled {
          opacity: 0.4;
          cursor: not-allowed;
        }
        .start-btn {
          background-color: var(--primary-color, #03a9f4);
        }
        .complete-btn {
          background-color: var(--success-color, #4caf50);
        }
        .skip-btn {
          /* Theme-taugliche Flaeche: --secondary-background-color kontrastiert
             in Light- UND Dark-Mode zuverlaessig mit --secondary-text-color
             (Icon-Farbe unten), anders als die frueher genutzte Textfarbe mit
             weissem Icon. */
          background-color: var(--secondary-background-color, #e0e0e0);
        }
        .skip-btn .btn-icon {
          color: var(--secondary-text-color);
        }
        .skip-btn.confirm {
          background-color: var(--warning-color, #ff9800);
        }
        .skip-btn.confirm .btn-icon {
          color: #fff;
        }
        .btn-icon {
          --mdc-icon-size: 18px;
          color: #fff;
        }
        .empty-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 24px 16px;
          color: var(--secondary-text-color);
          text-align: center;
        }
        .empty-state ha-icon {
          --mdc-icon-size: 48px;
          color: var(--success-color, #4caf50);
          margin-bottom: 12px;
        }
        .empty-state .title {
          font-size: 1rem;
          font-weight: 500;
          margin-bottom: 4px;
        }
        .empty-state .subtitle {
          font-size: 0.85rem;
        }
        .warning-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 24px 16px;
          color: var(--secondary-text-color);
          text-align: center;
        }
        .warning-state ha-icon {
          --mdc-icon-size: 48px;
          color: var(--warning-color, #ff9800);
          margin-bottom: 12px;
        }
        .warning-state .title {
          font-size: 1rem;
          font-weight: 500;
          margin-bottom: 4px;
          color: var(--primary-text-color);
        }
        .warning-state .subtitle {
          font-size: 0.85rem;
        }
      </style>
      <ha-card>
        <div class="header">
          <span class="header-title">${this._escapeHtml(this._config.title)}</span>
          ${
            dataUnavailable && !hasData
              ? `<span class="badge badge-warn">!</span>`
              : overdueCount > 0
                ? `<span class="badge badge-overdue">${overdueCount}</span>`
                : dueCount > 0
                  ? `<span class="badge badge-due">${dueCount}</span>`
                  : `<span class="badge badge-ok">0</span>`
          }
        </div>
        ${
          !hasData
            ? dataUnavailable
              ? `
          <div class="warning-state">
            <ha-icon icon="mdi:alert-circle-outline"></ha-icon>
            <div class="title">Pflegedaten nicht verfügbar</div>
            <div class="subtitle">Die Aufgaben-Sensoren sind derzeit nicht erreichbar.</div>
          </div>
        `
              : `
          <div class="empty-state">
            <ha-icon icon="mdi:check-circle-outline"></ha-icon>
            <div class="title">Alles erledigt!</div>
            <div class="subtitle">Keine Pflegeaufgaben ausstehend.</div>
          </div>
        `
            : `
          ${
            overdueTasks.length > 0
              ? `
            <div class="section-overdue">
              <div class="section-label">Ueberfaellig (${overdueTasks.length})</div>
              ${this._buildTaskRows(overdueTasks, "overdue")}
            </div>
          `
              : ""
          }
          ${
            dueTodayTasks.length > 0
              ? `
            <div class="section-today">
              <div class="section-label">Heute faellig (${dueTodayTasks.length})</div>
              ${this._buildTaskRows(dueTodayTasks, "today")}
            </div>
          `
              : ""
          }
          ${
            upcomingTasks.length > 0
              ? `
            <div class="section-upcoming">
              <div class="section-label">Anstehend (${upcomingTasks.length})</div>
              ${this._buildTaskRows(upcomingTasks, "upcoming")}
            </div>
          `
              : ""
          }
        `
        }
      </ha-card>
    `;

    // Interactive mode: wire the per-task start/complete/skip buttons.
    // Read-only mode renders no action buttons, so there is nothing to bind.
    if (this._config.interactive) {
      this.shadowRoot.querySelectorAll(".action-btn").forEach((btn) => {
        btn.addEventListener("click", (e) => this._handleActionClick(e));
      });
    }
  }

  _handleActionClick(event) {
    const btn = event.currentTarget;
    const action = btn.dataset.action;
    const taskKey = btn.dataset.taskKey;
    if (!action || !taskKey || !this._hass) return;

    // State-basierter Race-Schutz: laeuft fuer diese Aufgabe bereits ein
    // Service-Call, wird jeder weitere Tap (auch das Skip-Armen) ignoriert.
    if (this._pendingActions && this._pendingActions.has(taskKey)) return;

    // Skip is destructive on a touch dashboard, so require a two-tap confirm:
    // the first tap arms the button (icon + colour change), a second tap within
    // the timeout actually skips. start/complete execute on the first tap.
    if (action === "skip" && btn.dataset.confirm !== "1") {
      this._armSkipConfirm(btn);
      return;
    }

    this._executeAction(btn, action, taskKey);
  }

  _armSkipConfirm(btn) {
    btn.dataset.confirm = "1";
    btn.classList.add("confirm");
    btn.title = "Zum Bestätigen erneut tippen";
    btn.innerHTML = '<ha-icon icon="mdi:skip-next-circle" class="btn-icon"></ha-icon>';
    this._skipTimers = this._skipTimers || new WeakMap();
    clearTimeout(this._skipTimers.get(btn));
    this._skipTimers.set(
      btn,
      setTimeout(() => this._resetSkipConfirm(btn), 3000),
    );
  }

  _resetSkipConfirm(btn) {
    if (!btn.isConnected) return;
    btn.dataset.confirm = "";
    btn.classList.remove("confirm");
    btn.title = "Überspringen";
    btn.innerHTML = '<ha-icon icon="mdi:skip-next" class="btn-icon"></ha-icon>';
  }

  _executeAction(btn, action, taskKey) {
    this._pendingActions = this._pendingActions || new Set();
    // State-basierter Doppelklick-Schutz: eine bereits laufende Aufgabe wird
    // nicht erneut ausgeloest (ueberlebt auch ein zwischenzeitliches Re-Render).
    if (this._pendingActions.has(taskKey)) return;
    this._pendingActions.add(taskKey);

    // Ein evtl. armiertes Skip-Confirm zuruecksetzen, damit die Zeile einen
    // sauberen Spinner zeigt und kein Timer spaeter das Icon ueberschreibt.
    if (this._skipTimers) clearTimeout(this._skipTimers.get(btn));
    btn.classList.remove("confirm");
    btn.dataset.confirm = "";

    // Optimistic UI: disable every button in the row so the task cannot be
    // double-actioned while the coordinator refresh is in flight. The card
    // re-renders from live sensor data once the status changes.
    const row = btn.closest(".task-row");
    if (row) {
      row.querySelectorAll(".action-btn").forEach((b) => {
        b.disabled = true;
      });
    }
    btn.innerHTML = '<ha-icon icon="mdi:check-all" class="btn-icon"></ha-icon>';

    const service = `${action}_task`;
    // Den Promise auswerten: bei Erfolg raeumt der Live-State-Refresh die Zeile
    // auf; bei Fehler werden Buttons re-aktiviert, das Original-Icon wieder-
    // hergestellt und der Nutzer per Notification informiert (kein stiller Erfolg).
    this._hass
      .callService("kamerplanter", service, { task_key: taskKey })
      .then(() => {
        this._pendingActions.delete(taskKey);
      })
      .catch((err) => {
        this._pendingActions.delete(taskKey);
        this._handleActionError(btn, action, row, err);
      });
  }

  /** Standard-Icon (ungestoerter Zustand) je Aktionstyp. */
  _actionIcon(action) {
    const map = { start: "mdi:play", complete: "mdi:check", skip: "mdi:skip-next" };
    return map[action] || "mdi:check";
  }

  /** Menschenlesbarer Aktionsname fuer Titel und Fehlermeldung. */
  _actionTitle(action) {
    const map = { start: "Starten", complete: "Erledigt", skip: "Überspringen" };
    return map[action] || action;
  }

  /**
   * Schlaegt ein Service-Call fehl: die ganze Zeile wieder aktivieren, das
   * geklickte Button-Icon auf seinen Ausgangszustand zuruecksetzen und den
   * Fehler ueber ein `hass-notification`-Event sichtbar machen.
   */
  _handleActionError(btn, action, row, err) {
    if (row) {
      row.querySelectorAll(".action-btn").forEach((b) => {
        b.disabled = false;
      });
    }
    if (btn && btn.isConnected) {
      btn.disabled = false;
      btn.classList.remove("confirm");
      btn.dataset.confirm = "";
      btn.title = this._actionTitle(action);
      btn.innerHTML = `<ha-icon icon="${this._actionIcon(action)}" class="btn-icon"></ha-icon>`;
    }
    const message = err && err.message ? err.message : String(err || "Unbekannter Fehler");
    this._showError(`Aktion "${this._actionTitle(action)}" fehlgeschlagen: ${message}`);
  }

  /** Fehler-Feedback an den Nutzer via HA-Notification-Toast. */
  _showError(message) {
    const event = new Event("hass-notification", { bubbles: true, composed: true });
    event.detail = { message };
    this.dispatchEvent(event);
  }
}

customElements.define("kamerplanter-care-card", KamerplanterCareCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "kamerplanter-care-card",
  name: "Kamerplanter Care Card",
  description:
    "Displays overdue, today and upcoming plant care tasks grouped by urgency. " +
    "Optional interactive mode adds per-task start/complete/skip buttons.",
  preview: true,
});

console.info(
  `%c KAMERPLANTER-CARE-CARD %c v${CARD_VERSION} `,
  "color: white; background: #4CAF50; font-weight: bold;",
  "color: #4CAF50; background: white; font-weight: bold;"
);
