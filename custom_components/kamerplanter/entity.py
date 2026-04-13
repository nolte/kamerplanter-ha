"""Base entity for the Kamerplanter integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN


class KamerplanterEntity(CoordinatorEntity):
    """Base class for all Kamerplanter entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry_id: str,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._attr_device_info = device_info
        self._entry_id = entry_id


# --- DeviceInfo Factory Functions ---


def server_device_info(entry: ConfigEntry) -> DeviceInfo:
    """Create DeviceInfo for the Kamerplanter server (hub device)."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="Kamerplanter",
        manufacturer="Kamerplanter",
        model="Plant Management Server",
    )


def plant_device_info(entry: ConfigEntry, plant: dict[str, Any]) -> DeviceInfo:
    """Create DeviceInfo for a plant instance (child device)."""
    key = plant["key"]
    name = plant.get("plant_name") or plant.get("instance_id", key)
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_plant_{key}")},
        name=name,
        manufacturer="Kamerplanter",
        model="Plant Instance",
        via_device=(DOMAIN, entry.entry_id),
    )


def run_device_info(entry: ConfigEntry, run: dict[str, Any]) -> DeviceInfo:
    """Create DeviceInfo for a planting run (child device)."""
    key = run["key"]
    name = run.get("name", key)
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_run_{key}")},
        name=name,
        manufacturer="Kamerplanter",
        model=f"Planting Run ({run.get('run_type', 'unknown')})",
        via_device=(DOMAIN, entry.entry_id),
    )


def location_device_info(entry: ConfigEntry, loc: dict[str, Any]) -> DeviceInfo:
    """Create DeviceInfo for a location (child device)."""
    loc_key = loc.get("key") or loc.get("_key", "")
    name = loc.get("name", loc_key)
    loc_type = loc.get("location_type_key", "location")
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_location_{loc_key}")},
        name=name,
        manufacturer="Kamerplanter",
        model=f"Location ({loc_type})",
        via_device=(DOMAIN, entry.entry_id),
    )


def tank_device_info(
    entry: ConfigEntry,
    tank: dict[str, Any],
    loc: dict[str, Any] | None = None,
) -> DeviceInfo:
    """Create DeviceInfo for a tank (child device)."""
    key = tank.get("key", "")
    name = tank.get("name", key)
    tank_type = tank.get("tank_type", "unknown")
    volume = tank.get("volume_liters")
    model = f"Tank ({tank_type})"
    if volume:
        model += f" {volume}L"
    loc_name = loc.get("name", "") if loc else ""
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_tank_{key}")},
        name=name,
        manufacturer="Kamerplanter",
        model=model,
        suggested_area=loc_name or None,
        via_device=(DOMAIN, entry.entry_id),
    )


def _slugify_key(key: str) -> str:
    """Convert ArangoDB key to entity-id-safe slug."""
    return key.replace("-", "_").lower()
