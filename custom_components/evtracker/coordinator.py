"""Data update coordinator for EV Tracker."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import EVTrackerAPI, EVTrackerApiError
from .const import (
    CONF_CAR_ID,
    CONF_CAR_NAME,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class EVTrackerDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching EV Tracker data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: EVTrackerAPI,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        self.api = api
        self.config_entry = config_entry
        self.car_id: int = config_entry.data[CONF_CAR_ID]
        self.car_name: str = config_entry.data[CONF_CAR_NAME]

        # Get update interval from options, or use default
        update_interval = config_entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self.car_id}",
            update_interval=timedelta(seconds=update_interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from EV Tracker API."""
        try:
            state = await self.api.get_state_raw()
            _LOGGER.debug("Fetched state data: %s", state)

            # Add connection status
            state["connected"] = True

            return state

        except EVTrackerApiError as err:
            _LOGGER.error("Error fetching EV Tracker data: %s", err)
            # Return partial data with connection status
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    @property
    def last_session(self) -> dict[str, Any] | None:
        """Get the last charging session."""
        if self.data:
            return self.data.get("lastSession")
        return None

    @property
    def current_month(self) -> dict[str, Any] | None:
        """Get current month statistics."""
        if self.data:
            return self.data.get("currentMonth")
        return None

    @property
    def current_year(self) -> dict[str, Any] | None:
        """Get current year statistics."""
        if self.data:
            return self.data.get("currentYear")
        return None

    @property
    def cars(self) -> list[dict[str, Any]]:
        """Get list of cars."""
        if self.data:
            return self.data.get("cars", [])
        return []

    @property
    def is_connected(self) -> bool:
        """Check if API is connected."""
        if self.data:
            return self.data.get("connected", False)
        return False
