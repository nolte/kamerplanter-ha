"""Unit tests for the module-level service helpers."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from custom_components.kamerplanter.helpers import (
    resolve_entry_id,
    resolve_plant_channel,
    resolve_tank_key,
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

    assert (
        resolve_tank_key(hass, {"entity_id": "sensor.kp_90639_volume"}) == "90639"
    )


def test_resolve_tank_key_from_entity_id_with_tank_prefix() -> None:
    """Long ``solution_age_days`` suffix wins over short ``volume`` prefix conflicts."""
    hass = _make_hass(states={"sensor.kp_tank_42_solution_age_days": _make_state(None)})

    assert (
        resolve_tank_key(
            hass, {"entity_id": "sensor.kp_tank_42_solution_age_days"}
        )
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
    state = _make_state(
        {"plant_key": "p-1", "channel_id": "drip_a"}
    )
    hass = _make_hass(states={"sensor.kp_p_1_drip_a_mix": state})

    assert resolve_plant_channel(
        hass, {"entity_id": "sensor.kp_p_1_drip_a_mix"}
    ) == ("p-1", "drip_a")


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

    assert resolve_plant_channel(
        hass, {"plant_key": "p", "channel_id": "drip_b"}
    ) == ("p", "drip_b")


def test_resolve_plant_channel_unresolvable_returns_none_pair() -> None:
    hass = _make_hass(states={"sensor.kp_unknown_mix": _make_state(None)})

    assert resolve_plant_channel(
        hass, {"entity_id": "sensor.kp_unknown_mix"}
    ) == (None, None)


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
        resolve_entry_id(hass, {"entity_id": "sensor.kp_x_volume"})
        == "entry-from-reg"
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
