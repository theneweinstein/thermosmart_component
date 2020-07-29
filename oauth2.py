"""OAuth2 implementations for Thermosmart."""
import logging
from typing import Any, Optional, cast

from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from . import config_flow
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def register_oauth2_implementations(
    hass: HomeAssistant, client_id: str, client_secret: str
) -> None:
    """Register Thermosmart OAuth2 implementations."""
    config_flow.ThermosmartFlowHandler.async_register_implementation(
        hass,
        ThermosmartLocalOAuth2Implementation(
            hass,
            client_id=client_id,
            client_secret=client_secret,
            name="Thermosmart",
        ),
    )


class ThermosmartLocalOAuth2Implementation(config_entry_oauth2_flow.LocalOAuth2Implementation):
    """Local OAuth2 implementation for Thermosmart."""

    def __init__(
        self,
        hass: HomeAssistant,
        client_id: str,
        client_secret: str,
        name: str,
    ):
        """Local Thermosmart Oauth Implementation."""
        self._name = name

        super().__init__(
            hass=hass,
            domain=DOMAIN,
            client_id=client_id,
            client_secret=client_secret,
            authorize_url='https://api.thermosmart.com/oauth2/authorize',
            token_url='https://api.thermosmart.com/oauth2/token',
        )

    @property
    def name(self) -> str:
        """Name of the implementation."""
        return f"{self._name}"


    async def _token_request(self, data: dict) -> dict:
        """Make a token request."""
        session = async_get_clientsession(self.hass)

        data["client_id"] = self.client_id

        if self.client_secret is not None:
            data["client_secret"] = self.client_secret

        _LOGGER.warn(data)

        resp = await session.post(self.token_url, data=data)
        resp.raise_for_status()
        resp_json = cast(dict, await resp.json())
        # No expires_in supplied as the token never expires!
        # Set to 100 years.
        resp_json["expires_in"] = float(3.1556926E9)
        return resp_json