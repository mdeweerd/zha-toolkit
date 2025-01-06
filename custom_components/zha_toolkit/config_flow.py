# Inspired from https://aarongodfrey.dev/home%20automation
#                     /building_a_home_assistant_custom_component_part_3/
# from copy import deepcopy
import logging
from typing import Any, Optional

from homeassistant import config_entries

from . import utils as u
from .const import DOMAIN

# from homeassistant.const import CONF_ACCESS_TOKEN,CONF_NAME
# from homeassistant.const import CONF_PATH,CONF_URL
# from homeassistant.core import callback
# from homeassistant.helpers.aiohttp_client import async_get_clientsession
# import homeassistant.helpers.config_validation as cv
# from homeassistant.helpers.entity_registry import (
#    async_entries_for_config_entry,
#    async_get_registry,
# )
# import voluptuous as vol


_LOGGER = logging.getLogger(__name__)

# INITIAL_CONFIG_SCHEMA = vol.Schema(
#    #{vol.Required(CONF_SKEY): cv.string, vol.Optional(CONF_O_KEY): cv.string}
# )
# EXTRA_CONF_SCHEMA = vol.Schema(
#    {
#        #vol.Required(CONF_PATH): cv.string,
#        #vol.Optional(CONF_NAME): cv.string,
#        #vol.Optional("add_another"): cv.boolean,
#    }
# )

# OPTIONS_SCHEMA = vol.Schema({vol.Optional(CONF_NM, default="go"): cv.string})


class ZhaToolkitCustomConfigFlow(
    config_entries.ConfigFlow, domain=DOMAIN
):  # type:ignore[call-arg]
    """Zha Toolkit Custom config flow."""

    VERSION = 0
    MINOR_VERSION = 1

    data: Optional[dict[str, Any]]

    async def my_async_create_entry(self):
        if self.data is None:
            self.data = {}
        self.data["VERSION"] = await u.getVersion()
        # Create the configuration entry
        return self.async_create_entry(title="ZHA Toolkit", data=self.data)

    async def async_step_user(
        self, user_input: Optional[dict[str, Any]] = None
    ):
        """Invoked when a user initiates a flow via the user interface."""
        # errors: dict[str, str] = {}
        # Nothing special to configure, end configuration step
        return self.my_async_create_entry()


#       if user_input is not None:
#           # Initially None, but not None when user entered data.
#           try:
#               await validate_something(
#                   user_input[CONF_ACCESS_TOKEN], self.hass
#               )
#           except ValueError:
#               errors["base"] = "error_message"  # key in `strings.json`
#           if not errors:
#               # Input is valid, set data.
#               self.data = user_input
#               self.data[CONF_SOME_KEY] = []
#               # Return the form of the next step.
#               return await self.async_step_repo()

#       return self.async_show_form(
#           step_id="user", data_schema=INITIAL_CONFIG_SCHEMA, errors=errors
#       )

#   async def async_step_repo(
#       self, user_input: Optional[Dict[str, Any]] = None
#   ):
#       """Second step in config flow to add a repo to watch."""
#       errors: Dict[str, str] = {}
#       if user_input is not None:
#           # Validate the path.
#           try:
#               await validate_path(
#                   user_input[CONF_PATH],
#                   self.data[CONF_ACCESS_TOKEN],
#                   self.hass,
#               )
#           except ValueError:
#               errors["base"] = "invalid_path"

#           if not errors:
#               # Input is valid, set data.
#               self.data[CONF_REPOS].append(
#                   {
#                       "path": user_input[CONF_PATH],
#                       "name": user_input.get(
#                           CONF_NAME, user_input[CONF_PATH]
#                       ),
#                   }
#               )
#               # If user ticked the box show this form again so they can add
#               # an additional repo.
#               if user_input.get("add_another", False):
#                   return await self.async_step_repo()

#               # User is done adding repos, create the config entry.
#               return self.async_create_entry(
#                   title="GitHub Custom", data=self.data
#               )

#       return self.async_show_form(
#           step_id="repo", data_schema=EXTRA_CONF_SCHEMA, errors=errors
#       )

#   @staticmethod
#   @callback
#   def async_get_options_flow(config_entry):
#       """Get the options flow for this handler."""
#       return OptionsFlowHandler(config_entry)


# class OptionsFlowHandler(config_entries.OptionsFlow):
#   """Handles options flow for the component."""

#   def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
#       self.config_entry = config_entry

#   async def async_step_init(
#       self, user_input: Dict[str, Any] = None
#   ) -> Dict[str, Any]:
#       """Manage the options for the custom component."""
#       errors: Dict[str, str] = {}
#       # Grab all configured repos from the entity registry so we can populate
#       # the multi-select dropdown that will allow a user to remove a repo.
#       entity_registry = await async_get_registry(self.hass)
#       entries = async_entries_for_config_entry(
#           entity_registry, self.config_entry.entry_id
#       )
#       # Default value for our multi-select.
#       all_repos = {e.entity_id: e.original_name for e in entries}
#       repo_map = {e.entity_id: e for e in entries}

#       if user_input is not None:
#           updated_repos = deepcopy(self.config_entry.data[CONF_REPOS])

#           # Remove any unchecked repos.
#           removed_entities = [
#               entity_id
#               for entity_id in repo_map.keys()
#               if entity_id not in user_input["repos"]
#           ]
#           for entity_id in removed_entities:
#               # Unregister from HA
#               entity_registry.async_remove(entity_id)
#               # Remove from our configured repos.
#               entry = repo_map[entity_id]
#               entry_path = entry.unique_id
#               updated_repos = [
#                   e for e in updated_repos if e["path"] != entry_path
#               ]

#           if user_input.get(CONF_PATH):
#               # Validate the path.
#               access_token = self.hass.data[DOMAIN][
#                   self.config_entry.entry_id
#               ][CONF_ACCESS_TOKEN]
#               try:
#                   await validate_path(
#                       user_input[CONF_PATH], access_token, self.hass
#                   )
#               except ValueError:
#                   errors["base"] = "invalid_path"

#               if not errors:
#                   # Add the new repo.
#                   updated_repos.append(
#                       {
#                           "path": user_input[CONF_PATH],
#                           "name": user_input.get(
#                               CONF_NAME, user_input[CONF_PATH]
#                           ),
#                       }
#                   )

#           if not errors:
#               # Value of data will be set on the options property of our
#               # config_entry instance.
#               return self.async_create_entry(
#                   title="",
#                   data={CONF_REPOS: updated_repos},
#               )

#       options_schema = vol.Schema(
#           {
#               vol.Optional(
#                   "repos", default=list(all_repos.keys())
#               ): cv.multi_select(all_repos),
#               vol.Optional(CONF_PATH): cv.string,
#               vol.Optional(CONF_NAME): cv.string,
#           }
#       )
#       return self.async_show_form(
#           step_id="init", data_schema=options_schema, errors=errors
#       )
