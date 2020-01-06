"""
Component to integrate with Chargeamps.

For more details about this component, please refer to
https://github.com/kirei/hass-chargeamps
"""

import logging
from datetime import timedelta
from typing import Optional

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from chargeamps.base import ChargePoint, ChargePointConnectorStatus
from chargeamps.external import ChargeAmpsExternalClient
from homeassistant import config_entries
from homeassistant.const import (CONF_API_KEY, CONF_PASSWORD, CONF_URL,
                                 CONF_USERNAME)
from homeassistant.helpers import discovery
from homeassistant.util import Throttle

from .const import CONF_CHARGEPOINTS, DOMAIN, DOMAIN_DATA, PLATFORMS

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=30)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Required(CONF_API_KEY): cv.string,
                vol.Optional(CONF_URL): cv.url,
                vol.Optional(CONF_CHARGEPOINTS): vol.All(cv.ensure_list, [cv.string]),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

_SERVICE_MAP = {
    "set_current": "async_set_current",
    "enable": "async_enable_ev",
    "disable": "async_disable_ev",
}


async def async_setup(hass, config):
    """Set up this component using YAML."""
    if config.get(DOMAIN) is None:
        # We get here if the integration is set up using config flow
        return True

    # Create DATA dict
    hass.data[DOMAIN_DATA] = {}

    # Get "global" configuration.
    username = config[DOMAIN].get(CONF_USERNAME)
    password = config[DOMAIN].get(CONF_PASSWORD)
    api_key = config[DOMAIN].get(CONF_API_KEY)
    api_base_url = config[DOMAIN].get(CONF_URL)
    chargepoint_ids = config[DOMAIN].get(CONF_CHARGEPOINTS)

    # Configure the client.
    client = ChargeAmpsExternalClient(email=username,
                                      password=password,
                                      api_key=api_key,
                                      api_base_url=api_base_url)

    # check all configured chargepoints or discover
    if chargepoint_ids is not None:
        for cp_id in chargepoint_ids:
            try:
                await client.get_chargepoint_status(cp_id)
                _LOGGER.info("Adding chargepoint %s", cp_id)
            except Exception:
                _LOGGER.error("Error adding chargepoint %s", cp_id)
        if len(chargepoint_ids) == 0:
            _LOGGER.error("No chargepoints found")
            return False
    else:
        chargepoint_ids = []
        for cp in await client.get_chargepoints():
            _LOGGER.info("Discovered chargepoint %s", cp.id)
            chargepoint_ids.append(cp.id)

    handler = ChargeampsHandler(hass, client, chargepoint_ids)
    hass.data[DOMAIN_DATA]["handler"] = handler
    hass.data[DOMAIN_DATA]["info"] = {}
    hass.data[DOMAIN_DATA]["chargepoint"] = {}
    hass.data[DOMAIN_DATA]["connector"] = {}
    await handler.update_info()

    # Load platforms
    for domain in PLATFORMS:
        hass.async_create_task(
            discovery.async_load_platform(hass, domain, DOMAIN, {}, config)
        )

    return True


class ChargeampsHandler:
    """This class handle communication and stores the data."""

    def __init__(self, hass, client, chargepoint_ids):
        """Initialize the class."""
        self.hass = hass
        self.client = client
        self.chargepoint_ids = chargepoint_ids

    async def get_chargepoint_statuses(self):
        res = []
        for cp_id in self.chargepoint_ids:
            res.append(await self.client.get_chargepoint_status(cp_id))
        return res

    def get_chargepoint_info(self, chargepoint_id) -> ChargePoint:
        return self.hass.data[DOMAIN_DATA]["info"].get(chargepoint_id)

    def get_connector_status(self, chargepoint_id, connector_id) -> Optional[ChargePointConnectorStatus]:
        return self.hass.data[DOMAIN_DATA]["connector"].get((chargepoint_id, connector_id))

    async def update_info(self):
        for cp in await self.client.get_chargepoints():
            if cp.id in self.chargepoint_ids:
                self.hass.data[DOMAIN_DATA]["info"][cp.id] = cp
                _LOGGER.info("Update info for chargepoint %s", cp.id)
                _LOGGER.debug("INFO = %s", cp)

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def update_data(self, charge_point_id):
        """Update data."""
        try:
            _LOGGER.debug("Update data for chargepoint %s", charge_point_id)
            status = await self.client.get_chargepoint_status(charge_point_id)
            _LOGGER.debug("STATUS = %s", status)
            self.hass.data[DOMAIN_DATA]["chargepoint"][charge_point_id] = status
            for connector_status in status.connector_statuses:
                _LOGGER.debug("Update data for chargepoint %s connector %d", charge_point_id, connector_status.connector_id)
                self.hass.data[DOMAIN_DATA]["connector"][(charge_point_id, connector_status.connector_id)] = connector_status
        except Exception as error:  # pylint: disable=broad-except
            _LOGGER.error("Could not update data - %s", error)
