# Lovelace Card Patterns -- Analyse des offiziellen HA-Frontend

> **Quelle:** [home-assistant/frontend](https://github.com/home-assistant/frontend) (`dev`-Branch)
> **Datum:** 2026-04-03
> **Zweck:** Referenzdokumentation fuer die Entwicklung eigener Custom Lovelace Cards in `custom_components/kamerplanter/www/`

---

## 1. Card-Architektur

### 1.1 LovelaceCard-Interface

Jede Lovelace Card muss das `LovelaceCard`-Interface implementieren:

```typescript
// src/panels/lovelace/types.ts
export interface LovelaceCard extends HTMLElement {
  hass?: HomeAssistant;
  preview?: boolean;
  layout?: string;
  connectedWhileHidden?: boolean;
  getCardSize(): number | Promise<number>;
  /** @deprecated Use getGridOptions instead */
  getLayoutOptions?(): LovelaceLayoutOptions;
  getGridOptions?(): LovelaceGridOptions;
  setConfig(config: LovelaceCardConfig): void;
}
```

Grid-Options fuer das Sections-Layout:

```typescript
export interface LovelaceGridOptions {
  columns?: number | "full";
  rows?: number | "auto";
  max_columns?: number;
  min_columns?: number;
  min_rows?: number;
  max_rows?: number;
}
```

### 1.2 Basis-Config-Interface

```typescript
// src/data/lovelace/config/card.ts
export interface LovelaceCardConfig {
  index?: number;
  view_index?: number;
  view_layout?: any;
  grid_options?: LovelaceGridOptions;
  type: string;               // Pflichtfeld -- identifiziert den Card-Typ
  [key: string]: any;         // Beliebige zusaetzliche Properties
  visibility?: Condition[];
  disabled?: boolean;
}
```

### 1.3 Card-Lifecycle

Die Lifecycle-Methoden in Aufruf-Reihenfolge:

| Methode | Wann | Zweck |
|---------|------|-------|
| `constructor()` | Element-Erzeugung | Minimale Initialisierung |
| `setConfig(config)` | Konfiguration wird gesetzt/geaendert | Validierung, Config-Parsing. **Exception = Error Card** |
| `set hass(hass)` | Bei jedem State-Update (Setter, kein Lifecycle) | hass-Objekt an Kinder weitergeben |
| `connectedCallback()` | Element ins DOM eingefuegt | Event-Listener, Subscriptions |
| `shouldUpdate(changedProps)` | Vor jedem Render | Performance-Optimierung |
| `render()` | Lit-Render-Zyklus | HTML-Template zurueckgeben |
| `updated(changedProps)` | Nach Render | Theme-Anwendung, Side-Effects |
| `getCardSize()` | Masonry-Layout | Hoehe in 50px-Einheiten |
| `getGridOptions()` | Sections-Layout | Spalten/Zeilen-Angaben |
| `disconnectedCallback()` | Element aus DOM entfernt | Cleanup, Unsubscribe |

### 1.4 Vollstaendiges Card-Beispiel (offizielle Struktur)

Hier die `hui-plant-status-card` als Referenz -- die fuer Kamerplanter relevanteste Card:

```typescript
import { mdiSprout, mdiThermometer, mdiWaterPercent, mdiWhiteBalanceSunny } from "@mdi/js";
import type { HassEntity } from "home-assistant-js-websocket";
import type { PropertyValues } from "lit";
import { css, html, LitElement, nothing } from "lit";
import { customElement, property, state } from "lit/decorators";
import { applyThemesOnElement } from "../../../common/dom/apply_themes_on_element";
import { fireEvent } from "../../../common/dom/fire_event";
import { batteryLevelIcon } from "../../../common/entity/battery_icon";
import "../../../components/ha-card";
import "../../../components/ha-svg-icon";
import type { HomeAssistant } from "../../../types";
import { actionHandler } from "../common/directives/action-handler-directive";
import { findEntities } from "../common/find-entities";
import { hasConfigOrEntityChanged } from "../common/has-changed";
import { createEntityNotFoundWarning } from "../components/hui-warning";
import type { LovelaceCard, LovelaceCardEditor } from "../types";
import type { PlantAttributeTarget, PlantStatusCardConfig } from "./types";

const SENSOR_ICONS = {
  moisture: mdiWaterPercent,
  temperature: mdiThermometer,
  brightness: mdiWhiteBalanceSunny,
  conductivity: mdiSprout,
  battery: undefined,   // battery nutzt ha-icon statt ha-svg-icon
};

@customElement("hui-plant-status-card")
class HuiPlantStatusCard extends LitElement implements LovelaceCard {

  // --- Static Methods fuer Card-Picker & Editor ---

  public static async getConfigElement(): Promise<LovelaceCardEditor> {
    await import("../editor/config-elements/hui-plant-status-card-editor");
    return document.createElement("hui-plant-status-card-editor");
  }

  public static getStubConfig(
    hass: HomeAssistant,
    entities: string[],
    entitiesFallback: string[]
  ): PlantStatusCardConfig {
    const includeDomains = ["plant"];
    const maxEntities = 1;
    const foundEntities = findEntities(
      hass, maxEntities, entities, entitiesFallback, includeDomains
    );
    return { type: "plant-status", entity: foundEntities[0] || "" };
  }

  // --- Properties ---

  @property({ attribute: false }) public hass?: HomeAssistant;
  @state() private _config?: PlantStatusCardConfig;

  // --- Lifecycle ---

  public getCardSize(): number {
    return 3;
  }

  public setConfig(config: PlantStatusCardConfig): void {
    if (!config.entity || config.entity.split(".")[0] !== "plant") {
      throw new Error("Specify an entity from within the plant domain");
    }
    this._config = config;
  }

  protected shouldUpdate(changedProps: PropertyValues): boolean {
    return hasConfigOrEntityChanged(this, changedProps);
  }

  protected updated(changedProps: PropertyValues): void {
    super.updated(changedProps);
    if (!this._config || !this.hass) return;
    const oldHass = changedProps.get("hass") as HomeAssistant | undefined;
    const oldConfig = changedProps.get("_config") as PlantStatusCardConfig | undefined;
    if (!oldHass || !oldConfig ||
        oldHass.themes !== this.hass.themes ||
        oldConfig.theme !== this._config.theme) {
      applyThemesOnElement(this, this.hass.themes, this._config.theme);
    }
  }

  // --- Render ---

  protected render() {
    if (!this.hass || !this._config) return nothing;

    const stateObj = this.hass.states[this._config!.entity];
    if (!stateObj) {
      return html`
        <hui-warning .hass=${this.hass}>
          ${createEntityNotFoundWarning(this.hass, this._config.entity)}
        </hui-warning>
      `;
    }

    return html`
      <ha-card class=${stateObj.attributes.entity_picture ? "has-plant-image" : ""}>
        <div class="banner"
             style="background-image:url(${stateObj.attributes.entity_picture})">
          <div class="header">
            ${this.hass.formatEntityName(stateObj, this._config.name)}
          </div>
        </div>
        <div class="content">
          ${this._computeAttributes(stateObj).map((item) => html`
            <div class="attributes"
                 @action=${this._handleMoreInfo}
                 .actionHandler=${actionHandler()}
                 tabindex="0"
                 .value=${item}>
              <div class="icon">
                ${item === "battery"
                  ? html`<ha-icon .icon=${batteryLevelIcon(stateObj.attributes.battery)}></ha-icon>`
                  : html`<ha-svg-icon .path=${SENSOR_ICONS[item]}></ha-svg-icon>`}
              </div>
              <div class=${stateObj.attributes.problem.indexOf(item) === -1 ? "" : "problem"}>
                ${this._formatSensorValue(stateObj, item)}
              </div>
              <div class="uom">
                ${stateObj.attributes.unit_of_measurement_dict[item] || ""}
              </div>
            </div>
          `)}
        </div>
      </ha-card>
    `;
  }

  // --- Private Methods ---

  private _formatSensorValue(stateObj: HassEntity, attribute: string): string {
    const sensorEntityId = stateObj.attributes.sensors?.[attribute];
    const sensorStateObj = sensorEntityId ? this.hass!.states[sensorEntityId] : undefined;
    if (sensorStateObj) {
      return this.hass!.formatEntityStateToParts(sensorStateObj)
        .filter((part) => part.type !== "unit")
        .map((part) => part.value)
        .join("");
    }
    return stateObj.attributes[attribute] ?? "";
  }

  private _computeAttributes(stateObj: HassEntity): string[] {
    return Object.keys(SENSOR_ICONS).filter((key) => key in stateObj.attributes);
  }

  private _handleMoreInfo(ev: Event): void {
    const target = ev.currentTarget! as PlantAttributeTarget;
    const stateObj = this.hass!.states[this._config!.entity];
    if (target.value) {
      fireEvent(this, "hass-more-info", {
        entityId: stateObj.attributes.sensors[target.value],
      });
    }
  }

  // --- Styles ---

  static styles = css`
    ha-card { height: 100%; box-sizing: border-box; }
    .banner {
      display: flex; align-items: flex-end;
      background-repeat: no-repeat; background-size: cover;
      background-position: center; padding-top: 12px;
    }
    .has-plant-image .banner { padding-top: 30%; }
    .header {
      font-size: var(--ha-font-size-2xl);
      font-weight: var(--ha-font-weight-normal);
      padding: 8px 16px;
    }
    .has-plant-image .header {
      font-size: var(--ha-font-size-l);
      font-weight: var(--ha-font-weight-medium);
      padding: 16px; color: white; width: 100%;
      background: rgba(0, 0, 0, var(--dark-secondary-opacity));
    }
    .content {
      display: flex; justify-content: space-between;
      padding: 16px 32px 24px 32px;
    }
    ha-icon, ha-svg-icon { color: var(--state-icon-color); }
    .attributes { cursor: pointer; }
    .attributes:focus {
      outline: none; background: var(--divider-color);
      border-radius: var(--ha-border-radius-pill);
    }
    .attributes div { text-align: center; }
    .problem { color: var(--error-color); font-weight: var(--ha-font-weight-bold); }
    .uom { color: var(--secondary-text-color); }
  `;
}
```

### 1.5 Registrierung als Custom Card

Custom Cards (externe) registrieren sich ueber `window.customCards`:

```javascript
// Am Ende der Card-Datei
window.customCards = window.customCards || [];
window.customCards.push({
  type: "kamerplanter-plant-card",       // Pflicht: Element-Name ohne "custom:" Prefix
  name: "Kamerplanter Plant Card",       // Pflicht: Anzeigename im Card-Picker
  description: "Plant monitoring card",  // Optional
  preview: false,                        // Optional (default: false)
  documentationURL: "https://...",       // Optional: Link im Editor
});

customElements.define("kamerplanter-plant-card", KamerplanterPlantCard);
```

In der Lovelace-Config wird die Card dann referenziert als:
```yaml
type: custom:kamerplanter-plant-card
entity: sensor.tomato_moisture
```

**Wichtig:** Die JS-Datei muss als Resource in der Dashboard-Config registriert sein:
```yaml
resources:
  - url: /local/kamerplanter-plant-card.js
    type: module
```

### 1.6 Offizielle Card-Registrierung (intern)

Interne Cards nutzen `@customElement("hui-<name>-card")` und werden in `create-card-element.ts` registriert:

- **Always-loaded** (13 Cards): entity, entities, button, glance, grid, section, light, sensor, thermostat, weather-forecast, tile, heading, entity-button
- **Lazy-loaded** (50+ Cards): Dynamischer Import bei Bedarf via `LAZY_LOAD_TYPES` Map

---

## 2. Card-Editor-Patterns

### 2.1 Schema-basierter Editor (empfohlen)

Der moderne Ansatz nutzt `getConfigForm()` statt eines Custom-Editor-Elements:

```typescript
// hui-entity-card-editor.ts (vereinfacht)
const SCHEMA = [
  {
    name: "entity",
    required: true,
    selector: { entity: {} },
  },
  {
    type: "grid",
    name: "",
    schema: [
      { name: "icon", selector: { icon: {} } },
      { name: "attribute", selector: { attribute: {} } },
      { name: "unit", selector: { text: {} } },
      { name: "theme", selector: { theme: {} } },
      {
        name: "state_color",
        selector: { boolean: {} },
      },
    ],
  },
  {
    type: "expandable",
    name: "interactions",
    flatten: true,
    schema: [
      {
        name: "tap_action",
        selector: {
          ui_action: {
            default_action: "more-info",
            actions: ["more-info", "navigate", "url", "perform-action", "assist", "none"],
          },
        },
      },
      { name: "hold_action", selector: { ui_action: { /* ... */ } } },
      { name: "double_tap_action", selector: { ui_action: { /* ... */ } } },
    ],
  },
];

export default {
  schema: SCHEMA,
  assertConfig: (config) => { assert(config, cardConfigStruct); },
  computeLabel: (schema, localize) => {
    // Lokalisierte Labels fuer Formularfelder
    return localize(`ui.panel.lovelace.editor.card.generic.${schema.name}`) || schema.name;
  },
};
```

Die Card referenziert den Editor ueber:

```typescript
public static async getConfigForm() {
  return (await import("../editor/config-elements/hui-entity-card-editor")).default;
}
```

### 2.2 Custom Editor Element (legacy/komplex)

Fuer komplexere Editoren wird ein eigenes LitElement erstellt:

```typescript
@customElement("hui-entities-card-editor")
class HuiEntitiesCardEditor extends LitElement implements LovelaceCardEditor {
  @state() private _config?: EntitiesCardConfig;
  @property({ attribute: false }) public hass?: HomeAssistant;

  public setConfig(config: EntitiesCardConfig): void {
    assert(config, cardConfigStruct);  // superstruct-Validierung
    this._config = config;
  }

  protected render() {
    return html`
      <ha-form
        .hass=${this.hass}
        .data=${this._config}
        .schema=${this._schema(this.hass!.localize)}
        .computeLabel=${this._computeLabelCallback}
        @value-changed=${this._valueChanged}
      ></ha-form>
    `;
  }

  // Config-Aenderung an Parent melden:
  private _valueChanged(ev: CustomEvent): void {
    const config = ev.detail.value;
    fireEvent(this, "config-changed", { config });
  }
}
```

**Kernprinzip:** Der Editor feuert `config-changed` Events mit der neuen Config im Detail.

### 2.3 getStubConfig()

Liefert eine Default-Config wenn die Card im Picker ausgewaehlt wird:

```typescript
public static getStubConfig(
  hass: HomeAssistant,
  entities: string[],         // Entitaeten die noch nicht verwendet werden
  entitiesFallback: string[]  // Alle verfuegbaren Entitaeten
): PlantStatusCardConfig {
  const foundEntities = findEntities(hass, 1, entities, entitiesFallback, ["plant"]);
  return { type: "plant-status", entity: foundEntities[0] || "" };
}
```

---

## 3. UI-Komponenten & Styling

### 3.1 Wiederverwendbare HA-Komponenten

| Komponente | Zweck | Beispiel |
|------------|-------|---------|
| `<ha-card>` | Card-Container mit Schatten, Border, Header | Jede Card |
| `<ha-icon>` | Icon aus `mdi:` Icon-Set (string-basiert) | `<ha-icon .icon=${"mdi:water"}></ha-icon>` |
| `<ha-svg-icon>` | SVG-Path Icon (performanter) | `<ha-svg-icon .path=${mdiWaterPercent}></ha-svg-icon>` |
| `<ha-state-icon>` | Entity-State-abhaengiges Icon | Entity Card Icon |
| `<ha-attribute-value>` | Formatierter Attribut-Wert | Entity Card |
| `<ha-form>` | Schema-getriebenes Formular | Card Editors |
| `<hui-warning>` | Warning-Banner | Entity not found |
| `<state-history-charts>` | History-Graphen | History Graph Card |
| `<statistics-chart>` | Statistik-Visualisierung | Statistics Graph Card |

### 3.2 CSS Custom Properties (Theming)

Die wichtigsten CSS-Variablen fuer Cards:

```css
/* Card-Container */
--ha-card-background: var(--card-background-color, white);
--ha-card-border-radius: var(--ha-border-radius-lg);
--ha-card-border-width: 1px;
--ha-card-border-color: var(--divider-color, #e0e0e0);
--ha-card-box-shadow: none;
--ha-card-backdrop-filter: none;

/* Typografie */
--ha-font-size-l: /* large */;
--ha-font-size-2xl: /* extra large */;
--ha-font-size-3xl: /* display */;
--ha-font-weight-normal: /* normal */;
--ha-font-weight-medium: /* medium */;
--ha-font-weight-bold: /* bold */;
--ha-line-height-normal: /* normal */;
--ha-line-height-condensed: /* condensed */;
--ha-line-height-expanded: /* expanded */;
--ha-font-family-body: /* system font stack */;

/* Spacing */
--ha-space-2: /* 8px */;
--ha-space-3: /* 12px */;
--ha-space-4: /* 16px */;

/* Farben */
--primary-text-color: /* Haupttextfarbe */;
--secondary-text-color: /* Zweitfarbe (UoM, Labels) */;
--state-icon-color: /* Standard-Icon-Farbe */;
--error-color: /* Fehler/Problem-Rot */;
--divider-color: /* Trennlinien */;
--primary-color: /* Akzentfarbe */;
--dark-secondary-opacity: /* Overlay-Opacity */;

/* Card-Header (in ha-card) */
--ha-card-header-color: /* Header-Textfarbe */;
--ha-card-header-font-family: /* Header-Font */;
--ha-card-header-font-size: /* Header-Groesse */;

/* Border Radius */
--ha-border-radius-lg: /* Standard Card Radius */;
--ha-border-radius-pill: /* Pill-Form (Focus-States) */;

/* Row Gap (Entities Card) */
--entities-card-row-gap: var(--card-row-gap, 8px);
```

### 3.3 Card-Layout-Pattern

```css
/* Standard-Card: Flex-Column mit space-between */
ha-card {
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

/* Action-Cursor */
ha-card.action { cursor: pointer; }

/* Text-Overflow */
.name {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
```

### 3.4 Theme-Anwendung

Jede Card wendet Themes in `updated()` an:

```typescript
protected updated(changedProps: PropertyValues): void {
  super.updated(changedProps);
  if (!this._config || !this.hass) return;
  const oldHass = changedProps.get("hass") as HomeAssistant | undefined;
  const oldConfig = changedProps.get("_config") as CardConfig | undefined;
  if (
    !oldHass || !oldConfig ||
    oldHass.themes !== this.hass.themes ||
    oldConfig.theme !== this._config.theme
  ) {
    applyThemesOnElement(this, this.hass.themes, this._config.theme);
  }
}
```

---

## 4. Entity-Display-Patterns

### 4.1 State-Formatierung

```typescript
// Formatierter State mit Einheit (Parts-API)
const stateParts = this.hass.formatEntityStateToParts(stateObj);
const value = stateParts.filter(p => p.type === "value").map(p => p.value).join("");
const unit = stateParts.find(p => p.type === "unit")?.value;

// Entity-Name mit Config-Override
const name = this.hass.formatEntityName(stateObj, this._config.name);

// Attribut-Wert formatieren
const parts = this.hass.formatEntityAttributeValueToParts(stateObj, "temperature");
```

### 4.2 Entity-Not-Found Handling

```typescript
const stateObj = this.hass.states[this._config.entity];
if (!stateObj) {
  return html`
    <hui-warning .hass=${this.hass}>
      ${createEntityNotFoundWarning(this.hass, this._config.entity)}
    </hui-warning>
  `;
}
```

### 4.3 Unavailable/Unknown States

```typescript
import { isUnavailableState } from "../../../data/entity/entity";

if (isUnavailableState(stateObj.state)) {
  // "unavailable" oder "unknown"
  unit = undefined;  // Keine Einheit anzeigen
}
```

### 4.4 State-abhaengige Farben

```typescript
import { stateColorCss, stateColorBrightness } from "../../../common/entity/state_color";

// CSS-Farbe basierend auf Entity-State
const color = stateColorCss(stateObj);

// Brightness-Filter (fuer Lichter)
const brightness = stateColorBrightness(stateObj);

// Im Template:
style=${styleMap({
  color: colored ? this._computeColor(stateObj) : undefined,
  filter: colored ? stateColorBrightness(stateObj) : undefined,
})}
```

### 4.5 Problem-Highlighting (Plant Card)

```typescript
// Plant-Attribute mit Problem-Status
<div class=${stateObj.attributes.problem.indexOf(item) === -1 ? "" : "problem"}>
  ${value}
</div>

// CSS:
.problem {
  color: var(--error-color);
  font-weight: var(--ha-font-weight-bold);
}
```

### 4.6 Icon-Patterns

```typescript
// SVG-Path Icons (performanter, bevorzugt):
import { mdiWaterPercent } from "@mdi/js";
html`<ha-svg-icon .path=${mdiWaterPercent}></ha-svg-icon>`;

// String-basierte Icons (dynamisch):
html`<ha-icon .icon=${"mdi:water"}></ha-icon>`;

// State-abhaengige Icons:
html`<ha-state-icon .icon=${config.icon} .stateObj=${stateObj} .hass=${this.hass}></ha-state-icon>`;

// Battery-Level Icon (dynamisch basierend auf Wert):
import { batteryLevelIcon } from "../../../common/entity/battery_icon";
html`<ha-icon .icon=${batteryLevelIcon(stateObj.attributes.battery)}></ha-icon>`;
```

---

## 5. Action-Handling

### 5.1 ActionConfig-Typen

```typescript
// src/data/lovelace/config/action.ts
type ActionConfig =
  | ToggleActionConfig        // { action: "toggle" }
  | CallServiceActionConfig   // { action: "perform-action", perform_action: "light.turn_on", data: {...} }
  | NavigateActionConfig      // { action: "navigate", navigation_path: "/lovelace/..." }
  | UrlActionConfig           // { action: "url", url_path: "https://..." }
  | MoreInfoActionConfig      // { action: "more-info", entity?: "sensor.x" }
  | AssistActionConfig        // { action: "assist", pipeline_id?: "..." }
  | NoActionConfig            // { action: "none" }
  | CustomActionConfig;       // { action: "fire-dom-event" }
```

Jede Action kann eine Confirmation haben:

```typescript
interface ConfirmationRestrictionConfig {
  text?: string;
  title?: string;
  confirm_text?: string;
  dismiss_text?: string;
  exemptions?: { user: string }[];
}
```

### 5.2 Action-Handler-Directive

Die Directive bindet tap/hold/double-tap Events an ein Element:

```typescript
import { actionHandler } from "../common/directives/action-handler-directive";
import { handleAction } from "../common/handle-action";
import { hasAction, hasAnyAction } from "../common/has-action";
import type { ActionHandlerEvent } from "../../../data/lovelace/action_handler";

// Im Template:
html`
  <ha-card
    @action=${this._handleAction}
    .actionHandler=${actionHandler({
      hasHold: hasAction(this._config.hold_action),
      hasDoubleClick: hasAction(this._config.double_tap_action),
    })}
    tabindex=${hasAnyAction(this._config) ? "0" : undefined}
  >
    ...
  </ha-card>
`;

// Event-Handler:
private _handleAction(ev: ActionHandlerEvent) {
  handleAction(this, this.hass!, this._config!, ev.detail.action!);
}
```

### 5.3 ActionHandlerOptions

```typescript
export interface ActionHandlerOptions {
  hasTap?: boolean;       // default: true (wenn nicht explizit false)
  hasHold?: boolean;      // Hold-Erkennung aktivieren (500ms Timer)
  hasDoubleClick?: boolean; // Double-Tap-Erkennung (250ms Fenster)
  disabled?: boolean;     // Action-Handling komplett deaktivieren
}
```

### 5.4 Action-Handler Implementierung (Zusammenfassung)

Der `ActionHandler` ist ein unsichtbares Custom Element (`<action-handler>`), das:

1. **Tap:** Erkennt Klick/Touch ohne Hold. Feuert `{ action: "tap" }`
2. **Hold:** 500ms Timer mit visueller Animation (skalierender Kreis). Feuert `{ action: "hold" }`
3. **Double-Tap:** 250ms Fenster fuer zweiten Klick. Feuert `{ action: "double_tap" }`
4. **Cancellation:** Scroll, Mouseout, Wheel etc. brechen Hold ab
5. **Keyboard:** Enter und Space loesen `end` aus (Accessibility)

### 5.5 More-Info Event (einfachste Action)

```typescript
import { fireEvent } from "../../../common/dom/fire_event";

// Direkt More-Info Dialog oeffnen:
fireEvent(this, "hass-more-info", {
  entityId: "sensor.plant_moisture",
});
```

---

## 6. Graph/Chart-Funktionalitaet

### 6.1 History Graph Card

Die `hui-history-graph-card` zeigt Zustandshistorie:

```typescript
// Datenfluss:
// 1. subscribeHistoryStatesTimeWindow() -- Echtzeit-Subscription
// 2. computeHistory() -- Rohdaten → Chart-Format
// 3. fetchStatistics() -- Stundenaggregat fuer laengere Zeitraeume
// 4. mergeHistoryResults() -- State-History + Statistics zusammenfuehren

// Render:
html`
  <ha-card>
    <h1 class="card-header">${title}
      <a href="/history?...">
        <ha-icon-button .path=${mdiChartBoxOutline}></ha-icon-button>
      </a>
    </h1>
    <state-history-charts
      .hass=${this.hass}
      .historyData=${this._stateHistory}
      .names=${this._names}
      .hoursToShow=${this._hoursToShow}
      .showNames=${this._config.show_names !== false}
      .logarithmicScale=${this._config.logarithmic_scale}
      .minYAxis=${this._config.min_y_axis}
      .maxYAxis=${this._config.max_y_axis}
    ></state-history-charts>
  </ha-card>
`;
```

Config:

```typescript
export interface HistoryGraphCardConfig extends LovelaceCardConfig {
  entities: (EntityConfig | string)[];
  hours_to_show?: number;          // default: 24
  title?: string;
  show_names?: boolean;
  logarithmic_scale?: boolean;
  min_y_axis?: number;
  max_y_axis?: number;
  fit_y_data?: boolean;
  split_device_classes?: boolean;
}
```

### 6.2 Statistics Graph Card

Fuer laengere Zeitraeume mit aggregierten Statistiken:

```typescript
export interface StatisticsGraphCardConfig extends LovelaceCardConfig {
  entities: (EntityConfig | string)[];
  unit?: string;
  days_to_show?: number;
  period?: "auto" | "5minute" | "hour" | "day" | "week" | "month";
  stat_types?: "mean" | "min" | "max" | "sum" | ("mean" | "min" | "max" | "sum")[];
  chart_type?: "line" | "bar";
  // ... weitere Options
}
```

### 6.3 Sensor Card mit Graph-Footer

Die `hui-sensor-card` erweitert `hui-entity-card` und fuegt einen Graph-Footer hinzu:

```typescript
@customElement("hui-sensor-card")
class HuiSensorCard extends HuiEntityCard {
  public setConfig(config: SensorCardConfig): void {
    // Konvertiert graph-Config zu einem Footer-Element:
    const entityCardConfig: EntityCardConfig = { ...config };
    if (config.graph === "line") {
      entityCardConfig.footer = {
        type: "graph",
        entity: config.entity,
        hours_to_show: config.hours_to_show || DEFAULT_HOURS_TO_SHOW,
        detail: config.detail || 1,
        limits: config.limits,
      } as GraphHeaderFooterConfig;
    }
    super.setConfig(entityCardConfig);
  }
}
```

---

## 7. Advanced Card Features

### 7.1 Card Features (hui-card-features)

Card Features sind modulare UI-Elemente die Cards erweitern:

```typescript
export interface LovelaceCardFeature extends HTMLElement {
  hass?: HomeAssistant;
  context?: LovelaceCardFeatureContext;
  setConfig(config: LovelaceCardFeatureConfig);
  color?: string;
  position?: LovelaceCardFeaturePosition;  // "bottom" | "inline"
}

// Context verbindet Feature mit der Parent-Card:
export interface LovelaceCardFeatureContext {
  entity_id?: string;
  area_id?: string;
}
```

Beispiel-Feature-Typen: `light-brightness`, `target-temperature`, `cover-position`, `toggle`, `trend-graph`, `bar-gauge`, `area-controls`, etc.

### 7.2 Conditional Display

```typescript
// In Card-Config:
{
  type: "conditional",
  conditions: [
    { condition: "state", entity: "sensor.moisture", state: "low" }
  ],
  card: {
    type: "custom:kamerplanter-alert-card",
    entity: "sensor.moisture"
  }
}

// Visibility auf Card-Ebene (keine Wrapper-Card noetig):
{
  type: "custom:kamerplanter-plant-card",
  entity: "sensor.tomato",
  visibility: [
    { condition: "state", entity: "input_boolean.show_plants", state: "on" }
  ]
}
```

### 7.3 shouldUpdate-Optimierung

```typescript
import { hasConfigOrEntityChanged } from "../common/has-changed";

protected shouldUpdate(changedProps: PropertyValues): boolean {
  return hasConfigOrEntityChanged(this, changedProps);
}
```

Die Utility prueft:
1. Hat sich `_config` geaendert? → true
2. Hat sich `hass` nicht geaendert? → false
3. Hat sich der State der konfigurierten Entity geaendert? → true/false

### 7.4 Header/Footer-Elemente

Cards koennen Header und Footer haben:

```typescript
// In setConfig():
if (this._config.footer) {
  this._footerElement = createHeaderFooterElement(this._config.footer);
  this._footerElement.type = "footer";
  if (this._hass) this._footerElement.hass = this._hass;
}

// In render():
html`
  <ha-card>
    ${this._headerElement ? html`<div class="header-footer header">${this._headerElement}</div>` : ""}
    <div class="card-content">...</div>
    ${this._footerElement ? html`<div class="header-footer footer">${this._footerElement}</div>` : ""}
  </ha-card>
`;
```

---

## 8. Pattern-Zusammenfassung fuer Custom Cards

### 8.1 Minimales Custom Card Template

```javascript
class MyCustomCard extends HTMLElement {

  // --- Card Picker Integration ---
  static getStubConfig() {
    return { entity: "" };
  }

  // --- Lifecycle ---
  setConfig(config) {
    if (!config.entity) throw new Error("Entity required");
    this._config = config;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() { return 3; }

  getGridOptions() {
    return { columns: 12, rows: 3, min_columns: 6 };
  }

  // --- Render ---
  _render() {
    if (!this._hass || !this._config) return;
    const stateObj = this._hass.states[this._config.entity];
    if (!stateObj) {
      this.innerHTML = `<ha-card><hui-warning>Entity not found</hui-warning></ha-card>`;
      return;
    }
    this.innerHTML = `
      <ha-card>
        <div class="card-content">
          ${stateObj.state} ${stateObj.attributes.unit_of_measurement || ""}
        </div>
      </ha-card>
    `;
  }
}

customElements.define("my-custom-card", MyCustomCard);
window.customCards = window.customCards || [];
window.customCards.push({ type: "my-custom-card", name: "My Card" });
```

### 8.2 Empfohlene Patterns fuer Kamerplanter

| Pattern | Empfehlung | Grund |
|---------|------------|-------|
| Base Class | Vanilla `HTMLElement` (kein LitElement extern) | Keine externe Abhaengigkeit, einfacher zu deployen |
| State-Zugriff | `this._hass.states[entityId]` | Standard HA Pattern |
| Formatierung | `this._hass.formatEntityStateToParts(stateObj)` | Lokalisierung automatisch |
| Icons | `<ha-icon icon="mdi:water">` oder `<ha-svg-icon>` | Verfuegbar im HA-Kontext |
| Card-Container | `<ha-card>` | Einheitliches Aussehen |
| Actions | `fireEvent(this, "hass-more-info", { entityId })` | Einfachste Integration |
| Config-Validierung | Exception in `setConfig()` | HA zeigt Error Card |
| Theming | CSS Custom Properties nutzen | Automatisches Dark/Light Mode |
| Problem-States | `var(--error-color)` fuer Warnungen | Konsistentes HA-Design |
| Unavailable | Pruefe `stateObj.state === "unavailable"` | Graceful Degradation |

### 8.3 CSS Custom Properties Cheatsheet fuer Custom Cards

```css
/* In einer Custom Card verwenden: */
ha-card {
  /* Automatisch von ha-card gesetzt: */
  /* background, border, border-radius, box-shadow */
}

/* Eigene Inhalte: */
.my-value {
  color: var(--primary-text-color);
  font-size: var(--ha-font-size-3xl);          /* Grosser Wert */
}
.my-label {
  color: var(--secondary-text-color);
  font-size: var(--ha-font-size-l);
}
.my-icon {
  color: var(--state-icon-color);              /* Standard-Icon-Farbe */
}
.my-warning {
  color: var(--error-color);                   /* Rot fuer Probleme */
  font-weight: var(--ha-font-weight-bold);
}
.my-divider {
  background: var(--divider-color);
}
.my-focus:focus {
  outline: none;
  background: var(--divider-color);
  border-radius: var(--ha-border-radius-pill);
}
```

---

## 9. Relevanz fuer kamerplanter-plant-card

Die offizielle `hui-plant-status-card` zeigt:

1. **Sensor-Icon-Map:** Statisches Mapping von Attributnamen zu Icons (moisture, temperature, brightness, conductivity, battery)
2. **Problem-Highlighting:** `stateObj.attributes.problem` wird geprueft, Werte in Rot hervorgehoben
3. **Sensor-Entities:** Plant-Entity hat `attributes.sensors` Dict mit Referenzen auf Sensor-Entities
4. **Entity-Picture:** Optionales Pflanzen-Bild als Banner-Hintergrund
5. **More-Info Drill-Down:** Klick auf Attribut oeffnet More-Info des zugehoerigen Sensors
6. **Einfache Struktur:** ~150 Zeilen, keine externen Abhaengigkeiten

Fuer unsere Custom Card koennen wir dieses Pattern erweitern um:
- Phasen-Anzeige (Vegetativ, Bluete, etc.)
- VPD-Berechnung und -Anzeige
- Naehrstoff-Status
- Aufgaben-Countdown
- Bewaesserungsplan-Status
- Toggle-Sektionen fuer Detailansichten

---

## Quellen

- [Home Assistant Frontend Repository](https://github.com/home-assistant/frontend)
- [Custom Card Developer Documentation](https://developers.home-assistant.io/docs/frontend/custom-ui/custom-card/)
- [Thomas Loven's Simplest Custom Card Gist](https://gist.github.com/thomasloven/1de8c62d691e754f95b023105fe4b74b)
