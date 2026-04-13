# HA-Integration Style Guide — Home Assistant Custom Component

> Verbindlicher Style Guide fuer die Kamerplanter Home Assistant Custom Integration.
> Basiert auf den offiziellen HA Developer Docs (Stand April 2026) und der Gap-Analyse (`spec/ha-integration/HA-GAP-ANALYSIS.md`).
> Wird durch **ruff** (Linting), **pytest** (Tests) und **HACS-Validation** geprueft.

**Scope:** `custom_components/kamerplanter/`

**Referenzen:**
- `spec/ha-integration/HA-DEVELOPER-DOCS-RESEARCH.md` — Integration Architecture
- `spec/ha-integration/HA-DEVELOPER-PATTERNS.md` — Entity/DeviceInfo/Config Patterns
- `spec/ha-integration/LOVELACE-CARD-PATTERNS.md` — Custom Card Patterns
- `spec/ha-integration/HA-GAP-ANALYSIS.md` — Delta-Analyse Ist/Soll

---

## 1. Statische Analyse & Tooling

| Tool | Zweck | Config |
|------|-------|--------|
| **Ruff** | Python Linting + Formatting | Geteilt mit Backend-Config |
| **hassfest** | HA-Manifest-Validierung | CI via `hacs/action@main` |
| **pytest** | Unit-Tests | `pytest-homeassistant-custom-component` |

### 1.1 Ruff-Konfiguration

```toml
[tool.ruff]
line-length = 120
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "SIM"]
ignore = ["B008"]
```

### 1.2 CI-Pruefung

```bash
ruff check custom_components/kamerplanter/
ruff format --check custom_components/kamerplanter/
pytest tests/ha-integration/ --cov=custom_components.kamerplanter --cov-report=term-missing
```

---

## 2. Verzeichnisstruktur

```
custom_components/kamerplanter/
├── custom_components/kamerplanter/
│   ├── __init__.py              # async_setup_entry, async_unload_entry, Services
│   ├── api.py                   # REST-Client (KamerplanterApi dataclass)
│   ├── config_flow.py           # ConfigFlow + OptionsFlow + ReauthFlow + ReconfigureFlow
│   ├── coordinator.py           # DataUpdateCoordinators (5 Stueck)
│   ├── entity.py                # ★ Base Entity (KamerplanterEntity) + DeviceInfo-Helper
│   ├── sensor.py                # Sensor-Entities via EntityDescription
│   ├── binary_sensor.py         # Binary-Sensor-Entities
│   ├── button.py                # Refresh-Button
│   ├── calendar.py              # Kalender-Entities
│   ├── todo.py                  # Todo-Listen
│   ├── diagnostics.py           # Diagnostik mit async_redact_data
│   ├── const.py                 # Konstanten (DOMAIN, Keys, Defaults)
│   ├── services.yaml            # Service-Definitionen mit Selectors
│   ├── strings.json             # Englische Strings (Referenz + Entity States)
│   ├── icons.json               # ★ Icon-Mapping pro Entity + Service
│   ├── translations/
│   │   ├── en.json
│   │   └── de.json
│   ├── manifest.json
│   ├── brand/
│   └── www/                     # Custom Lovelace Cards (auto-registered)
├── www/                         # Standalone Lovelace Cards
└── tests/                       # pytest Tests
    ├── conftest.py
    ├── test_config_flow.py
    ├── test_init.py
    ├── test_coordinator.py
    ├── test_sensor.py
    └── fixtures/
```

### 2.1 Neue Dateien (gegenueber v1)

| Datei | Zweck | Gap-Referenz |
|-------|-------|-------------|
| `entity.py` | Base Entity + DeviceInfo-Helper | GAP-002 |
| `icons.json` | Icon-Mapping pro Entity-State + Service | GAP-012 |
| `tests/` | Vollstaendige Testabdeckung | GAP-025 |

---

## 3. Runtime Data Pattern (PFLICHT)

### 3.1 Typisiertes ConfigEntry

