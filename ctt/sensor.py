"""
Support for CTT tracking service (https://www.ctt.pt)

For more details about this platform, please refer to the documentation at
https://github.com/dpjrodrigues/ha_custom_components
"""

import logging
import async_timeout
import asyncio
from datetime import timedelta

import voluptuous as vol
import requests

from homeassistant.const import (CONF_NAME)
import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_state_change
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = "Powered by CTT.pt"
TRACKING_IDS = 'tracking_ids'
CONF_SOURCE_INPUT = 'input_entity_id'
CONF_STATE_TO_COUNT = 'state_to_count'
SCAN_INTERVAL = timedelta(minutes=5)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default="CTT Tracker"): cv.string,
    vol.Required(CONF_SOURCE_INPUT):cv.entity_id,
    vol.Optional(CONF_STATE_TO_COUNT): cv.string
})


async def async_setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Tube sensor."""

    sensor = CTTSensor(config.get(CONF_NAME), config.get(CONF_SOURCE_INPUT),
        hass.states.get(config.get(CONF_SOURCE_INPUT)).state, config.get(CONF_STATE_TO_COUNT) )
    add_entities([sensor], True)

class CTTSensor(Entity):
    """Sensor that reads the status of CTT Packages."""

    ICON = 'mdi:package-variant-closed'

    def __init__(self, name, source_input, tracking_ids, state_to_count):
        """Initialize the sensor."""
        self._name = name
        self._source_input = source_input
        self._tracking_ids = tracking_ids
        self._state_to_count = state_to_count
        self._state = 0
        self._delivered = 0
        self._not_delivered = 0
        self._details = {}
        
    async def async_added_to_hass(self):
        """Handle entity which will be added."""
        await super().async_added_to_hass()

        @callback
        def set_tracking_ids(entity, old_state, new_state):
            """Handle the sensor state changes."""            
            from pyCTT import Items

            self._tracking_ids = new_state.state
            self.schedule_update_ha_state(True)

        async_track_state_change(self.hass, self._source_input, set_tracking_ids)

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the item State"""
        return self._state

    @property
    def delivered(self):
        """Return Number of delivered item"""
        return self._delivered

    @property
    def details(self):
        """Return the item details"""
        return self._details

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return self.ICON

    @property
    def extra_state_attributes(self):
        """Return other details about the sensor state."""
        attrs = {}

        attrs["Number of Items Delivered"] = self._delivered
        attrs["Number of Items Not Delivered"] = self._not_delivered
        for item in self._details:
            attrs[item.id[0:13]]=item.state+" at "+item.date+" "+item.hour
        return attrs

    #@Throttle(SCAN_INTERVAL)
    async def async_update(self):        
        """Update the sensor."""
        from pyCTT import Items

        websession = async_get_clientsession(self.hass)
        with async_timeout.timeout(10):          
            data = await Items.get(websession,self._tracking_ids)

        self._not_delivered = await data.number_of_items_not_delivered()
        if(self._state_to_count is None):
            self._state = self._not_delivered
        else:
            self._state = await data.number_of_items_in_state(self._state_to_count)

        self._delivered = await data.number_of_items_delivered()
        self._details = await data.full_list()
