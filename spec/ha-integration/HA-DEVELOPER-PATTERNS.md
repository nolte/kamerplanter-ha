# Home Assistant Developer Patterns Reference

> Extracted from official HA developer docs (developers.home-assistant.io), April 2025.
> This document contains EXACT code patterns for implementing custom integrations.

---

## 1. Entity Naming & unique_id

### 1.1 `has_entity_name = True`

When `has_entity_name = True`, the entity name represents **only the data point**, not the device. HA constructs the friendly name automatically:

```
Entity NOT in device:     friendly_name = entity.name
Entity in device, name:   friendly_name = "{device.name} {entity.name}"
Entity in device, None:   friendly_name = "{device.name}"
```

Entity ID generation follows the same logic:

```
No device:                entity_id = binary_sensor.everyone_is_home
In device with name:      entity_id = sensor.nightlight_battery
In device, name is None:  entity_id = light.nightlight
```

**Main feature entity** (name = None, becomes the device name):

```python
from homeassistant.components.switch import SwitchEntity

class MySwitch(SwitchEntity):
    _attr_has_entity_name = True
    _attr_name = None  # entity gets device name directly
```

**Secondary feature entity** (has its own name):

```python
class MyBatterySensor(SensorEntity):
    _attr_has_entity_name = True

    @property
    def translation_key(self):
        return "battery_level"
```

**Rules:**
- Main device features SHOULD have `name` return `None`
- All other entities MUST have descriptive names starting with capital letters
- Entity names MUST NOT include the device type or device name (HA prepends it)

### 1.2 `translation_key` Pattern

Entity code:

```python
class MySwitch(SwitchEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "power_control"
```

`strings.json` structure:

```json
{
  "entity": {
    "switch": {
      "power_control": {
        "name": "Power Control",
        "state": {
          "on": "Active",
          "off": "Inactive"
        }
      }
    }
  }
}
```

The key hierarchy is: `entity.<platform>.<translation_key>.name`.

### 1.3 `unique_id` Requirements

**Rules:**
- MUST be unique within a platform (e.g., all `sensor.*` entities)
- MUST NOT be user-configurable or changeable
- REQUIRED when registering entities with devices
- Enables entity registry functionality (renaming, disabling, area assignment)

**Recommended format:**

```python
self._attr_unique_id = f"{device.serial}_{entity_description.key}"
```

**Anti-patterns:**
- Using entity_id as unique_id (entity_id can be renamed)
- Using names or user-configurable values
- Changing unique_id format between versions (breaks entity registry)

---

## 2. Entity Categories

```python
from homeassistant.const import EntityCategory
```

### `EntityCategory.CONFIG`

For entities that **allow changing device configuration**. Examples:
- A switch controlling background illumination
- A number entity setting polling interval
- A select entity choosing operating mode

```python
class BacklightSwitch(SwitchEntity):
    _attr_entity_category = EntityCategory.CONFIG
```

### `EntityCategory.DIAGNOSTIC`

For entities **exposing configuration or diagnostics without modification capability**. Examples:
- RSSI signal strength sensor
- MAC address sensor
- Firmware version sensor
- Identification/locate buttons

```python
class RssiSensor(SensorEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
```

### Other Entity Properties

| Property | Default | Purpose |
|----------|---------|---------|
| `entity_registry_enabled_default` | `True` | Set `False` for rarely-used or fast-changing diagnostic entities |
| `entity_registry_visible_default` | `True` | Controls initial visibility in entity registry |
| `device_class` | `None` | Domain-specific classification (e.g., `SensorDeviceClass.TEMPERATURE`) |
| `supported_features` | `None` | Bit flags for supported capabilities |
| `available` | `True` | `False` when HA cannot read state or control device |
| `assumed_state` | `False` | `True` when state is assumption-based (shows toggle instead of switch) |
| `attribution` | `None` | Required branding text from API providers |
| `force_update` | `False` | Write each update to state machine even if unchanged. Use with caution. |

