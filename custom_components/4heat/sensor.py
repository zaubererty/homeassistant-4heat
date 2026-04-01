"""The 4Heat integration."""

import logging

from homeassistant.const import CONF_MONITORED_CONDITIONS
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    MODE_NAMES,
    ERROR_NAMES,
    POWER_NAMES,
    MODE_TYPE,
    ERROR_TYPE,
    POWER_TYPE,
    SENSOR_TYPES,
    DOMAIN,
    DATA_COORDINATOR,
    ATTR_MARKER,
    ATTR_NUM_VAL,
    ATTR_READING_ID,
    ATTR_STOVE_ID,
)
from .coordinator import FourHeatDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Add a 4Heat entry."""
    coordinator: FourHeatDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        DATA_COORDINATOR
    ]

    entities = []
    sensor_ids = entry.data.get(CONF_MONITORED_CONDITIONS, [])

    for sensor_id in sensor_ids:
        if len(sensor_id) > 5:
            try:
                s_id = sensor_id[1:6]
                entities.append(
                    FourHeatDevice(
                        coordinator=coordinator,
                        sensor_type=s_id,
                        name=entry.title,
                    )
                )
            except Exception as exc:
                _LOGGER.debug("Error adding sensor %s: %s", sensor_id, exc)

    async_add_entities(entities)


class FourHeatDevice(CoordinatorEntity, SensorEntity):
    """Representation of a 4Heat sensor."""

    has_entity_name = True

    def __init__(self, coordinator, sensor_type, name):
        """Initialize the sensor."""
        super().__init__(coordinator)

        if sensor_type not in SENSOR_TYPES:
            _LOGGER.error(
                "Sensor '%s' unknown, notify maintainer.", sensor_type
            )
            SENSOR_TYPES[sensor_type] = [f"UN {sensor_type}", None, ""]

        self._sensor = SENSOR_TYPES[sensor_type][0]
        self._name = name
        self.type = sensor_type
        self.coordinator = coordinator
        self._last_value = None

        self.serial_number = coordinator.serial_number
        self.model = coordinator.model

        self._unit_of_measurement = SENSOR_TYPES[self.type][1]
        self._icon = SENSOR_TYPES[self.type][2]

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._name} {self._sensor}"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.type not in self.coordinator.data:
            return self._last_value

        try:
            raw_value = self.coordinator.data[self.type][0]

            if raw_value is None:
                _LOGGER.warning(
                    "Null value for sensor %s, keeping last value", self.name
                )
                return self._last_value

            if isinstance(raw_value, (int, float)) and raw_value < 0:
                _LOGGER.warning(
                    "Negative value for %s: %s, keeping last value",
                    self.name,
                    raw_value,
                )
                return self._last_value

            if self.type == MODE_TYPE:
                value = MODE_NAMES.get(
                    raw_value, f"Unknown_Mode_Name: {raw_value}"
                )
            elif self.type == ERROR_TYPE:
                value = ERROR_NAMES.get(
                    raw_value, f"Unknown_Error_Name: {raw_value}"
                )
            elif self.type == POWER_TYPE:
                value = POWER_NAMES.get(
                    raw_value, f"Unknown_Power_Name: {raw_value}"
                )
            else:
                value = raw_value

            self._last_value = value
            return value

        except Exception as exc:
            _LOGGER.error(
                "Error reading state for %s: %s", self.name, exc
            )
            return self._last_value

    # Legacy compatibility
    @property
    def state(self):
        """Return the state (legacy)."""
        return self.native_value

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

    @property
    def icon(self):
        """Return icon."""
        return self._icon

    @property
    def unique_id(self):
        """Return a stable unique id."""
        return f"{self.serial_number}_{self.type}"

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self.serial_number)},
            "name": self._name,
            "manufacturer": "4Heat",
            "model": self.model,
        }

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        try:
            val = {
                ATTR_MARKER: self.coordinator.data[self.type][1],
                ATTR_READING_ID: self.type,
                ATTR_STOVE_ID: self.coordinator.stove_id,
            }

            if self.type in (MODE_TYPE, ERROR_TYPE, POWER_TYPE):
                val[ATTR_NUM_VAL] = self.coordinator.data[self.type][0]

            return val

        except Exception as exc:
            _LOGGER.error(exc)
            return {}