```python
# __init__.py
from dataclasses import dataclass
from homeassistant.config_entries import ConfigEntry

@dataclass
class KamerplanterRuntimeData:
    """Runtime data for a Kamerplanter config entry."""
    api: KamerplanterApi
    coordinators: dict[str, DataUpdateCoordinator]

type KamerplanterConfigEntry = ConfigEntry[KamerplanterRuntimeData]
```

### 3.2 Setup mit runtime_data

```python
async def async_setup_entry(hass: HomeAssistant, entry: KamerplanterConfigEntry) -> bool:
    api = KamerplanterApi(...)
    coordinators = { "plants": ..., "locations": ..., ... }

    for coordinator in coordinators.values():
        await coordinator.async_config_entry_first_refresh()

    # ★ runtime_data statt hass.data[DOMAIN]
    entry.runtime_data = KamerplanterRuntimeData(api=api, coordinators=coordinators)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True
```

### 3.3 Unload (automatisch bereinigt)

```python
async def async_unload_entry(hass: HomeAssistant, entry: KamerplanterConfigEntry) -> bool:
    # runtime_data wird automatisch bereinigt — kein manuelles hass.data.pop() noetig
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
```

**Regel:** `hass.data[DOMAIN][entry.entry_id]` ist **verboten**. Immer `entry.runtime_data` verwenden.

---

## 4. Base Entity Pattern (PFLICHT)

### 4.1 entity.py

```python
"""Base entity for the Kamerplanter integration."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from .const import DOMAIN


class KamerplanterEntity(CoordinatorEntity):
    """Base entity for Kamerplanter."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry_id: str,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(coordinator)
        self._attr_device_info = device_info
        self._entry_id = entry_id
```

### 4.2 DeviceInfo-Hierarchie

```python
def server_device_info(entry: ConfigEntry) -> DeviceInfo:
    """Hub-Device (Parent aller Entities)."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="Kamerplanter",
        manufacturer="Kamerplanter",
        model="Plant Management Server",
    )

def plant_device_info(entry: ConfigEntry, plant: dict) -> DeviceInfo:
    """Plant-Device (Child des Servers)."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_plant_{plant['key']}")},
        name=plant.get("plant_name") or plant.get("instance_id") or plant["key"],
        manufacturer="Kamerplanter",
        model="Plant Instance",
        via_device=(DOMAIN, entry.entry_id),  # ★ Hierarchie zum Server
    )

def location_device_info(entry: ConfigEntry, loc: dict) -> DeviceInfo:
    """Location-Device (Child des Servers)."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_loc_{loc.get('key', '')}")},
        name=loc.get("name") or loc.get("key", ""),
        manufacturer="Kamerplanter",
        model="Location",
        via_device=(DOMAIN, entry.entry_id),
    )

def tank_device_info(entry: ConfigEntry, tank: dict) -> DeviceInfo:
    """Tank-Device (Child des Servers)."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_tank_{tank.get('key', '')}")},
        name=tank.get("name") or tank.get("key", ""),
        manufacturer="Kamerplanter",
        model="Tank",
        via_device=(DOMAIN, entry.entry_id),
    )
```

**Regeln:**
- Server-Device als Hub (kein `via_device`)
- Alle anderen Devices mit `via_device=(DOMAIN, entry.entry_id)` zum Server
- `identifiers` immer mit `entry.entry_id` Praefix (Multi-Instance-faehig)
- DeviceInfo-Funktionen in `entity.py`, **nicht** in `sensor.py`

---

## 5. Entity-ID-Generierung (PFLICHT)

### 5.1 Automatische Generierung durch HA

```python
# ★ RICHTIG: entity_id wird NICHT manuell gesetzt
class PlantPhaseSensor(KamerplanterEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "phase"

    def __init__(self, coordinator, entry, plant, device_info):
        super().__init__(coordinator, entry.entry_id, device_info)
        slug = plant["key"].replace("-", "_").lower()
        self._attr_unique_id = f"{entry.entry_id}_plant_{slug}_phase"
        # ★ KEIN self.entity_id = "sensor.kp_..."
```