---

## 3. DeviceInfo Patterns

### 3.1 TypedDict Definition (all fields optional)

```python
class DeviceInfo(TypedDict, total=False):
    configuration_url: str | URL | None
    connections: set[tuple[str, str]]
    identifiers: set[tuple[str, str]]
    manufacturer: str | None
    model: str | None
    model_id: str | None
    name: str | None
    serial_number: str | None
    suggested_area: str | None
    sw_version: str | None
    hw_version: str | None
    via_device: tuple[str, str]
    translation_key: str | None
    translation_placeholders: Mapping[str, str] | None
    entry_type: DeviceEntryType | None
    default_manufacturer: str
    default_model: str
    default_name: str
```

**Important:** `total=False` means ALL fields are optional at the type level, but in practice you MUST provide at least `identifiers` or `connections`.

### 3.2 `identifiers` vs `connections`

**identifiers** -- `set[tuple[str, str]]` with `(DOMAIN, unique_identifier)`:

```python
identifiers={(DOMAIN, "plant_abc123")}
```

- Identifies the device in the "outside world" (serial numbers, API IDs)
- Each item in the set uniquely defines a device entry
- Another device CANNOT have the same identifier

**connections** -- `set[tuple[str, str]]` with `(connection_type, value)`:

```python
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC

connections={(CONNECTION_NETWORK_MAC, "AA:BB:CC:DD:EE:FF")}
```

- Uses predefined connection types (`CONNECTION_NETWORK_MAC`, etc.)
- Matching logic: HA first tries to match by identifiers, then connections

### 3.3 Entity-based Device Registration

```python
class HueLight(LightEntity):
    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(hue.DOMAIN, self.unique_id)},
            name=self.name,
            manufacturer=self.light.manufacturername,
            model=self.light.productname,
            model_id=self.light.modelid,
            sw_version=self.light.swversion,
            via_device=(hue.DOMAIN, self.api.bridgeid),
        )
```

**Requirement:** Device info is only read if the entity is loaded via a config entry AND `unique_id` is defined.

### 3.4 Manual Device Registration

```python
from homeassistant.helpers import device_registry as dr

device_registry = dr.async_get(hass)

device_registry.async_get_or_create(
    config_entry_id=entry.entry_id,
    connections={(dr.CONNECTION_NETWORK_MAC, config.mac)},
    identifiers={(DOMAIN, config.bridgeid)},
    manufacturer="Signify",
    suggested_area="Kitchen",
    name=config.name,
    model=config.modelname,
    model_id=config.modelid,
    sw_version=config.swversion,
    hw_version=config.hwversion,
)
```

### 3.5 Sub-device / `via_device` Hierarchy

`via_device` links a child device to a parent device. Format: `(DOMAIN, parent_identifier)`.

```python
# Parent device (e.g., the Kamerplanter server)
DeviceInfo(
    identifiers={(DOMAIN, "kamerplanter_server")},
    name="Kamerplanter",
    manufacturer="Kamerplanter",
    model="Server",
    sw_version="1.0.0",
)

# Child device (e.g., a plant) linked to parent
DeviceInfo(
    identifiers={(DOMAIN, f"plant_{plant_key}")},
    name=plant_name,
    manufacturer="Kamerplanter",
    model="Plant",
    via_device=(DOMAIN, "kamerplanter_server"),
)
```

**Use case:** "A device that offers multiple endpoints may be split into separate devices and refer back to a parent device." Typical examples: smart power strips, multi-gang wall switches, hub+device hierarchies.

**For Kamerplanter:** Model as one server device with sub-devices per plant/location/tank, all using `via_device` to point back to the server.

### 3.6 Device Removal

```python
async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Remove a config entry from a device."""
    # Return True if device can be removed
    return True
```

If the removed config entry was the only one on the device, the device is also removed from the registry.

---

## 4. Config Entry Lifecycle

### 4.1 Lifecycle States

