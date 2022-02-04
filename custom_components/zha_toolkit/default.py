import importlib
import logging

LOGGER = logging.getLogger(__name__)


async def default(
    app, listener, ieee, cmd, data, service, params, event_data
):

    import sys;
    package_name = vars(sys.modules[__name__])['__package__']

    # The module name is before the '_' and the command
    # is the entire string
    module_name = cmd[:cmd.index("_")]

    LOGGER.debug(f"Trying to import {package_name}.{module_name} to call {cmd}")

    m = importlib.import_module(f".{module_name}", package=package_name)
 
    importlib.reload(m)

    handler = getattr(m, cmd)
    await handler( app, listener, ieee, cmd, data, service, params, event_data )
