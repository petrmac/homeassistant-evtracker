"""Tests for EV Tracker API client."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.evtracker.api import (
    EVTrackerAPI,
    EVTrackerApiError,
    EVTrackerAuthenticationError,
    EVTrackerConnectionError,
    EVTrackerRateLimitError,
)
from custom_components.evtracker.const import DEFAULT_API_BASE_URL


class TestEVTrackerAPI:
    """Test EVTrackerAPI class."""

    def test_init_default_values(self):
        """Test API client initialization with defaults."""
        api = EVTrackerAPI("test_key")

        assert api.api_key == "test_key"
        assert api.base_url == DEFAULT_API_BASE_URL
        assert api._session is None
        assert api._owned_session is False

    def test_init_custom_base_url(self):
        """Test API client with custom base URL."""
        api = EVTrackerAPI("test_key", base_url="https://custom.api.com/")

        assert api.base_url == "https://custom.api.com"  # trailing slash stripped

    def test_init_with_session(self):
        """Test API client with provided session."""
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        api = EVTrackerAPI("test_key", session=mock_session)

        assert api._session == mock_session
        assert api._owned_session is False

    def test_get_headers(self):
        """Test header generation."""
        api = EVTrackerAPI("test_api_key")
        headers = api._get_headers()

        assert headers["x-api-key"] == "test_api_key"
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"
        assert "HomeAssistant-EVTracker" in headers["User-Agent"]

    @pytest.mark.asyncio
    async def test_get_session_creates_new(self):
        """Test session creation when none exists."""
        api = EVTrackerAPI("test_key")

        session = await api._get_session()

        assert session is not None
        assert api._owned_session is True

        await api.close()

    @pytest.mark.asyncio
    async def test_close_owned_session(self):
        """Test closing owned session."""
        api = EVTrackerAPI("test_key")
        await api._get_session()  # Creates owned session

        await api.close()

        assert api._session.closed

    @pytest.mark.asyncio
    async def test_close_not_owned_session(self):
        """Test that external session is not closed."""
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_session.closed = False
        api = EVTrackerAPI("test_key", session=mock_session)

        await api.close()

        mock_session.close.assert_not_called()


def create_mock_response(
    status: int, json_data: dict | None = None, text: str = "", headers: dict | None = None
):
    """Create a mock response with proper async context manager support."""
    mock_response = MagicMock()
    mock_response.status = status
    mock_response.headers = headers or {}
    mock_response.json = AsyncMock(return_value=json_data)
    mock_response.text = AsyncMock(return_value=text)
    return mock_response


class TestAPIRequests:
    """Test API request methods."""

    @pytest.mark.asyncio
    async def test_get_cars_success(self):
        """Test successful get_cars call."""
        mock_response = create_mock_response(200, {"data": [{"id": 1, "name": "Car 1"}]})

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.closed = False
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_session.request = MagicMock(return_value=mock_cm)
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            api = EVTrackerAPI("test_key")
            api._session = mock_session
            api._owned_session = False

            result = await api.get_cars()

            assert result == [{"id": 1, "name": "Car 1"}]

    @pytest.mark.asyncio
    async def test_authentication_error_401(self):
        """Test 401 raises authentication error."""
        mock_response = create_mock_response(401)

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.closed = False
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_session.request = MagicMock(return_value=mock_cm)
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            api = EVTrackerAPI("test_key")
            api._session = mock_session
            api._owned_session = False

            with pytest.raises(EVTrackerAuthenticationError):
                await api.get_cars()

    @pytest.mark.asyncio
    async def test_authentication_error_403(self):
        """Test 403 raises authentication error."""
        mock_response = create_mock_response(403)

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.closed = False
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_session.request = MagicMock(return_value=mock_cm)
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            api = EVTrackerAPI("test_key")
            api._session = mock_session
            api._owned_session = False

            with pytest.raises(EVTrackerAuthenticationError):
                await api.get_state()

    @pytest.mark.asyncio
    async def test_rate_limit_error_429(self):
        """Test 429 raises rate limit error."""
        mock_response = create_mock_response(429, headers={"Retry-After": "120"})

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.closed = False
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_session.request = MagicMock(return_value=mock_cm)
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            api = EVTrackerAPI("test_key")
            api._session = mock_session
            api._owned_session = False

            with pytest.raises(EVTrackerRateLimitError) as exc_info:
                await api.get_cars()

            assert "120" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_server_error_500(self):
        """Test 500 raises API error."""
        mock_response = create_mock_response(500, text="Internal Server Error")

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.closed = False
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_session.request = MagicMock(return_value=mock_cm)
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            api = EVTrackerAPI("test_key")
            api._session = mock_session
            api._owned_session = False

            with pytest.raises(EVTrackerApiError) as exc_info:
                await api.get_cars()

            assert "500" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_connection_error(self):
        """Test connection error handling."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.closed = False
            mock_session.request = MagicMock(side_effect=aiohttp.ClientError("Connection failed"))
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            api = EVTrackerAPI("test_key")
            api._session = mock_session
            api._owned_session = False

            with pytest.raises(EVTrackerConnectionError):
                await api.get_cars()


