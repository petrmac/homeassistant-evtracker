"""Binary sensor platform for EV Tracker integration."""

from __future__ import annotations

from datetime import datetime, time
import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_change
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
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
from .coordinator import EVTrackerDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


BINARY_SENSOR_DESCRIPTIONS: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(
        key=BINARY_SENSOR_CONNECTED,
        translation_key=BINARY_SENSOR_CONNECTED,
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up EV Tracker binary sensor entities."""
    coordinator: EVTrackerDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities: list[BinarySensorEntity] = [
        EVTrackerBinarySensor(coordinator, description)
        for description in BINARY_SENSOR_DESCRIPTIONS
    ]

    # Add tariff sensor if configured
    tariff_source = config_entry.options.get(CONF_TARIFF_SOURCE)
    if tariff_source in (TARIFF_SOURCE_SCHEDULE, TARIFF_SOURCE_ENTITY):
        entities.append(EVTrackerLowTariffSensor(hass, coordinator, config_entry))

    async_add_entities(entities)


class EVTrackerBinarySensor(CoordinatorEntity[EVTrackerDataUpdateCoordinator], BinarySensorEntity):
    """Representation of an EV Tracker binary sensor."""

    entity_description: BinarySensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EVTrackerDataUpdateCoordinator,
        description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
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
    def is_on(self) -> bool:
        """Return true if the API is connected."""
        return self.coordinator.is_connected and self.coordinator.last_update_success


class EVTrackerLowTariffSensor(BinarySensorEntity):
    """Binary sensor for low tariff status."""

    _attr_has_entity_name = True
    _attr_translation_key = BINARY_SENSOR_LOW_TARIFF
    _attr_device_class = BinarySensorDeviceClass.POWER

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: EVTrackerDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the low tariff sensor."""
        self.hass = hass
        self.coordinator = coordinator
        self.config_entry = config_entry
        self._attr_unique_id = f"{coordinator.car_id}_{BINARY_SENSOR_LOW_TARIFF}"
        self._is_on: bool = False
        self._unsubscribe_callbacks: list = []

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
    def is_on(self) -> bool:
        """Return true if currently in low tariff period."""
        return self._is_on

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        options = self.config_entry.options
        tariff_source = options.get(CONF_TARIFF_SOURCE)

        attrs = {"tariff_source": tariff_source}

        if tariff_source == TARIFF_SOURCE_SCHEDULE:
            window_type = options.get(CONF_TARIFF_WINDOW_TYPE, WINDOW_TYPE_LOW)
            attrs["window_type"] = window_type
            attrs["window_1_start"] = options.get(CONF_TARIFF_LOW_START_1)
            attrs["window_1_end"] = options.get(CONF_TARIFF_LOW_END_1)
            if options.get(CONF_TARIFF_LOW_START_2):
                attrs["window_2_start"] = options.get(CONF_TARIFF_LOW_START_2)
                attrs["window_2_end"] = options.get(CONF_TARIFF_LOW_END_2)
            if options.get(CONF_TARIFF_LOW_START_3):
                attrs["window_3_start"] = options.get(CONF_TARIFF_LOW_START_3)
                attrs["window_3_end"] = options.get(CONF_TARIFF_LOW_END_3)
            if options.get(CONF_TARIFF_LOW_START_4):
                attrs["window_4_start"] = options.get(CONF_TARIFF_LOW_START_4)
                attrs["window_4_end"] = options.get(CONF_TARIFF_LOW_END_4)
            attrs["weekend_always_low"] = options.get(CONF_TARIFF_WEEKEND_LOW, False)
        elif tariff_source == TARIFF_SOURCE_ENTITY:
            attrs["source_entity"] = options.get(CONF_TARIFF_ENTITY)

        return attrs

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()

        tariff_source = self.config_entry.options.get(CONF_TARIFF_SOURCE)

        if tariff_source == TARIFF_SOURCE_SCHEDULE:
            # Update immediately
            self._update_schedule_state()

            # Track time changes every minute
            self._unsubscribe_callbacks.append(
                async_track_time_change(
                    self.hass,
                    self._handle_time_change,
                    second=0,
                )
            )
        elif tariff_source == TARIFF_SOURCE_ENTITY:
            entity_id = self.config_entry.options.get(CONF_TARIFF_ENTITY)
            if entity_id:
                # Update immediately
                self._update_entity_state()

                # Track entity state changes
                self._unsubscribe_callbacks.append(
                    async_track_state_change_event(
                        self.hass,
                        [entity_id],
                        self._handle_entity_change,
                    )
                )

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        for unsubscribe in self._unsubscribe_callbacks:
            unsubscribe()
        self._unsubscribe_callbacks.clear()

    @callback
    def _handle_time_change(self, now: datetime) -> None:
        """Handle time change for schedule-based tariff."""
        self._update_schedule_state()
        self.async_write_ha_state()

    @callback
    def _handle_entity_change(self, event) -> None:
        """Handle entity state change for entity-based tariff."""
        self._update_entity_state()
        self.async_write_ha_state()

    def _update_schedule_state(self) -> None:
        """Update state based on schedule configuration."""
        options = self.config_entry.options
        now = datetime.now()

        # Check weekend setting - always LOW on weekends if enabled
        if options.get(CONF_TARIFF_WEEKEND_LOW, False):
            # Weekend is Saturday (5) and Sunday (6)
            if now.weekday() >= 5:
                self._is_on = True
                return

        # Get window type - determines how to interpret the windows
        window_type = options.get(CONF_TARIFF_WINDOW_TYPE, WINDOW_TYPE_LOW)

        # Check if current time is in any configured window
        current_time = now.time()
        in_window = False

        # Check all 4 windows
        windows = [
            (options.get(CONF_TARIFF_LOW_START_1), options.get(CONF_TARIFF_LOW_END_1)),
            (options.get(CONF_TARIFF_LOW_START_2), options.get(CONF_TARIFF_LOW_END_2)),
            (options.get(CONF_TARIFF_LOW_START_3), options.get(CONF_TARIFF_LOW_END_3)),
            (options.get(CONF_TARIFF_LOW_START_4), options.get(CONF_TARIFF_LOW_END_4)),
        ]

        for start, end in windows:
            if start and end:
                if self._is_time_in_window(current_time, start, end):
                    in_window = True
                    break

        # Determine if LOW tariff based on window type:
        # - WINDOW_TYPE_LOW: windows define LOW periods, so in_window = LOW (is_on = True)
        # - WINDOW_TYPE_HIGH: windows define HIGH periods, so in_window = HIGH (is_on = False)
        if window_type == WINDOW_TYPE_HIGH:
            # Windows define HIGH tariff, so outside windows = LOW
            self._is_on = not in_window
        else:
            # Windows define LOW tariff (default)
            self._is_on = in_window

    def _is_time_in_window(self, current: time, start_str: str, end_str: str) -> bool:
        """Check if current time is within a time window."""
        try:
            start = time.fromisoformat(start_str)
            end = time.fromisoformat(end_str)

            # Handle overnight windows (e.g., 22:00 - 06:00)
            if start <= end:
                # Normal window (e.g., 08:00 - 12:00)
                return start <= current <= end
            else:
                # Overnight window (e.g., 22:00 - 06:00)
                return current >= start or current <= end
        except ValueError:
            _LOGGER.error("Invalid time format: start=%s, end=%s", start_str, end_str)
            return False

    def _update_entity_state(self) -> None:
        """Update state based on external entity."""
        entity_id = self.config_entry.options.get(CONF_TARIFF_ENTITY)
        if not entity_id:
            self._is_on = False
            return

        state = self.hass.states.get(entity_id)
        if state is None:
            self._is_on = False
            return

        # Consider "on", "true", "1", "low" as low tariff
        state_value = state.state.lower()
        self._is_on = state_value in ("on", "true", "1", "low", "yes")
