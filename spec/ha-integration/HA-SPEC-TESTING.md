# Spezifikation: Test-Infrastruktur fuer HA-Integration

```yaml
ID: HA-SPEC-TESTING
Titel: Testabdeckung fuer Kamerplanter HA Custom Integration
Status: Spezifiziert
Version: 1.0
Datum: 2026-04-03
Behebt: GAP-025
Abhaengigkeiten: HA-SPEC-CONFIG-LIFECYCLE, HA-SPEC-ENTITY-ARCHITECTURE (Tests basieren auf neuer Architektur)
Scope: tests/ha-integration/ (neues Verzeichnis)
Ziel: >95% Coverage auf config_flow.py, >80% auf restliche Module
Style Guide: spec/style-guides/HA-INTEGRATION.md §1.2
```

---

## 1. Ziel

Aufbau einer vollstaendigen Testinfrastruktur fuer die HA Custom Integration:
- Config-Flow-Tests (Bronze-Pflicht: 100% Coverage)
- Coordinator-Tests (Auth-Fehler, Connection-Fehler, Timeout, Enrichment)
- Entity-Tests (State-Werte, Attribute, Availability)
- Diagnostics-Tests (Redaktion sensitiver Daten)
- Service-Tests (fill_tank, water_channel, confirm_care)

---

## 2. Verzeichnisstruktur

```
custom_components/kamerplanter/
├── tests/
│   ├── __init__.py
│   ├── conftest.py                  # Shared Fixtures
│   ├── test_config_flow.py          # Config Flow (PFLICHT)
│   ├── test_init.py                 # Setup / Unload
│   ├── test_coordinator.py          # Coordinator Update + Fehler
│   ├── test_sensor.py               # Sensor States + Attribute
│   ├── test_binary_sensor.py        # Binary Sensor States
│   ├── test_diagnostics.py          # Diagnostics Redaktion
│   ├── test_services.py             # Service-Handler
│   └── fixtures/
│       ├── health.json              # GET /api/health Response
│       ├── plants.json              # GET /plant-instances Response
│       ├── locations.json           # GET /locations Response
│       ├── runs.json                # GET /planting-runs Response
│       ├── tasks_pending.json       # GET /tasks?status=pending Response
│       ├── tasks_overdue.json       # GET /tasks/overdue Response
│       ├── tenants.json             # GET /tenants Response
│       ├── user_me.json             # GET /users/me Response
│       ├── nutrient_plan.json       # GET /plant-instances/{key}/nutrient-plan
│       ├── current_dosages.json     # GET /plant-instances/{key}/current-dosages
│       └── tanks.json               # GET /tanks Response
```

---

## 3. Dependencies

```toml
# pyproject.toml oder requirements-test.txt
[tool.pytest.ini_options]
testpaths = ["custom_components/kamerplanter/tests"]
asyncio_mode = "auto"

[project.optional-dependencies]
test = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-homeassistant-custom-component>=0.13",
    "pytest-cov>=5.0",
    "aioresponses>=0.7",
]
```

---

## 4. conftest.py — Shared Fixtures

```python
"""Shared fixtures for Kamerplanter HA integration tests."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant

from custom_components.kamerplanter.const import (
    CONF_API_KEY,
    CONF_TENANT_SLUG,
    DOMAIN,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> Any:
    """Load a JSON fixture file."""
    return json.loads((FIXTURES_DIR / name).read_text())


@pytest.fixture
def mock_config_entry() -> ConfigEntry:
    """Create a mock config entry."""
    return ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="Kamerplanter (test)",
        data={
            CONF_URL: "http://localhost:8000",
            CONF_API_KEY: "kp_test_key_123",
            CONF_TENANT_SLUG: "test-tenant",
        },
        source="user",
        entry_id="test_entry_id",
        unique_id="http://localhost:8000_test-tenant",
    )


@pytest.fixture
def mock_api():
    """Create a mock KamerplanterApi."""
    with patch(
        "custom_components.kamerplanter.api.KamerplanterApi"
    ) as mock_cls:
        api = mock_cls.return_value
        api.async_get_health = AsyncMock(return_value=load_fixture("health.json"))
        api.async_get_current_user = AsyncMock(return_value=load_fixture("user_me.json"))
        api.async_get_tenants = AsyncMock(return_value=load_fixture("tenants.json"))
        api.async_get_plants = AsyncMock(return_value=load_fixture("plants.json"))
        api.async_get_pending_tasks = AsyncMock(return_value=load_fixture("tasks_pending.json"))
        api.async_get_overdue_tasks = AsyncMock(return_value=load_fixture("tasks_overdue.json"))
        api.async_get_tanks = AsyncMock(return_value=load_fixture("tanks.json"))
        api.async_get_plant_nutrient_plan = AsyncMock(return_value=load_fixture("nutrient_plan.json"))
        api.async_get_plant_current_dosages = AsyncMock(return_value=load_fixture("current_dosages.json"))
        api.async_get_plant_phase_history = AsyncMock(return_value=[])
        api.async_get_plant_active_channels = AsyncMock(return_value=[])
        api.async_get_planting_runs = AsyncMock(return_value=load_fixture("runs.json"))
        api.async_get_fertilizers = AsyncMock(return_value=[])
        api.async_get_sites = AsyncMock(return_value=[])
        api.async_get_all_locations = AsyncMock(return_value=load_fixture("locations.json"))
        yield api
```

