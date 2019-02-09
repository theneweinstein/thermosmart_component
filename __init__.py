"""
Support for the Thermosmart thermostat.

For more details about this component, please refer to the documentation at
??
"""
import logging
from datetime import timedelta

from aiohttp.web import json_response
import voluptuous as vol

from homeassistant.components.http import HomeAssistantView
from homeassistant.util import Throttle
from homeassistant.helpers import discovery
import homeassistant.helpers.config_validation as cv
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.auth.util import generate_secret

REQUIREMENTS = ['thermosmart_hass==0.2.0']

DEPENDENCIES = ['webhook']

_LOGGER = logging.getLogger(__name__)

CONF_CACHE_PATH = 'cache_path'

AUTH_CALLBACK_NAME = 'api:thermosmart'
AUTH_CALLBACK_PATH = '/api/thermosmart'

CONFIGURATOR_DESCRIPTION = 'To link your Thermosmart account, ' \
                           'click the link, login, and authorize:'
CONFIGURATOR_LINK_NAME = 'Link Thermosmart account'
CONFIGURATOR_SUBMIT_CAPTION = 'I authorized successfully'

WEBHOOKS_SUBSCRIBERS = []

UPDATE_TIME = timedelta(seconds=30)

DEFAULT_CACHE_PATH = '.thermosmart-token-cache'
DEFAULT_NAME = 'Thermosmart'
DEPENDENCIES = ['http']
DOMAIN = 'thermosmart'
THERMOSMART_DEVICE = 'thermosmart_device'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Optional(CONF_NAME): cv.string
    })
}, extra=vol.ALLOW_EXTRA)

def request_configuration(hass, config, oauth):
    """Request Thermomosmart autorization"""
    configurator = hass.components.configurator
    hass.data[DOMAIN] = configurator.request_config(
        DEFAULT_NAME, lambda _: None,
        link_name=CONFIGURATOR_LINK_NAME,
        link_url=oauth.get_authorize_url(),
        description=CONFIGURATOR_DESCRIPTION,
        submit_caption=CONFIGURATOR_SUBMIT_CAPTION)

def setup(hass, config):
    """Set up the Thermosmart."""
    from thermosmart_hass import oauth2 as oauth2
    
    callback_url = '{}{}'.format(hass.config.api.base_url, AUTH_CALLBACK_PATH)
    cache = config.get(CONF_CACHE_PATH, hass.config.path(DEFAULT_CACHE_PATH))
    oauth = oauth2.ThermosmartOAuth(callback_url, cache_path=cache)
    token_info = oauth.get_cached_token()
    if not token_info:
        _LOGGER.info("no token; requesting authorization")
        hass.http.register_view(ThermosmartAuthCallbackView(
            config, oauth))
        request_configuration(hass, config, oauth)
        return
    if hass.data.get(DOMAIN):
        configurator = hass.components.configurator
        configurator.request_done(hass.data.get(DOMAIN))
        del hass.data[DOMAIN]

    hass.data[DOMAIN] = ThermoSmartData(token_info)

    discovery.load_platform(hass, 'climate', DOMAIN, {}, config)
    #discovery.load_platform(hass, 'sensor', DOMAIN, {}, config)

    #webhook_id = generate_secret(entropy=32)
    #_LOGGER.log('Webhook_id: '+ webhook_id)
    #webhook_id = 'abdefg1234'
    #hass.data[DOMAIN].webhook(webhook_id)
    #hass.components.webhook.async_register(DOMAIN, 'Thermosmart', webhook_id, handle_webhook)

    return True

async def handle_webhook(hass, webhook_id, request):
    """Handle a thermosmart webhook message."""
    message = await request.json()

    _LOGGER.debug(message)
    # Callback to HA registered components.
    for subscriber in WEBHOOKS_SUBSCRIBERS:
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
        import thermosmart_hass as tsmart
        self.thermosmart = tsmart.ThermoSmart(token=token_info['access_token'])

    @Throttle(UPDATE_TIME)
    def update(self):
        """Get the latest update from Thermosmart."""
        self.thermosmart.update()