| State | Description |
|-------|-------------|
| `NOT_LOADED` | Initial state after creation or restart |
| `SETUP_IN_PROGRESS` | Loading attempt underway |
| `LOADED` | Successfully operational |
| `SETUP_ERROR` | Setup failure occurred |
| `SETUP_RETRY` | Dependency unavailable, auto-retry scheduled |
| `MIGRATION_ERROR` | Version migration failed |
| `UNLOAD_IN_PROGRESS` | Unloading underway |
| `FAILED_UNLOAD` | Unload unsupported or exception raised |

### 4.2 `async_setup_entry` / `async_unload_entry`

```python
async def async_setup_entry(hass: HomeAssistant, entry: MyConfigEntry) -> bool:
    """Set up from a config entry."""
    # 1. Create API client
    client = MyApiClient(entry.data["host"], entry.data["api_key"])

    # 2. Create coordinator
    coordinator = MyCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    # 3. Store runtime data
    entry.runtime_data = coordinator

    # 4. Forward platform setup
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: MyConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
```

**Critical rule:** A `ConfigEntry` object, including `data` and `options`, MUST NEVER be mutated directly. Use `hass.config_entries.async_update_entry()` instead.

### 4.3 Runtime Data Typing (modern pattern)

The `type` statement (Python 3.12+) creates a typed alias for `ConfigEntry` parameterized with your data class:

```python
# From unifi integration — simple pattern (store object directly):
from homeassistant.config_entries import ConfigEntry

type UnifiConfigEntry = ConfigEntry[UnifiHub]
```

```python
# From esphome integration — dataclass pattern:
from dataclasses import dataclass, field

@dataclass
class RuntimeEntryData:
    """Runtime data for ESPHome config entries."""
    client: APIClient
    entry_id: str
    title: str
    store: Store
    original_options: dict

type ESPHomeConfigEntry = ConfigEntry[RuntimeEntryData]
```

Usage in `async_setup_entry`:

```python
async def async_setup_entry(hass: HomeAssistant, entry: UnifiConfigEntry) -> bool:
    hub = entry.runtime_data = UnifiHub(hass, entry, api)
    # ...
```

```python
async def async_setup_entry(hass: HomeAssistant, entry: ESPHomeConfigEntry) -> bool:
    entry_data = RuntimeEntryData(client=cli, entry_id=entry.entry_id, ...)
    entry.runtime_data = entry_data
    # ...
```

**Key point:** `runtime_data` is automatically deleted when the entry is unloaded — no manual cleanup needed. This replaces the old `hass.data[DOMAIN][entry.entry_id]` pattern.

### 4.4 Migration Pattern

Class attributes on the config flow:

```python
class ExampleConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2
    MINOR_VERSION = 2
```

Full migration handler in `__init__.py`:

```python
async def async_migrate_entry(hass, config_entry: ConfigEntry):
    """Migrate old entry."""
    _LOGGER.debug(
        "Migrating configuration from version %s.%s",
        config_entry.version,
        config_entry.minor_version,
    )

    if config_entry.version > 1:
        # User has downgraded from a future version
        return False

    if config_entry.version == 1:
        new_data = {**config_entry.data}

        if config_entry.minor_version < 2:
            # Modify data for version 1.2 changes
            pass

        if config_entry.minor_version < 3:
            # Modify data for version 1.3 changes
            pass

        hass.config_entries.async_update_entry(
            config_entry, data=new_data, minor_version=3, version=1
        )

    _LOGGER.debug(
        "Migration to configuration version %s.%s successful",
        config_entry.version,
        config_entry.minor_version,
    )
    return True
```

### 4.5 Platform Forwarding

```python
PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.SWITCH]

await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
```

---

## 5. DataUpdateCoordinator

### 5.1 Full Coordinator Pattern

