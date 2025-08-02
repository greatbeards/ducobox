"""DucoBox integration for Home Assistant."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.config_entries import SOURCE_IGNORE, ConfigEntry

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

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
    CONCENTRATION_PARTS_PER_MILLION,
    PERCENTAGE,
    UnitOfTime,
)

from homeassistant.const import UnitOfVolumeFlowRate, UnitOfTemperature

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry


from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
)


import logging

from .ducobox import DucoBoxBase
from datetime import timedelta


DOMAIN = "ducobox"

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["sensor", "number", "fan"]  # "select",


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    dbb = DucoBoxBase(
        entry.data["serial_port"],
        baudrate=entry.data["baudrate"],
        slave_adr=entry.data["slave_adr"],
        simulate=entry.data["simulate"],
    )
    await dbb.create_serial_connection()
    await dbb.scan_modules()

    coordinator = DucoSensorCoordinator(hass, dbb)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = dbb, coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


class DucoSensorCoordinator(DataUpdateCoordinator):
    """My custom coordinator."""

    def __init__(self, hass, dbb) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="DucoBox coordinator",
            update_interval=timedelta(seconds=10),
        )
        self.dbb = dbb

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        return await self.dbb.update_sensors()


def get_unit(name):
    """Get the sensor unit based upon its name."""
    unit = None
    if name in "temperature":
        unit = UnitOfTemperature.CELSIUS
    elif name in [
        "ventilation level",
        "auto min",
        "auto max",
    ]:
        unit = PERCENTAGE
    elif "CO2" in name:
        unit = CONCENTRATION_PARTS_PER_MILLION
    elif name in ["flow", "inlet"]:
        unit = UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR
    elif "humidity" in name and "delta" not in name:
        unit = PERCENTAGE
    elif "button" in name:
        unit = PERCENTAGE
    elif "Time" in name:
        unit = UnitOfTime.MINUTES

    return unit
