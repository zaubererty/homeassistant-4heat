"""DataUpdateCoordinator for the 4heat Wi-Fi module.

Notes on the module (tested on a Fogo Montanha Square D pellet insert):
- the module's local server saturates easily: only one TCP exchange is made at a
  time (shared lock between polling and commands), polling runs every 120 s and
  backs off to 5 min after a failure;
- every socket call runs in the executor (no blocking I/O in the event loop);
- the room setpoint is reported as J30138 and can be written with the same frame
  shape as the ON/OFF commands: ["SEC","1","J30138000000000020"] -> 20 °C;
- when the stove loses its wireless room probe it falls back to its internal probe
  and reports wrong values (e.g. room 29 °C, setpoint 38 °C). This is detected on
  the setpoint (out of range, or a jump without a write from HA) and the last
  trusted setpoint / room values are kept until the probe is back.
"""
import asyncio
from datetime import timedelta
import logging
import socket

from async_timeout import timeout
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN, SOCKET_BUFFER, SOCKET_TIMEOUT, TCP_PORT, DATA_QUERY, ERROR_QUERY,
    RESULT_ERROR, CONF_MODE, MODES, MODE_TYPE, ERROR_TYPE,
    SETPOINT_ID, ROOM_TEMP_ID,
)

_LOGGER = logging.getLogger(__name__)

POLL_INTERVAL = timedelta(seconds=120)
BACKOFF_INTERVAL = timedelta(minutes=5)
FAILURES_BEFORE_UNAVAILABLE = 3      # keep last data for a couple of missed polls
CONFIRM_DELAY = 25                   # s, re-read after a command
SETPOINT_RANGE = (5, 30)             # °C, outside = internal probe fallback
SETPOINT_JUMP = 5                    # °C, jump without a write = probe lost


class FourHeatDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching 4heat data."""

    def __init__(self, hass: HomeAssistant, *, config: dict, options: dict, id: str):
        """Initialize global 4heat data updater."""
        self._host = config[CONF_HOST]
        self._mode = False
        self._lock = asyncio.Lock()
        self._confirm_unsub = None
        self.swiches = [MODE_TYPE]
        self.stove_id = id

        if CONF_MODE in config:
            self._mode = config[CONF_MODE]

        if self._mode == False:
            self._on_cmd = MODES[0][0]
            self._off_cmd = MODES[0][1]
            self._unblock_cmd = MODES[0][2]
            self.swiches.append(ERROR_TYPE)
        else:
            self._on_cmd = MODES[1][0]
            self._off_cmd = MODES[1][1]
            self._unblock_cmd = MODES[1][2]

        self.model = "Basic"
        self.serial_number = "1"
        self.last_successful_data = None
        self.failures = 0
        self.last_ok = None
        self.last_write = None
        self.setpoint_id = SETPOINT_ID
        self.probe_lost = False
        self.probe_lost_since = None
        self._trusted = {}

        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=POLL_INTERVAL)

    # ------------------------------------------------------------------ network
    def _exchange(self, payload: bytes) -> str:
        """One TCP request/response with the module (runs in the executor)."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(SOCKET_TIMEOUT)
        try:
            s.connect((self._host, TCP_PORT))
            s.send(payload)
            return s.recv(SOCKET_BUFFER).decode()
        finally:
            try:
                s.close()
            except OSError:
                pass

    async def _send(self, payload: bytes, label: str) -> bool:
        """Send a command, serialized with polling."""
        if payload is None:
            return False
        async with self._lock:
            try:
                async with timeout(SOCKET_TIMEOUT + 5):
                    answer = await self.hass.async_add_executor_job(self._exchange, payload)
                _LOGGER.debug("4heat %s -> %s", label, answer)
                return True
            except Exception as ex:  # noqa: BLE001
                _LOGGER.error("4heat: %s failed: %s", label, ex)
                return False

    @staticmethod
    def _parse(raw: str) -> list:
        return raw.replace("[", "").replace("]", "").replace('"', "").split(",")

    # ------------------------------------------------------------------ polling
    async def _async_update_data(self) -> dict:
        """Fetch data from 4heat."""

        def _update_data() -> dict:
            items = self._parse(self._exchange(DATA_QUERY))
            if not items or items[0] == "":
                raise UpdateFailed("Empty answer from the 4heat module")
            if items[0] == RESULT_ERROR:
                items = self._parse(self._exchange(ERROR_QUERY))
            data = dict(self.data or {})
            for item in items:
                if len(item) > 3:
                    try:
                        data[item[1:6]] = [int(item[7:]), item[0]]
                    except ValueError:
                        _LOGGER.debug("4heat: cannot parse %s", item)
            return data

        if self._lock.locked():
            # A command is being sent: do not open a second connection.
            if self.last_successful_data is None:
                raise UpdateFailed("4heat exchange already in progress")
            return self.last_successful_data

        try:
            async with self._lock:
                async with timeout(SOCKET_TIMEOUT + 5):
                    data = await self.hass.async_add_executor_job(_update_data)
        except Exception as err:  # noqa: BLE001
            self.update_interval = BACKOFF_INTERVAL
            self.failures += 1
            if self.last_successful_data is None or self.failures >= FAILURES_BEFORE_UNAVAILABLE:
                self.last_successful_data = None
                raise UpdateFailed(f"4heat module unreachable: {err}") from err
            _LOGGER.debug("4heat: poll failed (%s), keeping last data", err)
            return self.last_successful_data

        self._check_room_probe(data)
        self.last_successful_data = data
        self.failures = 0
        self.last_ok = dt_util.now()
        self.update_interval = POLL_INTERVAL
        return data

    def _check_room_probe(self, data: dict) -> None:
        """Detect the internal probe fallback and keep trusted values meanwhile."""
        sp = data.get(self.setpoint_id)
        if not sp:
            return
        trusted_sp = self._trusted.get(self.setpoint_id)
        written = self.last_write is not None and sp[0] == self.last_write.get("value")
        lost = not (SETPOINT_RANGE[0] <= sp[0] <= SETPOINT_RANGE[1]) or (
            trusted_sp is not None and not written and abs(sp[0] - trusted_sp[0]) >= SETPOINT_JUMP
        )
        if lost:
            if not self.probe_lost:
                self.probe_lost_since = dt_util.now()
                _LOGGER.warning(
                    "4heat: room probe lost (setpoint read %s, room %s), keeping last trusted values",
                    sp[0], (data.get(ROOM_TEMP_ID) or [None])[0],
                )
            self.probe_lost = True
            for key in (self.setpoint_id, ROOM_TEMP_ID):
                if key in self._trusted:
                    data[key] = list(self._trusted[key])
        else:
            if self.probe_lost:
                _LOGGER.info("4heat: room probe back")
            self.probe_lost = False
            self.probe_lost_since = None
            for key in (self.setpoint_id, ROOM_TEMP_ID):
                if key in data:
                    self._trusted[key] = list(data[key])

    def _schedule_confirm(self) -> None:
        """Re-read the stove a little after a command instead of immediately."""
        if self._confirm_unsub:
            self._confirm_unsub()

        async def _later(_now):
            self._confirm_unsub = None
            await self.async_request_refresh()

        self._confirm_unsub = async_call_later(self.hass, CONFIRM_DELAY, _later)

    # ------------------------------------------------------------------ commands
    async def async_turn_on(self) -> bool:
        ok = await self._send(self._on_cmd, "ON")
        self._schedule_confirm()
        return ok

    async def async_turn_off(self) -> bool:
        ok = await self._send(self._off_cmd, "OFF")
        self._schedule_confirm()
        return ok

    async def async_unblock(self) -> bool:
        ok = await self._send(self._unblock_cmd, "UNBLOCK")
        self._schedule_confirm()
        return ok

    async def async_set_value(self, id, value) -> bool:
        payload = f'["SEC","1","B{id}{str(int(value)).zfill(12)}"]'.encode()
        ok = await self._send(payload, f"B{id}={value}")
        if ok and self.data is not None and id in self.data:
            self.data[id] = [int(value), self.data[id][1]]
            self.async_set_updated_data(self.data)
        self._schedule_confirm()
        return ok

    async def async_set_j(self, id, value) -> bool:
        """Write a value reported with the 'J' marker (e.g. room setpoint J30138)."""
        value = int(value)
        payload = f'["SEC","1","J{id}{str(value).zfill(12)}"]'.encode()
        ok = await self._send(payload, f"J{id}={value}")
        if ok:
            self.last_write = {"id": id, "value": value}
            if self.data is not None:
                self.data[id] = [value, "J"]
                self.async_set_updated_data(self.data)
        self._schedule_confirm()
        return ok

    async def async_set_setpoint(self, value) -> bool:
        low, high = SETPOINT_RANGE
        return await self.async_set_j(self.setpoint_id, max(low, min(high, int(round(float(value))))))
