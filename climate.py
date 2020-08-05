"""
Support for Thermosmart thermostats.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/thermosmart/
"""
import logging

from custom_components import thermosmart
from custom_components.thermosmart import ThermosmartEntity

from .const import DOMAIN, DEVICE

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVAC_MODE_AUTO, HVAC_MODE_HEAT, HVAC_MODE_COOL, SUPPORT_PRESET_MODE, SUPPORT_TARGET_TEMPERATURE, PRESET_AWAY, 
    PRESET_NONE, CURRENT_HVAC_HEAT, CURRENT_HVAC_COOL, CURRENT_HVAC_IDLE)
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS

_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = (SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Thermosmart thermostat."""
    data = hass.data[DOMAIN].get(config_entry.entry_id)

    thermostat = ThermosmartThermostat(data[DEVICE], do_update = config_entry.data['do_update'])
    async_add_entities([thermostat])
    thermosmart.WEBHOOK_SUBSCRIBERS.append(thermostat)


class ThermosmartThermostat(ThermosmartEntity, ClimateEntity):
    """Representation of a Thermosmart thermostat."""

    def __init__(self, device, do_update = True):
        """Initialize the thermostat."""
        super().__init__(device, do_update = do_update)
        self._name = "Thermosmart"

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    @property
    def name(self):
        """Return the name of the Thermosmart, if any."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._client_id + '_climate'

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._thermosmart.room_temperature()

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._thermosmart.target_temperature()

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        self._thermosmart.set_target_temperature(temperature)
        self._force_update = True
        self.async_update()

    @property
    def preset_mode(self):
        """Return the preset mode."""
        if self._thermosmart.source() == 'pause':
            return PRESET_AWAY
        else:
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
            self._thermosmart.pause_thermostat(True)

        if preset_mode == PRESET_NONE:
            self._thermosmart.pause_thermostat(False)  

        self._force_update = True
        self.async_update()
        
    @property
    def hvac_mode(self):
        """Return current operation."""
        if self._thermosmart.source() == 'remote' or self._thermosmart.source() == 'manual':
            return HVAC_MODE_HEAT
        elif self._thermosmart.source() == 'schedule' or self._thermosmart.source() == 'exception':
            return HVAC_MODE_AUTO

    @property
    def hvac_modes(self):
        """Return the operation modes list."""
        if self._thermosmart.data['ot']['readable']['Cooling_config']:
            return [HVAC_MODE_AUTO, HVAC_MODE_HEAT, HVAC_MODE_COOL]
        else:
            return [HVAC_MODE_AUTO, HVAC_MODE_HEAT]

    def set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        if hvac_mode == HVAC_MODE_AUTO:
            self._thermosmart.pause_thermostat(False)
            self._force_update = True
            self.async_update()
        elif (hvac_mode == HVAC_MODE_HEAT) or (hvac_mode == HVAC_MODE_COOL):
            self._thermosmart.set_target_temperature(self.target_temperature)
            self._force_update = True
            self.async_update()

    @property
    def hvac_action(self):
        """Return the current running hvac operation if supported."""
        if self._thermosmart.data.get('ot'):
            # Find current HVAC action
            if self._thermosmart.data['ot']['readable']['CH_enabled']:
                return CURRENT_HVAC_HEAT
            elif self._thermosmart.data['ot']['readable']['Cooling_enabled']:
                return CURRENT_HVAC_COOL
            else:
                return CURRENT_HVAC_IDLE
            

