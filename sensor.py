"""
Support for Thermosmart sensor (boiler information).

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/thermosmart/
"""

import logging

from custom_components import thermosmart
from custom_components.thermosmart import BoilerEntity
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


class ThermosmartSensor(BoilerEntity, SensorEntity):
    """Representation of a Thermosmart sensor."""

    _attr_state_class = STATE_CLASS_MEASUREMENT

    def __init__(self, device, sensor, do_update = True):
        """Initialize the sensor."""
        super().__init__(device, do_update = do_update)
        self._name = 'Boiler, ' + sensor
        self.sensor = sensor
        self._unit_of_measurement = self._thermosmart.get_CV_sensor_list().get(sensor, '')
        self._state = None

    def __str__(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._thermosmart.data.get('ot'):
            self._state = self._thermosmart.data['ot']['readable'][self.sensor]
        else:
            self._state = None

        return self._state

    @property
    def name(self):
        """Get the name of the sensor."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._client_id + '_' + self.sensor

    @property
    def unit_of_measurement(self):
        """Return the unit this state is expressed in."""
        return self._unit_of_measurement

    @property
    def device_class(self):
        if self.sensor == 'Control setpoint' or 'Hot water temperature' or 'Return water temperature':
            return DEVICE_CLASS_TEMPERATURE
        if self.sensor == 'Water pressure':
            return DEVICE_CLASS_PRESSURE
        else:
            return None
