"""Todo entity for the Kamerplanter integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import EVENT_TASK_COMPLETED
from .coordinator import KamerplanterTaskCoordinator
from .entity import server_device_info

PARALLEL_UPDATES = 1  # Serialize task completions


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Kamerplanter todo entities."""
    task_coordinator: KamerplanterTaskCoordinator = entry.runtime_data.coordinators[
        "tasks"
    ]
    api = entry.runtime_data.api

    async_add_entities([KamerplanterTodoList(task_coordinator, entry, api)])


class KamerplanterTodoList(CoordinatorEntity, TodoListEntity):
    """Kamerplanter pending tasks as a Todo list."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:clipboard-check-outline"
    _attr_supported_features = TodoListEntityFeature.UPDATE_TODO_ITEM

    def __init__(
        self,
        coordinator: KamerplanterTaskCoordinator,
        entry: ConfigEntry,
        api: Any,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._api = api
        self._attr_unique_id = f"{entry.entry_id}_kp_todo"
        self._attr_translation_key = "tasks"
        self._attr_device_info = server_device_info(entry)

    @property
    def todo_items(self) -> list[TodoItem]:
        """Return current todo items from coordinator data."""
        if not self.coordinator.data:
            return []
        items: list[TodoItem] = []
        for task in self.coordinator.data:
            summary = task.get("name") or task.get("title") or "Untitled Task"

            # Build plain-text description
            desc_parts: list[str] = []
            if task.get("instruction"):
                desc_parts.append(task["instruction"])
            if task.get("category"):
                desc_parts.append(f"Kategorie: {task['category']}")
            if task.get("priority"):
                desc_parts.append(f"Priorit\u00e4t: {task['priority']}")
            if task.get("estimated_duration_minutes"):
                desc_parts.append(f"Dauer: {task['estimated_duration_minutes']} min")

            items.append(
                TodoItem(
                    uid=task["key"],
                    summary=summary,
                    description="\n".join(desc_parts) if desc_parts else None,
                    due=task.get("due_date"),
                    status=TodoItemStatus.NEEDS_ACTION,
                )
            )
        return items

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Mark a task as completed (HA-NFR-003: immediate state propagation)."""
        if item.uid and item.status == TodoItemStatus.COMPLETED:
            await self._api.async_complete_task(item.uid)

            # Fire event for cross-platform communication (HA-NFR-005)
            self.hass.bus.fire(
                EVENT_TASK_COMPLETED,
                {
                    "entry_id": self._entry.entry_id,
                    "task_key": item.uid,
                },
            )

            # Immediate refresh (HA-NFR-003)
            await self.coordinator.async_request_refresh()
