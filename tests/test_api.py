"""Unit tests for the KamerplanterApi HTTP client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import ClientTimeout

from custom_components.kamerplanter.api import (
    DEFAULT_REQUEST_TIMEOUT,
    KamerplanterApi,
)


def _make_session() -> MagicMock:
    """Build an aiohttp.ClientSession mock that records the requested URL."""
    session = MagicMock()
    response = MagicMock()
    response.status = 200
    response.json = AsyncMock(return_value={})
    response.raise_for_status = MagicMock()
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=response)
    cm.__aexit__ = AsyncMock(return_value=None)
    session.request = MagicMock(return_value=cm)
    return session


def test_api_path_default() -> None:
    """Default api_path is /api with no trailing slash."""
    api = KamerplanterApi(base_url="http://host:8000", session=MagicMock())

    assert api.api_path == "/api"
    assert api._tenant_prefix == "/api/v1"


def test_api_path_custom_normalised() -> None:
    """Leading slash is enforced, trailing slash stripped."""
    api = KamerplanterApi(
        base_url="http://host:8000",
        session=MagicMock(),
        api_path="kamerplanter/api/",
    )

    assert api.api_path == "/kamerplanter/api"
    assert api._tenant_prefix == "/kamerplanter/api/v1"


def test_api_path_with_tenant_prefix() -> None:
    """Tenant prefix nests under the configured api_path."""
    api = KamerplanterApi(
        base_url="http://host:8000",
        session=MagicMock(),
        tenant_slug="garden",
        api_path="/proxy/api",
    )

    assert api._tenant_prefix == "/proxy/api/v1/t/garden"


def test_api_path_traversal_falls_back_to_default(caplog) -> None:
    """A `..` segment never reaches the wire — fallback to DEFAULT_API_PATH."""
    api = KamerplanterApi(
        base_url="http://host:8000",
        session=MagicMock(),
        api_path="/api/../admin",
    )

    assert api.api_path == "/api"
    assert any("Rejecting api_path" in rec.message for rec in caplog.records)


def test_api_path_query_string_falls_back_to_default(caplog) -> None:
    """Query-string injection in api_path is rejected at construction time."""
    api = KamerplanterApi(
        base_url="http://host:8000",
        session=MagicMock(),
        api_path="/api?inject=1",
    )

    assert api.api_path == "/api"


def test_api_path_double_slash_falls_back_to_default(caplog) -> None:
    """A protocol-relative leading `//host` is rejected."""
    api = KamerplanterApi(
        base_url="http://host:8000",
        session=MagicMock(),
        api_path="//evil.example.com/api",
    )

    assert api.api_path == "/api"


@pytest.mark.asyncio
async def test_health_url_uses_custom_api_path() -> None:
    """async_get_health hits {api_path}/health, not the hardcoded /api/health."""
    session = _make_session()
    api = KamerplanterApi(
        base_url="http://host:8000/",
        session=session,
        api_path="/kamerplanter/api",
    )

    await api.async_get_health()

    method, url = session.request.call_args.args[:2]
    assert method == "GET"
    assert url == "http://host:8000/kamerplanter/api/health"


@pytest.mark.asyncio
async def test_tenants_url_uses_custom_api_path() -> None:
    """async_get_tenants hits {api_path}/v1/tenants/."""
    session = _make_session()
    api = KamerplanterApi(
        base_url="http://host:8000",
        session=session,
        api_path="/proxy/api",
    )

    await api.async_get_tenants()

    _, url = session.request.call_args.args[:2]
    assert url == "http://host:8000/proxy/api/v1/tenants/"


@pytest.mark.asyncio
async def test_site_weather_forecast_hits_endpoint() -> None:
    """async_get_site_weather_forecast GETs {tenant}/sites/{key}/weather-forecast."""
    session = _make_session()
    api = KamerplanterApi(
        base_url="http://host:8000",
        session=session,
        tenant_slug="garden",
    )

    await api.async_get_site_weather_forecast("site-1")

    method, url = session.request.call_args.args[:2]
    assert method == "GET"
    assert url == "http://host:8000/api/v1/t/garden/sites/site-1/weather-forecast"


@pytest.mark.asyncio
async def test_start_task_hits_start_endpoint() -> None:
    """async_start_task POSTs to {tenant}/tasks/{key}/start."""
    session = _make_session()
    api = KamerplanterApi(
        base_url="http://host:8000",
        session=session,
        tenant_slug="garden",
    )

    await api.async_start_task("task-1")

    method, url = session.request.call_args.args[:2]
    assert method == "POST"
    assert url == "http://host:8000/api/v1/t/garden/tasks/task-1/start"


@pytest.mark.asyncio
async def test_complete_task_hits_complete_endpoint() -> None:
    """async_complete_task POSTs to {tenant}/tasks/{key}/complete."""
    session = _make_session()
    api = KamerplanterApi(
        base_url="http://host:8000",
        session=session,
        tenant_slug="garden",
    )

    await api.async_complete_task("task-1")

    method, url = session.request.call_args.args[:2]
    assert method == "POST"
    assert url == "http://host:8000/api/v1/t/garden/tasks/task-1/complete"


@pytest.mark.asyncio
async def test_skip_task_hits_skip_endpoint() -> None:
    """async_skip_task POSTs to {tenant}/tasks/{key}/skip."""
    session = _make_session()
    api = KamerplanterApi(
        base_url="http://host:8000",
        session=session,
        tenant_slug="garden",
    )

    await api.async_skip_task("task-1")

    method, url = session.request.call_args.args[:2]
    assert method == "POST"
    assert url == "http://host:8000/api/v1/t/garden/tasks/task-1/skip"


def _make_session_with_status(status: int, *, json_side_effect=None) -> MagicMock:
    """Build a session mock whose response carries a specific status code."""
    session = MagicMock()
    response = MagicMock()
    response.status = status
    response.raise_for_status = MagicMock()
    if json_side_effect is not None:
        response.json = AsyncMock(side_effect=json_side_effect)
    else:
        response.json = AsyncMock(return_value={"ok": True})
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=response)
    cm.__aexit__ = AsyncMock(return_value=None)
    session.request = MagicMock(return_value=cm)
    return session


@pytest.mark.asyncio
async def test_request_tolerates_204_no_content() -> None:
    """A 204 response (task actions) returns None instead of failing on json()."""
    session = _make_session_with_status(
        204, json_side_effect=AssertionError("json() must not be called on 204")
    )
    api = KamerplanterApi(
        base_url="http://host:8000", session=session, tenant_slug="garden"
    )

    result = await api.async_complete_task("task-1")

    assert result is None


@pytest.mark.asyncio
async def test_request_tolerates_non_json_body() -> None:
    """A 200 with an empty/non-JSON body decodes to None, not a connection error."""
    session = _make_session_with_status(200, json_side_effect=ValueError("no json"))
    api = KamerplanterApi(
        base_url="http://host:8000", session=session, tenant_slug="garden"
    )

    result = await api.async_start_task("task-1")

    assert result is None


@pytest.mark.asyncio
async def test_request_disables_redirects_by_default() -> None:
    """Bearer-token leaks via cross-host redirects are blocked at the client level."""
    session = _make_session()
    api = KamerplanterApi(base_url="http://host:8000", session=session)

    await api.async_get_health()

    kwargs = session.request.call_args.kwargs
    assert kwargs["allow_redirects"] is False


@pytest.mark.asyncio
async def test_request_applies_default_timeout() -> None:
    """Direct API callers (service handlers) get a per-request timeout."""
    session = _make_session()
    api = KamerplanterApi(base_url="http://host:8000", session=session)

    await api.async_get_health()

    kwargs = session.request.call_args.kwargs
    assert kwargs["timeout"] is DEFAULT_REQUEST_TIMEOUT


@pytest.mark.asyncio
async def test_request_respects_caller_overrides() -> None:
    """Explicit timeout / allow_redirects from callers are not clobbered."""
    session = _make_session()
    api = KamerplanterApi(base_url="http://host:8000", session=session)
    custom_timeout = ClientTimeout(total=5)

    await api._request(
        "GET", "/api/health", allow_redirects=True, timeout=custom_timeout
    )

    kwargs = session.request.call_args.kwargs
    assert kwargs["allow_redirects"] is True
    assert kwargs["timeout"] is custom_timeout
