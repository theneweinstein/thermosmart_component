"""
Support for Thermosmart thermostats.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/thermosmart/
"""
import logging

from custom_components import thermosmart
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVAC_MODE_AUTO, HVAC_MODE_HEAT, HVAC_MODE_COOL, SUPPORT_PRESET_MODE, SUPPORT_TARGET_TEMPERATURE, PRESET_AWAY, 
    PRESET_NONE, CURRENT_HVAC_HEAT, CURRENT_HVAC_COOL, CURRENT_HVAC_IDLE)
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS

DEPENDENCIES = ['thermosmart']

_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = (SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Thermosmart thermostat."""
    name = discovery_info['name']
    call_update = discovery_info['update']
    thermostat = ThermosmartThermostat(name, hass.data[thermosmart.DOMAIN],
        update=call_update)
    add_entities([thermostat])
    thermosmart.WEBHOOK_SUBSCRIBERS.append(thermostat)

    return True


class ThermosmartThermostat(ClimateEntityh):
    """Representation of a Thermosmart thermostat."""

    def __init__(self, name, data, update=True):
        """Initialize the thermostat."""
        self._data = data
        self._client = data.thermosmart
        self._current_temperature = None
        self._target_temperature = None
        self._current_HVAC = None
        self._HVAC_mode = None
        if name:
            self._name = name
        else:
            self._name = self._client.id
        self._away = False
        self._client_id = self._client.id
        self._override_update = False
        self._doupdate = True
        self.update_without_throttle = True
        self.update()
        self._doupdate = update

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
        self._HVAC_mode = HVAC_MODE_HEAT

    @property
    def preset_mode(self):
        """Return the preset mode."""
        if self._away:
            return PRESET_AWAY

        return PRESET_NONE

    @property
    def preset_modes(self):
        """Return a list of available preset modes."""
        return [PRESET_AWAY, PRESET_NONE]


    def set_preset_mode(self, preset_mode: str) -> None:
        """Activate a preset."""
        if preset_mode == self.preset_mode:
            return

        if preset_mode == PRESET_AWAY:
            self._away = True
            self._client.pause_thermostat(True)
            self._override_update = True
            self.update_without_throttle = True

        if preset_mode == PRESET_NONE:
            self._away = False
            self._client.pause_thermostat(False)
            self._override_update = True
            self.update_without_throttle = True     
        
    @property
    def hvac_mode(self):
        """Return current operation."""
        return self._HVAC_mode

    @property
    def hvac_modes(self):
        """Return the operation modes list."""
        if self._client.latest_update['ot']['readable']['Cooling_config']:
            return [HVAC_MODE_AUTO, HVAC_MODE_HEAT, HVAC_MODE_COOL]
        else:
            return [HVAC_MODE_AUTO, HVAC_MODE_HEAT]

    def set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        if hvac_mode == HVAC_MODE_AUTO:
            self._client.pause_thermostat(False)
        elif (hvac_mode == HVAC_MODE_HEAT) or (hvac_mode == HVAC_MODE_COOL):
            self._client.set_target_temperature(self._target_temperature)
        
        self._override_update = True
        self.update_without_throttle = True

    @property
    def hvac_action(self):
        """Return the current running hvac operation if supported."""
        return self._current_HVAC

    def update(self):
        """Get the latest state from the thermostat."""
        if (not self._doupdate) & (not self._override_update):
            return

        if self._override_update:
            self._override_update = False

        if self.update_without_throttle:
            self._data.update(no_throttle=True)
            self.update_without_throttle = False
        else:
            self._data.update()

        # Get temperatures
        self._current_temperature = self._client.room_temperature()
        self._target_temperature = self._client.target_temperature()

        # Check if opentherm is enabled
        if self._client.latest_update.get('ot'):
            # Find current HVAC action
            if self._client.latest_update['ot']['readable']['CH_enabled']:
                self._current_HVAC =  CURRENT_HVAC_HEAT
            elif self._client.latest_update['ot']['readable']['Cooling_enabled']:
                self._current_HVAC =  CURRENT_HVAC_COOL
            else:
                self._current_HVAC =  CURRENT_HVAC_IDLE

        # Check if thermomsmart is paused
        if self._client.source() == 'pause':
            self._away = True
        else:
            self._away = False

        # Check HVAC mode
        if self._client.source() == 'remote' or self._client.source() == 'manual':
            self._HVAC_mode = HVAC_MODE_HEAT
        elif self._client.source() == 'schedule' or self._client.source() == 'exception':
            self._HVAC_mode = HVAC_MODE_AUTO
        

    def process_webhook(self, message):
        """Process a webhook message."""
        if message['thermostat'] != self._client_id:
            return

        if message.get('room_temperature'):
            self._current_temperature = message['room_temperature']

        if message.get('target_temperature'):
            self._target_temperature = message['target_temperature']

        if message.get('ot'):
            converted_ot = self._client.convert_ot_data(message['ot']['raw'])
            if converted_ot['CH_enabled']:
                self._current_HVAC =  CURRENT_HVAC_HEAT
            elif converted_ot['Cooling_enabled']:
                self._current_HVAC =  CURRENT_HVAC_COOL
            else:
                self._current_HVAC =  CURRENT_HVAC_IDLE

        if message.get('source'):
            if message['source'] == 'pause':
                self._away = True
            else:
                self._away = False

            if message['source'] == 'remote' or message['source'] == 'manual':
                self._HVAC_mode = HVAC_MODE_HEAT
            elif message['source'] == 'schedule' or message['source'] == 'exception':
                self._HVAC_mode = HVAC_MODE_AUTO
