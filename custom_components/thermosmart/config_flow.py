"""Config flow for Thermosmart."""
from __future__ import annotations
import logging
from typing import Any
import voluptuous as vol

from thermosmart_hass import thermosmart_api as Api

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, CONN_CLASS_CLOUD_POLL
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_entry_oauth2_flow

from .const import DOMAIN, CONF_WEBHOOK, CONF_WEBHOOK_OLD

_LOGGER = logging.getLogger(__name__)

class ThermosmartFlowHandler(config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN):
    """Handle an Thermosmart config flow."""

    DOMAIN = DOMAIN
    VERSION = 1
    CONNECTION_CLASS = CONN_CLASS_CLOUD_POLL

    @property
    def logger(self) -> logging.Logger:
        """Return logger."""
        return logging.getLogger(__name__)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> ThermosmartOptionsFlow:
        """Thermosmart options callback."""
        return ThermosmartOptionsFlow(config_entry)

    async def async_oauth_create_entry(self, data: dict[str, Any]) -> FlowResult:
        """Create an entry for thermosmart."""
        thermosmart = Api.ThermosmartApi(token=data["token"])

        try:
            id =  await self.hass.async_add_executor_job(thermosmart.get_thermostat_id)
        except Exception:
            return self.async_abort(reason="connection_error")

        data["id"] = id
        data["name"] = "Thermosmart"

        await self.async_set_unique_id(id)

        return self.async_create_entry(title='Thermosmart', data=data)

class ThermosmartOptionsFlow(config_entries.OptionsFlow):
    """Config flow options for Somneo."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialze the Thermosmart options flow."""
        self.entry = entry
        self.webhook = entry.options.get(CONF_WEBHOOK, None)
        _LOGGER.debug(self.webhook)

    async def async_step_init(self, _user_input=None):
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initialized by the user."""
        if user_input is not None:
            data = user_input
            data[CONF_WEBHOOK_OLD] = self.webhook
            data[CONF_WEBHOOK] = None if data[CONF_WEBHOOK] == 'None' else data[CONF_WEBHOOK]
            return self.async_create_entry(title="Thermosmart", data=data)

        return self.async_show_form(
            step_id="user", 
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_WEBHOOK, default=self.webhook): str, 
                }
            )
        ) 