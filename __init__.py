import importlib
import logging

import voluptuous as vol
import zigpy.types as t

import homeassistant.helpers.config_validation as cv

DEPENDENCIES = ['zha']

DOMAIN = 'zha_custom'

ATTR_COMMAND = 'command'
ATTR_COMMAND_DATA = 'command_data'
ATTR_IEEE = 'ieee'
DATA_ZHAC = 'zha_custom'

SERVICE_CUSTOM = 'execute'

_LOGGER = logging.getLogger(__name__)

SERVICE_SCHEMAS = {
    SERVICE_CUSTOM: vol.Schema({
        vol.Optional(ATTR_IEEE): t.EUI64.convert,
        vol.Optional(ATTR_COMMAND): cv.string,
        vol.Optional(ATTR_COMMAND_DATA): cv.string,
    }, extra=vol.ALLOW_EXTRA),
}


async def async_setup(hass, config):
    """Set up ZHA from config."""

    if DOMAIN not in config:
        return True

    try:
        zha_gw = hass.data['zha']['zha_gateway']
    except KeyError:
        return True

    async def custom_service(service):
        """Run command from custom module."""
        _LOGGER.info("Running custom service: %s", service)
        ieee = service.data.get(ATTR_IEEE)
        cmd = service.data.get(ATTR_COMMAND)
        cmd_data = service.data.get(ATTR_COMMAND_DATA)
        mod_path = 'custom_components.{}'.format(DOMAIN)
        try:
            module = importlib.import_module(mod_path)
        except ImportError as err:
            _LOGGER.error("Couldn't load zha_service module: %s", err)
            return
        importlib.reload(module)
        _LOGGER.debug("module is %s", module)
        if cmd:
            handler = getattr(module, 'command_handler_{}'.format(cmd))
            await handler(zha_gw.application_controller, zha_gw, ieee, cmd,
                          cmd_data, service)
        else:
            await module.default_command(
                zha_gw.application_controller, zha_gw, ieee, cmd, cmd_data,
                service)

    hass.services.async_register(DOMAIN, SERVICE_CUSTOM, custom_service,
                                 schema=SERVICE_SCHEMAS[SERVICE_CUSTOM])
    return True


async def default_command(app, listener, ieee, cmd, data, service):
    _LOGGER.debug("running default command: %s", service)


async def command_handler_handle_join(app, listener, ieee, cmd, data, service):
    """Rediscover a device.
    ieee -- ieee of the device
    data -- nwk of the device in decimal format
    """
    _LOGGER.debug("running 'handle_join' command: %s", service)
    if ieee is None:
        return
    app.handle_join(int(data, 16), ieee, 0)


async def command_handler_scan_device(*args, **kwargs):
    """Scan a device for all supported attributes and commands.
    ieee -- ieee of the device to scan

    ToDo: use manufacturer_id to scan for manufacturer specific clusters/attrs.
    """

    from . import scan_device
    importlib.reload(scan_device)

    await scan_device.scan_device(*args, **kwargs)


async def command_handler_get_groups(*args, **kwargs):
    """Get all groups a device is member of.
    ieee -- ieee of the device to issue "get_groups" cluster command
    """

    from . import groups
    importlib.reload(groups)

    await groups.get_groups(*args, **kwargs)


async def command_handler_add_group(*args, **kwargs):
    """Add a group to the device.
    ieee -- device to issue "add_group" Groups cluster command
    data -- group_id of the group to add, in 0xXXXX format
    """
    from . import groups
    importlib.reload(groups)

    await groups.add_group(*args, **kwargs)


async def command_handler_remove_group(*args, **kwargs):
    """Remove a group from the device.
    ieee -- device to issue "remove_group" Groups cluster command
    data -- group_id of the group to remove in 0xXXXX format
    """
    from . import groups
    importlib.reload(groups)

    await groups.remove_group(*args, **kwargs)


async def command_handler_remove_all_groups(*args, **kwargs):
    """Remove all groups from a device.
    ieee -- device to issue "remove all" Groups cluster command
    """
    from . import groups
    importlib.reload(groups)

    await groups.remove_all_groups(*args, **kwargs)


