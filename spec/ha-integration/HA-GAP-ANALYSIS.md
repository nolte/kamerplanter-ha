# Gap-Analyse: Kamerplanter HA-Integration vs. Best Practices

```yaml
Stand: 2026-04-03
Quellen:
  - developers.home-assistant.io (April 2026)
  - home-assistant/frontend (dev branch)
  - HACS Requirements (hacs.xyz)
  - HA-DEVELOPER-DOCS-RESEARCH.md (Agent 1)
  - LOVELACE-CARD-PATTERNS.md (Agent 2)
  - HA-DEVELOPER-PATTERNS.md (Agent 3)
Analysiert: custom_components/kamerplanter/
```

---

## Bewertungsschema

| Kategorie | Bedeutung |
|-----------|-----------|
| **KRITISCH** | Verletzt HA Best Practice, blockiert Quality Scale Bronze oder HACS-Akzeptanz |
| **HOCH** | Weicht signifikant von Best Practice ab, sollte vor Release gefixt werden |
| **MITTEL** | Verbesserungspotential, kein Blocker |
| **NIEDRIG** | Nice-to-have, kosmetisch |
| **OK** | Entspricht Best Practice |

---

## 1. Integration Architecture

### GAP-001: `hass.data` statt `runtime_data` (HOCH)

**Best Practice (seit HA 2024.x):**
```python
type KamerplanterConfigEntry = ConfigEntry[KamerplanterRuntimeData]

@dataclass
class KamerplanterRuntimeData:
    api: KamerplanterApi
    coordinators: dict[str, DataUpdateCoordinator]

async def async_setup_entry(hass, entry: KamerplanterConfigEntry) -> bool:
    entry.runtime_data = KamerplanterRuntimeData(api=api, coordinators=coordinators)
```

**Ist-Zustand (`__init__.py`):**
```python
type KamerplanterConfigEntry = ConfigEntry  # Untypisiert!
hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
    "api": api,
    "coordinators": coordinators,
}
```

**Problem:** `hass.data`-Pattern ist deprecated. `runtime_data` wird bei Unload automatisch aufgeraeumt, ist typsicher und erfordert kein manuelles `hass.data.pop()`.

**Auswirkung:** Manuelles Cleanup in `async_unload_entry` ist fehleranfaellig. Service-Handler greifen unsicher auf `hass.data[DOMAIN]` zu.

**Fix:** Migration auf `entry.runtime_data` mit typisiertem `KamerplanterConfigEntry`.

---

### GAP-002: Fehlende Base Entity Klasse (HOCH)

**Best Practice:** Eine gemeinsame `entity.py` mit Base Entity, die `CoordinatorEntity` erweitert und `device_info`, `unique_id`, `has_entity_name` zentral definiert.

```python
# entity.py
class KamerplanterEntity(CoordinatorEntity[KamerplanterCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator, description):
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(...)
```

**Ist-Zustand:** Keine `entity.py`. Jede Plattform (sensor.py, binary_sensor.py, etc.) definiert eigene Entity-Klassen mit duplizierten Patterns. `device_info`-Funktionen (`plant_device_info`, `server_device_info`, `location_device_info`) sind in `sensor.py` definiert und werden von `binary_sensor.py` importiert.

**Auswirkung:** Code-Duplizierung, inkonsistente Entity-Konstruktion, `sensor.py` wird zur Grab-bag-Datei.

---

### GAP-003: Fehlende `EntityDescription`-Pattern (HOCH)

**Best Practice:** Entities werden deklarativ ueber `SensorEntityDescription`-Tuples definiert:

```python
SENSOR_DESCRIPTIONS = (
    SensorEntityDescription(
        key="phase",
        translation_key="phase",
    ),
    SensorEntityDescription(
        key="vpd_target",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement="kPa",
        state_class=SensorStateClass.MEASUREMENT,
    ),
)
```

**Ist-Zustand (`sensor.py`):** Jede Sensor-Klasse ist eine eigene Klasse mit hardcodierten Attributen (`PlantPhaseSensor`, `PlantDaysInPhaseSensor`, `PlantVpdTargetSensor`, etc.). Dutzende individuelle Klassen statt deklarativer Beschreibungen.

