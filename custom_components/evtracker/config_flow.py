"""Config flow for EV Tracker integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .api import (
    EVTrackerAPI,
    EVTrackerAuthenticationError,
    EVTrackerConnectionError,
)
from .const import (
    CONF_API_KEY,
    CONF_CAR_ID,
    CONF_CAR_NAME,
    CONF_PRICE_HIGH,
    CONF_PRICE_LOW,
    CONF_TARIFF_ENTITY,
    CONF_TARIFF_LOW_END_1,
    CONF_TARIFF_LOW_END_2,
    CONF_TARIFF_LOW_END_3,
    CONF_TARIFF_LOW_END_4,
    CONF_TARIFF_LOW_START_1,
    CONF_TARIFF_LOW_START_2,
    CONF_TARIFF_LOW_START_3,
    CONF_TARIFF_LOW_START_4,
    CONF_TARIFF_SOURCE,
    CONF_TARIFF_WEEKEND_LOW,
    CONF_TARIFF_WINDOW_TYPE,
    CONF_UPDATE_INTERVAL,
    CONF_USE_PRICES,
    CONF_VAT_PERCENTAGE,
    DEFAULT_PRICE_HIGH,
    DEFAULT_PRICE_LOW,
    DEFAULT_TARIFF_LOW_END_1,
    DEFAULT_TARIFF_LOW_END_2,
    DEFAULT_TARIFF_LOW_END_3,
    DEFAULT_TARIFF_LOW_END_4,
    DEFAULT_TARIFF_LOW_START_1,
    DEFAULT_TARIFF_LOW_START_2,
    DEFAULT_TARIFF_LOW_START_3,
    DEFAULT_TARIFF_LOW_START_4,
    DEFAULT_TARIFF_WINDOW_TYPE,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_USE_PRICES,
    DEFAULT_VAT_PERCENTAGE,
    DOMAIN,
    ERROR_CANNOT_CONNECT,
    ERROR_INVALID_API_KEY,
    ERROR_UNKNOWN,
    TARIFF_SOURCE_ENTITY,
    TARIFF_SOURCE_NONE,
    TARIFF_SOURCE_SCHEDULE,
    WINDOW_TYPE_HIGH,
    WINDOW_TYPE_LOW,
)

_LOGGER = logging.getLogger(__name__)


class EVTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EV Tracker."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._api_key: str | None = None
        self._cars: list[dict[str, Any]] = []

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step - API key entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api_key = user_input[CONF_API_KEY]
            api = EVTrackerAPI(api_key)

            try:
                # Validate API key by fetching cars
                self._cars = await api.get_cars_raw()
                self._api_key = api_key

                if not self._cars:
                    errors["base"] = "no_cars"
                else:
                    # Proceed to car selection
                    return await self.async_step_select_car()

            except EVTrackerAuthenticationError:
                errors["base"] = ERROR_INVALID_API_KEY
            except EVTrackerConnectionError:
                errors["base"] = ERROR_CANNOT_CONNECT
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error during API key validation")
                errors["base"] = ERROR_UNKNOWN
            finally:
                await api.close()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): str,
                }
            ),
            errors=errors,
        )

    async def async_step_select_car(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle car selection step."""
        if user_input is not None:
            # SelectSelector returns string, convert to int
            car_id = int(user_input[CONF_CAR_ID])
            car_name = next(
                (car["name"] for car in self._cars if car["id"] == car_id),
                f"Car {car_id}",
            )

            # Check if this car is already configured
            await self.async_set_unique_id(f"{DOMAIN}_{car_id}")
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"EV Tracker - {car_name}",
                data={
                    CONF_API_KEY: self._api_key,
                    CONF_CAR_ID: car_id,
                    CONF_CAR_NAME: car_name,
                },
            )

        # Build car options - value must be string for SelectSelector
        car_options = [
            selector.SelectOptionDict(value=str(car["id"]), label=car["name"]) for car in self._cars
        ]

        return self.async_show_form(
            step_id="select_car",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CAR_ID): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=car_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> EVTrackerOptionsFlowHandler:
        """Get the options flow handler."""
        return EVTrackerOptionsFlowHandler(config_entry)


class EVTrackerOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for EV Tracker."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self._tariff_source: str = TARIFF_SOURCE_NONE
        self._tariff_data: dict[str, Any] = {}
        self._update_interval: int = DEFAULT_UPDATE_INTERVAL

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """First step - basic settings and tariff source selection."""
        if user_input is not None:
            self._tariff_source = user_input.get(CONF_TARIFF_SOURCE, TARIFF_SOURCE_NONE)
            self._update_interval = user_input.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)

            if self._tariff_source == TARIFF_SOURCE_SCHEDULE:
                return await self.async_step_tariff_schedule()
            elif self._tariff_source == TARIFF_SOURCE_ENTITY:
                return await self.async_step_tariff_entity()
            else:
                # No tariff tracking - go to prices
                self._tariff_data = {CONF_TARIFF_SOURCE: TARIFF_SOURCE_NONE}
                return await self.async_step_prices()

        current_source = self.config_entry.options.get(CONF_TARIFF_SOURCE, TARIFF_SOURCE_NONE)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_UPDATE_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=60,
                            max=3600,
                            step=60,
                            unit_of_measurement="seconds",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Optional(
                        CONF_TARIFF_SOURCE,
                        default=current_source,
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(
                                    value=TARIFF_SOURCE_NONE,
                                    label="Disabled",
                                ),
                                selector.SelectOptionDict(
                                    value=TARIFF_SOURCE_SCHEDULE,
                                    label="Configure schedule",
                                ),
                                selector.SelectOptionDict(
                                    value=TARIFF_SOURCE_ENTITY,
                                    label="Use existing entity",
                                ),
                            ],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            translation_key="tariff_source",
                        )
                    ),
                }
            ),
        )

    async def async_step_tariff_schedule(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure tariff schedule with up to 4 time windows."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate time windows
            start1 = user_input.get(CONF_TARIFF_LOW_START_1, "")
            end1 = user_input.get(CONF_TARIFF_LOW_END_1, "")
            start2 = user_input.get(CONF_TARIFF_LOW_START_2, "")
            end2 = user_input.get(CONF_TARIFF_LOW_END_2, "")
            start3 = user_input.get(CONF_TARIFF_LOW_START_3, "")
            end3 = user_input.get(CONF_TARIFF_LOW_END_3, "")
            start4 = user_input.get(CONF_TARIFF_LOW_START_4, "")
            end4 = user_input.get(CONF_TARIFF_LOW_END_4, "")

            # Window 1 is required if using schedule
            if not start1 or not end1:
                errors["base"] = "window1_required"
            # Each window must have both start and end if either is set
            elif (
                (start2 and not end2)
                or (end2 and not start2)
                or (start3 and not end3)
                or (end3 and not start3)
                or (start4 and not end4)
                or (end4 and not start4)
            ):
                errors["base"] = "window_incomplete"
            else:
                # Store tariff data and proceed to prices
                self._tariff_data = {
                    CONF_TARIFF_SOURCE: TARIFF_SOURCE_SCHEDULE,
                    CONF_TARIFF_WINDOW_TYPE: user_input.get(
                        CONF_TARIFF_WINDOW_TYPE, WINDOW_TYPE_LOW
                    ),
                    CONF_TARIFF_LOW_START_1: start1,
                    CONF_TARIFF_LOW_END_1: end1,
                    CONF_TARIFF_LOW_START_2: start2,
                    CONF_TARIFF_LOW_END_2: end2,
                    CONF_TARIFF_LOW_START_3: start3,
                    CONF_TARIFF_LOW_END_3: end3,
                    CONF_TARIFF_LOW_START_4: start4,
                    CONF_TARIFF_LOW_END_4: end4,
                    CONF_TARIFF_WEEKEND_LOW: user_input.get(CONF_TARIFF_WEEKEND_LOW, False),
                }
                return await self.async_step_prices()

        return self.async_show_form(
            step_id="tariff_schedule",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_TARIFF_WINDOW_TYPE,
                        default=self.config_entry.options.get(
                            CONF_TARIFF_WINDOW_TYPE, DEFAULT_TARIFF_WINDOW_TYPE
                        ),
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(
                                    value=WINDOW_TYPE_LOW,
                                    label="Windows define LOW tariff periods",
                                ),
                                selector.SelectOptionDict(
                                    value=WINDOW_TYPE_HIGH,
                                    label="Windows define HIGH tariff periods",
                                ),
                            ],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            translation_key="window_type",
                        )
                    ),
                    vol.Required(
                        CONF_TARIFF_LOW_START_1,
                        default=self.config_entry.options.get(
                            CONF_TARIFF_LOW_START_1, DEFAULT_TARIFF_LOW_START_1
                        ),
                    ): selector.TimeSelector(),
                    vol.Required(
                        CONF_TARIFF_LOW_END_1,
                        default=self.config_entry.options.get(
                            CONF_TARIFF_LOW_END_1, DEFAULT_TARIFF_LOW_END_1
                        ),
                    ): selector.TimeSelector(),
                    vol.Optional(
                        CONF_TARIFF_LOW_START_2,
                        default=self.config_entry.options.get(
                            CONF_TARIFF_LOW_START_2, DEFAULT_TARIFF_LOW_START_2
                        ),
                    ): selector.TimeSelector(),
                    vol.Optional(
                        CONF_TARIFF_LOW_END_2,
                        default=self.config_entry.options.get(
                            CONF_TARIFF_LOW_END_2, DEFAULT_TARIFF_LOW_END_2
                        ),
                    ): selector.TimeSelector(),
                    vol.Optional(
                        CONF_TARIFF_LOW_START_3,
                        default=self.config_entry.options.get(
                            CONF_TARIFF_LOW_START_3, DEFAULT_TARIFF_LOW_START_3
                        ),
                    ): selector.TimeSelector(),
                    vol.Optional(
                        CONF_TARIFF_LOW_END_3,
                        default=self.config_entry.options.get(
                            CONF_TARIFF_LOW_END_3, DEFAULT_TARIFF_LOW_END_3
                        ),
                    ): selector.TimeSelector(),
                    vol.Optional(
                        CONF_TARIFF_LOW_START_4,
                        default=self.config_entry.options.get(
                            CONF_TARIFF_LOW_START_4, DEFAULT_TARIFF_LOW_START_4
                        ),
                    ): selector.TimeSelector(),
                    vol.Optional(
                        CONF_TARIFF_LOW_END_4,
                        default=self.config_entry.options.get(
                            CONF_TARIFF_LOW_END_4, DEFAULT_TARIFF_LOW_END_4
                        ),
                    ): selector.TimeSelector(),
                    vol.Optional(
                        CONF_TARIFF_WEEKEND_LOW,
                        default=self.config_entry.options.get(CONF_TARIFF_WEEKEND_LOW, False),
                    ): selector.BooleanSelector(),
                }
            ),
            errors=errors,
        )

    async def async_step_tariff_entity(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select an existing entity for tariff tracking."""
        if user_input is not None:
            # Store tariff data and proceed to prices
            self._tariff_data = {
                CONF_TARIFF_SOURCE: TARIFF_SOURCE_ENTITY,
                CONF_TARIFF_ENTITY: user_input.get(CONF_TARIFF_ENTITY),
            }
            return await self.async_step_prices()

        return self.async_show_form(
            step_id="tariff_entity",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_TARIFF_ENTITY,
                        default=self.config_entry.options.get(CONF_TARIFF_ENTITY),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["binary_sensor", "input_boolean", "sensor"],
                        )
                    ),
                }
            ),
        )

    async def async_step_prices(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Configure default prices for charging sessions."""
        if user_input is not None:
            # Combine all options and create entry
            data = {
                CONF_UPDATE_INTERVAL: self._update_interval,
                **self._tariff_data,
                CONF_USE_PRICES: user_input.get(CONF_USE_PRICES, DEFAULT_USE_PRICES),
                CONF_PRICE_HIGH: user_input.get(CONF_PRICE_HIGH, DEFAULT_PRICE_HIGH),
                CONF_PRICE_LOW: user_input.get(CONF_PRICE_LOW, DEFAULT_PRICE_LOW),
                CONF_VAT_PERCENTAGE: user_input.get(CONF_VAT_PERCENTAGE, DEFAULT_VAT_PERCENTAGE),
            }
            return self.async_create_entry(title="", data=data)

        return self.async_show_form(
            step_id="prices",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_USE_PRICES,
                        default=self.config_entry.options.get(CONF_USE_PRICES, DEFAULT_USE_PRICES),
                    ): selector.BooleanSelector(),
                    vol.Optional(
                        CONF_PRICE_HIGH,
                        default=self.config_entry.options.get(CONF_PRICE_HIGH, DEFAULT_PRICE_HIGH),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0,
                            max=100,
                            step=0.01,
                            unit_of_measurement="CZK/kWh",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Optional(
                        CONF_PRICE_LOW,
                        default=self.config_entry.options.get(CONF_PRICE_LOW, DEFAULT_PRICE_LOW),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0,
                            max=100,
                            step=0.01,
                            unit_of_measurement="CZK/kWh",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Optional(
                        CONF_VAT_PERCENTAGE,
                        default=self.config_entry.options.get(
                            CONF_VAT_PERCENTAGE, DEFAULT_VAT_PERCENTAGE
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0,
                            max=100,
                            step=0.1,
                            unit_of_measurement="%",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                }
            ),
        )
