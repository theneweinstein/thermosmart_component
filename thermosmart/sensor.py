"""
Support for Thermosmart sensor (boiler information).

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/thermosmart/
"""

import logging

from custom_components import thermosmart
from custom_components.thermosmart import ThermosmartEntity
from homeassistant.const import DEVICE_CLASS_TEMPERATURE, DEVICE_CLASS_PRESSURE
from homeassistant.components.sensor import STATE_CLASS_MEASUREMENT, SensorEntity
from .const import DEVICE, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Thermosmart thermostat."""
    data = hass.data[DOMAIN]

    # Check if Openterm is enabled
    if not data[config_entry.entry_id][DEVICE].thermosmart.opentherm():
        _LOGGER.warn("Openterm is not enabled, cannot read sensors. Please contact supplier to enabled it.")
        return
    
    sensors_to_read = ['Control setpoint', 'Modulation level', 'Water pressure', 'Hot water flow rate', \
                    'Hot water temperature', 'Return water temperature']
    sensors = []
    for sensor in sensors_to_read:
        new_sensor = ThermosmartSensor(data[config_entry.entry_id][DEVICE], sensor, do_update = config_entry.data['do_update'])
        sensors.append(new_sensor)

    async_add_entities(sensors)
    thermosmart.WEBHOOK_SUBSCRIBERS.extend(sensors)

    return True


class ThermosmartSensor(ThermosmartEntity, SensorEntity):
    """Representation of a Thermosmart sensor."""

    _attr_state_class = STATE_CLASS_MEASUREMENT

    def __init__(self, device, sensor, do_update = True):
        """Initialize the sensor."""
        super().__init__(device, do_update = do_update)
        self._attr_name = 'Boiler, ' + sensor

        self._attr_state = self._thermosmart.data['ot']['readable'][sensor] if self._thermosmart.data.get('ot') else None
        self._attr_unit_of_measurement = self._thermosmart.get_CV_sensor_list().get(sensor, '')

        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._client_id + '_boiler')},
            "name": "Boiler",
            "model": "n/a",
            "manufacturer": "Generic",
            "via_device": (DOMAIN, self._client_id)
        }
        self._attr_unique_id = self._client_id + '_' + sensor
        if sensor == 'Control setpoint' or 'Hot water temperature' or 'Return water temperature':
            self._attr_device_class = DEVICE_CLASS_TEMPERATURE
        if sensor == 'Water pressure':
            self._attr_device_class =  DEVICE_CLASS_PRESSURE
        else:
            self._attr_device_class = None

