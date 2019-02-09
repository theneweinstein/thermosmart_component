"""
Support for Thermomsart thermostats.
For more details about this platform, please refer to the documentation at
??
"""
import logging

import voluptuous as vol

from custom_components import thermosmart
import homeassistant.helpers.config_validation as cv
from homeassistant.components.climate import (
    ClimateDevice, PLATFORM_SCHEMA, SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_AWAY_MODE)
from homeassistant.const import (CONF_NAME,
    TEMP_CELSIUS, ATTR_TEMPERATURE)


_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ['thermosmart']


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Thermosmart thermostat."""
    name = config.get(CONF_NAME, None)
    thermostat = ThermosmartThermostat(name, hass.data[thermosmart.DOMAIN])
    add_entities([thermostat])
    thermosmart.WEBHOOKS_SUBSCRIBERS.append(thermostat) 

    return True

class ThermosmartThermostat(ClimateDevice):
    """Representation of a Thermosmart thermostat."""

    def __init__(self, name, data):
        """Initialize the thermostat."""
        self._data = data
        self._client = data.thermosmart
        self._current_temperature = None
        self._target_temperature = None
        if name:
            self._name = name
        else:
            self._name = self._client.id
        self._away = False
        self._client_id = self._client.id
        self.update_without_throttle = False

    @property
    def supported_features(self):
        """Return the list of supported features."""
        supported = (SUPPORT_TARGET_TEMPERATURE | SUPPORT_AWAY_MODE)
        return supported

    @property
    def name(self):
        """Return the name of the Thermosmart, if any."""
        return self._name

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temperature

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        self._client.set_target_temperature(temperature)

    @property
    def is_away_mode_on(self):
        """Return true if away mode is on."""
        return self._away

    def turn_away_mode_on(self):
        """Turn away on."""
        self._away = True
        self._client.pause_thermostat(True)
        self.update_without_throttle = True

    def turn_away_mode_off(self):
        """Turn away off."""
        self._away = False
        self._client.pause_thermostat(False)
        self.update_without_throttle = True

    def update(self):
        """Get the latest state from the thermostat."""
        if self.update_without_throttle:
            self._data.update(no_throttle=True)
            self.update_without_throttle = False
        else:
            self._data.update()

        self._current_temperature = self._client.room_temperature()
        self._target_temperature = self._client.target_temperature()

    def process_webhook(self, message):
        """Process a webhook message."""
        if message['thermostat'] != self._client_id:
            return

        if message.get('room_temperature'):
            self._current_temperature = message['room_temperature']

        if message.get('target_temperature'):
            self._target_temperature = message['target_temperature']
        
        if message.get('source'):
            if message['source'] == 'pause':
                self._away = True
            else:
                self._away = False