---

## 5. test_config_flow.py (PFLICHT — 100% Coverage)

### 5.1 Testfaelle

| Test | Beschreibung | Ergebnis |
|------|-------------|----------|
| `test_user_flow_success` | URL + Key + Single-Tenant | CREATE_ENTRY |
| `test_user_flow_multi_tenant` | URL + Key → Tenant-Step | FORM (tenant) |
| `test_user_flow_light_mode` | URL ohne Key (Light) | CREATE_ENTRY |
| `test_user_flow_cannot_connect` | URL nicht erreichbar | FORM mit error |
| `test_user_flow_invalid_auth` | Falscher API-Key | FORM mit error |
| `test_user_flow_no_tenants` | Keine Tenants verfuegbar | FORM mit error |
| `test_user_flow_already_configured` | Duplikat | ABORT |
| `test_tenant_step` | Tenant-Auswahl | CREATE_ENTRY |
| `test_reauth_flow_success` | Neuer Key → Reload | UPDATE_RELOAD_ABORT |
| `test_reauth_flow_invalid` | Falscher Key | FORM mit error |
| `test_reconfigure_flow_success` | Neue URL → Reload | UPDATE_RELOAD_ABORT |
| `test_reconfigure_flow_cannot_connect` | URL nicht erreichbar | FORM mit error |
| `test_options_flow` | Polling-Intervalle aendern | CREATE_ENTRY |

### 5.2 Beispiel-Test

```python
async def test_user_flow_success(hass: HomeAssistant, mock_api) -> None:
    """Test successful user config flow with single tenant."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == "form"
    assert result["step_id"] == "user"

    with patch(
        "custom_components.kamerplanter.config_flow.KamerplanterApi"
    ) as mock_api_cls:
        mock_api_cls.return_value = mock_api
        mock_api.async_get_tenants.return_value = [{"slug": "garden", "name": "My Garden"}]

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_URL: "http://localhost:8000", CONF_API_KEY: "kp_test"},
        )

    assert result["type"] == "create_entry"
    assert result["title"] == "Kamerplanter (garden)"
    assert result["data"][CONF_URL] == "http://localhost:8000"
    assert result["data"][CONF_API_KEY] == "kp_test"
    assert result["data"][CONF_TENANT_SLUG] == "garden"


async def test_reauth_flow_success(hass: HomeAssistant, mock_config_entry, mock_api) -> None:
    """Test successful re-authentication flow."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "reauth", "entry_id": mock_config_entry.entry_id},
    )
    assert result["type"] == "form"
    assert result["step_id"] == "reauth_confirm"

    with patch(
        "custom_components.kamerplanter.config_flow.KamerplanterApi"
    ) as mock_api_cls:
        mock_api_cls.return_value = mock_api

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_API_KEY: "kp_new_key"},
        )

    assert result["type"] == "abort"
    assert result["reason"] == "reauth_successful"
```

---

## 6. test_coordinator.py

### 6.1 Testfaelle