HA generiert die `entity_id` automatisch aus Device-Name + Entity-Name.
Die entity_id basiert auf dem **uebersetzten Namen der HA-Systemsprache** bei der Erstregistrierung.

### 5.2 Englische entity_ids (PFLICHT)

Damit entity_ids immer englisch und sprachunabhaengig sind:

1. **HA-Systemsprache MUSS `en` sein** (`configuration.yaml: language: en`)
2. `strings.json` enthaelt englische Entity-Namen (Source of Truth)
3. `translations/de.json` enthaelt deutsche UI-Namen (nur Anzeige)
4. Nutzer koennen ihre persoenliche UI-Sprache auf Deutsch stellen

Beispiel:
- Device "Tomato #1" + Entity "Days Until Watering" → `sensor.tomato_1_days_until_watering`

**FALSCH** (bei `language: de`):
- `sensor.tomate_1_tage_bis_giessen` — deutsch, instabil, bricht bei Sprachwechsel

### 5.3 Verbotenes Pattern

```python
# ✗ VERBOTEN — Anti-Pattern
self.entity_id = f"sensor.kp_{slug}_phase"
```

### 5.4 unique_id Format

```
{entry_id}_{resource_type}_{resource_slug}_{suffix}
```

Beispiele:
```
abc123_plant_tomate_1_phase
abc123_loc_zelt_1_active_plants
abc123_tank_60l_fill_level
abc123_server_refresh_all
```

---

## 6. EntityDescription Pattern (PFLICHT fuer neue Entities)

### 6.1 Deklarative Sensor-Definitionen

```python
from homeassistant.components.sensor import SensorEntityDescription, SensorDeviceClass, SensorStateClass

PLANT_SENSOR_DESCRIPTIONS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="phase",
        translation_key="phase",
    ),
    SensorEntityDescription(
        key="days_in_phase",
        translation_key="days_in_phase",
        native_unit_of_measurement="d",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="vpd_target",
        translation_key="vpd_target",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement="kPa",
        state_class=SensorStateClass.MEASUREMENT,
    ),
)
```

### 6.2 Generische Entity-Klasse

```python
class KamerplanterPlantSensor(KamerplanterEntity, SensorEntity):
    """Sensor entity for plant data driven by EntityDescription."""

    entity_description: SensorEntityDescription

    def __init__(self, coordinator, entry, plant, description, device_info):
        super().__init__(coordinator, entry.entry_id, device_info)
        self.entity_description = description
        slug = plant["key"].replace("-", "_").lower()
        self._attr_unique_id = f"{entry.entry_id}_plant_{slug}_{description.key}"
        self._plant_key = plant["key"]

    @callback
    def _handle_coordinator_update(self) -> None:
        plant = self._find_plant()
        if plant:
            self._attr_native_value = self._extract_value(plant)
        self.async_write_ha_state()
```

### 6.3 Setup mit EntityDescription

```python
async def async_setup_entry(hass, entry, async_add_entities):
    data = entry.runtime_data
    entities = []
    for plant in data.coordinators["plants"].data or []:
        dev = plant_device_info(entry, plant)
        for desc in PLANT_SENSOR_DESCRIPTIONS:
            entities.append(KamerplanterPlantSensor(
                data.coordinators["plants"], entry, plant, desc, dev
            ))
    async_add_entities(entities)
```

---

## 7. Translations & Icons (PFLICHT)

### 7.1 strings.json mit Entity-States

