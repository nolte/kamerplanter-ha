# Home Assistant Developer Documentation Research

> Quelle: [home-assistant/developers.home-assistant](https://github.com/home-assistant/developers.home-assistant) (master branch)
> Stand: 2026-04-03

---

## 1. Integration Architecture

### 1.1 File Structure

Jede Integration liegt in einem eigenen Verzeichnis unter `custom_components/<domain>/`. Pflichtdateien:

| Datei | Zweck |
|-------|-------|
| `manifest.json` | Metadaten, Abhängigkeiten, IoT-Klasse |
| `__init__.py` | Entry-Point, `async_setup_entry` / `async_unload_entry` |

Empfohlene Dateien:

| Datei | Zweck |
|-------|-------|
| `config_flow.py` | Config Flow Handler |
| `coordinator.py` | DataUpdateCoordinator (MUSS dort liegen, keine Ausnahmen) |
| `entity.py` | Base Entity Klasse (CoordinatorEntity-Ableitung) |
| `sensor.py`, `binary_sensor.py`, `switch.py`, ... | Entity-Plattformen |
| `services.yaml` | Service-Action-Definitionen |
| `strings.json` | Übersetzungsstrings |
| `icons.json` | Icon-Mapping pro Entity/Service |
| `const.py` | Konstanten |
| `diagnostics.py` | Diagnostik-Export |
| `repairs.py` | Repair Flows |

### 1.2 Config Flow (config_flow.py)

**Voraussetzung:** `"config_flow": true` in `manifest.json`.

```python
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult

class ExampleConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Example integration."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            else:
                await self.async_set_unique_id(info["unique_id"])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=info["title"], data=user_input
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("host"): str,
                vol.Required("api_key"): str,
            }),
            errors=errors,
        )
```

**Reservierte Step-IDs:**
- `user` — Manueller Setup
- `reauth` — Re-Authentifizierung bei Token-Ablauf
- `reconfigure` — Konfigurationsänderung (NICHT für Auth-Probleme)
- `discovery`, `zeroconf`, `ssdp`, `mqtt`, `dhcp`, `usb`, `homekit`, `bluetooth` — Discovery

**Unique ID Best Practices:**
- Muss stabil und innerhalb der Domain eindeutig sein
- Quellen: Seriennummern, MAC-Adressen, Device-IDs
- `await self.async_set_unique_id(uid)` gefolgt von `self._abort_if_unique_id_configured()`
- Discovery-Steps MÜSSEN eine Unique ID setzen

**Reauth Flow:**

```python
async def async_step_reauth(
    self, entry_data: Mapping[str, Any]
) -> ConfigFlowResult:
    """Handle reauthentication."""
    return await self.async_step_reauth_confirm()

async def async_step_reauth_confirm(
    self, user_input: dict[str, Any] | None = None
) -> ConfigFlowResult:
    if user_input is None:
        return self.async_show_form(step_id="reauth_confirm")
    # Validate new credentials, then:
    self._abort_if_unique_id_mismatch()
    return self.async_update_reload_and_abort(
        self._get_reauth_entry(), data_updates=new_data
    )
```

**Reconfigure Flow:**

```python
async def async_step_reconfigure(
    self, user_input: dict[str, Any] | None = None
) -> ConfigFlowResult:
    if user_input is not None:
        return self.async_update_reload_and_abort(
            self._get_reconfigure_entry(), data_updates=user_input
        )
    return self.async_show_form(
        step_id="reconfigure",
        data_schema=vol.Schema({vol.Required("host"): str}),
    )
```

### 1.3 DataUpdateCoordinator Pattern

**Datei: `coordinator.py`** (verpflichtende Konvention).

```python
from datetime import timedelta
import async_timeout
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.exceptions import ConfigEntryAuthFailed

class KamerplanterCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for Kamerplanter API data."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        client: KamerplanterClient,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=timedelta(seconds=30),
            always_update=False,  # Vermeidet unnötige Callbacks
        )
        self.client = client

    async def _async_setup(self) -> None:
        """Einmaliges Setup (seit HA 2024.8)."""
        self.initial_data = await self.client.get_metadata()

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            async with async_timeout.timeout(10):
                return await self.client.fetch_all_data()
        except AuthError as err:
            raise ConfigEntryAuthFailed from err
        except ApiError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
```

**Setup in `__init__.py`:**

```python
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    client = KamerplanterClient(
        entry.data["host"],
        entry.data["api_key"],
        async_get_clientsession(hass),
    )
    coordinator = KamerplanterCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(
        entry, ["sensor", "binary_sensor", "switch"]
    )
    return True
```

**Wichtige Details:**
- `always_update=False` — Nur Callback wenn Daten sich geaendert haben (`__eq__`)
- `_async_setup()` — Einmaliges Init-Loading, gleiche Fehlerbehandlung wie `_async_update_data`
- `async_config_entry_first_refresh()` — Wirft `ConfigEntryNotReady` bei Fehler
- `ConfigEntryAuthFailed` — Triggert automatisch Reauth-Flow
- `UpdateFailed` — Markiert Entities als unavailable, HA retried automatisch
- Seit 2025.11: `UpdateFailed` unterstuetzt `retry_after` Parameter fuer verzögerten Retry
- Seit 2025.10: Coordinator kann Updates retriggern waehrend laufendem Update

### 1.4 Entity Platform Patterns

#### Base Entity (entity.py)

```python
from homeassistant.helpers.update_coordinator import CoordinatorEntity

class KamerplanterEntity(CoordinatorEntity[KamerplanterCoordinator]):
    """Base entity for Kamerplanter."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: KamerplanterCoordinator,
        description: EntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name="Kamerplanter",
            manufacturer="Kamerplanter",
            model="Plant Management System",
            sw_version=coordinator.data.get("version"),
        )
```

**CoordinatorEntity bietet automatisch:**
- `should_poll = False`
- `available` basierend auf Coordinator-Erfolg
- `async_update` delegiert an Coordinator
- `async_added_to_hass` registriert Listener

#### Sensor Entity

```python
from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
    SensorStateClass,
)

SENSOR_DESCRIPTIONS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        translation_key="temperature",
    ),
    SensorEntityDescription(
        key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        translation_key="humidity",
    ),
    SensorEntityDescription(
        key="phase",
        translation_key="phase",
        # Kein device_class — Custom States via strings.json
    ),
)

class KamerplanterSensor(KamerplanterEntity, SensorEntity):
    entity_description: SensorEntityDescription

    @property
    def native_value(self) -> StateType:
        return self.coordinator.data.get(self.entity_description.key)

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        KamerplanterSensor(coordinator, desc) for desc in SENSOR_DESCRIPTIONS
    )
```

**Sensor state_class Optionen:**
- `MEASUREMENT` — Momentanwert (Temperatur, Feuchte, Leistung)
- `TOTAL` — Kumulativ, kann steigen und fallen
- `TOTAL_INCREASING` — Monoton steigend, Abfall = Meter-Reset
- `MEASUREMENT_ANGLE` — Winkel in Grad

#### Switch Entity

```python
class KamerplanterSwitch(KamerplanterEntity, SwitchEntity):
    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.get(self.entity_description.key)

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.client.set_state(self.entity_description.key, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.client.set_state(self.entity_description.key, False)
        await self.coordinator.async_request_refresh()
```

#### Button Entity (Stateless Actions)

```python
class KamerplanterButton(KamerplanterEntity, ButtonEntity):
    async def async_press(self) -> None:
        await self.coordinator.client.trigger_action(self.entity_description.key)
        await self.coordinator.async_request_refresh()
```

#### Select Entity

```python
class KamerplanterSelect(KamerplanterEntity, SelectEntity):
    @property
    def current_option(self) -> str | None:
        return self.coordinator.data.get(self.entity_description.key)

    @property
    def options(self) -> list[str]:
        return ["option_a", "option_b", "option_c"]

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.client.set_option(self.entity_description.key, option)
        await self.coordinator.async_request_refresh()
```

#### Number Entity

```python
class KamerplanterNumber(KamerplanterEntity, NumberEntity):
    _attr_native_min_value = 0.0
    _attr_native_max_value = 100.0
    _attr_native_step = 0.1
    _attr_mode = NumberMode.SLIDER

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.get(self.entity_description.key)

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.client.set_value(self.entity_description.key, value)
        await self.coordinator.async_request_refresh()
```

#### Calendar Entity

```python
class KamerplanterCalendar(KamerplanterEntity, CalendarEntity):
    @property
    def event(self) -> CalendarEvent | None:
        """Return next upcoming event."""
        return self.coordinator.data.get("next_event")

    async def async_get_events(
        self, hass, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        return await self.coordinator.client.get_events(start_date, end_date)
```

Unterstuetzt `CalendarEntityFeature.CREATE_EVENT`, `DELETE_EVENT`, `UPDATE_EVENT`.

#### Todo Entity

```python
class KamerplanterTodo(KamerplanterEntity, TodoListEntity):
    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
    )

    @property
    def todo_items(self) -> list[TodoItem] | None:
        return self.coordinator.data.get("tasks")

    async def async_create_todo_item(self, item: TodoItem) -> None:
        await self.coordinator.client.create_task(item.summary, item.due)
        await self.coordinator.async_request_refresh()
```

### 1.5 Entity Naming Conventions

**Pflicht:** `_attr_has_entity_name = True`

**Namensregeln:**
- Entity-Name beschreibt NUR den Datenpunkt, NICHT das Geraet
- `friendly_name` wird automatisch zusammengesetzt: `{device_name} {entity_name}`
- Haupt-Feature eines Geraets: `_attr_name = None` → `entity_id = <domain>.<device_name>`
- Sekundaer-Features: Name oder `translation_key` setzen

**Beispiel:**
- Device: "Growbox Sensor" → Haupt-Temperatur: `sensor.growbox_sensor` (name=None)
- Device: "Growbox Sensor" → Feuchte: `sensor.growbox_sensor_humidity`

### 1.6 unique_id Patterns

- MUSS innerhalb einer Plattform (z.B. `sensor.kamerplanter`) eindeutig sein
- DARF NICHT vom Benutzer konfigurierbar sein
- Format: `{config_entry_id}_{entity_key}` oder `{device_serial}_{entity_key}`
- Bei Aenderung verliert der User alle Customizations (Name, Area, etc.)

### 1.7 DeviceInfo

```python
from homeassistant.helpers.device_registry import DeviceInfo

DeviceInfo(
    identifiers={(DOMAIN, "unique_device_id")},  # PFLICHT
    connections={("mac", "AA:BB:CC:DD:EE:FF")},   # Optional, alternative ID
    name="My Device",
    manufacturer="Kamerplanter",
    model="Sensor Hub v2",
    sw_version="1.2.3",
    hw_version="rev-b",
    via_device=(DOMAIN, "parent_hub_id"),  # Parent-Device fuer Topologie
)
```

- `identifiers`: Set von (DOMAIN, id) Tupeln — primaere Identifikation
- `connections`: Set von (type, id) — z.B. MAC-Adresse
- `via_device`: Verknuepfung zu Eltern-Device (Hub → Sensor)
- Geraete koennen per `async_remove_config_entry_device` entfernbar gemacht werden

### 1.8 Entity Categories

```python
from homeassistant.const import EntityCategory

# CONFIG — Aendert Geraete-Konfiguration (z.B. Hintergrundbeleuchtung-Switch)
_attr_entity_category = EntityCategory.CONFIG

# DIAGNOSTIC — Zeigt Diagnose-Info, read-only (z.B. RSSI, MAC, Firmware)
_attr_entity_category = EntityCategory.DIAGNOSTIC
```

### 1.9 Service Definitions (services.yaml)

Services werden in `async_setup` registriert (NICHT `async_setup_entry`):

```python
async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    async def handle_water_plant(call: ServiceCall) -> None:
        plant_id = call.data["plant_id"]
        amount_ml = call.data.get("amount_ml", 250)
        # ...

    hass.services.async_register(
        DOMAIN, "water_plant", handle_water_plant
    )
```

**services.yaml:**

```yaml
water_plant:
  target:
    entity:
      domain: sensor
  fields:
    plant_id:
      required: true
      example: "plant_001"
      selector:
        text:
    amount_ml:
      required: false
      default: 250
      selector:
        number:
          min: 50
          max: 5000
          step: 50
          unit_of_measurement: "ml"
```

**Response-faehige Services:**

```python
from homeassistant.core import SupportsResponse

hass.services.async_register(
    DOMAIN,
    "get_plant_status",
    handle_get_status,
    supports_response=SupportsResponse.ONLY,
)
```

**icons.json fuer Services:**
```json
{
  "services": {
    "water_plant": { "service": "mdi:watering-can" },
    "get_plant_status": { "service": "mdi:flower-outline" }
  }
}
```

### 1.10 String Translations (strings.json)

```json
{
  "config": {
    "flow_title": "Kamerplanter ({host})",
    "step": {
      "user": {
        "title": "Connect to Kamerplanter",
        "description": "Enter your Kamerplanter instance details.",
        "data": {
          "host": "Host",
          "api_key": "API Key"
        }
      },
      "reauth_confirm": {
        "title": "Re-authenticate",
        "description": "Your API key has expired."
      }
    },
    "error": {
      "cannot_connect": "Cannot connect to Kamerplanter",
      "invalid_auth": "Invalid API key"
    },
    "abort": {
      "already_configured": "This instance is already configured",
      "reauth_successful": "Re-authentication successful"
    }
  },
  "options": {
    "step": {
      "init": {
        "data": {
          "scan_interval": "Update interval (seconds)"
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
          "harvest": "Harvest"
        }
      },
      "temperature": {
        "name": "Temperature"
      }
    }
  },
  "services": {
    "water_plant": {
      "name": "Water plant",
      "description": "Trigger watering for a plant.",
      "fields": {
        "plant_id": {
          "name": "Plant ID",
          "description": "The plant to water."
        },
        "amount_ml": {
          "name": "Amount",
          "description": "Water amount in milliliters."
        }
      }
    }
  },
  "exceptions": {
    "connection_failed": {
      "message": "Could not connect to {host}"
    }
  }
}
```

**icons.json:**

```json
{
  "entity": {
    "sensor": {
      "phase": {
        "default": "mdi:sprout",
        "state": {
          "germination": "mdi:seed",
          "seedling": "mdi:sprout",
          "vegetative": "mdi:leaf",
          "flowering": "mdi:flower",
          "harvest": "mdi:fruit-cherries"
        }
      }
    }
  },
  "services": {
    "water_plant": { "service": "mdi:watering-can" }
  }
}
```

---

## 2. Authentication & API Communication

### 2.1 aiohttp Session Management

**Shared Session verwenden (Regelfall):**

```python
from homeassistant.helpers.aiohttp_client import async_get_clientsession

async def async_setup_entry(hass, entry):
    session = async_get_clientsession(hass)
    client = MyApiClient(entry.data["host"], entry.data["token"], session)
```

**Eigene Session (nur bei Cookies o.ae.):**

```python
from homeassistant.helpers.aiohttp_client import async_create_clientsession

session = async_create_clientsession(hass)
```

### 2.2 Auth Library Pattern (PyPI-Bibliothek)

Alle API-spezifische Logik MUSS in einer separaten PyPI-Bibliothek liegen, nicht in der Integration selbst.

**Async Auth mit Token:**

```python
from aiohttp import ClientSession

class KamerplanterAuth:
    def __init__(self, websession: ClientSession, host: str, api_key: str):
        self.websession = websession
        self.host = host
        self.api_key = api_key

    async def request(self, method: str, path: str, **kwargs):
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.api_key}"
        return await self.websession.request(
            method, f"{self.host}/api/v1/{path}", headers=headers, **kwargs
        )
```

**OAuth2 Token Refresh Pattern:**

```python
from abc import ABC, abstractmethod

class AbstractAuth(ABC):
    def __init__(self, websession: ClientSession, host: str):
        self.websession = websession
        self.host = host

    @abstractmethod
    async def async_get_access_token(self) -> str:
        """Return a valid access token."""

    async def request(self, method: str, url: str, **kwargs):
        headers = kwargs.pop("headers", {})
        access_token = await self.async_get_access_token()
        headers["Authorization"] = f"Bearer {access_token}"
        return await self.websession.request(
            method, f"{self.host}/{url}", headers=headers, **kwargs
        )
```

### 2.3 Error Handling & Retry

| Exception | Wann | Effekt |
|-----------|------|--------|
| `ConfigEntryNotReady` | `async_setup_entry` | Automatischer Retry mit steigendem Interval |
| `ConfigEntryAuthFailed` | `async_setup_entry` oder Coordinator | Triggert Reauth-Flow |
| `UpdateFailed` | Coordinator `_async_update_data` | Entities werden unavailable, Retry |
| `PlatformNotReady` | `async_setup_platform` (Legacy) | Plattform-Retry |

**Wichtig:**
- NICHT in `async_setup_entry` einer Plattform `ConfigEntryNotReady` raisen — zu spaet
- Fehlermeldungen als ersten Parameter uebergeben
- Kein eigenes Logging auf Error-Level — Framework loggt automatisch
- `async_config_entry_first_refresh()` wirft automatisch `ConfigEntryNotReady` bei Fehler
- Seit 2025.11: `UpdateFailed(message, retry_after=60)` fuer verzögerten Retry

---

## 3. Quality Requirements

### 3.1 Quality Scale Tiers

| Tier | Anforderungen |
|------|---------------|
| **Bronze** | UI-Config-Flow, grundlegende Code-Standards, Config-Flow-Tests, Basis-Doku |
| **Silver** | + Aktive Code Owners, Auto-Recovery bei Verbindungsfehlern, Reauth bei Auth-Fehlern, Troubleshooting-Doku |
| **Gold** | + Auto-Discovery, Uebersetzungen, ausfuehrliche Doku fuer Non-Tech-User, volle Testabdeckung |
| **Platinum** | + Volle Type Annotations, komplett async, optimierte Netzwerk/CPU-Nutzung |

### 3.2 Test-Anforderungen

**Pflicht:** Vollstaendige Testabdeckung von `config_flow.py` fuer Core-Integrations.

```bash
# Tests ausfuehren
pytest tests/components/<domain>/ --cov=homeassistant.components.<domain> --cov-report term-missing -vv

# Snapshot-Tests erstellen
pytest tests/components/<domain>/test_sensor.py --snapshot-update
```

**Test-Patterns:**
- Setup via `async_setup_component` oder `hass.config_entries.async_setup`
- State pruefen via `hass.states`
- Services via `hass.services` aufrufen
- `MockConfigEntry` fuer Config Entries
- Snapshot-Tests (Syrupy) ergaenzend, nicht ersetzend
- Registries (`DeviceEntry`, Entity Registry, Config Entries) fuer Verifikation

### 3.3 Code Quality Standards

- **PEP 8** (Ruff) und **PEP 257** (Docstrings)
- F-Strings fuer allgemeinen Code, %-Formatierung fuer Logging
- Vollstaendige Type Annotations
- Kommentare als vollstaendige Saetze mit Punkt
- Konstanten, Listen, Dicts alphabetisch sortiert
- Logging: Kein Duplizieren von Plattform/Component-Namen, keine Punkte am Ende, NIE sensible Daten
- `_LOGGER.info` nur fuer User-facing Messages, `_LOGGER.debug` fuer Entwickler

### 3.4 Manifest Requirements (manifest.json)

```json
{
  "domain": "kamerplanter",
  "name": "Kamerplanter",
  "version": "1.0.0",
  "documentation": "https://github.com/user/kamerplanter",
  "issue_tracker": "https://github.com/user/kamerplanter/issues",
  "codeowners": ["@username"],
  "config_flow": true,
  "iot_class": "local_polling",
  "integration_type": "hub",
  "requirements": ["kamerplanter-api==1.0.0"],
  "dependencies": [],
  "loggers": ["kamerplanter"]
}
```

**Pflichtfelder:** `domain`, `name`, `documentation`, `codeowners`, `integration_type`, `iot_class`

**Integration Types:** `hub` (mehrere Geraete), `device` (einzelnes Geraet), `service`, `helper`, `entity`, `hardware`, `virtual`

**IoT Classes:** `local_polling`, `local_push`, `cloud_polling`, `cloud_push`, `assumed_state`, `calculated`

**Version:** Pflicht fuer Custom Integrations (CalVer oder SemVer). Entfaellt fuer Core.

### 3.5 HACS Compatibility

**Repository-Anforderungen:**
- Öffentliches GitHub-Repository
- Repository-Beschreibung (kurz)
- Topics gesetzt (Suchbarkeit)
- README mit Nutzungsanleitung
- Brand-Assets: `brand/icon.png` (Pflicht), optional `brand/logo.png`

**Dateistruktur:**
```
repository-root/
├── custom_components/
│   └── kamerplanter/
│       ├── __init__.py
│       ├── manifest.json
│       ├── config_flow.py
│       ├── coordinator.py
│       ├── entity.py
│       ├── sensor.py
│       ├── ...
│       └── strings.json
├── hacs.json
└── README.md
```

**hacs.json (Pflicht, Repository-Root):**
```json
{
  "name": "Kamerplanter",
  "render_readme": true
}
```

Optionale Felder: `content_in_root` (bool), `zip_release` (bool), `filename` (string), `hide_default_branch` (bool).

**Releases:** Empfohlen aber nicht Pflicht. HACS zeigt die 5 neuesten Releases + Default-Branch.

### 3.6 Was Integrations ablehnen laesst

- Grosse, ungeteilte Code-Dumps
- Mehr als eine Plattform pro PR
- Unnoetige Features ueber Minimum hinaus
- Direkte API-Calls statt PyPI-Bibliothek
- Fehlende Config-Validierung (Voluptuous)
- Ungepinnte Requirements-Versionen
- Mischen von Refactoring und neuen Features
- PRs die von nicht-gemergter Arbeit abhaengen
- Sensible Daten in Logs

---

## 4. Advanced Patterns

### 4.1 Diagnostics (diagnostics.py)

```python
from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

TO_REDACT = {"api_key", "password", "token", "location"}

async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    return {
        "entry_data": async_redact_data(dict(entry.data), TO_REDACT),
        "coordinator_data": coordinator.data,
    }

async def async_get_device_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry, device: DeviceEntry
) -> dict[str, Any]:
    """Return diagnostics for a device."""
    # Device-spezifische Diagnostik
    return {"device": async_redact_data(device_data, TO_REDACT)}
```

**Kritisch:** Keine sensiblen Daten (Passwoerter, API-Keys, Tokens, Standortdaten) exponieren.

### 4.2 Repair Flows (repairs.py)

```python
from homeassistant.components.repairs import RepairsFlow
from homeassistant.helpers import issue_registry as ir

# Issue erstellen:
ir.async_create_issue(
    hass,
    DOMAIN,
    "firmware_update_required",
    is_fixable=True,
    is_persistent=False,
    severity=ir.IssueSeverity.WARNING,
    translation_key="firmware_update_required",
)

# Repair Flow:
class FirmwareRepairFlow(RepairsFlow):
    async def async_step_init(self, user_input=None):
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input=None):
        if user_input is not None:
            await trigger_firmware_update()
            return self.async_create_entry(title="", data={})
        return self.async_show_form(step_id="confirm")

async def async_create_fix_flow(hass, issue_id, data):
    return FirmwareRepairFlow()
```

**Severity-Level:** `ERROR` (sofort), `WARNING` (zukuenftig), `CRITICAL` (Notfall)

### 4.3 Config Entry Migration

```python
# config_flow.py
class KamerplanterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2
    MINOR_VERSION = 3

# __init__.py
async def async_migrate_entry(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> bool:
    _LOGGER.debug(
        "Migrating from version %s.%s",
        config_entry.version,
        config_entry.minor_version,
    )

    if config_entry.version > 2:
        return False  # Downgrade nicht unterstuetzt

    if config_entry.version == 1:
        new_data = {**config_entry.data}
        if config_entry.minor_version < 2:
            new_data["scan_interval"] = 30  # Neues Feld
        hass.config_entries.async_update_entry(
            config_entry, data=new_data, version=2, minor_version=1
        )

    if config_entry.version == 2:
        new_data = {**config_entry.data}
        if config_entry.minor_version < 3:
            new_data["feature_flag"] = True
        hass.config_entries.async_update_entry(
            config_entry, data=new_data, minor_version=3
        )

    return True
```

**Regeln:**
- MINOR_VERSION-Differenz bei gleichem VERSION: Setup laeuft auch OHNE Migration
- VERSION-Differenz: Migration MUSS implementiert sein
- `ConfigEntry` NIEMALS direkt mutieren, immer `async_update_entry` verwenden

### 4.4 Options Flow

```python
from homeassistant.config_entries import OptionsFlow, OptionsFlowWithReload

class KamerplanterOptionsFlow(OptionsFlowWithReload):
    """Options flow with automatic reload."""

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema({
                    vol.Optional("scan_interval", default=30): int,
                    vol.Optional("show_inactive", default=False): bool,
                }),
                self.config_entry.options,
            ),
        )
```

- `OptionsFlowWithReload` — Automatischer Reload nach Aenderung (seit 2024.11)
- `OptionsFlow` — Manuelles Listener-Setup noetig

### 4.5 Subentries

Config Entries koennen logisch in Subentries aufgeteilt werden. Beispiel: Haupt-Entry speichert Auth-Daten, jeder Standort/jede Pflanze ist ein Subentry. Subentries unterstuetzen optional Reconfigure-Steps.

### 4.6 Entity Availability

```python
class KamerplanterSensor(KamerplanterEntity, SensorEntity):
    @property
    def available(self) -> bool:
        """Check if entity data exists in coordinator."""
        return (
            super().available  # Coordinator-Basis-Check
            and self.entity_description.key in self.coordinator.data
        )
```

**Regeln:**
- Daten nicht abrufbar → Entity `unavailable`
- Daten abrufbar aber Wert fehlt temporaer → State `unknown` (nicht unavailable)

---

## 5. Custom Lovelace Cards

### 5.1 Card Lifecycle

Custom Cards sind Web Components (HTMLElement):

```javascript
class KamerplanterPlantCard extends HTMLElement {
  // 1. Konfiguration empfangen und validieren
  setConfig(config) {
    if (!config.entity) {
      throw new Error("You need to define an entity");
    }
    this._config = config;
    this._render();
  }

  // 2. Hass-Objekt empfangen (bei jedem State-Update)
  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  // 3. Kartenhoehe fuer Masonry-Layout (1 unit = 50px)
  getCardSize() {
    return 4;
  }

  // 4. Grid-Optionen fuer Sections-View (12-Spalten-Grid)
  getGridOptions() {
    return {
      rows: 3,
      columns: 6,
      min_rows: 2,
      max_rows: 6,
    };
  }

  // 5. DOM-Lifecycle
  connectedCallback() {
    this._render();
  }

  disconnectedCallback() {
    // Subscriptions aufraemen
  }

  _render() {
    if (!this._config || !this._hass) return;
    // Shadow DOM oder innerHTML
  }
}
```

### 5.2 Card Editor

```javascript
class KamerplanterPlantCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = config;
  }

  set hass(hass) {
    this._hass = hass;
  }

  // Aenderungen als Event dispatchen
  _valueChanged(ev) {
    const event = new CustomEvent("config-changed", {
      detail: { config: this._config },
      bubbles: true,
      composed: true,
    });
    this.dispatchEvent(event);
  }
}

customElements.define("kamerplanter-plant-card-editor", KamerplanterPlantCardEditor);
```

**Alternativ: Form-basierter Editor (einfacher):**

```javascript
class KamerplanterPlantCard extends HTMLElement {
  // Statt getConfigElement:
  static getConfigForm() {
    return {
      schema: [
        { name: "entity", required: true, selector: { entity: { domain: "sensor" } } },
        { name: "name", selector: { text: {} } },
        { name: "show_phase", selector: { boolean: {} } },
      ],
      assertConfig: (config) => {
        if (!config.entity) throw new Error("Entity required");
      },
    };
  }
}
```

### 5.3 Card Registration

```javascript
// Card registrieren
customElements.define("kamerplanter-plant-card", KamerplanterPlantCard);

// Im Card Picker anzeigen
window.customCards = window.customCards || [];
window.customCards.push({
  type: "kamerplanter-plant-card",
  name: "Kamerplanter Plant Card",
  preview: false,
  description: "Displays plant status from Kamerplanter",
  documentationURL: "https://github.com/user/kamerplanter",
});
```

### 5.4 Card als Resource einbinden

**Option A: www-Verzeichnis (manuell):**
```yaml
resources:
  - url: /local/kamerplanter-plant-card.js
    type: module
```

**Option B: Aus Custom Integration heraus (automatisch):**
Die Integration kann die JS-Datei aus ihrem `www/`-Unterverzeichnis automatisch als Resource registrieren via `hass.http.register_static_path()` und Frontend-Event.

### 5.5 Grid-Optionen fuer Sections View

```javascript
getGridOptions() {
  return {
    rows: 3,        // Default-Hoehe
    columns: 6,     // Default-Breite (max 12)
    min_rows: 2,    // Minimum
    max_rows: 6,    // Maximum
    min_columns: 3,
    max_columns: 12,
  };
}
```

Zelle: ca. 30px breit x 56px hoch, 8px Abstand.

---

## Zusammenfassung der wichtigsten Best Practices

1. **Coordinator in `coordinator.py`**, Base Entity in `entity.py` — keine Ausnahmen
2. **`has_entity_name = True`** ist Pflicht fuer moderne Integrations
3. **`always_update=False`** am Coordinator wenn Daten `__eq__` unterstuetzen
4. **`_async_setup()`** fuer einmaliges Init statt Checks in `_async_update_data`
5. **Shared aiohttp Session** via `async_get_clientsession(hass)`
6. **API-Code in separater PyPI-Bibliothek**, nicht in der Integration
7. **`ConfigEntryAuthFailed`** fuer Auth-Fehler (triggert Reauth), **`UpdateFailed`** fuer transiente Fehler
8. **Config Entry NIEMALS direkt mutieren** — immer `async_update_entry`
9. **Diagnostics immer mit `async_redact_data`** fuer sensible Daten
10. **services.yaml mit Selectors** fuer UI-Integration
11. **strings.json fuer alle User-facing Strings** inkl. Entity-States
12. **icons.json** statt `icon`-Property (bevorzugt)
13. **Volle Config-Flow-Tests** sind Pflicht

---

## Quellen

- [Config Flow Handler](https://developers.home-assistant.io/docs/config_entries_config_flow_handler/)
- [Fetching Data / DataUpdateCoordinator](https://developers.home-assistant.io/docs/integration_fetching_data/)
- [Entity Architecture](https://developers.home-assistant.io/docs/core/entity/)
- [Device Registry](https://developers.home-assistant.io/docs/device_registry_index/)
- [Internationalization](https://developers.home-assistant.io/docs/internationalization/)
- [Integration Manifest](https://developers.home-assistant.io/docs/creating_integration_manifest/)
- [Integration File Structure](https://developers.home-assistant.io/docs/creating_integration_file_structure/)
- [Services / Actions](https://developers.home-assistant.io/docs/dev_101_services/)
- [Options Flow](https://developers.home-assistant.io/docs/config_entries_options_flow_handler/)
- [Config Entries Lifecycle](https://developers.home-assistant.io/docs/config_entries_index/)
- [Setup Failures](https://developers.home-assistant.io/docs/integration_setup_failures/)
- [Development Guidelines](https://developers.home-assistant.io/docs/development_guidelines/)
- [Component Code Review](https://developers.home-assistant.io/docs/creating_component_code_review/)
- [Platform Code Review](https://developers.home-assistant.io/docs/creating_platform_code_review/)
- [Testing](https://developers.home-assistant.io/docs/development_testing/)
- [Quality Scale](https://developers.home-assistant.io/docs/core/integration-quality-scale/)
- [Diagnostics](https://developers.home-assistant.io/docs/core/integration_diagnostics/)
- [Repairs](https://developers.home-assistant.io/docs/core/platform/repairs/)
- [Custom Lovelace Cards](https://developers.home-assistant.io/docs/frontend/custom-ui/custom-card/)
- [Websession Injection](https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/inject-websession/)
- [Auth Library Pattern](https://developers.home-assistant.io/docs/api_lib_auth/)
- [Common Modules Rule](https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/common-modules/)
- [Coordinator async_setup (2024.8)](https://developers.home-assistant.io/blog/2024/08/05/coordinator_async_setup/)
- [Coordinator Retry After (2025.11)](https://developers.home-assistant.io/blog/2025/11/17/retry-after-update-failed/)
- [HACS General Requirements](https://www.hacs.xyz/docs/publish/start/)
- [HACS Integration Requirements](https://www.hacs.xyz/docs/publish/integration/)
