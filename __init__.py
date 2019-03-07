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
