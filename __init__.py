import importlib
import logging
import os

from homeassistant.util.json import save_json


_LOGGER = logging.getLogger(__name__)


async def default_command(app, listener, ieee, cmd, data, service):
    _LOGGER.debug("running default command: %s", service)


async def command_handler_handle_join(app, listener, ieee, cmd, data, service):
    _LOGGER.debug("running 'handle_join' command: %s", service)
    if ieee is None:
        return
    app.handle_join(int(data), ieee, 0)


async def command_handler_scan_device(app, listener, ieee, cmd, data, service):
    from . import scan_device
    importlib.reload(scan_device)

    if ieee is None:
        return
    _LOGGER.debug("running 'scan_device' command: %s", service)
    device = app.get_device(ieee=ieee)
    scan = await scan_device.scan_results(device)

    model = scan.get('model')
    manufacturer = scan.get('manufacturer')
    if model is not None and manufacturer is not None:
        ieee_tail = ''.join(['%02x' % (o, ) for o in ieee[-4:]])
        file_name = '{}_{}_{}_scan_results.txt'.format(model, manufacturer,
                                                       ieee_tail)
    else:
        ieee_tail = ''.join(['%02x' % (o, ) for o in ieee])
        file_name = '{}_scan_results.txt'.format(ieee_tail)

    file_name = os.path.join(
        listener._hass.config.config_dir, 'scans', file_name)
    save_json(file_name, scan)
    _LOGGER.debug("Finished writing scan results int '%s'", file_name)


async def command_handler_scan_neighbors(app, listener, ieee, cmd, data,
                                         service):
    _LOGGER.debug("Scanning neigbour: %s", service)
    zha_dev = listener.get_device_entity(service.data.get('ieee_address'))
    if zha_dev is not None:
        await zha_dev.async_update_tech_info()


async def command_handler_get_ieee(app, listener, ieee, cmd, data, service):
    if ieee is None:
        return

    _LOGGER.debug("running 'get_ieee' command: %s", service)
    nwk = await app._ezsp.lookupNodeIdByEui64(ieee)
    _LOGGER.debug("NWK 0x%04x for %s node", nwk, ieee)


async def command_handler_get_groups(app, listener, ieee, cmd, data, service):
    from . import groups
    importlib.reload(groups)

    _LOGGER.debug("running 'fmr group' command: %s", service)
    if ieee is None:
        return
    src_dev = app.get_device(ieee=ieee)
    await groups.get_groups(src_dev)


async def command_handler_set_group(app, listener, ieee, cmd, data, service):
    from . import groups
    importlib.reload(groups)

    _LOGGER.debug("running 'fmr group' command: %s", service)
    if ieee is None or not data:
        return
    src_dev = app.get_device(ieee=ieee)
    group_id = int(data, base=16)
    await groups.set_group(src_dev, group_id)


async def command_handler_bind_group(app, listener, ieee, cmd, data, service):
    from . import binds
    importlib.reload(binds)

    _LOGGER.debug("running 'bind group' command: %s", service)
    if ieee is None:
        return
    src_dev = app.get_device(ieee=ieee)
    if not data:
        return
    group_id = int(data, base=16)

    await binds.bind_group(src_dev, group_id)


async def command_handler_unbind_group(app, listener, ieee, cmd, data,
                                       service):
    from . import binds
    importlib.reload(binds)

    _LOGGER.debug("running 'bind group' command: %s", service)
    if ieee is None or not data:
        return
    src_dev = app.get_device(ieee=ieee)
    group_id = int(data, base=16)

    await binds.unbind_group(src_dev, group_id)


async def command_handler_bind_ieee(app, listener, ieee, cmd, data, service):
    from zigpy import types as t
    from . import binds
    importlib.reload(binds)

    if ieee is None or not data:
        return
    _LOGGER.debug("running 'bind ieee' command: %s", service)
    src_dev = app.get_device(ieee=ieee)
    dst_ieee = t.EUI64([t.uint8_t(p, base=16) for p in data.split(':')])
    dst_dev = app.get_device(ieee=dst_ieee)

    await binds.bind_ieee(src_dev, dst_dev)
