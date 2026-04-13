# Spezifikation: Config Entry Lifecycle Migration

```yaml
ID: HA-SPEC-CONFIG
Titel: Config Entry Lifecycle auf HA Best Practices migrieren
Status: Spezifiziert
Version: 1.0
Datum: 2026-04-03
Behebt: GAP-001, GAP-007, GAP-008, GAP-009, GAP-010, GAP-016, GAP-017, GAP-032
Abhaengigkeiten: Keine (kann als erstes umgesetzt werden)
Scope: __init__.py, config_flow.py, diagnostics.py, manifest.json, strings.json, const.py
Style Guide: spec/style-guides/HA-INTEGRATION.md §3, §8, §11, §12
```

---

## 1. Ziel

Migration des Config Entry Lifecycles auf moderne HA-Patterns:
- `runtime_data` statt `hass.data[DOMAIN]`
- Reauth-Flow fuer abgelaufene/revoked API-Keys
- Reconfigure-Flow fuer URL-Aenderung
- Unique ID auf Config Entry (Duplikat-Verhinderung)
- `OptionsFlowWithReload` statt manuellem Listener
- `async_redact_data` in Diagnostics
- manifest.json Pflichtfelder ergaenzen

---

## 2. runtime_data Migration (__init__.py)

### 2.1 RuntimeData Dataclass

```python
from dataclasses import dataclass

@dataclass
class KamerplanterRuntimeData:
    """Runtime data stored on the config entry."""
    api: KamerplanterApi
    coordinators: dict[str, DataUpdateCoordinator]

type KamerplanterConfigEntry = ConfigEntry[KamerplanterRuntimeData]
```

### 2.2 async_setup_entry — Vorher/Nachher

**Vorher:**
```python
hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
    "api": api,
    "coordinators": coordinators,
}
```

**Nachher:**
```python
entry.runtime_data = KamerplanterRuntimeData(api=api, coordinators=coordinators)
```

### 2.3 async_unload_entry — Vorher/Nachher

**Vorher:**
```python
async def async_unload_entry(hass, entry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)
            # Manuelles Service-Deregistrieren...
    return unload_ok
```

**Nachher:**
```python
async def async_unload_entry(hass: HomeAssistant, entry: KamerplanterConfigEntry) -> bool:
    # runtime_data wird automatisch bereinigt
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
```

### 2.4 Service-Handler Migration

Service-Handler muessen von `hass.data[DOMAIN]` auf `entry.runtime_data` umgestellt werden.

**Vorher:**
```python
data = hass.data[DOMAIN].get(entry.entry_id)
api = data["api"]
coordinators = data["coordinators"]
```

**Nachher:**
```python
entry = hass.config_entries.async_entries(DOMAIN)[0]
api = entry.runtime_data.api
coordinators = entry.runtime_data.coordinators
```

### 2.5 Plattform-Setup Migration

**Vorher (sensor.py etc.):**
```python
data = hass.data[DOMAIN][entry.entry_id]
coordinator = data["coordinators"]["plants"]
```

**Nachher:**
```python
coordinator = entry.runtime_data.coordinators["plants"]
```

---

## 3. Reauth-Flow (config_flow.py)

### 3.1 Trigger

Wenn ein Coordinator `ConfigEntryAuthFailed` raised (API-Key revoked, abgelaufen), zeigt HA automatisch "Reauthentication required" an. Der User klickt darauf und wird zum Reauth-Flow geleitet.

### 3.2 Implementation

```python
class KamerplanterConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    # ... bestehende Steps ...

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-authentication when API key is invalid."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask user for new API key."""
        errors: dict[str, str] = {}

        if user_input is not None:
            reauth_entry = self._get_reauth_entry()
            session = async_get_clientsession(self.hass)
            api = KamerplanterApi(
                base_url=reauth_entry.data[CONF_URL],
                session=session,
                api_key=user_input[CONF_API_KEY],
            )
            try:
                await api.async_get_current_user()
            except KamerplanterAuthError:
                errors["base"] = "invalid_auth"
            except KamerplanterConnectionError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={CONF_API_KEY: user_input[CONF_API_KEY]},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({
                vol.Required(CONF_API_KEY): str,
            }),
            errors=errors,
        )
```

### 3.3 strings.json Ergaenzung

```json
{
  "config": {
    "step": {
      "reauth_confirm": {
        "title": "Re-authenticate Kamerplanter",
        "description": "Your API key is invalid or expired. Please enter a new one.",
        "data": {
          "api_key": "API Key (kp_...)"
        }
      }
    },
    "abort": {
      "reauth_successful": "Re-authentication successful"
    }
  }
}
```

---

## 4. Reconfigure-Flow (config_flow.py)

### 4.1 Zweck

Erlaubt dem User die URL zu aendern (z.B. Server-Migration) ohne die Integration loeschen und neu einrichten zu muessen. Erreichbar ueber das 3-Punkte-Menue der Integration.

### 4.2 Implementation

