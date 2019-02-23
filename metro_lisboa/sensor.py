"""
Support for UnderLX Metro service (https://github.com/underlx/disturbancesmlx)

For more details about this platform, please refer to the documentation at
https://github.com/dpjrodrigues/ha_custom_components
"""

import logging
import async_timeout
from datetime import timedelta

import voluptuous as vol
import requests

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
from homeassistant.helpers.aiohttp_client import async_get_clientsession

REQUIREMENTS = ['pyUnderLX==1.0.1']

_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = "Powered by UnderLX"
CONF_LINE = 'line'
SCAN_INTERVAL = timedelta(minutes=5)

METRO_LINES = {
    "Linha Azul": 'pt-ml-azul',
    "Linha Verde": 'pt-ml-verde',
    "Linha Vermelha": 'pt-ml-vermelha',
    "Linha Amarela": 'pt-ml-amarela',
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_LINE):
        vol.All(cv.ensure_list, [vol.In(list(METRO_LINES.keys()))]),
})


async def async_setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Tube sensor."""

    from pyUnderLX import Occurrences

    websession = async_get_clientsession(hass)
    with async_timeout.timeout(10, loop=hass.loop):
        data = await Occurrences.get(websession)

    sensors = []
    for line in config.get(CONF_LINE):
        sensors.append(MetroLisboaSensor(line, data))

    add_entities(sensors, True)

class MetroLisboaSensor(Entity):
    """Sensor that reads the status of a line from Occurrences."""

    ICON = 'mdi:subway'

    def __init__(self, name, data):
        """Initialize the sensor."""
        self._name = name
        self._data = data
        self._occurences = None
        self._state = None
        self._num_occurrences = None
        self._line_id = None
        self._details = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def num_occurrences(self):
        """Return the number of occurences."""
        return self._num_occurrences

    @property
    def details(self):
        """Return the occurences details"""
        return self._details

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return self.ICON

    @property
    def device_state_attributes(self):
        """Return other details about the sensor state."""
        attrs = {}
        details_attr = {}
        attrs["Number of Occurrences"] = self._num_occurrences
        attrs["LineID"] = self._details[0]
        for i in self._details[2]:
#            details_attr[i.id] = {"startTime": i.startTime, "endTime": i.endTime, 
#                                "Description": i.description, "Ended": str(i.ended)}
            details_attr[i.startTime] = i.description
        attrs['Details'] = details_attr
        return attrs

    @Throttle(SCAN_INTERVAL)
    async def async_update(self):
        """Update the sensor."""
        with async_timeout.timeout(10, loop=self.hass.loop):
            self._occurences = await self._data.ongoing()
            self._num_occurrences = await self._data.number_of_occurrences(METRO_LINES[self._name])
            if self._num_occurrences > 0:
                self._state = "Issue(s) on the line"
            else:
                self._state = "Good service"
            self._details = await self._data.occurrences_in_metroLine(METRO_LINES[self._name])