```python
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.exceptions import ConfigEntryAuthFailed

class MyCoordinator(DataUpdateCoordinator):
    """My custom coordinator."""

    def __init__(self, hass, config_entry, my_api):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="My sensor",
            config_entry=config_entry,
            update_interval=timedelta(seconds=30),
            always_update=True,
        )
        self.my_api = my_api
        self._device: MyDevice | None = None

    async def _async_setup(self):
        """Set up the coordinator.

        This is the place to set up your coordinator,
        or to load data, that only needs to be loaded once.

        This method will be called automatically during
        coordinator.async_config_entry_first_refresh.
        """
        self._device = await self.my_api.get_device()

    async def _async_update_data(self):
        """Fetch data from API endpoint."""
        try:
            async with async_timeout.timeout(10):
                listening_idx = set(self.async_contexts())
                return await self.my_api.fetch_data(listening_idx)
        except ApiAuthError as err:
            raise ConfigEntryAuthFailed from err
        except ApiError as err:
            raise UpdateFailed(f"Error communicating with API: {err}")
        except ApiRateLimited as err:
            raise UpdateFailed(retry_after=60)
```

### 5.2 `always_update` Parameter

| Value | Behavior |
|-------|----------|
| `True` (default) | Listeners always receive callbacks on every poll, even if data unchanged |
| `False` | Listeners only notified when data actually changes (compared via `__eq__`) |

**Use `False`** when the API returns data that can be meaningfully compared with `__eq__` (e.g., dataclasses, dicts). This prevents unnecessary state machine writes.

### 5.3 Error Handling Hierarchy

| Exception | Effect | Use Case |
|-----------|--------|----------|
| `ConfigEntryAuthFailed` | Cancels ALL future updates, initiates reauth flow | Authentication/credential failures |
| `UpdateFailed` | Marks coordinator as unavailable, retries on next interval | General API errors, timeouts |
| `UpdateFailed(retry_after=N)` | Same as above, but waits N seconds before retry | Rate limiting |
| `ConfigEntryNotReady` | Only during setup: delays entry setup with auto-retry | Initial connection failure |

**Error handling order in `_async_update_data`:**
1. Catch auth errors -> raise `ConfigEntryAuthFailed`
2. Catch API errors -> raise `UpdateFailed`
3. Catch rate limiting -> raise `UpdateFailed(retry_after=60)`

### 5.4 Initial Refresh

```python
# In async_setup_entry:
coordinator = MyCoordinator(hass, entry, api)
await coordinator.async_config_entry_first_refresh()
```

**`async_config_entry_first_refresh()`**: If the refresh fails, it raises `ConfigEntryNotReady` automatically, and HA will retry setup later. This also calls `_async_setup()` before the first `_async_update_data()`.

**Alternative:** `coordinator.async_refresh()` -- does NOT raise `ConfigEntryNotReady` on failure.

### 5.5 Entity Subscription

```python
class MyEntity(CoordinatorEntity, SensorEntity):
    """An entity using CoordinatorEntity."""

    def __init__(self, coordinator, idx):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator, context=idx)
        self.idx = idx

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_is_on = self.coordinator.data[self.idx]["state"]
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs):
        """Turn the light on."""
        # After action, request a refresh
        await self.coordinator.async_request_refresh()
```

`CoordinatorEntity` provides automatic:
- Polling management
- `async_update` implementation
- `async_added_to_hass` / `async_will_remove_from_hass` listener management
- `available` property (False when coordinator last update failed)

### 5.6 Push-based Updates

```python
# When new data arrives from websocket/callback:
coordinator.async_set_updated_data(new_data)
```

This notifies all listening entities immediately without waiting for the next poll interval.

---

## 6. Services with Entity Targeting

### 6.1 Domain Service (integration-level)

```python
@callback
def handle_hello(call: ServiceCall) -> None:
    """Handle the service action call."""
    name = call.data.get(ATTR_NAME, DEFAULT_NAME)
    hass.states.async_set("hello_action.hello", name)

hass.services.async_register(DOMAIN, "hello", handle_hello)
```

### 6.2 `SupportsResponse` Pattern

