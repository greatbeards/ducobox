"""Platform for sensor integration."""
from __future__ import annotations
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import (
    TEMP_CELSIUS,
    VOLUME_FLOW_RATE_CUBIC_METERS_PER_HOUR,
    CONCENTRATION_PARTS_PER_MILLION,
    PERCENTAGE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.entity import DeviceInfo, Entity

from homeassistant.config_entries import ConfigEntry


from . import DOMAIN
from .ducobox import GenericSensor, DucoBox
from datetime import timedelta

SCAN_INTERVAL = timedelta(seconds=5)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add cover for passed config_entry in HA."""
    # The hub is loaded from the associated hass.data entry that was created in the
    # __init__.async_setup_entry function
    dbb = hass.data[DOMAIN][config_entry.entry_id]

    # master_module = dbb.modules[0]
    for module in dbb.modules:
        device_id = module.base_adr
        sensors = [DocuSensor(sensor, device_id) for sensor in module.sensors]
        sensors += [DocuSensor(sensor, device_id) for sensor in module.actuators]

        for sens in sensors:
            print(sens.unique_id)

        # Add all entities to HA
        async_add_entities(sensors, update_before_add=True)

    # async_add_entities(
    #    [DocuSensor(sensor, config_entry.entry_id) for sensor in dbb.actuators],
    #    update_before_add=True,
    # )


class DocuSensor(SensorEntity):
    """Representation of a sensor."""

    _attr_should_poll = True
    _attr_unique_id = True

    def __init__(self, sens: GenericSensor, device_id) -> None:
        """Initialize the sensor."""
        self.sens_obj = sens
        self._state = sens.update()
        self.device_id = device_id

        if "temperature" in sens.name:
            self.unit = TEMP_CELSIUS
        elif "vent" in sens.name:
            self.unit = PERCENTAGE
        elif "co2" in sens.name:
            self.unit = CONCENTRATION_PARTS_PER_MILLION
        elif "flow" in sens.name:
            self.unit = VOLUME_FLOW_RATE_CUBIC_METERS_PER_HOUR
        else:
            self.unit = None

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self.sens_obj.name

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return self.sens_obj.alias

    @property
    def state(self):
        """Return the state of the sensor."""
        return self.sens_obj.value

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return self.unit

    async def async_update(self) -> None:
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        await self.sens_obj.update()

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""

        logging.info(type(self.sens_obj.module))

        return DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    self.device_id,
                )
            },
            name=self.sens_obj.module.name + str(" @ adress ") + str(self.device_id),
            manufacturer="DucoBox Focus",
            model=self.sens_obj.module.name,
        )