**Auswirkung:** ~800 Zeilen sensor.py statt ~200 mit EntityDescription-Pattern. Jede neue Entity erfordert eine neue Klasse.

---

### GAP-004: Services in `async_setup_entry` statt `async_setup` (MITTEL)

**Best Practice (HA Docs):** Domain-Services gehoeren in `async_setup()` (einmal pro Integration), nicht in `async_setup_entry()` (einmal pro Config Entry).

**Ist-Zustand:** Services werden in `_async_register_services()` registriert, aufgerufen aus `async_setup_entry()`, mit Idempotenz-Guard (`hass.services.has_service()`).

**Bewertung:** Der Idempotenz-Guard funktioniert, aber das Pattern ist nicht canonical. Fuer Custom Integrations ohne `async_setup` ist es akzeptabel, aber die Service-Handler schliessen ueber `hass`-Closures, was das Testing erschwert.

---

### GAP-005: Fehlende `_async_setup()` auf Coordinators (MITTEL)

**Best Practice (seit HA 2024.8):** Einmalige Initialisierung in `_async_setup()` statt in `_async_update_data()`:

```python
async def _async_setup(self) -> None:
    self.initial_data = await self.client.get_metadata()
```

**Ist-Zustand:** Alle Coordinators laden alles direkt in `_async_update_data()`. Es gibt kein einmaliges Setup (z.B. Fertilizer-Lookup, Tank-Lookup) das zwischen Updates wiederverwendet wird.

**Auswirkung:** `KamerplanterLocationCoordinator._async_update_data()` holt bei JEDEM Poll alle Fertilizers, alle Tanks, alle Runs pro Location. Das einmalige Laden von Stammdaten (Fertilizer-Names, Tank-Zuordnungen) in `_async_setup()` wuerde die API-Last deutlich reduzieren.

---

### GAP-006: Fehlende `async_timeout` in Coordinators (NIEDRIG)

**Best Practice:**
```python
async with async_timeout.timeout(10):
    return await self.api.fetch_data()
```

**Ist-Zustand:** Kein Timeout in den Coordinator `_async_update_data()` Methoden. Wenn die API haengt, blockiert der Coordinator unbegrenzt.

---

## 2. Config Flow

### GAP-007: Fehlender Reauth-Flow (HOCH)

**Best Practice (Quality Scale Silver):** Bei `ConfigEntryAuthFailed` muss ein Reauth-Flow verfuegbar sein:

```python
async def async_step_reauth(self, entry_data):
    return await self.async_step_reauth_confirm()

async def async_step_reauth_confirm(self, user_input=None):
    if user_input:
        return self.async_update_reload_and_abort(
            self._get_reauth_entry(), data_updates=new_data
        )
    return self.async_show_form(step_id="reauth_confirm", ...)
```

**Ist-Zustand:** Coordinators raisen korrekt `ConfigEntryAuthFailed`, aber `config_flow.py` hat keinen `async_step_reauth`. HA zeigt dem User "Reauthentication required", aber es gibt keinen Flow dafuer.

**Auswirkung:** Bei API-Key-Ablauf oder -Revocation muss der User die Integration komplett loeschen und neu einrichten.

---

### GAP-008: Fehlender Reconfigure-Flow (MITTEL)

**Best Practice:** URL-Aenderung (z.B. neuer Server) ueber Reconfigure-Flow statt Integration loeschen + neu einrichten:

```python
async def async_step_reconfigure(self, user_input=None):
    if user_input:
        return self.async_update_reload_and_abort(
            self._get_reconfigure_entry(), data_updates=user_input
        )
```

**Ist-Zustand:** Nicht implementiert. User muss Integration loeschen und neu einrichten bei URL-Aenderung.

---

### GAP-009: Fehlende Unique ID auf Config Entry (MITTEL)

**Best Practice:** Config Flow setzt `async_set_unique_id()` + `_abort_if_unique_id_configured()` um Duplikate zu verhindern.

**Ist-Zustand:** `config_flow.py` setzt keine Unique ID. Dadurch kann derselbe Kamerplanter-Server + Tenant mehrfach konfiguriert werden.

**Fix:** `await self.async_set_unique_id(f"{base_url}_{tenant_slug}")` nach erfolgreicher Validierung.

---

