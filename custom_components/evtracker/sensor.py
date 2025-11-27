"""Sensor platform for EV Tracker integration."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
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
from .coordinator import EVTrackerDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class EVTrackerSensorEntityDescription(SensorEntityDescription):
    """Describes EV Tracker sensor entity."""

    value_fn: Callable[[EVTrackerDataUpdateCoordinator], Any] | None = None


SENSOR_DESCRIPTIONS: tuple[EVTrackerSensorEntityDescription, ...] = (
    EVTrackerSensorEntityDescription(
        key=SENSOR_MONTHLY_ENERGY,
        translation_key=SENSOR_MONTHLY_ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda c: c.current_month.get("energyConsumedKwh") if c.current_month else None,
    ),
    EVTrackerSensorEntityDescription(
        key=SENSOR_MONTHLY_COST,
        translation_key=SENSOR_MONTHLY_COST,
        native_unit_of_measurement=CURRENCY_CZK,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda c: c.current_month.get("totalCostWithVat") if c.current_month else None,
    ),
    EVTrackerSensorEntityDescription(
        key=SENSOR_MONTHLY_SESSIONS,
        translation_key=SENSOR_MONTHLY_SESSIONS,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:counter",
        value_fn=lambda c: c.current_month.get("sessionCount") if c.current_month else None,
    ),
    EVTrackerSensorEntityDescription(
        key=SENSOR_YEARLY_ENERGY,
        translation_key=SENSOR_YEARLY_ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda c: c.current_year.get("energyConsumedKwh") if c.current_year else None,
    ),
    EVTrackerSensorEntityDescription(
        key=SENSOR_YEARLY_COST,
        translation_key=SENSOR_YEARLY_COST,
        native_unit_of_measurement=CURRENCY_CZK,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda c: c.current_year.get("totalCostWithVat") if c.current_year else None,
    ),
    EVTrackerSensorEntityDescription(
        key=SENSOR_LAST_SESSION_ENERGY,
        translation_key=SENSOR_LAST_SESSION_ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        icon="mdi:ev-station",
        value_fn=lambda c: c.last_session.get("energyConsumedKwh") if c.last_session else None,
    ),
    EVTrackerSensorEntityDescription(
        key=SENSOR_LAST_SESSION_COST,
        translation_key=SENSOR_LAST_SESSION_COST,
        native_unit_of_measurement=CURRENCY_CZK,
        device_class=SensorDeviceClass.MONETARY,
        icon="mdi:currency-usd",
        value_fn=lambda c: c.last_session.get("totalCostWithVat") if c.last_session else None,
    ),
    EVTrackerSensorEntityDescription(
        key=SENSOR_AVG_COST_PER_KWH,
        translation_key=SENSOR_AVG_COST_PER_KWH,
        native_unit_of_measurement=UNIT_CZK_PER_KWH,
        icon="mdi:chart-line",
        value_fn=lambda c: c.current_month.get("averageCostPerKwh") if c.current_month else None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up EV Tracker sensor entities."""
    coordinator: EVTrackerDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = [EVTrackerSensor(coordinator, description) for description in SENSOR_DESCRIPTIONS]

    async_add_entities(entities)


class EVTrackerSensor(CoordinatorEntity[EVTrackerDataUpdateCoordinator], SensorEntity):
    """Representation of an EV Tracker sensor."""

    entity_description: EVTrackerSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EVTrackerDataUpdateCoordinator,
        description: EVTrackerSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.car_id}_{description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, str(self.coordinator.car_id))},
            name=f"EV Tracker - {self.coordinator.car_name}",
            manufacturer="EV Tracker",
            model="Cloud Integration",
            sw_version=VERSION,
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://evtracker.cz/settings/api-keys",
        )

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if self.entity_description.value_fn is None:
            return None
        return self.entity_description.value_fn(self.coordinator)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        attrs: dict[str, Any] = {}

        if self.entity_description.key == SENSOR_LAST_SESSION_ENERGY:
            if self.coordinator.last_session:
                session = self.coordinator.last_session
                attrs["car_name"] = session.get("carName")
                attrs["start_time"] = session.get("startTime")
                attrs["end_time"] = session.get("endTime")
                attrs["provider"] = session.get("provider")
                attrs["location"] = session.get("location")

        if self.entity_description.key == SENSOR_MONTHLY_SESSIONS:
            if self.coordinator.current_month:
                month = self.coordinator.current_month
                attrs["currency"] = month.get("currency", CURRENCY_CZK)

        return attrs if attrs else None
