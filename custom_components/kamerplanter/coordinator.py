"""DataUpdateCoordinators for the Kamerplanter integration."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import (
    KamerplanterApi,
    KamerplanterApiError,
    KamerplanterAuthError,
    KamerplanterConnectionError,
)
from .const import (
    CONF_POLL_ALERTS,
    CONF_POLL_IPM,
    CONF_POLL_LOCATIONS,
    CONF_POLL_PLANTS,
    CONF_POLL_TASKS,
    CONF_POLL_WEATHER,
    DEFAULT_POLL_ALERTS,
    DEFAULT_POLL_IPM,
    DEFAULT_POLL_LOCATIONS,
    DEFAULT_POLL_PLANTS,
    DEFAULT_POLL_TASKS,
    DEFAULT_POLL_WEATHER,
    DOMAIN,
    EVENT_IPM_ALERT,
    TANK_HOLDER_MARKER,
)
from .helpers import annotate_tasks_with_names, plant_display_name

# Pest pressure levels that trigger an IPM alert event.
IPM_ALERT_LEVELS: frozenset[str] = frozenset({"high", "critical"})

_LOGGER = logging.getLogger(__name__)


async def _annotate_tasks(api: KamerplanterApi, tasks: list[dict[str, Any]]) -> None:
    """Attach readable plant/display names to a task list in place (issue #57).

    Loads the plant instances once to resolve each task's referenced plant into
    a human-readable label. Plant loading failures are non-fatal — tasks keep
    their raw backend name so the coordinator update never aborts over naming.
    """
    try:
        plants = await api.async_get_plants()
    except Exception:  # noqa: BLE001
        _LOGGER.debug("Could not load plants for task name resolution")
        plants = []
    annotate_tasks_with_names(tasks, plants)


async def _fetch_published_keys(
    api: KamerplanterApi, entity_type: str
) -> set[str] | None:
    """Return the set of HA-published keys for an entity type, or None.

    ``None`` means the backend predates per-entity HA publishing, so callers
    must not filter (publish everything for backwards compatibility). An empty
    set means the feature exists but nothing is published yet — strict opt-in,
    so nothing is exposed to Home Assistant.
    """
    keys = await api.async_get_ha_published_keys(entity_type)
    return None if keys is None else set(keys)


def _filter_published(
    items: list[dict[str, Any]],
    published: set[str] | None,
    key: Callable[[dict[str, Any]], str] = lambda i: i.get("key", ""),
) -> list[dict[str, Any]]:
    """Keep only HA-published items.

    ``published is None`` (feature unavailable on the backend) keeps everything;
    an empty set keeps nothing (strict opt-in). The single chokepoint for the
    opt-in semantics shared by the plant/location/tank/IPM coordinators.
    """
    if published is None:
        return items
    return [item for item in items if key(item) in published]


def _normalize_phase_name(name: str) -> str:
    """Normalize phase name for comparison (lowercase, stripped)."""
    return name.strip().lower()


def _phase_names_match(a: str, b: str) -> bool:
    """Check if two phase names refer to the same phase."""
    return _normalize_phase_name(a) == _normalize_phase_name(b)


def _calc_current_week(started_at_iso: str) -> int:
    """Calculate current week number from phase start date (1-based).

    Falls back to week 1 when the timestamp is missing or malformed, so a bad
    ``current_phase_started_at`` never aborts a coordinator update.
    """
    try:
        started = datetime.fromisoformat(started_at_iso)
    except (ValueError, TypeError):
        return 1
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
            async with asyncio.timeout(30):
                plants = await self.api.async_get_plants()
                published = await _fetch_published_keys(self.api, "plant")
                active_plants = _filter_published(
                    [p for p in plants if not p.get("removed_on")], published
                )

                # Parallel enrichment instead of sequential
                enrichment_tasks = [
                    self._enrich_plant(plant) for plant in active_plants
                ]
                await asyncio.gather(*enrichment_tasks, return_exceptions=True)

                return active_plants
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
            async with asyncio.timeout(30):
                locations = await self.api.async_get_all_locations()
                published_loc = await _fetch_published_keys(self.api, "location")
                published_tank = await _fetch_published_keys(self.api, "tank")
                locations = _filter_published(
                    locations,
                    published_loc,
                    key=lambda loc: loc.get("key") or loc.get("_key", ""),
                )

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

                # Expose every HA-published tank as a standalone device, decoupled
                # from whether its parent location is published (issue #59). Tanks
                # whose location survived the publish filter hang off that location
                # (keeps the legacy location-tank sensors + fertigation volume
                # lookup working); tanks whose location is unpublished or absent are
                # collected on a synthetic holder appended to the data, so sensor.py
                # and the device cleanup still find them without a dedicated
                # coordinator. The opt-in semantics stay at the single
                # ``_filter_published`` chokepoint.
                published_tanks = _filter_published(self._all_tanks, published_tank)

                # Enrich every published tank once (fill status + HA sensor map),
                # regardless of its location's publish state.
                for tank in published_tanks:
                    tk = tank.get("key", "")
                    if not tk:
                        continue
                    try:
                        tank[
                            "_latest_fill"
                        ] = await self.api.async_get_tank_latest_fill(tk)
                    except Exception:  # noqa: BLE001
                        tank["_latest_fill"] = None
                    try:
                        tank["_ha_sensors"] = await self.api.async_get_tank_sensors(tk)
                    except Exception:  # noqa: BLE001
                        tank["_ha_sensors"] = []

                tanks_by_loc: dict[str, list[dict[str, Any]]] = {}
                for tank in published_tanks:
                    tlk = tank.get("location_key")
                    if tlk:
                        tanks_by_loc.setdefault(tlk, []).append(tank)

                published_loc_keys: set[str] = set()
                for loc in locations:
                    loc_key = loc.get("key") or loc.get("_key", "")
                    if loc_key:
                        published_loc_keys.add(loc_key)
                    loc["_tanks"] = tanks_by_loc.get(loc_key, [])

                # Published tanks whose location is not among the published
                # locations (or that carry no location_key) would otherwise be
                # dropped. Attach them to a keyless synthetic holder so they still
                # surface as standalone tank devices. Consumers that key off a
                # location skip this entry via ``if not loc_key``.
                orphan_tanks = [
                    tank
                    for tank in published_tanks
                    if (tank.get("location_key") or "") not in published_loc_keys
                ]
                if orphan_tanks:
                    locations.append({TANK_HOLDER_MARKER: True, "_tanks": orphan_tanks})

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
            async with asyncio.timeout(10):
                tasks = await self.api.async_get_overdue_tasks()
                await _annotate_tasks(self.api, tasks)
                return tasks
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
            async with asyncio.timeout(30):
                runs = await self.api.async_get_planting_runs()

                # Enrich each run in parallel. Isolating enrichment per run
                # (return_exceptions=True) keeps a single run's failure from
                # dropping the whole update, and cuts poll latency for setups
                # with several active runs.
                await asyncio.gather(
                    *(self._enrich_run(run) for run in runs),
                    return_exceptions=True,
                )

                return runs
        except TimeoutError as err:
            raise UpdateFailed("API request timed out") from err
        except KamerplanterAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except KamerplanterConnectionError as err:
            raise UpdateFailed(str(err)) from err

    async def _enrich_run(self, run: dict[str, Any]) -> None:
        """Enrich a single planting run with plan, timeline, channels, schedule."""
        if run.get("status") in ("completed", "cancelled"):
            return
        key = run.get("key")
        if not key:
            # A run without a key cannot be enriched; surface a graceful
            # UpdateFailed instead of a raw KeyError. Isolated by the caller's
            # gather(return_exceptions=True), so only this run is skipped.
            raise UpdateFailed("Planting run is missing its key")

        plan = await self.api.async_get_run_nutrient_plan(key)
        run["_nutrient_plan"] = plan
        if plan and plan.get("key"):
            entries = await self.api.async_get_plan_phase_entries(plan["key"])
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
        timeline = await self.api.async_get_run_phase_timeline(key)
        run["_timeline"] = timeline
        all_entries = run.get("_phase_entries", [])
        is_seasonal = plan and plan.get("cycle_restart_from_sequence") is not None
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
            channels = await self.api.async_get_run_active_channels(key, eff_week)
            run["_active_channels"] = channels
        except Exception:  # noqa: BLE001
            run["_active_channels"] = []

        # Watering schedule (next watering dates)
        try:
            ws = await self.api.async_get_run_watering_schedule(key)
            run["_watering_schedule"] = ws
        except Exception:  # noqa: BLE001
            run["_watering_schedule"] = None


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
            async with asyncio.timeout(10):
                tasks = await self.api.async_get_pending_tasks()
                await _annotate_tasks(self.api, tasks)
                return tasks
        except TimeoutError as err:
            raise UpdateFailed("API request timed out") from err
        except KamerplanterAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except KamerplanterConnectionError as err:
            raise UpdateFailed(str(err)) from err


def _days_until(date_iso: str | None) -> int | None:
    """Return whole days from today until an ISO date/datetime (negative = past)."""
    if not date_iso:
        return None
    try:
        parsed = datetime.fromisoformat(date_iso)
    except ValueError:
        try:
            parsed = datetime.combine(
                date.fromisoformat(date_iso[:10]), datetime.min.time()
            )
        except ValueError:
            return None
    target = parsed.date() if parsed.tzinfo is None else parsed.astimezone().date()
    return (target - date.today()).days


def _days_since(date_iso: str | None) -> int | None:
    """Return whole days from an ISO date/datetime until today (negative = future)."""
    days = _days_until(date_iso)
    return None if days is None else -days


class KamerplanterIpmCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    """Coordinator for IPM data (pest pressure, Karenz, harvest safety) per plant.

    The backend exposes IPM only through granular, plant-scoped endpoints, so we
    aggregate them client-side into one record per active plant. The record list
    mirrors the plant-coordinator shape (each item carries ``key`` = plant_key),
    which lets the IPM sensors reuse ``KpSensorBase._find_resource``.
    """

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, api: KamerplanterApi
    ) -> None:
        interval = entry.options.get(CONF_POLL_IPM, DEFAULT_POLL_IPM)
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_ipm",
            config_entry=entry,
            update_interval=timedelta(seconds=interval),
            always_update=False,
        )
        self.api = api
        # Remember the last pressure level per plant so we only fire an alert
        # on the transition *into* a high/critical level, not every poll.
        self._prev_pressure: dict[str, str] = {}

    async def _async_update_data(self) -> list[dict[str, Any]]:
        try:
            async with asyncio.timeout(30):
                plants = await self.api.async_get_plants()
                published = await _fetch_published_keys(self.api, "plant")
                active_plants = _filter_published(
                    [p for p in plants if not p.get("removed_on")], published
                )

                records = await asyncio.gather(
                    *(self._build_ipm_record(plant) for plant in active_plants),
                    return_exceptions=True,
                )
                result = [r for r in records if isinstance(r, dict)]
                self._fire_alerts(result)
                return result
        except TimeoutError as err:
            raise UpdateFailed("API request timed out") from err
        except KamerplanterAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except KamerplanterConnectionError as err:
            raise UpdateFailed(str(err)) from err

    async def _build_ipm_record(self, plant: dict[str, Any]) -> dict[str, Any]:
        """Aggregate the per-plant IPM endpoints into a single record."""
        key = plant.get("key")
        if not key:
            # Guard against malformed plant records: a graceful UpdateFailed
            # instead of a raw KeyError. The caller's gather isolates it, so
            # only this plant is skipped (filtered out by the dict check).
            raise UpdateFailed("Plant instance is missing its key")
        inspections, karenz, harvest = await asyncio.gather(
            self.api.async_get_pest_inspections(key),
            self.api.async_get_karenz(key),
            self.api.async_get_harvest_safety(key),
            return_exceptions=True,
        )
        if isinstance(inspections, BaseException) or not inspections:
            inspections = []
        if isinstance(karenz, BaseException) or not karenz:
            karenz = []
        if isinstance(harvest, BaseException):
            harvest = None

        latest = max(
            inspections,
            key=lambda i: i.get("inspected_at", ""),
            default=None,
        )

        record: dict[str, Any] = {
            "key": key,
            "plant_name": plant_display_name(plant),
            "pressure_level": (latest or {}).get("pressure_level", "none"),
            "detected_pest_keys": (latest or {}).get("detected_pest_keys", []),
            "last_inspection_at": (latest or {}).get("inspected_at"),
            "last_inspection_days": _days_since((latest or {}).get("inspected_at")),
            "karenz_remaining_days": None,
            "karenz_safe_date": None,
            "treatment_name": None,
            "active_ingredient": None,
            "can_harvest": True,
            "blocking_treatments": [],
        }

        # The backend returns a list of Karenz periods; the one with the latest
        # safe_date binds harvest the longest, so it drives the sensor values.
        periods = [k for k in karenz if isinstance(k, dict) and k.get("safe_date")]
        if periods:
            binding = max(periods, key=lambda k: k["safe_date"])
            record["karenz_safe_date"] = binding.get("safe_date")
            record["karenz_remaining_days"] = max(
                0, _days_until(binding.get("safe_date")) or 0
            )
            record["treatment_name"] = binding.get("treatment_name")
            record["active_ingredient"] = binding.get("active_ingredient")

        if harvest is not None:
            record["can_harvest"] = harvest.get("can_harvest", True)
            record["blocking_treatments"] = harvest.get("blocking_treatments", [])

        return record

    def _fire_alerts(self, records: list[dict[str, Any]]) -> None:
        """Fire EVENT_IPM_ALERT when a plant transitions into high/critical."""
        current: dict[str, str] = {}
        for record in records:
            key = record["key"]
            level = record.get("pressure_level", "none")
            current[key] = level
            was = self._prev_pressure.get(key, "none")
            if level in IPM_ALERT_LEVELS and was not in IPM_ALERT_LEVELS:
                self.hass.bus.async_fire(
                    EVENT_IPM_ALERT,
                    {
                        "plant_key": key,
                        "plant_name": record.get("plant_name"),
                        "pressure_level": level,
                        "detected_pest_keys": record.get("detected_pest_keys", []),
                    },
                )
        self._prev_pressure = current


class KamerplanterWeatherCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    """Coordinator for the per-site weather forecast + proactive frost warning.

    Reads ``GET /sites/{site_key}/weather-forecast`` once per site (issue #53).
    The per-location frost endpoint no longer carries the proactive forecast
    fields, so a site with N locations no longer triggers N identical forecast
    reads — reading per site is the efficiency win that backend change enabled.

    Weather changes slowly, hence a much longer default poll interval than the
    other coordinators. One record per site, keyed by ``key`` so the frost
    sensors reuse ``find_by_key``. Sites are not subject to the HA-publish
    opt-in gate (there is no ``site`` published-key type), so every site with a
    reachable forecast surfaces a frost sensor.
    """

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, api: KamerplanterApi
    ) -> None:
        interval = entry.options.get(CONF_POLL_WEATHER, DEFAULT_POLL_WEATHER)
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_weather",
            config_entry=entry,
            update_interval=timedelta(seconds=interval),
            always_update=False,
        )
        self.api = api

    async def _async_update_data(self) -> list[dict[str, Any]]:
        try:
            async with asyncio.timeout(30):
                sites = await self.api.async_get_sites()
                records = await asyncio.gather(
                    *(self._build_site_record(site) for site in sites),
                    return_exceptions=True,
                )
                return [r for r in records if isinstance(r, dict)]
        except TimeoutError as err:
            raise UpdateFailed("API request timed out") from err
        except KamerplanterAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except KamerplanterConnectionError as err:
            raise UpdateFailed(str(err)) from err

    async def _build_site_record(self, site: dict[str, Any]) -> dict[str, Any]:
        """Read one site's forecast into a flat frost-summary record.

        A per-site forecast error is non-fatal: the site still yields a record
        with ``None`` frost fields (sensor state ``unknown``) so a transient
        error does not make the entity disappear.
        """
        site_key = site.get("key") or site.get("_key", "")
        if not site_key:
            # Isolated by the caller's gather; only this malformed site is skipped.
            raise UpdateFailed("Site is missing its key")
        try:
            forecast = await self.api.async_get_site_weather_forecast(site_key)
        except KamerplanterApiError:
            forecast = None
        forecast = forecast or {}
        return {
            "key": site_key,
            "name": site.get("name", site_key),
            "type": site.get("type"),
            "frost_warning": forecast.get("forecast_frost_warning"),
            "min_temperature": forecast.get("forecast_min_temperature"),
            "expected_date": forecast.get("forecast_expected_date"),
            "source": forecast.get("forecast_source"),
        }
