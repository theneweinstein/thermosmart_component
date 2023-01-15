"""
Support for the Thermosmart.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/thermosmart/
"""
from datetime import timedelta
import logging
from typing import Any

from homeassistant.components.webhook import (
    async_register as webhook_register,
    async_unregister as webhook_unregister,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.config_entry_oauth2_flow import (
    OAuth2Session,
    async_get_config_entry_implementation,
)
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from homeassistant.helpers.typing import HomeAssistantType

from thermosmart_hass import thermosmart_api as Api
from thermosmart_hass import ThermosmartDevice as Thermosmart

from .const import DOMAIN, CONF_WEBHOOK, CONF_WEBHOOK_OLD

PLATFORMS = [Platform.CLIMATE, Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=300)

async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry) -> bool:
    """Set up Thermosmart from a config entry."""

    implementation = await async_get_config_entry_implementation(hass, entry)
    session = OAuth2Session(hass, entry, implementation)

    api = Api.ThermosmartApi(token=session.token)
    device_id =  await hass.async_add_executor_job(api.get_thermostat_id)
    thermosmart = Thermosmart(api = api, device_id = device_id)

    coordinator = ThermosmartCoordinator(
        hass,
        thermosmart,
        entry.options.get(CONF_WEBHOOK, None),
        entry.options.get(CONF_WEBHOOK_OLD, None)
    )
    entry.async_on_unload(entry.add_update_listener(update_listener))
    
    await coordinator.async_config_entry_first_refresh()
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    if coordinator.data.get('ot'):
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    else:
        await hass.config_entries.async_forward_entry_setups(entry, [Platform.CLIMATE])

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    )

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)

class ThermosmartCoordinator(DataUpdateCoordinator[None]):
    """Representation of a Somneo Coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: Thermosmart,
        webhook: str | None = None,
        old_webhook: str | None = None,
    ) -> None:
        """Initialize Thermosmart coordinator."""
        
        self.client = client
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=None if webhook else SCAN_INTERVAL,
            update_method=self._update,
            request_refresh_debouncer=Debouncer(
                hass, _LOGGER, cooldown=1.0, immediate=False
            ),
        )

        # Unregister old webhook
        _LOGGER.debug('The old webhook is: %s', old_webhook)
        if old_webhook:
            _LOGGER.debug("Unregister Thermosmart old webhook (%s)", old_webhook)
            webhook_unregister(hass, old_webhook)

        # Register a webhook
        _LOGGER.debug('The new webhook is: %s', webhook)
        if webhook:
            _LOGGER.debug("Register Thermosmart new webhook (%s)", webhook)
            webhook_register(
                hass,
                DOMAIN,
                "Thermosmart",
                webhook,
                self.handle_webhook,
            )

            async def unregister_webhook(event):
                _LOGGER.debug("Unregister Thermosmart webhook (%s)", webhook)
                webhook_unregister(hass, webhook)

            hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, unregister_webhook)
            

    async def _update(self):
        """Fetch latest data."""
        await self.hass.async_add_executor_job(self.client.get_thermostat)
        return self.client.data

    async def handle_webhook(self, hass: HomeAssistant, webhook_id: str, request) -> None:
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
            await hass.async_add_executor_job(self.client.process_webhook, data)
        except:
            _LOGGER.error("Could not process data received from Thermosmart webhook")

        self.async_set_updated_data(self.client.data)

