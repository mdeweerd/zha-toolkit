from __future__ import annotations

import importlib
import logging
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType

LOGGER = logging.getLogger(__name__)


async def default(app, listener, ieee, cmd, data, service, params, event_data):
    """Default handler that delegates CORE_ACTION to CORE.py/ACTION"""

    # This defaults handler enables adding new handler methods
    # by adding a file such as "CORE.py" containing the
    # ACTION.  The corresponding service name is "CORE_ACTION".
    #
    # This avoids having to add the mapping in __init__.py
    # and also allows the user to freely add new services.

    # get our package name to know where to load from
    package_name = vars(sys.modules[__name__])["__package__"]

    # The module name is before the '_' and the command
    # is the entire string
    if isinstance(cmd, str):
        module_name = cmd[: cmd.index("_")]
    else:
        # When cmd is not a string, it must be a list [ MODULE, CMD ]
        module_name = cmd[0]
        cmd = cmd[1]

    def _reload_command_module() -> ModuleType:
        LOGGER.debug(
            f"Trying to import {package_name}.{module_name} to call {cmd}"
        )
        m = importlib.import_module(f".{module_name}", package=package_name)

        importlib.reload(m)
        return m

    m = await listener.hass.async_add_import_executor_job(
        _reload_command_module
    )
    # Get handler (cmd) in loaded module.
    handler = getattr(m, cmd)
    # Call the handler
    await handler(app, listener, ieee, cmd, data, service, params, event_data)
