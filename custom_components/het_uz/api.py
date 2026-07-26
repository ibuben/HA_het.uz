"""API client for het.uz."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import aiohttp

from .const import API_BASE_URL, USER_AGENT

_LOGGER = logging.getLogger(__name__)


class HetUzAuthError(Exception):
    """Authentication failed."""


class HetUzApiError(Exception):
    """API error."""


def _is_success(response: Any) -> bool:
    """Check if API response indicates success."""
    if isinstance(response, str):
        return "Successfully" in response
    if isinstance(response, dict):
        message = response.get("message", "")
        return "Successfully" in str(message) or "Successfully" in str(response)
    return False


class HetUzApi:
    """Client for the het.uz household consumer API."""

    def __init__(
        self,
        login: str,
        password: str,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        """Initialize the API client."""
        self._login = login
        self._password = password
        self._session = session
        self._own_session = session is None
        self._access_token: str | None = None
        self._coato_code: str | None = None
        self._token_expires_at: float | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            connector = aiohttp.TCPConnector(ssl=False)
            self._session = aiohttp.ClientSession(
                headers={"User-Agent": USER_AGENT},
                connector=connector,
            )
        return self._session

    async def close(self) -> None:
        """Close the HTTP session if owned by this client."""
        if self._own_session and self._session:
            await self._session.close()
            self._session = None

    def _is_token_valid(self) -> bool:
        if not self._access_token or self._token_expires_at is None:
            return False
        return self._token_expires_at > datetime.now(UTC).timestamp()

    def update_auth_from_storage(self, auth_data: dict[str, Any]) -> None:
        """Restore cached authentication from storage."""
        self._access_token = auth_data.get("access_token")
        self._coato_code = auth_data.get("coato_code")
        self._token_expires_at = auth_data.get("token_expires_at")

    def get_auth_for_storage(self) -> dict[str, Any]:
        """Return authentication data for persistent storage."""
        return {
            "access_token": self._access_token,
            "coato_code": self._coato_code,
            "token_expires_at": self._token_expires_at,
        }

    async def authenticate(self, *, force: bool = False) -> None:
        """Authenticate and cache the access token."""
        if not force and self._is_token_valid():
            return

        session = await self._get_session()
        url = f"{API_BASE_URL}/user-login"
        payload = {"login": self._login, "password": self._password}
        headers = {
            "Content-Type": "application/json",
            "Connection": "keep-alive",
            "Keep-Alive": "timeout=5, max=100",
        }

        try:
            async with session.post(
                url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                data = await response.json(content_type=None)
        except aiohttp.ClientError as err:
            raise HetUzApiError(f"Login request failed: {err}") from err

        if not _is_success(data):
            _LOGGER.debug("Login failed for account %s: %s", self._login, data)
            raise HetUzAuthError("Invalid login or password")

        token_data = data.get("data", {})
        self._access_token = token_data.get("accessToken")
        self._coato_code = token_data.get("coatoCode")
        expires_in = token_data.get("expiresIn", 3600)
        timestamp = data.get("timestamp", datetime.now(UTC).timestamp())
        self._token_expires_at = float(timestamp) + float(expires_in)

        if not self._access_token or not self._coato_code:
            raise HetUzAuthError("Incomplete authentication response")

    async def get_consumer_state(self) -> dict[str, Any]:
        """Fetch current consumer state from the API."""
        await self.authenticate()

        session = await self._get_session()
        url = f"{API_BASE_URL}/consumer-state"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Coato-Code": self._coato_code,
            "Connection": "keep-alive",
            "Keep-Alive": "timeout=5, max=100",
        }

        data = await self._request_consumer_state(session, url, headers)

        if not _is_success(data):
            await self.authenticate(force=True)
            headers["Authorization"] = f"Bearer {self._access_token}"
            headers["Coato-Code"] = self._coato_code
            data = await self._request_consumer_state(session, url, headers)

        if not _is_success(data):
            raise HetUzApiError(f"Failed to get consumer state: {data}")

        return data.get("data", {})

    async def _request_consumer_state(
        self,
        session: aiohttp.ClientSession,
        url: str,
        headers: dict[str, str],
    ) -> Any:
        try:
            async with session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                return await response.json(content_type=None)
        except aiohttp.ClientError as err:
            raise HetUzApiError(f"Consumer state request failed: {err}") from err
