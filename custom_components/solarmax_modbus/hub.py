
import asyncio
import logging
import time
from typing import Any
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
        self._client: AsyncModbusTcpClient # to get rid of the pylance errors
        self._client = None # type: ignore
        self._icmp_privileged = hass.data[DOMAIN]["icmp_privileged"]

    async def start_coordinator(self) -> None:
        """Ensure the coordinators are running and scheduled."""
        _LOGGER.info("Starting main coordinator scheduling... ")
        try:
            await self.async_request_refresh()
            _LOGGER.info("Main coordinator refresh requested")
        except Exception as e:
            _LOGGER.error(f"Failed to request main coordinator refresh: {e}")

    async def _async_host_alive(self, host) -> bool:
        """Ping host to check if alive."""
        _LOGGER.debug("ping address: %s", self._ping_host)
        try:
            data = await async_ping(
                host,
                count=1,
                timeout=1,
                privileged=self._icmp_privileged,
            )
        except NameLookupError as error:
            _LOGGER.info("Error resolving host: %s", self._ping_host)
            self._ping_host_reachable = False
            raise error from None
        return data.is_alive

    async def _async_maintain_connection(self):
        """Maintain the connection."""
        if self._client is None:
            self._client = AsyncModbusTcpClient(host=self._host, port=self._port, timeout=10)
        if not self._client.connected:
            _LOGGER.info(f"Connecting to Modbus client at {self._host}:{self._port}...")
            try:
                await self._client.connect()
            except Exception as e:
                _LOGGER.warning(f"connection error {e}")
            if not self._client.connected:
                _LOGGER.error(f"Failed to connect to Modbus client at {self._host}:{self._port}")
                raise ConnectionError(f"Failed to connect to {self._host}:{self._port}")
            _LOGGER.info(f"Connected to Modbus client at {self._host}:{self._port}")

    async def _async_update_data(self) -> dict[str, Any]:
        """Regular poll cycle: read fresh values."""
        _LOGGER.debug("Regular poll cycle")
        if self._ping_host != "":
            _LOGGER.debug("ping address: %s", self._ping_host)
            try:
                self._ping_host_reachable = await self._async_host_alive(
                    self._ping_host
                )
            except NameLookupError:
                _LOGGER.info("Error resolving host: %s", self._ping_host)
                self._ping_host_reachable = False
                return {"InverterMode": "Resolve Error"}
            if not self._ping_host_reachable:
                return {"InverterMode": "offline"}
        await self._async_maintain_connection()
        try:
            regs = await self._client.read_holding_registers(4097, count=60)
        except Exception as e:
            _LOGGER.error(f"Error reading holding registers: {e}")
            raise ConnectionError(f"Failed to connect to {self._host}:{self._port}")
        _LOGGER.info(f"got {regs.registers} registers")
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

    async def async_determineInverterType(self, hub, configdict):
        """Get the Inverter type."""
        _LOGGER.info(f"{hub.name}: trying to determine SolarMax inverter type")

        try:
            await self._async_maintain_connection()
            # Lese Seriennummer von Register 6672-6678 (7 Register)
            sn_data = await self._client.read_holding_registers(6672, count=7)
            #sn_data = await hub.async_read_holding_registers(unit=hub._modbus_addr, address=6672, count=7)

            if sn_data.isError():
                _LOGGER.error(f"{hub.name}: could not read serial number from address 6672-6678. Please check connection and Modbus address.")
                return 0

            # Dekodiere Seriennummer: Register enthalten 16-bit Werte, die zu ASCII konvertiert werden müssen
            seriesnumber = ""
            _LOGGER.debug(f"{hub.name}: Raw register values: {sn_data.registers}")

            for register_value in sn_data.registers:
                if register_value > 0:  # Nur wenn Wert > 0
                    # Versuche verschiedene Dekodierungsmethoden
                    try:
                        # Methode 1: High-Byte und Low-Byte einzeln
                        high_byte = (register_value >> 8) & 0xFF
                        low_byte = register_value & 0xFF

                        if high_byte > 0 and high_byte < 128:  # Gültiger ASCII-Bereich
                            seriesnumber += chr(high_byte)
                        if low_byte > 0 and low_byte < 128:  # Gültiger ASCII-Bereich
                            seriesnumber += chr(low_byte)

                    except Exception as e:
                        _LOGGER.debug(f"{hub.name}: Error converting register {register_value}: {e}")
                        # Fallback: Direkte Konvertierung falls Wert im ASCII-Bereich
                        if 32 <= register_value <= 126:  # Druckbare ASCII-Zeichen
                            seriesnumber += chr(register_value)

            seriesnumber = seriesnumber.strip()  # Entferne eventuelle Leerzeichen
            hub.seriesnumber = seriesnumber
            _LOGGER.info(f"{hub.name}: Inverter serial number: {seriesnumber}")

            # Überprüfe ob es sich um einen SolarMax/SunWay Inverter handelt
            if seriesnumber and len(seriesnumber) > 0:
                # Spezielle Behandlung für bekannte Seriennummern
                if seriesnumber == "2245-211303511":
                    self.inverter_model = "SolarMax 6SMT"
                    _LOGGER.info(f"{hub.name}: Detected known SolarMax 6SMT with SN: {seriesnumber}")
                elif seriesnumber.startswith("2245-"):
                    self.inverter_model = f"SolarMax 6SMT-{seriesnumber[-6:]}"
                    _LOGGER.info(f"{hub.name}: Detected SolarMax 6SMT series with SN: {seriesnumber}")
                else:
                    self.inverter_model = f"SolarMax-{seriesnumber}"
                    _LOGGER.info(f"{hub.name}: Detected SolarMax inverter with SN: {seriesnumber}")
                return "SOLARMAX_6SMT_10KTL"
            else:
                # Falls Seriennummer leer ist, aber Verbindung funktioniert, akzeptiere trotzdem
                _LOGGER.warning(f"{hub.name}: Serial number is empty, but trying to proceed as SolarMax inverter")
                self.inverter_model = "SolarMax-Unknown"
                return "SOLARMAX_6SMT_10KTL"

        except Exception as e:
            _LOGGER.error(f"{hub.name}: Error determining inverter type: {e}")
            # Selbst bei Fehlern, versuche als SolarMax zu behandeln
            _LOGGER.info(f"{hub.name}: Treating as SolarMax inverter despite detection error")
            self.inverter_model = "SolarMax-Fallback"
            return "SOLARMAX_6SMT_10KTL"

    def matchInverterWithMask(self, inverterspec, entitymask, serialnumber="not relevant", blacklist=None):
        return (inverterspec & entitymask) != 0

    def getSoftwareVersion(self, new_data):
        raw_version = new_data.get("firmware_version")
        if raw_version is not None:
             return str(raw_version)
        return None

    def getHardwareVersion(self, new_data):
        return None
