"""
Support for the Thermosmart.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/thermosmart/
"""
from datetime import timedelta
import logging

import voluptuous as vol

from homeassistant.core import callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_CLIENT_ID, CONF_CLIENT_SECRET, CONF_WEBHOOK_ID, EVENT_HOMEASSISTANT_STOP
from homeassistant.helpers import (
    config_entry_oauth2_flow,
    config_validation as cv,
)
from homeassistant.components.webhook import (
    async_register as webhook_register,
    async_unregister as webhook_unregister,
)

from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.util import Throttle

from thermosmart_hass import thermosmart_api
from .const import DOMAIN, API, PLATFORMS, DEVICE, CONFIG
from .oauth2 import register_oauth2_implementations

_LOGGER = logging.getLogger(__name__)

UPDATE_TIME = timedelta(seconds=30)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_CLIENT_ID): cv.string,
        vol.Required(CONF_CLIENT_SECRET): cv.string,
        vol.Optional(CONF_NAME): cv.string,
        vol.Optional(CONF_WEBHOOK_ID): cv.string
    })
}, extra=vol.ALLOW_EXTRA)

WEBHOOK_SUBSCRIBERS = []

async def async_setup(hass, config):
    """Set up the Thermosmart component."""
    if DOMAIN not in config:
        return True

    hass.data[DOMAIN] = {}
    hass.data[DOMAIN][CONFIG] = config[DOMAIN]

    return True

async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry):
    """Set up Thermosmart from a config entry."""

    implementation = await config_entry_oauth2_flow.async_get_config_entry_implementation(
        hass, entry
    )

    session = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)

    thermo_api = thermosmart_api.ThermosmartApi(token=session.token)
    thermo_id =  await hass.async_add_executor_job(thermo_api.get_thermostat_id)
    
    hass.data[DOMAIN][entry.entry_id] = {
        API: thermo_api,
        DEVICE: ThermosmartDevice(hass, entry.entry_id, thermo_api, thermo_id),
    }

    if CONF_WEBHOOK_ID in hass.data[DOMAIN][CONFIG]:
        webhook_id = hass.data[DOMAIN][CONFIG][CONF_WEBHOOK_ID]
        do_update = False
    else:
        webhook_id = None
        do_update = True 
    hass.config_entries.async_update_entry(
        entry, data={**entry.data, CONF_WEBHOOK_ID: webhook_id, "do_update": do_update}
    )

    # Register a webhook
    if entry.data[CONF_WEBHOOK_ID]:
        webhook_id = entry.data[CONF_WEBHOOK_ID]

        webhook_register(
            hass,
            DOMAIN,
            "Thermosmart",
            webhook_id,
            hass.data[DOMAIN][entry.entry_id][DEVICE].handle_webhook,
        )

        async def unregister_webhook(event):
            _LOGGER.debug("Unregister Thermosmart webhook (%s)", entry.data[CONF_WEBHOOK_ID])
            webhook_unregister(hass, entry.data[CONF_WEBHOOK_ID])

        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, unregister_webhook)

    await hass.data[DOMAIN][entry.entry_id][DEVICE].update()

    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )

    return True


class ThermosmartDevice:
    """Get the latest data from Thermosmart."""

    def __init__(self, hass, entry_id, api, device_id):
        """Initialize."""
        import thermosmart_hass as tsmart
        self._hass = hass
        self._entry_id = entry_id
        self.thermosmart = tsmart.ThermosmartDevice(api=api, device_id = device_id)

    @Throttle(UPDATE_TIME)
    async def update(self):
        """Get the latest update from Thermosmart."""
        await self._hass.async_add_executor_job(self.thermosmart.get_thermostat)

    async def handle_webhook(self, hass: HomeAssistantType, webhook_id: str, request) -> None:
        """Handle webhook callback."""
        try:
            data = await request.json()
        except ValueError:
            return

        _LOGGER.debug("Got webhook data: %s", data)

        # Webhook expired notification
        if data.get("code") == 510:
            return

        try:
            await self._hass.async_add_executor_job(self.thermosmart.process_webhook, data)
            for subscriber in WEBHOOK_SUBSCRIBERS:
                subscriber.webhook_update()
        except:
            _LOGGER.error("Could not process data received from Thermosmart webhook")

class ThermosmartEntity(Entity):
    """Generic entity for thermosmart."""
    def __init__(self, device, do_update = True):
        """Initialize the Somfy device."""
        self._device = device
        self._do_update = do_update
        self._force_update = False
        self._thermosmart = self._device.thermosmart
        self._client_id = self._thermosmart.device_id

    @callback
    def async_update_callback(self, reason):
        """Update the device's state."""
        self.async_schedule_update_ha_state()

    async def async_update(self):
        """Get the latest data and updates the states."""
        if self._do_update:
            await self._device.update()
        if self._force_update:
            await self._device.update(no_throttle=True)
            self._force_update = False

    def webhook_update(self):
        """Update entity when webhook arrived.""" 
        self.async_schedule_update_ha_state()