| Test | Beschreibung |
|------|-------------|
| `test_plant_coordinator_update` | Erfolgreicher Fetch + Enrichment |
| `test_plant_coordinator_auth_error` | KamerplanterAuthError → ConfigEntryAuthFailed |
| `test_plant_coordinator_connection_error` | KamerplanterConnectionError → UpdateFailed |
| `test_plant_coordinator_timeout` | API-Timeout → UpdateFailed |
| `test_plant_coordinator_enrichment_failure` | Enrichment-Fehler → Plant trotzdem in Data |
| `test_location_coordinator_update` | Erfolgreicher Location-Fetch |
| `test_alert_coordinator_update` | Overdue-Tasks korrekt geladen |
| `test_task_coordinator_update` | Pending-Tasks korrekt geladen |

---

## 7. test_sensor.py

### 7.1 Testfaelle

| Test | Beschreibung |
|------|-------------|
| `test_plant_phase_sensor_state` | Phase-Sensor zeigt korrekte Phase |
| `test_plant_days_in_phase` | Tage-Berechnung korrekt |
| `test_sensor_unavailable_on_coordinator_failure` | Entity unavailable bei Fehler |
| `test_sensor_available_with_data` | Entity available mit Daten |
| `test_tasks_due_today_count` | Count-Sensor korrekt |
| `test_tasks_overdue_attributes` | Overdue-Attribute korrekt |

---

## 8. test_diagnostics.py

```python
async def test_diagnostics_redaction(hass, mock_config_entry) -> None:
    """Test that sensitive data is redacted in diagnostics."""
    # Setup entry...
    result = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    # API key must be redacted
    assert result["entry_data"]["api_key"] == "**REDACTED**"
    # Non-sensitive data must be present
    assert result["entry_data"]["url"] == "http://localhost:8000"
    assert result["plant_count"] >= 0
```

---

## 9. test_services.py

### 9.1 Testfaelle

| Test | Beschreibung |
|------|-------------|
| `test_fill_tank_by_entity_id` | fill_tank mit Entity-ID |
| `test_fill_tank_by_key` | fill_tank mit direktem Tank-Key |
| `test_fill_tank_missing_key` | fill_tank ohne Key → Error-Log |
| `test_water_channel_by_entity_id` | water_channel mit Entity-ID |
| `test_confirm_care` | confirm_care mit Notification-Key |
| `test_refresh_data` | refresh_data triggert Coordinator-Refresh |

---

## 10. Fixtures (JSON-Beispieldaten)

### 10.1 health.json

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "mode": "full"
}
```

### 10.2 tenants.json

```json
[
  {"slug": "test-tenant", "name": "Test Garden", "key": "tenant-001"}
]
```

### 10.3 plants.json (Minimal)

```json
[
  {
    "key": "plant-001",
    "plant_name": "Tomate #1",
    "instance_id": "PLANT-001",
    "current_phase": "vegetative",
    "current_phase_started_at": "2026-03-01T00:00:00Z",
    "removed_on": null,
    "slot_key": "slot-001"
  }
]
```

### 10.4 tasks_pending.json

```json
[
  {
    "key": "task-001",
    "name": "Tomate giessen",
    "title": "Tomate giessen",
    "category": "watering",
    "priority": "high",
    "status": "pending",
    "due_date": "2026-04-03T08:00:00Z"
  }
]
```

---

## 11. Coverage-Kommando

```bash
pytest custom_components/kamerplanter/tests/ \
  --cov=custom_components.kamerplanter \
  --cov-report=term-missing \
  --cov-fail-under=80 \
  -vv
```

**Ziel-Coverage:**
| Modul | Minimum |
|-------|---------|
| `config_flow.py` | 95% (Bronze-Pflicht) |
| `coordinator.py` | 80% |
| `__init__.py` | 80% |
| `sensor.py` | 70% |
| `diagnostics.py` | 90% |
| Gesamt | 80% |

---

## 12. Akzeptanzkriterien

- [ ] `tests/` Verzeichnis existiert mit conftest.py und Fixtures
- [ ] `test_config_flow.py` deckt alle 13 Testfaelle ab
- [ ] Config-Flow-Tests: User-Flow, Light-Mode, Multi-Tenant, Fehler, Reauth, Reconfigure
- [ ] Coordinator-Tests: Erfolg, Auth-Fehler, Connection-Fehler, Timeout
- [ ] Diagnostics-Test: API-Key wird redaktiert
- [ ] Coverage >= 80% gesamt, >= 95% auf config_flow.py
- [ ] Tests laufen mit `pytest-homeassistant-custom-component`
- [ ] Keine Tests brechen bei bestehender Funktionalitaet
