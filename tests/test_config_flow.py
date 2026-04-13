"""Tests for the Kamerplanter config flow."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.kamerplanter.const import (
    CONF_API_KEY,
    CONF_POLL_PLANTS,
    CONF_TENANT_SLUG,
    DOMAIN,
)

from .conftest import load_fixture


@pytest.fixture
def mock_api_cls():
    """Patch the KamerplanterApi class in config_flow."""
    with patch(
        "custom_components.kamerplanter.config_flow.KamerplanterApi"
    ) as cls:
        api = cls.return_value
        api.async_get_health = AsyncMock(return_value=load_fixture("health.json"))
        api.async_get_current_user = AsyncMock(return_value=load_fixture("user_me.json"))
        api.async_get_tenants = AsyncMock(
            return_value=[{"slug": "garden", "name": "My Garden"}]
        )
        yield api


async def test_user_flow_success_single_tenant(
    hass: HomeAssistant, mock_api_cls
) -> None:
    """Test successful user config flow with single tenant."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_URL: "http://localhost:8000", CONF_API_KEY: "kp_test"},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Kamerplanter (garden)"
    assert result["data"][CONF_URL] == "http://localhost:8000"
    assert result["data"][CONF_API_KEY] == "kp_test"
    assert result["data"][CONF_TENANT_SLUG] == "garden"


async def test_user_flow_multi_tenant(
    hass: HomeAssistant, mock_api_cls
) -> None:
    """Test user flow with multiple tenants shows tenant step."""
    mock_api_cls.async_get_tenants.return_value = [
        {"slug": "garden-1", "name": "Garden 1"},
        {"slug": "garden-2", "name": "Garden 2"},
    ]

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_URL: "http://localhost:8000", CONF_API_KEY: "kp_test"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "tenant"


async def test_user_flow_cannot_connect(
    hass: HomeAssistant, mock_api_cls
) -> None:
    """Test user flow with connection error."""
    from custom_components.kamerplanter.api import KamerplanterConnectionError
    mock_api_cls.async_get_health.side_effect = KamerplanterConnectionError("fail")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_URL: "http://bad-host:8000", CONF_API_KEY: "kp_test"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"]["base"] == "cannot_connect"


async def test_user_flow_invalid_auth(
    hass: HomeAssistant, mock_api_cls
) -> None:
    """Test user flow with invalid API key."""
    from custom_components.kamerplanter.api import KamerplanterAuthError
    mock_api_cls.async_get_current_user.side_effect = KamerplanterAuthError("bad key")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_URL: "http://localhost:8000", CONF_API_KEY: "kp_bad"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_auth"


async def test_user_flow_no_tenants(
    hass: HomeAssistant, mock_api_cls
) -> None:
    """Test user flow when no tenants are available."""
    mock_api_cls.async_get_tenants.return_value = []

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_URL: "http://localhost:8000", CONF_API_KEY: "kp_test"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"]["base"] == "no_tenants"


async def test_user_flow_light_mode(
    hass: HomeAssistant, mock_api_cls
) -> None:
    """Test user flow in light mode (no API key required)."""
    mock_api_cls.async_get_health.return_value = {
        "status": "healthy",
        "version": "1.0.0",
        "mode": "light",
    }

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_URL: "http://localhost:8000"},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["light_mode"] is True


async def test_tenant_step(
    hass: HomeAssistant, mock_api_cls
) -> None:
    """Test tenant selection step."""
    mock_api_cls.async_get_tenants.return_value = [
        {"slug": "garden-1", "name": "Garden 1"},
        {"slug": "garden-2", "name": "Garden 2"},
    ]

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_URL: "http://localhost:8000", CONF_API_KEY: "kp_test"},
    )
    assert result["step_id"] == "tenant"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_TENANT_SLUG: "garden-2"},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_TENANT_SLUG] == "garden-2"
