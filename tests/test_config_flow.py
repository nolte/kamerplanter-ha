"""Tests for the Kamerplanter config flow."""
from __future__ import annotations

from ipaddress import IPv4Address
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from custom_components.kamerplanter.const import (
    CONF_API_KEY,
    CONF_API_PATH,
    CONF_INSTANCE_ID,
    CONF_POLL_PLANTS,
    CONF_TENANT_SLUG,
    DOMAIN,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .conftest import load_fixture


@pytest.fixture(autouse=True)
def _bypass_integration_setup():
    """Stop HA from really setting up the entry after a successful flow.

    These tests assert the flow result, not the runtime setup. Without this,
    HA loads the created entry, the coordinator makes a real network call, and
    pytest-homeassistant-custom-component blocks the socket (HASocketBlockedError),
    failing the test in teardown.
    """
    with patch(
        "custom_components.kamerplanter.async_setup_entry", return_value=True
    ):
        yield


def _make_zeroconf_info(
    *,
    instance_id: str = "kp-homelab-01",
    version: str = "1.0.0",
    mode: str = "full",
    api_path: str = "/api",
    tenant: str | None = None,
    host: str = "192.168.1.42",
    port: int = 8000,
    scheme: str | None = None,
) -> ZeroconfServiceInfo:
    """Build a ZeroconfServiceInfo fixture matching the Kamerplanter TXT records."""
    properties: dict[str, str] = {
        "version": version,
        "mode": mode,
        "api_path": api_path,
    }
    if instance_id:
        properties["instance_id"] = instance_id
    if tenant is not None:
        properties["tenant"] = tenant
    if scheme is not None:
        properties["scheme"] = scheme

    ip = IPv4Address(host)
    return ZeroconfServiceInfo(
        ip_address=ip,
        ip_addresses=[ip],
        port=port,
        hostname=f"{instance_id or 'kamerplanter'}.local.",
        type="_kamerplanter._tcp.local.",
        name=f"Kamerplanter ({instance_id or 'unknown'})._kamerplanter._tcp.local.",
        properties=properties,
    )


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


# --- Zeroconf discovery flow ---


async def test_zeroconf_flow_success_full_mode(
    hass: HomeAssistant, mock_api_cls
) -> None:
    """Zeroconf discovery asks for API key and creates entry with instance_id."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=_make_zeroconf_info(),
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discovery_confirm"
    assert result["description_placeholders"]["url"] == "http://192.168.1.42:8000"
    assert result["description_placeholders"]["mode"] == "Full"
    assert result["description_placeholders"]["version"] == "1.0.0"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_API_KEY: "kp_test"},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_URL] == "http://192.168.1.42:8000"
    assert result["data"][CONF_API_KEY] == "kp_test"
    assert result["data"][CONF_INSTANCE_ID] == "kp-homelab-01"
    assert result["data"][CONF_TENANT_SLUG] == "garden"


async def test_zeroconf_flow_light_mode_skips_api_key(
    hass: HomeAssistant, mock_api_cls
) -> None:
    """In light mode the confirmation dialog creates the entry without an API key."""
    mock_api_cls.async_get_health.return_value = {
        "status": "healthy",
        "version": "1.0.0",
        "mode": "light",
    }

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=_make_zeroconf_info(mode="light"),
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discovery_confirm"
    assert result["description_placeholders"]["mode"] == "Light"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["light_mode"] is True
    assert CONF_API_KEY not in result["data"]


async def test_zeroconf_flow_missing_instance_id_aborts(
    hass: HomeAssistant, mock_api_cls
) -> None:
    """A discovery without instance_id TXT record must abort with a clear reason."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=_make_zeroconf_info(instance_id=""),
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "missing_instance_id"


async def test_zeroconf_flow_cannot_connect_aborts(
    hass: HomeAssistant, mock_api_cls
) -> None:
    """Discovery with an unreachable host aborts before prompting for credentials."""
    from custom_components.kamerplanter.api import KamerplanterConnectionError

    mock_api_cls.async_get_health.side_effect = KamerplanterConnectionError("fail")

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=_make_zeroconf_info(),
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"


async def test_zeroconf_flow_duplicate_instance_aborts(
    hass: HomeAssistant, mock_api_cls
) -> None:
    """A second discovery for a known instance_id aborts and refreshes the URL."""
    existing = MockConfigEntry(
        domain=DOMAIN,
        unique_id="kp-homelab-01",
        data={
            CONF_URL: "http://10.0.0.5:8000",
            CONF_API_KEY: "kp_existing",
            CONF_INSTANCE_ID: "kp-homelab-01",
            CONF_TENANT_SLUG: "garden",
            "light_mode": False,
        },
    )
    existing.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=_make_zeroconf_info(host="192.168.1.42"),
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert existing.data[CONF_URL] == "http://192.168.1.42:8000"


async def test_zeroconf_flow_tenant_txt_shortcut(
    hass: HomeAssistant, mock_api_cls
) -> None:
    """A tenant TXT record skips the tenant lookup and scopes the unique_id."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=_make_zeroconf_info(tenant="indoor"),
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_API_KEY: "kp_test"}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_TENANT_SLUG] == "indoor"
    assert mock_api_cls.async_get_tenants.await_count == 0


async def test_zeroconf_flow_default_api_path_not_persisted(
    hass: HomeAssistant, mock_api_cls
) -> None:
    """A default api_path of /api is not stored in the config entry data."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=_make_zeroconf_info(),
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_API_KEY: "kp_test"}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert CONF_API_PATH not in result["data"]


