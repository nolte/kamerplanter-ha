"""Module-level helpers for the Kamerplanter integration.

These resolvers translate user-facing service-call payloads (entity ids,
direct keys) into the underlying domain identifiers the API expects.
Extracted from `__init__.py` so they can be unit-tested without spinning up
a full Home Assistant instance.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from collections.abc import Mapping, MutableMapping, Sequence
from typing import TYPE_CHECKING, Any

from .const import DOMAIN

if TYPE_CHECKING:  # pragma: no cover — imports needed only for typing
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Separator the backend uses between the plant slug and the activity in a task
# name (e.g. ``"SPATH-0617-XUB — watering"``). An em dash flanked by spaces.
TASK_NAME_SEPARATOR: str = "—"

# Additional separators we tolerate when splitting the activity suffix off a
# raw task name (en dash, spaced hyphen).
_ACTIVITY_SEPARATORS: tuple[str, ...] = (TASK_NAME_SEPARATOR, "–", " - ")


# Suffixes used by tank entity unique-ids; order matters because longer
# suffixes must match before shorter prefixes.
TANK_ENTITY_SUFFIXES: tuple[str, ...] = (
    "_solution_age_days",
    "_alert_active",
    "_water_temp",
    "_fill_level",
    "_volume",
    "_info",
    "_ec",
    "_ph",
)
CHANNEL_SUFFIX: str = "_mix"


def slugify_label(text: str) -> str:
    """Slugify a free-text label into a stable entity-id fragment."""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", "_", text.lower())
    return text.strip("_")


def resolve_tank_key(hass: HomeAssistant, call_data: dict[str, Any]) -> str | None:
    """Resolve a tank key from service call data.

    Strategy 1: read ``tank_key`` from state attributes of the supplied
    ``entity_id``.
    Strategy 2: parse ``kp_<key>_<suffix>`` from the entity object id.
    Strategy 3: fall back to a directly supplied ``tank_key``.
    """
    entity_id = call_data.get("entity_id")
    if entity_id:
        entity_id = str(entity_id)
        state = hass.states.get(entity_id)
        if state and state.attributes.get("tank_key"):
            _LOGGER.debug("Resolved tank_key from state attributes")
            return str(state.attributes["tank_key"])

        object_id = entity_id.split(".", 1)[-1]
        if object_id.startswith("kp_"):
            rest = object_id[3:]
            if rest.startswith("tank_"):
                rest = rest[5:]
            for suffix in TANK_ENTITY_SUFFIXES:
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


def resolve_plant_channel(
    hass: HomeAssistant, call_data: dict[str, Any]
) -> tuple[str | None, str | None]:
    """Resolve a (plant_key, channel_id) pair from service call data.

    Strategy 1: read both fields from state attributes.
    Strategy 2: parse the entity_id and match against coordinator data.
    Strategy 3: fall back to direct ``plant_key`` / ``channel_id`` values.
    """
    entity_id = call_data.get("entity_id")
    if entity_id:
        entity_id = str(entity_id)
        state = hass.states.get(entity_id)
        if state:
            attrs = state.attributes or {}
            if attrs.get("plant_key") and attrs.get("channel_id"):
                _LOGGER.debug("Resolved plant/channel from state attributes")
                return str(attrs["plant_key"]), str(attrs["channel_id"])

        object_id = entity_id.split(".", 1)[-1]
        if object_id.startswith("kp_") and object_id.endswith(CHANNEL_SUFFIX):
            rest = object_id[3 : -len(CHANNEL_SUFFIX)]
            for entry in hass.config_entries.async_entries(DOMAIN):
                if not hasattr(entry, "runtime_data"):
                    continue
                plant_coord = entry.runtime_data.coordinators.get("plants")
                if not plant_coord or not plant_coord.data:
                    continue
                for plant in plant_coord.data:
                    pk = plant.get("key", "")
                    slug = pk.replace("-", "_").lower()
                    if not rest.startswith(slug + "_"):
                        continue
                    channel_slug = rest[len(slug) + 1 :]
                    dosage_data = plant.get("_current_dosages")
                    if not isinstance(dosage_data, dict):
                        continue
                    for ch in dosage_data.get("channels", []):
                        ch_id = ch.get("channel_id", "")
                        if slugify_label(ch_id) == channel_slug:
                            _LOGGER.debug(
                                "Resolved plant_key='%s', channel_id='%s' from entity_id",
                                pk,
                                ch_id,
                            )
                            return pk, ch_id

        _LOGGER.error("Could not resolve plant/channel from entity_id %s", entity_id)
        return None, None

    plant_key = call_data.get("plant_key")
    channel_id = call_data.get("channel_id")
    if plant_key:
        return str(plant_key), str(channel_id) if channel_id else None
    return None, None


def resolve_entry_id(hass: HomeAssistant, call_data: dict[str, Any]) -> str | None:
    """Resolve a Kamerplanter config-entry id from service call data.

    Order of resolution:
    1. Explicit ``entry_id`` in the payload.
    2. Lookup the entity in the entity registry and read its
       ``config_entry_id``.
    3. If exactly one Kamerplanter entry is configured, use it.
    Otherwise return ``None`` so the caller can surface an actionable error.
    """
    explicit = call_data.get("entry_id")
    if explicit:
        return str(explicit)

    entity_id = call_data.get("entity_id")
    if entity_id:
        from homeassistant.helpers import entity_registry as er

        registry = er.async_get(hass)
        entry = registry.async_get(str(entity_id))
        if entry and entry.config_entry_id:
            return entry.config_entry_id

    entries = list(hass.config_entries.async_entries(DOMAIN))
    if len(entries) == 1:
        return entries[0].entry_id
    return None


# ---------------------------------------------------------------------------
# Human-readable plant + task names (issue #57)
# ---------------------------------------------------------------------------
#
# The backend identifies a plant instance by a machine slug (``instance_id``,
# e.g. ``"DRACA-0616-OWL"``). These helpers turn a plant-instance record into a
# human-readable label following the operator-confirmed priority:
#
#   plant_name (nickname) > species.common_names[0] > species.scientific_name
#   > instance_id (code slug) > key
#
# and reconstruct task labels as ``"<readable name> — <activity>"`` so cards and
# calendars never surface the raw slug as the primary label.


def _first_nonempty(values: Sequence[Any] | None) -> str | None:
    """Return the first stripped, non-empty string from a sequence."""
    if not isinstance(values, (list, tuple)):
        return None
    for value in values:
        text = str(value).strip()
        if text:
            return text
    return None


def plant_display_name(plant: Mapping[str, Any]) -> str:
    """Return the human-readable primary label for a plant-instance record.

    Priority (each step falls through to the next when empty/missing):
    ``plant_name`` (user nickname) → ``species.common_names[0]`` (first
    trivial name) → ``species.scientific_name`` → ``instance_id`` (code slug)
    → ``key``. The result is never empty.
    """
    nickname = str(plant.get("plant_name") or "").strip()
    if nickname:
        return nickname

    species = plant.get("species")
    if isinstance(species, Mapping):
        common = _first_nonempty(species.get("common_names"))
        if common:
            return common
        scientific = str(species.get("scientific_name") or "").strip()
        if scientific:
            return scientific

    # Denormalized flat fallback (e.g. in-phase / run-plant response shapes).
    flat_common = _first_nonempty(plant.get("species_common_names"))
    if flat_common:
        return flat_common
    flat_scientific = str(plant.get("species_scientific_name") or "").strip()
    if flat_scientific:
        return flat_scientific

    instance_id = str(plant.get("instance_id") or "").strip()
    if instance_id:
        return instance_id

    return str(plant.get("key") or "").strip() or "Plant"


def plant_instance_code(plant: Mapping[str, Any]) -> str:
    """Return the code slug (``instance_id``) for use as a secondary subtitle."""
    return str(plant.get("instance_id") or plant.get("key") or "").strip()


def build_plant_name_index(
    plants: Sequence[Mapping[str, Any]] | None,
) -> dict[str, dict[str, str]]:
    """Index plant records by both ``key`` and ``instance_id``.

    Each entry maps to ``{"name": <readable>, "code": <instance_id>}`` so task
    resolution can look a plant up regardless of whether the reference carries
    the internal key (``entity_key``) or the embedded code slug (task name).
    """
    index: dict[str, dict[str, str]] = {}
    for plant in plants or []:
        if not isinstance(plant, Mapping):
            continue
        entry = {"name": plant_display_name(plant), "code": plant_instance_code(plant)}
        for token in (plant.get("key"), plant.get("instance_id")):
            token_str = str(token or "").strip()
            if token_str:
                index[token_str] = entry
    return index


def resolve_task_plant_name(
    task: Mapping[str, Any], index: Mapping[str, dict[str, str]]
) -> str | None:
    """Resolve the readable plant name a task refers to, or ``None``.

    Strategy 1: match ``entity_key`` (the plant instance key) against the index.
    Strategy 2: match the head token of the raw task name (the embedded code
    slug) against the index.
    """
    entity_key = str(task.get("entity_key") or "").strip()
    if entity_key and entity_key in index:
        return index[entity_key]["name"]

    raw = str(task.get("name") or task.get("name_de") or "")
    head = raw.split(TASK_NAME_SEPARATOR, 1)[0].strip()
    if head and head in index:
        return index[head]["name"]
    return None


def _task_activity(task: Mapping[str, Any], raw: str) -> str:
    """Extract the activity portion of a task (e.g. ``"watering"``)."""
    for sep in _ACTIVITY_SEPARATORS:
        if sep in raw:
            tail = raw.rsplit(sep, 1)[-1].strip()
            if tail:
                return tail
    fallback = task.get("category") or task.get("activity_key") or ""
    return str(fallback).replace("_", " ").strip()


def resolve_task_display_name(
    task: Mapping[str, Any], index: Mapping[str, dict[str, str]]
) -> str:
    """Reconstruct a task label as ``"<readable plant name> — <activity>"``.

    Falls back to the raw backend name (which may embed the slug) only when the
    task cannot be linked to a known plant instance, and never returns empty.
    """
    raw = str(
        task.get("name") or task.get("name_de") or task.get("title") or ""
    ).strip()
    plant_name = resolve_task_plant_name(task, index)
    activity = _task_activity(task, raw)
    if plant_name:
        if activity:
            return f"{plant_name} {TASK_NAME_SEPARATOR} {activity}"
        return plant_name
    return raw or activity or str(task.get("key") or "Task")


def annotate_tasks_with_names(
    tasks: Sequence[MutableMapping[str, Any]] | None,
    plants: Sequence[Mapping[str, Any]] | None,
) -> None:
    """Enrich task dicts in place with readable ``plant_name`` + ``_display_name``.

    ``plant_name`` carries the readable plant label alone (consumed by the
    aggregate task sensors / care card), while ``_display_name`` carries the
    full ``"<name> — <activity>"`` label (consumed by the todo list and task
    calendar). Both are safe to call on any task list; unresolved tasks keep
    their raw backend name.
    """
    index = build_plant_name_index(plants)
    for task in tasks or []:
        if not isinstance(task, MutableMapping):
            continue
        plant_name = resolve_task_plant_name(task, index)
        if plant_name:
            task["plant_name"] = plant_name
        task["_display_name"] = resolve_task_display_name(task, index)