### GAP-010: `OptionsFlow` statt `OptionsFlowWithReload` (NIEDRIG)

**Best Practice (seit HA 2024.11):** `OptionsFlowWithReload` statt manuellem Update-Listener:

```python
class KamerplanterOptionsFlow(OptionsFlowWithReload):
    ...
```

**Ist-Zustand:** `KamerplanterOptionsFlow(OptionsFlow)` mit separatem `entry.add_update_listener()`.

**Auswirkung:** Funktioniert identisch, aber `OptionsFlowWithReload` ist der moderne, cleane Weg.

---

## 3. Entity Patterns

### GAP-011: Fehlende `translation_key` fuer Entity-States (HOCH)

**Best Practice:** Custom States (z.B. Wachstumsphasen) in `strings.json` definieren:

```json
{
  "entity": {
    "sensor": {
      "phase": {
        "name": "Growth Phase",
        "state": {
          "germination": "Germination",
          "seedling": "Seedling",
          "vegetative": "Vegetative",
          "flowering": "Flowering"
        }
      }
    }
  }
}
```

**Ist-Zustand:** `strings.json` enthaelt nur Config-Flow-Strings. Entity-States werden als rohe Strings an HA uebergeben, ohne Uebersetzung.

**Auswirkung:** Phasennamen erscheinen in HA immer auf Englisch, unabhaengig von der HA-Sprache. Kein i18n.

---

### GAP-012: Fehlende `icons.json` (MITTEL)

**Best Practice:** Icons pro Entity und pro State in `icons.json`:

```json
{
  "entity": {
    "sensor": {
      "phase": {
        "default": "mdi:sprout",
        "state": {
          "germination": "mdi:seed",
          "flowering": "mdi:flower"
        }
      }
    }
  },
  "services": {
    "fill_tank": { "service": "mdi:water-plus" }
  }
}
```

**Ist-Zustand:** Icons werden per `_attr_icon` auf Entity-Ebene gesetzt. Keine `icons.json`.

---

### GAP-013: `entity_id` manuell gesetzt (HOCH)

**Best Practice:** `entity_id` wird NICHT manuell gesetzt. HA generiert es automatisch aus `has_entity_name`, Device-Name und Entity-Name:

```python
# RICHTIG: HA generiert entity_id automatisch
self._attr_has_entity_name = True
self._attr_name = "Phase"
# → sensor.kamerplanter_server_phase (basierend auf Device-Name)
```

**Ist-Zustand:** Jede Entity setzt `self.entity_id` manuell:
```python
self.entity_id = f"sensor.kp_{slug}_phase"
```

**Problem:** Manuelles Setzen von `entity_id` verhindert, dass der User die Entity umbenennen kann, und ist ein Anti-Pattern. Es kann auch zu Konflikten bei Multi-Instance fuehren.

**Auswirkung:** Quality Scale verlangt, dass `entity_id` vom Framework generiert wird. Manuelles Setzen gilt als Fehler.

---

### GAP-014: Fehlende `EntityCategory` Nutzung (NIEDRIG)

**Best Practice:** Diagnostik-Entities als `EntityCategory.DIAGNOSTIC` markieren:

```python
_attr_entity_category = EntityCategory.DIAGNOSTIC
```

**Ist-Zustand:** Keine Entity nutzt `EntityCategory`. Der Refresh-Button (`button.py`) sollte `EntityCategory.CONFIG` sein, der "Sensor Offline"-Binary-Sensor `EntityCategory.DIAGNOSTIC`.

---

### GAP-015: Device-Hierarchie flach statt via_device (MITTEL)

**Best Practice:** Multi-Endpoint-Geraete als Device-Hierarchie mit `via_device`:

```python
# Server Device (Parent)
DeviceInfo(
    identifiers={(DOMAIN, f"{entry.entry_id}_server")},
    name="Kamerplanter",
    manufacturer="Kamerplanter",
    model="Server",
)

# Plant Device (Child)
DeviceInfo(
    identifiers={(DOMAIN, f"plant_{plant_key}")},
    name=plant_name,
    via_device=(DOMAIN, f"{entry.entry_id}_server"),
)
```

