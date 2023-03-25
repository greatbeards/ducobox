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
import logging

from .ducobox import DucoBoxBase, GenericActuator, GenericSensor

DOMAIN = "ducobox"

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["sensor"]  # "fan"


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

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = dbb

    # hass.helpers.discovery.load_platform("sensor", DOMAIN, {}, entry)
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True
