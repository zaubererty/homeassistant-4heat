"""Provides the 4Heat DataUpdateCoordinator."""

from __future__ import annotations

from datetime import timedelta
import logging
import socket
import time
import asyncio
import threading

from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    DOMAIN,
    SOCKET_BUFFER,
    SOCKET_TIMEOUT,
    TCP_PORT,
    DATA_QUERY,
    ERROR_QUERY,
    RESULT_ERROR,
    CONF_MODE,
    MODES,
    MODE_TYPE,
    ERROR_TYPE,
)

_LOGGER = logging.getLogger(__name__)


class FourHeatDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching 4Heat data."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        config: dict,
        options: dict,
        id: str,
    ):
        """Initialize the 4Heat data coordinator."""
        self._host = config[CONF_HOST]
        self._mode = bool(config.get(CONF_MODE, False))

        # NOTE: legacy name kept on purpose
        self.swiches: list[str] = [MODE_TYPE]

        self.stove_id = id
        self.model = "Basic"
        self.serial_number = "1"

        if not self._mode:
            self._on_cmd = MODES[0][0]
            self._off_cmd = MODES[0][1]
            self._unblock_cmd = MODES[0][2]
            self.swiches.append(ERROR_TYPE)
        else:
            self._on_cmd = MODES[1][0]
            self._off_cmd = MODES[1][1]
            self._unblock_cmd = MODES[1][2]

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=60),
        )

    # ------------------------------------------------------------------
    # Low-level socket helpers (SYNC, executor only)
    # ------------------------------------------------------------------

    def _send_and_receive(self, payload: bytes) -> str:
        """Send raw payload to the stove and return response."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(SOCKET_TIMEOUT)
            sock.connect((self._host, TCP_PORT))
            sock.send(payload)
            return sock.recv(SOCKET_BUFFER).decode()

    def _query_stove(self, payload: bytes) -> list[str]:
        """Query the stove with retry logic."""
        max_retries = 5
        retry_delay = 2

        for attempt in range(1, max_retries + 1):
            try:
                _LOGGER.debug(
                    "4Heat query attempt %s/%s", attempt, max_retries
                )

                response = self._send_and_receive(payload)
                response = (
                    response.replace("[", "")
                    .replace("]", "")
                    .replace('"', "")
                )
                data = response.split(",")

                if data and data[0]:
                    return data

                _LOGGER.warning("Empty response received")

            except Exception as err:
                _LOGGER.error(
                    "Socket error on attempt %s/%s: %s",
                    attempt,
                    max_retries,
                    err,
                )

            if attempt < max_retries:
                # Wait without blocking HA shutdown
                wait_event = threading.Event()
                wait_event.wait(retry_delay)
                retry_delay *= 2

        _LOGGER.error("All retries failed, returning previous data")
        return []

    def _update_data_sync(self) -> dict:
        """Fetch data synchronously from the stove."""
        result = self._query_stove(DATA_QUERY)
        if not result:
            return self.data or {}

        data = self.data or {}

        if result[0] == RESULT_ERROR:
            result = self._query_stove(ERROR_QUERY)

        for entry in result:
            if len(entry) > 3:
                try:
                    data[entry[1:6]] = [int(entry[7:]), entry[0]]
                except ValueError:
                    _LOGGER.error("Failed parsing data entry: %s", entry)

        return data

    # ------------------------------------------------------------------
    # DataUpdateCoordinator API
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> dict:
        """Fetch data from the 4Heat device."""
        for attempt in range(5):
            try:
                return await self.hass.async_add_executor_job(
                    self._update_data_sync
                )
            except Exception as err:
                _LOGGER.warning(
                    "Update attempt %s/5 failed: %s", attempt + 1, err
                )
                await asyncio.sleep(5)

        raise UpdateFailed(
            "Failed to update data from 4Heat after 5 attempts"
        )

    # ------------------------------------------------------------------
    # Command helpers (ASYNC wrappers)
    # ------------------------------------------------------------------

    async def async_turn_on(self) -> bool:
        """Turn stove on."""
        await self.hass.async_add_executor_job(
            self._send_and_receive, self._on_cmd
        )
        _LOGGER.debug("4Heat turned ON")
        return True

    async def async_turn_off(self) -> bool:
        """Turn stove off."""
        await self.hass.async_add_executor_job(
            self._send_and_receive, self._off_cmd
        )
        _LOGGER.debug("4Heat turned OFF")
        return True

    async def async_unblock(self) -> bool:
        """Unblock stove."""
        await self.hass.async_add_executor_job(
            self._send_and_receive, self._unblock_cmd
        )
        _LOGGER.debug("4Heat unblocked")
        return True

    async def async_set_value(self, reading_id: str, value: int) -> bool:
        """Set a numeric value on the stove."""
        val = str(value).zfill(12)
        payload = f'["SEC","1","B{reading_id}{val}"]'.encode()

        _LOGGER.debug("Sending set_value command: %s", payload)

        await self.hass.async_add_executor_job(
            self._send_and_receive, payload
        )
        return True