**Ist-Zustand:** `sensor.py` definiert separate `plant_device_info()`, `location_device_info()`, `server_device_info()` Funktionen. Pflanzen und Locations sind eigenstaendige Devices, aber OHNE `via_device` zum Server.

**Auswirkung:** In der HA Device Registry erscheinen alle Devices flach nebeneinander ohne erkennbare Hierarchie.

---

## 4. Diagnostics

### GAP-016: Fehlende `async_redact_data` (HOCH)

**Best Practice:**
```python
from homeassistant.components.diagnostics import async_redact_data

TO_REDACT = {"api_key", "password", "token"}

async def async_get_config_entry_diagnostics(hass, entry):
    return {
        "entry_data": async_redact_data(dict(entry.data), TO_REDACT),
        ...
    }
```

**Ist-Zustand (`diagnostics.py`):** API-Key wird manuell gekuerzt (`api_key[:8]...`), aber `async_redact_data` wird nicht verwendet. Der Tenant-Slug wird unredaktiert ausgegeben.

**Auswirkung:** Inkonsistente Redaktion. `async_redact_data` ist der Standard und redaktiert rekursiv.

---

## 5. Manifest & HACS

### GAP-017: Fehlende Felder in `manifest.json` (HOCH)

**Best Practice:**
```json
{
  "domain": "kamerplanter",
  "name": "Kamerplanter",
  "version": "0.1.0",
  "documentation": "https://...",
  "issue_tracker": "https://...",
  "codeowners": ["@kamerplanter"],
  "config_flow": true,
  "iot_class": "cloud_polling",
  "integration_type": "hub",
  "requirements": [],
  "loggers": ["custom_components.kamerplanter"]
}
```

**Ist-Zustand:**
```json
{
  "domain": "kamerplanter",
  "name": "Kamerplanter",
  "codeowners": ["@kamerplanter"],
  "config_flow": true,
  "documentation": "https://github.com/kamerplanter/kamerplanter-ha",
  "iot_class": "cloud_polling",
  "issue_tracker": "https://github.com/kamerplanter/kamerplanter-ha/issues",
  "requirements": [],
  "version": "0.1.0"
}
```

**Fehlend:**
- `integration_type`: Sollte `"hub"` sein (mehrere Geraete/Entities)
- `loggers`: Sollte `["custom_components.kamerplanter"]` sein fuer korrektes Log-Level-Management

---

### GAP-018: Fehlende `hacs.json` im Integrations-Root (NIEDRIG)

**Best Practice:** `hacs.json` im Repository-Root:
```json
{
  "name": "Kamerplanter",
  "render_readme": true,
  "homeassistant": "2024.1.0"
}
```

**Ist-Zustand:** Existiert in Spec (HA-CUSTOM-INTEGRATION.md §HA-005), aber nicht im Code.

---

## 6. Custom Lovelace Cards

### GAP-019: Cards nicht als HACS Frontend-Plugin registriert (MITTEL)

**Best Practice:** Cards werden aus der Custom Integration heraus automatisch als Resource registriert, oder als separates HACS Frontend-Plugin mit eigenem `hacs.json`.

**Ist-Zustand:** Cards liegen in `www/` der Integration und `custom_components/kamerplanter/www/`, muessen aber manuell als Resource registriert werden. Keine automatische Registrierung.

---

### ~~GAP-020~~: `window.customCards` Registrierung — **OK**

Alle 4 Cards (`plant-card`, `tank-card`, `mix-card`, `care-card`) registrieren sich korrekt ueber `window.customCards.push()` mit `type`, `name` und `description`. **Kein Gap.**

---

### GAP-021: `getGridOptions()` nur auf 3 von 4 Cards (NIEDRIG)

**Best Practice (Sections View):**
```javascript
getGridOptions() {
  return { columns: 6, rows: 3, min_columns: 3, min_rows: 2, max_rows: 6 };
}
```

**Ist-Zustand:** `plant-card`, `tank-card` und `mix-card` implementieren `getGridOptions()` korrekt. Die `care-card` (in `custom_components/www/`) hat nur `getCardSize()` aber kein `getGridOptions()`.

Alle 4 Cards haben `getConfigElement()`, `getStubConfig()` und Schema-basierte Editoren — vorbildlich.

---

### GAP-022: Inline-CSS statt CSS Custom Properties (MITTEL)

