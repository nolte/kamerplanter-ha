"""Tests for orphaned-device cleanup when elements are un-published."""

from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kamerplanter import (
    KamerplanterRuntimeData,
    _async_cleanup_orphaned_devices,
)
from custom_components.kamerplanter.const import DOMAIN


def _coord(data, success: bool = True) -> MagicMock:
    coord = MagicMock()
    coord.last_update_success = success
    coord.data = data
    return coord


def _runtime(entry, **coords) -> None:
    entry.runtime_data = KamerplanterRuntimeData(
        api=MagicMock(),
        coordinators=coords,
    )


def _mk_device(dev_reg, entry, suffix: str):
    ident = (
        (DOMAIN, f"{entry.entry_id}_{suffix}") if suffix else (DOMAIN, entry.entry_id)
    )
    return dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={ident}
    )


async def test_cleanup_removes_unpublished_plant(hass) -> None:
    """A plant no longer in coordinator data has its device removed."""
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    dev_reg = dr.async_get(hass)

    server = _mk_device(dev_reg, entry, "")
    keep = _mk_device(dev_reg, entry, "plant_plant-1")
    drop = _mk_device(dev_reg, entry, "plant_plant-2")

    _runtime(
        entry,
        plants=_coord([{"key": "plant-1"}]),
        locations=_coord([]),
        runs=_coord([]),
    )

    _async_cleanup_orphaned_devices(hass, entry)

    assert dev_reg.async_get(drop.id) is None
    assert dev_reg.async_get(keep.id) is not None
    assert dev_reg.async_get(server.id) is not None


async def test_cleanup_removes_unpublished_location_and_tank(hass) -> None:
    """Locations/tanks dropping out of data are pruned; published ones kept."""
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    dev_reg = dr.async_get(hass)

    keep_loc = _mk_device(dev_reg, entry, "location_loc-1")
    keep_tank = _mk_device(dev_reg, entry, "tank_tank-1")
    drop_loc = _mk_device(dev_reg, entry, "location_loc-2")
    drop_tank = _mk_device(dev_reg, entry, "tank_tank-2")

    _runtime(
        entry,
        plants=_coord([]),
        locations=_coord([{"key": "loc-1", "_tanks": [{"key": "tank-1"}]}]),
        runs=_coord([]),
    )

    _async_cleanup_orphaned_devices(hass, entry)

    assert dev_reg.async_get(keep_loc.id) is not None
    assert dev_reg.async_get(keep_tank.id) is not None
    assert dev_reg.async_get(drop_loc.id) is None
    assert dev_reg.async_get(drop_tank.id) is None


async def test_cleanup_skips_on_failed_update(hass) -> None:
    """A failed coordinator update aborts the pass — nothing is removed."""
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    dev_reg = dr.async_get(hass)

    dev = _mk_device(dev_reg, entry, "plant_plant-2")

    _runtime(
        entry,
        plants=_coord([{"key": "plant-1"}], success=False),  # backend hiccup
        locations=_coord([]),
        runs=_coord([]),
    )

    _async_cleanup_orphaned_devices(hass, entry)

    # plant-2 would be orphaned, but the failed update must prevent removal.
    assert dev_reg.async_get(dev.id) is not None


async def test_cleanup_keeps_completed_run_out(hass) -> None:
    """Completed/cancelled runs are treated as orphaned."""
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    dev_reg = dr.async_get(hass)

    active = _mk_device(dev_reg, entry, "run_run-1")
    done = _mk_device(dev_reg, entry, "run_run-2")

    _runtime(
        entry,
        plants=_coord([]),
        locations=_coord([]),
        runs=_coord(
            [
                {"key": "run-1", "status": "active"},
                {"key": "run-2", "status": "completed"},
            ]
        ),
    )

    _async_cleanup_orphaned_devices(hass, entry)

    assert dev_reg.async_get(active.id) is not None
    assert dev_reg.async_get(done.id) is None
