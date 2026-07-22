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
from .helpers import plant_display_name, plant_instance_code


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
    """Create DeviceInfo for a plant instance (child device).

    The device ``name`` is the human-readable plant label (issue #57); the code
    slug is retained in ``model`` for disambiguation.
    """
    key = plant["key"]
    name = plant_display_name(plant)
    code = plant_instance_code(plant)
    model = f"Plant Instance ({code})" if code else "Plant Instance"
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_plant_{key}")},
        name=name,
        manufacturer="Kamerplanter",
        model=model,
        model_id="plant_instance",
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
        model_id="planting_run",
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


def site_device_info(entry: ConfigEntry, site: dict[str, Any]) -> DeviceInfo:
    """Create DeviceInfo for a site (child device).

    Sites group per-site entities such as the proactive frost-forecast binary
    sensor (issue #53). A dedicated device per site keeps multi-site setups
    cleanly separated and consistent with the other domain devices.
    """
    site_key = site.get("key") or site.get("_key", "")
    name = site.get("name", site_key)
    site_type = site.get("type", "site")
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_site_{site_key}")},
        name=name,
        manufacturer="Kamerplanter",
        model=f"Site ({site_type})",
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


def find_by_key(data: list[dict[str, Any]] | None, key: str) -> dict[str, Any] | None:
    """Return the coordinator-data item whose ``key`` (or ``_key``) matches.

    The ``or _key`` fallback covers location records that only carry ``_key``;
    for plant/run/IPM records ``key`` is always set, so the fallback is inert.
    """
    if not data:
        return None
    for item in data:
        if (item.get("key") or item.get("_key", "")) == key:
            return item
    return None
