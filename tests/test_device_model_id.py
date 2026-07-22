"""Tests for stable ``model_id`` on device factories (issue #63).

The plant-card and houseplant-card editors filter their device picker by
``model_id`` so only Plant Instance / Planting Run devices are offered. The
human-readable ``model`` carries a variable suffix and cannot be filtered on
exactly, so the stable token lives in ``model_id``.
"""

from __future__ import annotations

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kamerplanter.const import DOMAIN
from custom_components.kamerplanter.entity import (
    location_device_info,
    plant_device_info,
    run_device_info,
    server_device_info,
    tank_device_info,
)


def _entry() -> MockConfigEntry:
    return MockConfigEntry(domain=DOMAIN, entry_id="test_entry")


def test_plant_device_has_stable_model_id() -> None:
    info = plant_device_info(_entry(), {"key": "p1", "instance_id": "DRACA-0616"})
    assert info["model_id"] == "plant_instance"
    # human-readable model still carries the variable suffix
    assert info["model"].startswith("Plant Instance")


def test_run_device_has_stable_model_id() -> None:
    info = run_device_info(_entry(), {"key": "r1", "run_type": "sowing"})
    assert info["model_id"] == "planting_run"
    assert info["model"].startswith("Planting Run")


def test_other_devices_have_no_plant_model_id() -> None:
    """Hub, location and tank must not carry the plant/run model_id tokens."""
    entry = _entry()
    for info in (
        server_device_info(entry),
        location_device_info(entry, {"key": "l1", "location_type_key": "greenhouse"}),
        tank_device_info(entry, {"key": "t1", "tank_type": "rain"}),
    ):
        assert info.get("model_id") not in ("plant_instance", "planting_run")
