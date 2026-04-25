"""Tests for Lovelace resource cleanup on entry removal."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.kamerplanter import (
    _async_deregister_lovelace_resources,
    async_remove_entry,
)
from custom_components.kamerplanter.const import DOMAIN


class _StubResources:
    """Minimal stand-in for ``ResourceStorageCollection``."""

    def __init__(self, items: list[dict[str, str]]) -> None:
        self._items = list(items)
        self.loaded = True
        self.async_load = AsyncMock()
        self.deleted: list[str] = []

    def async_items(self) -> list[dict[str, str]]:
        return list(self._items)

    async def async_delete_item(self, item_id: str) -> None:
        self._items = [r for r in self._items if r["id"] != item_id]
        self.deleted.append(item_id)


@pytest.mark.asyncio
async def test_deregister_lovelace_resources_drops_only_owned_urls() -> None:
    resources = _StubResources(
        [
            {"id": "1", "url": f"/{DOMAIN}/card.js"},
            {"id": "2", "url": "/local/foreign.js"},
            {"id": "3", "url": f"/{DOMAIN}/other.js"},
        ]
    )
    hass = MagicMock()
    hass.data = {"lovelace": SimpleNamespace(resources=resources)}

    await _async_deregister_lovelace_resources(hass)

    assert resources.deleted == ["1", "3"]
    # Foreign Lovelace resource is left intact.
    assert any(r["url"] == "/local/foreign.js" for r in resources.async_items())


@pytest.mark.asyncio
async def test_async_remove_entry_keeps_resources_when_other_entries_remain() -> None:
    resources = _StubResources([{"id": "1", "url": f"/{DOMAIN}/card.js"}])
    hass = MagicMock()
    hass.data = {"lovelace": SimpleNamespace(resources=resources)}
    hass.config_entries.async_entries.return_value = [
        SimpleNamespace(entry_id="kept", domain=DOMAIN),
        SimpleNamespace(entry_id="removed", domain=DOMAIN),
    ]
    removed = SimpleNamespace(entry_id="removed", domain=DOMAIN)

    await async_remove_entry(hass, removed)

    assert resources.deleted == []  # other entry still uses the cards


@pytest.mark.asyncio
async def test_async_remove_entry_cleans_when_last_entry_disappears() -> None:
    resources = _StubResources(
        [
            {"id": "1", "url": f"/{DOMAIN}/card.js"},
            {"id": "2", "url": "/local/unrelated.js"},
        ]
    )
    hass = MagicMock()
    hass.data = {"lovelace": SimpleNamespace(resources=resources)}
    hass.config_entries.async_entries.return_value = [
        SimpleNamespace(entry_id="last", domain=DOMAIN),
    ]
    last = SimpleNamespace(entry_id="last", domain=DOMAIN)

    await async_remove_entry(hass, last)

    assert resources.deleted == ["1"]
