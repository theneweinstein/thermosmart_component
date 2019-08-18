"""
Support for Thermosmart sensor (boiler information).

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/thermosmart/
"""

import logging

from custom_components import thermosmart
from homeassistant.helpers.entity import Entity

DEPENDENCIES = ['thermosmart']

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Thermosmart platform."""
    name = discovery_info['name']
    call_update = discovery_info['update']

    sensors = []
    _LOGGER.debug("Setting up platform.")

    sensors_to_read = ['Control setpoint', 'Modulation level', 'Water pressure', 'Hot water flow rate', \
                    'Hot water temperature', 'Return water temperature']
    for _sensor in sensors_to_read:
        new_sensor = ThermosmartSensor(hass.data[thermosmart.DOMAIN], _sensor, update=call_update)
        sensors.append(new_sensor)
    add_entities(sensors)
    thermosmart.WEBHOOK_SUBSCRIBERS.extend(sensors)

    return True


class ThermosmartSensor(Entity):
    """Representation of a Thermosmart sensor."""

    def __init__(self, data, sensor, update=True, 
                    should_fire_event=False):
        """Initialize the sensor."""
        self._data = data
        self._client = self._data.thermosmart
        self._name = self._client.id
        self._client_id = self._client.id
        self.should_fire_event = should_fire_event
        self.sensor = sensor
        self._unit_of_measurement = self._client.\
            get_CV_sensor_list().get(sensor, '')
        self._state = None
        self.type = None
        self._doupdate = True
        self.update_without_throttle = True
        self.update()
        self._doupdate = update
        self.update_without_throttle = False

    def __str__(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def name(self):
        """Get the name of the sensor."""
        return "{} {}".format('Boiler', self.sensor)

    @property
    def unit_of_measurement(self):
        """Return the unit this state is expressed in."""
        return self._unit_of_measurement

    def update(self):
        """Get the latest state of the sensor."""
        if not self._doupdate:
            return

        if self.update_without_throttle:
            self._data.update(no_throttle=True)
            self.update_without_throttle = False
        else:
            self._data.update()

        if self._client.latest_update.get('ot'):
            self._state = \
                self._client.latest_update['ot']['readable'][self.sensor]
        else:
            self._state = None
        

    def process_webhook(self, message):
        """Process a webhook message."""
        if message['thermostat'] != self._client_id:
            return

        if message.get('ot'):
            converted_ot = self._client.convert_ot_data(message['ot']['raw'])
            if converted_ot.get(self.sensor):
                self._state = converted_ot[self.sensor]