"""DataUpdateCoordinators for the Kamerplanter integration."""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

import async_timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import KamerplanterApi, KamerplanterAuthError, KamerplanterConnectionError
from .const import (
    CONF_POLL_ALERTS,
    CONF_POLL_LOCATIONS,
    CONF_POLL_PLANTS,
    CONF_POLL_TASKS,
    DEFAULT_POLL_ALERTS,
    DEFAULT_POLL_LOCATIONS,
    DEFAULT_POLL_PLANTS,
    DEFAULT_POLL_TASKS,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def _normalize_phase_name(name: str) -> str:
    """Normalize phase name for comparison (lowercase, stripped)."""
    return name.strip().lower()


def _phase_names_match(a: str, b: str) -> bool:
    """Check if two phase names refer to the same phase."""
    return _normalize_phase_name(a) == _normalize_phase_name(b)


def _calc_current_week(started_at_iso: str) -> int:
    """Calculate current week number from phase start date (1-based)."""
    started = datetime.fromisoformat(started_at_iso)
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    delta = datetime.now(tz=timezone.utc) - started
    return max(1, delta.days // 7 + 1)


def _calc_effective_plan_week(
    timeline: list[dict[str, Any]],
    entries: list[dict[str, Any]],
) -> int | None:
    """Calculate the effective plan week based on current phase + weeks into it."""
    current_phase_name: str | None = None
    current_phase_entered: str | None = None
    for species in timeline:
        for phase in species.get("phases", []):
            if phase.get("status") == "current":
                current_phase_name = phase.get("phase_name")
                current_phase_entered = phase.get("actual_entered_at")
                break
        if current_phase_name:
            break

    if not current_phase_name or not current_phase_entered:
        return None

    weeks_in_phase = _calc_current_week(current_phase_entered) - 1

    phase_plan_start: int | None = None
    for entry in entries:
        if _phase_names_match(entry.get("phase_name", ""), current_phase_name):
            ws = entry.get("week_start", 0)
            if phase_plan_start is None or ws < phase_plan_start:
                phase_plan_start = ws
            break

    if phase_plan_start is None:
        return None

    return phase_plan_start + weeks_in_phase


def _filter_current_phase_entries(
    entries: list[dict[str, Any]], current_week: int
) -> list[dict[str, Any]]:
    """Filter phase entries to only the one matching the current week."""
    for entry in entries:
        ws = entry.get("week_start", 0)
        we = entry.get("week_end", 0)
        if ws <= current_week < we:
            return [entry]
    if entries:
        return [entries[-1]]
    return []


class KamerplanterPlantCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    """Coordinator for plant data."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, api: KamerplanterApi
    ) -> None:
        interval = entry.options.get(CONF_POLL_PLANTS, DEFAULT_POLL_PLANTS)
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_plants",
            config_entry=entry,
            update_interval=timedelta(seconds=interval),
            always_update=False,
        )
        self.api = api
        self._fert_lookup: dict[str, str] = {}

    async def _async_setup(self) -> None:
        """Load static data once (fertilizer names for dosage enrichment)."""
        try:
            fertilizers = await self.api.async_get_fertilizers()
            self._fert_lookup = {
                f.get("key", ""): f.get("product_name", f.get("name", ""))
                for f in fertilizers
            }
        except KamerplanterConnectionError:
            self._fert_lookup = {}
            _LOGGER.debug("Could not pre-load fertilizer names")

    async def _async_update_data(self) -> list[dict[str, Any]]:
        try:
            async with async_timeout.timeout(30):
                plants = await self.api.async_get_plants()
                active_plants = [p for p in plants if not p.get("removed_on")]

                # Parallel enrichment instead of sequential
                enrichment_tasks = [
                    self._enrich_plant(plant) for plant in active_plants
                ]
                await asyncio.gather(*enrichment_tasks, return_exceptions=True)

                return plants
        except TimeoutError as err:
            raise UpdateFailed("API request timed out") from err
        except KamerplanterAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except KamerplanterConnectionError as err:
            raise UpdateFailed(str(err)) from err

    async def _enrich_plant(self, plant: dict[str, Any]) -> None:
        """Enrich a single plant with nutrient plan, dosages, and history."""
        key = plant["key"]
        started = plant.get("current_phase_started_at")

        # Nutrient plan + phase entries
        try:
            plan = await self.api.async_get_plant_nutrient_plan(key)
            plant["_nutrient_plan"] = plan
            # Enrich plan with phase entries (needed for progress calculation)
            if plan and plan.get("key"):
                try:
                    entries = await self.api.async_get_plan_phase_entries(plan["key"])
                    plan["phase_entries"] = entries
                except Exception:  # noqa: BLE001
                    plan["phase_entries"] = []
        except Exception:  # noqa: BLE001
            plant["_nutrient_plan"] = None

        # Current dosages (only if plan present)
        # Seasonal plans (cycle_restart_from_sequence set) use ISO calendar
        # week instead of weeks-since-phase-start, because their phase entries
        # are keyed to calendar weeks (W1=Jan, W14=Apr, etc.).
        # Fallback to week 1 when current_phase_started_at is missing
        # (common for houseplants without explicit phase transitions).
        plan = plant.get("_nutrient_plan")
        if plan:
            is_seasonal = plan.get("cycle_restart_from_sequence") is not None
            if is_seasonal:
                week = date.today().isocalendar().week
            elif started:
                week = _calc_current_week(started)
            else:
                week = 1
            try:
                plant[
                    "_current_dosages"
                ] = await self.api.async_get_plant_current_dosages(key, week)
            except Exception:  # noqa: BLE001
                plant["_current_dosages"] = None
            try:
                plant[
                    "_active_channels"
                ] = await self.api.async_get_plant_active_channels(key, week)
            except Exception:  # noqa: BLE001
                plant["_active_channels"] = []
        else:
            plant["_current_dosages"] = None
            plant["_active_channels"] = []

        # Phase history
        try:
            plant["_phase_history"] = await self.api.async_get_plant_phase_history(key)
        except Exception:  # noqa: BLE001
            plant["_phase_history"] = []

        # Watering: phase interval > care profile, + last confirmation → next due date
        try:
            # Phase-specific interval takes priority
            phase_interval = None
            phase_key = plant.get("current_phase_key")
            if phase_key:
                phase = await self.api.async_get_growth_phase(phase_key)
                if phase:
                    phase_interval = phase.get("watering_interval_days")

            profile = await self.api.async_get_care_profile(key)
            if profile:
                interval = (
                    phase_interval
                    or profile.get("watering_interval_learned")
                    or profile.get("watering_interval_days")
                    or 7
                )
                history = await self.api.async_get_care_history(key, "watering", 1)
                if history:
                    last_date = history[0].get("confirmed_at", "")[:10]
                else:
                    last_date = None
                plant["_watering_interval_days"] = interval
                plant["_watering_last_date"] = last_date
            else:
                plant["_watering_interval_days"] = None
                plant["_watering_last_date"] = None
        except Exception:  # noqa: BLE001
            plant["_watering_interval_days"] = None
            plant["_watering_last_date"] = None


class KamerplanterLocationCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    """Coordinator for location data enriched with assigned runs/instances."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, api: KamerplanterApi
    ) -> None:
        interval = entry.options.get(CONF_POLL_LOCATIONS, DEFAULT_POLL_LOCATIONS)
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_locations",
            config_entry=entry,
            update_interval=timedelta(seconds=interval),
            always_update=False,
        )
        self.api = api
        self._fert_lookup: dict[str, str] = {}
        self._all_tanks: list[dict[str, Any]] = []

    async def _async_setup(self) -> None:
        """Pre-load fertilizer names and tank list (rarely change)."""
        try:
            fertilizers = await self.api.async_get_fertilizers()
            self._fert_lookup = {
                f.get("key", ""): f.get("product_name", f.get("name", ""))
                for f in fertilizers
            }
        except KamerplanterConnectionError:
            self._fert_lookup = {}

        try:
            self._all_tanks = await self.api.async_get_tanks()
        except KamerplanterConnectionError:
            self._all_tanks = []

    async def _async_update_data(self) -> list[dict[str, Any]]:
        try:
            async with async_timeout.timeout(30):
                locations = await self.api.async_get_all_locations()

                for loc in locations:
                    loc_key = loc.get("key") or loc.get("_key", "")
                    if not loc_key:
                        continue
                    # Fetch runs assigned to this location
                    try:
                        runs = await self.api.async_get_runs_by_location(loc_key)
                    except Exception:  # noqa: BLE001
                        runs = []
                    active_runs = [
                        r
                        for r in runs
                        if r.get("status") not in ("completed", "cancelled")
                    ]
                    loc["_active_runs"] = active_runs
                    loc["_active_run_count"] = len(active_runs)

                    # Derive plant count
                    run_plant_count = sum(
                        r.get("actual_quantity", 0) for r in active_runs
                    )
                    try:
                        slot_plants = (
                            await self.api.async_get_plant_instances_by_location(
                                loc_key
                            )
                        )
                    except Exception:  # noqa: BLE001
                        slot_plants = []
                    active_slot_plants = [
                        p for p in slot_plants if not p.get("removed_on")
                    ]
                    loc["_active_plants"] = active_slot_plants
                    loc["_active_plant_count"] = max(
                        run_plant_count, len(active_slot_plants)
                    )
                    loc["_run_plant_count"] = run_plant_count
                    _LOGGER.debug(
                        "Location %s: %d active runs, %d run_plants, %d slot_plants",
                        loc_key,
                        len(active_runs),
                        run_plant_count,
                        len(active_slot_plants),
                    )

                    # Enrich primary run
                    primary = active_runs[0] if active_runs else None
                    if primary:
                        run_key = primary.get("key", "")
                        plan = await self.api.async_get_run_nutrient_plan(run_key)
                        primary["_nutrient_plan"] = plan
                        if plan and plan.get("key"):
                            entries = await self.api.async_get_plan_phase_entries(
                                plan["key"]
                            )
                            for entry in entries:
                                for channel in entry.get("delivery_channels", []):
                                    for dosage in channel.get("fertilizer_dosages", []):
                                        fk = dosage.get("fertilizer_key", "")
                                        if (
                                            fk
                                            and fk in self._fert_lookup
                                            and "product_name" not in dosage
                                        ):
                                            dosage["product_name"] = self._fert_lookup[
                                                fk
                                            ]
                            primary["_phase_entries"] = entries
                        timeline = await self.api.async_get_run_phase_timeline(run_key)
                        primary["_timeline"] = timeline
                        all_entries = primary.get("_phase_entries", [])
                        is_seasonal = (
                            plan and plan.get("cycle_restart_from_sequence") is not None
                        )
                        if is_seasonal:
                            eff_week = date.today().isocalendar().week
                        else:
                            eff_week = _calc_effective_plan_week(timeline, all_entries)
                        if eff_week is not None:
                            primary["_current_week"] = eff_week
                            primary["_current_phase_entries"] = (
                                _filter_current_phase_entries(all_entries, eff_week)
                            )
                        loc["_primary_run"] = primary

                # Enrich locations with tank data (use cached tank list, only poll fill status)
                tanks_by_loc: dict[str, list[dict[str, Any]]] = {}
                for tank in self._all_tanks:
                    tlk = tank.get("location_key")
                    if tlk:
                        tanks_by_loc.setdefault(tlk, []).append(tank)

                for loc in locations:
                    loc_key = loc.get("key") or loc.get("_key", "")
                    loc_tanks = tanks_by_loc.get(loc_key, [])
                    for tank in loc_tanks:
                        tk = tank.get("key", "")
                        try:
                            latest = await self.api.async_get_tank_latest_fill(tk)
                            tank["_latest_fill"] = latest
                        except Exception:  # noqa: BLE001
                            tank["_latest_fill"] = None
                        try:
                            tank["_ha_sensors"] = await self.api.async_get_tank_sensors(
                                tk
                            )
                        except Exception:  # noqa: BLE001
                            tank["_ha_sensors"] = []
                    loc["_tanks"] = loc_tanks

                return locations
        except TimeoutError as err:
            raise UpdateFailed("API request timed out") from err
        except KamerplanterAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except KamerplanterConnectionError as err:
            raise UpdateFailed(str(err)) from err


class KamerplanterAlertCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    """Coordinator for alerts (derived from overdue tasks)."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, api: KamerplanterApi
    ) -> None:
        interval = entry.options.get(CONF_POLL_ALERTS, DEFAULT_POLL_ALERTS)
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_alerts",
            config_entry=entry,
            update_interval=timedelta(seconds=interval),
            always_update=False,
        )
        self.api = api

    async def _async_update_data(self) -> list[dict[str, Any]]:
        try:
            async with async_timeout.timeout(10):
                return await self.api.async_get_overdue_tasks()
        except TimeoutError as err:
            raise UpdateFailed("API request timed out") from err
        except KamerplanterAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except KamerplanterConnectionError as err:
            raise UpdateFailed(str(err)) from err


class KamerplanterRunCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    """Coordinator for planting run data."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, api: KamerplanterApi
    ) -> None:
        interval = entry.options.get(CONF_POLL_PLANTS, DEFAULT_POLL_PLANTS)
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_runs",
            config_entry=entry,
            update_interval=timedelta(seconds=interval),
            always_update=False,
        )
        self.api = api
        self._fert_lookup: dict[str, str] = {}

    async def _async_setup(self) -> None:
        """Load static data once (fertilizer names)."""
        try:
            fertilizers = await self.api.async_get_fertilizers()
            self._fert_lookup = {
                f.get("key", ""): f.get("product_name", f.get("name", ""))
                for f in fertilizers
            }
        except KamerplanterConnectionError:
            self._fert_lookup = {}
            _LOGGER.debug("Could not pre-load fertilizer names for runs")

    async def _async_update_data(self) -> list[dict[str, Any]]:
        try:
            async with async_timeout.timeout(30):
                runs = await self.api.async_get_planting_runs()

                for run in runs:
                    if run.get("status") in ("completed", "cancelled"):
                        continue
                    plan = await self.api.async_get_run_nutrient_plan(run["key"])
                    run["_nutrient_plan"] = plan
                    if plan and plan.get("key"):
                        entries = await self.api.async_get_plan_phase_entries(
                            plan["key"]
                        )
                        for entry in entries:
                            for channel in entry.get("delivery_channels", []):
                                for dosage in channel.get("fertilizer_dosages", []):
                                    fk = dosage.get("fertilizer_key", "")
                                    if (
                                        fk
                                        and fk in self._fert_lookup
                                        and "product_name" not in dosage
                                    ):
                                        dosage["product_name"] = self._fert_lookup[fk]
                        run["_phase_entries"] = entries
                    timeline = await self.api.async_get_run_phase_timeline(run["key"])
                    run["_timeline"] = timeline
                    all_entries = run.get("_phase_entries", [])
                    is_seasonal = (
                        plan and plan.get("cycle_restart_from_sequence") is not None
                    )
                    if is_seasonal:
                        eff_week = date.today().isocalendar().week
                    else:
                        eff_week = _calc_effective_plan_week(timeline, all_entries)
                    if eff_week is not None:
                        run["_current_week"] = eff_week
                        run["_current_phase_entries"] = _filter_current_phase_entries(
                            all_entries, eff_week
                        )
                    try:
                        channels = await self.api.async_get_run_active_channels(
                            run["key"], eff_week
                        )
                        run["_active_channels"] = channels
                    except Exception:  # noqa: BLE001
                        run["_active_channels"] = []

                    # Watering schedule (next watering dates)
                    try:
                        ws = await self.api.async_get_run_watering_schedule(run["key"])
                        run["_watering_schedule"] = ws
                    except Exception:  # noqa: BLE001
                        run["_watering_schedule"] = None

                return runs
        except TimeoutError as err:
            raise UpdateFailed("API request timed out") from err
        except KamerplanterAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except KamerplanterConnectionError as err:
            raise UpdateFailed(str(err)) from err


class KamerplanterTaskCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    """Coordinator for pending tasks."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, api: KamerplanterApi
    ) -> None:
        interval = entry.options.get(CONF_POLL_TASKS, DEFAULT_POLL_TASKS)
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_tasks",
            config_entry=entry,
            update_interval=timedelta(seconds=interval),
            always_update=False,
        )
        self.api = api

    async def _async_update_data(self) -> list[dict[str, Any]]:
        try:
            async with async_timeout.timeout(10):
                return await self.api.async_get_pending_tasks()
        except TimeoutError as err:
            raise UpdateFailed("API request timed out") from err
        except KamerplanterAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except KamerplanterConnectionError as err:
            raise UpdateFailed(str(err)) from err
