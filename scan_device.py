import asyncio
import logging
from collections import OrderedDict

from zigpy.util import retryable
from zigpy.exceptions import DeliveryError


_LOGGER = logging.getLogger(__name__)


@retryable((DeliveryError, asyncio.TimeoutError), tries=5)
async def read_attr(cluster, attrs):
    return await cluster.read_attributes(attrs, allow_cache=False)


@retryable((DeliveryError, asyncio.TimeoutError), tries=5)
def wrapper(cmd, *args, **kwargs):
    return cmd(*args, **kwargs)


async def scan_results(device):
    result = {
        'ieee': str(device.ieee),
        'nwk': '0x{:04x}'.format(device.nwk),
    }

    _LOGGER.debug("Scanning device 0x{:04x}".format(device.nwk))

    endpoints = []
    for epid, ep in device.endpoints.items():
        if epid == 0:
            continue
        _LOGGER.debug("scanning endpoint #%i", epid)
        result['model'] = ep.model
        result['manufacturer'] = ep.manufacturer
        endpoint = {
            'id': epid,
            'device_type': '0x{:04x}'.format(ep.device_type),
            'profile': '0x{:04x}'.format(ep.profile_id),
        }
        endpoint.update(await scan_endpoint(ep))
        endpoints.append(endpoint)

    result['endpoints'] = endpoints
    return result


async def scan_endpoint(ep):
    result = {}
    clusters = {}
    for cluster in ep.in_clusters.values():
        _LOGGER.debug(
            "Scanning cluster_id 0x{:04x}/'{}' input cluster".format(
                cluster.cluster_id, cluster.ep_attribute))
        key = '0x{:04x}'.format(cluster.cluster_id)
        clusters[key] = await scan_cluster(cluster, is_server=True)
    result['in_clusters'] = OrderedDict(
        sorted(clusters.items(), key=lambda k: k[0])
    )

    clusters = {}
    for cluster in ep.out_clusters.values():
        _LOGGER.debug(
            "Scanning cluster_id 0x{:04x}/'{}' output cluster".format(
                cluster.cluster_id, cluster.ep_attribute))
        key = '0x{:04x}'.format(cluster.cluster_id)
        clusters[key] = await scan_cluster(cluster, is_server=True)
    result['out_clusters'] = OrderedDict(
        sorted(clusters.items(), key=lambda k: k[0])
    )
    return result


async def scan_cluster(cluster, is_server=True):
    if is_server:
        cmds_gen = 'commands_generated'
        cmds_rec = 'commands_received'
    else:
        cmds_rec = 'commands_generated'
        cmds_gen = 'commands_received'
    return {
        'cluster_id': '0x{:04x}'.format(cluster.cluster_id),
        'name': cluster.ep_attribute,
        'attributes': await discover_attributes_extended(cluster),
        cmds_rec: await discover_commands_received(cluster, is_server),
        cmds_gen: await discover_commands_generated(cluster, is_server),
    }


