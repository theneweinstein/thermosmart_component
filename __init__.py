"""
Support for the Thermosmart.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/thermosmart/
"""
from datetime import timedelta
import logging

from aiohttp.web import json_response
import voluptuous as vol

from homeassistant.components.http import HomeAssistantView
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import discovery
import homeassistant.helpers.config_validation as cv
from homeassistant.util import Throttle

REQUIREMENTS = ['thermosmart_hass==0.4.0']

DEPENDENCIES = ['http', 'webhook']

_LOGGER = logging.getLogger(__name__)

AUTH_CALLBACK_NAME = 'api:thermosmart'
AUTH_CALLBACK_PATH = '/api/thermosmart'
AUTH_DATA = 'thermosmart_auth'

CONF_API_CLIENT_ID = 'client_id'
CONF_API_CLIENT_SECRET = 'client_secret'
CONF_WEBHOOK = 'webhook'

CONFIGURATOR_DESCRIPTION = "To link your Thermosmart account, " \
                           "click the link, login, and authorize:"
CONFIGURATOR_LINK_NAME = "Link Thermosmart account"
CONFIGURATOR_SUBMIT_CAPTION = "I authorized successfully"

DEFAULT_CACHE_PATH = '.thermosmart-token-cache'
DEFAULT_NAME = 'Thermosmart'

DOMAIN = 'thermosmart'

UPDATE_TIME = timedelta(seconds=30)

WEBHOOK_SUBSCRIBERS  = []

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_API_CLIENT_ID): cv.string,
        vol.Required(CONF_API_CLIENT_SECRET): cv.string,
        vol.Optional(CONF_NAME): cv.string,
        vol.Optional(CONF_WEBHOOK): cv.string
    })
}, extra=vol.ALLOW_EXTRA)


def request_configuration(hass, config, oauth):
    """Request Thermomosmart autorization."""
    configurator = hass.components.configurator
    hass.data[AUTH_DATA] = configurator.request_config(
        DEFAULT_NAME, lambda _: None,
        link_name=CONFIGURATOR_LINK_NAME,
        link_url=oauth.get_authorize_url(),
        description=CONFIGURATOR_DESCRIPTION,
        submit_caption=CONFIGURATOR_SUBMIT_CAPTION)


def setup(hass, config):
    """Set up the Thermosmart."""
    from thermosmart_hass import oauth2

    callback_url = '{}{}'.format(hass.config.api.base_url, AUTH_CALLBACK_PATH)
    client_id = config[DOMAIN].get(CONF_API_CLIENT_ID)
    client_secret = config[DOMAIN].get(CONF_API_CLIENT_SECRET)
    cache = hass.config.path(DEFAULT_CACHE_PATH)
    oauth = oauth2.ThermosmartOAuth(
        client_id, client_secret,
        callback_url, cache_path=cache
    )
    token_info = oauth.get_cached_token()
    if not token_info:
        _LOGGER.info("No token, requesting authorization.")
        hass.http.register_view(ThermosmartAuthCallbackView(
            config, oauth))
        request_configuration(hass, config, oauth)
        return True
    if hass.data.get(AUTH_DATA):
        _LOGGER.info("Token found.")
        configurator = hass.components.configurator
        configurator.request_done(hass.data.get(AUTH_DATA))
        del hass.data[AUTH_DATA]

    hass.data[DOMAIN] = ThermoSmartData(token_info)

    call_update = True
    webhook_id = config[DOMAIN].get(CONF_WEBHOOK, None)
    if not webhook_id:
        hass.data[DOMAIN].webhook(webhook_id)
        hass.components.webhook.async_register(DOMAIN, 'Thermosmart', 
            webhook_id, handle_webhook)
        call_update = False

    discovery.load_platform(
        hass, 'climate', DOMAIN,
        {CONF_NAME: config[DOMAIN].get(CONF_NAME, None),
        'update': call_update}, config
    )

    _LOGGER.info(hass.data[DOMAIN].thermosmart.latest_update)

    if hass.data[DOMAIN].thermosmart.opentherm():
        discovery.load_platform(
            hass, 'sensor', DOMAIN,
            {CONF_NAME: config[DOMAIN].get(CONF_NAME, None),
            'update': call_update}, config
        )

    return True


async def handle_webhook(hass, webhook_id, request):
    """Hanlde a thermosmart webhook message."""
    message = await request.json()

    _LOGGER.debug(message)
    # Callback to HA registered components.
    for subscriber in WEBHOOK_SUBSCRIBERS:
        subscriber.process_webhook(message)

    return json_response([])


class ThermosmartAuthCallbackView(HomeAssistantView):
    """Thermosmart Authorization Callback View."""

    requires_auth = False
    url = AUTH_CALLBACK_PATH
    name = AUTH_CALLBACK_NAME

    def __init__(self, config, oauth):
        """Initialize."""
        self.config = config
        self.oauth = oauth

    @callback
    def get(self, request):
        """Receive authorization token."""
        hass = request.app['hass']
        self.oauth.get_access_token(request.query['code'])
        hass.async_add_job(
            setup, hass, self.config)


class ThermoSmartData:
    """Get the latest data from Thermosmart."""

    def __init__(self, token_info):
        """Initialize."""
        import thermosmart_hass as tsmart
        self.thermosmart = tsmart.ThermoSmart(token=token_info['access_token'])

    @Throttle(UPDATE_TIME)
    def update(self):
        """Get the latest update from Thermosmart."""
        self.thermosmart.update()