```python
async def async_step_reconfigure(
    self, user_input: dict[str, Any] | None = None
) -> ConfigFlowResult:
    """Handle reconfiguration (URL change)."""
    errors: dict[str, str] = {}

    if user_input is not None:
        new_url = user_input[CONF_URL].rstrip("/")
        session = async_get_clientsession(self.hass)
        api = KamerplanterApi(base_url=new_url, session=session)
        try:
            await api.async_get_health()
        except KamerplanterConnectionError:
            errors["base"] = "cannot_connect"
        else:
            return self.async_update_reload_and_abort(
                self._get_reconfigure_entry(),
                data_updates={CONF_URL: new_url},
            )

    reconfigure_entry = self._get_reconfigure_entry()
    return self.async_show_form(
        step_id="reconfigure",
        data_schema=vol.Schema({
            vol.Required(CONF_URL, default=reconfigure_entry.data.get(CONF_URL, "")): str,
        }),
        errors=errors,
    )
```

### 4.3 strings.json Ergaenzung

```json
{
  "config": {
    "step": {
      "reconfigure": {
        "title": "Reconfigure Kamerplanter",
        "description": "Change the Kamerplanter server URL.",
        "data": {
          "url": "URL"
        }
      }
    }
  }
}
```

---

## 5. Unique ID auf Config Entry

### 5.1 Implementation in async_step_user

Nach erfolgreicher URL-Validierung und Tenant-Auswahl:

```python
# In async_step_user (nach Health-Check):
unique_id = f"{self._base_url}_{self._tenants[0]['slug'] if len(self._tenants) == 1 else ''}"

# In async_step_tenant:
unique_id = f"{self._base_url}_{user_input[CONF_TENANT_SLUG]}"

# Setzen:
await self.async_set_unique_id(unique_id)
self._abort_if_unique_id_configured()
```

### 5.2 strings.json Ergaenzung

```json
{
  "config": {
    "abort": {
      "already_configured": "This Kamerplanter instance is already configured"
    }
  }
}
```

---

## 6. OptionsFlowWithReload

### 6.1 Vorher

```python
class KamerplanterOptionsFlow(OptionsFlow):
    ...

# In __init__.py:
entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

async def _async_reload_entry(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)
```

### 6.2 Nachher

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

Das manuelle `add_update_listener` + `_async_reload_entry` in `__init__.py` kann entfernt werden.

---

## 7. Diagnostics mit async_redact_data

### 7.1 Vorher

```python
api_key = config_entry.data.get(CONF_API_KEY, "")
redacted_key = f"{api_key[:8]}..." if len(api_key) > 8 else "***"
return { "api_key_prefix": redacted_key, ... }
```

### 7.2 Nachher

```python
from homeassistant.components.diagnostics import async_redact_data

TO_REDACT = {CONF_API_KEY, "password", "token"}

async def async_get_config_entry_diagnostics(hass, config_entry):
    data = config_entry.runtime_data
    coordinators = data.coordinators
    return {
        "entry_data": async_redact_data(dict(config_entry.data), TO_REDACT),
        "entry_options": dict(config_entry.options),
        "plant_count": len(coordinators["plants"].data or []),
        "location_count": len(coordinators["locations"].data or []),
        "run_count": len(coordinators["runs"].data or []),
        "active_alerts": len(coordinators["alerts"].data or []),
        "pending_tasks": len(coordinators["tasks"].data or []),
        "coordinator_update_intervals": {
            name: coord.update_interval.total_seconds()
            for name, coord in coordinators.items()
        },
    }
```

---

## 8. manifest.json Ergaenzungen

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

Neue Felder gegenueber Ist-Zustand:
- `"integration_type": "hub"` (GAP-017)
- `"loggers": ["custom_components.kamerplanter"]` (GAP-017)

---

## 9. flow_title in strings.json

```json
{
  "config": {
    "flow_title": "Kamerplanter ({url})"
  }
}
```

---

## 10. Umsetzungsreihenfolge

1. `manifest.json` ergaenzen (integration_type, loggers)
2. `KamerplanterRuntimeData` Dataclass erstellen
3. `__init__.py`: `async_setup_entry` auf `runtime_data` umstellen
4. `__init__.py`: `async_unload_entry` vereinfachen
5. Service-Handler auf `entry.runtime_data` umstellen
6. Alle Plattform-Dateien: `hass.data[DOMAIN]` → `entry.runtime_data`
7. `config_flow.py`: Reauth-Flow hinzufuegen
8. `config_flow.py`: Reconfigure-Flow hinzufuegen
9. `config_flow.py`: Unique ID setzen + abort_if_configured
10. `config_flow.py`: `OptionsFlowWithReload` verwenden
11. `__init__.py`: `_async_reload_entry` + `add_update_listener` entfernen
12. `diagnostics.py`: `async_redact_data` verwenden
13. `strings.json` / `translations/*.json`: Neue Steps + flow_title

---

## 11. Akzeptanzkriterien

- [ ] `hass.data[DOMAIN]` kommt nirgends mehr vor
- [ ] `entry.runtime_data` ist typisiert via `KamerplanterConfigEntry`
- [ ] `async_unload_entry` hat kein manuelles `hass.data.pop()`
- [ ] Reauth-Flow funktioniert: API-Key aendern nach `ConfigEntryAuthFailed`
- [ ] Reconfigure-Flow funktioniert: URL aendern
- [ ] Doppelte Konfiguration derselben URL+Tenant wird verhindert
- [ ] `OptionsFlowWithReload` wird verwendet, kein manueller Listener
- [ ] `diagnostics.py` nutzt `async_redact_data`
- [ ] `manifest.json` hat `integration_type` und `loggers`
- [ ] `strings.json` hat `reauth_confirm`, `reconfigure`, `flow_title`
