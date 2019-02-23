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
from homeassistant.components.camera import Camera, PLATFORM_SCHEMA
from homeassistant.components.ffmpeg import (
    DATA_FFMPEG, CONF_INPUT, CONF_EXTRA_ARGUMENTS)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import (
    async_aiohttp_proxy_stream, async_get_clientsession)

_LOGGER = logging.getLogger(__name__)

REQUIREMENTS = ['pyEstradasPT==1.0.2']
DEPENDENCIES = ['ffmpeg']
DEFAULT_NAME = 'estradas_pt'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_INPUT): cv.string,
    vol.Optional(CONF_EXTRA_ARGUMENTS): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})

SCAN_INTERVAL = timedelta(minutes=1)


async def async_setup_platform(hass, config, async_add_entities,
                               discovery_info=None):
    """Set up a FFmpeg camera."""

    websession = async_get_clientsession(hass)

    from pyEstradasPT import Cameras
#    with async_timeout.timeout(10, loop=hass.loop):
    cams = await Cameras.get(websession) 
       
    url = await cams.UrlByCameraName(config.get(CONF_INPUT))      

    async_add_entities([FFmpegCamera(hass, config, url.replace(".3gp?token=", ".webm?token="))])



class FFmpegCamera(Camera):
    """An implementation of an FFmpeg camera."""

    def __init__(self, hass, config, url):
        """Initialize a FFmpeg camera."""
        super().__init__()

        self._manager = hass.data[DATA_FFMPEG]
        self._name = config.get(CONF_NAME)
        self._cam_name = config.get(CONF_INPUT)
        self._input = url
        self._token_changed = True
        self._extra_arguments = config.get(CONF_EXTRA_ARGUMENTS)
        self._last_update = datetime.now()


    async def async_camera_image(self):
        """Return a still image response from the camera."""
        from haffmpeg import ImageFrame, IMAGE_JPEG
        ffmpeg = ImageFrame(self._manager.binary, loop=self.hass.loop)

        image = await asyncio.shield(ffmpeg.get_image(
            self._input, output_format=IMAGE_JPEG,
            extra_cmd=self._extra_arguments), loop=self.hass.loop)
        return image

    async def handle_async_mjpeg_stream(self, request):
        """Generate an HTTP MJPEG stream from the camera."""
        from haffmpeg import CameraMjpeg

        await self.async_update()
        stream = CameraMjpeg(self._manager.binary, loop=self.hass.loop)
        await stream.open_camera(
            self._input, extra_cmd=self._extra_arguments)

        try:
            return await async_aiohttp_proxy_stream(
                self.hass, request, stream,
                self._manager.ffmpeg_stream_content_type)
        finally:
            await stream.close()

    @property
    def name(self):
        """Return the name of this camera."""
        return self._name
    
    @property
    def device_state_attributes(self):
        """Return other details about the sensor state."""
        attrs = {}
        attrs["camera_name"] = self._cam_name
        attrs["last_update"] = self._last_update
        attrs["token_changed"] = self._token_changed
        attrs["url"] = self._input
        return attrs 

    @Throttle(SCAN_INTERVAL)
    async def async_update(self):
        """Update the cam."""

        websession = async_get_clientsession(self.hass)
        
        from pyEstradasPT import Cameras
        #    with async_timeout.timeout(10, loop=hass.loop):
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