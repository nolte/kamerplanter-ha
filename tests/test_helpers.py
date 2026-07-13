"""Unit tests for the module-level service helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from custom_components.kamerplanter.helpers import (
    annotate_tasks_with_names,
    build_plant_name_index,
    plant_display_name,
    resolve_entry_id,
    resolve_plant_channel,
    resolve_tank_key,
    resolve_task_display_name,
    resolve_task_plant_name,
    slugify_label,
)


def _make_state(attrs: dict[str, object] | None) -> SimpleNamespace:
    """Build a minimal state stub compatible with `hass.states.get`."""
    return SimpleNamespace(attributes=attrs or {})


def _make_hass(*, states: dict[str, SimpleNamespace] | None = None) -> MagicMock:
    """Build a hass stub exposing ``states.get``, ``config_entries`` etc."""
    hass = MagicMock()
    hass.states.get.side_effect = lambda eid: (states or {}).get(eid)
    hass.config_entries.async_entries.return_value = []
    return hass


# --- slugify_label -----------------------------------------------------------


def test_slugify_label_strips_diacritics_and_punctuation() -> None:
    assert slugify_label("Drip A — 10L") == "drip_a_10l"
    assert slugify_label("Foliar Spray") == "foliar_spray"


# --- resolve_tank_key --------------------------------------------------------


def test_resolve_tank_key_from_state_attributes() -> None:
    hass = _make_hass(
        states={"sensor.kp_90639_info": _make_state({"tank_key": "tk-explicit"})}
    )

    assert (
        resolve_tank_key(hass, {"entity_id": "sensor.kp_90639_info"}) == "tk-explicit"
    )


def test_resolve_tank_key_from_entity_id_pattern() -> None:
    hass = _make_hass(states={"sensor.kp_90639_volume": _make_state(None)})

    assert resolve_tank_key(hass, {"entity_id": "sensor.kp_90639_volume"}) == "90639"


def test_resolve_tank_key_from_entity_id_with_tank_prefix() -> None:
    """Long ``solution_age_days`` suffix wins over short ``volume`` prefix conflicts."""
    hass = _make_hass(states={"sensor.kp_tank_42_solution_age_days": _make_state(None)})

    assert (
        resolve_tank_key(hass, {"entity_id": "sensor.kp_tank_42_solution_age_days"})
        == "42"
    )


def test_resolve_tank_key_falls_back_to_direct_key() -> None:
    hass = _make_hass()

    assert resolve_tank_key(hass, {"tank_key": "direct-7"}) == "direct-7"


def test_resolve_tank_key_unresolvable_returns_none() -> None:
    hass = _make_hass(states={"sensor.foreign": _make_state(None)})

    assert resolve_tank_key(hass, {"entity_id": "sensor.foreign"}) is None


# --- resolve_plant_channel ---------------------------------------------------


def test_resolve_plant_channel_from_state_attributes() -> None:
    state = _make_state({"plant_key": "p-1", "channel_id": "drip_a"})
    hass = _make_hass(states={"sensor.kp_p_1_drip_a_mix": state})

    assert resolve_plant_channel(hass, {"entity_id": "sensor.kp_p_1_drip_a_mix"}) == (
        "p-1",
        "drip_a",
    )


def test_resolve_plant_channel_from_entity_id_via_coordinator() -> None:
    plant = {
        "key": "plant-7",
        "_current_dosages": {"channels": [{"channel_id": "Drip A"}]},
    }
    coord = MagicMock()
    coord.data = [plant]
    entry = SimpleNamespace(
        runtime_data=SimpleNamespace(coordinators={"plants": coord})
    )
    hass = MagicMock()
    hass.states.get.return_value = _make_state(None)
    hass.config_entries.async_entries.return_value = [entry]

    plant_key, channel_id = resolve_plant_channel(
        hass, {"entity_id": "sensor.kp_plant_7_drip_a_mix"}
    )

    assert plant_key == "plant-7"
    assert channel_id == "Drip A"


def test_resolve_plant_channel_falls_back_to_direct_keys() -> None:
    hass = _make_hass()

    assert resolve_plant_channel(hass, {"plant_key": "p", "channel_id": "drip_b"}) == (
        "p",
        "drip_b",
    )


def test_resolve_plant_channel_unresolvable_returns_none_pair() -> None:
    hass = _make_hass(states={"sensor.kp_unknown_mix": _make_state(None)})

    assert resolve_plant_channel(hass, {"entity_id": "sensor.kp_unknown_mix"}) == (
        None,
        None,
    )


# --- resolve_entry_id --------------------------------------------------------


def test_resolve_entry_id_prefers_explicit_value() -> None:
    hass = _make_hass()

    assert resolve_entry_id(hass, {"entry_id": "abc"}) == "abc"


def test_resolve_entry_id_uses_entity_registry(monkeypatch) -> None:
    hass = MagicMock()
    hass.states.get.return_value = None
    hass.config_entries.async_entries.return_value = []

    registry = MagicMock()
    registry.async_get.return_value = SimpleNamespace(config_entry_id="entry-from-reg")

    from homeassistant.helpers import entity_registry as er

    monkeypatch.setattr(er, "async_get", lambda _hass: registry)

    assert (
        resolve_entry_id(hass, {"entity_id": "sensor.kp_x_volume"}) == "entry-from-reg"
    )


def test_resolve_entry_id_singleton_fallback() -> None:
    entry = SimpleNamespace(entry_id="only-one")
    hass = MagicMock()
    hass.config_entries.async_entries.return_value = [entry]
    hass.states.get.return_value = None

    assert resolve_entry_id(hass, {}) == "only-one"


def test_resolve_entry_id_ambiguous_returns_none() -> None:
    hass = MagicMock()
    hass.config_entries.async_entries.return_value = [
        SimpleNamespace(entry_id="a"),
        SimpleNamespace(entry_id="b"),
    ]
    hass.states.get.return_value = None

    assert resolve_entry_id(hass, {}) is None


# --- plant_display_name (issue #57) -----------------------------------------


def test_plant_display_name_prefers_nickname() -> None:
    plant = {
        "key": "11441519",
        "instance_id": "DRACA-0616-OWL",
        "plant_name": "Woody",
        "species": {
            "scientific_name": "Dracaena reflexa",
            "common_names": ["Drachenbaum"],
        },
    }

    assert plant_display_name(plant) == "Woody"


def test_plant_display_name_uses_first_common_name_when_no_nickname() -> None:
    """Drachenbaum case: nickname=None, first common name wins; code is NOT primary."""
    plant = {
        "key": "11441519",
        "instance_id": "DRACA-0616-OWL",
        "plant_name": None,
        "species": {
            "scientific_name": "Dracaena reflexa",
            "common_names": ["Drachenbaum", "Grünlilie"],
        },
    }

    name = plant_display_name(plant)

    assert name == "Drachenbaum"
    assert name != plant["instance_id"]


def test_plant_display_name_falls_back_to_scientific_name() -> None:
    plant = {
        "key": "k1",
        "instance_id": "MONST-0101-AAA",
        "plant_name": "   ",
        "species": {"scientific_name": "Monstera deliciosa", "common_names": []},
    }

    assert plant_display_name(plant) == "Monstera deliciosa"


def test_plant_display_name_falls_back_to_instance_id_when_species_none() -> None:
    plant = {
        "key": "k1",
        "instance_id": "SPATH-0617-XUB",
        "plant_name": None,
        "species": None,
    }

    assert plant_display_name(plant) == "SPATH-0617-XUB"


def test_plant_display_name_falls_back_to_key_as_last_resort() -> None:
    plant = {"key": "raw-key-only"}

    assert plant_display_name(plant) == "raw-key-only"


def test_plant_display_name_skips_blank_common_names() -> None:
    plant = {
        "key": "k1",
        "instance_id": "CODE-1",
        "species": {
            "scientific_name": "Ficus",
            "common_names": ["", "  ", "Birkenfeige"],
        },
    }

    assert plant_display_name(plant) == "Birkenfeige"


# --- task name resolution (issue #57) ---------------------------------------


def _drachenbaum() -> dict[str, object]:
    return {
        "key": "plant-key-1",
        "instance_id": "DRACA-0616-OWL",
        "plant_name": None,
        "species": {
            "scientific_name": "Dracaena reflexa",
            "common_names": ["Drachenbaum"],
        },
    }


def test_resolve_task_display_name_replaces_slug_via_entity_key() -> None:
    index = build_plant_name_index(
        [
            {
                "key": "plant-spath",
                "instance_id": "SPATH-0617-XUB",
                "plant_name": None,
                "species": {
                    "scientific_name": "Spathiphyllum wallisii",
                    "common_names": ["Einblatt"],
                },
            }
        ]
    )
    task = {
        "key": "task-1",
        "name": "SPATH-0617-XUB — watering",
        "category": "watering",
        "entity_key": "plant-spath",
    }

    label = resolve_task_display_name(task, index)

    assert label == "Einblatt — watering"
    assert "SPATH-0617-XUB" not in label


def test_resolve_task_plant_name_via_embedded_slug_head_token() -> None:
    """When entity_key is absent, the code slug in the name still resolves."""
    index = build_plant_name_index([_drachenbaum()])
    task = {"key": "t", "name": "DRACA-0616-OWL — pest_check"}

    assert resolve_task_plant_name(task, index) == "Drachenbaum"


def test_resolve_task_display_name_activity_from_category_when_no_separator() -> None:
    index = build_plant_name_index([_drachenbaum()])
    task = {
        "key": "t",
        "name": "DRACA-0616-OWL",
        "category": "pest_check",
        "entity_key": "plant-key-1",
    }

    assert resolve_task_display_name(task, index) == "Drachenbaum — pest check"


def test_resolve_task_display_name_keeps_raw_when_unresolvable() -> None:
    task = {"key": "t", "name": "UNKNOWN-9 — watering", "category": "watering"}

    assert resolve_task_display_name(task, {}) == "UNKNOWN-9 — watering"


def test_annotate_tasks_with_names_enriches_in_place() -> None:
    plants = [_drachenbaum()]
    tasks = [
        {
            "key": "t1",
            "name": "DRACA-0616-OWL — watering",
            "category": "watering",
            "entity_key": "plant-key-1",
        }
    ]

    annotate_tasks_with_names(tasks, plants)

    assert tasks[0]["plant_name"] == "Drachenbaum"
    assert tasks[0]["_display_name"] == "Drachenbaum — watering"


def test_annotate_tasks_with_names_tolerates_empty_inputs() -> None:
    tasks: list[dict[str, object]] = [{"key": "t", "name": "Raw name"}]

    annotate_tasks_with_names(tasks, None)

    # No plant match → no plant_name added, display falls back to raw name.
    assert "plant_name" not in tasks[0]
    assert tasks[0]["_display_name"] == "Raw name"
