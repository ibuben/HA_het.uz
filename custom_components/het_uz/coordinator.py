"""Data update coordinator for HET.uz."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import HetUzApi, HetUzApiError, HetUzAuthError
from .const import CONF_LOGIN, CONF_PASSWORD, DEFAULT_SCAN_INTERVAL, DOMAIN, STORAGE_AUTH

_LOGGER = logging.getLogger(__name__)


class HetUzDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for het.uz consumer state updates."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self.api = HetUzApi(
            login=entry.data[CONF_LOGIN],
            password=entry.data[CONF_PASSWORD],
            session=async_get_clientsession(hass, verify_ssl=False),
        )
        self._auth_store = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}.{STORAGE_AUTH}")

        scan_interval = entry.options.get(
            "scan_interval",
            int(DEFAULT_SCAN_INTERVAL.total_seconds()),
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_setup(self) -> None:
        """Load cached authentication token."""
        auth_data = await self._auth_store.async_load()
        if auth_data:
            self.api.update_auth_from_storage(auth_data)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the API."""
        try:
            data = await self.api.get_consumer_state()
        except HetUzAuthError as err:
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except HetUzApiError as err:
            raise UpdateFailed(str(err)) from err

        await self._auth_store.async_save(self.api.get_auth_for_storage())
        return data

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        await self.api.close()
