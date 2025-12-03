"""Tests for EV Tracker config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.evtracker.const import (
    CONF_API_KEY,
    CONF_CAR_ID,
    CONF_CAR_NAME,
    CONF_PRICE_HIGH,
    CONF_PRICE_LOW,
    CONF_TARIFF_ENTITY,
    CONF_TARIFF_LOW_END_1,
    CONF_TARIFF_LOW_END_2,
    CONF_TARIFF_LOW_START_1,
    CONF_TARIFF_LOW_START_2,
    CONF_TARIFF_SOURCE,
    CONF_TARIFF_WEEKEND_LOW,
    CONF_TARIFF_WINDOW_TYPE,
    CONF_UPDATE_INTERVAL,
    CONF_USE_PRICES,
    CONF_VAT_PERCENTAGE,
    DEFAULT_PRICE_HIGH,
    DEFAULT_PRICE_LOW,
    DEFAULT_USE_PRICES,
    DEFAULT_VAT_PERCENTAGE,
    DOMAIN,
    ERROR_CANNOT_CONNECT,
    ERROR_INVALID_API_KEY,
    ERROR_UNKNOWN,
    TARIFF_SOURCE_ENTITY,
    TARIFF_SOURCE_NONE,
    TARIFF_SOURCE_SCHEDULE,
    WINDOW_TYPE_LOW,
)


class TestConfigFlow:
    """Test config flow."""

    @pytest.mark.asyncio
    async def test_form_user_step(
        self,
        hass: HomeAssistant,
        auto_enable_custom_integrations,
    ):
        """Test user step shows form."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {}

    @pytest.mark.asyncio
    async def test_user_step_invalid_api_key(
        self,
        hass: HomeAssistant,
        auto_enable_custom_integrations,
    ):
        """Test handling invalid API key."""
        with patch("custom_components.evtracker.config_flow.EVTrackerAPI") as mock_api_class:
            from custom_components.evtracker.api import EVTrackerAuthenticationError

            mock_api = mock_api_class.return_value
            mock_api.get_cars_raw = AsyncMock(side_effect=EVTrackerAuthenticationError("Invalid key"))
            mock_api.close = AsyncMock()

            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_API_KEY: "invalid_key"},
            )

            assert result["type"] == FlowResultType.FORM
            assert result["errors"] == {"base": ERROR_INVALID_API_KEY}

    @pytest.mark.asyncio
    async def test_user_step_cannot_connect(
        self,
        hass: HomeAssistant,
        auto_enable_custom_integrations,
    ):
        """Test handling connection error."""
        with patch("custom_components.evtracker.config_flow.EVTrackerAPI") as mock_api_class:
            from custom_components.evtracker.api import EVTrackerConnectionError

            mock_api = mock_api_class.return_value
            mock_api.get_cars_raw = AsyncMock(side_effect=EVTrackerConnectionError("Connection failed"))
            mock_api.close = AsyncMock()

            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_API_KEY: "test_key"},
            )

            assert result["type"] == FlowResultType.FORM
            assert result["errors"] == {"base": ERROR_CANNOT_CONNECT}

    @pytest.mark.asyncio
    async def test_user_step_unknown_error(
        self,
        hass: HomeAssistant,
        auto_enable_custom_integrations,
    ):
        """Test handling unknown error."""
        with patch("custom_components.evtracker.config_flow.EVTrackerAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.get_cars_raw = AsyncMock(side_effect=Exception("Unknown error"))
            mock_api.close = AsyncMock()

            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_API_KEY: "test_key"},
            )

            assert result["type"] == FlowResultType.FORM
            assert result["errors"] == {"base": ERROR_UNKNOWN}

    @pytest.mark.asyncio
    async def test_user_step_no_cars(
        self,
        hass: HomeAssistant,
        auto_enable_custom_integrations,
    ):
        """Test handling no cars found."""
        with patch("custom_components.evtracker.config_flow.EVTrackerAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.get_cars_raw = AsyncMock(return_value=[])
            mock_api.close = AsyncMock()

            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_API_KEY: "test_key"},
            )

            assert result["type"] == FlowResultType.FORM
            assert result["errors"] == {"base": "no_cars"}

    @pytest.mark.asyncio
    async def test_user_step_success_to_car_selection(
        self,
        hass: HomeAssistant,
        auto_enable_custom_integrations,
        mock_cars_response: list[dict],
    ):
        """Test successful API key validation leads to car selection."""
        with patch("custom_components.evtracker.config_flow.EVTrackerAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.get_cars_raw = AsyncMock(return_value=mock_cars_response)
            mock_api.close = AsyncMock()

            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_API_KEY: "valid_key"},
            )

            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "select_car"

    @pytest.mark.asyncio
    async def test_car_selection_creates_entry(
        self,
        hass: HomeAssistant,
        auto_enable_custom_integrations,
        mock_cars_response: list[dict],
    ):
        """Test car selection creates config entry."""
        with patch("custom_components.evtracker.config_flow.EVTrackerAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.get_cars_raw = AsyncMock(return_value=mock_cars_response)
            mock_api.close = AsyncMock()

            # Start flow
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            # Enter API key
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_API_KEY: "valid_key"},
            )

            # Select car (value is string from SelectSelector)
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_CAR_ID: "123"},
            )

            assert result["type"] == FlowResultType.CREATE_ENTRY
            assert result["title"] == "EV Tracker - Test Tesla Model 3"
            assert result["data"] == {
                CONF_API_KEY: "valid_key",
                CONF_CAR_ID: 123,  # Converted back to int
                CONF_CAR_NAME: "Test Tesla Model 3",
            }

    @pytest.mark.asyncio
    async def test_car_already_configured(
        self,
        hass: HomeAssistant,
        auto_enable_custom_integrations,
        mock_cars_response: list[dict],
        mock_config_entry_data: dict,
    ):
        """Test that already configured car aborts."""
        # Create existing entry using MockConfigEntry
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="EV Tracker - Test Tesla Model 3",
            data=mock_config_entry_data,
            unique_id=f"{DOMAIN}_123",
        )
        entry.add_to_hass(hass)

        with patch("custom_components.evtracker.config_flow.EVTrackerAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.get_cars_raw = AsyncMock(return_value=mock_cars_response)
            mock_api.close = AsyncMock()

            # Start flow
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            # Enter API key
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_API_KEY: "valid_key"},
            )

            # Select same car (value is string from SelectSelector)
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_CAR_ID: "123"},
            )

            assert result["type"] == FlowResultType.ABORT
            assert result["reason"] == "already_configured"