**Best Practice:** HA CSS Custom Properties fuer Farben, Fonts, Spacing verwenden:
```css
.my-label {
  color: var(--secondary-text-color);
  font-size: var(--ha-font-size-l);
}
```

**Ist-Zustand:** Cards verwenden `var(--primary-text-color)` korrekt fuer Farben, aber hardcodierte Pixel-Werte fuer Spacing und Font-Sizes (`font-size: 1.15em`, `padding: 16px`). Die neueren HA-Variablen `--ha-font-size-*`, `--ha-space-*`, `--ha-font-weight-*` werden nicht verwendet.

**Bewertung:** Teilweise OK. Die grundlegenden Farbvariablen sind korrekt. Die Font/Spacing-Variablen sind relativ neu und noch nicht in allen HA-Versionen verfuegbar.

---

### GAP-023: Keine Action-Handling-Integration (NIEDRIG)

**Best Practice:** Cards unterstuetzen tap/hold/double-tap Actions:
```javascript
// fireEvent(this, "hass-more-info", { entityId: "sensor.x" });
```

**Ist-Zustand:** Cards sind reine Anzeige-Cards ohne Interaktion (ausser den Done-Buttons in der Care Card). Kein `more-info` bei Klick auf Werte.

---

## 7. API & Auth Patterns

### GAP-033: API-Code direkt in Integration statt PyPI-Bibliothek (MITTEL)

**Best Practice (HA Core):** Alle API-spezifische Logik MUSS in einer separaten PyPI-Bibliothek liegen, nicht in der Integration. Die Integration importiert nur die Bibliothek.

**Ist-Zustand:** `api.py` (446 Zeilen) liegt direkt in `custom_components/kamerplanter/`. Fuer **Core-Integrations** ist das ein harter Blocker, fuer **HACS Custom Integrations** wird es toleriert.

**Bewertung:** Kein Blocker fuer HACS, aber bei einem eventuellen Core-PR muesste `kamerplanter-api` als separates PyPI-Paket publiziert werden. Fuer den aktuellen Scope akzeptabel.

---

### GAP-034: Shared aiohttp Session korrekt verwendet — **OK**

Die Integration nutzt korrekt `async_get_clientsession(hass)` in `__init__.py` und `config_flow.py`. **Kein Gap.**

---

## 8. Fehlende Patterns aus Research

### GAP-028: Fehlender `always_update=False` auf Coordinators (MITTEL)

**Best Practice:** Wenn Daten via `__eq__` vergleichbar sind (dicts, dataclasses), sollte `always_update=False` gesetzt werden um unnoetige Entity-Updates zu vermeiden.

**Ist-Zustand:** Keiner der 5 Coordinators setzt `always_update`. Default ist `True` — d.h. bei JEDEM 5-Minuten-Poll werden ALLE Entities updated, auch wenn sich nichts geaendert hat.

**Auswirkung:** Unnoetige State-Machine-Writes, History-Eintraege, und Automation-Trigger.

---

### GAP-029: `sensor.py` ist 1907 Zeilen mit 40+ Klassen (HOCH)

**Ist-Zustand:** Eine einzelne Datei enthaelt alle Sensor-Entities: Plant-Sensors (7 Typen), Run-Sensors (7 Typen), Location-Sensors (12 Typen), Tank-Sensors (2 Typen), Task-Sensors (3 Typen). Dazu `device_info`-Helper-Funktionen die von anderen Plattformen importiert werden.

**Best Practice:** Aufteilen in:
- `entity.py` — Base Entity, DeviceInfo-Patterns
- `sensor.py` — EntityDescription-basierte Sensor-Definitionen
- Ggf. `sensor_plant.py`, `sensor_location.py`, `sensor_tank.py` bei dieser Groesse

---

### GAP-030: Fehlende `available`-Property auf Entity-Ebene (NIEDRIG)

**Best Practice:** Entities sollten `available = False` zurueckgeben wenn ihre spezifischen Daten fehlen (nicht nur wenn der Coordinator fehlschlaegt):

```python
@property
def available(self) -> bool:
    return super().available and self._plant_key in self.coordinator.data_map
```

**Ist-Zustand:** `KpSensorBase` nutzt nur das default `CoordinatorEntity.available`. Wenn eine Pflanze entfernt wird, bleibt die Entity als `available` aber mit `None`-State.

