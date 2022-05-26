"""Application credentials platform for Thermosmart."""

from homeassistant.components.application_credentials import AuthorizationServer
from homeassistant.core import HomeAssistant


async def async_get_authorization_server(hass: HomeAssistant) -> AuthorizationServer:
    """Return authorization server."""
    return AuthorizationServer(
        authorize_url="https://api.thermosmart.com/oauth2/authorize",
        token_url="https://api.thermosmart.com/oauth2/token",
    )