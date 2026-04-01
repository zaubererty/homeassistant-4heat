"""Config flow for the 4Heat integration."""

from __future__ import annotations

import socket
import logging
import voluptuous as vol

from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_MONITORED_CONDITIONS,
)
from homeassistant.core import HomeAssistant, callback

from .const import (
    DOMAIN,
    SENSOR_TYPES,
    DATA_QUERY,
    SOCKET_BUFFER,
    SOCKET_TIMEOUT,
    TCP_PORT,
    CONF_MODE,
    CMD_MODE_OPTIONS,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_MONITORED_CONDITIONS = ["30001"]


@callback
def _configured_hosts(hass: HomeAssistant) -> set[str]:
    """Return a set of configured hosts."""
    return {
        entry.data[CONF_HOST]
        for entry in hass.config_entries.async_entries(DOMAIN)
        if CONF_HOST in entry.data
    }


class FourHeatConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for 4Heat."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._errors: dict[str, str] = {}
        self._conditions: list[str] = []

    # ------------------------------------------------------------------
    # Connection test (SYNC, executed in executor)
    # ------------------------------------------------------------------

    def _check_host(self, host: str) -> bool:
        """Check if we can connect to the 4Heat device."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(SOCKET_TIMEOUT)
                sock.connect((host, TCP_PORT))
                sock.send(DATA_QUERY)
                result = sock.recv(SOCKET_BUFFER).decode()

            result = (
                result.replace("[", "")
                .replace("]", "")
                .replace('"', "")
            )

            self._conditions = result.split(",")

            return len(self._conditions) > 3

        except OSError as err:
            _LOGGER.error("Connection check failed for %s: %s", host, err)
            self._errors[CONF_HOST] = "cannot_connect"
            return False

    # ------------------------------------------------------------------
    # User step
    # ------------------------------------------------------------------

    async def async_step_user(self, user_input: dict | None = None):
        """Handle the initial step."""
        self._errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            name = user_input[CONF_NAME]
            legacy_mode = user_input.get(CONF_MODE, False)

            if host in _configured_hosts(self.hass):
                self._errors[CONF_HOST] = "host_exists"
            else:
                can_connect = await self.hass.async_add_executor_job(
                    self._check_host, host
                )

                if can_connect:
                    # Unique ID = host (local device)
                    await self.async_set_unique_id(host)
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=name,
                        data={
                            CONF_HOST: host,
                            CONF_MODE: legacy_mode,
                            CONF_MONITORED_CONDITIONS: self._conditions,
                        },
                    )

        # Defaults for first load or retry
        defaults = {
            CONF_NAME: "Stove",
            CONF_HOST: "192.168.0.100",
            CONF_MODE: False,
        }

        monitored_conditions = (
            self._conditions
            if self._conditions
            else DEFAULT_MONITORED_CONDITIONS
        )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_NAME, default=user_input.get(CONF_NAME, defaults[CONF_NAME])
                    if user_input else defaults[CONF_NAME]
                ): str,
                vol.Required(
                    CONF_HOST, default=user_input.get(CONF_HOST, defaults[CONF_HOST])
                    if user_input else defaults[CONF_HOST]
                ): str,
                vol.Optional(
                    CONF_MODE,
                    default=user_input.get(CONF_MODE, defaults[CONF_MODE])
                    if user_input else defaults[CONF_MODE],
                ): bool,
                vol.Optional(
                    CONF_MONITORED_CONDITIONS,
                    default=monitored_conditions,
                ): cv.multi_select(SENSOR_TYPES),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=self._errors,
        )

    # ------------------------------------------------------------------
    # Import step (kept for safety, even if YAML is removed)
    # ------------------------------------------------------------------

    async def async_step_import(self, user_input: dict):
        """Handle import from configuration.yaml."""
        return await self.async_step_user(user_input)
