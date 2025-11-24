"""The home-assistant-solar-max-modbus integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SCAN_INTERVAL

from .const import DOMAIN, DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, DEFAULT_FAST_POLL, ATTR_MANUFACTURER
from .hub import SolarMaxModbusHub
from icmplib import SocketPermissionError, async_ping

_PLATFORMS: list[Platform] = [Platform.SENSOR]

type New_NameConfigEntry = ConfigEntry[SolarMaxModbusHub]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the SolarMax Modbus component."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["icmp_privileged"] = await _can_use_icmp_lib_with_privilege()
    return True

async def async_setup_entry(hass: HomeAssistant, entry: New_NameConfigEntry) -> bool:
    """Set up home-assistant-solar-max-modbus from a config entry."""

    hub = await _create_hub(hass, entry)

    if not hub:
        return False

    hass.data[DOMAIN][entry.entry_id] = {
        "hub": hub,
        "device_info": _create_device_info(entry)
    }

    # Start the main and fast coordinator scheduling
    await hub.start_coordinator()

    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    return True


# TODO Update entry annotation
async def async_unload_entry(hass: HomeAssistant, entry: New_NameConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)


async def _create_hub(hass: HomeAssistant, entry: New_NameConfigEntry) -> SolarMaxModbusHub | None:
    """Helper function to create the SolarMax Modbus hub."""
    hub = None
    try:
        hub = SolarMaxModbusHub(
            hass,
            entry.data[CONF_NAME],  # Name is always in data, not in options
            #_get_config_value(entry, CONF_HOST),
            entry.options.get(CONF_HOST, entry.data.get(CONF_HOST)),
            entry.options.get(CONF_PORT, entry.data.get(CONF_PORT, DEFAULT_PORT)),
            entry.options.get(CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)),
            entry.options.get("ping_host", entry.data.get("ping_host", None)),
        )
        # Ensure the scan_interval is correctly passed to the hub
        scan_interval = entry.options.get(CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
        _LOGGER.info(f"Setting scan interval to {scan_interval} seconds")
        _LOGGER.info(f"Starting hub with first refresh...")
        await hub.async_config_entry_first_refresh()
        _LOGGER.info(f"Hub first refresh completed, coordinator should run every {scan_interval} seconds")
    except Exception as e:
        _LOGGER.error(f"Failed to set up SolarMax Modbus hub: {e}")
    return hub

def _create_device_info(entry: New_NameConfigEntry) -> dict:
    """Create the device info for SolarMax Modbus hub."""
    return {
        "identifiers": {(DOMAIN, entry.data[CONF_NAME])},
        "name": entry.data[CONF_NAME],
        "manufacturer": ATTR_MANUFACTURER
    }

async def _can_use_icmp_lib_with_privilege() -> bool | None:
    """Verify we can create a raw socket."""
    try:
        await async_ping("127.0.0.1", count=0, timeout=0, privileged=True)
    except SocketPermissionError:
        try:
            await async_ping("127.0.0.1", count=0, timeout=0, privileged=False)
        except SocketPermissionError:
            _LOGGER.info(
                "Cannot use icmplib because privileges are insufficient to create the"
                " socket"
            )
            return None

        _LOGGER.info("Using icmplib in privileged=False mode")
        return False

    _LOGGER.info("Using icmplib in privileged=True mode")
    return True
