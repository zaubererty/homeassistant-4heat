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
            return None  # Evita di inviare valori non validi

        try:
            raw_value = self.coordinator.data[self.type][0]  # Ottiene il valore grezzo

            # Controlla se il valore è None o non valido
            if raw_value is None:
                _LOGGER.warning(f"Valore nullo per il sensore {self.name}, non inviato.")
                return self._last_value  # Mantiene l'ultimo valore valido

            if isinstance(raw_value, (int, float)) and raw_value < 0:  # Aggiungi altri controlli se necessario
                _LOGGER.warning(f"Valore negativo per {self.name}: {raw_value}, non inviato.")
                return self._last_value

            # Mappa il valore grezzo nei nomi, se necessario
            if self.type == MODE_TYPE:
                state = MODE_NAMES.get(raw_value, "Unknown_Mode_Name: " + str(raw_value))
            elif self.type == ERROR_TYPE:
                state = ERROR_NAMES.get(raw_value, "Unknown_Error_Name: " + str(raw_value))
            elif self.type == POWER_TYPE:
                state = POWER_NAMES.get(raw_value, "Unknown_Power_Name: " + str(raw_value))
            else:
                state = raw_value

            self._last_value = state  # Aggiorna solo se valido
            return state

        except Exception as ex:
            _LOGGER.error(f"Errore durante la lettura dello stato di {self.name}: {ex}")
            return self._last_value  # Evita di inviare dati errati



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