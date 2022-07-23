"""
Support for Thermosmart thermostats.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/thermosmart/
"""
import logging
import voluptuous as vol

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ClimateEntityFeature, HVAC_MODE_AUTO, HVAC_MODE_HEAT, HVAC_MODE_COOL, PRESET_AWAY, 
    PRESET_NONE, CURRENT_HVAC_HEAT, CURRENT_HVAC_COOL, CURRENT_HVAC_IDLE)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from . import ThermosmartCoordinator

_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = (
    ClimateEntityFeature.TARGET_TEMPERATURE
    | ClimateEntityFeature.PRESET_MODE
)

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

    thermostat = ThermosmartThermostat(coordinator, unique_id, name)
    async_add_entities([thermostat])

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

class ThermosmartThermostat(CoordinatorEntity[ThermosmartCoordinator], ClimateEntity):
    """Representation of a Thermosmart thermostat."""

    _attr_supported_features = SUPPORT_FLAGS
    _attr_temperature_unit = TEMP_CELSIUS
    _attr_preset_modes = [PRESET_AWAY, PRESET_NONE]
    _attr_has_entity_name = True

    def __init__(self, coordinator: ThermosmartCoordinator, unique_id: str, name: str):
        """Initialize the thermostat."""
        super().__init__(coordinator)
        
        self._attr_name = name.capitalize()
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, unique_id)},
            manufacturer="Thermosmart",
            model="V3",
            name=name,
        )
        self._attr_unique_id = unique_id + '_climate'
        self._attr_hvac_modes = [HVAC_MODE_AUTO, HVAC_MODE_HEAT, HVAC_MODE_COOL] if self.coordinator.data['ot']['readable']['Cooling_config'] else [HVAC_MODE_AUTO, HVAC_MODE_HEAT]
        self._exceptions = self.coordinator.data['exceptions']

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        await self.hass.async_add_executor_job(self.coordinator.client.set_target_temperature, temperature)
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Activate a preset."""
        if preset_mode == self.preset_mode:
            return

        if preset_mode == PRESET_AWAY:
            await self.hass.async_add_executor_job(self.coordinator.client.pause_thermostat, True)

        if preset_mode == PRESET_NONE:
            await self.hass.async_add_executor_job(self.coordinator.client.pause_thermostat, False)  

        await self.coordinator.async_request_refresh()

    @property
    def current_temperature(self):
        return self.coordinator.data['room_temperature']

    @property
    def target_temperature(self):
        return self.coordinator.data['target_temperature']

    @property
    def preset_mode(self):
        return PRESET_AWAY if self.coordinator.data['source'] == 'pause' else PRESET_NONE
        
    @property
    def hvac_mode(self):
        """Return current operation."""
        if self.coordinator.data['source'] == 'remote' or self.coordinator.data['source'] == 'manual':
            return HVAC_MODE_HEAT
        elif self.coordinator.data['source'] == 'schedule' or self.coordinator.data['source'] == 'exception':
            return HVAC_MODE_AUTO

    @property
    def hvac_action(self):
        """Return the current running hvac operation if supported."""
        if self.coordinator.data.get('ot'):
            # Find current HVAC action
            if self.coordinator.data['ot']['readable']['CH_enabled']:
                return CURRENT_HVAC_HEAT
            elif self.coordinator.data['ot']['readable']['Cooling_enabled']:
                return CURRENT_HVAC_COOL
            else:
                return CURRENT_HVAC_IDLE

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        if hvac_mode == HVAC_MODE_AUTO:
            await self.hass.async_add_executor_job(self.coordinator.client.pause_thermostat, False)
        elif (hvac_mode == HVAC_MODE_HEAT) or (hvac_mode == HVAC_MODE_COOL):
            await self.hass.async_add_executor_job(self.coordinator.client.set_target_temperature, self.target_temperature)
        await self.coordinator.async_request_refresh()

    # Define service-calls
    async def add_exception(self,start_day, start_month, start_year, start_time, end_day, end_month, end_year, end_time, program):
        """Add exceptions to the current list."""
        exceptions = self._exceptions

        new_exception = {"start": [start_year, start_month-1, start_day, start_time.hour, round(start_time.minute/15)*15],
                        "end": [end_year, end_month-1, end_day, end_time.hour, round(end_time.minute/15)*15],
                        "temperature": program}

        exceptions.append(new_exception)

        await self.hass.async_add_executor_job(self.coordinator.client.set_exceptions, exceptions)
        await self.coordinator.async_request_refresh()

    async def clear_exceptions(self):
        """Clear all exceptions."""
        await self.hass.async_add_executor_job(self.coordinator.client.set_exceptions, [])
        await self.coordinator.async_request_refresh()

            

