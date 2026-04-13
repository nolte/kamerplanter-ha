"""Diagnostics for the Kamerplanter integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_API_KEY

TO_REDACT = {CONF_API_KEY, "password", "token"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = config_entry.runtime_data
    coordinators = data.coordinators

    return {
        "entry_data": async_redact_data(dict(config_entry.data), TO_REDACT),
        "entry_options": dict(config_entry.options),
        "plant_count": len(coordinators["plants"].data or []),
        "location_count": len(coordinators["locations"].data or []),
        "run_count": len(coordinators["runs"].data or []),
        "active_alerts": len(coordinators["alerts"].data or []),
        "pending_tasks": len(coordinators["tasks"].data or []),
        "coordinator_update_intervals": {
            name: coord.update_interval.total_seconds()
            for name, coord in coordinators.items()
        },
    }
