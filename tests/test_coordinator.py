"""Tests for EV Tracker coordinator."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.evtracker.api import EVTrackerApiError
from custom_components.evtracker.const import (
    CONF_API_KEY,
    CONF_CAR_ID,
    CONF_CAR_NAME,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
)
from custom_components.evtracker.coordinator import EVTrackerDataUpdateCoordinator


class TestEVTrackerDataUpdateCoordinator:
    """Test EVTrackerDataUpdateCoordinator."""

    @pytest.fixture
    def mock_config_entry(
        self,
        mock_api_key: str,
        mock_car_id: int,
        mock_car_name: str,
    ) -> MagicMock:
        """Create a mock config entry."""
        entry = MagicMock()
        entry.data = {
            CONF_API_KEY: mock_api_key,
            CONF_CAR_ID: mock_car_id,
            CONF_CAR_NAME: mock_car_name,
        }
        entry.options = {}
        return entry

    @pytest.fixture
    def mock_api_instance(self, mock_state_response: dict) -> AsyncMock:
        """Create a mock API instance."""
        api = AsyncMock()
        api.get_state = AsyncMock(return_value=mock_state_response)
        return api

    def test_coordinator_init(
        self,
        hass: HomeAssistant,
        mock_api_instance: AsyncMock,
        mock_config_entry: MagicMock,
        mock_car_id: int,
        mock_car_name: str,
    ):
        """Test coordinator initialization."""
        coordinator = EVTrackerDataUpdateCoordinator(hass, mock_api_instance, mock_config_entry)

        assert coordinator.car_id == mock_car_id
        assert coordinator.car_name == mock_car_name
        assert coordinator.update_interval == timedelta(seconds=DEFAULT_UPDATE_INTERVAL)

    def test_coordinator_custom_interval(
        self,
        hass: HomeAssistant,
        mock_api_instance: AsyncMock,
        mock_config_entry: MagicMock,
    ):
        """Test coordinator with custom update interval."""
        mock_config_entry.options = {CONF_UPDATE_INTERVAL: 600}

        coordinator = EVTrackerDataUpdateCoordinator(hass, mock_api_instance, mock_config_entry)

        assert coordinator.update_interval == timedelta(seconds=600)

    @pytest.mark.asyncio
    async def test_async_update_data_success(
        self,
        hass: HomeAssistant,
        mock_api_instance: AsyncMock,
        mock_config_entry: MagicMock,
        mock_state_response: dict,
    ):
        """Test successful data update."""
        coordinator = EVTrackerDataUpdateCoordinator(hass, mock_api_instance, mock_config_entry)

        data = await coordinator._async_update_data()

        assert data["connected"] is True
        assert data["currentMonth"] == mock_state_response["currentMonth"]
        assert data["currentYear"] == mock_state_response["currentYear"]
        assert data["lastSession"] == mock_state_response["lastSession"]
        mock_api_instance.get_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_update_data_api_error(
        self,
        hass: HomeAssistant,
        mock_api_instance: AsyncMock,
        mock_config_entry: MagicMock,
    ):
        """Test data update with API error."""
        mock_api_instance.get_state = AsyncMock(side_effect=EVTrackerApiError("API Error"))

        coordinator = EVTrackerDataUpdateCoordinator(hass, mock_api_instance, mock_config_entry)

        with pytest.raises(UpdateFailed) as exc_info:
            await coordinator._async_update_data()

        assert "Error communicating with API" in str(exc_info.value)


class TestCoordinatorProperties:
    """Test coordinator property methods."""

    @pytest.fixture
    def coordinator_with_data(
        self,
        hass: HomeAssistant,
        mock_state_response: dict,
        mock_car_id: int,
        mock_car_name: str,
    ) -> EVTrackerDataUpdateCoordinator:
        """Create a coordinator with data."""
        mock_api = AsyncMock()
        mock_entry = MagicMock()
        mock_entry.data = {
            CONF_API_KEY: "test_key",
            CONF_CAR_ID: mock_car_id,
            CONF_CAR_NAME: mock_car_name,
        }
        mock_entry.options = {}

        coordinator = EVTrackerDataUpdateCoordinator(hass, mock_api, mock_entry)
        coordinator.data = mock_state_response
        return coordinator

    @pytest.fixture
    def coordinator_without_data(
        self,
        hass: HomeAssistant,
        mock_car_id: int,
        mock_car_name: str,
    ) -> EVTrackerDataUpdateCoordinator:
        """Create a coordinator without data."""
        mock_api = AsyncMock()
        mock_entry = MagicMock()
        mock_entry.data = {
            CONF_API_KEY: "test_key",
            CONF_CAR_ID: mock_car_id,
            CONF_CAR_NAME: mock_car_name,
        }
        mock_entry.options = {}

        coordinator = EVTrackerDataUpdateCoordinator(hass, mock_api, mock_entry)
        coordinator.data = None
        return coordinator

    def test_last_session_with_data(
        self,
        coordinator_with_data: EVTrackerDataUpdateCoordinator,
        mock_state_response: dict,
    ):
        """Test last_session property with data."""
        assert coordinator_with_data.last_session == mock_state_response["lastSession"]

    def test_last_session_without_data(
        self,
        coordinator_without_data: EVTrackerDataUpdateCoordinator,
    ):
        """Test last_session property without data."""
        assert coordinator_without_data.last_session is None

    def test_current_month_with_data(
        self,
        coordinator_with_data: EVTrackerDataUpdateCoordinator,
        mock_state_response: dict,
    ):
        """Test current_month property with data."""
        assert coordinator_with_data.current_month == mock_state_response["currentMonth"]

    def test_current_month_without_data(
        self,
        coordinator_without_data: EVTrackerDataUpdateCoordinator,
    ):
        """Test current_month property without data."""
        assert coordinator_without_data.current_month is None

    def test_current_year_with_data(
        self,
        coordinator_with_data: EVTrackerDataUpdateCoordinator,
        mock_state_response: dict,
    ):
        """Test current_year property with data."""
        assert coordinator_with_data.current_year == mock_state_response["currentYear"]

    def test_current_year_without_data(
        self,
        coordinator_without_data: EVTrackerDataUpdateCoordinator,
    ):
        """Test current_year property without data."""
        assert coordinator_without_data.current_year is None

    def test_cars_with_data(
        self,
        coordinator_with_data: EVTrackerDataUpdateCoordinator,
        mock_state_response: dict,
    ):
        """Test cars property with data."""
        assert coordinator_with_data.cars == mock_state_response["cars"]

    def test_cars_without_data(
        self,
        coordinator_without_data: EVTrackerDataUpdateCoordinator,
    ):
        """Test cars property without data."""
        assert coordinator_without_data.cars == []

    def test_is_connected_with_data(
        self,
        coordinator_with_data: EVTrackerDataUpdateCoordinator,
    ):
        """Test is_connected property with data."""
        assert coordinator_with_data.is_connected is True

    def test_is_connected_without_data(
        self,
        coordinator_without_data: EVTrackerDataUpdateCoordinator,
    ):
        """Test is_connected property without data."""
        assert coordinator_without_data.is_connected is False

    def test_is_connected_false_in_data(
        self,
        coordinator_with_data: EVTrackerDataUpdateCoordinator,
    ):
        """Test is_connected when explicitly false in data."""
        coordinator_with_data.data["connected"] = False
        assert coordinator_with_data.is_connected is False
