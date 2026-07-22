"""Tests for the per-site frost-forecast binary sensor (issue #53).

Covers the state mapping (frost_warning True/False/None) and attribute
passthrough of ``SiteFrostForecastSensor`` without a full HA entity lifecycle.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant.components.binary_sensor import BinarySensorDeviceClass

from custom_components.kamerplanter.binary_sensor import SiteFrostForecastSensor
from custom_components.kamerplanter.entity import site_device_info


def _sensor(record: dict | None) -> SiteFrostForecastSensor:
    entry = MagicMock()
    entry.entry_id = "test"
    coordinator = MagicMock()
    coordinator.data = [record] if record is not None else []
    device_info = site_device_info(entry, {"key": "site-1", "name": "Garden"})
    sensor = SiteFrostForecastSensor(coordinator, entry, "site-1", device_info)
    # Bypass the HA state-machine write; we assert on the computed attributes.
    sensor.async_write_ha_state = MagicMock()
    return sensor


def test_frost_warning_true_is_on() -> None:
    sensor = _sensor(
        {
            "key": "site-1",
            "frost_warning": True,
            "min_temperature": -1.0,
            "expected_date": "2026-11-20",
            "source": "dwd",
        }
    )
    sensor._handle_coordinator_update()
    assert sensor.is_on is True
    assert sensor.extra_state_attributes["min_temperature"] == -1.0
    assert sensor.extra_state_attributes["expected_date"] == "2026-11-20"
    assert sensor.extra_state_attributes["source"] == "dwd"


def test_frost_warning_false_is_off() -> None:
    sensor = _sensor({"key": "site-1", "frost_warning": False})
    sensor._handle_coordinator_update()
    assert sensor.is_on is False


def test_frost_warning_none_is_unknown() -> None:
    """No forecast source (None) maps to unknown (is_on None), not off."""
    sensor = _sensor({"key": "site-1", "frost_warning": None})
    sensor._handle_coordinator_update()
    assert sensor.is_on is None


def test_frost_no_record_is_unknown() -> None:
    """A site missing from coordinator data yields unknown, not a crash."""
    sensor = _sensor(None)
    sensor._handle_coordinator_update()
    assert sensor.is_on is None


def test_frost_sensor_metadata() -> None:
    sensor = _sensor({"key": "site-1", "frost_warning": False})
    assert sensor.device_class == BinarySensorDeviceClass.COLD
    assert sensor.translation_key == "frost_forecast"
    assert sensor.unique_id == "test_kp_site_site_1_frost_forecast"