```python
from homeassistant.core import SupportsResponse, ServiceResponse

async def search_items(call: ServiceCall) -> ServiceResponse:
    """Search and return matching items."""
    items = await my_client.search(call.data["start"], call.data["end"])
    return {
        "items": [
            {
                "summary": item["summary"],
                "description": item["description"],
            }
            for item in items
        ],
    }

hass.services.async_register(
    DOMAIN,
    "search_items",
    search_items,
    schema=vol.Schema({
        vol.Required("start"): datetime.datetime,
        vol.Required("end"): datetime.datetime,
    }),
    supports_response=SupportsResponse.ONLY,
)
```

`SupportsResponse` values:
- `SupportsResponse.NONE` -- default, no response data
- `SupportsResponse.ONLY` -- always returns data (cannot be called without expecting response)
- `SupportsResponse.OPTIONAL` -- may return data

### 6.3 Entity Service (targets specific entities)

```python
from homeassistant.helpers import service

service.async_register_platform_entity_service(
    hass,
    DOMAIN,
    "set_sleep_timer",
    entity_domain=MEDIA_PLAYER_DOMAIN,
    schema={vol.Required("sleep_time"): cv.time_period},
    func="set_sleep_timer",
)
```

**Entity services** automatically handle entity/device/area targeting. The `func` string references a method name on the entity class, or pass a callable.

### 6.4 Target Selectors in `services.yaml`

```yaml
set_speed:
  target:
    entity:
      domain: fan
      supported_features:
        - fan.FanEntityFeature.SET_SPEED
  fields:
    speed:
      required: true
      advanced: true
      example: "low"
      default: "high"
      selector:
        select:
          translation_key: "fan_speed"
          options:
            - "off"
            - "low"
            - "medium"
            - "high"
```

Multiple required features (AND logic -- inner list):

```yaml
supported_features:
  - - fan.FanEntityFeature.SET_SPEED
    - fan.FanEntityFeature.OSCILLATE
```

Attribute filtering:

```yaml
filter:
  attribute:
    supported_color_modes:
      - light.ColorMode.COLOR_TEMP
      - light.ColorMode.HS
```

---

## 7. Repair Flows

### 7.1 Creating Repair Issues

```python
from homeassistant.helpers import issue_registry as ir

ir.async_create_issue(
    hass,
    DOMAIN,
    "manual_migration",              # issue_id (unique within domain)
    breaks_in_ha_version="2022.9.0", # when it becomes breaking
    is_fixable=False,                # can HA auto-fix it?
    is_persistent=True,              # survives restarts?
    severity=ir.IssueSeverity.ERROR,
    translation_key="manual_migration",
    learn_more_url="https://example.com/docs",
)
```

### 7.2 Severity Levels

| Level | Use Case |
|-------|----------|
| `IssueSeverity.CRITICAL` | Reserved for true panic situations only |
| `IssueSeverity.ERROR` | Current breakage requiring immediate action |
| `IssueSeverity.WARNING` | Future API shutdowns, deprecations |

### 7.3 `is_persistent` Logic

- `True` -- for events detected only during runtime (failed updates, unknown actions). Issue persists across restarts.
- `False` -- for checkable conditions (low disk space) that may resolve naturally. Needs to be re-created each startup.

### 7.4 ConfirmRepairFlow Implementation

Create `repairs.py` in your integration:

```python
from __future__ import annotations

import voluptuous as vol

from homeassistant import data_entry_flow
from homeassistant.components.repairs import ConfirmRepairFlow, RepairsFlow
from homeassistant.core import HomeAssistant


class Issue1RepairFlow(RepairsFlow):
    """Handler for an issue fixing flow."""

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the first step of a fix flow."""
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the confirm step of a fix flow."""
        if user_input is not None:
            # Perform the fix here
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
        )


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    """Create flow."""
    if issue_id == "issue_1":
        return Issue1RepairFlow()
    # For simple confirmation-only fixes:
    return ConfirmRepairFlow()
```

