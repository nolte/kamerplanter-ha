"""Tests for the first-class task services (start / complete / skip)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kamerplanter import (
    KamerplanterRuntimeData,
    _async_register_services,
)
from custom_components.kamerplanter.const import (
    DOMAIN,
    SERVICE_COMPLETE_TASK,
    SERVICE_SKIP_TASK,
    SERVICE_START_TASK,
)


def _mock_api() -> MagicMock:
    api = MagicMock()
    api.async_start_task = AsyncMock(return_value={"status": "in_progress"})
    api.async_complete_task = AsyncMock(return_value={"status": "completed"})
    api.async_skip_task = AsyncMock(return_value={"status": "skipped"})
    return api


def _mock_coordinator() -> MagicMock:
    coord = MagicMock()
    coord.async_request_refresh = AsyncMock()
    return coord


async def _setup_entry(hass) -> tuple[MockConfigEntry, MagicMock, MagicMock]:
    """Register services and attach a config entry with mock runtime_data."""
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    api = _mock_api()
    coordinator = _mock_coordinator()
    entry.runtime_data = KamerplanterRuntimeData(
        api=api,
        coordinators={"tasks": coordinator, "alerts": _mock_coordinator()},
    )
    await _async_register_services(hass)
    return entry, api, coordinator


@pytest.mark.parametrize(
    ("service", "api_attr"),
    [
        (SERVICE_START_TASK, "async_start_task"),
        (SERVICE_COMPLETE_TASK, "async_complete_task"),
        (SERVICE_SKIP_TASK, "async_skip_task"),
    ],
)
async def test_task_service_registered(hass, service, api_attr) -> None:
    """Each task service is registered under the kamerplanter domain."""
    await _setup_entry(hass)
    assert hass.services.has_service(DOMAIN, service)


@pytest.mark.parametrize(
    ("service", "api_attr"),
    [
        (SERVICE_START_TASK, "async_start_task"),
        (SERVICE_COMPLETE_TASK, "async_complete_task"),
        (SERVICE_SKIP_TASK, "async_skip_task"),
    ],
)
async def test_task_service_calls_api_by_task_key(hass, service, api_attr) -> None:
    """Calling the service with a task_key triggers the matching API call."""
    _entry, api, coordinator = await _setup_entry(hass)

    await hass.services.async_call(
        DOMAIN, service, {"task_key": "task-42"}, blocking=True
    )

    getattr(api, api_attr).assert_awaited_once_with("task-42")
    coordinator.async_request_refresh.assert_awaited()


async def test_task_service_targets_by_entity_id(hass) -> None:
    """The service resolves the task_key from a targeted entity's attributes."""
    _entry, api, coordinator = await _setup_entry(hass)

    hass.states.async_set("sensor.kp_task", "1", {"task_key": "task-from-entity"})

    await hass.services.async_call(
        DOMAIN,
        SERVICE_COMPLETE_TASK,
        {"entity_id": "sensor.kp_task"},
        blocking=True,
    )

    api.async_complete_task.assert_awaited_once_with("task-from-entity")
    coordinator.async_request_refresh.assert_awaited()


async def test_task_service_without_target_is_noop(hass) -> None:
    """Without task_key or entity_id no API call is made."""
    _entry, api, coordinator = await _setup_entry(hass)

    await hass.services.async_call(DOMAIN, SERVICE_START_TASK, {}, blocking=True)

    api.async_start_task.assert_not_awaited()
    coordinator.async_request_refresh.assert_not_awaited()


async def test_task_service_raises_on_api_error(hass) -> None:
    """An API failure propagates as HomeAssistantError instead of a silent log."""
    _entry, api, coordinator = await _setup_entry(hass)
    api.async_complete_task = AsyncMock(side_effect=RuntimeError("backend down"))

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN, SERVICE_COMPLETE_TASK, {"task_key": "task-1"}, blocking=True
        )

    # The refresh must not run when the action itself failed.
    coordinator.async_request_refresh.assert_not_awaited()
