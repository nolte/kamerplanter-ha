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
from typing import TYPE_CHECKING, Any

from .const import DOMAIN

if TYPE_CHECKING:  # pragma: no cover — imports needed only for typing
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


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


def resolve_entry_id(
    hass: HomeAssistant, call_data: dict[str, Any]
) -> str | None:
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
