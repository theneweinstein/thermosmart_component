"""API for Thermosmart bound to Home Assistant OAuth."""

from thermosmart_hass import thermosmart_api

from homeassistant import config_entries, core
from homeassistant.helpers import config_entry_oauth2_flow


class ConfigEntryThermosmartApi(thermosmart_api.ThermosmartApi):
    """Provide a Somfy API tied into an OAuth2 based config entry."""

    def __init__(
        self,
        hass: core.HomeAssistant,
        config_entry: config_entries.ConfigEntry,
        implementation: config_entry_oauth2_flow.AbstractOAuth2Implementation,
    ):
        """Initialize the Config Entry Somfy API."""
        self.hass = hass
        self.config_entry = config_entry
        self.session = config_entry_oauth2_flow.OAuth2Session(
            hass, config_entry, implementation
        )
        super().__init__(None, None, token=self.session.token)