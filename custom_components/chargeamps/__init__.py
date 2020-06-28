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
from chargeamps.base import (
    ChargePoint,
    ChargePointConnector,
    ChargePointConnectorSettings,
    ChargePointConnectorStatus,
)
from chargeamps.external import ChargeAmpsExternalClient
from homeassistant.const import CONF_API_KEY, CONF_PASSWORD, CONF_URL, CONF_USERNAME
from homeassistant.helpers import discovery
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

from .const import (
    CONF_CHARGEPOINTS,
    CONF_READONLY,
    DEFAULT_ICON,
    DIMMER_VALUES,
    DOMAIN,
    DOMAIN_DATA,
    ICON_MAP,
    PLATFORMS,
)

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
                vol.Optional(CONF_READONLY): cv.boolean,
                vol.Optional(CONF_CHARGEPOINTS): vol.All(cv.ensure_list, [cv.string]),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

_SERVICE_MAP = {
    "set_light": "async_set_light",
    "set_max_current": "async_set_max_current",
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
    charge_point_ids = config[DOMAIN].get(CONF_CHARGEPOINTS)
    readonly = config[DOMAIN].get(CONF_READONLY, False)

    # Configure the client.
    client = ChargeAmpsExternalClient(
        email=username, password=password, api_key=api_key, api_base_url=api_base_url
    )

    # check all configured chargepoints or discover
    if charge_point_ids is not None:
        for cp_id in charge_point_ids:
            try:
                await client.get_chargepoint_status(cp_id)
                _LOGGER.info("Adding chargepoint %s", cp_id)
            except Exception:
                _LOGGER.error("Error adding chargepoint %s", cp_id)
        if len(charge_point_ids) == 0:
            _LOGGER.error("No chargepoints found")
            return False
    else:
        charge_point_ids = []
        for cp in await client.get_chargepoints():
            _LOGGER.info("Discovered chargepoint %s", cp.id)
            charge_point_ids.append(cp.id)

    handler = ChargeampsHandler(hass, client, charge_point_ids, readonly)
    hass.data[DOMAIN_DATA]["handler"] = handler
    hass.data[DOMAIN_DATA]["chargepoint_info"] = {}
    hass.data[DOMAIN_DATA]["chargepoint_status"] = {}
    hass.data[DOMAIN_DATA]["chargepoint_settings"] = {}
    hass.data[DOMAIN_DATA]["connector_info"] = {}
    hass.data[DOMAIN_DATA]["connector_status"] = {}
    hass.data[DOMAIN_DATA]["connector_settings"] = {}
    hass.data[DOMAIN_DATA]["chargepoint_total_energy"] = {}
    await handler.update_info()
    for cp_id in charge_point_ids:
        await handler.force_update_data(cp_id)

    # Register services to hass
    async def execute_service(call):
        function_name = _SERVICE_MAP[call.service]
        function_call = getattr(handler, function_name)
        await function_call(call.data)

    for service in _SERVICE_MAP:
        hass.services.async_register(DOMAIN, service, execute_service)

    # Load platforms
    for domain in PLATFORMS:
        hass.async_create_task(
            discovery.async_load_platform(hass, domain, DOMAIN, {}, config)
        )

    return True


class ChargeampsHandler:
    """This class handle communication and stores the data."""

    def __init__(self, hass, client, charge_point_ids, readonly):
        """Initialize the class."""
        self.hass = hass
        self.client = client
        self.charge_point_ids = charge_point_ids
        self.default_charge_point_id = charge_point_ids[0]
        self.default_connector_id = 1
        self.readonly = readonly
        if self.readonly:
            _LOGGER.warning(
                "Running in read-only mode, chargepoint will never be updated"
            )

    async def get_chargepoint_statuses(self):
        res = []
        for cp_id in self.charge_point_ids:
            res.append(await self.client.get_chargepoint_status(cp_id))
        return res

    def get_chargepoint_total_energy(self, charge_point_id) -> float:
        return self.hass.data[DOMAIN_DATA]["chargepoint_total_energy"].get(
            charge_point_id
        )

    def get_chargepoint_info(self, charge_point_id) -> ChargePoint:
        return self.hass.data[DOMAIN_DATA]["chargepoint_info"].get(charge_point_id)

    def get_chargepoint_settings(self, charge_point_id):
        return self.hass.data[DOMAIN_DATA]["chargepoint_settings"].get(charge_point_id)

    def get_connector_info(self, charge_point_id, connector_id) -> ChargePointConnector:
        key = (charge_point_id, connector_id)
        return self.hass.data[DOMAIN_DATA]["connector_info"].get(key)

    async def set_chargepoint_lights(self, charge_point_id, dimmer, downlight):
        settings = await self.client.get_chargepoint_settings(charge_point_id)
        if dimmer is not None:
            settings.dimmer = dimmer.capitalize()
        if downlight is not None:
            settings.down_light = downlight
        if self.readonly:
            _LOGGER.info("NOT setting chargepoint: %s", settings)
        else:
            _LOGGER.info("Setting chargepoint: %s", settings)
            await self.client.set_chargepoint_settings(settings)
        await self.force_update_data(charge_point_id)

    def get_connector_status(
        self, charge_point_id, connector_id
    ) -> Optional[ChargePointConnectorStatus]:
        key = (charge_point_id, connector_id)
        return self.hass.data[DOMAIN_DATA]["connector_status"].get(key)

    def get_connector_settings(
        self, charge_point_id, connector_id
    ) -> Optional[ChargePointConnectorSettings]:
        key = (charge_point_id, connector_id)
        return self.hass.data[DOMAIN_DATA]["connector_settings"].get(key)

    def get_connector_measurements(self, charge_point_id, connector_id):
        connector_status = self.get_connector_status(charge_point_id, connector_id)
        if connector_status:
            return connector_status.measurements
        return None

    async def set_connector_mode(self, charge_point_id, connector_id, mode):
        settings = await self.client.get_chargepoint_connector_settings(
            charge_point_id, connector_id
        )
        settings.mode = mode
        if self.readonly:
            _LOGGER.info("NOT setting chargepoint connector: %s", settings)
        else:
            _LOGGER.info("Setting chargepoint connector: %s", settings)
            await self.client.set_chargepoint_connector_settings(settings)
        await self.force_update_data(charge_point_id)

    async def set_connector_max_current(
        self, charge_point_id, connector_id, max_current
    ):
        settings = await self.client.get_chargepoint_connector_settings(
            charge_point_id, connector_id
        )
        settings.max_current = max_current
        if self.readonly:
            _LOGGER.info("NOT setting chargepoint connector: %s", settings)
        else:
            _LOGGER.info("Setting chargepoint connector: %s", settings)
            await self.client.set_chargepoint_connector_settings(settings)
        await self.force_update_data(charge_point_id)

    async def update_info(self):
        for cp in await self.client.get_chargepoints():
            if cp.id in self.charge_point_ids:
                _LOGGER.debug("CHARGEPOINT INFO = %s", cp)
                self.hass.data[DOMAIN_DATA]["chargepoint_info"][cp.id] = cp
                for c in cp.connectors:
                    key = (c.charge_point_id, c.connector_id)
                    self.hass.data[DOMAIN_DATA]["connector_info"][key] = c
                _LOGGER.debug("CONNECTOR INFO = %s", c)
                _LOGGER.info("Update info for chargepoint %s", cp.id)

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def update_data(self, charge_point_id):
        _LOGGER.debug("Update data for chargepoint %s", charge_point_id)
        await self._update_data(charge_point_id)

    async def force_update_data(self, charge_point_id):
        _LOGGER.debug("Force update data for chargepoint %s", charge_point_id)
        await self._update_data(charge_point_id)

    async def _update_data(self, charge_point_id):
        """Update data."""
        try:
            status = await self.client.get_chargepoint_status(charge_point_id)
            _LOGGER.debug("STATUS = %s", status)
            self.hass.data[DOMAIN_DATA]["chargepoint_status"][charge_point_id] = status
            for connector_status in status.connector_statuses:
                _LOGGER.debug(
                    "Update data for chargepoint %s connector %d",
                    charge_point_id,
                    connector_status.connector_id,
                )
                key = (charge_point_id, connector_status.connector_id)
                self.hass.data[DOMAIN_DATA]["connector_status"][key] = connector_status
                connector_settings = await self.client.get_chargepoint_connector_settings(
                    charge_point_id, connector_status.connector_id
                )
                self.hass.data[DOMAIN_DATA]["connector_settings"][
                    key
                ] = connector_settings
            total_energy = sum(
                [
                    v.total_consumption_kwh
                    for v in await self.client.get_all_chargingsessions(charge_point_id)
                ]
            )
            _LOGGER.debug(
                "Total consumption for chargepoint %s: %f",
                charge_point_id,
                total_energy,
            )
            self.hass.data[DOMAIN_DATA]["chargepoint_total_energy"][
                charge_point_id
            ] = round(total_energy, 2)
            settings = await self.client.get_chargepoint_settings(charge_point_id)
            self.hass.data[DOMAIN_DATA]["chargepoint_settings"][
                charge_point_id
            ] = settings
        except Exception as error:  # pylint: disable=broad-except
            _LOGGER.error("Could not update data - %s", error)

    async def async_set_max_current(self, param):
        """Set current maximum in async way."""
        try:
            max_current = param["max_current"]
        except (KeyError, ValueError) as ex:
            _LOGGER.warning("Current value is not correct. %s", ex)
            return
        charge_point_id = param.get("chargepoint", self.default_charge_point_id)
        connector_id = param.get("connector", self.default_connector_id)
        await self.set_connector_max_current(charge_point_id, connector_id, max_current)

    async def async_set_light(self, param):
        """Set charge point lights in async way."""
        charge_point_id = param.get("chargepoint", self.default_charge_point_id)
        dimmer = param.get("dimmer")
        if dimmer is not None and dimmer not in DIMMER_VALUES:
            _LOGGER.warning("Dimmer is not one of %s - got %s", DIMMER_VALUES, dimmer)
            return
        downlight = param.get("downlight")
        if downlight is not None and not isinstance(downlight, bool):
            _LOGGER.warning("Downlight must be true or false - got %s", downlight)
            return
        await self.set_chargepoint_lights(charge_point_id, dimmer, downlight)

    async def async_enable_ev(self, param):
        """Enable EV in async way."""
        charge_point_id = param.get("chargepoint", self.default_charge_point_id)
        connector_id = param.get("connector", self.default_connector_id)
        await self.set_connector_mode(charge_point_id, connector_id, "On")

    async def async_disable_ev(self, param=None):
        """Disable EV in async way."""
        charge_point_id = param.get("chargepoint", self.default_charge_point_id)
        connector_id = param.get("connector", self.default_connector_id)
        await self.set_connector_mode(charge_point_id, connector_id, "Off")


class ChargeampsEntity(Entity):
    """Chargeamps Entity class."""

    def __init__(self, hass, name, charge_point_id, connector_id):
        self.hass = hass
        self.charge_point_id = charge_point_id
        self.connector_id = connector_id
        self.handler = self.hass.data[DOMAIN_DATA]["handler"]
        self._name = name
        self._state = None
        self._attributes = {}
        self._interviewed = False

    async def interview(self):
        chargepoint_info = self.handler.get_chargepoint_info(self.charge_point_id)
        connector_info = self.handler.get_connector_info(
            self.charge_point_id, self.connector_id
        )
        self._attributes["chargepoint_type"] = chargepoint_info.type
        self._attributes["connector_type"] = connector_info.type
        self._interviewed = True

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        if not self.device_class:
            connector_info = self.handler.get_connector_info(
                self.charge_point_id, self.connector_id
            )
            if connector_info:
                return ICON_MAP.get(connector_info.type, DEFAULT_ICON)
            return DEFAULT_ICON

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""
        return self._attributes

    @property
    def unique_id(self):
        """Return a unique ID to use for this sensor."""
        return f"{DOMAIN}_{self.charge_point_id}_{self.connector_id}"