class TestOptionsFlow:
    """Test options flow."""

    @pytest.mark.asyncio
    async def test_options_flow_init(
        self,
        hass: HomeAssistant,
        auto_enable_custom_integrations,
        mock_config_entry_data: dict,
    ):
        """Test options flow shows form."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="EV Tracker - Test",
            data=mock_config_entry_data,
            unique_id=f"{DOMAIN}_123",
        )
        entry.add_to_hass(hass)

        result = await hass.config_entries.options.async_init(entry.entry_id)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "init"

    @pytest.mark.asyncio
    async def test_options_flow_update(
        self,
        hass: HomeAssistant,
        auto_enable_custom_integrations,
        mock_config_entry_data: dict,
    ):
        """Test options flow updates interval through multi-step flow."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="EV Tracker - Test",
            data=mock_config_entry_data,
            unique_id=f"{DOMAIN}_123",
        )
        entry.add_to_hass(hass)

        # Step 1: Init - set update interval and tariff source
        result = await hass.config_entries.options.async_init(entry.entry_id)
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "init"

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {CONF_UPDATE_INTERVAL: 600},  # tariff_source defaults to "none"
        )

        # Step 2: Prices - complete with defaults
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "prices"

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {},  # Use all defaults for prices
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"] == {
            CONF_UPDATE_INTERVAL: 600,
            CONF_TARIFF_SOURCE: TARIFF_SOURCE_NONE,
            CONF_USE_PRICES: DEFAULT_USE_PRICES,
            CONF_PRICE_HIGH: DEFAULT_PRICE_HIGH,
            CONF_PRICE_LOW: DEFAULT_PRICE_LOW,
            CONF_VAT_PERCENTAGE: DEFAULT_VAT_PERCENTAGE,
        }

    @pytest.mark.asyncio
    async def test_options_flow_schedule_tariff_shows_form(
        self,
        hass: HomeAssistant,
        auto_enable_custom_integrations,
        mock_config_entry_data: dict,
    ):
        """Test options flow shows schedule tariff form when schedule selected."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="EV Tracker - Test",
            data=mock_config_entry_data,
            unique_id=f"{DOMAIN}_123",
        )
        entry.add_to_hass(hass)

        # Step 1: Init - select schedule tariff
        result = await hass.config_entries.options.async_init(entry.entry_id)
        assert result["step_id"] == "init"

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                CONF_UPDATE_INTERVAL: 300,
                CONF_TARIFF_SOURCE: TARIFF_SOURCE_SCHEDULE,
            },
        )

        # Should show tariff schedule form
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "tariff_schedule"

    @pytest.mark.asyncio
    async def test_options_flow_entity_tariff(
        self,
        hass: HomeAssistant,
        auto_enable_custom_integrations,
        mock_config_entry_data: dict,
    ):
        """Test options flow with entity tariff configuration."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="EV Tracker - Test",
            data=mock_config_entry_data,
            unique_id=f"{DOMAIN}_123",
        )
        entry.add_to_hass(hass)

        # Step 1: Init - select entity tariff
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                CONF_UPDATE_INTERVAL: 300,
                CONF_TARIFF_SOURCE: TARIFF_SOURCE_ENTITY,
            },
        )

        # Step 2: Entity selection
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "tariff_entity"

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                CONF_TARIFF_ENTITY: "binary_sensor.low_tariff",
            },
        )

        # Step 3: Prices
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "prices"

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {},
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_TARIFF_SOURCE] == TARIFF_SOURCE_ENTITY
        assert result["data"][CONF_TARIFF_ENTITY] == "binary_sensor.low_tariff"

    @pytest.mark.asyncio
    async def test_options_flow_prices_step(
        self,
        hass: HomeAssistant,
        auto_enable_custom_integrations,
        mock_config_entry_data: dict,
    ):
        """Test options flow prices step with custom values."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="EV Tracker - Test",
            data=mock_config_entry_data,
            unique_id=f"{DOMAIN}_123",
        )
        entry.add_to_hass(hass)

        # Step 1: Init
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {CONF_UPDATE_INTERVAL: 300},
        )

        # Step 2: Prices with custom values
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                CONF_USE_PRICES: True,
                CONF_PRICE_HIGH: 7.50,
                CONF_PRICE_LOW: 4.00,
                CONF_VAT_PERCENTAGE: 15.0,
            },
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_USE_PRICES] is True
        assert result["data"][CONF_PRICE_HIGH] == 7.50
        assert result["data"][CONF_PRICE_LOW] == 4.00
        assert result["data"][CONF_VAT_PERCENTAGE] == 15.0


class TestConfigFlowSelectCar:
    """Test car selection edge cases."""

    @pytest.mark.asyncio
    async def test_car_selection_fallback_name(
        self,
        hass: HomeAssistant,
        auto_enable_custom_integrations,
    ):
        """Test car selection with unknown car uses fallback name."""
        # Create response with car that will be selected but with different ID
        cars_response = [{"id": 999, "name": "Known Car"}]

        with patch("custom_components.evtracker.config_flow.EVTrackerAPI") as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.get_cars_raw = AsyncMock(return_value=cars_response)
            mock_api.close = AsyncMock()

            # Start flow
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            # Enter API key
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_API_KEY: "valid_key"},
            )

            # Manually set cars to simulate edge case where selected car_id doesn't match
            flow = hass.config_entries.flow._progress.get(result["flow_id"])
            flow._cars = [{"id": 888, "name": "Different Car"}]  # Car 999 won't be found

            # Select car 999 which won't be found in the list
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_CAR_ID: "999"},
            )

            assert result["type"] == FlowResultType.CREATE_ENTRY
            # Falls back to "Car 999" since car name not found
            assert result["data"][CONF_CAR_NAME] == "Car 999"


class TestOptionsFlowHandler:
    """Test OptionsFlowHandler methods."""

    @pytest.mark.asyncio
    async def test_get_options_flow_returns_handler(
        self,
        hass: HomeAssistant,
        auto_enable_custom_integrations,
        mock_config_entry_data: dict,
    ):
        """Test that async_get_options_flow returns the handler."""
        from custom_components.evtracker.config_flow import (
            EVTrackerConfigFlow,
            EVTrackerOptionsFlowHandler,
        )

        entry = MockConfigEntry(
            domain=DOMAIN,
            title="EV Tracker - Test",
            data=mock_config_entry_data,
            unique_id=f"{DOMAIN}_123",
        )

        handler = EVTrackerConfigFlow.async_get_options_flow(entry)

        assert isinstance(handler, EVTrackerOptionsFlowHandler)
        assert handler.config_entry == entry

