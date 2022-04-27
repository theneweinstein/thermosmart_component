"""
Support for Thermosmart thermostats.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/thermosmart/
"""
import logging
import voluptuous as vol

from custom_components import thermosmart
from custom_components.thermosmart import ThermosmartEntity

from .const import DOMAIN, DEVICE

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ClimateEntityFeature, HVAC_MODE_AUTO, HVAC_MODE_HEAT, HVAC_MODE_COOL, PRESET_AWAY, 
    PRESET_NONE, CURRENT_HVAC_HEAT, CURRENT_HVAC_COOL, CURRENT_HVAC_IDLE)
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS
from homeassistant.helpers import config_validation as cv, entity_platform

_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = (
    ClimateEntityFeature.TARGET_TEMPERATURE
    | ClimateEntityFeature.PRESET_MODE
)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Thermosmart thermostat."""
    data = hass.data[DOMAIN].get(config_entry.entry_id)

    thermostat = ThermosmartThermostat(data[DEVICE], do_update = config_entry.data['do_update'])
    async_add_entities([thermostat])
    thermosmart.WEBHOOK_SUBSCRIBERS.append(thermostat)

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        'add_exception',
        {
            vol.Required("start_day"): vol.All(cv.positive_int, vol.Range(min=1,max=31)),
            vol.Required("start_month"): vol.All(cv.positive_int, vol.Range(min=1,max=12)),
            vol.Required("start_year",): cv.positive_int, 
            vol.Required("start_time"): cv.time,
            vol.Required("end_day"): vol.All(cv.positive_int, vol.Range(min=1,max=31)),
            vol.Required("end_month"): vol.All(cv.positive_int, vol.Range(min=1,max=12)),
            vol.Required("end_year",): cv.positive_int, 
            vol.Required("end_time"): cv.time,
            vol.Required("program"): vol.All(cv.string, vol.In(["anti_freeze","not_home","home","comfort"]))
        },
        'add_exception'
    )

    platform.async_register_entity_service(
        'clear_exceptions',
        {},
        'clear_exceptions'
    )

class ThermosmartThermostat(ThermosmartEntity, ClimateEntity):
    """Representation of a Thermosmart thermostat."""

    _attr_supported_features = SUPPORT_FLAGS

    def __init__(self, device, do_update = True):
        """Initialize the thermostat."""
        super().__init__(device, do_update = do_update)
        self._attr_name = "Thermosmart"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._client_id)},
            "name": "Thermosmart",
            "model": "V3",
            "manufacturer": "Thermosmart",
        }
        self._attr_unique_id = self._client_id + '_climate'

        self._attr_temperature_unit = TEMP_CELSIUS

        self._attr_preset_modes = [PRESET_AWAY, PRESET_NONE]
        self._attr_hvac_modes = [HVAC_MODE_AUTO, HVAC_MODE_HEAT, HVAC_MODE_COOL] if self._thermosmart.data['ot']['readable']['Cooling_config'] else [HVAC_MODE_AUTO, HVAC_MODE_HEAT]
        self._exceptions = self._thermosmart.exceptions()

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        self._thermosmart.set_target_temperature(temperature)
        self._force_update = True
        self.async_update()

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
    def current_temperature(self):
        return self._thermosmart.room_temperature()

    @property
    def target_temperature(self):
        return self._thermosmart.target_temperature()

    @property
    def preset_mode(self):
        return PRESET_AWAY if self._thermosmart.source() == 'pause' else PRESET_NONE
        
    @property
    def hvac_mode(self):
        """Return current operation."""
        if self._thermosmart.source() == 'remote' or self._thermosmart.source() == 'manual':
            return HVAC_MODE_HEAT
        elif self._thermosmart.source() == 'schedule' or self._thermosmart.source() == 'exception':
            return HVAC_MODE_AUTO

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

    # Define service-calls
    def add_exception(self,start_day, start_month, start_year, start_time, end_day, end_month, end_year, end_time, program):
        """Add exceptions to the current list."""
        exceptions = self._exceptions

        new_exception = {"start": [start_year, start_month-1, start_day, start_time.hour, round(start_time.minute/15)*15],
                        "end": [end_year, end_month-1, end_day, end_time.hour, round(end_time.minute/15)*15],
                        "temperature": program}

        exceptions.append(new_exception)

        self._thermosmart.set_exceptions(exceptions)

    def clear_exceptions(self):
        """Clear all exceptions."""
        self._thermosmart.set_exceptions([])

            

