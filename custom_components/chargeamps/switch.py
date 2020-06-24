"""Switch platform for Chargeamps."""

import logging

from homeassistant.components.switch import SwitchEntity

from . import ChargeampsEntity
from .const import DOMAIN_DATA

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
                    f"{cp_info.name}_{connector.charge_point_id}_{connector.connector_id}",
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


class ChargeampsSwitch(SwitchEntity, ChargeampsEntity):
    """Chargeamps Switch class."""

    def __init__(self, hass, name, charge_point_id, connector_id):
        super().__init__(hass, name, charge_point_id, connector_id)
        self._current_power_w = 0

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
        self._attributes["max_current"] = (
            round(settings.max_current) if settings.max_current else None
        )
        measurements = self.handler.get_connector_measurements(
            self.charge_point_id, self.connector_id
        )
        if measurements:
            self._current_power_w = round(
                sum([phase.current * phase.voltage for phase in measurements]), 0
            )
        else:
            self._current_power_w = 0

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
    def current_power_w(self):
        """Return the current power usage in W."""
        return self._current_power_w
