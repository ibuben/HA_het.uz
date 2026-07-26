"""Config flow for HET.uz."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .api import HetUzApi, HetUzAuthError, HetUzApiError
from .const import CONF_LOGIN, CONF_PASSWORD, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_LOGIN): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required("scan_interval"): vol.All(
            vol.Coerce(int), vol.Range(min=300, max=86400)
        ),
    }
)


class HetUzConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HET.uz."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            login = user_input[CONF_LOGIN].strip()
            password = user_input[CONF_PASSWORD]

            await self.async_set_unique_id(login)
            self._abort_if_unique_id_configured()

            session = async_get_clientsession(self.hass, verify_ssl=False)
            api = HetUzApi(login=login, password=password, session=session)

            try:
                await api.authenticate(force=True)
                await api.get_consumer_state()
            except HetUzAuthError:
                errors["base"] = "invalid_auth"
            except (HetUzApiError, aiohttp.ClientError):
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during setup")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=f"HET.uz {login}",
                    data={
                        CONF_LOGIN: login,
                        CONF_PASSWORD: password,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return HetUzOptionsFlow()


class HetUzOptionsFlow(OptionsFlow):
    """Handle options for HET.uz."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options.get(
            "scan_interval",
            int(DEFAULT_SCAN_INTERVAL.total_seconds()),
        )

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA, {"scan_interval": current}
            ),
        )
