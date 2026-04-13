"""Tests for the Kamerplanter diagnostics."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.kamerplanter.diagnostics import (
    async_get_config_entry_diagnostics,
)


async def test_diagnostics_redaction(hass) -> None:
    """Test that sensitive data is redacted in diagnostics."""
    # Build mock runtime_data
    mock_coordinators = {
        "plants": MagicMock(data=[], update_interval=MagicMock(total_seconds=MagicMock(return_value=300))),
        "locations": MagicMock(data=[], update_interval=MagicMock(total_seconds=MagicMock(return_value=300))),
        "runs": MagicMock(data=[], update_interval=MagicMock(total_seconds=MagicMock(return_value=300))),
        "alerts": MagicMock(data=[], update_interval=MagicMock(total_seconds=MagicMock(return_value=60))),
        "tasks": MagicMock(data=[], update_interval=MagicMock(total_seconds=MagicMock(return_value=300))),
    }

    mock_runtime = MagicMock()
    mock_runtime.coordinators = mock_coordinators

    mock_entry = MagicMock()
    mock_entry.data = {
        "url": "http://localhost:8000",
        "api_key": "kp_secret_key_12345",
        "tenant_slug": "test-tenant",
    }
    mock_entry.options = {"poll_interval_plants": 300}
    mock_entry.runtime_data = mock_runtime

    result = await async_get_config_entry_diagnostics(hass, mock_entry)

    # API key must be redacted
    assert result["entry_data"]["api_key"] == "**REDACTED**"
    # URL must be present
    assert result["entry_data"]["url"] == "http://localhost:8000"
    # Counts must be present
    assert result["plant_count"] == 0
    assert result["location_count"] == 0
