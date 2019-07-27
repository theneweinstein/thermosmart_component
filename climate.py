"""
Support for Thermosmart thermostats.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/thermosmart/
"""
import logging

from custom_components import thermosmart
from homeassistant.components.climate import ClimateDevice
from homeassistant.components.climate.const import (
    HVAC_MODE_AUTO, SUPPORT_PRESET_MODE, SUPPORT_TARGET_TEMPERATURE, PRESET_AWAY)
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS

DEPENDENCIES = ['thermosmart']

_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = (SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE)

PRESET_MODES = [
    PRESET_AWAY
]


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Thermosmart thermostat."""
    name = discovery_info['name']
    call_update = discovery_info['update']
    thermostat = ThermosmartThermostat(name, hass.data[thermosmart.DOMAIN],
        update=call_update)
    add_entities([thermostat])
    thermosmart.WEBHOOK_SUBSCRIBERS.append(thermostat)

    return True


class ThermosmartThermostat(ClimateDevice):
    """Representation of a Thermosmart thermostat."""

    def __init__(self, name, data, update=True):
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
        self._doupdate = True
        self.update_without_throttle = True
        self.update()
        self._doupdate = update
        self._operation_list = [HVAC_MODE_AUTO]

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS

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
    def preset_mode(self):
        """Return the preset mode."""
        if self._away:
            return PRESET_AWAY

        return None

    @property
    def preset_modes(self):
        """Return a list of available preset modes."""
        return PRESET_MODES

    def set_preset_mode(self, preset_mode):
        """Activate a preset."""
        if preset_mode == self.preset_mode:
            return

        if preset_mode == PRESET_AWAY:
            self._away = True
            self._client.pause_thermostat(True)
            self.update_without_throttle = True

        if preset_mode == None:
            self._away = False
            self._client.pause_thermostat(False)
            self.update_without_throttle = True       
        
    @property
    def hvac_mode(self):
        """Return current operation."""
        return HVAC_MODE_AUTO

    @property
    def hvac_modes(self):
        """Return the operation modes list."""
        return self._operation_list

    def update(self):
        """Get the latest state from the thermostat."""
        if not self._doupdate:
            return

        if self.update_without_throttle:
            self._data.update(no_throttle=True)
            self.update_without_throttle = False
        else:
            self._data.update()

        self._current_temperature = self._client.room_temperature()
        self._target_temperature = self._client.target_temperature()

        if self._client.source() == 'pause':
            self._away = True
        else:
            self._away = False

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
