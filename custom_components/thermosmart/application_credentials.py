"""Application credentials platform for Thermosmart."""
from typing import cast

from homeassistant.components.application_credentials import AuthImplementation, AuthorizationServer, ClientCredential
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession


class OAuth2Impl(AuthImplementation):
    """Custom OAuth2 implementation for thermomsmart."""

    async def _token_request(self, data: dict) -> dict:
        """Make a token request."""
        session = async_get_clientsession(self.hass)

        data["client_id"] = self.client_id

        if self.client_secret is not None:
            data["client_secret"] = self.client_secret

        resp = await session.post(self.token_url, data=data)
        resp.raise_for_status()
        resp_json = cast(dict, await resp.json())
        # No expires_in supplied as the token never expires!
        # Set to 100 years.
        resp_json["expires_in"] = float(3.1556926E9)
        return resp_json

async def async_get_auth_implementation(
    hass: HomeAssistant, auth_domain: str, credential: ClientCredential
) -> config_entry_oauth2_flow.AbstractOAuth2Implementation:
    """Return auth implementation for a custom auth implementation."""
    return OAuth2Impl(
        hass,
        auth_domain,
        credential,
        AuthorizationServer(
            authorize_url="https://api.thermosmart.com/oauth2/authorize",
            token_url="https://api.thermosmart.com/oauth2/token",
        )
    )