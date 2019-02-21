import logging
import async_timeout
import urllib.request
import time
import re
from datetime import datetime, timedelta

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.util import Throttle
from homeassistant.helpers.aiohttp_client import async_get_clientsession

REQUIREMENTS = ['pyEstradasPT==1.0.2']

_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = "Powered by estradas.pt"
CONF_CAMERA = 'camera'
SCAN_INTERVAL = timedelta(minutes=5)

DOMAIN = 'estradaspt'

PLATFORM_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({ 
        vol.Required(CONF_CAMERA): vol.All(cv.ensure_list, [cv.string])
    })
}, extra=vol.ALLOW_EXTRA)

async def async_setup(hass, config):
    """Set up the Camera component"""
    from pyEstradasPT import Cameras

    websession = async_get_clientsession(hass)
    with async_timeout.timeout(10, loop=hass.loop):
        cameras = await Cameras.get(websession) 

    component = EntityComponent(_LOGGER, DOMAIN, hass)

    entities = []
    conf = config.get(DOMAIN)
       
    for camera in conf[0].get(CONF_CAMERA):
        url = await cameras.UrlByCameraName(camera)
        file_name='/config/www/'+re.sub('[^A-Za-z0-9]+', '', camera)+'.3gp'
        entities.append(CameraVideo(camera,file_name,url))
        await store_cam_video(url, file_name)

    await component.async_add_entities(entities)
   
    return True


async def store_cam_video(url, file_name):
    """Save camera 3gp """
    urllib.request.urlretrieve(url, file_name)



class CameraVideo(Entity):
    """Sensor that reads and stores the camera video."""

    ICON = 'mdi:webcam'

    def __init__(self, name, file_name, url):
        """Initialize the component."""
        self._name = name
        self._file_name = file_name
        self._url = url
        self._last_update = datetime.now()
        
    @property
    def name(self):
        """Return the name of the component."""
        return self._name

    @property
    def file_name(self):
        """Return the file_name where camara was saved."""
        return self._file_name

    @property
    def url(self):
        """Return the url of the camera."""
        return self._file_name

    @property
    def last_update(self):
        """Return the date when camera url refreshed."""
        return self._last_update

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return self.ICON

    @property
    def device_state_attributes(self):
        """Return other details about the sensor state."""
        attrs = {}
        attrs["name"] = self._name
        attrs["last_update"] = self._last_update
        attrs["file_name"] = self._file_name
        attrs["url"] = self._url
        return attrs 

    @Throttle(SCAN_INTERVAL)
    async def async_update(self):
        """Update the cam."""
        await store_cam_video(self._url, self._file_name)

        self._last_update = datetime.now()
        self.schedule_update_ha_state()
    