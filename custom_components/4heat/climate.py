"""Climate entity for the 4heat stove: room setpoint (J30138) and ON/OFF."""
import logging

from homeassistant.components.climate import (
    ClimateEntity, ClimateEntityFeature, HVACAction, HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, DATA_COORDINATOR, MODE_TYPE, MODE_NAMES, ROOM_TEMP_ID

_LOGGER = logging.getLogger(__name__)

OFF_STATES = (None, 0, 8, 9)       # OFF, Safety, Block
IDLE_STATES = (7, 11)              # Extinguishing, Standby


async def async_setup_entry(hass, entry, async_add_entities):
    """Add the thermostat only if the stove reports a room setpoint."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    if not coordinator.data or coordinator.setpoint_id not in coordinator.data:
        _LOGGER.debug("4heat: no room setpoint (J%s) reported, no thermostat", coordinator.setpoint_id)
        return
    async_add_entities([FourHeatClimate(coordinator, entry.title)])


class FourHeatClimate(CoordinatorEntity, ClimateEntity):
    """Stove thermostat."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_min_temp = 15
    _attr_max_temp = 28
    _attr_target_temperature_step = 1
    _attr_icon = "mdi:fireplace"
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(self, coordinator, name):
        super().__init__(coordinator)
        self._attr_name = f"{name} thermostat"
        self._attr_unique_id = f"{coordinator.stove_id}_climate"

    @property
    def available(self):
        return bool(self.coordinator.last_update_success and self.coordinator.data)

    def _v(self, key):
        data = self.coordinator.data or {}
        return data[key][0] if key and key in data else None

    @property
    def current_temperature(self):
        return self._v(ROOM_TEMP_ID)

    @property
    def target_temperature(self):
        return self._v(self.coordinator.setpoint_id)

    @property
    def hvac_mode(self):
        return HVACMode.OFF if self._v(MODE_TYPE) in OFF_STATES else HVACMode.HEAT

    @property
    def hvac_action(self):
        mode = self._v(MODE_TYPE)
        if mode in OFF_STATES:
            return HVACAction.OFF
        if mode in IDLE_STATES:
            return HVACAction.IDLE
        return HVACAction.HEATING

    @property
    def extra_state_attributes(self):
        c = self.coordinator
        mode = self._v(MODE_TYPE)
        return {
            "stove_state": MODE_NAMES.get(mode, mode),
            "setpoint_parameter": f"J{c.setpoint_id}",
            "last_write": c.last_write,
            "last_answer": c.last_ok.isoformat() if c.last_ok else None,
            "missed_polls": c.failures,
            "room_probe": (
                f"lost since {c.probe_lost_since.strftime('%H:%M')}"
                if c.probe_lost and c.probe_lost_since else "ok"
            ),
        }

    async def async_set_temperature(self, **kwargs):
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is not None:
            await self.coordinator.async_set_setpoint(temp)

    async def async_set_hvac_mode(self, hvac_mode):
        if hvac_mode == HVACMode.HEAT:
            await self.coordinator.async_turn_on()
        else:
            await self.coordinator.async_turn_off()

    async def async_turn_on(self):
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self):
        await self.async_set_hvac_mode(HVACMode.OFF)
