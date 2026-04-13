"""Calendar entities for the Kamerplanter integration."""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import EVENT_TASK_COMPLETED
from .coordinator import KamerplanterPlantCoordinator, KamerplanterTaskCoordinator
from .entity import server_device_info

PARALLEL_UPDATES = 0  # CoordinatorEntity — no own polling

_LOGGER = logging.getLogger(__name__)

# Phase status labels
_PHASE_STATUS_LABEL: dict[str, str] = {
    "completed": "\u2705 Completed",
    "current": "\u25b6\ufe0f Active",
    "projected": "\U0001f4c5 Projected",
}

# Phase name → emoji icon
_PHASE_ICON: dict[str, str] = {
    # Core phases (REQ-003)
    "germination": "\U0001f331",  # 🌱 seedling
    "seedling": "\U0001f33f",  # 🌿 herb
    "vegetative": "\U0001f33e",  # 🌾 sheaf of rice
    "flowering": "\U0001f33a",  # 🌺 hibiscus
    "harvest": "\u2702\ufe0f",  # ✂️ scissors
    # Extended phases (perennial cycle)
    "ripening": "\U0001f347",  # 🍇 grapes
    "juvenile": "\U0001f33b",  # 🌻 sunflower (young growth)
    "climbing": "\U0001faa2",  # 🪢 knot (climbing/twining)
    "mature": "\U0001f333",  # 🌳 deciduous tree
    "dormancy": "\u2744\ufe0f",  # ❄️ snowflake
    "senescence": "\U0001f342",  # 🍂 fallen leaf
    # Special phases
    "flushing": "\U0001f4a7",  # 💧 droplet (nutrient flush)
    "short_day_induction": "\U0001f319",  # 🌙 crescent moon
    "leaf_phase": "\U0001fab4",  # 🪴 potted plant (bulb leaf growth)
    # Post-harvest / transitions
    "drying": "\U0001f32c\ufe0f",  # 🌬️ wind
    "curing": "\U0001f3fa",  # 🏺 amphora
    "pre_sowing": "\U0001f3f7\ufe0f",  # 🏷️ label (preparation)
    "transplant": "\U0001f9f4",  # 🧴 bucket (repotting)
}

# Task category → emoji icon
_TASK_ICON: dict[str, str] = {
    "watering": "\U0001f4a7",  # droplet
    "feeding": "\U0001f9ed",  # test tube (nutrients)
    "maintenance": "\U0001f527",  # wrench
    "inspection": "\U0001f50d",  # magnifying glass
    "harvest": "\u2702\ufe0f",  # scissors
    "treatment": "\U0001f48a",  # pill (IPM)
    "training": "\u2702\ufe0f",  # scissors (HST)
    "transplant": "\U0001f9f4",  # bucket
    "measurement": "\U0001f4cf",  # ruler
    "observation": "\U0001f441\ufe0f",  # eye
    "care": "\U0001faa3",  # watering can (care reminder)
}


