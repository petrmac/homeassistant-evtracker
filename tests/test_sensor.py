"""Tests for EV Tracker sensors."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType

from custom_components.evtracker.const import (
    CONF_API_KEY,
    CONF_CAR_ID,
    CONF_CAR_NAME,
    CURRENCY_CZK,
    DOMAIN,
    SENSOR_AVG_COST_PER_KWH,
    SENSOR_LAST_SESSION_COST,
    SENSOR_LAST_SESSION_ENERGY,
    SENSOR_MONTHLY_COST,
    SENSOR_MONTHLY_ENERGY,
    SENSOR_MONTHLY_SESSIONS,
    SENSOR_YEARLY_COST,
    SENSOR_YEARLY_ENERGY,
    UNIT_CZK_PER_KWH,
    VERSION,
)
from custom_components.evtracker.sensor import (
    SENSOR_DESCRIPTIONS,
    EVTrackerSensor,
    EVTrackerSensorEntityDescription,
    async_setup_entry,
)


class TestSensorDescriptions:
    """Test sensor descriptions."""

    def test_sensor_count(self):
        """Test that all sensors are defined."""
        assert len(SENSOR_DESCRIPTIONS) == 8

    def test_monthly_energy_description(self):
        """Test monthly energy sensor description."""
        desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == SENSOR_MONTHLY_ENERGY)

        assert desc.native_unit_of_measurement == UnitOfEnergy.KILO_WATT_HOUR
        assert desc.device_class == SensorDeviceClass.ENERGY
        assert desc.state_class == SensorStateClass.TOTAL

    def test_monthly_cost_description(self):
        """Test monthly cost sensor description."""
        desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == SENSOR_MONTHLY_COST)

        assert desc.native_unit_of_measurement == CURRENCY_CZK
        assert desc.device_class == SensorDeviceClass.MONETARY
        assert desc.state_class == SensorStateClass.TOTAL

    def test_monthly_sessions_description(self):
        """Test monthly sessions sensor description."""
        desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == SENSOR_MONTHLY_SESSIONS)

        assert desc.state_class == SensorStateClass.TOTAL
        assert desc.icon == "mdi:counter"

    def test_yearly_energy_description(self):
        """Test yearly energy sensor description."""
        desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == SENSOR_YEARLY_ENERGY)

        assert desc.native_unit_of_measurement == UnitOfEnergy.KILO_WATT_HOUR
        assert desc.device_class == SensorDeviceClass.ENERGY
        assert desc.state_class == SensorStateClass.TOTAL

    def test_yearly_cost_description(self):
        """Test yearly cost sensor description."""
        desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == SENSOR_YEARLY_COST)

        assert desc.native_unit_of_measurement == CURRENCY_CZK
        assert desc.device_class == SensorDeviceClass.MONETARY
        assert desc.state_class == SensorStateClass.TOTAL

    def test_last_session_energy_description(self):
        """Test last session energy sensor description."""
        desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == SENSOR_LAST_SESSION_ENERGY)

        assert desc.native_unit_of_measurement == UnitOfEnergy.KILO_WATT_HOUR
        assert desc.device_class == SensorDeviceClass.ENERGY
        assert desc.icon == "mdi:ev-station"

    def test_last_session_cost_description(self):
        """Test last session cost sensor description."""
        desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == SENSOR_LAST_SESSION_COST)

        assert desc.native_unit_of_measurement == CURRENCY_CZK
        assert desc.device_class == SensorDeviceClass.MONETARY
        assert desc.icon == "mdi:currency-usd"

    def test_avg_cost_per_kwh_description(self):
        """Test average cost per kWh sensor description."""
        desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == SENSOR_AVG_COST_PER_KWH)

        assert desc.native_unit_of_measurement == UNIT_CZK_PER_KWH
        assert desc.icon == "mdi:chart-line"


class TestEVTrackerSensor:
    """Test EVTrackerSensor class."""

    @pytest.fixture
    def sensor_monthly_energy(self, mock_coordinator: MagicMock) -> EVTrackerSensor:
        """Create monthly energy sensor."""
        desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == SENSOR_MONTHLY_ENERGY)
        return EVTrackerSensor(mock_coordinator, desc)

    @pytest.fixture
    def sensor_monthly_sessions(self, mock_coordinator: MagicMock) -> EVTrackerSensor:
        """Create monthly sessions sensor."""
        desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == SENSOR_MONTHLY_SESSIONS)
        return EVTrackerSensor(mock_coordinator, desc)

    @pytest.fixture
    def sensor_last_session_energy(self, mock_coordinator: MagicMock) -> EVTrackerSensor:
        """Create last session energy sensor."""
        desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == SENSOR_LAST_SESSION_ENERGY)
        return EVTrackerSensor(mock_coordinator, desc)

    def test_unique_id(
        self,
        sensor_monthly_energy: EVTrackerSensor,
        mock_car_id: int,
    ):
        """Test sensor unique ID."""
        assert sensor_monthly_energy.unique_id == f"{mock_car_id}_{SENSOR_MONTHLY_ENERGY}"

    def test_has_entity_name(self, sensor_monthly_energy: EVTrackerSensor):
        """Test sensor has entity name."""
        assert sensor_monthly_energy._attr_has_entity_name is True

    def test_device_info(
        self,
        sensor_monthly_energy: EVTrackerSensor,
        mock_car_id: int,
        mock_car_name: str,
    ):
        """Test sensor device info."""
        device_info = sensor_monthly_energy.device_info

        assert device_info["identifiers"] == {(DOMAIN, str(mock_car_id))}
        assert device_info["name"] == f"EV Tracker - {mock_car_name}"
        assert device_info["manufacturer"] == "EV Tracker"
        assert device_info["model"] == "Cloud Integration"
        assert device_info["sw_version"] == VERSION
        assert device_info["entry_type"] == DeviceEntryType.SERVICE
        assert device_info["configuration_url"] == "https://evtracker.cz/settings/api-keys"

    def test_native_value_monthly_energy(
        self,
        sensor_monthly_energy: EVTrackerSensor,
        mock_state_response: dict,
    ):
        """Test monthly energy native value."""
        value = sensor_monthly_energy.native_value

        assert value == mock_state_response["currentMonth"]["energyConsumedKwh"]

    def test_native_value_with_no_value_fn(self, mock_coordinator: MagicMock):
        """Test native value when value_fn is None."""
        desc = EVTrackerSensorEntityDescription(
            key="test_sensor",
            translation_key="test_sensor",
            value_fn=None,
        )
        sensor = EVTrackerSensor(mock_coordinator, desc)

        assert sensor.native_value is None


class TestSensorExtraStateAttributes:
    """Test sensor extra state attributes."""

    @pytest.fixture
    def sensor_last_session_energy(self, mock_coordinator: MagicMock) -> EVTrackerSensor:
        """Create last session energy sensor."""
        desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == SENSOR_LAST_SESSION_ENERGY)
        return EVTrackerSensor(mock_coordinator, desc)

    @pytest.fixture
    def sensor_monthly_sessions(self, mock_coordinator: MagicMock) -> EVTrackerSensor:
        """Create monthly sessions sensor."""
        desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == SENSOR_MONTHLY_SESSIONS)
        return EVTrackerSensor(mock_coordinator, desc)

    @pytest.fixture
    def sensor_monthly_energy(self, mock_coordinator: MagicMock) -> EVTrackerSensor:
        """Create monthly energy sensor."""
        desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == SENSOR_MONTHLY_ENERGY)
        return EVTrackerSensor(mock_coordinator, desc)

    def test_last_session_energy_attributes(
        self,
        sensor_last_session_energy: EVTrackerSensor,
        mock_state_response: dict,
    ):
        """Test last session energy extra attributes."""
        attrs = sensor_last_session_energy.extra_state_attributes

        assert attrs is not None
        assert attrs["car_name"] == mock_state_response["lastSession"]["carName"]
        assert attrs["start_time"] == mock_state_response["lastSession"]["startTime"]
        assert attrs["end_time"] == mock_state_response["lastSession"]["endTime"]
        assert attrs["provider"] == mock_state_response["lastSession"]["provider"]
        assert attrs["location"] == mock_state_response["lastSession"]["location"]

    def test_monthly_sessions_attributes(
        self,
        sensor_monthly_sessions: EVTrackerSensor,
        mock_state_response: dict,
    ):
        """Test monthly sessions extra attributes."""
        attrs = sensor_monthly_sessions.extra_state_attributes

        assert attrs is not None
        assert attrs["currency"] == mock_state_response["currentMonth"]["currency"]

    def test_other_sensor_no_attributes(
        self,
        sensor_monthly_energy: EVTrackerSensor,
    ):
        """Test that other sensors return no extra attributes."""
        attrs = sensor_monthly_energy.extra_state_attributes

        assert attrs is None

    def test_last_session_no_data(self, mock_coordinator: MagicMock):
        """Test last session attributes when no session data."""
        mock_coordinator.last_session = None
        desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == SENSOR_LAST_SESSION_ENERGY)
        sensor = EVTrackerSensor(mock_coordinator, desc)

        attrs = sensor.extra_state_attributes

        # Should return empty dict or None when no data
        assert attrs is None or attrs == {}

    def test_monthly_sessions_no_data(self, mock_coordinator: MagicMock):
        """Test monthly sessions attributes when no month data."""
        mock_coordinator.current_month = None
        desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == SENSOR_MONTHLY_SESSIONS)
        sensor = EVTrackerSensor(mock_coordinator, desc)

        attrs = sensor.extra_state_attributes

        # Should return empty dict or None when no data
        assert attrs is None or attrs == {}


class TestSensorValueFunctions:
    """Test sensor value functions."""

    def test_all_value_functions(self, mock_coordinator: MagicMock, mock_state_response: dict):
        """Test all sensor value functions return expected values."""
        expected_values = {
            SENSOR_MONTHLY_ENERGY: mock_state_response["currentMonth"]["energyConsumedKwh"],
            SENSOR_MONTHLY_COST: mock_state_response["currentMonth"]["totalCostWithVat"],
            SENSOR_MONTHLY_SESSIONS: mock_state_response["currentMonth"]["sessionCount"],
            SENSOR_YEARLY_ENERGY: mock_state_response["currentYear"]["energyConsumedKwh"],
            SENSOR_YEARLY_COST: mock_state_response["currentYear"]["totalCostWithVat"],
            SENSOR_LAST_SESSION_ENERGY: mock_state_response["lastSession"]["energyConsumedKwh"],
            SENSOR_LAST_SESSION_COST: mock_state_response["lastSession"]["totalCostWithVat"],
            SENSOR_AVG_COST_PER_KWH: mock_state_response["currentMonth"]["averageCostPerKwh"],
        }

        for desc in SENSOR_DESCRIPTIONS:
            if desc.value_fn:
                value = desc.value_fn(mock_coordinator)
                assert value == expected_values[desc.key], f"Mismatch for {desc.key}"

    def test_value_functions_with_none_data(self, mock_coordinator: MagicMock):
        """Test value functions return None when data is missing."""
        mock_coordinator.current_month = None
        mock_coordinator.current_year = None
        mock_coordinator.last_session = None

        for desc in SENSOR_DESCRIPTIONS:
            if desc.value_fn:
                value = desc.value_fn(mock_coordinator)
                assert value is None, f"Expected None for {desc.key}"


class TestAsyncSetupEntry:
    """Test async_setup_entry function."""

    @pytest.fixture
    def mock_config_entry(
        self,
        mock_api_key: str,
        mock_car_id: int,
        mock_car_name: str,
    ) -> MagicMock:
        """Create a mock config entry."""
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "test_entry_id"
        entry.data = {
            CONF_API_KEY: mock_api_key,
            CONF_CAR_ID: mock_car_id,
            CONF_CAR_NAME: mock_car_name,
        }
        entry.options = {}
        return entry

    @pytest.mark.asyncio
    async def test_async_setup_entry_creates_entities(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
        mock_config_entry: MagicMock,
    ):
        """Test that async_setup_entry creates all sensor entities."""
        hass.data[DOMAIN] = {mock_config_entry.entry_id: mock_coordinator}

        added_entities = []

        def async_add_entities(entities):
            added_entities.extend(entities)

        await async_setup_entry(hass, mock_config_entry, async_add_entities)

        # Should create all 8 sensor entities
        assert len(added_entities) == 8
        assert all(isinstance(e, EVTrackerSensor) for e in added_entities)

    @pytest.mark.asyncio
    async def test_async_setup_entry_creates_correct_sensors(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
        mock_config_entry: MagicMock,
    ):
        """Test that async_setup_entry creates the correct sensors."""
        hass.data[DOMAIN] = {mock_config_entry.entry_id: mock_coordinator}

        added_entities = []

        def async_add_entities(entities):
            added_entities.extend(entities)

        await async_setup_entry(hass, mock_config_entry, async_add_entities)

        # Check all expected sensor keys
        expected_keys = {
            SENSOR_MONTHLY_ENERGY,
            SENSOR_MONTHLY_COST,
            SENSOR_MONTHLY_SESSIONS,
            SENSOR_YEARLY_ENERGY,
            SENSOR_YEARLY_COST,
            SENSOR_LAST_SESSION_ENERGY,
            SENSOR_LAST_SESSION_COST,
            SENSOR_AVG_COST_PER_KWH,
        }
        actual_keys = {e.entity_description.key for e in added_entities}
        assert actual_keys == expected_keys
