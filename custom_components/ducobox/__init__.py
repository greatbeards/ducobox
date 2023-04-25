# https://developers.home-assistant.io/docs/integration_fetching_data
# https://github.com/home-assistant/example-custom-config/tree/master/custom_components/example_sensor/

# https://github.com/home-assistant/example-custom-config/blob/master/custom_components/example_load_platform/sensor.py

"""Example Load Platform integration."""
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


import logging

from .ducobox import DucoBoxBase
from datetime import timedelta


DOMAIN = "ducobox"

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["sensor", "number", "climate"]  # "fan"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # async def async_setup_platform(
    #    hass: HomeAssistant,
    #    config: ConfigType,
    #    async_add_entities: AddEntitiesCallback,
    #    discovery_info: DiscoveryInfoType | None = None,
    # ) -> None:
    """Your controller/hub specific code."""
    # Data that you want to share with your platforms

    dbb = DucoBoxBase(
        entry.data["serial_port"],
        baudrate=entry.data["baudrate"],
        slave_adr=entry.data["slave_adr"],
        simulate=entry.data["simulate"],
    )
    await dbb.create_serial_connection()
    await dbb.scan_modules()

    coordinator = MyCoordinator(hass, dbb)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = dbb, coordinator

    # hass.helpers.discovery.load_platform("sensor", DOMAIN, {}, entry)
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


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


def get_unit(name):
    """Get the sensor unit based upon its name"""
    unit = None
    if name in "temperature":
        unit = TEMP_CELSIUS
    elif name in [
        "ventilation level",
        "auto min",
        "auto max",
    ]:
        unit = PERCENTAGE
    elif "CO2" in name:
        unit = CONCENTRATION_PARTS_PER_MILLION
    elif name in ["flow", "inlet"]:
        unit = VOLUME_FLOW_RATE_CUBIC_METERS_PER_HOUR
    elif "humidity" in name and not "delta" in name:
        unit = PERCENTAGE
    elif "button" in name:
        unit = PERCENTAGE
    elif "Time" in name:
        unit = TIME_MINUTES

    return unit
