"""Tests for the Kamerplanter coordinators."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.kamerplanter.api import (
    KamerplanterApi,
    KamerplanterAuthError,
    KamerplanterConnectionError,
)
from custom_components.kamerplanter.coordinator import (
    KamerplanterAlertCoordinator,
    KamerplanterPlantCoordinator,
    KamerplanterTaskCoordinator,
    _calc_current_week,
)

from .conftest import load_fixture


def test_calc_current_week() -> None:
    """Test week calculation from ISO date."""
    # 7 days = week 2
    from datetime import datetime, timedelta, timezone

    started = (datetime.now(tz=timezone.utc) - timedelta(days=7)).isoformat()
    assert _calc_current_week(started) == 2

    # Day 0 = week 1
    started = datetime.now(tz=timezone.utc).isoformat()
    assert _calc_current_week(started) == 1


async def test_plant_coordinator_auth_error(hass) -> None:
    """Test that auth errors raise ConfigEntryAuthFailed."""
    from homeassistant.exceptions import ConfigEntryAuthFailed

    api = MagicMock(spec=KamerplanterApi)
    api.async_get_plants = AsyncMock(side_effect=KamerplanterAuthError("expired"))
    api.async_get_fertilizers = AsyncMock(return_value=[])

    entry = MagicMock()
    entry.options = {}
    entry.entry_id = "test"

    coord = KamerplanterPlantCoordinator(hass, entry, api)
    with pytest.raises(ConfigEntryAuthFailed):
        await coord._async_update_data()


async def test_plant_coordinator_connection_error(hass) -> None:
    """Test that connection errors raise UpdateFailed."""
    from homeassistant.helpers.update_coordinator import UpdateFailed

    api = MagicMock(spec=KamerplanterApi)
    api.async_get_plants = AsyncMock(side_effect=KamerplanterConnectionError("down"))
    api.async_get_fertilizers = AsyncMock(return_value=[])

    entry = MagicMock()
    entry.options = {}
    entry.entry_id = "test"

    coord = KamerplanterPlantCoordinator(hass, entry, api)
    with pytest.raises(UpdateFailed):
        await coord._async_update_data()


def _plant_api(plants: list[dict], published: list[str] | None) -> MagicMock:
    """Build a mock API for the plant coordinator with neutral enrichment."""
    api = MagicMock(spec=KamerplanterApi)
    api.async_get_plants = AsyncMock(return_value=plants)
    api.async_get_ha_published_keys = AsyncMock(return_value=published)
    # Enrichment methods return neutral values so _enrich_plant is a no-op.
    api.async_get_plant_nutrient_plan = AsyncMock(return_value=None)
    api.async_get_plant_phase_history = AsyncMock(return_value=[])
    api.async_get_growth_phase = AsyncMock(return_value=None)
    api.async_get_care_profile = AsyncMock(return_value=None)
    api.async_get_care_history = AsyncMock(return_value=[])
    api.async_get_plant_current_dosages = AsyncMock(return_value=None)
    api.async_get_plant_active_channels = AsyncMock(return_value=[])
    return api


async def test_plant_coordinator_ha_publish_filter(hass) -> None:
    """Plant coordinator returns only HA-published plants when feature active."""
    api = _plant_api([{"key": "plant-1"}, {"key": "plant-2"}], ["plant-1"])

    entry = MagicMock()
    entry.options = {}
    entry.entry_id = "test"

    coord = KamerplanterPlantCoordinator(hass, entry, api)
    result = await coord._async_update_data()
    assert {p["key"] for p in result} == {"plant-1"}


async def test_plant_coordinator_no_filter_without_feature(hass) -> None:
    """A backend without ha-publish (None) is not filtered."""
    api = _plant_api([{"key": "plant-1"}, {"key": "plant-2"}], None)

    entry = MagicMock()
    entry.options = {}
    entry.entry_id = "test"

    coord = KamerplanterPlantCoordinator(hass, entry, api)
    result = await coord._async_update_data()
    assert {p["key"] for p in result} == {"plant-1", "plant-2"}


async def test_alert_coordinator_success(hass) -> None:
    """Test successful alert coordinator update."""
    api = MagicMock(spec=KamerplanterApi)
    api.async_get_overdue_tasks = AsyncMock(return_value=[])

    entry = MagicMock()
    entry.options = {}
    entry.entry_id = "test"

    coord = KamerplanterAlertCoordinator(hass, entry, api)
    result = await coord._async_update_data()
    assert result == []


async def test_task_coordinator_success(hass) -> None:
    """Test successful task coordinator update."""
    tasks = load_fixture("tasks_pending.json")
    api = MagicMock(spec=KamerplanterApi)
    api.async_get_pending_tasks = AsyncMock(return_value=tasks)

    entry = MagicMock()
    entry.options = {}
    entry.entry_id = "test"

    coord = KamerplanterTaskCoordinator(hass, entry, api)
    result = await coord._async_update_data()
    assert len(result) == 1
    assert result[0]["key"] == "task-001"


async def test_task_coordinator_resolves_readable_names(hass) -> None:
    """Task coordinator replaces the code slug with a readable plant name (#57)."""
    tasks = [
        {
            "key": "task-xub",
            "name": "SPATH-0617-XUB — watering",
            "category": "watering",
            "entity_key": "plant-spath",
            "due_date": "2026-04-03T08:00:00Z",
        }
    ]
    plants = [
        {
            "key": "plant-spath",
            "instance_id": "SPATH-0617-XUB",
            "plant_name": None,
            "species": {
                "scientific_name": "Spathiphyllum wallisii",
                "common_names": ["Einblatt"],
            },
        }
    ]
    api = MagicMock(spec=KamerplanterApi)
    api.async_get_pending_tasks = AsyncMock(return_value=tasks)
    api.async_get_plants = AsyncMock(return_value=plants)

    entry = MagicMock()
    entry.options = {}
    entry.entry_id = "test"

    coord = KamerplanterTaskCoordinator(hass, entry, api)
    result = await coord._async_update_data()

    assert result[0]["plant_name"] == "Einblatt"
    assert result[0]["_display_name"] == "Einblatt — watering"
    assert "SPATH-0617-XUB" not in result[0]["_display_name"]
