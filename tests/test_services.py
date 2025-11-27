"""Tests for EV Tracker services."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant

from custom_components.evtracker.const import (
    ATTR_CAR_ID,
    ATTR_END_TIME,
    ATTR_ENERGY_KWH,
    ATTR_ENERGY_SOURCE,
    ATTR_EXTERNAL_ID,
    ATTR_LOCATION,
    ATTR_NOTES,
    ATTR_PRICE_PER_KWH,
    ATTR_PROVIDER,
    ATTR_START_TIME,
    ATTR_VAT_PERCENTAGE,
    DOMAIN,
    SERVICE_LOG_SESSION,
    SERVICE_LOG_SESSION_SIMPLE,
)
from custom_components.evtracker.services import (
    async_setup_services,
    async_unload_services,
)


class TestServiceSetup:
    """Test service setup and unload."""

    @pytest.mark.asyncio
    async def test_setup_services_registers_services(
        self,
        hass: HomeAssistant,
    ):
        """Test that services are registered."""
        hass.data[DOMAIN] = {"entry_1": MagicMock()}

        await async_setup_services(hass)

        assert hass.services.has_service(DOMAIN, SERVICE_LOG_SESSION)
        assert hass.services.has_service(DOMAIN, SERVICE_LOG_SESSION_SIMPLE)

    @pytest.mark.asyncio
    async def test_unload_services_removes_services(
        self,
        hass: HomeAssistant,
    ):
        """Test that services are removed when no entries."""
        hass.data[DOMAIN] = {"entry_1": MagicMock()}
        await async_setup_services(hass)

        # Clear entries to trigger removal
        hass.data[DOMAIN] = {}
        await async_unload_services(hass)

        assert not hass.services.has_service(DOMAIN, SERVICE_LOG_SESSION)
        assert not hass.services.has_service(DOMAIN, SERVICE_LOG_SESSION_SIMPLE)

    @pytest.mark.asyncio
    async def test_unload_services_keeps_services_with_entries(
        self,
        hass: HomeAssistant,
    ):
        """Test that services are kept when entries remain."""
        hass.data[DOMAIN] = {"entry_1": MagicMock()}
        await async_setup_services(hass)

        # Keep one entry
        await async_unload_services(hass)

        # Services should still exist
        assert hass.services.has_service(DOMAIN, SERVICE_LOG_SESSION)


class TestLogSessionService:
    """Test log_session service."""

    @pytest.fixture
    def mock_coordinator_for_service(
        self,
        mock_session_response: dict,
        mock_car_id: int,
    ) -> MagicMock:
        """Create a mock coordinator for service tests."""
        coordinator = MagicMock()
        coordinator.car_id = mock_car_id
        coordinator.api = AsyncMock()
        coordinator.api.log_session = AsyncMock(return_value=mock_session_response)
        coordinator.async_request_refresh = AsyncMock()
        return coordinator

    @pytest.mark.asyncio
    async def test_log_session_minimal(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_service: MagicMock,
    ):
        """Test log_session with minimal parameters."""
        hass.data[DOMAIN] = {"entry_1": mock_coordinator_for_service}
        await async_setup_services(hass)

        await hass.services.async_call(
            DOMAIN,
            SERVICE_LOG_SESSION,
            {ATTR_ENERGY_KWH: 25.5},
            blocking=True,
        )

        mock_coordinator_for_service.api.log_session.assert_called_once()
        call_kwargs = mock_coordinator_for_service.api.log_session.call_args.kwargs
        assert call_kwargs["energy_kwh"] == 25.5
        mock_coordinator_for_service.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_session_full_parameters(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_service: MagicMock,
    ):
        """Test log_session with all parameters."""
        hass.data[DOMAIN] = {"entry_1": mock_coordinator_for_service}
        await async_setup_services(hass)

        start_time = datetime(2024, 1, 15, 8, 0, 0)
        end_time = datetime(2024, 1, 15, 12, 0, 0)

        await hass.services.async_call(
            DOMAIN,
            SERVICE_LOG_SESSION,
            {
                ATTR_ENERGY_KWH: 35.5,
                ATTR_START_TIME: start_time,
                ATTR_END_TIME: end_time,
                ATTR_CAR_ID: 123,
                ATTR_LOCATION: "Home",
                ATTR_EXTERNAL_ID: "HA-12345",
                ATTR_PROVIDER: "HOME",
                ATTR_ENERGY_SOURCE: "GRID",
                ATTR_PRICE_PER_KWH: 4.50,
                ATTR_VAT_PERCENTAGE: 21.0,
                ATTR_NOTES: "Test session",
            },
            blocking=True,
        )

        call_kwargs = mock_coordinator_for_service.api.log_session.call_args.kwargs
        assert call_kwargs["energy_kwh"] == 35.5
        assert call_kwargs["start_time"] == start_time
        assert call_kwargs["end_time"] == end_time
        assert call_kwargs["car_id"] == 123
        assert call_kwargs["location"] == "Home"
        assert call_kwargs["external_id"] == "HA-12345"
        assert call_kwargs["provider"] == "HOME"
        assert call_kwargs["energy_source"] == "GRID"
        assert call_kwargs["price_per_kwh"] == 4.50
        assert call_kwargs["vat_percentage"] == 21.0
        assert call_kwargs["notes"] == "Test session"

    @pytest.mark.asyncio
    async def test_log_session_finds_coordinator_by_car_id(
        self,
        hass: HomeAssistant,
        mock_session_response: dict,
    ):
        """Test that service finds correct coordinator by car_id."""
        coordinator1 = MagicMock()
        coordinator1.car_id = 123
        coordinator1.api = AsyncMock()
        coordinator1.api.log_session = AsyncMock(return_value=mock_session_response)
        coordinator1.async_request_refresh = AsyncMock()

        coordinator2 = MagicMock()
        coordinator2.car_id = 456
        coordinator2.api = AsyncMock()
        coordinator2.api.log_session = AsyncMock(return_value=mock_session_response)
        coordinator2.async_request_refresh = AsyncMock()

        hass.data[DOMAIN] = {"entry_1": coordinator1, "entry_2": coordinator2}
        await async_setup_services(hass)

        await hass.services.async_call(
            DOMAIN,
            SERVICE_LOG_SESSION,
            {ATTR_ENERGY_KWH: 25.5, ATTR_CAR_ID: 456},
            blocking=True,
        )

        coordinator1.api.log_session.assert_not_called()
        coordinator2.api.log_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_session_uses_first_coordinator_without_car_id(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_service: MagicMock,
    ):
        """Test that service uses first coordinator when no car_id specified."""
        hass.data[DOMAIN] = {"entry_1": mock_coordinator_for_service}
        await async_setup_services(hass)

        await hass.services.async_call(
            DOMAIN,
            SERVICE_LOG_SESSION,
            {ATTR_ENERGY_KWH: 25.5},
            blocking=True,
        )

        # Should use the first coordinator's car_id
        call_kwargs = mock_coordinator_for_service.api.log_session.call_args.kwargs
        assert call_kwargs["car_id"] == mock_coordinator_for_service.car_id


class TestLogSessionSimpleService:
    """Test log_session_simple service."""

    @pytest.fixture
    def mock_coordinator_for_service(
        self,
        mock_session_response: dict,
        mock_car_id: int,
    ) -> MagicMock:
        """Create a mock coordinator for service tests."""
        coordinator = MagicMock()
        coordinator.car_id = mock_car_id
        coordinator.api = AsyncMock()
        coordinator.api.log_session_simple = AsyncMock(return_value=mock_session_response)
        coordinator.async_request_refresh = AsyncMock()
        return coordinator

    @pytest.mark.asyncio
    async def test_log_session_simple_minimal(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_service: MagicMock,
    ):
        """Test log_session_simple with minimal parameters."""
        hass.data[DOMAIN] = {"entry_1": mock_coordinator_for_service}
        await async_setup_services(hass)

        await hass.services.async_call(
            DOMAIN,
            SERVICE_LOG_SESSION_SIMPLE,
            {ATTR_ENERGY_KWH: 20.0},
            blocking=True,
        )

        mock_coordinator_for_service.api.log_session_simple.assert_called_once()
        call_kwargs = mock_coordinator_for_service.api.log_session_simple.call_args.kwargs
        assert call_kwargs["energy_kwh"] == 20.0
        mock_coordinator_for_service.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_session_simple_with_all_params(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_service: MagicMock,
    ):
        """Test log_session_simple with all parameters."""
        hass.data[DOMAIN] = {"entry_1": mock_coordinator_for_service}
        await async_setup_services(hass)

        start_time = datetime(2024, 1, 20, 10, 0, 0)
        end_time = datetime(2024, 1, 20, 14, 0, 0)

        await hass.services.async_call(
            DOMAIN,
            SERVICE_LOG_SESSION_SIMPLE,
            {
                ATTR_ENERGY_KWH: 30.0,
                ATTR_START_TIME: start_time,
                ATTR_END_TIME: end_time,
                ATTR_LOCATION: "Work",
                ATTR_EXTERNAL_ID: "HA-67890",
            },
            blocking=True,
        )

        call_kwargs = mock_coordinator_for_service.api.log_session_simple.call_args.kwargs
        assert call_kwargs["energy_kwh"] == 30.0
        assert call_kwargs["start_time"] == start_time
        assert call_kwargs["end_time"] == end_time
        assert call_kwargs["location"] == "Work"
        assert call_kwargs["external_id"] == "HA-67890"


class TestServiceErrors:
    """Test service error handling."""

    @pytest.mark.asyncio
    async def test_log_session_no_coordinators(
        self,
        hass: HomeAssistant,
    ):
        """Test log_session with no coordinators."""
        hass.data[DOMAIN] = {}
        await async_setup_services(hass)

        # Should not raise, just log error
        await hass.services.async_call(
            DOMAIN,
            SERVICE_LOG_SESSION,
            {ATTR_ENERGY_KWH: 25.5},
            blocking=True,
        )

    @pytest.mark.asyncio
    async def test_log_session_car_id_not_found(
        self,
        hass: HomeAssistant,
        mock_session_response: dict,
    ):
        """Test log_session with car_id not found."""
        coordinator = MagicMock()
        coordinator.car_id = 123
        coordinator.api = AsyncMock()
        coordinator.api.log_session = AsyncMock(return_value=mock_session_response)

        hass.data[DOMAIN] = {"entry_1": coordinator}
        await async_setup_services(hass)

        # Should not raise, just log error
        await hass.services.async_call(
            DOMAIN,
            SERVICE_LOG_SESSION,
            {ATTR_ENERGY_KWH: 25.5, ATTR_CAR_ID: 999},
            blocking=True,
        )

        coordinator.api.log_session.assert_not_called()

    @pytest.mark.asyncio
    async def test_log_session_api_error(
        self,
        hass: HomeAssistant,
        mock_car_id: int,
    ):
        """Test log_session handles API errors."""
        coordinator = MagicMock()
        coordinator.car_id = mock_car_id
        coordinator.api = AsyncMock()
        coordinator.api.log_session = AsyncMock(side_effect=Exception("API Error"))
        coordinator.async_request_refresh = AsyncMock()

        hass.data[DOMAIN] = {"entry_1": coordinator}
        await async_setup_services(hass)

        with pytest.raises(Exception) as exc_info:
            await hass.services.async_call(
                DOMAIN,
                SERVICE_LOG_SESSION,
                {ATTR_ENERGY_KWH: 25.5},
                blocking=True,
            )

        assert "API Error" in str(exc_info.value)
