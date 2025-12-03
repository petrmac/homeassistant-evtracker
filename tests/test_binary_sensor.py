"""Tests for EV Tracker binary sensors."""

from __future__ import annotations

from datetime import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.device_registry import DeviceEntryType

from custom_components.evtracker.binary_sensor import (
    BINARY_SENSOR_DESCRIPTIONS,
    EVTrackerBinarySensor,
    EVTrackerLowTariffSensor,
    async_setup_entry,
)
from custom_components.evtracker.const import (
    BINARY_SENSOR_CONNECTED,
    BINARY_SENSOR_LOW_TARIFF,
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
    DOMAIN,
    TARIFF_SOURCE_ENTITY,
    TARIFF_SOURCE_SCHEDULE,
    VERSION,
    WINDOW_TYPE_HIGH,
    WINDOW_TYPE_LOW,
)


class TestBinarySensorDescriptions:
    """Test binary sensor descriptions."""

    def test_binary_sensor_count(self):
        """Test that all binary sensors are defined."""
        assert len(BINARY_SENSOR_DESCRIPTIONS) == 1

    def test_connected_description(self):
        """Test connected binary sensor description."""
        desc = next(d for d in BINARY_SENSOR_DESCRIPTIONS if d.key == BINARY_SENSOR_CONNECTED)

        assert desc.device_class == BinarySensorDeviceClass.CONNECTIVITY
        assert desc.translation_key == BINARY_SENSOR_CONNECTED


class TestEVTrackerBinarySensor:
    """Test EVTrackerBinarySensor class."""

    @pytest.fixture
    def binary_sensor_connected(self, mock_coordinator: MagicMock) -> EVTrackerBinarySensor:
        """Create connected binary sensor."""
        desc = next(d for d in BINARY_SENSOR_DESCRIPTIONS if d.key == BINARY_SENSOR_CONNECTED)
        return EVTrackerBinarySensor(mock_coordinator, desc)

    def test_unique_id(
        self,
        binary_sensor_connected: EVTrackerBinarySensor,
        mock_car_id: int,
    ):
        """Test binary sensor unique ID."""
        assert binary_sensor_connected.unique_id == f"{mock_car_id}_{BINARY_SENSOR_CONNECTED}"

    def test_has_entity_name(self, binary_sensor_connected: EVTrackerBinarySensor):
        """Test binary sensor has entity name."""
        assert binary_sensor_connected._attr_has_entity_name is True

    def test_device_info(
        self,
        binary_sensor_connected: EVTrackerBinarySensor,
        mock_car_id: int,
        mock_car_name: str,
    ):
        """Test binary sensor device info."""
        device_info = binary_sensor_connected.device_info

        assert device_info["identifiers"] == {(DOMAIN, str(mock_car_id))}
        assert device_info["name"] == f"EV Tracker - {mock_car_name}"
        assert device_info["manufacturer"] == "EV Tracker"
        assert device_info["model"] == "Cloud Integration"
        assert device_info["sw_version"] == VERSION
        assert device_info["entry_type"] == DeviceEntryType.SERVICE
        assert device_info["configuration_url"] == "https://evtracker.cz/settings/api-keys"


