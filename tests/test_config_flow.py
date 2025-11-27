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
    CONF_TARIFF_SOURCE,
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
    TARIFF_SOURCE_NONE,
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
            mock_api.get_cars = AsyncMock(side_effect=EVTrackerAuthenticationError("Invalid key"))
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
            mock_api.get_cars = AsyncMock(side_effect=EVTrackerConnectionError("Connection failed"))
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
            mock_api.get_cars = AsyncMock(side_effect=Exception("Unknown error"))
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
            mock_api.get_cars = AsyncMock(return_value=[])
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
            mock_api.get_cars = AsyncMock(return_value=mock_cars_response)
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
            mock_api.get_cars = AsyncMock(return_value=mock_cars_response)
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
            mock_api.get_cars = AsyncMock(return_value=mock_cars_response)
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
