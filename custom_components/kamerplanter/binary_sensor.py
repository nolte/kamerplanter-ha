"""Binary sensor entities for the Kamerplanter integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .coordinator import (
    KamerplanterAlertCoordinator,
    KamerplanterLocationCoordinator,
)
from .entity import (
    KamerplanterEntity,
    _slugify_key,
    location_device_info,
    plant_device_info,
    server_device_info,
)

PARALLEL_UPDATES = 0  # CoordinatorEntity — no own polling


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Kamerplanter binary sensor entities."""
    coordinators = entry.runtime_data.coordinators
    alert_coordinator: KamerplanterAlertCoordinator = coordinators["alerts"]
    plant_coordinator = coordinators["plants"]
    loc_coordinator: KamerplanterLocationCoordinator = coordinators["locations"]

    entities: list[BinarySensorEntity] = []

    # Plant attention sensors (derived from overdue tasks)
    if alert_coordinator.data and plant_coordinator.data:
        plant_lookup: dict[str, dict[str, Any]] = {
            p["key"]: p for p in plant_coordinator.data if not p.get("removed_on")
        }
        plant_keys_seen: set[str] = set()
        for alert in alert_coordinator.data:
            plant_key = alert.get("plant_key")
            if (
                plant_key
                and plant_key not in plant_keys_seen
                and plant_key in plant_lookup
            ):
                plant_keys_seen.add(plant_key)
                dev = plant_device_info(entry, plant_lookup[plant_key])
                entities.append(
                    PlantNeedsAttentionSensor(alert_coordinator, entry, plant_key, dev)
                )

    # Location needs-attention sensors
    if loc_coordinator.data:
        for loc in loc_coordinator.data:
            loc_key = loc.get("key") or loc.get("_key", "")
            if not loc_key:
                continue
            if (
                loc.get("_active_run_count", 0) > 0
                or loc.get("_active_plant_count", 0) > 0
            ):
                dev = location_device_info(entry, loc)
                entities.append(
                    LocationNeedsAttentionSensor(
                        alert_coordinator, loc_coordinator, entry, loc_key, dev
                    )
                )

    # Global sensor offline — under server device
    srv_dev = server_device_info(entry)
    entities.append(SensorOfflineSensor(alert_coordinator, entry, srv_dev))

    # Care overdue — true when at least one task is overdue (REQ-030)
    entities.append(CareOverdueSensor(alert_coordinator, entry, srv_dev))

    async_add_entities(entities)


class PlantNeedsAttentionSensor(KamerplanterEntity, RestoreEntity, BinarySensorEntity):
    """Binary sensor indicating a plant needs attention."""

    _attr_translation_key = "needs_attention"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(
        self,
        coordinator: KamerplanterAlertCoordinator,
        entry: ConfigEntry,
        plant_key: str,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(coordinator, entry.entry_id, device_info)
        self._plant_key = plant_key
        slug = _slugify_key(plant_key)
        self._attr_unique_id = f"{entry.entry_id}_kp_{slug}_needs_attention"

    @callback
    def _handle_coordinator_update(self) -> None:
        if self.coordinator.data:
            self._attr_is_on = any(
                a.get("plant_key") == self._plant_key for a in self.coordinator.data
            )
        else:
            self._attr_is_on = False
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last and last.state not in ("unknown", "unavailable", ""):
            self._attr_is_on = last.state == "on"
            self.async_write_ha_state()


class SensorOfflineSensor(KamerplanterEntity, RestoreEntity, BinarySensorEntity):
    """Binary sensor indicating sensor connectivity issues."""

    _attr_translation_key = "sensor_offline"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: KamerplanterAlertCoordinator,
        entry: ConfigEntry,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(coordinator, entry.entry_id, device_info)
        self._attr_unique_id = f"{entry.entry_id}_kp_sensor_offline"

    @callback
    def _handle_coordinator_update(self) -> None:
        if self.coordinator.data:
            self._attr_is_on = any(
                a.get("type") == "sensor_offline" for a in self.coordinator.data
            )
        else:
            self._attr_is_on = False
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last and last.state not in ("unknown", "unavailable", ""):
            self._attr_is_on = last.state == "on"
            self.async_write_ha_state()


class LocationNeedsAttentionSensor(
    KamerplanterEntity, RestoreEntity, BinarySensorEntity
):
    """Binary sensor indicating a location needs attention."""

    _attr_translation_key = "needs_attention"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(
        self,
        alert_coordinator: KamerplanterAlertCoordinator,
        loc_coordinator: KamerplanterLocationCoordinator,
        entry: ConfigEntry,
        location_key: str,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(alert_coordinator, entry.entry_id, device_info)
        self._location_key = location_key
        self._loc_coordinator = loc_coordinator
        slug = _slugify_key(location_key)
        self._attr_unique_id = f"{entry.entry_id}_kp_loc_{slug}_needs_attention"

    def _get_location_plant_keys(self) -> set[str]:
        """Get all plant keys associated with this location."""
        plant_keys: set[str] = set()
        if not self._loc_coordinator.data:
            return plant_keys
        for loc in self._loc_coordinator.data:
            key = loc.get("key") or loc.get("_key", "")
            if key != self._location_key:
                continue
            for plant in loc.get("_active_plants", []):
                pk = plant.get("key")
                if pk:
                    plant_keys.add(pk)
            break
        return plant_keys

    @callback
    def _handle_coordinator_update(self) -> None:
        if self.coordinator.data:
            plant_keys = self._get_location_plant_keys()
            self._attr_is_on = any(
                a.get("plant_key") in plant_keys
                or a.get("location_key") == self._location_key
                for a in self.coordinator.data
            )
        else:
            self._attr_is_on = False
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last and last.state not in ("unknown", "unavailable", ""):
            self._attr_is_on = last.state == "on"
            self.async_write_ha_state()


class CareOverdueSensor(KamerplanterEntity, RestoreEntity, BinarySensorEntity):
    """Binary sensor indicating at least one care task is overdue (REQ-030)."""

    _attr_translation_key = "care_overdue"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(
        self,
        coordinator: KamerplanterAlertCoordinator,
        entry: ConfigEntry,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(coordinator, entry.entry_id, device_info)
        self._attr_unique_id = f"{entry.entry_id}_kp_care_overdue"

    @callback
    def _handle_coordinator_update(self) -> None:
        if self.coordinator.data:
            self._attr_is_on = len(self.coordinator.data) > 0
            self._attr_extra_state_attributes = {
                "overdue_count": len(self.coordinator.data),
            }
        else:
            self._attr_is_on = False
            self._attr_extra_state_attributes = {"overdue_count": 0}
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last and last.state not in ("unknown", "unavailable", ""):
            self._attr_is_on = last.state == "on"
            self.async_write_ha_state()