---

### GAP-031: RestoreEntity auf fast allen Entities (NIEDRIG)

**Ist-Zustand:** Die meisten Entities erben von `RestoreEntity`. Das ist sinnvoll fuer Binary-Sensors (Needs Attention behalt Zustand ueber Neustarts), aber fragwuerdig fuer Sensoren die bei jedem Poll aktualisiert werden (PlantPhaseSensor, etc.).

**Best Practice:** `RestoreEntity` nur verwenden wenn der letzte Zustand zwischen Neustarts relevant ist UND nicht sofort durch den naechsten Poll ueberschrieben wird.

---

### GAP-032: Kein `flow_title` in strings.json (NIEDRIG)

**Best Practice:** `flow_title` zeigt kontextuelle Informationen waehrend des Config Flows:

```json
{
  "config": {
    "flow_title": "Kamerplanter ({url})"
  }
}
```

**Ist-Zustand:** Nicht vorhanden. Standard-Titel wird angezeigt.

---

## 8. Repair Flows & Error Handling

### GAP-024: Fehlende Repair Issues (NIEDRIG)

**Best Practice:** Bei bekannten Problemen (z.B. API-Version-Mismatch, fehlende Berechtigungen) Repair Issues erstellen:

```python
ir.async_create_issue(hass, DOMAIN, "api_version_mismatch", ...)
```

**Ist-Zustand:** Nicht implementiert. Alle Fehler werden nur geloggt.

---

## 8. Testing

### GAP-025: Keine Tests vorhanden (KRITISCH)

**Best Practice (Quality Scale Bronze):** Vollstaendige Config-Flow-Tests sind Pflicht:
- Erfolgreicher Setup
- Verbindungsfehler
- Auth-Fehler
- Bereits konfiguriert
- Options Flow

**Ist-Zustand:** Keine Tests im HA-Integration-Verzeichnis.

**Auswirkung:** Blockiert Quality Scale Bronze. Fuer HACS nicht zwingend, aber fuer Qualitaet essenziell.

---

## 9. Weitere fehlende Features

### GAP-026: Fehlender `async_remove_config_entry_device` (NIEDRIG)

**Best Practice:** Erlaubt dem User, einzelne Devices (z.B. entfernte Pflanzen) zu loeschen:
```python
async def async_remove_config_entry_device(hass, config_entry, device_entry) -> bool:
    return True
```

**Ist-Zustand:** Nicht implementiert. Verwaiste Devices (entfernte Pflanzen) bleiben in der Registry.

---

### GAP-027: Coordinator macht zu viele API-Calls pro Update (HOCH)

**Ist-Zustand (`coordinator.py`):** `KamerplanterPlantCoordinator._async_update_data()` macht fuer JEDE Pflanze:
1. `async_get_plants()` (1 Call)
2. Pro Pflanze: `async_get_plant_nutrient_plan()` (N Calls)
3. Pro Pflanze: `async_get_plant_current_dosages()` (N Calls)
4. Pro Pflanze: `async_get_plant_active_channels()` (N Calls)
5. Pro Pflanze: `async_get_plant_phase_history()` (N Calls)

Bei 10 Pflanzen: **41 API-Calls pro 5-Minuten-Poll.**

`KamerplanterLocationCoordinator` ist noch schlimmer — pro Location werden Sites, Trees, Runs, Slots, Plants, Plans, Entries, Timelines, Tanks, Tank-Fills, Tank-Sensors geholt.

**Best Practice:** Bulk-/Summary-Endpoints im Backend bereitstellen, oder mindestens `_async_setup()` fuer Stammdaten nutzen und nur veraenderliche Daten pollen.

---

## Zusammenfassung: Priorisierte Massnahmen

### Phase 1 — Muss vor Release (KRITISCH + HOCH)

