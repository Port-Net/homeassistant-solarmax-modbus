"""Constants for the home-assistant-solar-max-modbus integration."""


from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfTime
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)

ATTR_MANUFACTURER = "SolarMax"

DOMAIN = "solarmax_modbus"
DEFAULT_NAME = "SolarMax"
DEFAULT_SCAN_INTERVAL = 60
DEFAULT_PORT = 502
CONF_SOLARMAX_HUB = "solarmax_hub"
DEFAULT_FAST_POLL = False

SENSOR_TYPES = {}

line_sensor = [
    {"name": "Voltage",   "type": "UINT16", "factor":  0.1,
     "unit": UnitOfElectricPotential.VOLT, "device_class": SensorDeviceClass.VOLTAGE,
     "state_class": SensorStateClass.MEASUREMENT, "icon": "mdi:sine-wave"},
    {"name": "Current",   "type": "UINT16", "factor": 0.01,
     "unit": UnitOfElectricCurrent.AMPERE, "device_class": SensorDeviceClass.CURRENT,
     "state_class": SensorStateClass.MEASUREMENT, "icon": "mdi:current-ac"},
    {"name": "Power",     "type": "UINT32", "factor":  0.1,
     "unit": UnitOfPower.WATT, "device_class": SensorDeviceClass.POWER,
     "state_class": SensorStateClass.MEASUREMENT, "icon": "mdi:transmission-tower"},
    {"name": "Frequency", "type": "UINT16", "factor": 0.01,
     "unit": UnitOfFrequency.HERTZ, "device_class": SensorDeviceClass.FREQUENCY,
     "state_class": SensorStateClass.MEASUREMENT, "icon": "mdi:sine-wave"},
]

pv_sensor = [
    {"name": "Voltage",   "type": "UINT16", "factor":  0.1,
     "unit": UnitOfElectricPotential.VOLT, "device_class": SensorDeviceClass.VOLTAGE,
     "state_class": SensorStateClass.MEASUREMENT, "icon": "mdi:current-dc"},
    {"name": "Current",   "type": "UINT16", "factor": 0.01,
     "unit": UnitOfElectricCurrent.AMPERE, "device_class": SensorDeviceClass.CURRENT,
     "state_class": SensorStateClass.MEASUREMENT, "icon": "mdi:current-dc"},
    {"name": "Power",     "type": "UINT32", "factor":  0.1,
     "unit": UnitOfPower.WATT, "device_class": SensorDeviceClass.POWER,
     "state_class": SensorStateClass.MEASUREMENT, "icon": "mdi:solar-power"},
]

energy_sensor = [
    {"name": "Total Energy", "type": "UINT32", "factor":  1,
     "unit": UnitOfEnergy.KILO_WATT_HOUR, "device_class": SensorDeviceClass.ENERGY,
     "state_class": SensorStateClass.TOTAL_INCREASING, "icon": "mdi:solar-power"},
    {"name": "Total Hours", "type": "UINT32", "factor":  1,
     "unit": UnitOfTime.HOURS, "device_class": SensorDeviceClass.DURATION,
     "state_class": SensorStateClass.TOTAL_INCREASING, "icon": "mdi:timeline-clock-outline"},
]

power_sensors = [
    {"name": "Active Power", "type": "UINT32", "factor":  0.001,
     "unit": UnitOfPower.KILO_WATT, "device_class": SensorDeviceClass.POWER,
     "state_class": SensorStateClass.MEASUREMENT, "icon": "mdi:solar-power"},
    {"name": "Reactive Power", "type": "UINT32", "factor":  0.001,
     "unit": UnitOfPower.KILO_WATT, "device_class": SensorDeviceClass.REACTIVE_POWER,
     "state_class": SensorStateClass.MEASUREMENT, "icon": "mdi:solar-power"},
    {"name": "Today max Power", "type": "UINT32", "factor":  0.1,
     "unit": UnitOfPower.WATT, "device_class": SensorDeviceClass.POWER,
     "state_class": SensorStateClass.MEASUREMENT, "icon": "mdi:solar-power"},
]

STATUS_INVERTER_MODE = {
  0: "Initial Mode",
  1: "Standby",
  3: "OnGrid",
  5: "Error",
  9: "Shutdown"
}

