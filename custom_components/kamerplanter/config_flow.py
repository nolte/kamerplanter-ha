"""Config flow for the Kamerplanter integration."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
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
    CONF_API_PATH,
    CONF_INSTANCE_ID,
    CONF_LIGHT_MODE,
    CONF_POLL_ALERTS,
    CONF_POLL_IPM,
    CONF_POLL_LOCATIONS,
    CONF_POLL_PLANTS,
    CONF_POLL_TASKS,
    CONF_POLL_WEATHER,
    CONF_TENANT_SLUG,
    DEFAULT_API_PATH,
    DEFAULT_POLL_ALERTS,
    DEFAULT_POLL_IPM,
    DEFAULT_POLL_LOCATIONS,
    DEFAULT_POLL_PLANTS,
    DEFAULT_POLL_TASKS,
    DEFAULT_POLL_WEATHER,
    DOMAIN,
    MIN_POLL_ALERTS,
    MIN_POLL_IPM,
    MIN_POLL_LOCATIONS,
    MIN_POLL_PLANTS,
    MIN_POLL_TASKS,
    MIN_POLL_WEATHER,
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
        vol.Optional(
            CONF_POLL_IPM,
            default=DEFAULT_POLL_IPM,
        ): vol.All(int, vol.Range(min=MIN_POLL_IPM)),
        vol.Optional(
            CONF_POLL_WEATHER,
            default=DEFAULT_POLL_WEATHER,
        ): vol.All(int, vol.Range(min=MIN_POLL_WEATHER)),
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
        self._api_path: str = DEFAULT_API_PATH
        self._light_mode: bool = False
        self._server_version: str = ""
        self._tenants: list[dict[str, Any]] = []
        self._instance_id: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1: Enter Kamerplanter URL and API key."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._base_url = user_input[CONF_URL].rstrip("/")
            self._api_key = user_input.get(CONF_API_KEY) or None
            session = async_get_clientsession(self.hass)

            # Probe health endpoint (no auth needed). Every API call in this
            # flow catches both error classes plus a broad fallback so a
            # behandelbarer Fehler never surfaces as a raw "unknown" abort.
            api_no_auth = KamerplanterApi(
                base_url=self._base_url,
                session=session,
                api_path=self._api_path,
            )
            try:
                health = await api_no_auth.async_get_health()
                self._server_version = health.get("version", "unknown")
                server_mode = health.get("mode", "full")
                self._light_mode = server_mode == "light"
            except KamerplanterAuthError:
                errors["base"] = "invalid_auth"
            except KamerplanterConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error probing Kamerplanter health")
                errors["base"] = "unknown"

            # Light mode (REQ-027): LightAuthProvider skips authentication
            api = KamerplanterApi(
                base_url=self._base_url,
                session=session,
                api_key=self._api_key,
                api_path=self._api_path,
            )
            if not errors and not self._light_mode:
                if not self._api_key:
                    errors["base"] = "invalid_auth"
                else:
                    try:
                        await api.async_get_current_user()
                    except KamerplanterAuthError:
                        errors["base"] = "invalid_auth"
                    except KamerplanterConnectionError:
                        errors["base"] = "cannot_connect"
                    except Exception:  # noqa: BLE001
                        _LOGGER.exception("Unexpected error validating credentials")
                        errors["base"] = "unknown"

            # Fetch available tenants
            if not errors:
                try:
                    self._tenants = await api.async_get_tenants()
                except KamerplanterAuthError:
                    errors["base"] = "invalid_auth"
                except KamerplanterConnectionError:
                    errors["base"] = "cannot_connect"
                except Exception:  # noqa: BLE001
                    _LOGGER.exception("Unexpected error fetching tenants")
                    errors["base"] = "unknown"

            if not errors and not self._tenants:
                errors["base"] = "no_tenants"

            if not errors:
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

    # --- Zeroconf Discovery Flow ---

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle mDNS/Zeroconf discovery of a Kamerplanter backend."""
        properties = discovery_info.properties

        instance_id = properties.get("instance_id", "")
        version = properties.get("version", "unknown")
        mode = properties.get("mode", "full")
        api_path = properties.get("api_path") or DEFAULT_API_PATH
        scheme = (properties.get("scheme") or "http").lower()
        if scheme not in ("http", "https"):
            scheme = "http"
        tenant = properties.get("tenant")

        if not instance_id:
            return self.async_abort(reason="missing_instance_id")

        self._api_path = api_path

        # Deduplicate by instance_id (+ tenant if provided)
        unique_suffix = f"{instance_id}_{tenant}" if tenant else instance_id
        await self.async_set_unique_id(unique_suffix)
        self._base_url = self._build_url(discovery_info, scheme=scheme)
        self._abort_if_unique_id_configured(
            updates={CONF_URL: self._base_url, CONF_API_PATH: self._api_path}
        )

        self._server_version = version
        self._light_mode = mode == "light"
        self._instance_id = instance_id

        self.context["title_placeholders"] = {
            "name": discovery_info.name.split(".")[0],
            "host": str(discovery_info.host) if discovery_info.host else "unknown",
        }

        # Health-check before showing dialog
        session = async_get_clientsession(self.hass)
        api_no_auth = KamerplanterApi(
            base_url=self._base_url,
            session=session,
            api_path=self._api_path,
        )
        try:
            await api_no_auth.async_get_health()
        except KamerplanterConnectionError:
            return self.async_abort(reason="cannot_connect")

        if tenant:
            self._tenants = [{"slug": tenant, "name": tenant}]

        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm discovered Kamerplanter instance and collect API key."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._api_key = user_input.get(CONF_API_KEY) or None

            if not self._light_mode:
                if not self._api_key:
                    errors["base"] = "invalid_auth"
                    return self.async_show_form(
                        step_id="discovery_confirm",
                        data_schema=self._discovery_confirm_schema(),
                        description_placeholders=self._discovery_placeholders(),
                        errors=errors,
                    )
                session = async_get_clientsession(self.hass)
                api = KamerplanterApi(
                    base_url=self._base_url,
                    session=session,
                    api_key=self._api_key,
                    api_path=self._api_path,
                )
                try:
                    await api.async_get_current_user()
                except KamerplanterAuthError:
                    errors["base"] = "invalid_auth"
                except KamerplanterConnectionError:
                    errors["base"] = "cannot_connect"
                except Exception:  # noqa: BLE001
                    _LOGGER.exception("Unexpected error validating credentials")
                    errors["base"] = "unknown"
                if errors:
                    return self.async_show_form(
                        step_id="discovery_confirm",
                        data_schema=self._discovery_confirm_schema(),
                        description_placeholders=self._discovery_placeholders(),
                        errors=errors,
                    )

            # Fetch tenants if not already known from TXT record
            if not self._tenants:
                session = async_get_clientsession(self.hass)
                api = KamerplanterApi(
                    base_url=self._base_url,
                    session=session,
                    api_key=self._api_key,
                    api_path=self._api_path,
                )
                try:
                    self._tenants = await api.async_get_tenants()
                except KamerplanterAuthError:
                    errors["base"] = "invalid_auth"
                except KamerplanterConnectionError:
                    errors["base"] = "cannot_connect"
                except Exception:  # noqa: BLE001
                    _LOGGER.exception("Unexpected error fetching tenants")
                    errors["base"] = "unknown"
                if errors:
                    return self.async_show_form(
                        step_id="discovery_confirm",
                        data_schema=self._discovery_confirm_schema(),
                        description_placeholders=self._discovery_placeholders(),
                        errors=errors,
                    )

                if not self._tenants:
                    return self.async_abort(reason="no_tenants")

                if len(self._tenants) > 1:
                    return await self.async_step_tenant()

            tenant_slug = self._tenants[0]["slug"]
            await self.async_set_unique_id(f"{self._instance_id}_{tenant_slug}")
            self._abort_if_unique_id_configured(
                updates={CONF_URL: self._base_url, CONF_API_PATH: self._api_path}
            )
            return self._create_entry(tenant_slug=tenant_slug)

        return self.async_show_form(
            step_id="discovery_confirm",
            data_schema=self._discovery_confirm_schema(),
            description_placeholders=self._discovery_placeholders(),
        )

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
                api_path=reauth_entry.data.get(CONF_API_PATH, DEFAULT_API_PATH),
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
        """Handle reconfiguration (URL and api_path)."""
        errors: dict[str, str] = {}
        reconfigure_entry = self._get_reconfigure_entry()

        if user_input is not None:
            new_url = user_input[CONF_URL].rstrip("/")
            new_api_path = (user_input.get(CONF_API_PATH) or DEFAULT_API_PATH).rstrip(
                "/"
            )
            existing_api_key = reconfigure_entry.data.get(CONF_API_KEY)
            session = async_get_clientsession(self.hass)
            api = KamerplanterApi(
                base_url=new_url,
                session=session,
                api_key=existing_api_key,
                api_path=new_api_path,
            )
            try:
                await api.async_get_health()
                # Re-validate the stored API key against the new endpoint so
                # the bearer token never gets reused against a foreign instance.
                if existing_api_key and not reconfigure_entry.data.get(CONF_LIGHT_MODE):
                    await api.async_get_current_user()
            except KamerplanterAuthError:
                errors["base"] = "invalid_auth"
            except KamerplanterConnectionError:
                errors["base"] = "cannot_connect"
            else:
                data_updates: dict[str, Any] = {CONF_URL: new_url}
                if new_api_path != DEFAULT_API_PATH:
                    data_updates[CONF_API_PATH] = new_api_path
                elif CONF_API_PATH in reconfigure_entry.data:
                    # Caller reset to default — drop the stored override.
                    data_updates[CONF_API_PATH] = DEFAULT_API_PATH

                # Keep a URL-derived unique_id in sync when the server URL
                # changes. User-flow entries key on "{url}_{tenant}"; leave
                # instance-based zeroconf unique_ids untouched.
                abort_kwargs: dict[str, Any] = {"data_updates": data_updates}
                old_url = reconfigure_entry.data.get(CONF_URL, "")
                tenant_slug = reconfigure_entry.data.get(CONF_TENANT_SLUG)
                if (
                    tenant_slug
                    and new_url != old_url
                    and reconfigure_entry.unique_id == f"{old_url}_{tenant_slug}"
                ):
                    new_unique_id = f"{new_url}_{tenant_slug}"
                    await self.async_set_unique_id(new_unique_id)
                    abort_kwargs["unique_id"] = new_unique_id

                return self.async_update_reload_and_abort(
                    reconfigure_entry,
                    **abort_kwargs,
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_URL, default=reconfigure_entry.data.get(CONF_URL, "")
                    ): str,
                    vol.Optional(
                        CONF_API_PATH,
                        default=reconfigure_entry.data.get(
                            CONF_API_PATH, DEFAULT_API_PATH
                        ),
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

    @staticmethod
    def _build_url(discovery_info: ZeroconfServiceInfo, scheme: str = "http") -> str:
        """Build base URL (scheme://host:port) from Zeroconf discovery info.

        Scheme defaults to ``http`` and is overridden by the ``scheme`` TXT
        property advertised by the backend. Only ``http`` and ``https`` are
        accepted; anything else is coerced to ``http`` by the caller.
        """
        host = str(discovery_info.host) if discovery_info.host else "unknown"
        port = discovery_info.port
        # IPv6 addresses in brackets
        if ":" in host:
            host = f"[{host}]"
        return f"{scheme}://{host}:{port}"

    def _discovery_confirm_schema(self) -> vol.Schema:
        """Schema for discovery confirmation (API key only)."""
        if self._light_mode:
            return vol.Schema({})
        return vol.Schema(
            {
                vol.Required(CONF_API_KEY): str,
            }
        )

    def _discovery_placeholders(self) -> dict[str, str]:
        """Placeholders for discovery confirmation description."""
        return {
            "url": self._base_url,
            "version": self._server_version,
            "mode": "Light" if self._light_mode else "Full",
        }

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
        if self._instance_id:
            data[CONF_INSTANCE_ID] = self._instance_id
        if self._api_path and self._api_path != DEFAULT_API_PATH:
            data[CONF_API_PATH] = self._api_path

        return self.async_create_entry(title=title, data=data)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> KamerplanterOptionsFlow:
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
