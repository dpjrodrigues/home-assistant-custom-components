"""
Support for Estradas.pt Cameras.
Based on https://home-assistant.io/components/camera.ffmpeg/
"""
import asyncio
import logging
import async_timeout
import voluptuous as vol

from datetime import datetime, timedelta
from homeassistant.util import Throttle
from homeassistant.const import CONF_NAME
from homeassistant.components.ffmpeg.camera import FFmpegCamera, PLATFORM_SCHEMA
from homeassistant.components.ffmpeg import (
    DATA_FFMPEG, CONF_INPUT, CONF_EXTRA_ARGUMENTS)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import (
    async_aiohttp_proxy_stream, async_get_clientsession)

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = 'estradas_pt'
IMAGE_REFRESH = 'image_refresh_in_min'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_INPUT): cv.string,
    vol.Optional(CONF_EXTRA_ARGUMENTS): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(IMAGE_REFRESH, default=5): cv.positive_int,
})

SCAN_INTERVAL = timedelta(minutes=1)


async def async_setup_platform(hass, config, async_add_entities,
                               discovery_info=None):
    """Set up a FFmpeg camera."""

    websession = async_get_clientsession(hass)

    from pyEstradasPT import Cameras
    #with async_timeout.timeout(10, loop=hass.loop):
    cams = await Cameras.get(websession) 
       
    url = await cams.UrlByCameraName(config.get(CONF_INPUT))      
    
    async_add_entities([EstradasCamera(hass, config, url.replace(".3gp?token=", ".webm?token="))])

class EstradasCamera(FFmpegCamera):
    """An implementation of an FFmpeg camera."""

    def __init__(self, hass, config, url):
        """Initialize a Estradas camera."""
        super().__init__(hass,config)

        self._manager = hass.data[DATA_FFMPEG]
        self._name = config.get(CONF_NAME)
        self._cam_name = config.get(CONF_INPUT)
        self._input = url
        self._token_changed = True
        self._extra_arguments = config.get(CONF_EXTRA_ARGUMENTS)
        self._last_update = datetime.now()
        self._last_image = None
        self._image_refresh = config.get(IMAGE_REFRESH)
        self._last_image_refresh = datetime.now()

    async def async_camera_image(self):
        """Return a still image response from the camera."""
        await self.async_update()
        
        d = (datetime.now()-self._last_image_refresh)
        ds = d.days * 86400 + d.seconds

        if (self._last_image == None or len(self._last_image) < 5 or ds >= self._image_refresh*60 ):
            self._last_image = await super().async_camera_image()
            self._last_image_refresh = datetime.now()

        return self._last_image

    async def handle_async_mjpeg_stream(self, request):
        """Generate an HTTP MJPEG stream from the camera."""
        await self.async_update()
        await super().handle_async_mjpeg_stream(request)

    @property
    def device_state_attributes(self):
        """Return other details about the sensor state."""
        attrs = {}
        attrs["camera_name"] = self._cam_name
        attrs["last_update"] = self._last_update
        attrs["token_changed"] = self._token_changed
        attrs["url"] = self._input
        attrs["image_refresh_in_min"] = self._image_refresh
        attrs["last_image_refresh"] = self._last_image_refresh
        return attrs 

    @Throttle(SCAN_INTERVAL)
    async def async_update(self):
        """Update the cam."""

        websession = async_get_clientsession(self.hass)
        
        from pyEstradasPT import Cameras
        #with async_timeout.timeout(10, loop=hass.loop):
        cams = await Cameras.get(websession) 
       
        url = await cams.UrlByCameraName(self._cam_name)
        url = url.replace(".3gp?token=", ".webm?token=")

        if url == self._input:
            self._token_changed = False
        else:
            self._token_changed = True
            self._input = url

        self._last_update = datetime.now()
        self.schedule_update_ha_state()