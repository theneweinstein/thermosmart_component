"""
Support for Thermosmart sensor (boiler information).
For more details about this platform, please refer to the documentation at
??
"""

import logging

import voluptuous as vol

from custom_components import thermosmart
import homeassistant.helpers.config_validation as cv
from homeassistant.const import ATTR_ENTITY_ID, ATTR_NAME, CONF_NAME
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.util import slugify

DEPENDENCIES = ['thermosmart']

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES = thermosmart.SENSOR_LIST


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Thermosmart platform."""
    name = config.get(CONF_NAME, None)

    sensors = []
    _LOGGER.debug("Setting up platform")

    client = hass.data[thermosmart.DOMAIN]
    for _sensor in list(SENSOR_TYPES.keys()):
        new_sensor = ThermosmartSensor(name, client, _sensor)
        sensors.append(new_sensor)
    add_entities(sensors)


class ThermosmartSensor(Entity):
    """Representation of a Thermosmart sensor."""

    def __init__(self, name, client, sensor, should_fire_event=False):
        """Initialize the sensor."""
        self.client = client
        if name:
            self._name = name
        else:
            self._name = client.id
        self.should_fire_event = should_fire_event
        self.sensor = sensor
        self._unit_of_measurement = SENSOR_TYPES.get(sensor, '')
        self._state = None
        self.type = None

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
        return "{} {}".format(self._name, self.sensor)

    @property
    def unit_of_measurement(self):
        """Return the unit this state is expressed in."""
        return self._unit_of_measurement

    def update(self):
        """Get the latest state of the sensor."""
        result = self.client.request_thermostat()
        if result.get('ot'):
            self._state = result['ot']['readable'][self.sensor]
        else:
            self._state = None