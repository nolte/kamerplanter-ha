"""Tests for resource-bound sensor availability (WP-10)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from custom_components.kamerplanter.sensor import PlantPhaseSensor, TankVolumeSensor


def _entry() -> MagicMock:
    entry = MagicMock()
    entry.entry_id = "e1"
    return entry


def _coord(data: list[dict[str, Any]]) -> MagicMock:
    coord = MagicMock()
    coord.last_update_success = True
    coord.data = data
    return coord


def test_plant_sensor_available_when_resource_present() -> None:
    """A plant sensor is available while its plant is in the coordinator data."""
    coord = _coord([{"key": "plant-1", "current_phase": "vegetative"}])
    sensor = PlantPhaseSensor(coord, _entry(), "plant-1", MagicMock())
    assert sensor.available is True


def test_plant_sensor_unavailable_when_resource_gone() -> None:
    """A plant sensor becomes unavailable when its plant is archived/unpublished."""
    coord = _coord([])
    sensor = PlantPhaseSensor(coord, _entry(), "plant-1", MagicMock())
    assert sensor.available is False


def test_plant_sensor_unavailable_on_coordinator_failure() -> None:
    """A failed coordinator update marks the sensor unavailable regardless of data."""
    coord = _coord([{"key": "plant-1"}])
    coord.last_update_success = False
    sensor = PlantPhaseSensor(coord, _entry(), "plant-1", MagicMock())
    assert sensor.available is False


def test_tank_volume_sensor_available_uses_tank_lookup() -> None:
    """The standalone tank sensor resolves availability via the tank, not a location."""
    coord = _coord(
        [{"key": "loc-1", "_tanks": [{"key": "tank-9", "volume_liters": 50}]}]
    )
    sensor = TankVolumeSensor(coord, _entry(), "tank-9", "loc-1", MagicMock())
    assert sensor.available is True


def test_tank_volume_sensor_unavailable_when_tank_gone() -> None:
    """The tank sensor becomes unavailable once the tank drops out of the data."""
    coord = _coord([{"key": "loc-1", "_tanks": []}])
    sensor = TankVolumeSensor(coord, _entry(), "tank-9", "loc-1", MagicMock())
    assert sensor.available is False
