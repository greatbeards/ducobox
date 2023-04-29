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


from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_IP_ADDRESS,
    CONF_PASSWORD,
    CONF_TOKEN,
    CONF_UNIQUE_ID,
    PRECISION_WHOLE,
    UnitOfTemperature,
)

from homeassistant.components.climate import (
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback


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

        if isinstance(module, (DucoBox, DucoValve, DucoRelay)):
            _LOGGER.info("Adding %s" % str(module))
            new_entity = MyClimateEntity(module, device_id)
            entities_list.append(new_entity)

    # Add all entities to HA
    async_add_entities(entities_list, update_before_add=False)


class MyClimateEntity(ClimateEntity):
    # Implement one of these methods.

    _attr_hvac_modes = [HVACMode.FAN_ONLY, HVACMode.OFF]
    _attr_hvac_mode = HVACMode.FAN_ONLY
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_HUMIDITY | ClimateEntityFeature.FAN_MODE
    )  # | ClimateEntityFeature.SUPPORT_PRESET_MODE
    _attr_target_temperature_step = PRECISION_WHOLE
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_fan_modes = [FAN_AUTO, FAN_LOW, FAN_MEDIUM, FAN_HIGH]
    _attr_fan_mode = FAN_AUTO

    def __init__(self, module, device_id):
        self.device_id = device_id
        self._vent_actuator = module['ventilation setpoint']
        self._action = module['action']
        self._status = module['action']
        self._temperature = module['temperature']
        self.module = module

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        pass

    async def async_set_fan_mode(self, fan_mode):
        """Set new target fan mode."""
        pass

    async def async_set_humidity(self, humidity):
        """Set new target humidity."""
        pass



