import logging
import async_timeout
import urllib.request
import time
import re
import os
from datetime import datetime, timedelta
from selenium import webdriver

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.util import Throttle
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from selenium.webdriver.firefox.options import Options

REQUIREMENTS = ['selenium==3.141.0']

_LOGGER = logging.getLogger(__name__)

USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) ' \
             'Chrome/41.0.2228.0 Safari/537.36'
CHROME_WEBDRIVER_ARGS = [
    '--headless', '--user-agent={}'.format(USER_AGENT), '--disable-extensions',
    '--disable-gpu', '--no-sandbox'
]
FIREFOXOPTIONS = Options()
FIREFOXOPTIONS.add_argument("--headless")


DRIVERPATH = '/usr/bin/chromedriver'
#DRIVERPATH = '/usr/bin/phantomjs'
#DRIVERPATH = '/usr/bin/geckodriver'


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
    component = EntityComponent(_LOGGER, DOMAIN, hass)
           
    entities = []
    conf = config.get(DOMAIN)
       
    for camera in conf[0].get(CONF_CAMERA):

        if os.path.exists(DRIVERPATH):
            await store_cam_video(camera, '/config/www/'+re.sub('[^A-Za-z0-9]+', '', camera)+'.3gp')
            entities.append(CameraVideo(camera,'/config/www/'+re.sub('[^A-Za-z0-9]+', '', camera)+'.3gp','On'))
        else:
            _LOGGER.warning('Chromedriver is still being installed. If cameras are not working wait for the "estradaspt" entities to be updated of force the update')
            entities.append(CameraVideo(camera,'/config/www/'+re.sub('[^A-Za-z0-9]+', '', camera)+'.3gp','Not loaded yet'))

    await component.async_add_entities(entities)
   
    return True


async def store_cam_video(camera_name, file_name):
    """Get the camera url"""

    chrome_options = webdriver.ChromeOptions()
    for arg in CHROME_WEBDRIVER_ARGS:
        chrome_options.add_argument(arg)
    driver = webdriver.Chrome(chrome_options=chrome_options)
#    driver = webdriver.PhantomJS()
#    driver = webdriver.Firefox(firefox_options=FIREFOXOPTIONS)

    driver.get('http://www.estradas.pt/index')
    link = driver.find_element_by_css_selector("a[href*='"+camera_name+"']")
     
    pattern = re.compile(r'''((?:[^,"']|"[^"]*"|'[^']*')+)''')
    url = pattern.split(link.get_attribute("href"))[3]
        
    driver.quit()

    urllib.request.urlretrieve(url[1:-1], file_name)



class CameraVideo(Entity):
    """Sensor that reads and stores the camera video."""

    ICON = 'mdi:webcam'

    def __init__(self, name, file_name, state):
        """Initialize the sensor."""
        self._name = name
        self._state = state
        self._file_name = file_name
        self._last_update = datetime.now()

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def file_name(self):
        """Return the state of the sensor."""
        return self._file_name

    @property
    def last_update(self):
        """Return the state of the sensor."""
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
        return attrs 

    @Throttle(SCAN_INTERVAL)
    async def async_update(self):
        """Update the sensor."""
#        with async_timeout.timeout(10, loop=self.hass.loop):
        if os.path.exists(DRIVERPATH):
            await store_cam_video(self._name, self._file_name)
            self._state = 'On'
        else:
            self._state = 'Not loaded yet'
        self._last_update = datetime.now()
        self.schedule_update_ha_state()
    