"""
Support for Thermosmart sensor (boiler information).

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/thermosmart/
"""

import logging

from thermosmart_hass import SENSOR_LIST

from .const import DOMAIN
from . import ThermosmartCoordinator

from homeassistant.components.sensor import SensorDeviceClass, STATE_CLASS_MEASUREMENT, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import UnitOfTemperature, UnitOfPressure
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity


_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, 
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Thermosmart thermostat."""
    
    coordinator = hass.data[DOMAIN].get(config_entry.entry_id)
    unique_id= config_entry.unique_id
    assert unique_id is not None
    name = config_entry.data['name']

    # Check if Openterm is enabled
    if coordinator.data.get('ot'):
        if not coordinator.data['ot']['enabled']:
            _LOGGER.warn("Openterm is not enabled, cannot read sensors. Please contact supplier to enabled it.")
            return
    
    sensors_to_read = ['Control setpoint', 'Modulation level', 'Water pressure', 'Hot water flow rate', \
                    'Hot water temperature', 'Return water temperature']
    sensors = []
    for sensor in sensors_to_read:
        new_sensor = ThermosmartSensor(coordinator, unique_id, name, sensor)
        sensors.append(new_sensor)

    async_add_entities(sensors)

    return True


class ThermosmartSensor(CoordinatorEntity[ThermosmartCoordinator], SensorEntity):
    """Representation of a Thermosmart sensor."""

    _attr_state_class = STATE_CLASS_MEASUREMENT
    _attr_has_entity_name = True

    def __init__(self, coordinator: ThermosmartCoordinator, unique_id: str, name: str, sensor: str):
        """Initialize the sensor."""
        super().__init__(coordinator)
        
        self._sensor = sensor
        
        self._attr_name = sensor.capitalize()        
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, unique_id)},
            manufacturer="Thermosmart",
            model="V3",
            name=name
        )
        self._attr_unique_id = unique_id + '_' + sensor

        if sensor == 'Control setpoint' or 'Hot water temperature' or 'Return water temperature':
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        if sensor == 'Water pressure':
            self._attr_device_class =  SensorDeviceClass.PRESSURE
            self._attr_native_unit_of_measurement = UnitOfPressure.BAR
        else:
            self._attr_device_class = None
            self._attr_native_unit_of_measurement = SENSOR_LIST.get(sensor, '')

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data['ot']['readable'][self._sensor] if self.coordinator.data.get('ot') else None
