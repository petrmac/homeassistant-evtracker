"""Tests for EV Tracker services."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant, State

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
from custom_components.evtracker.services import (
    _get_auto_prices,
    _get_auto_rate_type,
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

    @pytest.mark.asyncio
    async def test_log_session_simple_no_coordinators(
        self,
        hass: HomeAssistant,
    ):
        """Test log_session_simple with no coordinators."""
        hass.data[DOMAIN] = {}
        await async_setup_services(hass)

        # Should not raise, just log error
        await hass.services.async_call(
            DOMAIN,
            SERVICE_LOG_SESSION_SIMPLE,
            {ATTR_ENERGY_KWH: 25.5},
            blocking=True,
        )

    @pytest.mark.asyncio
    async def test_log_session_simple_car_id_not_found(
        self,
        hass: HomeAssistant,
        mock_session_response: dict,
    ):
        """Test log_session_simple with car_id not found."""
        coordinator = MagicMock()
        coordinator.car_id = 123
        coordinator.api = AsyncMock()
        coordinator.api.log_session_simple = AsyncMock(return_value=mock_session_response)

        hass.data[DOMAIN] = {"entry_1": coordinator}
        await async_setup_services(hass)

        # Should not raise, just log error
        await hass.services.async_call(
            DOMAIN,
            SERVICE_LOG_SESSION_SIMPLE,
            {ATTR_ENERGY_KWH: 25.5, ATTR_CAR_ID: 999},
            blocking=True,
        )

        coordinator.api.log_session_simple.assert_not_called()

    @pytest.mark.asyncio
    async def test_log_session_simple_api_error(
        self,
        hass: HomeAssistant,
        mock_car_id: int,
    ):
        """Test log_session_simple handles API errors."""
        coordinator = MagicMock()
        coordinator.car_id = mock_car_id
        coordinator.api = AsyncMock()
        coordinator.api.log_session_simple = AsyncMock(side_effect=Exception("API Error"))
        coordinator.async_request_refresh = AsyncMock()

        hass.data[DOMAIN] = {"entry_1": coordinator}
        await async_setup_services(hass)

        with pytest.raises(Exception) as exc_info:
            await hass.services.async_call(
                DOMAIN,
                SERVICE_LOG_SESSION_SIMPLE,
                {ATTR_ENERGY_KWH: 25.5},
                blocking=True,
            )

        assert "API Error" in str(exc_info.value)


class TestAutoRateType:
    """Test _get_auto_rate_type function."""

    @pytest.fixture
    def mock_coordinator(self, mock_car_id: int) -> MagicMock:
        """Create a mock coordinator."""
        coordinator = MagicMock()
        coordinator.car_id = mock_car_id
        return coordinator

    def test_no_config_entry(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ):
        """Test auto rate when no config entry found."""
        hass.data[DOMAIN] = {}

        result = _get_auto_rate_type(hass, mock_coordinator)

        assert result is None

    def test_tariff_source_none(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ):
        """Test auto rate with tariff source none."""
        entry_id = "test_entry"
        mock_entry = MagicMock()
        mock_entry.options = {CONF_TARIFF_SOURCE: TARIFF_SOURCE_NONE}
        hass.data[DOMAIN] = {entry_id: mock_coordinator}
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        result = _get_auto_rate_type(hass, mock_coordinator)

        assert result is None

    def test_tariff_source_schedule_low(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
        mock_car_id: int,
    ):
        """Test auto rate from schedule - low tariff."""
        entry_id = "test_entry"
        mock_entry = MagicMock()
        mock_entry.options = {CONF_TARIFF_SOURCE: TARIFF_SOURCE_SCHEDULE}
        hass.data[DOMAIN] = {entry_id: mock_coordinator}
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        # Mock the binary sensor state
        entity_id = f"binary_sensor.evtracker_{mock_car_id}_{BINARY_SENSOR_LOW_TARIFF}"
        hass.states.async_set(entity_id, "on")

        result = _get_auto_rate_type(hass, mock_coordinator)

        assert result == RATE_TYPE_LOW

    def test_tariff_source_schedule_high(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
        mock_car_id: int,
    ):
        """Test auto rate from schedule - high tariff."""
        entry_id = "test_entry"
        mock_entry = MagicMock()
        mock_entry.options = {CONF_TARIFF_SOURCE: TARIFF_SOURCE_SCHEDULE}
        hass.data[DOMAIN] = {entry_id: mock_coordinator}
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        # Mock the binary sensor state as off (high tariff)
        entity_id = f"binary_sensor.evtracker_{mock_car_id}_{BINARY_SENSOR_LOW_TARIFF}"
        hass.states.async_set(entity_id, "off")

        result = _get_auto_rate_type(hass, mock_coordinator)

        assert result == RATE_TYPE_HIGH

    def test_tariff_source_schedule_sensor_not_found(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ):
        """Test auto rate from schedule when sensor not found."""
        entry_id = "test_entry"
        mock_entry = MagicMock()
        mock_entry.options = {CONF_TARIFF_SOURCE: TARIFF_SOURCE_SCHEDULE}
        hass.data[DOMAIN] = {entry_id: mock_coordinator}
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        # Don't set any state, sensor doesn't exist

        result = _get_auto_rate_type(hass, mock_coordinator)

        assert result is None

    def test_tariff_source_entity_low(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ):
        """Test auto rate from external entity - low tariff."""
        entry_id = "test_entry"
        mock_entry = MagicMock()
        mock_entry.options = {
            CONF_TARIFF_SOURCE: TARIFF_SOURCE_ENTITY,
            CONF_TARIFF_ENTITY: "binary_sensor.low_tariff",
        }
        hass.data[DOMAIN] = {entry_id: mock_coordinator}
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        # Mock the entity state
        hass.states.async_set("binary_sensor.low_tariff", "on")

        result = _get_auto_rate_type(hass, mock_coordinator)

        assert result == RATE_TYPE_LOW

    def test_tariff_source_entity_high(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ):
        """Test auto rate from external entity - high tariff."""
        entry_id = "test_entry"
        mock_entry = MagicMock()
        mock_entry.options = {
            CONF_TARIFF_SOURCE: TARIFF_SOURCE_ENTITY,
            CONF_TARIFF_ENTITY: "binary_sensor.low_tariff",
        }
        hass.data[DOMAIN] = {entry_id: mock_coordinator}
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        # Mock the entity state as off (high tariff)
        hass.states.async_set("binary_sensor.low_tariff", "off")

        result = _get_auto_rate_type(hass, mock_coordinator)

        assert result == RATE_TYPE_HIGH

    def test_tariff_source_entity_not_found(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ):
        """Test auto rate when external entity not found."""
        entry_id = "test_entry"
        mock_entry = MagicMock()
        mock_entry.options = {
            CONF_TARIFF_SOURCE: TARIFF_SOURCE_ENTITY,
            CONF_TARIFF_ENTITY: "binary_sensor.nonexistent",
        }
        hass.data[DOMAIN] = {entry_id: mock_coordinator}
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        result = _get_auto_rate_type(hass, mock_coordinator)

        assert result is None

    def test_tariff_source_entity_no_entity_configured(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ):
        """Test auto rate when no entity configured."""
        entry_id = "test_entry"
        mock_entry = MagicMock()
        mock_entry.options = {
            CONF_TARIFF_SOURCE: TARIFF_SOURCE_ENTITY,
            # No CONF_TARIFF_ENTITY
        }
        hass.data[DOMAIN] = {entry_id: mock_coordinator}
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        result = _get_auto_rate_type(hass, mock_coordinator)

        assert result is None

    def test_tariff_source_unknown(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ):
        """Test auto rate with unknown tariff source returns None."""
        entry_id = "test_entry"
        mock_entry = MagicMock()
        mock_entry.options = {
            CONF_TARIFF_SOURCE: "unknown_source",
        }
        hass.data[DOMAIN] = {entry_id: mock_coordinator}
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        result = _get_auto_rate_type(hass, mock_coordinator)

        assert result is None

    @pytest.mark.parametrize(
        "state_value,expected",
        [
            ("on", RATE_TYPE_LOW),
            ("true", RATE_TYPE_LOW),
            ("1", RATE_TYPE_LOW),
            ("low", RATE_TYPE_LOW),
            ("yes", RATE_TYPE_LOW),
            ("ON", RATE_TYPE_LOW),  # Case insensitive
            ("off", RATE_TYPE_HIGH),
            ("false", RATE_TYPE_HIGH),
            ("0", RATE_TYPE_HIGH),
            ("high", RATE_TYPE_HIGH),
        ],
    )
    def test_tariff_source_entity_various_states(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
        state_value: str,
        expected: str,
    ):
        """Test auto rate with various entity state values."""
        entry_id = "test_entry"
        mock_entry = MagicMock()
        mock_entry.options = {
            CONF_TARIFF_SOURCE: TARIFF_SOURCE_ENTITY,
            CONF_TARIFF_ENTITY: "binary_sensor.tariff",
        }
        hass.data[DOMAIN] = {entry_id: mock_coordinator}
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        hass.states.async_set("binary_sensor.tariff", state_value)

        result = _get_auto_rate_type(hass, mock_coordinator)

        assert result == expected


class TestAutoPrices:
    """Test _get_auto_prices function."""

    @pytest.fixture
    def mock_coordinator(self, mock_car_id: int) -> MagicMock:
        """Create a mock coordinator."""
        coordinator = MagicMock()
        coordinator.car_id = mock_car_id
        return coordinator

    def test_no_config_entry(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ):
        """Test auto prices when no config entry found."""
        hass.data[DOMAIN] = {}

        price, vat = _get_auto_prices(hass, mock_coordinator, RATE_TYPE_LOW)

        assert price is None
        assert vat is None

    def test_use_prices_disabled(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ):
        """Test auto prices when price configuration disabled."""
        entry_id = "test_entry"
        mock_entry = MagicMock()
        mock_entry.options = {CONF_USE_PRICES: False}
        hass.data[DOMAIN] = {entry_id: mock_coordinator}
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        price, vat = _get_auto_prices(hass, mock_coordinator, RATE_TYPE_LOW)

        assert price is None
        assert vat is None

    def test_low_rate_price(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ):
        """Test auto prices for low rate."""
        entry_id = "test_entry"
        mock_entry = MagicMock()
        mock_entry.options = {
            CONF_USE_PRICES: True,
            CONF_PRICE_LOW: 3.50,
            CONF_PRICE_HIGH: 5.00,
            CONF_VAT_PERCENTAGE: 21.0,
        }
        hass.data[DOMAIN] = {entry_id: mock_coordinator}
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        price, vat = _get_auto_prices(hass, mock_coordinator, RATE_TYPE_LOW)

        assert price == 3.50
        assert vat == 21.0

    def test_high_rate_price(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ):
        """Test auto prices for high rate."""
        entry_id = "test_entry"
        mock_entry = MagicMock()
        mock_entry.options = {
            CONF_USE_PRICES: True,
            CONF_PRICE_LOW: 3.50,
            CONF_PRICE_HIGH: 5.00,
            CONF_VAT_PERCENTAGE: 21.0,
        }
        hass.data[DOMAIN] = {entry_id: mock_coordinator}
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        price, vat = _get_auto_prices(hass, mock_coordinator, RATE_TYPE_HIGH)

        assert price == 5.00
        assert vat == 21.0

    def test_no_rate_type_uses_high(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ):
        """Test auto prices when no rate type uses high price."""
        entry_id = "test_entry"
        mock_entry = MagicMock()
        mock_entry.options = {
            CONF_USE_PRICES: True,
            CONF_PRICE_LOW: 3.50,
            CONF_PRICE_HIGH: 5.00,
            CONF_VAT_PERCENTAGE: 21.0,
        }
        hass.data[DOMAIN] = {entry_id: mock_coordinator}
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        price, vat = _get_auto_prices(hass, mock_coordinator, None)

        assert price == 5.00
        assert vat == 21.0

    def test_price_zero_returns_none(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ):
        """Test that zero price returns None."""
        entry_id = "test_entry"
        mock_entry = MagicMock()
        mock_entry.options = {
            CONF_USE_PRICES: True,
            CONF_PRICE_LOW: 0,
            CONF_PRICE_HIGH: 0,
            CONF_VAT_PERCENTAGE: 21.0,
        }
        hass.data[DOMAIN] = {entry_id: mock_coordinator}
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        price, vat = _get_auto_prices(hass, mock_coordinator, RATE_TYPE_LOW)

        assert price is None
        assert vat is None

    def test_price_none_returns_none(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ):
        """Test that unconfigured price returns None."""
        entry_id = "test_entry"
        mock_entry = MagicMock()
        mock_entry.options = {
            CONF_USE_PRICES: True,
            # No prices configured
        }
        hass.data[DOMAIN] = {entry_id: mock_coordinator}
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        price, vat = _get_auto_prices(hass, mock_coordinator, RATE_TYPE_LOW)

        assert price is None
        assert vat is None


class TestAutoDetectionInServices:
    """Test auto-detection of rate_type and prices in service calls."""

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
        coordinator.api.log_session_simple = AsyncMock(return_value=mock_session_response)
        coordinator.async_request_refresh = AsyncMock()
        return coordinator

    @pytest.mark.asyncio
    async def test_log_session_auto_rate_type(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_service: MagicMock,
        mock_car_id: int,
    ):
        """Test log_session with auto-detected rate_type."""
        entry_id = "entry_1"
        mock_entry = MagicMock()
        mock_entry.options = {CONF_TARIFF_SOURCE: TARIFF_SOURCE_SCHEDULE}
        hass.data[DOMAIN] = {entry_id: mock_coordinator_for_service}
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        # Set up low tariff binary sensor
        entity_id = f"binary_sensor.evtracker_{mock_car_id}_{BINARY_SENSOR_LOW_TARIFF}"
        hass.states.async_set(entity_id, "on")

        await async_setup_services(hass)

        await hass.services.async_call(
            DOMAIN,
            SERVICE_LOG_SESSION,
            {ATTR_ENERGY_KWH: 25.5},
            blocking=True,
        )

        call_kwargs = mock_coordinator_for_service.api.log_session.call_args.kwargs
        assert call_kwargs["rate_type"] == RATE_TYPE_LOW

    @pytest.mark.asyncio
    async def test_log_session_explicit_rate_overrides_auto(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_service: MagicMock,
        mock_car_id: int,
    ):
        """Test that explicit rate_type overrides auto-detected."""
        entry_id = "entry_1"
        mock_entry = MagicMock()
        mock_entry.options = {CONF_TARIFF_SOURCE: TARIFF_SOURCE_SCHEDULE}
        hass.data[DOMAIN] = {entry_id: mock_coordinator_for_service}
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        # Set up low tariff binary sensor
        entity_id = f"binary_sensor.evtracker_{mock_car_id}_{BINARY_SENSOR_LOW_TARIFF}"
        hass.states.async_set(entity_id, "on")  # Auto would detect LOW

        await async_setup_services(hass)

        await hass.services.async_call(
            DOMAIN,
            SERVICE_LOG_SESSION,
            {ATTR_ENERGY_KWH: 25.5, ATTR_RATE_TYPE: "HIGH"},  # Explicit HIGH
            blocking=True,
        )

        call_kwargs = mock_coordinator_for_service.api.log_session.call_args.kwargs
        assert call_kwargs["rate_type"] == "HIGH"

    @pytest.mark.asyncio
    async def test_log_session_auto_prices(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_service: MagicMock,
        mock_car_id: int,
    ):
        """Test log_session with auto-detected prices."""
        entry_id = "entry_1"
        mock_entry = MagicMock()
        mock_entry.options = {
            CONF_TARIFF_SOURCE: TARIFF_SOURCE_SCHEDULE,
            CONF_USE_PRICES: True,
            CONF_PRICE_LOW: 3.50,
            CONF_PRICE_HIGH: 5.00,
            CONF_VAT_PERCENTAGE: 21.0,
        }
        hass.data[DOMAIN] = {entry_id: mock_coordinator_for_service}
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        # Set up low tariff binary sensor
        entity_id = f"binary_sensor.evtracker_{mock_car_id}_{BINARY_SENSOR_LOW_TARIFF}"
        hass.states.async_set(entity_id, "on")

        await async_setup_services(hass)

        await hass.services.async_call(
            DOMAIN,
            SERVICE_LOG_SESSION,
            {ATTR_ENERGY_KWH: 25.5},
            blocking=True,
        )

        call_kwargs = mock_coordinator_for_service.api.log_session.call_args.kwargs
        assert call_kwargs["rate_type"] == RATE_TYPE_LOW
        assert call_kwargs["price_per_kwh"] == 3.50
        assert call_kwargs["vat_percentage"] == 21.0

    @pytest.mark.asyncio
    async def test_log_session_explicit_price_overrides_auto(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_service: MagicMock,
        mock_car_id: int,
    ):
        """Test that explicit prices override auto-detected."""
        entry_id = "entry_1"
        mock_entry = MagicMock()
        mock_entry.options = {
            CONF_TARIFF_SOURCE: TARIFF_SOURCE_NONE,
            CONF_USE_PRICES: True,
            CONF_PRICE_LOW: 3.50,
            CONF_PRICE_HIGH: 5.00,
            CONF_VAT_PERCENTAGE: 21.0,
        }
        hass.data[DOMAIN] = {entry_id: mock_coordinator_for_service}
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        await async_setup_services(hass)

        await hass.services.async_call(
            DOMAIN,
            SERVICE_LOG_SESSION,
            {
                ATTR_ENERGY_KWH: 25.5,
                ATTR_PRICE_PER_KWH: 10.00,  # Explicit price
                ATTR_VAT_PERCENTAGE: 15.0,  # Explicit VAT
            },
            blocking=True,
        )

        call_kwargs = mock_coordinator_for_service.api.log_session.call_args.kwargs
        assert call_kwargs["price_per_kwh"] == 10.00
        assert call_kwargs["vat_percentage"] == 15.0

    @pytest.mark.asyncio
    async def test_log_session_simple_auto_rate_type(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_service: MagicMock,
        mock_car_id: int,
    ):
        """Test log_session_simple with auto-detected rate_type."""
        entry_id = "entry_1"
        mock_entry = MagicMock()
        mock_entry.options = {
            CONF_TARIFF_SOURCE: TARIFF_SOURCE_ENTITY,
            CONF_TARIFF_ENTITY: "binary_sensor.tariff",
        }
        hass.data[DOMAIN] = {entry_id: mock_coordinator_for_service}
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        # Set up tariff entity
        hass.states.async_set("binary_sensor.tariff", "on")

        await async_setup_services(hass)

        await hass.services.async_call(
            DOMAIN,
            SERVICE_LOG_SESSION_SIMPLE,
            {ATTR_ENERGY_KWH: 25.5},
            blocking=True,
        )

        call_kwargs = mock_coordinator_for_service.api.log_session_simple.call_args.kwargs
        assert call_kwargs["rate_type"] == RATE_TYPE_LOW

    @pytest.mark.asyncio
    async def test_log_session_simple_explicit_rate_overrides_auto(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_service: MagicMock,
        mock_car_id: int,
    ):
        """Test that explicit rate_type overrides auto-detected in log_session_simple."""
        entry_id = "entry_1"
        mock_entry = MagicMock()
        mock_entry.options = {
            CONF_TARIFF_SOURCE: TARIFF_SOURCE_ENTITY,
            CONF_TARIFF_ENTITY: "binary_sensor.tariff",
        }
        hass.data[DOMAIN] = {entry_id: mock_coordinator_for_service}
        hass.config_entries.async_get_entry = MagicMock(return_value=mock_entry)

        # Set up tariff entity as low
        hass.states.async_set("binary_sensor.tariff", "on")

        await async_setup_services(hass)

        await hass.services.async_call(
            DOMAIN,
            SERVICE_LOG_SESSION_SIMPLE,
            {ATTR_ENERGY_KWH: 25.5, ATTR_RATE_TYPE: "HIGH"},  # Explicit HIGH
            blocking=True,
        )

        call_kwargs = mock_coordinator_for_service.api.log_session_simple.call_args.kwargs
        assert call_kwargs["rate_type"] == "HIGH"

    @pytest.mark.asyncio
    async def test_log_session_simple_finds_coordinator_by_car_id(
        self,
        hass: HomeAssistant,
        mock_session_response: dict,
    ):
        """Test that log_session_simple finds correct coordinator by car_id."""
        coordinator1 = MagicMock()
        coordinator1.car_id = 123
        coordinator1.api = AsyncMock()
        coordinator1.api.log_session_simple = AsyncMock(return_value=mock_session_response)
        coordinator1.async_request_refresh = AsyncMock()

        coordinator2 = MagicMock()
        coordinator2.car_id = 456
        coordinator2.api = AsyncMock()
        coordinator2.api.log_session_simple = AsyncMock(return_value=mock_session_response)
        coordinator2.async_request_refresh = AsyncMock()

        hass.data[DOMAIN] = {"entry_1": coordinator1, "entry_2": coordinator2}
        await async_setup_services(hass)

        await hass.services.async_call(
            DOMAIN,
            SERVICE_LOG_SESSION_SIMPLE,
            {ATTR_ENERGY_KWH: 25.5, ATTR_CAR_ID: 456},
            blocking=True,
        )

        coordinator1.api.log_session_simple.assert_not_called()
        coordinator2.api.log_session_simple.assert_called_once()
