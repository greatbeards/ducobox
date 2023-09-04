"""Platform for sensor integration."""
from __future__ import annotations
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor.const import SensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import  CoordinatorEntity

from . import DOMAIN
from .ducobox import GenericSensor, GenericActuator
from . import get_unit, DucoSensorCoordinator


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
            if isinstance(sens, GenericSensor):
                new_entity = DocuSensor(coordinator, sens, device_id)
                sensors.append(new_entity)

        # Add all sensor entities to HA
        async_add_entities(sensors, update_before_add=True)


class DocuSensor(CoordinatorEntity, SensorEntity):
    """Representation of a sensor."""

    _attr_unique_id = True

    def __init__(
        self,
        coordinator: DucoSensorCoordinator,
        sens: GenericSensor | GenericActuator,
        device_id,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, context=device_id)
        self.sens_obj = sens
        self.device_id = device_id

        self.unit = get_unit(self.name)

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
    def entity_registry_visible_default(self):
        return self.sens_obj.enabled

    @property
    def options(self) -> list[str] | None:
        return self.sens_obj.value_mapping

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return self.unit

    @property
    def device_class(self) -> str | None:
        if self.sens_obj.value_mapping:
            return SensorDeviceClass.ENUM

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


