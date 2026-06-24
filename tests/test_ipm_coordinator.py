"""Tests for the Kamerplanter IPM coordinator (REQ-010)."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_homeassistant_custom_component.common import async_capture_events

from custom_components.kamerplanter.api import (
    KamerplanterApi,
    KamerplanterAuthError,
    KamerplanterConnectionError,
)
from custom_components.kamerplanter.const import EVENT_IPM_ALERT
from custom_components.kamerplanter.coordinator import (
    KamerplanterIpmCoordinator,
    _days_since,
    _days_until,
)


def _mock_entry() -> MagicMock:
    entry = MagicMock()
    entry.options = {}
    entry.entry_id = "test"
    return entry


def _ipm_api(
    *,
    plants: list[dict] | None = None,
    inspections: list[dict] | None = None,
    karenz: dict | None = None,
    harvest: dict | None = None,
) -> MagicMock:
    api = MagicMock(spec=KamerplanterApi)
    api.async_get_plants = AsyncMock(
        return_value=plants
        if plants is not None
        else [{"key": "plant-1", "plant_name": "Tomato"}]
    )
    api.async_get_pest_inspections = AsyncMock(return_value=inspections or [])
    api.async_get_karenz = AsyncMock(return_value=karenz)
    api.async_get_harvest_safety = AsyncMock(return_value=harvest)
    # Default: no HA-publish feature -> no filtering.
    api.async_get_ha_published_keys = AsyncMock(return_value=None)
    return api


def test_days_until_and_since() -> None:
    """Date-only helpers are deterministic relative to today."""
    future = (date.today() + timedelta(days=5)).isoformat()
    past = (date.today() - timedelta(days=3)).isoformat()
    assert _days_until(future) == 5
    assert _days_since(past) == 3
    assert _days_until(None) is None
    assert _days_since(None) is None
    assert _days_until("not-a-date") is None


async def test_ipm_coordinator_aggregates_record(hass) -> None:
    """A plant record aggregates inspection, Karenz and harvest-safety data."""
    safe_date = (date.today() + timedelta(days=5)).isoformat()
    api = _ipm_api(
        inspections=[
            {"inspected_at": "2026-06-01", "pressure_level": "low"},
            {
                "inspected_at": "2026-06-20",
                "pressure_level": "high",
                "detected_pest_keys": ["aphid"],
            },
        ],
        karenz=[
            {
                "safe_date": safe_date,
                "treatment_name": "Neem",
                "active_ingredient": "azadirachtin",
            },
        ],
        harvest={"can_harvest": False, "blocking_treatments": [{"name": "Neem"}]},
    )

    coord = KamerplanterIpmCoordinator(hass, _mock_entry(), api)
    result = await coord._async_update_data()

    assert len(result) == 1
    rec = result[0]
    assert rec["key"] == "plant-1"
    # Latest inspection (highest inspected_at) wins.
    assert rec["pressure_level"] == "high"
    assert rec["detected_pest_keys"] == ["aphid"]
    assert rec["karenz_remaining_days"] == 5
    assert rec["karenz_safe_date"] == safe_date
    assert rec["treatment_name"] == "Neem"
    assert rec["can_harvest"] is False
    assert rec["blocking_treatments"] == [{"name": "Neem"}]


async def test_ipm_coordinator_picks_longest_binding_karenz(hass) -> None:
    """With several Karenz periods, the latest safe_date drives the values."""
    near = (date.today() + timedelta(days=2)).isoformat()
    far = (date.today() + timedelta(days=9)).isoformat()
    api = _ipm_api(
        karenz=[
            {"safe_date": near, "treatment_name": "Sulphur"},
            {"safe_date": far, "treatment_name": "Neem"},
        ],
    )

    coord = KamerplanterIpmCoordinator(hass, _mock_entry(), api)
    rec = (await coord._async_update_data())[0]

    assert rec["karenz_remaining_days"] == 9
    assert rec["karenz_safe_date"] == far
    assert rec["treatment_name"] == "Neem"


async def test_ipm_coordinator_defaults_without_data(hass) -> None:
    """No inspections/Karenz yields safe defaults and never crashes."""
    api = _ipm_api(inspections=[], karenz=None, harvest=None)

    coord = KamerplanterIpmCoordinator(hass, _mock_entry(), api)
    result = await coord._async_update_data()

    assert len(result) == 1
    rec = result[0]
    assert rec["pressure_level"] == "none"
    assert rec["karenz_remaining_days"] is None
    assert rec["can_harvest"] is True
    assert rec["last_inspection_days"] is None


async def test_ipm_coordinator_respects_ha_publish_filter(hass) -> None:
    """Only HA-published plants yield IPM records when the feature is active."""
    api = _ipm_api(
        plants=[
            {"key": "plant-1", "plant_name": "Tomato"},
            {"key": "plant-2", "plant_name": "Basil"},
        ]
    )
    api.async_get_ha_published_keys = AsyncMock(return_value=["plant-1"])

    coord = KamerplanterIpmCoordinator(hass, _mock_entry(), api)
    result = await coord._async_update_data()

    assert {r["key"] for r in result} == {"plant-1"}


async def test_ipm_coordinator_no_filter_when_feature_absent(hass) -> None:
    """A backend without the ha-publish feature (None) is not filtered."""
    api = _ipm_api(
        plants=[
            {"key": "plant-1", "plant_name": "Tomato"},
            {"key": "plant-2", "plant_name": "Basil"},
        ]
    )
    api.async_get_ha_published_keys = AsyncMock(return_value=None)

    coord = KamerplanterIpmCoordinator(hass, _mock_entry(), api)
    result = await coord._async_update_data()

    assert {r["key"] for r in result} == {"plant-1", "plant-2"}


async def test_ipm_coordinator_empty_publish_list_exposes_nothing(hass) -> None:
    """Opt-in: an empty published list yields no records (strict)."""
    api = _ipm_api(plants=[{"key": "plant-1", "plant_name": "Tomato"}])
    api.async_get_ha_published_keys = AsyncMock(return_value=[])

    coord = KamerplanterIpmCoordinator(hass, _mock_entry(), api)
    result = await coord._async_update_data()

    assert result == []


async def test_ipm_coordinator_skips_removed_plants(hass) -> None:
    """Removed plants are not included in the IPM records."""
    api = _ipm_api(
        plants=[
            {"key": "plant-1", "plant_name": "Tomato"},
            {"key": "plant-2", "plant_name": "Old", "removed_on": "2026-01-01"},
        ]
    )

    coord = KamerplanterIpmCoordinator(hass, _mock_entry(), api)
    result = await coord._async_update_data()

    assert {r["key"] for r in result} == {"plant-1"}


async def test_ipm_coordinator_fires_alert_on_transition(hass) -> None:
    """Entering high pressure fires EVENT_IPM_ALERT exactly once per transition."""
    api = _ipm_api(
        inspections=[{"inspected_at": "2026-06-20", "pressure_level": "high"}]
    )
    coord = KamerplanterIpmCoordinator(hass, _mock_entry(), api)

    events = async_capture_events(hass, EVENT_IPM_ALERT)

    await coord._async_update_data()
    await hass.async_block_till_done()
    assert len(events) == 1
    assert events[0].data["plant_key"] == "plant-1"
    assert events[0].data["pressure_level"] == "high"

    # Still high on the next poll -> no duplicate alert.
    await coord._async_update_data()
    await hass.async_block_till_done()
    assert len(events) == 1


async def test_ipm_coordinator_no_alert_below_threshold(hass) -> None:
    """Low/medium pressure does not fire an alert."""
    api = _ipm_api(
        inspections=[{"inspected_at": "2026-06-20", "pressure_level": "medium"}]
    )
    coord = KamerplanterIpmCoordinator(hass, _mock_entry(), api)

    events = async_capture_events(hass, EVENT_IPM_ALERT)
    await coord._async_update_data()
    await hass.async_block_till_done()
    assert len(events) == 0


async def test_ipm_coordinator_auth_error(hass) -> None:
    """Auth errors surface as ConfigEntryAuthFailed."""
    from homeassistant.exceptions import ConfigEntryAuthFailed

    api = MagicMock(spec=KamerplanterApi)
    api.async_get_plants = AsyncMock(side_effect=KamerplanterAuthError("expired"))

    coord = KamerplanterIpmCoordinator(hass, _mock_entry(), api)
    with pytest.raises(ConfigEntryAuthFailed):
        await coord._async_update_data()


async def test_ipm_coordinator_connection_error(hass) -> None:
    """Connection errors surface as UpdateFailed."""
    from homeassistant.helpers.update_coordinator import UpdateFailed

    api = MagicMock(spec=KamerplanterApi)
    api.async_get_plants = AsyncMock(side_effect=KamerplanterConnectionError("down"))

    coord = KamerplanterIpmCoordinator(hass, _mock_entry(), api)
    with pytest.raises(UpdateFailed):
        await coord._async_update_data()
