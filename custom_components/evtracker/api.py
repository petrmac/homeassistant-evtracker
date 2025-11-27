"""API client for EV Tracker."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import aiohttp

from .const import (
    DEFAULT_API_BASE_URL,
    ENDPOINT_CARS,
    ENDPOINT_CARS_DEFAULT,
    ENDPOINT_HA_STATE,
    ENDPOINT_SESSIONS,
    ENDPOINT_SESSIONS_SIMPLE,
    VERSION,
)

_LOGGER = logging.getLogger(__name__)


class EVTrackerApiError(Exception):
    """Base exception for EV Tracker API errors."""


class EVTrackerAuthenticationError(EVTrackerApiError):
    """Exception for authentication errors."""


class EVTrackerConnectionError(EVTrackerApiError):
    """Exception for connection errors."""


class EVTrackerRateLimitError(EVTrackerApiError):
    """Exception for rate limit errors."""


class EVTrackerAPI:
    """API client for EV Tracker."""

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_API_BASE_URL,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        """Initialize the API client."""
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._session = session
        self._owned_session = False

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            self._owned_session = True
        return self._session

    async def close(self) -> None:
        """Close the session if we own it."""
        if self._owned_session and self._session and not self._session.closed:
            await self._session.close()

    def _get_headers(self) -> dict[str, str]:
        """Get headers for API requests."""
        return {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"HomeAssistant-EVTracker/{VERSION}",
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make an API request."""
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        _LOGGER.debug("API request: %s %s", method, url)

        try:
            async with session.request(
                method,
                url,
                headers=headers,
                **kwargs,
            ) as response:
                _LOGGER.debug("API response status: %s", response.status)

                if response.status == 401:
                    raise EVTrackerAuthenticationError("Invalid API key")

                if response.status == 403:
                    raise EVTrackerAuthenticationError(
                        "API key lacks required permissions or PRO subscription required"
                    )

                if response.status == 429:
                    retry_after = response.headers.get("Retry-After", "60")
                    raise EVTrackerRateLimitError(
                        f"Rate limit exceeded. Retry after {retry_after} seconds"
                    )

                if response.status >= 500:
                    text = await response.text()
                    raise EVTrackerApiError(f"Server error: {response.status} - {text}")

                if response.status >= 400:
                    try:
                        error_data = await response.json()
                        error_msg = error_data.get("error", {}).get("message", "Unknown error")
                    except Exception:
                        error_msg = await response.text()
                    raise EVTrackerApiError(f"API error: {response.status} - {error_msg}")

                return await response.json()

        except aiohttp.ClientError as err:
            _LOGGER.error("Connection error: %s", err)
            raise EVTrackerConnectionError(f"Connection error: {err}") from err

    async def get_cars(self) -> list[dict[str, Any]]:
        """Get user's cars."""
        response = await self._request("GET", ENDPOINT_CARS)
        return response.get("data", [])

    async def get_default_car(self) -> dict[str, Any] | None:
        """Get user's default car."""
        response = await self._request("GET", ENDPOINT_CARS_DEFAULT)
        return response.get("data")

    async def get_state(self) -> dict[str, Any]:
        """Get Home Assistant state with all statistics."""
        response = await self._request("GET", ENDPOINT_HA_STATE)
        return response.get("data", {})

    async def log_session(
        self,
        energy_kwh: float,
        start_time: datetime | str | None = None,
        end_time: datetime | str | None = None,
        car_id: int | None = None,
        location: str | None = None,
        external_id: str | None = None,
        provider: str | None = None,
        energy_source: str | None = None,
        rate_type: str | None = None,
        price_per_kwh: float | None = None,
        vat_percentage: float | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Log a charging session with full control.

        Args:
            energy_kwh: Energy consumed in kWh
            start_time: When charging started
            end_time: When charging ended
            car_id: Car ID to associate with session
            location: Charging location
            external_id: External ID for idempotency
            provider: Charging provider (HOME, CEZ, EOON, etc.)
            energy_source: Energy source (GRID or SOLAR)
            rate_type: Tariff rate type (HIGH or LOW) for dual-rate electricity
            price_per_kwh: Price per kWh without VAT
            vat_percentage: VAT percentage
            notes: Additional notes
        """
        payload: dict[str, Any] = {
            "energyConsumedKwh": energy_kwh,
        }

        if start_time:
            if isinstance(start_time, datetime):
                payload["startTime"] = start_time.isoformat()
            else:
                payload["startTime"] = start_time

        if end_time:
            if isinstance(end_time, datetime):
                payload["endTime"] = end_time.isoformat()
            else:
                payload["endTime"] = end_time

        if car_id is not None:
            payload["carId"] = car_id

        if location:
            payload["location"] = location

        if external_id:
            payload["externalId"] = external_id

        if provider:
            payload["provider"] = provider

        if energy_source:
            payload["energySource"] = energy_source.upper()

        if rate_type:
            payload["rateType"] = rate_type.upper()

        if price_per_kwh is not None:
            payload["pricePerKwhWithoutVat"] = price_per_kwh

        if vat_percentage is not None:
            payload["vatPercentage"] = vat_percentage

        if notes:
            payload["notes"] = notes

        _LOGGER.debug("Logging session: %s", payload)

        response = await self._request("POST", ENDPOINT_SESSIONS, json=payload)
        return response.get("data", {})

    async def log_session_simple(
        self,
        energy_kwh: float,
        start_time: datetime | str | None = None,
        end_time: datetime | str | None = None,
        car_id: int | None = None,
        location: str | None = None,
        external_id: str | None = None,
        energy_source: str | None = None,
        rate_type: str | None = None,
    ) -> dict[str, Any]:
        """Log a charging session with smart defaults.

        Args:
            energy_kwh: Energy consumed in kWh (only required field)
            start_time: When charging started (estimated if not provided)
            end_time: When charging ended (defaults to now)
            car_id: Car ID (uses default car if not specified)
            location: Charging location (defaults to "Home")
            external_id: External ID for idempotency
            energy_source: Energy source (GRID or SOLAR) - can be mapped from HA sensor
            rate_type: Tariff rate type (HIGH or LOW) - can be mapped from HA sensor
        """
        payload: dict[str, Any] = {
            "energyConsumedKwh": energy_kwh,
        }

        if start_time:
            if isinstance(start_time, datetime):
                payload["startTime"] = start_time.isoformat()
            else:
                payload["startTime"] = start_time

        if end_time:
            if isinstance(end_time, datetime):
                payload["endTime"] = end_time.isoformat()
            else:
                payload["endTime"] = end_time

        if car_id is not None:
            payload["carId"] = car_id

        if location:
            payload["location"] = location

        if external_id:
            payload["externalId"] = external_id

        if energy_source:
            payload["energySource"] = energy_source.upper()

        if rate_type:
            payload["rateType"] = rate_type.upper()

        _LOGGER.debug("Logging simple session: %s", payload)

        response = await self._request("POST", ENDPOINT_SESSIONS_SIMPLE, json=payload)
        return response.get("data", {})

    async def validate_api_key(self) -> bool:
        """Validate the API key by fetching cars."""
        try:
            await self.get_cars()
            return True
        except EVTrackerAuthenticationError:
            return False
        except EVTrackerApiError as err:
            _LOGGER.warning("API key validation error: %s", err)
            return False
