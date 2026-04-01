"""Integration for 4Heat."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, valid_entity_id

from .const import (
    DOMAIN,
    PLATFORMS,
    DATA_COORDINATOR,
    ATTR_MARKER,
    ATTR_READING_ID,
    ATTR_STOVE_ID,
)
from .coordinator import FourHeatDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the 4Heat integration."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up 4Heat from a config entry."""
    coordinator = FourHeatDataUpdateCoordinator(
        hass,
        config=entry.data,
        options=entry.options,
        id=entry.entry_id,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        DATA_COORDINATOR: coordinator,
    }

    # --------------------------------------------------------------
    # Service: set_value (register once)
    # --------------------------------------------------------------

    if not hass.services.has_service(DOMAIN, "set_value"):

        async def async_handle_set_value(call):
            """Handle the service call to set a value."""
            entity_id = call.data.get("entity_id", "")
            value = call.data.get("value", 5)

            if isinstance(value, str):
                if value.isnumeric():
                    val = int(value)
                elif valid_entity_id(value):
                    state = hass.states.get(value)
                    val = int(float(state.state)) if state else 0
                else:
                    val = 0
            else:
                val = value

            if not valid_entity_id(entity_id):
                _LOGGER.error('"%s" is not a valid entity ID', entity_id)
                return

            entity = hass.states.get(entity_id)
            if not entity:
                _LOGGER.error('Entity "%s" not found', entity_id)
                return

            if entity.attributes.get(ATTR_MARKER) != "B":
                _LOGGER.error('"%s" is not valid to be set', entity_id)
                return

            stove_id = entity.attributes.get(ATTR_STOVE_ID)
            reading_id = entity.attributes.get(ATTR_READING_ID)

            if stove_id not in hass.data.get(DOMAIN, {}):
                _LOGGER.error("Stove %s not found", stove_id)
                return

            coord = hass.data[DOMAIN][stove_id][DATA_COORDINATOR]
            await coord.async_set_value(reading_id, val)
            await coord.async_request_refresh()

        hass.services.async_register(
            DOMAIN,
            "set_value",
            async_handle_set_value,
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    )

    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)

    return unload_ok
