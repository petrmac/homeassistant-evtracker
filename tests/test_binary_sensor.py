"""Tests for EV Tracker binary sensors."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.helpers.device_registry import DeviceEntryType

from custom_components.evtracker.binary_sensor import (
    BINARY_SENSOR_DESCRIPTIONS,
    EVTrackerBinarySensor,
)
from custom_components.evtracker.const import (
    BINARY_SENSOR_CONNECTED,
    DOMAIN,
    VERSION,
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