class TestLogSession:
    """Test session logging methods."""

    @pytest.mark.asyncio
    async def test_log_session_minimal(self):
        """Test log_session with minimal parameters."""
        mock_response = create_mock_response(200, {"data": {"id": 100}})

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.closed = False
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_session.request = MagicMock(return_value=mock_cm)
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            api = EVTrackerAPI("test_key")
            api._session = mock_session
            api._owned_session = False

            result = await api.log_session(energy_kwh=25.5)

            assert result == {"id": 100}

    @pytest.mark.asyncio
    async def test_log_session_full_parameters(self):
        """Test log_session with all parameters."""
        mock_response = create_mock_response(200, {"data": {"id": 101}})

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.closed = False
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_session.request = MagicMock(return_value=mock_cm)
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            api = EVTrackerAPI("test_key")
            api._session = mock_session
            api._owned_session = False

            start = datetime(2024, 1, 15, 8, 0, 0)
            end = datetime(2024, 1, 15, 12, 0, 0)

            result = await api.log_session(
                energy_kwh=35.5,
                start_time=start,
                end_time=end,
                car_id=123,
                location="Home",
                external_id="HA-12345",
                provider="HOME",
                energy_source="GRID",
                price_per_kwh=4.50,
                vat_percentage=21.0,
                notes="Test session",
            )

            assert result == {"id": 101}

    @pytest.mark.asyncio
    async def test_log_session_simple(self):
        """Test log_session_simple."""
        mock_response = create_mock_response(200, {"data": {"id": 102}})

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.closed = False
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_session.request = MagicMock(return_value=mock_cm)
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            api = EVTrackerAPI("test_key")
            api._session = mock_session
            api._owned_session = False

            result = await api.log_session_simple(
                energy_kwh=20.0,
                location="Work",
            )

            assert result == {"id": 102}


class TestValidateApiKey:
    """Test API key validation."""

    @pytest.mark.asyncio
    async def test_validate_api_key_success(self):
        """Test successful API key validation."""
        mock_response = create_mock_response(200, {"data": []})

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.closed = False
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_session.request = MagicMock(return_value=mock_cm)
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            api = EVTrackerAPI("valid_key")
            api._session = mock_session
            api._owned_session = False

            result = await api.validate_api_key()

            assert result is True

    @pytest.mark.asyncio
    async def test_validate_api_key_invalid(self):
        """Test invalid API key validation."""
        mock_response = create_mock_response(401)

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.closed = False
            mock_cm = MagicMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_session.request = MagicMock(return_value=mock_cm)
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            api = EVTrackerAPI("invalid_key")
            api._session = mock_session
            api._owned_session = False

            result = await api.validate_api_key()

            assert result is False
