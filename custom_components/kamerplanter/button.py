"""Button entities for the Kamerplanter integration (HA-NFR-007)."""

from __future__ import annotations

from datetime import datetime, timezone

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import EVENT_DATA_REFRESHED
from .entity import server_device_info

PARALLEL_UPDATES = 1  # Serialize button presses


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Kamerplanter button entities."""
    async_add_entities([KamerplanterRefreshButton(hass, entry)])


class KamerplanterRefreshButton(ButtonEntity):
    """Button to trigger an immediate data refresh."""

    _attr_has_entity_name = True
    _attr_translation_key = "refresh_all"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_kp_refresh_all"
        self._attr_device_info = server_device_info(entry)

    async def async_press(self) -> None:
        """Handle the button press."""
        for coordinator in self._entry.runtime_data.coordinators.values():
            await coordinator.async_request_refresh()

        self.hass.bus.fire(
            EVENT_DATA_REFRESHED,
            {
                "entry_id": self._entry.entry_id,
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            },
        )
