"""The 4Heat integration."""

import logging
from homeassistant.const import CONF_MONITORED_CONDITIONS
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    MODE_NAMES, ERROR_NAMES, POWER_NAMES,
    MODE_TYPE, ERROR_TYPE, POWER_TYPE,
    SENSOR_TYPES, DOMAIN, DATA_COORDINATOR,
    ATTR_MARKER, ATTR_NUM_VAL, ATTR_READING_ID, ATTR_STOVE_ID
)
from .coordinator import FourHeatDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Add an FourHeat entry."""
    coordinator: FourHeatDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        DATA_COORDINATOR
    ]
    entities = []
    sensorIds = entry.data[CONF_MONITORED_CONDITIONS]

    for sensorId in sensorIds:
        if len(sensorId) > 5:
            try:
                sId = sensorId[1:6]
                entities.append(FourHeatDevice(coordinator, sId, entry.title))
            except:
                _LOGGER.debug(f"Error adding {sensorId}")

    async_add_entities(entities)


class FourHeatDevice(CoordinatorEntity):
    """Representation of a 4Heat device."""

    def __init__(self, coordinator, sensor_type, name):
        """Initialize the sensor."""
        super().__init__(coordinator)
        if sensor_type not in SENSOR_TYPES:
            _LOGGER.error(f"Sensor '{sensor_type}' unkonwn, notify maintainer.")
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
        _LOGGER.debug(self.coordinator)

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._name} {self._sensor}"

    @property
    def state(self):
        """Return the state of the device."""
        if self.type not in self.coordinator.data: 
            return None
        try:
            if self.type == MODE_TYPE:
                state = MODE_NAMES[self.coordinator.data[self.type][0]]
            elif self.type == ERROR_TYPE:
                state = ERROR_NAMES[self.coordinator.data[self.type][0]]
            elif self.type == POWER_TYPE:
                state = POWER_NAMES[self.coordinator.data[self.type][0]]
            else:
                state = self.coordinator.data[self.type][0]

            self._last_value = state
        except Exception as ex:
            _LOGGER.error(ex)
            state = self._last_value
        return state

    @property
    def maker(self):
        """Maker information"""
        return self.coordinator.data[self.type][1]

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement this sensor expresses itself in."""
        return self._unit_of_measurement

    @property
    def icon(self):
        """Return icon."""
        return self._icon

    @property
    def unique_id(self):
        """Return unique id based on device serial and variable."""
        return f"{self._name}_{self.type}"

    @property
    def device_info(self):
        """Return information about the device."""
        return {
            "identifiers": {(DOMAIN, self.serial_number)},
            "name": self._name,
            "manufacturer": "4Heat",
            "model": self.model,
        }

    @property
    def state_attributes(self):
        try:
            val = {ATTR_MARKER: self.coordinator.data[self.type][1]}
            val[ATTR_READING_ID] = self.type
            val[ATTR_STOVE_ID] = self.coordinator.stove_id

            if self.type == MODE_TYPE or self.type == ERROR_TYPE or self.type == POWER_TYPE:
                val[ATTR_NUM_VAL] = self.coordinator.data[self.type][0]
                
            return val

        except Exception as ex:
            _LOGGER.error(ex)
            return None