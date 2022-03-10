""" Integration for 4heat"""
import voluptuous as vol
import logging

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.core import valid_entity_id
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_MONITORED_CONDITIONS,
)
import homeassistant.helpers.config_validation as cv

from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.typing import HomeAssistantType

from .const import ATTR_MARKER, ATTR_READING_ID, ATTR_STOVE_ID, DOMAIN, DATA_COORDINATOR, CONF_MODE
from .coordinator import FourHeatDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_NAME): cv.string,
                vol.Required(CONF_HOST): cv.string,
                vol.Optional(CONF_MODE, default=False): cv.boolean,
                vol.Optional(CONF_MONITORED_CONDITIONS): cv.ensure_list,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass, config):
    """Platform setup, do nothing."""
    hass.data.setdefault(DOMAIN, {})

    if DOMAIN not in config:
        return True

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_IMPORT}, data=dict(config[DOMAIN])
        )
    )
    return True



async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry):
    """Load the saved entities."""
    coordinator = FourHeatDataUpdateCoordinator(
        hass,
        config=entry.data,
        options=entry.options,
        id=entry.entry_id,
    )

    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data[DOMAIN][entry.entry_id] = {
        DATA_COORDINATOR: coordinator,
    }


    async def async_handle_set_value(call):
        """Handle the service call to set a value."""
        entity_id = call.data.get('entity_id', '')
        value = call.data.get('value', 5)        
        val = 1
        if isinstance(value, str):
            if value.isnumeric():
                val = int(value)
            elif valid_entity_id(value):
                val = int(float(hass.states.get(value).state))
        else:
            val = value

        if valid_entity_id(entity_id):
            e_id = hass.states.get(entity_id)
            if e_id.attributes[ATTR_MARKER] == 'B':
                c = hass.data[DOMAIN][e_id.attributes[ATTR_STOVE_ID]][DATA_COORDINATOR]
                await c.async_set_value(e_id.attributes[ATTR_READING_ID], val)
                await c.async_request_refresh()
            else:
                _LOGGER.error(f'"{entity_id}" is not valid to be set')
        else:
            _LOGGER.error(f'"{entity_id}" is no valid entity ID')

    
    hass.services.async_register(DOMAIN, "set_value", async_handle_set_value)

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "switch")
    )
    return True