class TestBinarySensorIsOn:
    """Test binary sensor is_on property."""

    @pytest.fixture
    def binary_sensor(self, mock_coordinator: MagicMock) -> EVTrackerBinarySensor:
        """Create connected binary sensor."""
        desc = next(d for d in BINARY_SENSOR_DESCRIPTIONS if d.key == BINARY_SENSOR_CONNECTED)
        return EVTrackerBinarySensor(mock_coordinator, desc)

    def test_is_on_when_connected_and_successful(
        self,
        mock_coordinator: MagicMock,
    ):
        """Test is_on is True when connected and update successful."""
        mock_coordinator.is_connected = True
        mock_coordinator.last_update_success = True

        desc = next(d for d in BINARY_SENSOR_DESCRIPTIONS if d.key == BINARY_SENSOR_CONNECTED)
        sensor = EVTrackerBinarySensor(mock_coordinator, desc)

        assert sensor.is_on is True

    def test_is_off_when_not_connected(
        self,
        mock_coordinator: MagicMock,
    ):
        """Test is_on is False when not connected."""
        mock_coordinator.is_connected = False
        mock_coordinator.last_update_success = True

        desc = next(d for d in BINARY_SENSOR_DESCRIPTIONS if d.key == BINARY_SENSOR_CONNECTED)
        sensor = EVTrackerBinarySensor(mock_coordinator, desc)

        assert sensor.is_on is False

    def test_is_off_when_update_failed(
        self,
        mock_coordinator: MagicMock,
    ):
        """Test is_on is False when update failed."""
        mock_coordinator.is_connected = True
        mock_coordinator.last_update_success = False

        desc = next(d for d in BINARY_SENSOR_DESCRIPTIONS if d.key == BINARY_SENSOR_CONNECTED)
        sensor = EVTrackerBinarySensor(mock_coordinator, desc)

        assert sensor.is_on is False

    def test_is_off_when_both_false(
        self,
        mock_coordinator: MagicMock,
    ):
        """Test is_on is False when both conditions are False."""
        mock_coordinator.is_connected = False
        mock_coordinator.last_update_success = False

        desc = next(d for d in BINARY_SENSOR_DESCRIPTIONS if d.key == BINARY_SENSOR_CONNECTED)
        sensor = EVTrackerBinarySensor(mock_coordinator, desc)

        assert sensor.is_on is False


class TestAsyncSetupEntry:
    """Test async_setup_entry function."""

    @pytest.mark.asyncio
    async def test_setup_without_tariff(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ):
        """Test setup without tariff configuration."""
        config_entry = MagicMock()
        config_entry.entry_id = "test_entry"
        config_entry.options = {}

        hass.data[DOMAIN] = {config_entry.entry_id: mock_coordinator}

        entities_added = []

        def async_add_entities(entities):
            entities_added.extend(entities)

        await async_setup_entry(hass, config_entry, async_add_entities)

        assert len(entities_added) == 1
        assert isinstance(entities_added[0], EVTrackerBinarySensor)

    @pytest.mark.asyncio
    async def test_setup_with_schedule_tariff(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ):
        """Test setup with schedule tariff configuration."""
        config_entry = MagicMock()
        config_entry.entry_id = "test_entry"
        config_entry.options = {CONF_TARIFF_SOURCE: TARIFF_SOURCE_SCHEDULE}

        hass.data[DOMAIN] = {config_entry.entry_id: mock_coordinator}

        entities_added = []

        def async_add_entities(entities):
            entities_added.extend(entities)

        await async_setup_entry(hass, config_entry, async_add_entities)

        assert len(entities_added) == 2
        assert isinstance(entities_added[0], EVTrackerBinarySensor)
        assert isinstance(entities_added[1], EVTrackerLowTariffSensor)

    @pytest.mark.asyncio
    async def test_setup_with_entity_tariff(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ):
        """Test setup with entity tariff configuration."""
        config_entry = MagicMock()
        config_entry.entry_id = "test_entry"
        config_entry.options = {CONF_TARIFF_SOURCE: TARIFF_SOURCE_ENTITY}

        hass.data[DOMAIN] = {config_entry.entry_id: mock_coordinator}

        entities_added = []

        def async_add_entities(entities):
            entities_added.extend(entities)

        await async_setup_entry(hass, config_entry, async_add_entities)

        assert len(entities_added) == 2
        assert isinstance(entities_added[1], EVTrackerLowTariffSensor)


