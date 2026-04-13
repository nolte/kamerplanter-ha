"""The Kamerplanter integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from aiohttp import ClientSession
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import KamerplanterApi
from .const import (
    CONF_API_KEY,
    CONF_TENANT_SLUG,
    DOMAIN,
    PLATFORMS,
    SERVICE_CLEAR_CACHE,
    SERVICE_CONFIRM_CARE,
    SERVICE_FILL_TANK,
    SERVICE_REFRESH,
    SERVICE_WATER_CHANNEL,
)
from .coordinator import (
    KamerplanterAlertCoordinator,
    KamerplanterLocationCoordinator,
    KamerplanterPlantCoordinator,
    KamerplanterRunCoordinator,
    KamerplanterTaskCoordinator,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class KamerplanterRuntimeData:
    """Runtime data stored on the config entry."""

    api: KamerplanterApi
    coordinators: dict[str, DataUpdateCoordinator]


type KamerplanterConfigEntry = ConfigEntry[KamerplanterRuntimeData]


async def async_setup_entry(
    hass: HomeAssistant, entry: KamerplanterConfigEntry
) -> bool:
    """Set up Kamerplanter from a config entry."""
    session: ClientSession = async_get_clientsession(hass)

    api = KamerplanterApi(
        base_url=entry.data[CONF_URL],
        session=session,
        api_key=entry.data.get(CONF_API_KEY),
        tenant_slug=entry.data.get(CONF_TENANT_SLUG),
    )

    coordinators: dict[str, DataUpdateCoordinator] = {
        "plants": KamerplanterPlantCoordinator(hass, entry, api),
        "locations": KamerplanterLocationCoordinator(hass, entry, api),
        "runs": KamerplanterRunCoordinator(hass, entry, api),
        "alerts": KamerplanterAlertCoordinator(hass, entry, api),
        "tasks": KamerplanterTaskCoordinator(hass, entry, api),
    }

    # First refresh all coordinators
    for coordinator in coordinators.values():
        await coordinator.async_config_entry_first_refresh()

    # Store runtime_data on the config entry (HA best practice)
    entry.runtime_data = KamerplanterRuntimeData(api=api, coordinators=coordinators)

    # Register services (HA-NFR-002: idempotency guard)
    if not hass.services.has_service(DOMAIN, SERVICE_REFRESH):
        await _async_register_services(hass)

    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Auto-register Lovelace cards and assets from www/ subdirectory
    www_dir = Path(__file__).parent / "www"
    if www_dir.is_dir():
        from homeassistant.components.http import StaticPathConfig

        js_files = await hass.async_add_executor_job(lambda: list(www_dir.glob("*.js")))
        paths = [
            StaticPathConfig(f"/{DOMAIN}/{js_file.name}", str(js_file), True)
            for js_file in js_files
        ]

        # Register Kami phase SVGs under /local/kami/ so cards can reference them
        kami_dir = www_dir / "kami"
        if await hass.async_add_executor_job(kami_dir.is_dir):
            paths.append(StaticPathConfig("/local/kami", str(kami_dir), True))

        if paths:
            # On reload, routes are already registered — filter out existing ones
            registered = {
                r.get_info().get("path", "")
                for r in hass.http.app.router.routes()
                if hasattr(r, "get_info")
            }
            new_paths = [p for p in paths if p.url_path not in registered]
            if new_paths:
                await hass.http.async_register_static_paths(new_paths)
                for p in new_paths:
                    _LOGGER.debug("Registered static path: %s", p.url_path)

        # Register as Lovelace resources so cards appear in the card picker
        await _async_register_lovelace_resources(hass, js_files)

    return True


async def _async_register_lovelace_resources(
    hass: HomeAssistant, js_files: list[Path]
) -> None:
    """Register JS files as Lovelace resources (idempotent)."""
    try:
        from homeassistant.components.lovelace import (
            DOMAIN as LOVELACE_DOMAIN,
        )
        from homeassistant.components.lovelace.resources import (
            ResourceStorageCollection,
        )

        lovelace_data = hass.data.get(LOVELACE_DOMAIN)
        if lovelace_data is None:
            return
        resources: ResourceStorageCollection | None = getattr(
            lovelace_data, "resources", None
        )
        if resources is None:
            return

        # Ensure storage is loaded
        if not resources.loaded:
            await resources.async_load()

        existing_urls = {r["url"] for r in resources.async_items()}

        for js_file in js_files:
            url = f"/{DOMAIN}/{js_file.name}"
            if url not in existing_urls:
                await resources.async_create_item({"res_type": "module", "url": url})
                _LOGGER.info("Registered Lovelace resource: %s", url)
    except Exception:
        _LOGGER.debug("Could not auto-register Lovelace resources", exc_info=True)


async def async_unload_entry(
    hass: HomeAssistant, entry: KamerplanterConfigEntry
) -> bool:
    """Unload a config entry."""
    # runtime_data is automatically cleaned up by HA
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_register_services(hass: HomeAssistant) -> None:
    """Register Kamerplanter services."""

    def _get_runtime_data(entry_id: str = "") -> KamerplanterRuntimeData | None:
        """Get runtime_data from the first (or targeted) config entry."""
        entries = [
            e
            for e in hass.config_entries.async_entries(DOMAIN)
            if not entry_id or e.entry_id == entry_id
        ]
        if entries and hasattr(entries[0], "runtime_data"):
            return entries[0].runtime_data
        return None

    async def handle_refresh(call: ServiceCall) -> None:
        target_id = call.data.get("entry_id", "")
        entries = [
            e
            for e in hass.config_entries.async_entries(DOMAIN)
            if not target_id or e.entry_id == target_id
        ]
        for entry in entries:
            if hasattr(entry, "runtime_data"):
                for coordinator in entry.runtime_data.coordinators.values():
                    await coordinator.async_request_refresh()

    async def handle_clear_cache(call: ServiceCall) -> None:
        target_id = call.data.get("entry_id", "")
        entries = [
            e
            for e in hass.config_entries.async_entries(DOMAIN)
            if not target_id or e.entry_id == target_id
        ]
        for entry in entries:
            if hasattr(entry, "runtime_data"):
                for coordinator in entry.runtime_data.coordinators.values():
                    coordinator.data = None
                    await coordinator.async_request_refresh()

    # Known suffixes for tank entities (used to extract tank_key from entity_id)
    _TANK_ENTITY_SUFFIXES = (
        "_info",
        "_volume",
        "_fill_level",
        "_ec",
        "_ph",
        "_water_temp",
        "_solution_age_days",
        "_alert_active",
    )

    def _resolve_tank_key(call_data: dict) -> str | None:
        """Resolve tank_key from entity_id or direct tank_key."""
        if "entity_id" in call_data:
            entity_id = str(call_data["entity_id"])

            # Strategy 1: Read tank_key from state attributes
            state = hass.states.get(entity_id)
            if state and state.attributes.get("tank_key"):
                _LOGGER.debug("Resolved tank_key from state attributes")
                return str(state.attributes["tank_key"])

            # Strategy 2: Parse from entity_id pattern
            entity_name = entity_id.split(".", 1)[-1]
            if entity_name.startswith("kp_"):
                rest = entity_name[3:]
                if rest.startswith("tank_"):
                    rest = rest[5:]
                for suffix in _TANK_ENTITY_SUFFIXES:
                    if rest.endswith(suffix):
                        tank_key = rest[: -len(suffix)]
                        _LOGGER.debug(
                            "Resolved tank_key '%s' from entity_id pattern", tank_key
                        )
                        return tank_key

            _LOGGER.error("Could not resolve tank_key from entity_id %s", entity_id)
            return None

        if "tank_key" in call_data:
            return str(call_data["tank_key"])

        return None

    async def handle_fill_tank(call: ServiceCall) -> None:
        """Handle the fill_tank service call."""
        _LOGGER.debug(
            "fill_tank call.data keys: %s, values: %s",
            list(call.data.keys()),
            dict(call.data),
        )
        tank_key = _resolve_tank_key(dict(call.data))
        if not tank_key:
            _LOGGER.error(
                "No tank_key or entity_id provided. Received data: %s",
                dict(call.data),
            )
            return
        fill_type = call.data.get("fill_type", "full_change")

        # Find the API instance from runtime_data
        runtime_data = _get_runtime_data()
        if not runtime_data:
            _LOGGER.error("No Kamerplanter instance found")
            return

        api = runtime_data.api

        # Fetch tank details for default volume
        tanks = await api.async_get_tanks()
        tank = next((t for t in tanks if t.get("key") == tank_key), None)
        if not tank:
            _LOGGER.error("Tank %s not found", tank_key)
            return

        volume = call.data.get("volume_liters") or tank.get("volume_liters", 0)

        # Resolve current dosages from the location coordinator
        fertilizers_used: list[dict[str, object]] = []
        loc_coord = runtime_data.coordinators.get("locations")
        if loc_coord and loc_coord.data:
            tank_location_key = tank.get("location_key")
            for loc in loc_coord.data:
                loc_key = loc.get("key") or loc.get("_key", "")
                if loc_key != tank_location_key:
                    continue
                run = loc.get("_primary_run")
                if not run:
                    break
                current_entries = run.get(
                    "_current_phase_entries", run.get("_phase_entries", [])
                )
                for pe in current_entries:
                    for channel in pe.get("delivery_channels", []):
                        ch_label = channel.get("label", "")
                        tank_name = tank.get("name", "")
                        tank_vol = str(int(tank.get("volume_liters", 0)))
                        if (
                            tank_name.lower() in ch_label.lower()
                            or f"{tank_vol}l" in ch_label.lower().replace(" ", "")
                            or f"{tank_vol} l" in ch_label.lower()
                        ):
                            for dosage in channel.get("fertilizer_dosages", []):
                                ml = dosage.get("ml_per_liter")
                                if ml is not None and ml > 0:
                                    fertilizers_used.append(
                                        {
                                            "product_key": dosage.get("fertilizer_key"),
                                            "product_name": dosage.get(
                                                "product_name",
                                                dosage.get("fertilizer_key", "unknown"),
                                            ),
                                            "ml_per_liter": ml,
                                        }
                                    )
                break

        # Build fill event payload
        payload: dict[str, object] = {
            "fill_type": fill_type,
            "volume_liters": volume,
            "fertilizers_used": fertilizers_used,
            "performed_by": "home_assistant",
        }
        if call.data.get("measured_ec_ms") is not None:
            payload["measured_ec_ms"] = call.data["measured_ec_ms"]
        if call.data.get("measured_ph") is not None:
            payload["measured_ph"] = call.data["measured_ph"]
        if call.data.get("notes"):
            payload["notes"] = call.data["notes"]

        _LOGGER.info(
            "Filling tank %s (%s): %.1fL, %d fertilizers",
            tank_key,
            fill_type,
            volume,
            len(fertilizers_used),
        )

        try:
            result = await api.async_fill_tank(tank_key, payload)
            _LOGGER.info(
                "Tank fill recorded: %s", result.get("fill_event", {}).get("key")
            )

            # Refresh coordinators to reflect new state
            for coordinator in runtime_data.coordinators.values():
                await coordinator.async_request_refresh()
        except Exception:
            _LOGGER.exception("Failed to fill tank %s", tank_key)

    # Known suffixes for plant channel entities
    _CHANNEL_SUFFIX = "_mix"

    def _resolve_plant_channel(call_data: dict) -> tuple[str | None, str | None]:
        """Resolve plant_key and channel_id from entity_id or direct parameters."""
        if "entity_id" in call_data:
            entity_id = str(call_data["entity_id"])

            # Strategy 1: Read from state attributes
            state = hass.states.get(entity_id)
            if state:
                attrs = state.attributes or {}
                if attrs.get("plant_key") and attrs.get("channel_id"):
                    _LOGGER.debug("Resolved plant/channel from state attributes")
                    return str(attrs["plant_key"]), str(attrs["channel_id"])

            # Strategy 2: Parse from entity_id pattern
            entity_name = entity_id.split(".", 1)[-1]
            if entity_name.startswith("kp_") and entity_name.endswith(_CHANNEL_SUFFIX):
                rest = entity_name[3 : -len(_CHANNEL_SUFFIX)]
                for entry in hass.config_entries.async_entries(DOMAIN):
                    if not hasattr(entry, "runtime_data"):
                        continue
                    plant_coord = entry.runtime_data.coordinators.get("plants")
                    if plant_coord and plant_coord.data:
                        for plant in plant_coord.data:
                            pk = plant.get("key", "")
                            slug = pk.replace("-", "_").lower()
                            if rest.startswith(slug + "_"):
                                channel_slug = rest[len(slug) + 1 :]
                                dosage_data = plant.get("_current_dosages")
                                if dosage_data and isinstance(dosage_data, dict):
                                    for ch in dosage_data.get("channels", []):
                                        ch_id = ch.get("channel_id", "")
                                        if _slugify_label(ch_id) == channel_slug:
                                            _LOGGER.debug(
                                                "Resolved plant_key='%s', channel_id='%s' from entity_id",
                                                pk,
                                                ch_id,
                                            )
                                            return pk, ch_id

                _LOGGER.error(
                    "Could not resolve plant/channel from entity_id %s", entity_id
                )
                return None, None

        plant_key = call_data.get("plant_key")
        channel_id = call_data.get("channel_id")
        if plant_key:
            return str(plant_key), str(channel_id) if channel_id else None
        return None, None

    def _slugify_label(text: str) -> str:
        """Slugify a label for entity ID matching (simplified)."""
        import re
        import unicodedata

        text = unicodedata.normalize("NFKD", text)
        text = text.encode("ascii", "ignore").decode("ascii")
        text = re.sub(r"[^a-z0-9]+", "_", text.lower())
        return text.strip("_")

    async def handle_water_channel(call: ServiceCall) -> None:
        """Handle the water_channel service call."""
        _LOGGER.debug(
            "water_channel call.data keys: %s, values: %s",
            list(call.data.keys()),
            dict(call.data),
        )
        plant_key, channel_id = _resolve_plant_channel(dict(call.data))
        if not plant_key:
            _LOGGER.error(
                "No plant_key or entity_id provided. Received data: %s",
                dict(call.data),
            )
            return

        runtime_data = _get_runtime_data()
        if not runtime_data:
            _LOGGER.error("No Kamerplanter instance found")
            return

        api = runtime_data.api

        # Resolve dosages and volume from plant coordinator
        fertilizers_used: list[dict[str, object]] = []
        volume_liters: float | None = call.data.get("volume_liters")
        plant_coord = runtime_data.coordinators.get("plants")

        if plant_coord and plant_coord.data:
            plant = next(
                (p for p in plant_coord.data if p.get("key") == plant_key), None
            )
            if plant:
                dosage_data = plant.get("_current_dosages")
                if dosage_data and isinstance(dosage_data, dict):
                    for ch in dosage_data.get("channels", []):
                        ch_id = ch.get("channel_id", "")
                        if channel_id and ch_id != channel_id:
                            continue
                        if not channel_id:
                            channel_id = ch_id
                        if volume_liters is None:
                            volume_liters = ch.get("volume_liters")
                        for dosage in ch.get("dosages", []):
                            ml = dosage.get("ml_per_liter")
                            fert_key = dosage.get("fertilizer_key")
                            if ml is not None and ml > 0 and fert_key:
                                fertilizers_used.append(
                                    {
                                        "fertilizer_key": fert_key,
                                        "ml_per_liter": ml,
                                    }
                                )
                        break

        if volume_liters is None or volume_liters <= 0:
            _LOGGER.error(
                "No volume resolved for plant %s channel %s. "
                "Provide volume_liters or ensure the nutrient plan defines a channel volume.",
                plant_key,
                channel_id,
            )
            return

        # Build watering log payload
        payload: dict[str, object] = {
            "application_method": call.data.get("application_method", "drench"),
            "volume_liters": volume_liters,
            "plant_keys": [plant_key],
            "channel_id": channel_id,
            "fertilizers_used": fertilizers_used,
            "performed_by": "home_assistant",
        }
        if call.data.get("measured_ec_ms") is not None:
            payload["ec_before"] = call.data["measured_ec_ms"]
        if call.data.get("measured_ph") is not None:
            payload["ph_before"] = call.data["measured_ph"]
        if call.data.get("notes"):
            payload["notes"] = call.data["notes"]

        _LOGGER.info(
            "Watering plant %s channel '%s': %.2fL, %d fertilizers",
            plant_key,
            channel_id,
            volume_liters,
            len(fertilizers_used),
        )

        try:
            result = await api.async_create_watering_log(payload)
            log_data = result.get("log", result)
            _LOGGER.info("Watering log created: %s", log_data.get("key", "unknown"))

            for coordinator in runtime_data.coordinators.values():
                await coordinator.async_request_refresh()
        except Exception:
            _LOGGER.exception("Failed to create watering log for plant %s", plant_key)

    async def handle_confirm_care(call: ServiceCall) -> None:
        """Handle the confirm_care service call (REQ-030)."""
        notification_key = call.data.get("notification_key")
        if not notification_key:
            _LOGGER.error(
                "No notification_key provided. Received data: %s",
                dict(call.data),
            )
            return

        action = call.data.get("action", "confirmed")

        runtime_data = _get_runtime_data()
        if not runtime_data:
            _LOGGER.error("No Kamerplanter instance found")
            return

        api = runtime_data.api

        _LOGGER.info(
            "Confirming care reminder %s with action '%s'",
            notification_key,
            action,
        )

        try:
            result = await api.async_confirm_care_reminder(
                notification_key=notification_key,
                action=action,
            )
            _LOGGER.info(
                "Care reminder %s confirmed: %s",
                notification_key,
                result,
            )

            for coordinator in runtime_data.coordinators.values():
                await coordinator.async_request_refresh()
        except Exception:
            _LOGGER.exception("Failed to confirm care reminder %s", notification_key)

    hass.services.async_register(DOMAIN, SERVICE_REFRESH, handle_refresh)
    hass.services.async_register(DOMAIN, SERVICE_CLEAR_CACHE, handle_clear_cache)
    hass.services.async_register(DOMAIN, SERVICE_FILL_TANK, handle_fill_tank)
    hass.services.async_register(DOMAIN, SERVICE_WATER_CHANNEL, handle_water_channel)
    hass.services.async_register(DOMAIN, SERVICE_CONFIRM_CARE, handle_confirm_care)
