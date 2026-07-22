"""Tests for the Kamerplanter weather coordinator (issue #53).

The coordinator reads GET /sites/{site_key}/weather-forecast once per site and
exposes one flat frost-summary record per site. The backend is graceful: a site
without a forecast source returns 200 with the ``forecast_*`` fields set to
``None``.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.kamerplanter.api import (
    KamerplanterApi,
    KamerplanterAuthError,
    KamerplanterConnectionError,
)
from custom_components.kamerplanter.coordinator import KamerplanterWeatherCoordinator


def _mock_entry() -> MagicMock:
    entry = MagicMock()
    entry.options = {}
    entry.entry_id = "test"
    return entry


def _weather_api(
    *,
    sites: list[dict] | None = None,
    forecast: dict | None = None,
    forecast_side_effect: Exception | None = None,
) -> MagicMock:
    api = MagicMock(spec=KamerplanterApi)
    api.async_get_sites = AsyncMock(
        return_value=sites if sites is not None else [{"key": "site-1", "name": "Garden"}]
    )
    if forecast_side_effect is not None:
        api.async_get_site_weather_forecast = AsyncMock(
            side_effect=forecast_side_effect
        )
    else:
        api.async_get_site_weather_forecast = AsyncMock(return_value=forecast)
    return api


async def test_weather_coordinator_full_forecast(hass) -> None:
    """A site with a forecast produces a populated frost record."""
    api = _weather_api(
        sites=[{"key": "site-1", "name": "Garden", "type": "outdoor"}],
        forecast={
            "site_key": "site-1",
            "forecast_frost_warning": True,
            "forecast_min_temperature": -2.5,
            "forecast_expected_date": "2026-11-15",
            "forecast_source": "dwd",
        },
    )

    coord = KamerplanterWeatherCoordinator(hass, _mock_entry(), api)
    result = await coord._async_update_data()

    assert len(result) == 1
    rec = result[0]
    assert rec["key"] == "site-1"
    assert rec["name"] == "Garden"
    assert rec["type"] == "outdoor"
    assert rec["frost_warning"] is True
    assert rec["min_temperature"] == -2.5
    assert rec["expected_date"] == "2026-11-15"
    assert rec["source"] == "dwd"


async def test_weather_coordinator_graceful_none_forecast(hass) -> None:
    """A site whose forecast fields are all None yields a record with None fields."""
    api = _weather_api(
        forecast={
            "site_key": "site-1",
            "forecast_frost_warning": None,
            "forecast_min_temperature": None,
            "forecast_expected_date": None,
            "forecast_source": None,
        },
    )

    coord = KamerplanterWeatherCoordinator(hass, _mock_entry(), api)
    rec = (await coord._async_update_data())[0]

    assert rec["key"] == "site-1"
    assert rec["frost_warning"] is None
    assert rec["min_temperature"] is None


async def test_weather_coordinator_missing_forecast_is_non_fatal(hass) -> None:
    """A per-site forecast error still yields a record with None frost fields."""
    api = _weather_api(
        forecast_side_effect=KamerplanterConnectionError("site forecast down"),
    )

    coord = KamerplanterWeatherCoordinator(hass, _mock_entry(), api)
    result = await coord._async_update_data()

    assert len(result) == 1
    assert result[0]["key"] == "site-1"
    assert result[0]["frost_warning"] is None


async def test_weather_coordinator_empty_sites(hass) -> None:
    """No sites yields an empty record list, not an error."""
    api = _weather_api(sites=[])

    coord = KamerplanterWeatherCoordinator(hass, _mock_entry(), api)
    result = await coord._async_update_data()

    assert result == []
    api.async_get_site_weather_forecast.assert_not_called()


async def test_weather_coordinator_skips_keyless_site(hass) -> None:
    """A malformed site without a key is skipped, others still surface."""
    api = _weather_api(
        sites=[{"name": "no key"}, {"key": "site-2", "name": "Balcony"}],
        forecast={"forecast_frost_warning": False},
    )

    coord = KamerplanterWeatherCoordinator(hass, _mock_entry(), api)
    result = await coord._async_update_data()

    keys = {r["key"] for r in result}
    assert keys == {"site-2"}


async def test_weather_coordinator_auth_error(hass) -> None:
    """Auth errors on the sites read surface as ConfigEntryAuthFailed."""
    from homeassistant.exceptions import ConfigEntryAuthFailed

    api = MagicMock(spec=KamerplanterApi)
    api.async_get_sites = AsyncMock(side_effect=KamerplanterAuthError("expired"))

    coord = KamerplanterWeatherCoordinator(hass, _mock_entry(), api)
    with pytest.raises(ConfigEntryAuthFailed):
        await coord._async_update_data()


async def test_weather_coordinator_connection_error(hass) -> None:
    """Connection errors on the sites read surface as UpdateFailed."""
    from homeassistant.helpers.update_coordinator import UpdateFailed

    api = MagicMock(spec=KamerplanterApi)
    api.async_get_sites = AsyncMock(side_effect=KamerplanterConnectionError("down"))

    coord = KamerplanterWeatherCoordinator(hass, _mock_entry(), api)
    with pytest.raises(UpdateFailed):
        await coord._async_update_data()
