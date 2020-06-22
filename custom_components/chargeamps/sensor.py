"""Sensor platform for Chargeamps."""

import logging

from homeassistant.helpers.entity import Entity

from .const import DOMAIN, DOMAIN_DATA, ICON

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass, config, async_add_entities, discovery_info=None
):  # pylint: disable=unused-argument
    """Setup sensor platform."""
    sensors = []
    handler = hass.data[DOMAIN_DATA]["handler"]
    for cp_id in handler.charge_point_ids:
        cp_info = handler.get_chargepoint_info(cp_id)
        sensors.append(
            ChargeampsTotalEnergy(hass, f"{cp_info.name}_{cp_id}_total_energy", cp_id,)
        )
        for connector in cp_info.connectors:
            sensors.append(
                ChargeampsSensor(
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
    async_add_entities(sensors, True)


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
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""
        return self._attributes

    @property
    def unique_id(self):
        """Return a unique ID to use for this sensor."""
        return f"{DOMAIN}_{self.charge_point_id}_{self.connector_id}"


class ChargeampsSensor(ChargeampsEntity):
    """Chargeamps Sensor class."""

    def __init__(self, hass, name, charge_point_id, connector_id):
        super().__init__(self, hass, name, charge_point_id, connector_id)
        self._icon = ICON

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return self._icon

    async def async_update(self):
        """Update the sensor."""
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
        status = self.handler.get_connector_status(
            self.charge_point_id, self.connector_id
        )
        if status is None:
            return
        self._state = status.status
        self._attributes["total_consumption_kwh"] = round(
            status.total_consumption_kwh, 3
        )
        if not self._interviewed:
            await self.interview()


class ChargeampsTotalEnergy(Entity):
    """Chargeamps Total Energy class."""

    def __init__(self, hass, name, charge_point_id):
        self.hass = hass
        self.charge_point_id = charge_point_id
        self.handler = self.hass.data[DOMAIN_DATA]["handler"]
        self._name = name
        self._state = None

    async def async_update(self):
        """Update the sensor."""
        _LOGGER.debug(
            "Update chargepoint %s", self.charge_point_id,
        )
        await self.handler.update_data(self.charge_point_id)
        _LOGGER.debug(
            "Finished update chargepoint %s", self.charge_point_id,
        )

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        return self.handler.get_chargepoint_total_energy(self.charge_point_id)

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return "kWh"

    @property
    def unique_id(self):
        """Return a unique ID to use for this sensor."""
        return f"{DOMAIN}_{self.charge_point_id}_total_energy"
