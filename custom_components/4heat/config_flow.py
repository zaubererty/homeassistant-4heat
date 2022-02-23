"""Config flow for Kostal piko integration."""
# import logging

import voluptuous as vol
import socket
from requests.exceptions import HTTPError, ConnectTimeout

from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv

from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_MONITORED_CONDITIONS,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import slugify

from .const import (
    DOMAIN,
    SENSOR_TYPES, 
    DATA_QUERY,
    SOCKET_BUFFER, 
    SOCKET_TIMEOUT,
    TCP_PORT,
    CONF_MODE,
    CMD_MODE_OPTIONS
)  

SUPPORTED_SENSOR_TYPES = list(SENSOR_TYPES)

DEFAULT_MONITORED_CONDITIONS = [
    "30001",
]


@callback
def four_heat_entries(hass: HomeAssistant):
    """Return the hosts for the domain."""
    return set(
        (entry.data[CONF_HOST]) for entry in hass.config_entries.async_entries(DOMAIN)
    )


class FourHeatConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """4Heat config flow."""

    VERSION = 1

    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    conditions=[]

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._errors = {}
        self._info = {}

    def _host_in_configuration_exists(self, host) -> bool:
        """Return True if site_id exists in configuration."""
        if host in four_heat_entries(self.hass):
            return True
        return False

    def _check_host(self, host) -> bool:
        """Check if we can connect to the FourHeat."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(SOCKET_TIMEOUT)
            s.connect((host, TCP_PORT))
            s.send(DATA_QUERY)
            result= s.recv(SOCKET_BUFFER).decode()
            s.close()
            result = result.replace("]","")
            result = result.replace('"',"")
            self.conditions = result.split(",")
            if len(self.conditions) > 3:
                return True
        except (ConnectTimeout, HTTPError):
            self._errors[CONF_HOST] = "could_not_connect"
            return False

        return True

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""

        if user_input is not None:
            if self._host_in_configuration_exists(user_input[CONF_HOST]):
                self._errors[CONF_HOST] = "host_exists"
            else:
                name = user_input[CONF_NAME]
                host = user_input[CONF_HOST]
                legacy_cmd = user_input[CONF_MODE]
                can_connect = await self.hass.async_add_executor_job(
                    self._check_host, host
                )
                if can_connect:
                    return self.async_create_entry(
                        title=f"{name}",
                        data={
                            CONF_HOST: host,
                            CONF_MODE: legacy_cmd,
                            CONF_MONITORED_CONDITIONS: self.conditions,
                        },
                    )
        else:
            user_input = {}
            user_input[CONF_NAME] = "Stove"
            user_input[CONF_HOST] = "192.168.0.0"
            user_input[CONF_MODE] = False

        default_monitored_conditions = (
            self.conditions if len(self.conditions) == 0 else DEFAULT_MONITORED_CONDITIONS
        )

        setup_schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=user_input[CONF_NAME]): str,
                vol.Required(CONF_HOST, default=user_input[CONF_HOST]): str,
                vol.Optional(
                    CONF_MODE, default=user_input[CONF_MODE],
                    description='mode'
                ): bool,
                vol.Optional(
                    CONF_MONITORED_CONDITIONS, default=default_monitored_conditions
                ): cv.multi_select(self.conditions),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=setup_schema, errors=self._errors
        )

    async def async_step_import(self, user_input=None):
        """Import a config entry."""
        if self._host_in_configuration_exists(user_input[CONF_HOST]):
            return self.async_abort(reason="host_exists")
        return await self.async_step_user(user_input)