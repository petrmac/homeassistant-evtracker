"""Services for EV Tracker integration."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_CAR_ID,
    ATTR_END_TIME,
    ATTR_ENERGY_KWH,
    ATTR_ENERGY_SOURCE,
    ATTR_EXTERNAL_ID,
    ATTR_LOCATION,
    ATTR_NOTES,
    ATTR_PRICE_PER_KWH,
    ATTR_PROVIDER,
    ATTR_RATE_TYPE,
    ATTR_START_TIME,
    ATTR_VAT_PERCENTAGE,
    BINARY_SENSOR_LOW_TARIFF,
    CONF_PRICE_HIGH,
    CONF_PRICE_LOW,
    CONF_TARIFF_ENTITY,
    CONF_TARIFF_SOURCE,
    CONF_USE_PRICES,
    CONF_VAT_PERCENTAGE,
    DOMAIN,
    RATE_TYPE_HIGH,
    RATE_TYPE_LOW,
    SERVICE_LOG_SESSION,
    SERVICE_LOG_SESSION_SIMPLE,
    TARIFF_SOURCE_ENTITY,
    TARIFF_SOURCE_NONE,
    TARIFF_SOURCE_SCHEDULE,
)
from .coordinator import EVTrackerDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Service schemas
SERVICE_LOG_SESSION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENERGY_KWH): vol.Coerce(float),
        vol.Optional(ATTR_START_TIME): cv.datetime,
        vol.Optional(ATTR_END_TIME): cv.datetime,
        vol.Optional(ATTR_CAR_ID): vol.Coerce(int),
        vol.Optional(ATTR_LOCATION): cv.string,
        vol.Optional(ATTR_EXTERNAL_ID): cv.string,
        vol.Optional(ATTR_PROVIDER): cv.string,
        vol.Optional(ATTR_ENERGY_SOURCE): vol.In(["GRID", "SOLAR", "grid", "solar"]),
        vol.Optional(ATTR_RATE_TYPE): vol.In(["HIGH", "LOW", "high", "low"]),
        vol.Optional(ATTR_PRICE_PER_KWH): vol.Coerce(float),
        vol.Optional(ATTR_VAT_PERCENTAGE): vol.Coerce(float),
        vol.Optional(ATTR_NOTES): cv.string,
    }
)

SERVICE_LOG_SESSION_SIMPLE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENERGY_KWH): vol.Coerce(float),
        vol.Optional(ATTR_START_TIME): cv.datetime,
        vol.Optional(ATTR_END_TIME): cv.datetime,
        vol.Optional(ATTR_CAR_ID): vol.Coerce(int),
        vol.Optional(ATTR_LOCATION): cv.string,
        vol.Optional(ATTR_EXTERNAL_ID): cv.string,
        vol.Optional(ATTR_ENERGY_SOURCE): vol.In(["GRID", "SOLAR", "grid", "solar"]),
        vol.Optional(ATTR_RATE_TYPE): vol.In(["HIGH", "LOW", "high", "low"]),
    }
)


def _get_auto_rate_type(
    hass: HomeAssistant,
    coordinator: EVTrackerDataUpdateCoordinator,
) -> str | None:
    """Auto-detect rate_type from configured tariff sensor.

    Returns:
        "HIGH", "LOW", or None if tariff tracking is disabled.
    """
    # Get tariff source from config entry options
    config_entry = None
    for entry_id, coord in hass.data.get(DOMAIN, {}).items():
        if coord is coordinator:
            config_entry = hass.config_entries.async_get_entry(entry_id)
            break

    if not config_entry:
        return None

    tariff_source = config_entry.options.get(CONF_TARIFF_SOURCE, TARIFF_SOURCE_NONE)

    if tariff_source == TARIFF_SOURCE_NONE:
        return None

    if tariff_source == TARIFF_SOURCE_SCHEDULE:
        # Check the low tariff binary sensor we created
        entity_id = f"binary_sensor.evtracker_{coordinator.car_id}_{BINARY_SENSOR_LOW_TARIFF}"
        state = hass.states.get(entity_id)
        if state is None:
            _LOGGER.debug("Low tariff sensor not found: %s", entity_id)
            return None
        return RATE_TYPE_LOW if state.state == "on" else RATE_TYPE_HIGH

    if tariff_source == TARIFF_SOURCE_ENTITY:
        # Check the user-configured entity
        entity_id = config_entry.options.get(CONF_TARIFF_ENTITY)
        if not entity_id:
            return None
        state = hass.states.get(entity_id)
        if state is None:
            _LOGGER.debug("Tariff entity not found: %s", entity_id)
            return None
        # Consider "on", "true", "1", "low" as low tariff
        state_value = state.state.lower()
        is_low = state_value in ("on", "true", "1", "low", "yes")
        return RATE_TYPE_LOW if is_low else RATE_TYPE_HIGH

    return None


def _get_auto_prices(
    hass: HomeAssistant,
    coordinator: EVTrackerDataUpdateCoordinator,
    rate_type: str | None,
) -> tuple[float | None, float | None]:
    """Get auto-detected prices based on configured defaults and rate_type.

    Returns:
        Tuple of (price_per_kwh, vat_percentage) or (None, None) if not configured.
    """
    # Get config entry for this coordinator
    config_entry = None
    for entry_id, coord in hass.data.get(DOMAIN, {}).items():
        if coord is coordinator:
            config_entry = hass.config_entries.async_get_entry(entry_id)
            break

    if not config_entry:
        return None, None

    # Check if price configuration is enabled
    use_prices = config_entry.options.get(CONF_USE_PRICES, False)
    if not use_prices:
        return None, None

    # Get VAT percentage
    vat_percentage = config_entry.options.get(CONF_VAT_PERCENTAGE)

    # Get price based on rate_type
    if rate_type == RATE_TYPE_LOW:
        price_per_kwh = config_entry.options.get(CONF_PRICE_LOW)
    elif rate_type == RATE_TYPE_HIGH:
        price_per_kwh = config_entry.options.get(CONF_PRICE_HIGH)
    else:
        # No rate_type, use HIGH tariff price as default
        price_per_kwh = config_entry.options.get(CONF_PRICE_HIGH)

    # Only return prices if they are configured (> 0)
    if price_per_kwh is not None and price_per_kwh > 0:
        return price_per_kwh, vat_percentage

    return None, None


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up EV Tracker services."""

    async def handle_log_session(call: ServiceCall) -> None:
        """Handle log_session service call."""
        coordinators: list[EVTrackerDataUpdateCoordinator] = list(hass.data[DOMAIN].values())

        if not coordinators:
            _LOGGER.error("No EV Tracker integrations configured")
            return

        # Get car_id from call or use first coordinator's car
        car_id = call.data.get(ATTR_CAR_ID)
        coordinator = None

        if car_id:
            # Find coordinator for this car
            for coord in coordinators:
                if coord.car_id == car_id:
                    coordinator = coord
                    break
            if not coordinator:
                _LOGGER.error("No integration found for car_id: %s", car_id)
                return
        else:
            # Use first coordinator and its car_id
            coordinator = coordinators[0]
            car_id = coordinator.car_id

        # Get rate_type - use explicit value if provided, otherwise auto-detect
        rate_type = call.data.get(ATTR_RATE_TYPE)
        if rate_type is None:
            rate_type = _get_auto_rate_type(hass, coordinator)
            if rate_type:
                _LOGGER.debug("Auto-detected rate_type: %s", rate_type)

        # Get prices - use explicit values if provided, otherwise auto-detect
        price_per_kwh = call.data.get(ATTR_PRICE_PER_KWH)
        vat_percentage = call.data.get(ATTR_VAT_PERCENTAGE)
        if price_per_kwh is None:
            auto_price, auto_vat = _get_auto_prices(hass, coordinator, rate_type)
            if auto_price is not None:
                price_per_kwh = auto_price
                _LOGGER.debug("Auto-detected price_per_kwh: %s", price_per_kwh)
            if vat_percentage is None and auto_vat is not None:
                vat_percentage = auto_vat
                _LOGGER.debug("Auto-detected vat_percentage: %s", vat_percentage)

        try:
            result = await coordinator.api.log_session(
                energy_kwh=call.data[ATTR_ENERGY_KWH],
                start_time=call.data.get(ATTR_START_TIME),
                end_time=call.data.get(ATTR_END_TIME),
                car_id=car_id,
                location=call.data.get(ATTR_LOCATION),
                external_id=call.data.get(ATTR_EXTERNAL_ID),
                provider=call.data.get(ATTR_PROVIDER),
                energy_source=call.data.get(ATTR_ENERGY_SOURCE),
                rate_type=rate_type,
                price_per_kwh=price_per_kwh,
                vat_percentage=vat_percentage,
                notes=call.data.get(ATTR_NOTES),
            )
            _LOGGER.info("Successfully logged charging session: %s", result)

            # Refresh data after logging session
            await coordinator.async_request_refresh()

        except Exception as err:
            _LOGGER.error("Failed to log charging session: %s", err)
            raise

    async def handle_log_session_simple(call: ServiceCall) -> None:
        """Handle log_session_simple service call."""
        coordinators: list[EVTrackerDataUpdateCoordinator] = list(hass.data[DOMAIN].values())

        if not coordinators:
            _LOGGER.error("No EV Tracker integrations configured")
            return

        # Get car_id from call or use first coordinator's car
        car_id = call.data.get(ATTR_CAR_ID)
        coordinator = None

        if car_id:
            # Find coordinator for this car
            for coord in coordinators:
                if coord.car_id == car_id:
                    coordinator = coord
                    break
            if not coordinator:
                _LOGGER.error("No integration found for car_id: %s", car_id)
                return
        else:
            # Use first coordinator and its car_id
            coordinator = coordinators[0]
            car_id = coordinator.car_id

        # Get rate_type - use explicit value if provided, otherwise auto-detect
        rate_type = call.data.get(ATTR_RATE_TYPE)
        if rate_type is None:
            rate_type = _get_auto_rate_type(hass, coordinator)
            if rate_type:
                _LOGGER.debug("Auto-detected rate_type: %s", rate_type)

        try:
            result = await coordinator.api.log_session_simple(
                energy_kwh=call.data[ATTR_ENERGY_KWH],
                start_time=call.data.get(ATTR_START_TIME),
                end_time=call.data.get(ATTR_END_TIME),
                car_id=car_id,
                location=call.data.get(ATTR_LOCATION),
                external_id=call.data.get(ATTR_EXTERNAL_ID),
                energy_source=call.data.get(ATTR_ENERGY_SOURCE),
                rate_type=rate_type,
            )
            _LOGGER.info("Successfully logged simple charging session: %s", result)

            # Refresh data after logging session
            await coordinator.async_request_refresh()

        except Exception as err:
            _LOGGER.error("Failed to log simple charging session: %s", err)
            raise

    # Register services
    hass.services.async_register(
        DOMAIN,
        SERVICE_LOG_SESSION,
        handle_log_session,
        schema=SERVICE_LOG_SESSION_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_LOG_SESSION_SIMPLE,
        handle_log_session_simple,
        schema=SERVICE_LOG_SESSION_SIMPLE_SCHEMA,
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload EV Tracker services."""
    # Only unload services if no more config entries exist
    if not hass.data.get(DOMAIN):
        hass.services.async_remove(DOMAIN, SERVICE_LOG_SESSION)
        hass.services.async_remove(DOMAIN, SERVICE_LOG_SESSION_SIMPLE)