```json
{
  "config": {
    "flow_title": "Kamerplanter ({url})",
    "step": {
      "user": {
        "title": "Connect to Kamerplanter",
        "data": { "url": "URL", "api_key": "API Key (kp_...)" }
      },
      "reauth_confirm": {
        "title": "Re-authenticate",
        "description": "Your API key is invalid or expired."
      },
      "reconfigure": {
        "title": "Reconfigure",
        "data": { "url": "URL" }
      },
      "tenant": {
        "title": "Select Tenant",
        "data": { "tenant_slug": "Tenant" }
      }
    },
    "error": {
      "cannot_connect": "Cannot connect to Kamerplanter",
      "invalid_auth": "Invalid or missing API key",
      "no_tenants": "No tenants found for this account"
    },
    "abort": {
      "already_configured": "This Kamerplanter instance is already configured",
      "reauth_successful": "Re-authentication successful"
    }
  },
  "options": {
    "step": {
      "init": {
        "title": "Kamerplanter Options",
        "data": {
          "poll_interval_plants": "Plants polling interval (seconds)",
          "poll_interval_locations": "Locations polling interval (seconds)",
          "poll_interval_alerts": "Alerts polling interval (seconds)",
          "poll_interval_tasks": "Tasks polling interval (seconds)"
        }
      }
    }
  },
  "entity": {
    "sensor": {
      "phase": {
        "name": "Growth Phase",
        "state": {
          "germination": "Germination",
          "seedling": "Seedling",
          "vegetative": "Vegetative",
          "flowering": "Flowering",
          "ripening": "Ripening",
          "harvest": "Harvest",
          "dormancy": "Dormancy",
          "flushing": "Flushing",
          "drying": "Drying",
          "curing": "Curing",
          "juvenile": "Juvenile",
          "climbing": "Climbing",
          "mature": "Mature",
          "senescence": "Senescence",
          "leaf_phase": "Leaf Phase",
          "short_day_induction": "Short Day Induction"
        }
      },
      "days_in_phase": { "name": "Days in Phase" },
      "vpd_target": { "name": "VPD Target" },
      "ec_target": { "name": "EC Target" },
      "nutrient_plan": { "name": "Nutrient Plan" },
      "active_channels": { "name": "Active Channels" },
      "phase_timeline": { "name": "Phase Timeline" },
      "next_phase": { "name": "Next Phase" },
      "run_status": { "name": "Status" },
      "plant_count": { "name": "Plant Count" },
      "active_runs": { "name": "Active Runs" },
      "active_plants": { "name": "Active Plants" },
      "tank_info": { "name": "Tank Info" },
      "tank_volume": { "name": "Volume" },
      "fill_level": { "name": "Fill Level" },
      "tasks_due_today": { "name": "Tasks Due Today" },
      "tasks_overdue": { "name": "Tasks Overdue" },
      "next_watering": { "name": "Next Watering" }
    },
    "binary_sensor": {
      "needs_attention": { "name": "Needs Attention" },
      "sensor_offline": { "name": "Sensor Offline" },
      "care_overdue": { "name": "Care Overdue" }
    },
    "button": {
      "refresh_all": { "name": "Refresh All Data" }
    },
    "calendar": {
      "phases": { "name": "Growth Phases" },
      "tasks": { "name": "Tasks" }
    },
    "todo": {
      "tasks": { "name": "Tasks" }
    }
  },
  "services": {
    "refresh_data": {
      "name": "Refresh Data",
      "description": "Re-poll all coordinators.",
      "fields": { "entry_id": { "name": "Config Entry ID", "description": "Target instance." } }
    },
    "fill_tank": {
      "name": "Fill Tank",
      "description": "Record a tank fill event.",
      "fields": {
        "entity_id": { "name": "Tank Entity", "description": "Any tank entity." },
        "fill_type": { "name": "Fill Type", "description": "Type of fill operation." },
        "volume_liters": { "name": "Volume", "description": "Volume in liters." }
      }
    },
    "water_channel": {
      "name": "Water Channel",
      "description": "Record a watering event for a delivery channel.",
      "fields": {
        "entity_id": { "name": "Channel Entity", "description": "Channel mix entity." },
        "volume_liters": { "name": "Volume", "description": "Volume in liters." }
      }
    },
    "confirm_care": {
      "name": "Confirm Care",
      "description": "Confirm a care reminder as completed.",
      "fields": {
        "notification_key": { "name": "Notification Key", "description": "Key of the notification." },
        "action": { "name": "Action", "description": "confirmed or skipped." }
      }
    }
  }
}
```

