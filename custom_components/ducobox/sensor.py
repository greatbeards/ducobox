"""Platform for sensor integration."""
from __future__ import annotations
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.components.switch import SwitchEntity
from homeassistant.components.select import SelectEntity

from homeassistant.components.sensor.const import SensorDeviceClass
from homeassistant.const import (
    TEMP_CELSIUS,
    VOLUME_FLOW_RATE_CUBIC_METERS_PER_HOUR,
    CONCENTRATION_PARTS_PER_MILLION,
    PERCENTAGE,
    TIME_MINUTES,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.entity import DeviceInfo, Entity

from homeassistant.helpers.entity import EntityCategory

from homeassistant.config_entries import ConfigEntry


from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from . import DOMAIN
from .ducobox import GenericSensor, DucoBox, GenericActuator
from datetime import timedelta
from . import get_unit

ENTITY_TYPES: tuple[NumberEntityDescription, ...] = (
    NumberEntityDescription(
        key="flow",
        name="flow",
        native_max_value=9999,
        native_step=1,
        native_min_value=0,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        entity_category=EntityCategory.CONFIG,
    ),
    NumberEntityDescription(
        key="screensaverBrightness",
        name="Screensaver brightness",
        native_max_value=255,
        native_step=1,
        # native_min_value=0,
        # entity_category=EntityCategory.CONFIG,
    ),
    NumberEntityDescription(
        key="timeToScreenOffV2",
        name="Screen off timer",
        native_max_value=9999,
        native_step=1,
        native_min_value=0,
        # native_unit_of_measurement=UnitOfTime.SECONDS,
        # entity_category=EntityCategory.CONFIG,
    ),
    NumberEntityDescription(
        key="screenBrightness",
        name="Screen brightness",
        native_max_value=255,
        native_step=1,
        native_min_value=0,
    ),
)


# SCAN_INTERVAL = timedelta(seconds=5)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add cover for passed config_entry in HA."""
    # The hub is loaded from the associated hass.data entry that was created in the
    # __init__.async_setup_entry function
    dbb, coordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Fetch initial data so we have data when entities subscribe
    #
    # If the refresh fails, async_config_entry_first_refresh will
    # raise ConfigEntryNotReady and setup will try again later
    #
    # If you do not want to retry setup on failure, use
    # coordinator.async_refresh() instead
    #
    # await coordinator.async_config_entry_first_refresh()

    # master_module = dbb.modules[0]
    for module in dbb.modules:
        device_id = module.base_adr
        sensors = []
        for sens in module.sensors:
            if isinstance(sens, GenericSensor):
                new_entity = DocuSensor(coordinator, sens, device_id)
                sensors.append(new_entity)

        # Add all entities to HA
        async_add_entities(sensors, update_before_add=True)


class MyCoordinator(DataUpdateCoordinator):
    """My custom coordinator."""

    def __init__(self, hass, dbb):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="DucoBox coordinator",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=30),
        )
        self.dbb = dbb

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        await self.dbb.update_sensors()




class DocuSensor(CoordinatorEntity, SensorEntity):
    """Representation of a sensor."""

    _attr_unique_id = True

    def __init__(
        self,
        coordinator: MyCoordinator,
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


class DucoSwitch(CoordinatorEntity, SwitchEntity):
    """Use to control humidity delta option"""

    pass


class DucoAction(CoordinatorEntity, SelectEntity):
    """Use to control the action states"""

    pass