async def test_zeroconf_flow_custom_api_path_persisted(
    hass: HomeAssistant, mock_api_cls
) -> None:
    """A non-default api_path TXT (reverse-proxy prefix) is stored on the entry."""
    custom_path = "/kamerplanter/api"

    with patch(
        "custom_components.kamerplanter.config_flow.KamerplanterApi"
    ) as cls:
        instances: list[object] = []

        def factory(**kwargs):  # noqa: ANN001 — patch helper
            inst = cls.return_value
            instances.append(kwargs)
            return inst

        cls.side_effect = factory
        api = cls.return_value
        api.async_get_health = AsyncMock(return_value=load_fixture("health.json"))
        api.async_get_current_user = AsyncMock(
            return_value=load_fixture("user_me.json")
        )
        api.async_get_tenants = AsyncMock(
            return_value=[{"slug": "garden", "name": "My Garden"}]
        )

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_ZEROCONF},
            data=_make_zeroconf_info(api_path=custom_path),
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_API_KEY: "kp_test"}
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_API_PATH] == custom_path
    # Every API client constructed during the flow received the custom api_path
    assert instances, "expected at least one KamerplanterApi instantiation"
    assert all(call.get("api_path") == custom_path for call in instances)


async def test_zeroconf_flow_empty_api_path_falls_back_to_default(
    hass: HomeAssistant, mock_api_cls
) -> None:
    """An empty api_path TXT value is treated as the /api default."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=_make_zeroconf_info(api_path=""),
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_API_KEY: "kp_test"}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert CONF_API_PATH not in result["data"]


async def test_zeroconf_flow_https_scheme_from_txt(
    hass: HomeAssistant, mock_api_cls
) -> None:
    """An ``https`` scheme TXT property builds an https:// base URL."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=_make_zeroconf_info(scheme="https", port=8443),
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_API_KEY: "kp_test"}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_URL] == "https://192.168.1.42:8443"


async def test_zeroconf_flow_invalid_scheme_falls_back_to_http(
    hass: HomeAssistant, mock_api_cls
) -> None:
    """A bogus scheme value is coerced to http to prevent URL injection."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=_make_zeroconf_info(scheme="javascript"),
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_API_KEY: "kp_test"}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_URL].startswith("http://")


# --- Reconfigure flow ---


async def test_reconfigure_revalidates_api_key(
    hass: HomeAssistant, mock_api_cls
) -> None:
    """Pointing reconfigure at a different host re-checks /users/me before saving."""
    from custom_components.kamerplanter.api import KamerplanterAuthError

    existing = MockConfigEntry(
        domain=DOMAIN,
        unique_id="kp-homelab-01",
        data={
            CONF_URL: "http://10.0.0.5:8000",
            CONF_API_KEY: "kp_existing",
            CONF_INSTANCE_ID: "kp-homelab-01",
            CONF_TENANT_SLUG: "garden",
            "light_mode": False,
        },
    )
    existing.add_to_hass(hass)

    mock_api_cls.async_get_current_user.side_effect = KamerplanterAuthError("nope")

    result = await existing.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_URL: "http://10.0.0.99:8000"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_auth"
    # The original URL must remain — no silent token reuse against the new host.
    assert existing.data[CONF_URL] == "http://10.0.0.5:8000"


async def test_reconfigure_persists_api_path_change(
    hass: HomeAssistant, mock_api_cls
) -> None:
    """Reconfigure now accepts api_path and persists non-default values."""
    existing = MockConfigEntry(
        domain=DOMAIN,
        unique_id="kp-homelab-01",
        data={
            CONF_URL: "http://10.0.0.5:8000",
            CONF_API_KEY: "kp_existing",
            CONF_INSTANCE_ID: "kp-homelab-01",
            CONF_TENANT_SLUG: "garden",
            "light_mode": False,
        },
    )
    existing.add_to_hass(hass)

    result = await existing.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_URL: "http://10.0.0.5:8000",
            CONF_API_PATH: "/proxy/api",
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert existing.data[CONF_API_PATH] == "/proxy/api"
