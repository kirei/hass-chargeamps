"""Switch platform for Chargeamps."""

import logging

from homeassistant.components.switch import SwitchDevice

from .const import DOMAIN, DOMAIN_DATA, ICON

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass, config, async_add_entities, discovery_info=None
):  # pylint: disable=unused-argument
    """Setup switch platform."""
    switches = []
    handler = hass.data[DOMAIN_DATA]["handler"]
    for cp_id in handler.charge_point_ids:
        cp_info = handler.get_chargepoint_info(cp_id)
        for connector in cp_info.connectors:
            switches.append(
                ChargeampsSwitch(
                    hass,
                    cp_info.name + "_" + str(connector.charge_point_id) + "_connector_" + str(connector.connector_id),
                    connector.charge_point_id,
                    connector.connector_id,
                )
            )
            _LOGGER.info(
                "Adding chargepoint %s connector %s",
                connector.charge_point_id,
                connector.connector_id,
            )
    async_add_entities(switches, True)


class ChargeampsSwitch(SwitchDevice):
    """Chargeamps Switch class."""

    def __init__(self, hass, name, charge_point_id, connector_id):
        self.hass = hass
        self.charge_point_id = charge_point_id
        self.connector_id = connector_id
        self.handler = self.hass.data[DOMAIN_DATA]["handler"]
        self._name = name
        self._icon = ICON
        self._attributes = {}
        self._status = None

    async def async_update(self):
        """Update the switch."""
        _LOGGER.debug(
            "Update chargepoint %s connector %s",
            self.charge_point_id,
            self.connector_id,
        )
        await self.handler.update_data(self.charge_point_id)
        _LOGGER.debug(
            "Finished update chargepoint %s connector %s",
            self.charge_point_id,
            self.connector_id,
        )
        settings = self.handler.get_connector_settings(
            self.charge_point_id, self.connector_id
        )
        if settings is None:
            return
        if settings.mode == "On":
            self._status = True
        elif settings.mode == "Off":
            self._status = False
        else:
            self._status = None
        self._attributes["max_current"] = round(settings.max_current) if settings.max_current else None

    async def async_turn_on(self, **kwargs):  # pylint: disable=unused-argument
        """Turn on the switch."""
        await self.handler.set_connector_mode(
            self.charge_point_id, self.connector_id, "On"
        )

    async def async_turn_off(self, **kwargs):  # pylint: disable=unused-argument
        """Turn off the switch."""
        await self.handler.set_connector_mode(
            self.charge_point_id, self.connector_id, "Off"
        )

    @property
    def is_on(self):
        """Return true if the switch is on."""
        return self._status

    @property
    def name(self):
        """Return the name of the switch."""
        return self._name

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return self._icon

    @property
    def device_state_attributes(self):
        """Return the state attributes of the switch."""
        return self._attributes

    @property
    def unique_id(self):
        """Return a unique ID to use for this sswi."""
        return f"{DOMAIN}_{self.charge_point_id}_{self.connector_id}"

    @property
    def device_info(self):
        info = self.handler.get_chargepoint_info(self.charge_point_id)
        _LOGGER.debug("INFO = %s", info)
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self._name,
            "manufacturer": "Chargeamps",
            "model": info.type,
            "sw_version": info.firmware_version,
        }