def _parse_dt(value: str | None) -> datetime | None:
    """Parse an ISO datetime string to a timezone-aware datetime."""
    if not value:
        return None
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _to_date(dt: datetime) -> date:
    """Convert datetime to date for all-day events."""
    return dt.date()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Kamerplanter calendar entities."""
    coordinators = entry.runtime_data.coordinators
    plant_coordinator: KamerplanterPlantCoordinator = coordinators["plants"]
    task_coordinator: KamerplanterTaskCoordinator = coordinators["tasks"]

    async_add_entities(
        [
            KamerplanterPhaseCalendar(plant_coordinator, entry),
            KamerplanterTaskCalendar(hass, entry, task_coordinator),
        ]
    )


class KamerplanterPhaseCalendar(CoordinatorEntity, CalendarEntity):
    """Calendar showing plant growth phases as multi-day events.

    Uses PlantCoordinator to show phases for ALL active plant instances,
    not just planting runs.
    """

    _attr_has_entity_name = True
    _attr_icon = "mdi:calendar-plant"

    def __init__(
        self,
        coordinator: KamerplanterPlantCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_kp_phases_calendar"
        self._attr_translation_key = "phases"
        self._attr_device_info = server_device_info(entry)

    def _build_events(self) -> list[CalendarEvent]:
        """Build calendar events from plant instance phase histories."""
        if not self.coordinator.data:
            return []

        events: list[CalendarEvent] = []
        now_date = date.today()

        for plant in self.coordinator.data:
            if plant.get("removed_on"):
                continue

            plant_name = (
                plant.get("plant_name")
                or plant.get("instance_id")
                or f"Plant {plant.get('key', '?')}"
            )
            history = plant.get("_phase_history", [])
            current_phase = plant.get("current_phase", "")

            for entry in history:
                phase_name = entry.get("phase_name", "")
                entered = _parse_dt(entry.get("entered_at"))
                exited = _parse_dt(entry.get("exited_at"))
                if not entered:
                    continue

                # Determine if this is the current phase
                is_current = phase_name.lower() == current_phase.lower() and (
                    exited is None or _to_date(exited) >= now_date
                )

                start_date = _to_date(entered)
                if exited:
                    end_date = _to_date(exited)
                elif is_current:
                    # Current phase with no end — show until today + 1
                    end_date = now_date
                else:
                    continue

                # Ensure end >= start
                if end_date < start_date:
                    end_date = start_date

                # Status
                if is_current:
                    status_label = _PHASE_STATUS_LABEL.get("current", "Aktiv")
                else:
                    status_label = _PHASE_STATUS_LABEL.get("completed", "Abgeschlossen")

                # Description
                desc_parts = [f"Status: {status_label}"]
                duration = entry.get("actual_duration_days")
                if duration:
                    desc_parts.append(f"Duration: {duration} days")
                desc_parts.append(f"Plant: {plant_name}")

                # Icon from phase name
                icon = _PHASE_ICON.get(phase_name.lower(), "\U0001f33f")
                display_name = phase_name.replace("_", " ").title()

                events.append(
                    CalendarEvent(
                        summary=f"{icon} {display_name} \u2014 {plant_name}",
                        start=start_date,
                        end=end_date,
                        description="\n".join(desc_parts),
                    )
                )

        return events

    @property
    def event(self) -> CalendarEvent | None:
        """Return the current or next upcoming event."""
        today = date.today()
        events = self._build_events()
        # Prefer current (active) events
        current = [e for e in events if e.start <= today <= e.end]
        if current:
            return current[0]
        # Fallback to next future event
        future = sorted(
            [e for e in events if e.start > today],
            key=lambda e: e.start,
        )
        return future[0] if future else None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return phase events overlapping the requested time range."""
        range_start = (
            start_date.date() if isinstance(start_date, datetime) else start_date
        )
        range_end = end_date.date() if isinstance(end_date, datetime) else end_date
        return [
            e
            for e in self._build_events()
            if e.end >= range_start and e.start <= range_end
        ]


class KamerplanterTaskCalendar(CalendarEntity):
    """Calendar showing pending tasks with due dates.

    Future: integrate with iCal feed (REQ-015 §4.2).
    """

    _attr_has_entity_name = True
    _attr_icon = "mdi:calendar-check"

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        coordinator: KamerplanterTaskCoordinator,
    ) -> None:
        self._entry = entry
        self._coordinator = coordinator
        self._unsub: Any = None
        self._attr_unique_id = f"{entry.entry_id}_kp_tasks_calendar"
        self._attr_translation_key = "tasks"
        self._attr_device_info = server_device_info(entry)

    def _build_events(self) -> list[CalendarEvent]:
        """Build calendar events from pending tasks."""
        if not self._coordinator.data:
            return []
        events: list[CalendarEvent] = []
        for task in self._coordinator.data:
            due = task.get("due_date")
            if not due:
                continue
            due_dt = _parse_dt(due)
            if not due_dt:
                continue
            due_date = _to_date(due_dt)
            raw_name = task.get("name") or task.get("title") or "Task"
            category = task.get("category", "").lower()
            icon = _TASK_ICON.get(category, "\U0001f4cc")
            name = f"{icon} {raw_name}"
            desc_parts: list[str] = []
            if task.get("instruction"):
                desc_parts.append(task["instruction"])
            if task.get("category"):
                desc_parts.append(f"Kategorie: {task['category']}")
            if task.get("priority"):
                desc_parts.append(f"Priorit\u00e4t: {task['priority']}")

            events.append(
                CalendarEvent(
                    summary=name,
                    start=due_date,
                    end=due_date,
                    description="\n".join(desc_parts) if desc_parts else None,
                )
            )
        return events

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming task event."""
        today = date.today()
        future = sorted(
            [e for e in self._build_events() if e.start >= today],
            key=lambda e: e.start,
        )
        return future[0] if future else None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return task events in the requested time range."""
        range_start = (
            start_date.date() if isinstance(start_date, datetime) else start_date
        )
        range_end = end_date.date() if isinstance(end_date, datetime) else end_date
        return [
            e
            for e in self._build_events()
            if e.end >= range_start and e.start <= range_end
        ]

    async def async_added_to_hass(self) -> None:
        """Register event listener (HA-NFR-005)."""
        self._unsub = self.hass.bus.async_listen(
            EVENT_TASK_COMPLETED, self._on_task_completed
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unregister event listener."""
        if self._unsub:
            self._unsub()

    @callback
    def _on_task_completed(self, event: Any) -> None:
        """Handle task completion — refresh calendar."""
        if event.data.get("entry_id") != self._entry.entry_id:
            return
        self.async_schedule_update_ha_state(force_refresh=True)
