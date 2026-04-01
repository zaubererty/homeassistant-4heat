"""The 4Heat integration."""

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    MODE_NAMES,
    SENSOR_TYPES,
    DOMAIN,
    DATA_COORDINATOR,
    MODE_TYPE,
    ERROR_TYPE,
)
from .coordinator import FourHeatDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Add a 4Heat entry."""
    coordinator: FourHeatDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        DATA_COORDINATOR
    ]

    entities = []

    for sensor_id in coordinator.swiches:
        try:
            entities.append(
                FourHeatSwitch(
                    coordinator=coordinator,
                    sensor_type=sensor_id,
                    name=entry.title,
                )
            )
        except Exception as exc:
            _LOGGER.debug("Error adding switch %s: %s", sensor_id, exc)

    async_add_entities(entities)


class FourHeatSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a 4Heat switch."""

    has_entity_name = True

    def __init__(self, coordinator, sensor_type, name):
        """Initialize the switch."""
        super().__init__(coordinator)

        self._sensor = SENSOR_TYPES[sensor_type][0]
        self._name = name
        self.type = sensor_type
        self.coordinator = coordinator
        self._last_value = None

        self.serial_number = coordinator.serial_number
        self.model = coordinator.model

    @property
    def name(self):
        """Return the name of the switch."""
        return f"{self._name} {self._sensor}"

    @property
    def is_on(self):
        """Return true if switch is on."""
        if self.type not in self.coordinator.data:
            return False

        if self.type == MODE_TYPE:
            return self.coordinator.data[self.type][0] not in (0, 7, 8, 9)

        if self.type == ERROR_TYPE:
            return self.coordinator.data[self.type][0] != 0

        return False

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        if self.type == MODE_TYPE:
            await self.coordinator.async_turn_on()
        elif self.type == ERROR_TYPE:
            pass

        await self.coordinator.async_request_refresh()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        if self.type == MODE_TYPE:
            await self.coordinator.async_turn_off()
        elif self.type == ERROR_TYPE:
            await self.coordinator.async_unblock()

        await self.coordinator.async_request_refresh()
        self.async_write_ha_state()

    @property
    def unique_id(self):
        """Return a stable unique id."""
        return f"{self.serial_number}_{self.type}"

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
    def extra_state_attributes(self):
        """Return extra state attributes."""
        try:
            if self.type == MODE_TYPE:
                return {
                    "Num Val": self.coordinator.data[self.type][0],
                    "Val text": MODE_NAMES.get(
                        self.coordinator.data[self.type][0],
                        "Unknown",
                    ),
                }

            if self.type == ERROR_TYPE:
                return {
                    "Num Val": self.coordinator.data[self.type][0],
                }

            return {}

        except Exception as exc:
            _LOGGER.error(exc)
            return {}
