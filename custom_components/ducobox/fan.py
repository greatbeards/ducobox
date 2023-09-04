from __future__ import annotations
import logging


from homeassistant import config_entries
from homeassistant.components.fan import (
    DIRECTION_FORWARD,
    DIRECTION_REVERSE,
    FanEntity,
    FanEntityFeature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import (
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)

from . import DOMAIN
from .ducobox import GenericSensor, DucoBox, GenericActuator, DucoValve, DucoRelay
from datetime import timedelta
from . import get_unit

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
    entities_list = []
    for module in dbb.modules:
        device_id = module.base_adr

        if isinstance(module, (DucoBox, DucoValve)):
            _LOGGER.info("Adding %s" % str(module))
            new_entity = DucoFanEntity(module, device_id)
            entities_list.append(new_entity)

    # Add all entities to HA
    async_add_entities(entities_list, update_before_add=False)



class DucoFanEntity(FanEntity):
    
    _attr_supported_features = FanEntityFeature.SET_SPEED 
    _attr_preset_modes = ["Auto"]
    _attr_speed_count = 100
    _attr_unique_id = True
    
    def __init__(self, module, device_id):
        self.module = module
        self.device_id = device_id
        self._status = module.sensors_by_name['action']
        self._setpoint = module.sensors_by_name['ventilation setpoint']
        
    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode of the fan."""
        if preset_mode == "Auto":
            await self._status.write("Auto")
            await self._setpoint.write(-1)
    
    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed of the fan, as a percentage."""
        await self._setpoint.write(int(percentage))
        
    async def async_turn_off(self, **kwargs) -> None:
        """Turn the fan off."""
        await self.async_set_preset_mode("Auto")
        
    @property
    def is_on(self):
        return self._setpoint.value != 0
        
    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self.module.name
        
    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return "FAN_" + self.module.name + str(self.device_id)
    
    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""

        return DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    self.device_id,
                )
            },
            name=self.module.name + str(" @ adress ") + str(self.device_id),
            manufacturer="DucoBox Focus",
            model=self.module.name,
        )