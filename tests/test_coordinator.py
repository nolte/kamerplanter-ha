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
