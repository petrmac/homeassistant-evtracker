"""Fixtures for EV Tracker tests."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import CONF_API_KEY

from custom_components.evtracker.const import (
    CONF_CAR_ID,
    CONF_CAR_NAME,
)

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for testing."""
    yield


@pytest.fixture
def mock_api_key() -> str:
    """Return a mock API key."""
    return "test_api_key_12345"


@pytest.fixture
def mock_car_id() -> int:
    """Return a mock car ID."""
    return 123


@pytest.fixture
def mock_car_name() -> str:
    """Return a mock car name."""
    return "Test Tesla Model 3"


@pytest.fixture
def mock_config_entry_data(mock_api_key: str, mock_car_id: int, mock_car_name: str) -> dict:
    """Return mock config entry data."""
    return {
        CONF_API_KEY: mock_api_key,
        CONF_CAR_ID: mock_car_id,
        CONF_CAR_NAME: mock_car_name,
    }


@pytest.fixture
def mock_cars_response() -> list[dict]:
    """Return mock cars API response."""
    return [
        {"id": 123, "name": "Test Tesla Model 3"},
        {"id": 456, "name": "Test VW ID.4"},
    ]


@pytest.fixture
def mock_state_response() -> dict:
    """Return mock HA state API response."""
    return {
        "currentMonth": {
            "energyConsumedKwh": 150.5,
            "totalCostWithVat": 680.25,
            "sessionCount": 12,
            "averageCostPerKwh": 4.52,
            "currency": "CZK",
        },
        "currentYear": {
            "energyConsumedKwh": 1250.75,
            "totalCostWithVat": 5625.50,
        },
        "lastSession": {
            "id": 999,
            "energyConsumedKwh": 35.2,
            "totalCostWithVat": 158.40,
            "carName": "Test Tesla Model 3",
            "startTime": "2024-01-15T08:00:00Z",
            "endTime": "2024-01-15T12:30:00Z",
            "provider": "HOME",
            "location": "Home",
        },
        "cars": [
            {"id": 123, "name": "Test Tesla Model 3"},
        ],
        "connected": True,
    }


@pytest.fixture
def mock_session_response() -> dict:
    """Return mock session logging API response."""
    return {
        "id": 1000,
        "energyConsumedKwh": 25.5,
        "totalCostWithVat": 114.75,
        "startTime": "2024-01-20T10:00:00Z",
        "endTime": "2024-01-20T14:00:00Z",
    }


@pytest.fixture
def mock_api(
    mock_cars_response: list[dict],
    mock_state_response: dict,
    mock_session_response: dict,
) -> Generator[AsyncMock, None, None]:
    """Create a mock API client."""
    with patch("custom_components.evtracker.api.EVTrackerAPI", autospec=True) as mock_api_class:
        mock_instance = mock_api_class.return_value
        mock_instance.get_cars_raw = AsyncMock(return_value=mock_cars_response)
        mock_instance.get_state_raw = AsyncMock(return_value=mock_state_response)
        mock_instance.get_default_car = AsyncMock(return_value=mock_cars_response[0])
        mock_instance.log_session = AsyncMock(return_value=mock_session_response)
        mock_instance.log_session_simple = AsyncMock(return_value=mock_session_response)
        mock_instance.validate_api_key = AsyncMock(return_value=True)
        mock_instance.close = AsyncMock()
        yield mock_instance


@pytest.fixture
def mock_coordinator(mock_state_response: dict, mock_car_id: int, mock_car_name: str) -> MagicMock:
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.data = mock_state_response
    coordinator.car_id = mock_car_id
    coordinator.car_name = mock_car_name
    coordinator.last_update_success = True
    coordinator.last_session = mock_state_response.get("lastSession")
    coordinator.current_month = mock_state_response.get("currentMonth")
    coordinator.current_year = mock_state_response.get("currentYear")
    coordinator.cars = mock_state_response.get("cars", [])
    coordinator.is_connected = True
    coordinator.async_request_refresh = AsyncMock()
    return coordinator
