from homeassistant import config_entries
import logging
import voluptuous as vol
from typing import Any, Dict, Optional

from .ducobox import DucoBoxBase

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

USER_CONFIG = vol.Schema(
    {
        vol.Required("serial_port", default=""): str,
        vol.Required("baudrate", default=9600): int,
        vol.Optional("slave_adr", default=1): vol.All(int, vol.Range(min=1, max=32)),
        vol.Optional("simulate", default=0): vol.All(int, vol.Range(min=0, max=1)),
    }
)


async def check_config(user_input):
    ret = False
    try:
        dbb = DucoBoxBase(**user_input)
        await dbb.create_serial_connection()
        await dbb.scan_modules()
        if len(dbb.modules) > 0:
            ret = True
    except:
        _LOGGER.exception("Could not reach any module")
        # TODO: report errors
        pass
    return ret


class DucoboxConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Example config flow."""

    # The schema version of the entries that it creates
    # Home Assistant will call your migrate method if the version changes
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors: Dict[str, str] = {}
        if user_input is not None:
            # Validate user input
            valid = await check_config(user_input)
            if valid:
                # See next section on create entry usage
                return self.async_create_entry(
                    title="Ducobox Focus",
                    data=user_input,
                )

            _LOGGER.info(f"config failed {valid}")
            errors["base"] = "incorrect settings"

        return self.async_show_form(
            step_id="user", data_schema=USER_CONFIG, errors=errors
        )
