"""Provides the MYPV DataUpdateCoordinator."""
from datetime import timedelta
import logging
import socket

from async_timeout import timeout
from homeassistant.util.dt import utcnow
from homeassistant.const import CONF_HOST
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN, SOCKET_BUFFER, SOCKET_TIMEOUT, TCP_PORT, DATA_QUERY, ERROR_QUERY, 
    ON_CMD, OFF_CMD, UNBLOCK_CMD, RESULT_VALS, RESULT_ERROR
)

_LOGGER = logging.getLogger(__name__)


class FourHeatDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching 4heat data."""

    def __init__(self, hass: HomeAssistantType, *, config: dict, options: dict):
        """Initialize global 4heat data updater."""
        self._host = config[CONF_HOST]
        self._next_update = 0
        self.model = "Basic"
        self.serial_number = "1"
        update_interval = timedelta(seconds=60)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> dict:
        """Fetch data from 4heat."""
        def _query_stove(query) -> list[str]:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(SOCKET_TIMEOUT)
                s.connect((self._host, TCP_PORT))
                s.send(query)
                result = s.recv(SOCKET_BUFFER).decode()
                s.close()
                result = result.replace("[","")
                result = result.replace("]","")
                result = result.replace('"',"")
                d = result.split(",")
            except Exception as error:
                _LOGGER.error(f"Update error: {error}")
                self._next_update = 5
                d = []
            return d

        def _update_data() -> dict:
            """Fetch data from 4heat via sync functions."""
            list = _query_stove(DATA_QUERY)
            dict = self.data
            if dict == None:
                dict = {}
            
            if list[0] == RESULT_ERROR:
                list = _query_stove(ERROR_QUERY)
                 
            for data in list:
                if len(data) > 3:
                    dict[data[1:6]] = int(data[7:])
            return dict

        try:
            async with timeout(10):
                return await self.hass.async_add_executor_job(_update_data)
        except Exception as error:
            raise UpdateFailed(f"Invalid response from API: {error}") from error

    async def async_turn_on(self) -> bool:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(SOCKET_TIMEOUT)
            s.connect((self._host, TCP_PORT))
            s.send(ON_CMD)
            s.recv(SOCKET_BUFFER).decode()
            s.close()
            _LOGGER.debug("Toggle ON")
        except Exception as ex:
            _LOGGER.error(ex)

    async def async_turn_off(self) -> bool:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(SOCKET_TIMEOUT)
            s.connect((self._host, TCP_PORT))
            s.send(OFF_CMD)
            s.recv(SOCKET_BUFFER).decode()
            s.close()
            _LOGGER.debug("Toggle OFF")
        except Exception as ex:
            _LOGGER.error(ex)

    async def async_unblock(self) -> bool:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(SOCKET_TIMEOUT)
            s.connect((self._host, TCP_PORT))
            s.send(UNBLOCK_CMD)
            s.recv(SOCKET_BUFFER).decode()
            s.close()
            _LOGGER.debug("Toggle Unblock")
        except Exception as ex:
            _LOGGER.error(ex)

