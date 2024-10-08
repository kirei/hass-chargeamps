"""Sensor platform for Chargeamps."""

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import STATE_UNAVAILABLE, UnitOfEnergy, UnitOfPower

from . import ChargeampsEntity
from .const import CHARGEPOINT_ONLINE, DOMAIN_DATA, SCAN_INTERVAL  # noqa

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):  # pylint: disable=unused-argument
    """Setup sensor platform."""
    sensors = []
    handler = hass.data[DOMAIN_DATA]["handler"]
    for cp_id in handler.charge_point_ids:
        cp_info = handler.get_chargepoint_info(cp_id)
        sensors.append(
            ChargeampsTotalEnergy(
                hass,
                f"{cp_info.name}_{cp_id}_total_energy",
                cp_id,
            )
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
            sensors.append(
                ChargeampsPowerSensor(
                    hass,
                    f"{cp_info.name} {connector.charge_point_id} {connector.connector_id} Power",
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


class ChargeampsSensor(ChargeampsEntity, SensorEntity):
    """Chargeamps Sensor class."""

    def __init__(self, hass, name, charge_point_id, connector_id):
        super().__init__(hass, name, charge_point_id, connector_id)
        self._interviewed = False

    async def interview(self):
        chargepoint_info = self.handler.get_chargepoint_info(self.charge_point_id)
        connector_info = self.handler.get_connector_info(self.charge_point_id, self.connector_id)
        self._attributes["chargepoint_type"] = chargepoint_info.type
        self._attributes["connector_type"] = connector_info.type
        self._interviewed = True

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
        cp_status = self.handler.get_chargepoint_status(self.charge_point_id)
        status = self.handler.get_connector_status(self.charge_point_id, self.connector_id)
        if status is None:
            return
        if cp_status.status != CHARGEPOINT_ONLINE:
            self._state = STATE_UNAVAILABLE
        else:
            self._state = status.status
        self._attributes["total_consumption_kwh"] = round(status.total_consumption_kwh, 3)
        if not self._interviewed:
            await self.interview()


class ChargeampsTotalEnergy(ChargeampsEntity, SensorEntity):
    """Chargeamps Total Energy class."""

    def __init__(self, hass, name, charge_point_id):
        super().__init__(hass, name, charge_point_id, "total_energy")
        del self._attributes["connector_id"]

    async def async_update(self):
        """Update the sensor."""
        _LOGGER.debug(
            "Update chargepoint %s",
            self.charge_point_id,
        )
        await self.handler.update_data(self.charge_point_id)
        self._state = self.handler.get_chargepoint_total_energy(self.charge_point_id)
        _LOGGER.debug(
            "Finished update chargepoint %s",
            self.charge_point_id,
        )

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return SensorDeviceClass.ENERGY

    @property
    def state_class(self):
        """Return the state class of the sensor."""
        return SensorStateClass.TOTAL_INCREASING

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return UnitOfEnergy.KILO_WATT_HOUR


class ChargeampsPowerSensor(ChargeampsEntity, SensorEntity):
    """Chargeamps Power Sensor class."""

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
        measurements = self.handler.get_connector_measurements(self.charge_point_id, self.connector_id)
        if measurements:
            self._state = round(sum([phase.current * phase.voltage for phase in measurements]), 0)
            self._attributes["active_phase"] = " ".join([i.phase for i in measurements if i.current > 0])
            for measure in measurements:
                self._attributes[f"{measure.phase.lower()}_power"] = round(measure.voltage * measure.current, 0)
                self._attributes[f"{measure.phase.lower()}_current"] = round(measure.current, 1)
        else:
            self._attributes["active_phase"] = ""
            for phase in range(1, 4):
                for measure in ("power", "current"):
                    self._attributes[f"l{phase}_{measure}"] = 0
            self._state = 0

    @property
    def unique_id(self):
        """Return a unique ID to use for this sensor."""
        return f"{super().unique_id}_power"

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return SensorDeviceClass.POWER

    @property
    def state_class(self):
        """Return the state class of the sensor."""
        return SensorStateClass.MEASUREMENT

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return UnitOfPower.WATT
