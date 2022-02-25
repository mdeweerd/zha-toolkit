from __future__ import annotations

import homeassistant.helpers.config_validation as cv
import voluptouous as vol
from homeassistant import config_entries, data_entry_flow

from . import DOMAIN
from .params import USER_PARAMS as P

CONFIG_SCHEMA = {
    vol.Optional(
        P.TRIES,
        description={
            P.TRIES: "Number of tries that should be made for zigbee transactions"
        },
    ): cv.positive_int,
    vol.Optional(
        P.EVENT_SUCCESS, description={"suggested_value": "zha_toolkit_success"}
    ): cv.string,
    vol.Optional(
        P.EVENT_FAIL, description={"suggested_value": "zha_toolkit_failed"}
    ): cv.string,
    vol.Optional(
        P.EVENT_DONE, description={"suggested_value": "zha_toolkit_done"}
    ): cv.string,
    vol.Optional(
        P.FAIL_EXCEPTION, description={"suggested_value": True}
    ): cv.boolean,  # raise exception when success==False
}


@config_entries.HANDLERS.register(DOMAIN)
class ZhaToolkitConfigFlow(data_entry_flow.FlowHandler):
    """ZHA-TOOLKIT Config Flow"""

    VERSION = 1

    async def async_step_user(self, user_input):
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        if self.hass.data.get(DOMAIN):
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            # valid = await is_valid(user_input)
            # if valid:
            self.user_defaults = user_input
            return await self.async_step_account()

        return self.async_show_form(
            step_id="user", data_scheme=vol.Schema(CONFIG_SCHEMA)
        )