| # | Gap | Aufwand | Prioritaet |
|---|-----|---------|------------|
| GAP-025 | Tests erstellen (Config Flow, Coordinator) | Hoch | KRITISCH |
| GAP-001 | Migration auf `runtime_data` | Mittel | HOCH |
| GAP-002 | Base Entity in `entity.py` | Mittel | HOCH |
| GAP-003 | EntityDescription-Pattern | Hoch | HOCH |
| GAP-007 | Reauth-Flow implementieren | Mittel | HOCH |
| GAP-011 | `translation_key` + Entity-States in strings.json | Mittel | HOCH |
| GAP-013 | Manuelles `entity_id` entfernen | Mittel | HOCH |
| GAP-016 | `async_redact_data` in Diagnostics | Niedrig | HOCH |
| GAP-017 | manifest.json ergaenzen | Niedrig | HOCH |
| GAP-027 | API-Call-Reduktion (Bulk-Endpoints / _async_setup) | Hoch | HOCH |

### Phase 2 — Sollte vor v1.0

| # | Gap | Aufwand |
|---|-----|---------|
| GAP-008 | Reconfigure-Flow | Mittel |
| GAP-009 | Unique ID auf Config Entry | Niedrig |
| GAP-012 | icons.json | Niedrig |
| GAP-015 | via_device Hierarchie | Niedrig |
| GAP-019 | Card Auto-Registration | Mittel |
| GAP-028 | always_update=False auf Coordinators | Niedrig |
| GAP-029 | sensor.py aufteilen (1907 Zeilen) | Hoch |

### Phase 3 — Nice-to-have

| # | Gap | Aufwand |
|---|-----|---------|
| GAP-004 | Services in async_setup | Mittel |
| GAP-005 | _async_setup() auf Coordinators | Mittel |
| GAP-006 | async_timeout in Coordinators | Niedrig |
| GAP-010 | OptionsFlowWithReload | Niedrig |
| GAP-014 | EntityCategory | Niedrig |
| GAP-018 | hacs.json | Niedrig |
| GAP-021 | getGridOptions() auf care-card | Niedrig |
| GAP-022 | CSS Custom Properties modernisieren | Niedrig |
| GAP-023 | Action-Handling auf Cards | Niedrig |
| GAP-024 | Repair Issues | Mittel |
| GAP-026 | async_remove_config_entry_device | Niedrig |
| GAP-030 | available-Property auf Entity-Ebene | Niedrig |
| GAP-031 | RestoreEntity-Verwendung ueberpruefen | Niedrig |
| GAP-032 | flow_title in strings.json | Niedrig |

---

## 11. Zusaetzliche Gaps aus Vertiefungs-Research

### GAP-035: Cards re-rendern bei JEDEM HA State-Change (MITTEL)

**Best Practice:** Card sollte nur re-rendern wenn sich die EIGENEN Entities geaendert haben:

```javascript
set hass(hass) {
  const oldState = this._hass?.states[this._config.entity];
  const newState = hass.states[this._config.entity];
  this._hass = hass;
  if (oldState === newState) return;  // Skip wenn Entity unveraendert
  this._update();
}
```

**Ist-Zustand (`kamerplanter-plant-card.js:687-690`):**
```javascript
set hass(hass) {
  this._hass = hass;
  this._update();  // Bei JEDEM State-Change in HA
}
```

**Auswirkung:** Bei 100+ Entities in einer HA-Instanz wird `_update()` dutzende Male pro Sekunde aufgerufen, obwohl sich die Kamerplanter-Daten nur alle 5 Minuten aendern. DOM-Rebuilds kosten CPU besonders auf schwacher Hardware (RPi).

---

### GAP-036: Fehlende `PARALLEL_UPDATES` Konstante (NIEDRIG)

**Best Practice (Quality Scale Silver):** Jede Plattform-Datei sollte `PARALLEL_UPDATES` definieren:

```python
PARALLEL_UPDATES = 1  # Serialize updates to prevent API flooding
```

**Ist-Zustand:** Keine Plattform-Datei setzt `PARALLEL_UPDATES`.

**Bewertung:** Bei Coordinator-basierten Entities ist das weniger kritisch, da der Coordinator selbst serialisiert. Aber fuer Services die API-Calls machen (fill_tank, water_channel) waere es relevant.

---

### GAP-037: Keine automatische Card-Resource-Registrierung (MITTEL)

**Best Practice:** Cards aus der Integration heraus automatisch als Lovelace-Resource registrieren:

