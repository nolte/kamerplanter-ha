"""Config flow for the Kamerplanter integration."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_URL
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    KamerplanterApi,
    KamerplanterAuthError,
    KamerplanterConnectionError,
)
from .const import (
    CONF_API_KEY,
    CONF_LIGHT_MODE,
    CONF_POLL_ALERTS,
    CONF_POLL_LOCATIONS,
    CONF_POLL_PLANTS,
    CONF_POLL_TASKS,
    CONF_TENANT_SLUG,
    DEFAULT_POLL_ALERTS,
    DEFAULT_POLL_LOCATIONS,
    DEFAULT_POLL_PLANTS,
    DEFAULT_POLL_TASKS,
    DOMAIN,
    MIN_POLL_ALERTS,
    MIN_POLL_LOCATIONS,
    MIN_POLL_PLANTS,
    MIN_POLL_TASKS,
)

_LOGGER = logging.getLogger(__name__)

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Optional(
            CONF_POLL_PLANTS,
            default=DEFAULT_POLL_PLANTS,
        ): vol.All(int, vol.Range(min=MIN_POLL_PLANTS)),
        vol.Optional(
            CONF_POLL_LOCATIONS,
            default=DEFAULT_POLL_LOCATIONS,
        ): vol.All(int, vol.Range(min=MIN_POLL_LOCATIONS)),
        vol.Optional(
            CONF_POLL_ALERTS,
            default=DEFAULT_POLL_ALERTS,
        ): vol.All(int, vol.Range(min=MIN_POLL_ALERTS)),
        vol.Optional(
            CONF_POLL_TASKS,
            default=DEFAULT_POLL_TASKS,
        ): vol.All(int, vol.Range(min=MIN_POLL_TASKS)),
    }
)


class KamerplanterConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Kamerplanter.

    Step 1 (user): URL + API key -- validates connection and credentials.
    Step 2 (tenant): Tenant selection from available tenants.
    Reauth: Re-enter API key when invalid/expired.
    Reconfigure: Change URL without removing the integration.
    """

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._base_url: str = ""
        self._api_key: str | None = None
        self._light_mode: bool = False
        self._server_version: str = ""
        self._tenants: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1: Enter Kamerplanter URL and API key."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._base_url = user_input[CONF_URL].rstrip("/")
            self._api_key = user_input.get(CONF_API_KEY) or None
            session = async_get_clientsession(self.hass)

            # Probe health endpoint (no auth needed)
            api_no_auth = KamerplanterApi(base_url=self._base_url, session=session)
            try:
                health = await api_no_auth.async_get_health()
                self._server_version = health.get("version", "unknown")
                server_mode = health.get("mode", "full")
                self._light_mode = server_mode == "light"
            except KamerplanterConnectionError:
                errors["base"] = "cannot_connect"
                return self.async_show_form(
                    step_id="user",
                    data_schema=self._user_schema(),
                    errors=errors,
                )

            # Light mode (REQ-027): LightAuthProvider skips authentication
            api = KamerplanterApi(
                base_url=self._base_url,
                session=session,
                api_key=self._api_key,
            )
            if not self._light_mode:
                if not self._api_key:
                    errors["base"] = "invalid_auth"
                    return self.async_show_form(
                        step_id="user",
                        data_schema=self._user_schema(),
                        errors=errors,
                    )
                try:
                    await api.async_get_current_user()
                except KamerplanterAuthError:
                    errors["base"] = "invalid_auth"
                    return self.async_show_form(
                        step_id="user",
                        data_schema=self._user_schema(),
                        errors=errors,
                    )

            # Fetch available tenants
            try:
                self._tenants = await api.async_get_tenants()
            except KamerplanterConnectionError:
                errors["base"] = "cannot_connect"
                return self.async_show_form(
                    step_id="user",
                    data_schema=self._user_schema(),
                    errors=errors,
                )

            if not self._tenants:
                errors["base"] = "no_tenants"
                return self.async_show_form(
                    step_id="user",
                    data_schema=self._user_schema(),
                    errors=errors,
                )

            # Single tenant: auto-select, skip step 2
            if len(self._tenants) == 1:
                tenant_slug = self._tenants[0]["slug"]
                await self.async_set_unique_id(f"{self._base_url}_{tenant_slug}")
                self._abort_if_unique_id_configured()
                return self._create_entry(tenant_slug=tenant_slug)

            # Multiple tenants: show selection
            return await self.async_step_tenant()

        return self.async_show_form(
            step_id="user",
            data_schema=self._user_schema(),
            errors=errors,
        )

    async def async_step_tenant(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2: Select tenant."""
        if user_input is not None:
            tenant_slug = user_input[CONF_TENANT_SLUG]
            await self.async_set_unique_id(f"{self._base_url}_{tenant_slug}")
            self._abort_if_unique_id_configured()
            return self._create_entry(tenant_slug=tenant_slug)

        tenant_options = {t["slug"]: t["name"] for t in self._tenants}
        schema = vol.Schema(
            {
                vol.Required(CONF_TENANT_SLUG): vol.In(tenant_options),
            }
        )
        return self.async_show_form(step_id="tenant", data_schema=schema)

    # --- Reauth Flow ---

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-authentication when API key is invalid."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask user for new API key."""
        errors: dict[str, str] = {}

        if user_input is not None:
            reauth_entry = self._get_reauth_entry()
            session = async_get_clientsession(self.hass)
            api = KamerplanterApi(
                base_url=reauth_entry.data[CONF_URL],
                session=session,
                api_key=user_input[CONF_API_KEY],
            )
            try:
                await api.async_get_current_user()
            except KamerplanterAuthError:
                errors["base"] = "invalid_auth"
            except KamerplanterConnectionError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={CONF_API_KEY: user_input[CONF_API_KEY]},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): str,
                }
            ),
            errors=errors,
        )

    # --- Reconfigure Flow ---

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration (URL change)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            new_url = user_input[CONF_URL].rstrip("/")
            session = async_get_clientsession(self.hass)
            api = KamerplanterApi(base_url=new_url, session=session)
            try:
                await api.async_get_health()
            except KamerplanterConnectionError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    self._get_reconfigure_entry(),
                    data_updates={CONF_URL: new_url},
                )

        reconfigure_entry = self._get_reconfigure_entry()
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_URL, default=reconfigure_entry.data.get(CONF_URL, "")
                    ): str,
                }
            ),
            errors=errors,
        )

    # --- Helpers ---

    @staticmethod
    def _user_schema() -> vol.Schema:
        """Build schema for step 1 (URL + API key)."""
        return vol.Schema(
            {
                vol.Required(CONF_URL, default="http://localhost:8000"): str,
                vol.Optional(CONF_API_KEY): str,
            }
        )

    def _create_entry(self, tenant_slug: str | None = None) -> ConfigFlowResult:
        title = "Kamerplanter"
        if tenant_slug:
            title = f"Kamerplanter ({tenant_slug})"

        data: dict[str, Any] = {
            CONF_URL: self._base_url,
            CONF_LIGHT_MODE: self._light_mode,
        }
        if self._api_key:
            data[CONF_API_KEY] = self._api_key
        if tenant_slug:
            data[CONF_TENANT_SLUG] = tenant_slug

        return self.async_create_entry(title=title, data=data)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigFlow) -> KamerplanterOptionsFlow:
        """Get the options flow handler."""
        return KamerplanterOptionsFlow()


class KamerplanterOptionsFlow(OptionsFlowWithReload):
    """Handle Kamerplanter options with automatic reload."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage polling interval options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA, self.config_entry.options
            ),
        )