class TestEVTrackerLowTariffSensor:
    """Test EVTrackerLowTariffSensor class."""

    @pytest.fixture
    def tariff_sensor(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> EVTrackerLowTariffSensor:
        """Create tariff sensor."""
        config_entry = MagicMock()
        config_entry.options = {
            CONF_TARIFF_SOURCE: TARIFF_SOURCE_SCHEDULE,
            CONF_TARIFF_LOW_START_1: "22:00",
            CONF_TARIFF_LOW_END_1: "06:00",
        }
        return EVTrackerLowTariffSensor(hass, mock_coordinator, config_entry)

    def test_unique_id(
        self,
        tariff_sensor: EVTrackerLowTariffSensor,
        mock_car_id: int,
    ):
        """Test tariff sensor unique ID."""
        assert tariff_sensor.unique_id == f"{mock_car_id}_{BINARY_SENSOR_LOW_TARIFF}"

    def test_has_entity_name(self, tariff_sensor: EVTrackerLowTariffSensor):
        """Test tariff sensor has entity name."""
        assert tariff_sensor._attr_has_entity_name is True

    def test_translation_key(self, tariff_sensor: EVTrackerLowTariffSensor):
        """Test tariff sensor translation key."""
        assert tariff_sensor._attr_translation_key == BINARY_SENSOR_LOW_TARIFF

    def test_device_class(self, tariff_sensor: EVTrackerLowTariffSensor):
        """Test tariff sensor device class."""
        assert tariff_sensor._attr_device_class == BinarySensorDeviceClass.POWER

    def test_device_info(
        self,
        tariff_sensor: EVTrackerLowTariffSensor,
        mock_car_id: int,
        mock_car_name: str,
    ):
        """Test tariff sensor device info."""
        device_info = tariff_sensor.device_info

        assert device_info["identifiers"] == {(DOMAIN, str(mock_car_id))}
        assert device_info["name"] == f"EV Tracker - {mock_car_name}"
        assert device_info["manufacturer"] == "EV Tracker"
        assert device_info["sw_version"] == VERSION
        assert device_info["entry_type"] == DeviceEntryType.SERVICE

    def test_is_on_default_false(self, tariff_sensor: EVTrackerLowTariffSensor):
        """Test is_on defaults to False."""
        assert tariff_sensor.is_on is False

    def test_is_on_after_update(self, tariff_sensor: EVTrackerLowTariffSensor):
        """Test is_on after manual update."""
        tariff_sensor._is_on = True
        assert tariff_sensor.is_on is True


class TestLowTariffExtraAttributes:
    """Test extra state attributes for tariff sensor."""

    def test_schedule_attributes(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ):
        """Test attributes for schedule-based tariff."""
        config_entry = MagicMock()
        config_entry.options = {
            CONF_TARIFF_SOURCE: TARIFF_SOURCE_SCHEDULE,
            CONF_TARIFF_WINDOW_TYPE: WINDOW_TYPE_LOW,
            CONF_TARIFF_LOW_START_1: "22:00",
            CONF_TARIFF_LOW_END_1: "06:00",
            CONF_TARIFF_LOW_START_2: "14:00",
            CONF_TARIFF_LOW_END_2: "17:00",
            CONF_TARIFF_WEEKEND_LOW: True,
        }
        sensor = EVTrackerLowTariffSensor(hass, mock_coordinator, config_entry)
        attrs = sensor.extra_state_attributes

        assert attrs["tariff_source"] == TARIFF_SOURCE_SCHEDULE
        assert attrs["window_type"] == WINDOW_TYPE_LOW
        assert attrs["window_1_start"] == "22:00"
        assert attrs["window_1_end"] == "06:00"
        assert attrs["window_2_start"] == "14:00"
        assert attrs["window_2_end"] == "17:00"
        assert attrs["weekend_always_low"] is True

    def test_schedule_attributes_all_windows(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ):
        """Test attributes for schedule with all 4 windows."""
        config_entry = MagicMock()
        config_entry.options = {
            CONF_TARIFF_SOURCE: TARIFF_SOURCE_SCHEDULE,
            CONF_TARIFF_WINDOW_TYPE: WINDOW_TYPE_LOW,
            CONF_TARIFF_LOW_START_1: "00:00",
            CONF_TARIFF_LOW_END_1: "06:00",
            CONF_TARIFF_LOW_START_2: "10:00",
            CONF_TARIFF_LOW_END_2: "12:00",
            CONF_TARIFF_LOW_START_3: "14:00",
            CONF_TARIFF_LOW_END_3: "16:00",
            CONF_TARIFF_LOW_START_4: "22:00",
            CONF_TARIFF_LOW_END_4: "23:59",
            CONF_TARIFF_WEEKEND_LOW: False,
        }
        sensor = EVTrackerLowTariffSensor(hass, mock_coordinator, config_entry)
        attrs = sensor.extra_state_attributes

        assert attrs["tariff_source"] == TARIFF_SOURCE_SCHEDULE
        assert attrs["window_1_start"] == "00:00"
        assert attrs["window_1_end"] == "06:00"
        assert attrs["window_2_start"] == "10:00"
        assert attrs["window_2_end"] == "12:00"
        assert attrs["window_3_start"] == "14:00"
        assert attrs["window_3_end"] == "16:00"
        assert attrs["window_4_start"] == "22:00"
        assert attrs["window_4_end"] == "23:59"
        assert attrs["weekend_always_low"] is False

    def test_entity_attributes(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ):
        """Test attributes for entity-based tariff."""
        config_entry = MagicMock()
        config_entry.options = {
            CONF_TARIFF_SOURCE: TARIFF_SOURCE_ENTITY,
            CONF_TARIFF_ENTITY: "binary_sensor.low_tariff",
        }
        sensor = EVTrackerLowTariffSensor(hass, mock_coordinator, config_entry)
        attrs = sensor.extra_state_attributes

        assert attrs["tariff_source"] == TARIFF_SOURCE_ENTITY
        assert attrs["source_entity"] == "binary_sensor.low_tariff"


class TestScheduleStateUpdate:
    """Test _update_schedule_state method."""

    @pytest.fixture
    def schedule_sensor(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ):
        """Create schedule-based tariff sensor."""
        config_entry = MagicMock()
        config_entry.options = {
            CONF_TARIFF_SOURCE: TARIFF_SOURCE_SCHEDULE,
            CONF_TARIFF_WINDOW_TYPE: WINDOW_TYPE_LOW,
            CONF_TARIFF_LOW_START_1: "22:00",
            CONF_TARIFF_LOW_END_1: "06:00",
        }
        return EVTrackerLowTariffSensor(hass, mock_coordinator, config_entry)

    def test_in_low_window_overnight(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ):
        """Test is_on when in overnight LOW window (23:00)."""
        config_entry = MagicMock()
        config_entry.options = {
            CONF_TARIFF_SOURCE: TARIFF_SOURCE_SCHEDULE,
            CONF_TARIFF_WINDOW_TYPE: WINDOW_TYPE_LOW,
            CONF_TARIFF_LOW_START_1: "22:00",
            CONF_TARIFF_LOW_END_1: "06:00",
        }
        sensor = EVTrackerLowTariffSensor(hass, mock_coordinator, config_entry)

        # Mock datetime to 23:00 on a weekday (Monday)
        with patch("custom_components.evtracker.binary_sensor.datetime") as mock_dt:
            mock_now = MagicMock()
            mock_now.weekday.return_value = 0  # Monday
            mock_now.time.return_value = time(23, 0)
            mock_dt.now.return_value = mock_now

            sensor._update_schedule_state()

        assert sensor._is_on is True

    def test_outside_low_window(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ):
        """Test is_on is False when outside LOW window (12:00)."""
        config_entry = MagicMock()
        config_entry.options = {
            CONF_TARIFF_SOURCE: TARIFF_SOURCE_SCHEDULE,
            CONF_TARIFF_WINDOW_TYPE: WINDOW_TYPE_LOW,
            CONF_TARIFF_LOW_START_1: "22:00",
            CONF_TARIFF_LOW_END_1: "06:00",
        }
        sensor = EVTrackerLowTariffSensor(hass, mock_coordinator, config_entry)

        with patch("custom_components.evtracker.binary_sensor.datetime") as mock_dt:
            mock_now = MagicMock()
            mock_now.weekday.return_value = 0  # Monday
            mock_now.time.return_value = time(12, 0)
            mock_dt.now.return_value = mock_now

            sensor._update_schedule_state()

        assert sensor._is_on is False

    def test_weekend_always_low(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ):
        """Test is_on is True on weekends when weekend_always_low is enabled."""
        config_entry = MagicMock()
        config_entry.options = {
            CONF_TARIFF_SOURCE: TARIFF_SOURCE_SCHEDULE,
            CONF_TARIFF_WINDOW_TYPE: WINDOW_TYPE_LOW,
            CONF_TARIFF_LOW_START_1: "22:00",
            CONF_TARIFF_LOW_END_1: "06:00",
            CONF_TARIFF_WEEKEND_LOW: True,
        }
        sensor = EVTrackerLowTariffSensor(hass, mock_coordinator, config_entry)

        with patch("custom_components.evtracker.binary_sensor.datetime") as mock_dt:
            mock_now = MagicMock()
            mock_now.weekday.return_value = 5  # Saturday
            mock_now.time.return_value = time(12, 0)  # Midday - normally HIGH
            mock_dt.now.return_value = mock_now

            sensor._update_schedule_state()

        assert sensor._is_on is True

    def test_window_type_high(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ):
        """Test HIGH window type - windows define HIGH periods."""
        config_entry = MagicMock()
        config_entry.options = {
            CONF_TARIFF_SOURCE: TARIFF_SOURCE_SCHEDULE,
            CONF_TARIFF_WINDOW_TYPE: WINDOW_TYPE_HIGH,
            CONF_TARIFF_LOW_START_1: "07:00",
            CONF_TARIFF_LOW_END_1: "21:00",  # HIGH period
        }
        sensor = EVTrackerLowTariffSensor(hass, mock_coordinator, config_entry)

        # At 23:00 - outside HIGH window, so LOW tariff
        with patch("custom_components.evtracker.binary_sensor.datetime") as mock_dt:
            mock_now = MagicMock()
            mock_now.weekday.return_value = 0
            mock_now.time.return_value = time(23, 0)
            mock_dt.now.return_value = mock_now

            sensor._update_schedule_state()

        assert sensor._is_on is True  # Outside HIGH window = LOW

    def test_window_type_high_inside_window(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ):
        """Test HIGH window type - inside HIGH window means HIGH tariff."""
        config_entry = MagicMock()
        config_entry.options = {
            CONF_TARIFF_SOURCE: TARIFF_SOURCE_SCHEDULE,
            CONF_TARIFF_WINDOW_TYPE: WINDOW_TYPE_HIGH,
            CONF_TARIFF_LOW_START_1: "07:00",
            CONF_TARIFF_LOW_END_1: "21:00",
        }
        sensor = EVTrackerLowTariffSensor(hass, mock_coordinator, config_entry)

        # At 12:00 - inside HIGH window
        with patch("custom_components.evtracker.binary_sensor.datetime") as mock_dt:
            mock_now = MagicMock()
            mock_now.weekday.return_value = 0
            mock_now.time.return_value = time(12, 0)
            mock_dt.now.return_value = mock_now

            sensor._update_schedule_state()

        assert sensor._is_on is False  # Inside HIGH window = not LOW

    def test_multiple_windows(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ):
        """Test multiple time windows."""
        config_entry = MagicMock()
        config_entry.options = {
            CONF_TARIFF_SOURCE: TARIFF_SOURCE_SCHEDULE,
            CONF_TARIFF_WINDOW_TYPE: WINDOW_TYPE_LOW,
            CONF_TARIFF_LOW_START_1: "22:00",
            CONF_TARIFF_LOW_END_1: "06:00",
            CONF_TARIFF_LOW_START_2: "14:00",
            CONF_TARIFF_LOW_END_2: "17:00",
        }
        sensor = EVTrackerLowTariffSensor(hass, mock_coordinator, config_entry)

        # At 15:00 - inside second window
        with patch("custom_components.evtracker.binary_sensor.datetime") as mock_dt:
            mock_now = MagicMock()
            mock_now.weekday.return_value = 0
            mock_now.time.return_value = time(15, 0)
            mock_dt.now.return_value = mock_now

            sensor._update_schedule_state()

        assert sensor._is_on is True


class TestTimeInWindow:
    """Test _is_time_in_window method."""

    @pytest.fixture
    def sensor(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> EVTrackerLowTariffSensor:
        """Create sensor for testing."""
        config_entry = MagicMock()
        config_entry.options = {}
        return EVTrackerLowTariffSensor(hass, mock_coordinator, config_entry)

    def test_normal_window_inside(self, sensor: EVTrackerLowTariffSensor):
        """Test time inside normal window (08:00-12:00)."""
        result = sensor._is_time_in_window(time(10, 0), "08:00", "12:00")
        assert result is True

    def test_normal_window_outside(self, sensor: EVTrackerLowTariffSensor):
        """Test time outside normal window."""
        result = sensor._is_time_in_window(time(14, 0), "08:00", "12:00")
        assert result is False

    def test_normal_window_at_start(self, sensor: EVTrackerLowTariffSensor):
        """Test time at window start."""
        result = sensor._is_time_in_window(time(8, 0), "08:00", "12:00")
        assert result is True

    def test_normal_window_at_end(self, sensor: EVTrackerLowTariffSensor):
        """Test time at window end."""
        result = sensor._is_time_in_window(time(12, 0), "08:00", "12:00")
        assert result is True

    def test_overnight_window_before_midnight(self, sensor: EVTrackerLowTariffSensor):
        """Test overnight window before midnight (22:00-06:00)."""
        result = sensor._is_time_in_window(time(23, 0), "22:00", "06:00")
        assert result is True

    def test_overnight_window_after_midnight(self, sensor: EVTrackerLowTariffSensor):
        """Test overnight window after midnight."""
        result = sensor._is_time_in_window(time(3, 0), "22:00", "06:00")
        assert result is True

    def test_overnight_window_outside(self, sensor: EVTrackerLowTariffSensor):
        """Test time outside overnight window."""
        result = sensor._is_time_in_window(time(12, 0), "22:00", "06:00")
        assert result is False

    def test_invalid_time_format(self, sensor: EVTrackerLowTariffSensor):
        """Test invalid time format returns False."""
        result = sensor._is_time_in_window(time(12, 0), "invalid", "06:00")
        assert result is False


class TestEntityStateUpdate:
    """Test _update_entity_state method."""

    def test_entity_on(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ):
        """Test entity state 'on' means LOW tariff."""
        config_entry = MagicMock()
        config_entry.options = {
            CONF_TARIFF_SOURCE: TARIFF_SOURCE_ENTITY,
            CONF_TARIFF_ENTITY: "binary_sensor.low_tariff",
        }
        sensor = EVTrackerLowTariffSensor(hass, mock_coordinator, config_entry)

        hass.states._states["binary_sensor.low_tariff"] = State(
            "binary_sensor.low_tariff", "on"
        )

        sensor._update_entity_state()

        assert sensor._is_on is True

    def test_entity_off(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ):
        """Test entity state 'off' means HIGH tariff."""
        config_entry = MagicMock()
        config_entry.options = {
            CONF_TARIFF_SOURCE: TARIFF_SOURCE_ENTITY,
            CONF_TARIFF_ENTITY: "binary_sensor.low_tariff",
        }
        sensor = EVTrackerLowTariffSensor(hass, mock_coordinator, config_entry)

        hass.states._states["binary_sensor.low_tariff"] = State(
            "binary_sensor.low_tariff", "off"
        )

        sensor._update_entity_state()

        assert sensor._is_on is False

    def test_entity_true(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ):
        """Test entity state 'true' means LOW tariff."""
        config_entry = MagicMock()
        config_entry.options = {
            CONF_TARIFF_SOURCE: TARIFF_SOURCE_ENTITY,
            CONF_TARIFF_ENTITY: "sensor.tariff",
        }
        sensor = EVTrackerLowTariffSensor(hass, mock_coordinator, config_entry)

        hass.states._states["sensor.tariff"] = State("sensor.tariff", "true")

        sensor._update_entity_state()

        assert sensor._is_on is True

    def test_entity_low(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ):
        """Test entity state 'low' means LOW tariff."""
        config_entry = MagicMock()
        config_entry.options = {
            CONF_TARIFF_SOURCE: TARIFF_SOURCE_ENTITY,
            CONF_TARIFF_ENTITY: "sensor.tariff",
        }
        sensor = EVTrackerLowTariffSensor(hass, mock_coordinator, config_entry)

        hass.states._states["sensor.tariff"] = State("sensor.tariff", "LOW")

        sensor._update_entity_state()

        assert sensor._is_on is True

    def test_entity_not_found(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ):
        """Test entity not found means HIGH tariff."""
        config_entry = MagicMock()
        config_entry.options = {
            CONF_TARIFF_SOURCE: TARIFF_SOURCE_ENTITY,
            CONF_TARIFF_ENTITY: "binary_sensor.nonexistent",
        }
        sensor = EVTrackerLowTariffSensor(hass, mock_coordinator, config_entry)

        sensor._update_entity_state()

        assert sensor._is_on is False

    def test_no_entity_configured(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ):
        """Test no entity configured means HIGH tariff."""
        config_entry = MagicMock()
        config_entry.options = {
            CONF_TARIFF_SOURCE: TARIFF_SOURCE_ENTITY,
        }
        sensor = EVTrackerLowTariffSensor(hass, mock_coordinator, config_entry)

        sensor._update_entity_state()

        assert sensor._is_on is False


class TestTariffSensorLifecycle:
    """Test tariff sensor lifecycle methods."""

    @pytest.mark.asyncio
    async def test_async_added_to_hass_schedule(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ):
        """Test async_added_to_hass with schedule tariff."""
        config_entry = MagicMock()
        config_entry.options = {
            CONF_TARIFF_SOURCE: TARIFF_SOURCE_SCHEDULE,
            CONF_TARIFF_LOW_START_1: "22:00",
            CONF_TARIFF_LOW_END_1: "06:00",
        }
        sensor = EVTrackerLowTariffSensor(hass, mock_coordinator, config_entry)

        with patch("custom_components.evtracker.binary_sensor.async_track_time_change") as mock_track:
            mock_track.return_value = MagicMock()

            await sensor.async_added_to_hass()

            mock_track.assert_called_once()
            assert len(sensor._unsubscribe_callbacks) == 1

    @pytest.mark.asyncio
    async def test_async_added_to_hass_entity(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ):
        """Test async_added_to_hass with entity tariff."""
        config_entry = MagicMock()
        config_entry.options = {
            CONF_TARIFF_SOURCE: TARIFF_SOURCE_ENTITY,
            CONF_TARIFF_ENTITY: "binary_sensor.low_tariff",
        }
        sensor = EVTrackerLowTariffSensor(hass, mock_coordinator, config_entry)

        hass.states._states["binary_sensor.low_tariff"] = State(
            "binary_sensor.low_tariff", "on"
        )

        with patch("custom_components.evtracker.binary_sensor.async_track_state_change_event") as mock_track:
            mock_track.return_value = MagicMock()

            await sensor.async_added_to_hass()

            mock_track.assert_called_once()
            assert len(sensor._unsubscribe_callbacks) == 1

    @pytest.mark.asyncio
    async def test_async_will_remove_from_hass(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ):
        """Test async_will_remove_from_hass clears callbacks."""
        config_entry = MagicMock()
        config_entry.options = {}
        sensor = EVTrackerLowTariffSensor(hass, mock_coordinator, config_entry)

        mock_unsubscribe = MagicMock()
        sensor._unsubscribe_callbacks.append(mock_unsubscribe)

        await sensor.async_will_remove_from_hass()

        mock_unsubscribe.assert_called_once()
        assert len(sensor._unsubscribe_callbacks) == 0

    def test_handle_time_change(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ):
        """Test _handle_time_change callback."""
        config_entry = MagicMock()
        config_entry.options = {
            CONF_TARIFF_SOURCE: TARIFF_SOURCE_SCHEDULE,
            CONF_TARIFF_LOW_START_1: "22:00",
            CONF_TARIFF_LOW_END_1: "06:00",
        }
        sensor = EVTrackerLowTariffSensor(hass, mock_coordinator, config_entry)

        with patch.object(sensor, "_update_schedule_state") as mock_update:
            with patch.object(sensor, "async_write_ha_state") as mock_write:
                from datetime import datetime
                sensor._handle_time_change(datetime.now())

                mock_update.assert_called_once()
                mock_write.assert_called_once()

    def test_handle_entity_change(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ):
        """Test _handle_entity_change callback."""
        config_entry = MagicMock()
        config_entry.options = {
            CONF_TARIFF_SOURCE: TARIFF_SOURCE_ENTITY,
            CONF_TARIFF_ENTITY: "binary_sensor.low_tariff",
        }
        sensor = EVTrackerLowTariffSensor(hass, mock_coordinator, config_entry)

        with patch.object(sensor, "_update_entity_state") as mock_update:
            with patch.object(sensor, "async_write_ha_state") as mock_write:
                sensor._handle_entity_change(MagicMock())

                mock_update.assert_called_once()
                mock_write.assert_called_once()