### 7.5 Deleting Repair Issues

```python
ir.async_delete_issue(hass, DOMAIN, "manual_migration")
```

Users can also ignore issues in the UI. Ignored issues only resurface after the integration deletes and re-creates them.

---

## 8. Options Flow vs Reconfigure Flow

### 8.1 Options Flow

**Purpose:** Tweaking behavior AFTER initial configuration. Available from the integration's gear icon. Does NOT modify `entry.data`, only `entry.options`.

**Registration:**

```python
class MyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlowHandler:
        return OptionsFlowHandler()
```

**Handler:**

```python
from homeassistant.config_entries import OptionsFlow, OptionsFlowWithReload

OPTIONS_SCHEMA = vol.Schema({
    vol.Required("show_things"): bool,
})

class OptionsFlowHandler(OptionsFlow):
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA, self.config_entry.options
            ),
        )
```

**With automatic reload** (reloads config entry when options change):

```python
class MyOptionsFlow(OptionsFlowWithReload):
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

**Manual update listener** (alternative to `OptionsFlowWithReload`):

```python
entry.async_on_unload(entry.add_update_listener(update_listener))

async def update_listener(hass: HomeAssistant, config_entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)
```

### 8.2 Reconfigure Flow

**Purpose:** Change CORE configuration (host, credentials, etc.) that lives in `entry.data`. NOT for optional tweaks.

**Implementation** (in config_flow.py, same class as ConfigFlow):

```python
async def async_step_reconfigure(
    self, user_input: dict[str, Any] | None = None
):
    if user_input is not None:
        self.async_set_unique_id(user_id)
        self._abort_if_unique_id_mismatch()
        return self.async_update_reload_and_abort(
            self._get_reconfigure_entry(),
            data_updates=data,
        )

    return self.async_show_form(
        step_id="reconfigure",
        data_schema=vol.Schema({vol.Required("input_parameter"): str}),
    )
```

### 8.3 When to Use Which

| Aspect | Options Flow | Reconfigure Flow |
|--------|-------------|-----------------|
| What it changes | `entry.options` | `entry.data` |
| Entry point | Always `async_step_init` | `async_step_reconfigure` |
| Creates new entry? | No (creates options entry) | No (updates + reloads + aborts) |
| Use for | Polling interval, display preferences, feature toggles | Host/URL, API key, credentials, connection params |
| Access current values | `self.config_entry` | `self._get_reconfigure_entry()` |
| Auto-reload | `OptionsFlowWithReload` or manual listener | Built-in via `async_update_reload_and_abort` |

---

## Appendix: Recent Changes (2024-2025)

1. **`runtime_data` on ConfigEntry** -- Replaces `hass.data[DOMAIN][entry.entry_id]` pattern. Typed via `type MyConfigEntry = ConfigEntry[MyDataClass]`. Auto-cleaned on unload.

2. **`OptionsFlowWithReload`** -- New base class that automatically reloads the config entry when options are saved. Replaces manual `add_update_listener` pattern.

3. **`UpdateFailed(retry_after=N)`** -- New parameter on `UpdateFailed` for rate-limited APIs. Coordinator waits N seconds before retrying.

4. **`_async_setup` on DataUpdateCoordinator** -- New method called once during `async_config_entry_first_refresh()`, before the first `_async_update_data()`. Use for one-time initialization.

5. **`config_entry` parameter on DataUpdateCoordinator** -- Pass the config entry directly to the coordinator constructor. Required for proper lifecycle management.

6. **`SupportsResponse.OPTIONAL`** -- Services can now optionally return data, in addition to `ONLY` and `NONE`.

7. **`async_update_reload_and_abort`** -- New helper for reconfigure flows that atomically updates data, triggers reload, and aborts the flow.

8. **`is_persistent` on repair issues** -- Controls whether issues survive HA restarts.

9. **`model_id` on DeviceInfo** -- Separate field for machine-readable model identifier (distinct from human-readable `model`).
