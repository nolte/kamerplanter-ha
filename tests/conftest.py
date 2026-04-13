"""Shared fixtures for Kamerplanter HA integration tests."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import CONF_URL

FIXTURES_DIR = Path(__file__).parent / "fixtures"

DOMAIN = "kamerplanter"
CONF_API_KEY = "api_key"
CONF_TENANT_SLUG = "tenant_slug"


def load_fixture(name: str) -> Any:
    """Load a JSON fixture file."""
    return json.loads((FIXTURES_DIR / name).read_text())


@pytest.fixture
def mock_config_entry_data() -> dict[str, Any]:
    """Create mock config entry data."""
    return {
        CONF_URL: "http://localhost:8000",
        CONF_API_KEY: "kp_test_key_123",
        CONF_TENANT_SLUG: "test-tenant",
        "light_mode": False,
    }


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
        api.async_get_run_nutrient_plan = AsyncMock(return_value=None)
        api.async_get_run_phase_timeline = AsyncMock(return_value=[])
        api.async_get_run_active_channels = AsyncMock(return_value=[])
        api.async_get_runs_by_location = AsyncMock(return_value=[])
        api.async_get_plant_instances_by_location = AsyncMock(return_value=[])
        api.async_get_tank_latest_fill = AsyncMock(return_value=None)
        api.async_get_tank_sensors = AsyncMock(return_value=[])
        api.async_get_plan_phase_entries = AsyncMock(return_value=[])
        yield api