### 7.2 icons.json

```json
{
  "entity": {
    "sensor": {
      "phase": {
        "default": "mdi:sprout",
        "state": {
          "germination": "mdi:seed-outline",
          "seedling": "mdi:sprout",
          "vegetative": "mdi:leaf",
          "flowering": "mdi:flower",
          "ripening": "mdi:fruit-grapes",
          "harvest": "mdi:content-cut",
          "dormancy": "mdi:snowflake",
          "flushing": "mdi:water",
          "drying": "mdi:weather-windy",
          "curing": "mdi:jar-outline"
        }
      },
      "days_in_phase": { "default": "mdi:calendar-clock" },
      "vpd_target": { "default": "mdi:gauge" },
      "ec_target": { "default": "mdi:flash" },
      "nutrient_plan": { "default": "mdi:clipboard-text" },
      "active_channels": { "default": "mdi:pipe" },
      "next_phase": { "default": "mdi:skip-next" },
      "run_status": { "default": "mdi:play-circle-outline" },
      "plant_count": { "default": "mdi:flower-outline" },
      "active_runs": { "default": "mdi:playlist-play" },
      "active_plants": { "default": "mdi:flower" },
      "tank_info": { "default": "mdi:barrel" },
      "tank_volume": { "default": "mdi:cup-water" },
      "fill_level": { "default": "mdi:waves-arrow-up" },
      "tasks_due_today": { "default": "mdi:clipboard-check-outline" },
      "tasks_overdue": { "default": "mdi:clipboard-alert-outline" },
      "next_watering": { "default": "mdi:watering-can" }
    },
    "binary_sensor": {
      "needs_attention": { "default": "mdi:alert-circle" },
      "sensor_offline": { "default": "mdi:access-point-network-off" },
      "care_overdue": { "default": "mdi:watering-can-outline" }
    },
    "button": {
      "refresh_all": { "default": "mdi:refresh" }
    }
  },
  "services": {
    "refresh_data": { "service": "mdi:refresh" },
    "clear_cache": { "service": "mdi:cached" },
    "fill_tank": { "service": "mdi:water-plus" },
    "water_channel": { "service": "mdi:watering-can" },
    "confirm_care": { "service": "mdi:check-circle" }
  }
}
```

### 7.3 Entity-Category

```python
from homeassistant.const import EntityCategory

# CONFIG — Aendert Verhalten (Refresh-Button)
class KamerplanterRefreshButton(KamerplanterEntity, ButtonEntity):
    _attr_entity_category = EntityCategory.CONFIG

# DIAGNOSTIC — Read-only Diagnose-Info
class SensorOfflineSensor(KamerplanterEntity, BinarySensorEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
```

---

## 8. Config Flow

### 8.1 Pflicht-Flows

| Flow | Zweck | Trigger |
|------|-------|---------|
| `async_step_user` | Ersteinrichtung (URL + Key + Tenant) | User klickt "Integration hinzufuegen" |
| `async_step_reauth` | API-Key erneuern | `ConfigEntryAuthFailed` im Coordinator |
| `async_step_reconfigure` | URL aendern | User klickt "Reconfigure" |
| Options Flow | Polling-Intervalle anpassen | User klickt Zahnrad |

### 8.2 Unique ID auf Config Entry

```python
async def async_step_user(self, user_input=None):
    if user_input is not None:
        # ... Validierung ...
        await self.async_set_unique_id(f"{base_url}_{tenant_slug}")
        self._abort_if_unique_id_configured()
        return self._create_entry(tenant_slug=tenant_slug)
```

### 8.3 Reauth Flow

