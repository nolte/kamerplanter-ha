"""The Kamerplanter integration."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path

from aiohttp import ClientSession
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import KamerplanterApi
from .const import (
    CONF_API_KEY,
    CONF_API_PATH,
    CONF_TENANT_SLUG,
    DEFAULT_API_PATH,
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
    KamerplanterIpmCoordinator,
    KamerplanterLocationCoordinator,
    KamerplanterPlantCoordinator,
    KamerplanterRunCoordinator,
    KamerplanterTaskCoordinator,
)
from .helpers import (
    resolve_entry_id,
    resolve_plant_channel,
    resolve_tank_key,
)

_LOGGER = logging.getLogger(__name__)

# Repairs issue raised when Lovelace runs in YAML resource mode and the cards
# therefore cannot be auto-registered.
ISSUE_LOVELACE_YAML_MODE = "lovelace_yaml_mode"
LOVELACE_DOCS_URL = (
    "https://github.com/nolte/kamerplanter-ha/blob/develop/"
    "docs/en/guides/lovelace-cards.md"
)


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
        api_path=entry.data.get(CONF_API_PATH, DEFAULT_API_PATH),
    )

    coordinators: dict[str, DataUpdateCoordinator] = {
        "plants": KamerplanterPlantCoordinator(hass, entry, api),
        "locations": KamerplanterLocationCoordinator(hass, entry, api),
        "runs": KamerplanterRunCoordinator(hass, entry, api),
        "alerts": KamerplanterAlertCoordinator(hass, entry, api),
        "tasks": KamerplanterTaskCoordinator(hass, entry, api),
        "ipm": KamerplanterIpmCoordinator(hass, entry, api),
    }

    # First refresh all coordinators in parallel. The first coordinator to
    # raise (ConfigEntryNotReady / ConfigEntryAuthFailed) propagates and aborts
    # setup, exactly as the previous sequential loop did — only faster.
    await asyncio.gather(
        *(
            coordinator.async_config_entry_first_refresh()
            for coordinator in coordinators.values()
        )
    )

    # Store runtime_data on the config entry (HA best practice)
    entry.runtime_data = KamerplanterRuntimeData(api=api, coordinators=coordinators)

    # Register services (HA-NFR-002: idempotency guard)
    if not hass.services.has_service(DOMAIN, SERVICE_REFRESH):
        await _async_register_services(hass)

    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Prune devices whose backing element is no longer HA-published / active.
    # New entities are only *created* for published elements, but HA never
    # *removes* devices on its own, so un-publishing a plant in Kamerplanter
    # would otherwise leave its device + entities behind. Run once now and on
    # every relevant coordinator update so un-publishing takes effect on the
    # next poll without a reload.
    @callback
    def _cleanup_orphaned_devices() -> None:
        _async_cleanup_orphaned_devices(hass, entry)

    for _name in ("plants", "locations", "runs"):
        _coord = coordinators.get(_name)
        if _coord is not None:
            entry.async_on_unload(_coord.async_add_listener(_cleanup_orphaned_devices))
    _cleanup_orphaned_devices()

    # Auto-register Lovelace cards and assets from www/ subdirectory
    www_dir = Path(__file__).parent / "www"
    if www_dir.is_dir():
        from homeassistant.components.http import StaticPathConfig

        js_files = await hass.async_add_executor_job(lambda: list(www_dir.glob("*.js")))
        # cache_headers=False: serve the cards with ETag revalidation instead of
        # a 31-day immutable cache. Otherwise an updated card stays masked by the
        # browser cache after a redeploy/update (stale getGridOptions, layout...).
        paths = [
            StaticPathConfig(f"/{DOMAIN}/{js_file.name}", str(js_file), False)
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


@callback
def _async_cleanup_orphaned_devices(
    hass: HomeAssistant, entry: KamerplanterConfigEntry
) -> None:
    """Remove devices whose backing element is no longer published / active.

    A plant/location/tank/run drops out of its coordinator data when it is
    un-published in Kamerplanter (or removed/completed). HA does not delete the
    matching device automatically, so we prune it here together with all of its
    entities.

    Conservative by design: if any source coordinator has not produced a
    successful update we skip the whole pass, so a transient backend error can
    never wipe still-valid devices.
    """
    coordinators = entry.runtime_data.coordinators
    plant_coord = coordinators.get("plants")
    loc_coord = coordinators.get("locations")
    run_coord = coordinators.get("runs")

    sources = [c for c in (plant_coord, loc_coord, run_coord) if c is not None]
    if any(not c.last_update_success or c.data is None for c in sources):
        return

    # Identifiers we consider valid; everything else under this entry is orphaned.
    valid: set[tuple[str, str]] = {(DOMAIN, entry.entry_id)}  # server hub
    if plant_coord and plant_coord.data:
        for plant in plant_coord.data:
            valid.add((DOMAIN, f"{entry.entry_id}_plant_{plant['key']}"))
    if run_coord and run_coord.data:
        for run in run_coord.data:
            if run.get("status") not in ("completed", "cancelled"):
                valid.add((DOMAIN, f"{entry.entry_id}_run_{run['key']}"))
    if loc_coord and loc_coord.data:
        for loc in loc_coord.data:
            loc_key = loc.get("key") or loc.get("_key", "")
            if loc_key:
                valid.add((DOMAIN, f"{entry.entry_id}_location_{loc_key}"))
            for tank in loc.get("_tanks", []):
                tank_key = tank.get("key", "")
                if tank_key:
                    valid.add((DOMAIN, f"{entry.entry_id}_tank_{tank_key}"))

    device_reg = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(device_reg, entry.entry_id):
        if not (device.identifiers & valid):
            _LOGGER.debug(
                "Removing orphaned Kamerplanter device %s", device.identifiers
            )
            device_reg.async_update_device(
                device.id, remove_config_entry_id=entry.entry_id
            )


async def _async_register_lovelace_resources(
    hass: HomeAssistant, js_files: list[Path]
) -> None:
    """Register JS files as Lovelace resources (idempotent).

    Auto-registration only works when Lovelace runs in *storage* mode. In YAML
    resource mode the resource list is owned by ``configuration.yaml`` and is
    read-only from our side, so instead of failing silently we raise a Repairs
    issue telling the user to add the cards manually.
    """
    from homeassistant.components.lovelace import DOMAIN as LOVELACE_DOMAIN
    from homeassistant.exceptions import HomeAssistantError
    from homeassistant.helpers import issue_registry as ir

    expected_urls = [f"/{DOMAIN}/{js_file.name}" for js_file in js_files]

    lovelace_data = hass.data.get(LOVELACE_DOMAIN)
    if lovelace_data is None:
        return
    resources = getattr(lovelace_data, "resources", None)
    if resources is None:
        return

    try:
        if not resources.loaded:
            await resources.async_load()

        # The YAML resource collection is read-only: it has no create method.
        # That is our reliable discriminator between storage and YAML mode.
        if not hasattr(resources, "async_create_item"):
            _async_handle_yaml_mode_resources(hass, resources, expected_urls)
            return

        existing_urls = {r["url"] for r in resources.async_items()}
        for url in expected_urls:
            if url not in existing_urls:
                await resources.async_create_item({"res_type": "module", "url": url})
                _LOGGER.info("Registered Lovelace resource: %s", url)

        # Storage mode succeeded — a stale YAML-mode repair no longer applies.
        ir.async_delete_issue(hass, DOMAIN, ISSUE_LOVELACE_YAML_MODE)
    except (HomeAssistantError, KeyError, AttributeError) as err:
        _LOGGER.warning("Could not auto-register Lovelace resources: %s", err)


@callback
def _async_handle_yaml_mode_resources(
    hass: HomeAssistant, resources: object, expected_urls: list[str]
) -> None:
    """Raise (or clear) a Repairs issue for Lovelace YAML resource mode.

    In YAML mode we cannot register the cards ourselves; we can only check
    whether the user has already listed them and, if not, surface an
    actionable issue with the exact ``resources:`` snippet to add.
    """
    from homeassistant.helpers import issue_registry as ir

    listed = {r["url"] for r in resources.async_items()}  # type: ignore[attr-defined]
    missing = [url for url in expected_urls if url not in listed]

    if not missing:
        ir.async_delete_issue(hass, DOMAIN, ISSUE_LOVELACE_YAML_MODE)
        return

    snippet = "\n".join(f"    - url: {url}\n      type: module" for url in missing)
    _LOGGER.warning(
        "Lovelace runs in YAML resource mode; the Kamerplanter cards are not "
        "registered. Add them to the `lovelace: resources:` list in "
        "configuration.yaml and restart Home Assistant:\n%s",
        snippet,
    )
    ir.async_create_issue(
        hass,
        DOMAIN,
        ISSUE_LOVELACE_YAML_MODE,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key=ISSUE_LOVELACE_YAML_MODE,
        translation_placeholders={"resources": snippet},
        learn_more_url=LOVELACE_DOCS_URL,
    )


async def async_unload_entry(
    hass: HomeAssistant, entry: KamerplanterConfigEntry
) -> bool:
    """Unload a config entry."""
    # runtime_data is automatically cleaned up by HA
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(
    hass: HomeAssistant, entry: KamerplanterConfigEntry
) -> None:
    """Remove auto-registered Lovelace resources when the last entry is gone.

    Called by HA after the entry has been unloaded and is being deleted. We
    only deregister the Lovelace resources when *no* Kamerplanter entries
    remain, so reload / multi-instance setups keep their cards working.
    """
    remaining = [
        e
        for e in hass.config_entries.async_entries(DOMAIN)
        if e.entry_id != entry.entry_id
    ]
    if remaining:
        return
    await _async_deregister_lovelace_resources(hass)


async def _async_deregister_lovelace_resources(hass: HomeAssistant) -> None:
    """Remove all Lovelace resources we previously auto-registered."""
    try:
        from homeassistant.components.lovelace import DOMAIN as LOVELACE_DOMAIN

        lovelace_data = hass.data.get(LOVELACE_DOMAIN)
        if lovelace_data is None:
            return
        resources = getattr(lovelace_data, "resources", None)
        if resources is None:
            return

        if not resources.loaded:
            await resources.async_load()

        # Resources we own are mounted under `/<DOMAIN>/`. Match by prefix so
        # we don't depend on the JS file list still existing on disk.
        prefix = f"/{DOMAIN}/"
        owned = [r for r in resources.async_items() if r["url"].startswith(prefix)]
        for resource in owned:
            await resources.async_delete_item(resource["id"])
            _LOGGER.info("Removed Lovelace resource: %s", resource["url"])
    except Exception:
        _LOGGER.debug("Could not deregister Lovelace resources", exc_info=True)


async def _async_register_services(hass: HomeAssistant) -> None:
    """Register Kamerplanter services."""

    def _runtime_data_for(entry_id: str | None) -> KamerplanterRuntimeData | None:
        """Return the runtime_data for a specific config entry."""
        if not entry_id:
            return None
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != DOMAIN:
            return None
        return getattr(entry, "runtime_data", None)

    def _resolve_runtime_data(
        call: ServiceCall, *, ambiguity_hint: str
    ) -> KamerplanterRuntimeData | None:
        """Resolve the targeted runtime_data, with a clear error on ambiguity."""
        entry_id = resolve_entry_id(hass, dict(call.data))
        if not entry_id:
            entries = list(hass.config_entries.async_entries(DOMAIN))
            if len(entries) > 1:
                _LOGGER.error(
                    "Multiple Kamerplanter instances configured — pass an "
                    "explicit `entry_id` or %s to target one (%d entries).",
                    ambiguity_hint,
                    len(entries),
                )
            else:
                _LOGGER.error("No Kamerplanter instance found")
            return None
        return _runtime_data_for(entry_id)

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

    async def handle_fill_tank(call: ServiceCall) -> None:
        """Handle the fill_tank service call."""
        _LOGGER.debug("fill_tank call.data keys: %s", list(call.data.keys()))
        tank_key = resolve_tank_key(hass, dict(call.data))
        if not tank_key:
            _LOGGER.error(
                "No tank_key or entity_id provided. Received keys: %s",
                list(call.data.keys()),
            )
            return
        fill_type = call.data.get("fill_type", "full_change")

        runtime_data = _resolve_runtime_data(call, ambiguity_hint="a tank entity_id")
        if not runtime_data:
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

    async def handle_water_channel(call: ServiceCall) -> None:
        """Handle the water_channel service call."""
        _LOGGER.debug("water_channel call.data keys: %s", list(call.data.keys()))
        plant_key, channel_id = resolve_plant_channel(hass, dict(call.data))
        if not plant_key:
            _LOGGER.error(
                "No plant_key or entity_id provided. Received keys: %s",
                list(call.data.keys()),
            )
            return

        runtime_data = _resolve_runtime_data(call, ambiguity_hint="a channel entity_id")
        if not runtime_data:
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
                "No notification_key provided. Received keys: %s",
                list(call.data.keys()),
            )
            return

        action = call.data.get("action", "confirmed")

        runtime_data = _resolve_runtime_data(
            call, ambiguity_hint="an explicit entry_id"
        )
        if not runtime_data:
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