async def discover_attributes_extended(cluster, manufacturer=None):
    from zigpy.zcl import foundation

    _LOGGER.debug("Discovering attributes extended")
    result = {}
    attr_id = 0
    done = False

    while not done:
        try:
            done, rsp = await wrapper(
                cluster.discover_attributes_extended, attr_id, 16, manufacturer)
        except DeliveryError as ex:
            _LOGGER.error(
                "Failed to discover attributes extended starting %s. Error: {}".
                format(attr_id, ex))
            break
        if isinstance(rsp, foundation.Status):
            _LOGGER.error("got %s status for discover_attribute starting %s", rsp, attr_id)
            break
        for attr_rec in rsp:
            attr_id = attr_rec.attrid
            attr_name = cluster.attributes.get(attr_rec.attrid, (str(attr_rec.attrid), None))[0]
            attr_type = foundation.DATA_TYPES.get(attr_rec.datatype)
            if attr_type:
                attr_type = [attr_type[1].__name__, attr_type[2].__name__]
            else:
                attr_type = '0x{:02x}'.format(attr_rec.datatype)
            try:
                access = foundation.AttributeAccessControl(attr_rec.acl).name
            except ValueError:
                access = 'undefined'

            result[attr_id] = {
                'attribute_id': '0x{:04x}'.format(attr_id),
                'attribute_name': attr_name,
                'value_type': attr_type,
                'access': access
            }
            attr_id += 1
        await asyncio.sleep(0.2)

    to_read = list(result.keys())
    _LOGGER.debug("Reading attrs: %s", to_read)
    chunk, to_read = to_read[:4], to_read[4:]
    while chunk:
        try:
            success, failed = await read_attr(cluster, chunk)
            _LOGGER.debug("Reading attr success: %s, failed %s", success, failed)
            for attr_id, value in success.items():
                if isinstance(value, bytes):
                    try:
                        value = value.split(b'\x00')[0].decode().strip()
                    except UnicodeDecodeError:
                        value = value.hex()
                result[attr_id]['attribute_value'] = value
        except DeliveryError as exc:
            _LOGGER.error("Couldn't read attr_id %i: %s", attr_id, exc)
        chunk, to_read = to_read[:4], to_read[4:]

    return OrderedDict(
        [('0x{:04x}'.format(a_id), result[a_id]) for a_id in sorted(result)]
    )


async def discover_commands_received(cluster, is_server, manufacturer=None):
    from zigpy.zcl.foundation import Status

    _LOGGER.debug("Discovering commands received")
    direction = 'received' if is_server else 'generated'
    result = {}
    cmd_id = 0
    done = False

    while not done:
        try:
            done, rsp = await wrapper(cluster.discover_commands_received,
                                      cmd_id, 16, manufacturer=manufacturer)
        except DeliveryError as ex:
            _LOGGER.error(
                "Failed to discover commands starting %s. Error: {}".format(
                    cmd_id, ex))
            break
        if isinstance(rsp, Status):
            _LOGGER.error("got %s status for discover_attribute starting %s", rsp, cmd_id)
            break
        for cmd_id in rsp:
            cmd_data = cluster.server_commands.get(cmd_id, (str(cmd_id), 'not_in_zcl', None))
            cmd_name, cmd_args, _ = cmd_data
            if not isinstance(cmd_args, str):
                cmd_args = [arg.__name__ for arg in cmd_args]
            key = '0x{:02x}'.format(cmd_id)
            result[key] = {
                'command_id': '0x{:02x}'.format(cmd_id),
                'command_name': cmd_name,
                'command_arguments': cmd_args
            }
            cmd_id += 1
        await asyncio.sleep(0.2)
    return OrderedDict(sorted(result.items(), key=lambda k: k[0]))


async def discover_commands_generated(cluster, is_server, manufacturer=None):
    from zigpy.zcl.foundation import Status
    direction = 'generated' if is_server else 'received'
    result = {}
    cmd_id = 0
    done = False

    while not done:
        try:
            done, rsp = await wrapper(cluster.discover_commands_generated,
                                      cmd_id, 16, manufacturer=manufacturer)
        except DeliveryError as ex:
            _LOGGER.error(
                "Failed to discover commands starting %s. Error: {}".format(cmd_id, ex))
            break
        if isinstance(rsp, Status):
            _LOGGER.error("got %s status for discover_attribute starting %s", rsp, cmd_id)
            break
        for cmd_id in rsp:
            cmd_data = cluster.client_commands.get(cmd_id, (str(cmd_id), 'not_in_zcl', None))
            cmd_name, cmd_args, _ = cmd_data
            if not isinstance(cmd_args, str):
                cmd_args = [arg.__name__ for arg in cmd_args]
            key = '0x{:02x}'.format(cmd_id)
            result[key] = {
                'command_id': '0x{:02x}'.format(cmd_id),
                'command_Name': cmd_name,
                'command_args': cmd_args,
            }
            cmd_id += 1
        await asyncio.sleep(0.2)
    return OrderedDict(sorted(result.items(), key=lambda k: k[0]))
