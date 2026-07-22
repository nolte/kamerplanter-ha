"""Tests for standalone tank devices decoupled from location publishing.

Regression coverage for issue #59: a tank marked "publish to HA" must surface
as its own device with entities even when its parent location is *not*
published. Previously the location coordinator only attached tanks to surviving
(published) locations, so publishing only the tank left it invisible.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import Entity
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kamerplanter import (
    KamerplanterRuntimeData,
    _async_cleanup_orphaned_devices,
)
from custom_components.kamerplanter.api import KamerplanterApi
from custom_components.kamerplanter.const import DOMAIN, TANK_HOLDER_MARKER
from custom_components.kamerplanter.coordinator import (
    KamerplanterLocationCoordinator,
)
from custom_components.kamerplanter.sensor import async_setup_entry as sensor_setup


def _loc_api(
    locations: list[dict],
    tanks: list[dict],
    published: dict[str, set[str] | None],
) -> MagicMock:
    """Build a mock API for the location coordinator.

    ``published`` maps ``entity_type`` ("location"/"tank"/...) to its published
    key set (or ``None`` for "feature unavailable"), mirroring the backend's
    per-entity HA-publish endpoint.
    """
    api = MagicMock(spec=KamerplanterApi)
    api.async_get_all_locations = AsyncMock(return_value=locations)
    api.async_get_tanks = AsyncMock(return_value=tanks)
    api.async_get_fertilizers = AsyncMock(return_value=[])
    api.async_get_runs_by_location = AsyncMock(return_value=[])
    api.async_get_plant_instances_by_location = AsyncMock(return_value=[])
    api.async_get_tank_latest_fill = AsyncMock(return_value=None)
    api.async_get_tank_sensors = AsyncMock(return_value=[])

    async def _published(entity_type: str) -> set[str] | None:
        return published.get(entity_type)

    api.async_get_ha_published_keys = AsyncMock(side_effect=_published)
    return api


async def _run_location_coordinator(hass, api: MagicMock) -> list[dict]:
    """Run a location coordinator update with static data pre-loaded."""
    entry = MagicMock()
    entry.options = {}
    entry.entry_id = "test"

    coord = KamerplanterLocationCoordinator(hass, entry, api)
    await coord._async_setup()  # populates self._all_tanks from async_get_tanks
    return await coord._async_update_data()


def _find_holder(data: list[dict]) -> dict | None:
    return next((loc for loc in data if loc.get(TANK_HOLDER_MARKER)), None)


async def test_published_tank_with_unpublished_location_surfaces(hass) -> None:
    """Core case: only the tank is published, its location is not.

    The tank must still appear (on the synthetic holder) so it can become a
    standalone device.
    """
    api = _loc_api(
        locations=[{"key": "loc-hidden", "name": "Hidden Tent"}],
        tanks=[
            {
                "key": "tank-1",
                "name": "60L Tank",
                "volume_liters": 60,
                "location_key": "loc-hidden",
            }
        ],
        published={"location": set(), "tank": {"tank-1"}},
    )

    data = await _run_location_coordinator(hass, api)

    # The unpublished location itself is filtered out.
    assert all(loc.get("key") != "loc-hidden" for loc in data)

    holder = _find_holder(data)
    assert holder is not None
    assert {t["key"] for t in holder["_tanks"]} == {"tank-1"}
    # Tank is enriched even without a published location.
    tank = holder["_tanks"][0]
    assert "_latest_fill" in tank
    assert "_ha_sensors" in tank


async def test_published_tank_without_location_key_surfaces(hass) -> None:
    """A published tank carrying no location_key still surfaces on the holder."""
    api = _loc_api(
        locations=[],
        tanks=[{"key": "tank-x", "name": "Floating Tank", "volume_liters": 25}],
        published={"location": set(), "tank": {"tank-x"}},
    )

    data = await _run_location_coordinator(hass, api)

    holder = _find_holder(data)
    assert holder is not None
    assert {t["key"] for t in holder["_tanks"]} == {"tank-x"}


async def test_tank_under_published_location_no_holder(hass) -> None:
    """Tank + published location: attached to the location, no holder, no dupes."""
    api = _loc_api(
        locations=[{"key": "loc-1", "name": "Tent 1"}],
        tanks=[
            {
                "key": "tank-1",
                "name": "60L Tank",
                "volume_liters": 60,
                "location_key": "loc-1",
            }
        ],
        published={"location": {"loc-1"}, "tank": {"tank-1"}},
    )

    data = await _run_location_coordinator(hass, api)

    assert _find_holder(data) is None
    loc = next(loc for loc in data if loc.get("key") == "loc-1")
    assert {t["key"] for t in loc["_tanks"]} == {"tank-1"}


async def test_empty_tank_publish_set_hides_all_tanks(hass) -> None:
    """Strict opt-in: an empty tank-published set exposes no tanks and no holder."""
    api = _loc_api(
        locations=[{"key": "loc-1", "name": "Tent 1"}],
        tanks=[
            {
                "key": "tank-1",
                "volume_liters": 60,
                "location_key": "loc-1",
            }
        ],
        published={"location": None, "tank": set()},
    )

    data = await _run_location_coordinator(hass, api)

    assert _find_holder(data) is None
    for loc in data:
        assert loc.get("_tanks") == []


async def test_no_publish_feature_keeps_all_tanks(hass) -> None:
    """A backend without the publish feature (None) exposes every tank."""
    api = _loc_api(
        locations=[{"key": "loc-1", "name": "Tent 1"}],
        tanks=[
            {"key": "tank-1", "volume_liters": 60, "location_key": "loc-1"},
            {"key": "tank-2", "volume_liters": 20, "location_key": "loc-gone"},
        ],
        published={"location": None, "tank": None},
    )

    data = await _run_location_coordinator(hass, api)

    loc = next(loc for loc in data if loc.get("key") == "loc-1")
    assert {t["key"] for t in loc["_tanks"]} == {"tank-1"}
    holder = _find_holder(data)
    assert holder is not None
    assert {t["key"] for t in holder["_tanks"]} == {"tank-2"}


# --- Sensor-level: the holder produces real tank devices + entities ---


def _coord(data: list[dict]) -> MagicMock:
    coord = MagicMock()
    coord.last_update_success = True
    coord.data = data
    return coord


async def test_sensor_setup_creates_orphan_tank_device(hass) -> None:
    """A published tank on the holder yields Info + Volume entities on a device."""
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)

    holder = {
        TANK_HOLDER_MARKER: True,
        "_tanks": [
            {
                "key": "tank-9",
                "name": "Orphan Tank",
                "volume_liters": 42,
                "location_key": "loc-hidden",
                "_latest_fill": None,
                "_ha_sensors": [],
            }
        ],
    }
    empty = _coord([])
    entry.runtime_data = KamerplanterRuntimeData(
        api=MagicMock(),
        coordinators={
            "plants": empty,
            "runs": empty,
            "locations": _coord([holder]),
            "tasks": empty,
            "alerts": empty,
            "ipm": empty,
        },
    )

    added: list[Entity] = []

    def _add(entities, update_before_add: bool = False) -> None:
        added.extend(entities)

    await sensor_setup(hass, entry, _add)

    tank_entities = [
        e
        for e in added
        if e.__class__.__name__ in ("TankInfoSensor", "TankVolumeSensor")
    ]
    assert {e.__class__.__name__ for e in tank_entities} == {
        "TankInfoSensor",
        "TankVolumeSensor",
    }
    expected = (DOMAIN, f"{entry.entry_id}_tank_tank-9")
    for entity in tank_entities:
        assert expected in entity.device_info["identifiers"]


# --- Device cleanup: orphan tank device is valid, not pruned ---


def _mk_device(dev_reg, entry, suffix: str):
    return dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, f"{entry.entry_id}_{suffix}")},
    )


async def test_cleanup_keeps_orphan_tank_device(hass) -> None:
    """The orphan tank device (carried on the holder) survives cleanup."""
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    dev_reg = dr.async_get(hass)

    keep_tank = _mk_device(dev_reg, entry, "tank_tank-9")
    drop_tank = _mk_device(dev_reg, entry, "tank_tank-stale")

    holder = {TANK_HOLDER_MARKER: True, "_tanks": [{"key": "tank-9"}]}
    entry.runtime_data = KamerplanterRuntimeData(
        api=MagicMock(),
        coordinators={
            "plants": _coord([]),
            "locations": _coord([holder]),
            "runs": _coord([]),
        },
    )

    _async_cleanup_orphaned_devices(hass, entry)

    assert dev_reg.async_get(keep_tank.id) is not None
    assert dev_reg.async_get(drop_tank.id) is None
