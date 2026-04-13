# Spezifikation: Custom Lovelace Cards Best Practices

```yaml
ID: HA-SPEC-CARDS
Titel: Lovelace Cards auf HA Best Practices migrieren
Status: Spezifiziert
Version: 1.0
Datum: 2026-04-03
Behebt: GAP-021, GAP-022, GAP-023, GAP-035, GAP-037, GAP-038
Scope: custom_components/kamerplanter/www/*.js, custom_components/kamerplanter/www/*.js
Style Guide: spec/style-guides/HA-INTEGRATION.md §13
Referenz: spec/ha-integration/LOVELACE-CARD-PATTERNS.md
```

---

## 1. Ziel

Migration der 4 Custom Lovelace Cards auf HA Best Practices:
- Entity-Change-Detection im `set hass()` Setter (Performance)
- `getGridOptions()` auf allen Cards (Sections View)
- Action-Handling (more-info bei Klick auf Werte)
- Automatische Resource-Registrierung aus der Integration
- Moderne CSS Custom Properties
- `__pycache__` aus Git entfernen

---

## 2. Betroffene Cards

| Card | Datei | getGridOptions | Change-Detection | Actions |
|------|-------|---------------|-----------------|---------|
| Plant Card | `www/kamerplanter-plant-card.js` | OK | FEHLT | FEHLT |
| Tank Card | `www/kamerplanter-tank-card.js` | OK | FEHLT | FEHLT |
| Mix Card | `www/kamerplanter-mix-card.js` | OK | FEHLT | FEHLT |
| Care Card | `custom_components/.../www/kamerplanter-care-card.js` | FEHLT | FEHLT | TEILWEISE (Done-Buttons) |

---

## 3. Entity-Change-Detection (alle 4 Cards)

### 3.1 Problem

Alle Cards re-rendern bei **jedem** HA State-Change (jede Entity im System), nicht nur bei Aenderungen der eigenen Entities. Bei 100+ Entities in einer HA-Instanz bedeutet das dutzende unnoetige DOM-Updates pro Sekunde.

### 3.2 Pattern: Device-basierte Cards (Plant Card)

Die Plant Card zeigt alle Entities eines Devices. Die relevanten Entity-IDs muessen beim `setConfig()` gesammelt werden:

```javascript
setConfig(config) {
  if (!config.device_id) throw new Error("device_id is required");
  this._config = config;
  this._monitoredEntities = [];  // Wird in set hass() initialisiert
}

set hass(hass) {
  // Beim ersten Aufruf: Entity-IDs sammeln
  if (this._monitoredEntities.length === 0 && hass) {
    this._monitoredEntities = Object.keys(hass.states).filter(
      id => id.startsWith("sensor.kp_") || id.startsWith("binary_sensor.kp_")
    );
  }

  // Change-Detection: Nur rendern wenn eigene Entities sich geaendert haben
  const changed = !this._hass || this._monitoredEntities.some(
    id => this._hass.states[id] !== hass.states[id]
  );
  this._hass = hass;

  if (changed) {
    this._update();
  }
}
```

### 3.3 Pattern: Entity-basierte Cards (Tank Card, Mix Card)

Diese Cards referenzieren explizite Entity-IDs in der Config:

```javascript
set hass(hass) {
  const entities = this._getMonitoredEntities();
  const changed = !this._hass || entities.some(
    id => this._hass.states[id] !== hass.states[id]
  );
  this._hass = hass;
  if (changed) this._render();
}

_getMonitoredEntities() {
  // Tank Card: tank_entity + optional ph/ec/temp entities
  const ids = [this._config.tank_entity];
  if (this._config.ph_entity) ids.push(this._config.ph_entity);
  if (this._config.ec_entity) ids.push(this._config.ec_entity);
  if (this._config.temp_entity) ids.push(this._config.temp_entity);
  return ids.filter(Boolean);
}
```

### 3.4 Pattern: Sensor-basierte Cards (Care Card)

```javascript
set hass(hass) {
  const oldDue = this._hass?.states[this._config.entity_due];
  const newDue = hass.states[this._config.entity_due];
  const oldOverdue = this._hass?.states[this._config.entity_overdue];
  const newOverdue = hass.states[this._config.entity_overdue];
  this._hass = hass;

  if (oldDue !== newDue || oldOverdue !== newOverdue || !this._rendered) {
    this._render();
    this._rendered = true;
  }
}
```

---

## 4. getGridOptions (Care Card)

Die Care Card fehlt `getGridOptions()`. Ergaenzen:

```javascript
getGridOptions() {
  return {
    columns: 6,
    rows: 4,
    min_columns: 3,
    min_rows: 2,
    max_rows: 8,
  };
}
```

---

## 5. Action-Handling: more-info bei Klick

### 5.1 Plant Card

Bei Klick auf einen Wert (z.B. Phase, VPD Target) den HA more-info Dialog oeffnen:

```javascript
_handleMoreInfo(entityId) {
  const event = new Event("hass-more-info", { bubbles: true, composed: true });
  event.detail = { entityId };
  this.dispatchEvent(event);
}
```

Im Render:

```javascript
// Klickbarer Wert mit Cursor-Aenderung
<div class="kp-value clickable" onclick="...">
  ${phaseLabel}
</div>
```

CSS:

```css
.clickable {
  cursor: pointer;
  border-radius: var(--ha-border-radius-pill, 20px);
}
.clickable:hover {
  background: var(--divider-color, rgba(0,0,0,0.05));
}
.clickable:focus {
  outline: none;
  background: var(--divider-color);
}
```

### 5.2 Umsetzung

Da die Cards vanilla HTMLElement verwenden (kein LitElement/Directives), ist `fireEvent`/`actionHandler` nicht direkt verfuegbar. Stattdessen das einfache `hass-more-info` Event verwenden.

**Einschraenkung:** Nur `more-info` Action (kein tap/hold/double-tap). Fuer komplexere Actions waere LitElement-Migration noetig.

---

## 6. Automatische Resource-Registrierung

### 6.1 __init__.py Ergaenzung

Cards aus `custom_components/kamerplanter/www/` automatisch als Lovelace-Resource registrieren:

```python
from pathlib import Path

async def async_setup_entry(hass, entry):
    # ... bestehender Code ...

    # Auto-register Lovelace cards from www/ subdirectory
    www_dir = Path(__file__).parent / "www"
    if www_dir.is_dir():
        for js_file in www_dir.glob("*.js"):
            url_path = f"/{DOMAIN}/{js_file.name}"
            hass.http.register_static_path(url_path, str(js_file), cache_headers=True)
            _LOGGER.debug("Registered Lovelace resource: %s", url_path)
```

Damit sind die Cards unter `/kamerplanter/kamerplanter-care-card.js` erreichbar — der User muss sie nur noch als Resource im Dashboard eintragen:

```yaml
resources:
  - url: /kamerplanter/kamerplanter-care-card.js
    type: module
```

### 6.2 Standalone Cards (www/ im Repo-Root)

Die Cards in `custom_components/kamerplanter/www/` (plant-card, tank-card, mix-card) werden vom User manuell nach `/config/www/` kopiert und als `/local/kamerplanter-plant-card.js` eingebunden. Dieses Pattern bleibt unveraendert.

---

## 7. CSS Custom Properties Modernisierung

### 7.1 Minimale Anpassungen

Die Cards nutzen bereits die Basis-HA-Variablen korrekt (`--primary-text-color`, `--error-color`, etc.). Folgende Stellen koennen modernisiert werden:

**Vorher (hardcodiert):**
```css
font-weight: 600;
font-weight: 700;
```

**Nachher (HA-Variable):**
```css
font-weight: var(--ha-font-weight-medium, 500);
font-weight: var(--ha-font-weight-bold, 700);
```

**Hinweis:** Die `--ha-font-*` und `--ha-space-*` Variablen sind relativ neu. Fallback-Werte sind Pflicht fuer Kompatibilitaet mit aelteren HA-Versionen:

```css
font-size: var(--ha-font-size-l, 1.1em);
padding: var(--ha-space-4, 16px);
border-radius: var(--ha-border-radius-lg, 12px);
```

### 7.2 Keine Pflicht-Migration

Da die bestehenden Cards funktional korrekt sind und die Basis-Variablen verwenden, ist die Migration auf die neueren Variablen **optional**. Prioritaet liegt bei Change-Detection (Performance).

---

## 8. __pycache__ aus Git entfernen

```bash
# .gitignore ergaenzen
echo "__pycache__/" >> .gitignore
echo "*.pyc" >> .gitignore

# Bestehende Dateien aus Git entfernen
git rm -r --cached custom_components/kamerplanter/__pycache__/
```

---

## 9. Umsetzungsreihenfolge

1. `__pycache__` aus Git entfernen + `.gitignore`
2. Entity-Change-Detection auf allen 4 Cards implementieren
3. `getGridOptions()` auf Care Card ergaenzen
4. `hass-more-info` Action auf Plant Card (Klick auf Phase-Label oeffnet Entity-Details)
5. Auto-Resource-Registration in `__init__.py`
6. Optional: CSS Custom Properties modernisieren

---

## 10. Akzeptanzkriterien

- [ ] Alle 4 Cards rendern nur bei Aenderung eigener Entities (nicht bei jedem State-Change)
- [ ] Alle 4 Cards haben `getGridOptions()` (Sections View)
- [ ] Plant Card: Klick auf Phase-Label oeffnet more-info Dialog
- [ ] Cards in `custom_components/.../www/` werden automatisch registriert
- [ ] `__pycache__/` ist in `.gitignore` und nicht mehr in Git
- [ ] CSS verwendet HA-Variablen mit Fallback-Werten wo moeglich
