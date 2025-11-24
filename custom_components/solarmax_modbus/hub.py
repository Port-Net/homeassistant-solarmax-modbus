
import asyncio
import logging
import time
from typing import Any
#from typing import Optional, Any, Dict, List, Callable
from datetime import timedelta
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from pymodbus.client import AsyncModbusTcpClient
from random import randint
from icmplib import NameLookupError, async_ping
from .const import DOMAIN
from . import const as _const

_LOGGER = logging.getLogger(__name__)

class SolarMaxModbusHub(DataUpdateCoordinator[dict[str, Any]]):
    """SolarMax Modbus hub."""
    def __init__(self, hass: HomeAssistant, name: str, host: str, port: int, scan_interval: int, ping_host: str | None) -> None:
        """Initialize the SolarMax Modbus hub."""
        super().__init__(
            hass,
            _LOGGER,
            name=name,
            update_interval=timedelta(seconds=scan_interval),
            update_method=self._async_update_data,
        )
        self._host = host
        self._port = port
        self._scan_interval = scan_interval
        self._ping_host = ping_host
        self._ping_host_reachable = False
        self.inverter_data: dict[str, Any] = {}
        self._key_dict = {}
        self._client = None  # type: AsyncModbusTcpClient | None
        self._icmp_privileged = hass.data[DOMAIN]["icmp_privileged"]

    async def start_coordinator(self) -> None:
        """Ensure the coordinators are running and scheduled."""
        _LOGGER.info("Starting main coordinator scheduling... ")
        try:
            await self.async_request_refresh()
            _LOGGER.info("Main coordinator refresh requested")
        except Exception as e:
            _LOGGER.error(f"Failed to request main coordinator refresh: {e}")

    async def _async_update_data(self) -> dict[str, Any]:
        """Regular poll cycle: read fresh values."""
        _LOGGER.debug("Regular poll cycle")
        if self._ping_host != "":
            _LOGGER.debug("ping address: %s", self._ping_host)
            try:
                data = await async_ping(
                    self._ping_host,
                    count=1,
                    timeout=1,
                    privileged=self._icmp_privileged,
                )
            except NameLookupError:
                _LOGGER.info("Error resolving host: %s", self._ping_host)
                self._ping_host_reachable = False
                return {"InverterMode": "Resolve Error"}

            _LOGGER.debug(
                "async_ping returned: reachable=%s sent=%i received=%s",
                data.is_alive,
                data.packets_sent,
                data.packets_received,
            )
            if not data.is_alive:
                return {"InverterMode": "offline"}
        if self._client is None:
            self._client = AsyncModbusTcpClient(host=self._host, port=self._port, timeout=10)
        if not self._client.connected:
            _LOGGER.info(f"Connecting to Modbus client at {self._host}:{self._port}...")
            await self._client.connect()
            if not self._client.connected:
                _LOGGER.error(f"Failed to connect to Modbus client at {self._host}:{self._port}")
                raise ConnectionError(f"Failed to connect to {self._host}:{self._port}")
            _LOGGER.info(f"Connected to Modbus client at {self._host}:{self._port}")
        try:
            regs = await self._client.read_holding_registers(4097, count=36)
        except Exception as e:
            _LOGGER.error(f"Error reading holding registers: {e}")
            raise ConnectionError(f"Failed to connect to {self._host}:{self._port}")
        _LOGGER.debug(f"got {regs.registers} registers")
        for offset in range(len(regs.registers)):
            if offset in self._key_dict:
                key = self._key_dict[offset]["key"]
                data_type: str = self._key_dict[offset]["type"]
                if data_type.startswith("STATUS"):
                    q = self._client.convert_from_registers(regs.registers[offset:offset+1], self._client.DATATYPE.UINT16)
                    t = getattr(_const, data_type)
                    if t and q in t:
                        self.inverter_data[key] = t[q]
                    else:
                        self.inverter_data[key] = f"unknown {q}"
                else:
                    factor = self._key_dict[offset]["factor"]
                    t = getattr(self._client.DATATYPE, data_type)
                    data_len = t.value[1]
                    r = self._client.convert_from_registers(regs.registers[offset:offset + data_len], t)
                    self.inverter_data[key] = r * factor
        return self.inverter_data

    async def update_runtime_settings(self, scan_interval: int, ping_host:str | None) -> None:
        """Update settings."""
        _LOGGER.info("Update settings")
        self._scan_interval = scan_interval
        self._ping_host = ping_host

    async def reconfigure_connection_settings(self, host: str, port: int, scan_interval: int, ping_host:str | None) -> None:
        """Update settings."""
        _LOGGER.info("Update settings")
        self._host = host
        self._port = port
        self._scan_interval = scan_interval
        self._ping_host = ping_host

    def set_key_dict(self, key_dict):
        """Set mapping between register position and variable."""
        self._key_dict = key_dict
