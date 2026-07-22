"""Tests for Lovelace resource auto-registration and YAML-mode handling."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.kamerplanter import (
    ISSUE_LOVELACE_YAML_MODE,
    NON_CARD_MODULES,
    _async_register_lovelace_resources,
)
from custom_components.kamerplanter.const import DOMAIN


class _StorageResources:
    """Stand-in for a writable ``ResourceStorageCollection`` (storage mode)."""

    def __init__(self, items: list[dict[str, str]]) -> None:
        self._items = list(items)
        self.loaded = True
        self.async_load = AsyncMock()
        self.created: list[str] = []

    def async_items(self) -> list[dict[str, str]]:
        return list(self._items)

    async def async_create_item(self, data: dict[str, str]) -> None:
        self._items.append({"id": str(len(self._items) + 1), **data})
        self.created.append(data["url"])


class _YamlResources:
    """Stand-in for the read-only YAML resource collection (no create method)."""

    def __init__(self, items: list[dict[str, str]]) -> None:
        self._items = list(items)
        self.loaded = True
        self.async_load = AsyncMock()

    def async_items(self) -> list[dict[str, str]]:
        return list(self._items)


def _hass(resources: object) -> MagicMock:
    hass = MagicMock()
    hass.data = {"lovelace": SimpleNamespace(resources=resources)}
    return hass


@pytest.mark.asyncio
async def test_storage_mode_registers_missing_resources() -> None:
    resources = _StorageResources([])
    hass = _hass(resources)

    with (
        patch(
            "homeassistant.helpers.issue_registry.async_create_issue"
        ) as create_issue,
        patch(
            "homeassistant.helpers.issue_registry.async_delete_issue"
        ) as delete_issue,
    ):
        await _async_register_lovelace_resources(hass, [Path("a.js"), Path("b.js")])

    assert resources.created == [f"/{DOMAIN}/a.js", f"/{DOMAIN}/b.js"]
    create_issue.assert_not_called()
    # A stale YAML-mode repair is cleared once storage registration succeeds.
    delete_issue.assert_called_once()


@pytest.mark.asyncio
async def test_shared_module_not_registered_as_resource() -> None:
    """The shared card module is served statically but is not a card.

    It must never be registered as a Lovelace resource (would pollute the card
    picker), while real cards in the same directory still get registered.
    """
    resources = _StorageResources([])
    hass = _hass(resources)

    js_files = [Path(name) for name in NON_CARD_MODULES]
    js_files.append(Path("kamerplanter-plant-card.js"))

    with (
        patch("homeassistant.helpers.issue_registry.async_create_issue"),
        patch("homeassistant.helpers.issue_registry.async_delete_issue"),
    ):
        await _async_register_lovelace_resources(hass, js_files)

    # Only the real card is registered; the shared module is filtered out.
    assert resources.created == [f"/{DOMAIN}/kamerplanter-plant-card.js"]
    for name in NON_CARD_MODULES:
        assert f"/{DOMAIN}/{name}" not in resources.created


@pytest.mark.asyncio
async def test_yaml_mode_missing_cards_raises_repair_issue() -> None:
    resources = _YamlResources([])
    hass = _hass(resources)

    with (
        patch(
            "homeassistant.helpers.issue_registry.async_create_issue"
        ) as create_issue,
        patch(
            "homeassistant.helpers.issue_registry.async_delete_issue"
        ) as delete_issue,
    ):
        await _async_register_lovelace_resources(hass, [Path("plant.js")])

    delete_issue.assert_not_called()
    create_issue.assert_called_once()
    args, kwargs = create_issue.call_args
    assert args[1] == DOMAIN
    assert args[2] == ISSUE_LOVELACE_YAML_MODE
    assert kwargs["is_fixable"] is False
    assert kwargs["translation_key"] == ISSUE_LOVELACE_YAML_MODE
    # The actionable snippet names the missing card URL.
    assert f"/{DOMAIN}/plant.js" in kwargs["translation_placeholders"]["resources"]


@pytest.mark.asyncio
async def test_yaml_mode_with_cards_present_clears_issue() -> None:
    resources = _YamlResources([{"id": "1", "url": f"/{DOMAIN}/plant.js"}])
    hass = _hass(resources)

    with (
        patch(
            "homeassistant.helpers.issue_registry.async_create_issue"
        ) as create_issue,
        patch(
            "homeassistant.helpers.issue_registry.async_delete_issue"
        ) as delete_issue,
    ):
        await _async_register_lovelace_resources(hass, [Path("plant.js")])

    create_issue.assert_not_called()
    delete_issue.assert_called_once()
