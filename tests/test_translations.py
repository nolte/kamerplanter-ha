"""Translation key parity across strings.json, en.json and de.json (WP-11)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_BASE = Path(__file__).resolve().parent.parent / "custom_components" / "kamerplanter"


def _load(name: str) -> dict[str, Any]:
    return json.loads((_BASE / name).read_text())


def _keys(obj: Any, prefix: str = "") -> set[str]:
    """Collect the full set of nested dict key paths."""
    keys: set[str] = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            path = f"{prefix}.{key}" if prefix else key
            keys.add(path)
            keys |= _keys(value, path)
    return keys


def test_en_matches_strings() -> None:
    """translations/en.json mirrors strings.json exactly."""
    assert _keys(_load("translations/en.json")) == _keys(_load("strings.json"))


def test_de_matches_strings() -> None:
    """translations/de.json mirrors strings.json exactly."""
    assert _keys(_load("translations/de.json")) == _keys(_load("strings.json"))


def test_config_abort_keys_present() -> None:
    """The behandelbare abort reasons carry human-readable strings."""
    abort = _load("strings.json")["config"]["abort"]
    for key in ("cannot_connect", "no_tenants", "reconfigure_successful"):
        assert key in abort


def test_config_unknown_error_present() -> None:
    """The generic fallback error is translatable."""
    assert "unknown" in _load("strings.json")["config"]["error"]


def test_service_field_translations_complete() -> None:
    """fill_tank / water_channel expose all their service fields for translation."""
    services = _load("strings.json")["services"]
    fill_fields = set(services["fill_tank"]["fields"])
    assert {"tank_key", "measured_ec_ms", "measured_ph", "notes"} <= fill_fields
    water_fields = set(services["water_channel"]["fields"])
    assert {
        "plant_key",
        "channel_id",
        "application_method",
        "measured_ec_ms",
        "measured_ph",
        "notes",
    } <= water_fields


def test_task_service_icons_present() -> None:
    """The three task services have dedicated icons."""
    icons = _load("icons.json")["services"]
    for key in ("start_task", "complete_task", "skip_task"):
        assert key in icons and "service" in icons[key]
