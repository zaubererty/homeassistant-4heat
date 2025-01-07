"""Provides the MYPV DataUpdateCoordinator."""
from datetime import timedelta
import logging
import socket
import time
import asyncio
from async_timeout import timeout
from homeassistant.util.dt import utcnow
from homeassistant.const import CONF_HOST
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN, SOCKET_BUFFER, SOCKET_TIMEOUT, TCP_PORT, DATA_QUERY, ERROR_QUERY,
    RESULT_ERROR, CONF_MODE, MODES, MODE_TYPE, ERROR_TYPE
)

_LOGGER = logging.getLogger(__name__)


class FourHeatDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching 4heat data."""

    def __init__(self, hass: HomeAssistantType, *, config: dict, options: dict, id: str):
        """Initialize global 4heat data updater."""
        self._host = config[CONF_HOST]
        self._mode = False
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
            """Invia una query al dispositivo 4Heat con retry in caso di fallimento."""
            max_retries = 5  # Numero massimo di tentativi
            retry_delay = 2  # Primo ritardo in secondi

            for attempt in range(1, max_retries + 1):
                try:
                    _LOGGER.debug(f"🔄 Tentativo {attempt} di inviare query: {query}")
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(SOCKET_TIMEOUT)
                    s.connect((self._host, TCP_PORT))
                    s.send(query)
                    result = s.recv(SOCKET_BUFFER).decode()
                    s.close()

                    _LOGGER.debug(f"✅ Risposta ricevuta: {result}")

                    result = result.replace("[", "").replace("]", "").replace('"', "")
                    d = result.split(",")

                    if not d or d[0] == "":
                        _LOGGER.warning("⚠️ Risposta vuota ricevuta, ritentiamo...")
                    else:
                        return d  # Se la risposta è valida, la restituiamo subito

                except Exception as error:
                    _LOGGER.error(f"❌ Errore durante il tentativo {attempt}: {error}")

                if attempt < max_retries:
                    _LOGGER.warning(f"🔁 Riprovo tra {retry_delay} secondi...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Aumenta il tempo di attesa in modo esponenziale

            _LOGGER.error("❌ Tutti i tentativi sono falliti. Uso i dati precedenti.")
            return []


        def _update_data() -> dict:
            """Fetch data from 4heat via sync functions."""
            list = _query_stove(DATA_QUERY)
            if not list:  # Se la lista è vuota, non aggiornare i dati
                _LOGGER.warning("Nessun dato valido ricevuto, mantenendo i valori precedenti.")
                return self.data if self.data else {}

            dict = self.data if self.data else {}

            if list[0] == RESULT_ERROR:
                list = _query_stove(ERROR_QUERY)

            for data in list:
                if len(data) > 3:
                    try:
                        dict[data[1:6]] = [int(data[7:]), data[0]]
                    except ValueError:
                        _LOGGER.error(f"Errore nel parsing del dato: {data}")

            return dict


        """Fetch data from 4heat."""
        for attempt in range(5):  # ⬅ Tentiamo fino a 3 volte
            try:
                async with timeout(20):  # ⬅ Timeout più lungo
                    d = await self.hass.async_add_executor_job(_update_data)
                    return d
            except Exception as error:
                _LOGGER.warning(f"Tentativo {attempt + 1}/3 fallito: {error}")
                await asyncio.sleep(5)  # ⬅ Aspettiamo 5 secondi prima di riprovare

        _LOGGER.error("Errore durante il recupero dei dati dopo 3 tentativi.")
        raise UpdateFailed("Errore durante il recupero dei dati dopo 3 tentativi.")


    async def async_turn_on(self) -> bool:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(SOCKET_TIMEOUT)
            s.connect((self._host, TCP_PORT))
            s.send(self._on_cmd)
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
            s.send(self._off_cmd)
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
            s.send(self._unblock_cmd)
            s.recv(SOCKET_BUFFER).decode()
            s.close()
            _LOGGER.debug("Toggle Unblock")
        except Exception as ex:
            _LOGGER.error(ex)


    async def async_set_value(self, id, value) -> bool:
        val = str(value).zfill(12)
        set_val = f'["SEC","1","B{id}{val}"]'.encode()
        _LOGGER.debug(f"Command to send: {set_val}")
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(SOCKET_TIMEOUT)
            s.connect((self._host, TCP_PORT))
            s.send(set_val)
            s.recv(SOCKET_BUFFER).decode()
            s.close()
            _LOGGER.debug("Set value")
        except Exception as ex:
            _LOGGER.error(ex)

