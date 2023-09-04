from __future__ import annotations
import logging

from homeassistant.components.sensor.const import SensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import  CoordinatorEntity
from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
)

from . import DOMAIN
from .ducobox import GenericActuator
from . import get_unit, MyCoordinator


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add cover for passed config_entry in HA."""
    
    dbb, coordinator = hass.data[DOMAIN][config_entry.entry_id]

    for module in dbb.modules:
        device_id = module.base_adr
        sensors = []
        for sens in module.sensors:
            if isinstance(sens, GenericActuator):
                new_entity = DucoNumberController(coordinator, sens, device_id)
                sensors.append(new_entity)

        # Add all entities to HA
        async_add_entities(sensors, update_before_add=True)


class DucoNumberController(CoordinatorEntity, NumberEntity):
    """Use to control valve flow, setpoints of CO2/Humidity"""

    # _attr_unique_id = True

    def __init__(
        self,
        coordinator: MyCoordinator,
        sens: GenericActuator,
        device_id,
    ) -> None:
        """Initialize the sensor."""
        CoordinatorEntity.__init__(self, coordinator, context=device_id)
        NumberEntity.__init__(self)
        self.sens_obj = sens
        self.device_id = device_id

    @property
    def entity_category(self):
        return EntityCategory.CONFIG

    @property
    def native_unit_of_measurement(self) -> str:
        return get_unit(self.name)

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self.sens_obj.name

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return self.sens_obj.alias

    @property
    def native_max_value(self):
        return self.sens_obj.max_value

    @property
    def native_min_value(self):
        return self.sens_obj.min_value

    @property
    def native_step(self):
        return self.sens_obj.step_value

    @property
    def native_value(self) -> int | None:
        return self.sens_obj.value

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        _LOGGER.info("%s Writing %f " % (self.sens_obj.alias, value))
        await self.sens_obj.write(value)

    @property
    def device_class(self) -> str | None:
        if self.sens_obj.value_mapping:
            return SensorDeviceClass.ENUM
        else:
            return NumberDeviceClass.VOLUME

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
