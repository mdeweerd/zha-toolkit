import importlib
import logging

LOGGER = logging.getLogger(__name__)


async def default(app, listener, ieee, cmd, data, service, params, event_data):
    """Default handler that delegates CORE_ACTION to CORE.PY/CORE_ACTION"""
    import sys

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

    LOGGER.debug(
        f"Trying to import {package_name}.{module_name} to call {cmd}"
    )
    m = importlib.import_module(f".{module_name}", package=package_name)

    importlib.reload(m)

    # Get handler (cmd) in loaded module.
    handler = getattr(m, cmd)
    # Call the handler
    await handler(app, listener, ieee, cmd, data, service, params, event_data)