```python
# In __init__.py oder eigene Datei
async def async_setup_entry(hass, entry):
    hass.http.register_static_path(
        "/kamerplanter/plant-card.js",
        hass.config.path("custom_components/kamerplanter/www/kamerplanter-plant-card.js"),
        cache_headers=True,
    )
```

**Ist-Zustand:** Cards muessen manuell als Lovelace-Resource registriert werden. User muss `/local/kamerplanter-plant-card.js` manuell in Dashboard-Config eintragen.

---

### GAP-038: `__pycache__` in Repository (NIEDRIG)

**Ist-Zustand:** `custom_components/kamerplanter/__pycache__/` enthaelt `.pyc` Dateien.

**Fix:** Zu `.gitignore` hinzufuegen.

---

## 12. Quality Scale Zusammenfassung

Abgleich gegen die 56 Rules der HA Integration Quality Scale:

### Bronze (19 Rules) — Aktueller Stand: 10/19 erfuellt

| Rule | Status | Gap |
|------|--------|-----|
| `config-flow` | OK | Config Flow vorhanden |
| `config-flow-test-coverage` | FEHLT | GAP-025 |
| `runtime-data` | FEHLT | GAP-001 |
| `has-entity-name` | OK | Alle Entities haben `_attr_has_entity_name = True` |
| `entity-unique-id` | OK | Alle Entities haben unique_id |
| `unique-config-entry` | FEHLT | GAP-009 |
| `test-before-configure` | OK | Config Flow testet Verbindung |
| `test-before-setup` | OK | `async_config_entry_first_refresh()` wirft bei Fehler |
| `action-setup` | TEILWEISE | GAP-004 (Services in setup_entry statt setup) |
| `appropriate-polling` | OK | 60s-300s je nach Datentyp |
| `brands` | OK | icon.png, logo.png vorhanden |
| `common-modules` | FEHLT | GAP-002 (keine entity.py) |
| `dependency-transparency` | OK | `requirements: []` |
| `docs-actions` | FEHLT | Keine Doku fuer Services |
| `docs-high-level-description` | TEILWEISE | README existiert in Spec |
| `docs-installation-instructions` | FEHLT | Keine Installations-Doku |
| `docs-removal-instructions` | FEHLT | Keine Deinstallations-Doku |
| `entity-event-setup` | OK | `async_added_to_hass` korrekt |
| `entity-unique-id` | OK | Alle haben unique_id |

### Silver (10 Rules) — Aktueller Stand: 4/10

| Rule | Status | Gap |
|------|--------|-----|
| `config-entry-unloading` | OK | `async_unload_entry` vorhanden |
| `reauthentication-flow` | FEHLT | GAP-007 |
| `entity-unavailable` | TEILWEISE | GAP-030 |
| `test-coverage` | FEHLT | GAP-025 |
| `integration-owner` | OK | @kamerplanter |
| `log-when-unavailable` | OK | Via Coordinator |
| `parallel-updates` | FEHLT | GAP-036 |
| `action-exceptions` | FEHLT | Services loggen Fehler, raisen nicht |
| `docs-configuration-parameters` | FEHLT | Keine Doku |
| `docs-installation-parameters` | FEHLT | Keine Doku |

### Gold (21 Rules) — Aktueller Stand: 3/21

| Rule | Status |
|------|--------|
| `devices` | OK (DeviceInfo vorhanden) |
| `diagnostics` | OK (diagnostics.py vorhanden) |
| `entity-device-class` | OK (SensorDeviceClass verwendet) |
| Rest | FEHLT (translation_key, icons.json, EntityCategory, Repair Issues, etc.) |

---

## Quellen

- [HA-DEVELOPER-DOCS-RESEARCH.md](HA-DEVELOPER-DOCS-RESEARCH.md) — Integration Architecture, Config Flow, Coordinator, Entity Patterns
- [LOVELACE-CARD-PATTERNS.md](LOVELACE-CARD-PATTERNS.md) — Card Lifecycle, Editor, Styling, Actions
- [HA-DEVELOPER-PATTERNS.md](HA-DEVELOPER-PATTERNS.md) — Entity Naming, DeviceInfo, Config Entry Lifecycle, Services, Repairs
- [HA-CUSTOM-INTEGRATION.md](HA-CUSTOM-INTEGRATION.md) — Bestehende Spezifikation