```python
async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
    return await self.async_step_reauth_confirm()

async def async_step_reauth_confirm(self, user_input=None) -> ConfigFlowResult:
    errors = {}
    if user_input is not None:
        # Validiere neuen API-Key
        try:
            api = KamerplanterApi(base_url=..., session=..., api_key=user_input[CONF_API_KEY])
            await api.async_get_current_user()
        except KamerplanterAuthError:
            errors["base"] = "invalid_auth"
        else:
            return self.async_update_reload_and_abort(
                self._get_reauth_entry(),
                data_updates={CONF_API_KEY: user_input[CONF_API_KEY]},
            )
    return self.async_show_form(
        step_id="reauth_confirm",
        data_schema=vol.Schema({vol.Required(CONF_API_KEY): str}),
        errors=errors,
    )
```

### 8.4 Options Flow mit automatischem Reload

```python
from homeassistant.config_entries import OptionsFlowWithReload

class KamerplanterOptionsFlow(OptionsFlowWithReload):
    async def async_step_init(self, user_input=None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA, self.config_entry.options
            ),
        )
```

---

## 9. Coordinator Pattern

### 9.1 Basis mit _async_setup und always_update

```python
class KamerplanterPlantCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):

    def __init__(self, hass, entry, api) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_plants",
            config_entry=entry,
            update_interval=timedelta(seconds=interval),
            always_update=False,  # ★ Nur Callback wenn Daten sich aendern
        )
        self.api = api

    async def _async_setup(self) -> None:
        """Einmaliges Setup — Stammdaten laden."""
        self._fertilizer_lookup = await self._build_fertilizer_lookup()

    async def _async_update_data(self) -> list[dict[str, Any]]:
        try:
            async with async_timeout.timeout(30):
                return await self._fetch_and_enrich()
        except KamerplanterAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except KamerplanterConnectionError as err:
            raise UpdateFailed(str(err)) from err
```

### 9.2 Regeln

- `always_update=False` — Entities nur updaten wenn Daten sich aendern
- `config_entry=entry` — Pflicht-Parameter fuer Lifecycle-Management
- `_async_setup()` — Stammdaten (Fertilizer-Names, etc.) einmalig laden
- `async_timeout.timeout(30)` — Kein unbegrenztes Warten auf API
- Enrichment-Fehler: Loggen + Ueberspringen, nie gesamten Update abbrechen

---

## 10. API-Client

### 10.1 Struktur

```python
@dataclass
class KamerplanterApi:
    base_url: str
    session: ClientSession
    api_key: str | None = None
    tenant_slug: str | None = None
```

### 10.2 Exception-Hierarchie

| Exception | HTTP | HA-Mapping |
|-----------|------|-----------|
| `KamerplanterAuthError` | 401, 403 | → `ConfigEntryAuthFailed` |
| `KamerplanterConnectionError` | Netzwerk, 5xx | → `UpdateFailed` |

### 10.3 Session-Management

```python
# ★ Immer shared Session verwenden
from homeassistant.helpers.aiohttp_client import async_get_clientsession

session = async_get_clientsession(hass)
api = KamerplanterApi(base_url=url, session=session, api_key=key)
```

---

## 11. Diagnostics

```python
from homeassistant.components.diagnostics import async_redact_data

TO_REDACT = {"api_key", "password", "token", "tenant_slug"}

async def async_get_config_entry_diagnostics(hass, entry):
    return {
        "entry_data": async_redact_data(dict(entry.data), TO_REDACT),
        "coordinator_data": { ... },
    }
```

**Regel:** Immer `async_redact_data` verwenden. Keine manuelle Kuerzung.

---

## 12. manifest.json

```json
{
  "domain": "kamerplanter",
  "name": "Kamerplanter",
  "codeowners": ["@kamerplanter"],
  "config_flow": true,
  "documentation": "https://github.com/kamerplanter/kamerplanter-ha",
  "iot_class": "cloud_polling",
  "issue_tracker": "https://github.com/kamerplanter/kamerplanter-ha/issues",
  "integration_type": "hub",
  "loggers": ["custom_components.kamerplanter"],
  "requirements": [],
  "version": "0.1.0"
}
```

