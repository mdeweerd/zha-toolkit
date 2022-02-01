import asyncio
import logging
import re

from zigpy.exceptions import DeliveryError
from zigpy.util import retryable
from zigpy import types as t

from . import utils as u
from .params import EP_ID

LOGGER = logging.getLogger(__name__)


@retryable((DeliveryError, asyncio.TimeoutError), tries=3)
async def read_attr(cluster, attrs):
    return await cluster.read_attributes(attrs, allow_cache=False)


@retryable((DeliveryError, asyncio.TimeoutError), tries=3)
def wrapper(cmd, *args, **kwargs):
    return cmd(*args, **kwargs)


async def scan_results(device, endpoints=None):
    """Construct scan results from information available in device"""
    result = {"ieee": str(device.ieee), "nwk": f"0x{device.nwk:04x}"}

    LOGGER.debug("Scanning device 0x{:04x}", device.nwk)

    if endpoints is not None and isinstance(endpoints, int):
        endpoints = [endpoints]

    if endpoints is None or not isinstance(endpoints, list):
        endpoints = []
        for epid, _ep in device.endpoints.items():
            endpoints.append(epid)

    LOGGER.debug("Endpoints %s", endpoints)

    ep_result = []
    for epid in endpoints:
        if epid == 0:
            continue
        LOGGER.debug("scanning endpoint #%i", epid)
        if epid in device.endpoints:
            ep = device.endpoints[epid]
            result["model"] = ep.model
            result["manufacturer"] = ep.manufacturer
            endpoint = {
                "id": epid,
                "device_type": f"0x{ep.device_type:04x}",
                "profile": f"0x{ep.profile_id:04x}",
            }
            if epid != 242:
                endpoint.update(await scan_endpoint(ep))
        ep_result.append(endpoint)

    result["endpoints"] = ep_result
    return result


async def scan_endpoint(ep):
    result = {}
    clusters = {}
    for cluster in ep.in_clusters.values():
        LOGGER.debug(
            "Scanning cluster_id 0x{:04x}/'{}' input cluster".format(
                cluster.cluster_id, cluster.ep_attribute
            )
        )
        key = f"0x{cluster.cluster_id:04x}"
        clusters[key] = await scan_cluster(cluster, is_server=True)
    result["in_clusters"] = dict(sorted(clusters.items(), key=lambda k: k[0]))

    clusters = {}
    for cluster in ep.out_clusters.values():
        LOGGER.debug(
            "Scanning cluster_id 0x{:04x}/'{}' output cluster".format(
                cluster.cluster_id, cluster.ep_attribute
            )
        )
        key = f"0x{cluster.cluster_id:04x}"
        clusters[key] = await scan_cluster(cluster, is_server=True)
    result["out_clusters"] = dict(sorted(clusters.items(), key=lambda k: k[0]))
    return result


async def scan_cluster(cluster, is_server=True):
    if is_server:
        cmds_gen = "commands_generated"
        cmds_rec = "commands_received"
    else:
        cmds_rec = "commands_generated"
        cmds_gen = "commands_received"
    return {
        "cluster_id": f"0x{cluster.cluster_id:04x}",
        "name": cluster.ep_attribute,
        "attributes": await discover_attributes_extended(cluster),
        cmds_rec: await discover_commands_received(cluster, is_server),
        cmds_gen: await discover_commands_generated(cluster, is_server),
    }


async def discover_attributes_extended(cluster, manufacturer=None):
    from zigpy.zcl import foundation

    LOGGER.debug("Discovering attributes extended")
    result = {}
    to_read = []
    attr_id = 0  # Start discovery at attr_id 0
    done = False

    while not done:  # Repeat until all attributes are discovered or timeout
        try:
            done, rsp = await wrapper(
                cluster.discover_attributes_extended,
                attr_id,  # Start attribute identifier
                16,  # Number of attributes to discover in this request
                manufacturer=manufacturer,
            )
            await asyncio.sleep(0.4)
        except (DeliveryError, asyncio.TimeoutError) as ex:
            LOGGER.error(
                (
                    "Failed 'discover_attributes_extended'"
                    + " starting 0x%04x/0x%04x."
                    + " Error: %s"
                ),
                cluster.cluster_id,
                attr_id,
                ex,
            )
            break
        if isinstance(rsp, foundation.Status):
            LOGGER.error(
                "got %s status for discover_attribute starting 0x%04x/0x%04x",
                rsp,
                cluster.cluster_id,
                attr_id,
            )
            break
        LOGGER.debug("Cluster %s attr_rec: %s", cluster.cluster_id, rsp)
        for attr_rec in rsp:  # Get attribute information from response
            attr_id = attr_rec.attrid
            attr_name = cluster.attributes.get(
                attr_rec.attrid, (str(attr_rec.attrid), None)
            )[0]
            attr_type = foundation.DATA_TYPES.get(attr_rec.datatype)
            access_acl = t.uint8_t(attr_rec.acl)

            if attr_rec.datatype not in [0x48] and (
                access_acl & foundation.AttributeAccessControl.READ != 0
            ):
                to_read.append(attr_id)
            if attr_type:
                attr_type = [attr_type[1].__name__, attr_type[2].__name__]
            else:
                attr_type = f"0x{attr_rec.datatype:02x}"
            try:
                access = re.sub(
                    "^.*\\.",
                    "",
                    str(foundation.AttributeAccessControl(access_acl)),
                )
            except ValueError:
                access = "undefined"

            result[attr_id] = {
                "attribute_id": f"0x{attr_id:04x}",
                "attribute_name": attr_name,
                "value_type": attr_type,
                "access": access,
                "access_acl": access_acl,
            }
            attr_id += 1
        await asyncio.sleep(0.2)

    LOGGER.debug("Reading attrs: %s", to_read)
    chunk, to_read = to_read[:4], to_read[4:]
    while chunk:
        try:
            chunk = sorted(chunk)
            success, failed = await read_attr(cluster, chunk)
            LOGGER.debug(
                "Reading attr success: %s, failed %s", success, failed
            )
            for attr_id, value in success.items():
                if isinstance(value, bytes):
                    try:
                        value = value.split(b"\x00")[0].decode().strip()
                    except UnicodeDecodeError:
                        value = value.hex()
                result[attr_id]["attribute_value"] = value
        except (DeliveryError, asyncio.TimeoutError) as ex:
            LOGGER.error(
                "Couldn't read 0x%04x/0x%04x: %s",
                cluster.cluster_id,
                attr_id,
                ex,
            )
        chunk, to_read = to_read[:4], to_read[4:]
        await asyncio.sleep(0.3)

    return {f"0x{a_id:04x}": result[a_id] for a_id in sorted(result)}