async def command_handler_bind_group(*args, **kwargs):
    """Add group binding to a device.
    ieee -- ieee of the remote (device configured with a binding)
    data -- group_id
    """
    from . import binds
    importlib.reload(binds)

    await binds.bind_group(*args, **kwargs)


async def command_handler_unbind_group(*args, **kwargs):
    """Remove group binding from a device.
    ieee -- ieee of the remote (device configured with a binding)
    data -- group_id
    """
    from . import binds
    importlib.reload(binds)

    await binds.unbind_group(*args, **kwargs)


async def command_handler_bind_ieee(*args, **kwargs):
    """IEEE bind device.
    ieee -- ieee of the remote (device configured with a binding)
    data -- ieee of the target device (device remote sends commands to)
    """
    from . import binds
    importlib.reload(binds)

    await binds.bind_ieee(*args, **kwargs)


async def command_handler_rejoin(app, listener, ieee, cmd, data, service):
    """Leave and rejoin command.
    data -- device ieee to allow joining through
    ieee -- ieee of the device to leave and rejoin
    """
    if ieee is None:
        _LOGGER.error("missing ieee")
        return
    _LOGGER.debug("running 'rejoin' command: %s", service)
    src = app.get_device(ieee=ieee)

    if data is None:
        await app.permit()
    else:
        await app.permit(node=convert_ieee(data))
    res = await src.zdo.request(0x0034, src.ieee, 0x01)
    _LOGGER("%s: leave and rejoin result: %s", src, ieee, res)


def command_handler_get_zll_groups(*args, **kwargs):
    from . import groups
    importlib.reload(groups)

    return groups.get_zll_groups(*args, **kwargs)


def command_handler_add_to_group(*args, **kwargs):
    """Add device to a group."""
    from . import groups
    importlib.reload(groups)

    return groups.add_to_group(*args, **kwargs)


def command_handler_remove_from_group(*args, **kwargs):
    """Remove device from a group."""
    from . import groups
    importlib.reload(groups)

    return groups.remove_from_group(*args, **kwargs)


def command_handler_sinope(*args, **kwargs):
    from . import sinope
    importlib.reload(sinope)

    return sinope.sinope_write_test(*args, **kwargs)


def command_handler_get_routes_and_neighbours(*args, **kwargs):
    """Scan a device for neighbours and routes.
    ieee -- ieee of the device to scan
    """
    from . import neighbours
    importlib.reload(neighbours)

    return neighbours.routes_and_neighbours(*args, **kwargs)


def command_handler_all_routes_and_neighbours(*args, **kwargs):
    """Scan all devices for neighbours and routes. """
    from . import neighbours
    importlib.reload(neighbours)

    return neighbours.all_routes_and_neighbours(*args, **kwargs)


def command_handler_get_node_desc(*args, **kwargs):
    from . import scan_device
    importlib.reload(scan_device)

    return scan_device.get_node_desc(*args, **kwargs)


def command_handler_leave(*args, **kwargs):
    from . import zdo
    importlib.reload(zdo)

    return zdo.leave(*args, **kwargs)

def command_handler_zigpy_deconz(*args, **kwargs):
    """Zigpy deconz test. """
    from . import zigpy_deconz
    importlib.reload(zigpy_deconz)

    return zigpy_deconz.zigpy_deconz(*args, **kwargs)


def command_handler_ezsp_set_channel(*args, **kwargs):
    """Set EZSP radio channel. """
    from . import ezsp
    importlib.reload(ezsp)

    return ezsp.set_channel(*args, **kwargs)


def command_handler_ezsp_get_token(*args, **kwargs):
    """Set EZSP radio channel. """
    from . import ezsp
    importlib.reload(ezsp)

    return ezsp.get_token(*args, **kwargs)


def command_handler_ota_notify(*args, **kwargs):
    """Set EZSP radio channel. """
    from . import ota
    importlib.reload(ota)

    return ota.notify(*args, **kwargs)