**Pflichtfelder fuer Custom Integration:**
- `integration_type: "hub"` (mehrere Devices/Entities)
- `loggers` (fuer Log-Level-Management)
- `version` (SemVer)

---

## 13. Custom Lovelace Cards

### 13.1 Card-Lifecycle (PFLICHT)

```javascript
class KamerplanterCard extends HTMLElement {
  setConfig(config) { /* throw Error bei ungueltig */ }
  set hass(hass) { /* Update nur bei Entity-Aenderung */ }
  getCardSize() { return 3; }
  getGridOptions() { return { columns: 6, rows: 3, min_columns: 3, min_rows: 2 }; }
  static getConfigElement() { return document.createElement("...editor"); }
  static getStubConfig() { return { entity: "" }; }
  connectedCallback() { this.attachShadow({ mode: "open" }); this._render(); }
}
```

### 13.2 Performance: Entity-Change-Detection

```javascript
set hass(hass) {
  // ★ Nur re-rendern wenn eigene Entities sich geaendert haben
  const changed = this._monitoredEntities.some(
    id => this._hass?.states[id] !== hass.states[id]
  );
  this._hass = hass;
  if (changed || !this._rendered) this._render();
}
```

### 13.3 Registrierung

```javascript
window.customCards = window.customCards || [];
window.customCards.push({
  type: "kamerplanter-plant-card",
  name: "Kamerplanter Plant Card",
  description: "Plant monitoring with phase timeline",
  preview: false,
});
customElements.define("kamerplanter-plant-card", KamerplanterPlantCard);
```

### 13.4 CSS Custom Properties

```css
/* ★ HA-Variablen statt hardcodierte Werte */
.value { color: var(--primary-text-color); }
.label { color: var(--secondary-text-color); }
.icon  { color: var(--state-icon-color); }
.error { color: var(--error-color); font-weight: var(--ha-font-weight-bold); }
.divider { background: var(--divider-color); }
```

---

## 14. Namenskonventionen

### 14.1 Konstanten

| Praefix | Zweck | Beispiel |
|---------|-------|----------|
| `CONF_` | Config-Keys | `CONF_API_KEY` |
| `DEFAULT_` | Default-Werte | `DEFAULT_POLL_PLANTS` |
| `MIN_` | Minimum-Werte | `MIN_POLL_PLANTS` |
| `EVENT_` | HA-Event-Namen | `EVENT_TASK_COMPLETED` |
| `SERVICE_` | Service-Namen | `SERVICE_FILL_TANK` |

### 14.2 Logging

```python
_LOGGER = logging.getLogger(__name__)

# ★ stdlib logging (NICHT structlog)
_LOGGER.debug("Loading plants: %s entries", len(plants))
_LOGGER.info("Tank fill recorded: %s", key)
_LOGGER.exception("Failed to fill tank %s", tank_key)  # Mit Traceback
```

### 14.3 Type Hints

```python
from __future__ import annotations   # In JEDER Datei
from typing import Any, Final
```

---

## 15. Deployment

```bash
# 1. Dateien kopieren
kubectl cp custom_components/kamerplanter/ \
  default/homeassistant-0:/config/custom_components/kamerplanter/

# 2. Bytecode-Cache loeschen (PFLICHT)
kubectl exec homeassistant-0 -n default -- \
  rm -rf /config/custom_components/kamerplanter/__pycache__

# 3. HA-Prozess neustarten (NICHT kubectl delete pod!)
# kill 1 startet nur den Container neu — InitContainers laufen NICHT erneut,
# d.h. die per kubectl cp kopierten Dateien bleiben erhalten.
kubectl exec homeassistant-0 -n default -- kill 1
```

---

## 16. Zusammenfassung der Pruefkette

```
Code-Aenderung
    │
    ├─→ ruff check + format       → Linting + Formatierung
    ├─→ pytest tests/ha-integration/ → Unit-Tests (>95% Coverage)
    ├─→ HACS Validation Action    → Manifest, Struktur
    └─→ kubectl cp + restart      → Manuelles Deployment
```