async def discover_commands_received(cluster, is_server, manufacturer=None):
    from zigpy.zcl.foundation import Status

    LOGGER.debug("Discovering commands received")
    direction = "received" if is_server else "generated"  # noqa: F841
    result = {}
    cmd_id = 0  # Discover commands starting from 0
    done = False

    while not done:
        try:
            done, rsp = await wrapper(
                cluster.discover_commands_received,
                cmd_id,  # Start index of commands to discover
                16,  # Number of commands to discover
                manufacturer=manufacturer,
            )
            await asyncio.sleep(0.3)
        except (DeliveryError, asyncio.TimeoutError) as ex:
            LOGGER.error(
                "Failed to discover %s commands starting %s. Error: %s",
                cmd_id,
                ex,
            )
            break
        if isinstance(rsp, Status):
            LOGGER.error(
                "got %s status for discover_commands starting %s", rsp, cmd_id
            )
            break
        for cmd_id in rsp:
            cmd_data = cluster.server_commands.get(
                cmd_id, (str(cmd_id), "not_in_zcl", None)
            )
            cmd_name, cmd_args, _ = cmd_data
            if not isinstance(cmd_args, str):
                cmd_args = [arg.__name__ for arg in cmd_args]
            key = f"0x{cmd_id:02x}"
            result[key] = {
                "command_id": f"0x{cmd_id:02x}",
                "command_name": cmd_name,
                "command_arguments": cmd_args,
            }
            cmd_id += 1
        await asyncio.sleep(0.2)
    return dict(sorted(result.items(), key=lambda k: k[0]))


async def discover_commands_generated(cluster, is_server, manufacturer=None):
    from zigpy.zcl.foundation import Status

    LOGGER.debug("Discovering commands generated")
    direction = "generated" if is_server else "received"  # noqa: F841
    result = {}
    cmd_id = 0  # Initial index of commands to discover
    done = False

    while not done:
        try:
            done, rsp = await wrapper(
                cluster.discover_commands_generated,
                cmd_id,  # Start index of commands to discover
                16,  # Number of commands to discover this run
                manufacturer=manufacturer,
            )
            await asyncio.sleep(0.3)
        except (DeliveryError, asyncio.TimeoutError) as ex:
            LOGGER.error(
                "Failed to discover commands starting %s. Error: %s",
                cmd_id,
                ex,
            )
            break
        if isinstance(rsp, Status):
            LOGGER.error(
                "got %s status for discover_commands starting %s", rsp, cmd_id
            )
            break
        for cmd_id in rsp:
            cmd_data = cluster.client_commands.get(
                cmd_id, (str(cmd_id), "not_in_zcl", None)
            )
            cmd_name, cmd_args, _ = cmd_data
            if not isinstance(cmd_args, str):
                cmd_args = [arg.__name__ for arg in cmd_args]
            key = f"0x{cmd_id:02x}"
            result[key] = {
                "command_id": f"0x{cmd_id:02x}",
                "command_name": cmd_name,
                "command_args": cmd_args,
            }
            cmd_id += 1
        await asyncio.sleep(0.2)
    return dict(sorted(result.items(), key=lambda k: k[0]))


async def scan_device(
    app, listener, ieee, cmd, data, service, params, event_data
):
    if ieee is None:
        LOGGER.error("missing ieee")
        return

    LOGGER.debug("running 'scan_device' command: %s", service)

    device = app.get_device(ieee)

    scan = await scan_results(device, params[EP_ID])

    event_data["scan"] = scan

    model = scan.get("model")
    manufacturer = scan.get("manufacturer")
    if model is not None and manufacturer is not None:
        ieee_tail = "".join([f"{o:02x}" for o in ieee[-4:]])
        file_name = f"{model}_{manufacturer}_{ieee_tail}_scan_results.txt"
    else:
        ieee_tail = "".join([f"{o:02x}" for o in ieee])
        file_name = f"{ieee_tail}_scan_results.txt"

    u.write_json_to_file(
        scan,
        subdir="scans",
        fname=file_name,
        desc="scan results",
        listener=listener,
    )
