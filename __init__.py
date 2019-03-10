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
    from zigpy.zcl.clusters.general import Groups
    _LOGGER.debug("running 'fmr group' command: %s", service)
    if ieee is None:
        return
    device = app.get_device(ieee=ieee)
    grp_id = int(data, base=16)
    for ep_id, ep in device.endpoints.items():
        if ep_id == 0:
            continue
        if Groups.cluster_id in ep.in_clusters:
            grp_cluster = ep.in_clusters[Groups.cluster_id]
            break
    name_support = await grp_cluster.read_attributes(['name_support'])
    _LOGGER.debug("Group on 0x%04x name support: %s", device.nwk, name_support)

    all_groups = await grp_cluster.get_membership([])
    _LOGGER.debug("Groups on 0x%04x : %s", device.nwk, all_groups)


async def command_handler_set_group(app, listener, ieee, cmd, data, service):
    from zigpy.zcl.clusters.general import Groups
    _LOGGER.debug("running 'fmr group' command: %s", service)
    if ieee is None:
        return
    device = app.get_device(ieee=ieee)
    grp_id = int(data, base=16)
    for ep_id, ep in device.endpoints.items():
        if ep_id == 0:
            continue
        if Groups.cluster_id in ep.in_clusters:
            grp_cluster = ep.in_clusters[Groups.cluster_id]
            break
    if not grp_id:
        return
    res = await grp_cluster.add(grp_id, [])
    _LOGGER.debug("0x%04x: Setting group 0x%04x: %s", device.nwk, grp_id, res)


async def command_handler_bind_group(app, listener, ieee, cmd, data, service):
    from zigpy.zdo.types import MultiAddress
    from zigpy import types as t
    _LOGGER.debug("running 'bind group' command: %s", service)
    if ieee is None:
        return
    device = app.get_device(ieee=ieee)
    grp_id = int(data, base=16)
    if not grp_id:
        return
    zdo = device.zdo
    src_cls = [6, 8]

    # find src ep_id
    for ep_id, ep in device.endpoints.items():
        if ep_id == 0:
            continue
        if src_cls[0] in ep.out_clusters:
            src_ep = ep_id
            break
    if not src_ep:
        _LOGGER.debug("0x%04x: couldn't find client ep", device.nwk)
        return
    dst_addr = MultiAddress()
    dst_addr.addrmode = t.uint8_t(1)
    dst_addr.nwk = t.uint16_t(grp_id)
    for src_cluster in src_cls:
        _LOGGER.debug("0x%04x: binding %s, ep: %s, cluster: %s",
                      device.nwk, str(device.ieee), src_ep, src_cluster)
        res = await zdo.request(0x0021, ieee, src_ep, src_cluster, dst_addr)
        _LOGGER.debug("0x%04x: binding group 0x%04x: %s",
                      device.nwk, grp_id, res)


async def command_handler_unbind_group(app, listener, ieee, cmd, data, service):
    from zigpy.zdo.types import MultiAddress
    from zigpy import types as t
    _LOGGER.debug("running 'bind group' command: %s", service)
    if ieee is None:
        return
    device = app.get_device(ieee=ieee)
    grp_id = int(data, base=16)
    if not grp_id:
        return
    zdo = device.zdo
    src_cls = [6, 8]

    # find src ep_id
    for ep_id, ep in device.endpoints.items():
        if ep_id == 0:
            continue
        if src_cls[0] in ep.out_clusters:
            src_ep = ep_id
            break
    if not src_ep:
        _LOGGER.debug("0x%04x: couldn't find client ep", device.nwk)
        return
    dst_addr = MultiAddress()
    dst_addr.addrmode = t.uint8_t(1)
    dst_addr.nwk = t.uint16_t(grp_id)
    for src_cluster in src_cls:
        _LOGGER.debug("0x%04x: unbinding %s, ep: %s, cluster: %s",
                      device.nwk, str(device.ieee), src_ep, src_cluster)
        res = await zdo.request(0x0022, ieee, src_ep, src_cluster, dst_addr)
        _LOGGER.debug("0x%04x: unbinding group 0x%04x: %s",
                      device.nwk, grp_id, res)
