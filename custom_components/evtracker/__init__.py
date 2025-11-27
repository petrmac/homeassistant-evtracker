"""EV Tracker integration for Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EVTrackerAPI
from .const import CONF_API_KEY, CONF_CAR_ID, CONF_CAR_NAME, DOMAIN
from .coordinator import EVTrackerDataUpdateCoordinator
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up EV Tracker from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Create API client using Home Assistant's session
    session = async_get_clientsession(hass)
    api = EVTrackerAPI(
        api_key=entry.data[CONF_API_KEY],
        session=session,
    )

    # Create coordinator
    coordinator = EVTrackerDataUpdateCoordinator(hass, api, entry)

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Set up services (only once)
    if len(hass.data[DOMAIN]) == 1:
        await async_setup_services(hass)

    # Register update listener for options
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    _LOGGER.info(
        "EV Tracker integration set up for car: %s (ID: %s)",
        entry.data[CONF_CAR_NAME],
        entry.data[CONF_CAR_ID],
    )

    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Remove coordinator
        hass.data[DOMAIN].pop(entry.entry_id)

        # Unload services if no more entries
        await async_unload_services(hass)

        _LOGGER.info(
            "EV Tracker integration unloaded for car: %s",
            entry.data[CONF_CAR_NAME],
        )

    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle removal of an entry."""
    _LOGGER.info(
        "EV Tracker integration removed for car: %s",
        entry.data[CONF_CAR_NAME],
    )
