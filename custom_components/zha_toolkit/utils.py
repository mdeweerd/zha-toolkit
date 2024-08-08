from __future__ import annotations

import asyncio
import functools
import json
import logging
import os
import re
import typing
from enum import Enum

import aiofiles
import zigpy
from homeassistant.core import HomeAssistant

try:
    from homeassistant.components.zha import Gateway as ZHAGateway
except ImportError:
    from homeassistant.components.zha.core.gateway import ZHAGateway

from homeassistant.components import zha

try:
    from homeassistant.components.zha import helpers as zha_helpers
except ImportError:
    zha_helpers = None

from homeassistant.util import dt as dt_util
from pkg_resources import get_distribution, parse_version
from zigpy import types as t
from zigpy.exceptions import ControllerException, DeliveryError
from zigpy.zcl import foundation as f

from .params import INTERNAL_PARAMS as p
from .params import USER_PARAMS as P

LOGGER = logging.getLogger(__name__)

# pylint: disable=too-many-lines

HA_VERSION = get_distribution("homeassistant").version
ZIGPY_VERSION = get_distribution("zigpy").version

if parse_version(HA_VERSION) < parse_version("2023.4"):
    # pylint: disable=ungrouped-imports
    from homeassistant.util.json import save_json
else:
    # pylint: disable=ungrouped-imports
    from homeassistant.helpers.json import save_json

if parse_version(HA_VERSION) >= parse_version("2024.6"):
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er

if typing.TYPE_CHECKING:
    VERSION_TIME: float = 0.0
    VERSION: str = "Unknown"
    MANIFEST: dict[str, str | list[str]] = {}


def get_zha_gateway(hass: HomeAssistant) -> ZHAGateway:
    """Get the ZHA gateway object."""
    if parse_version(HA_VERSION) >= parse_version("2024.8"):
        return zha_helpers.get_zha_gateway(hass)
    if isinstance(zha, dict):
        return zha.get("zha_gateway", None)
    return zha.gateway


def get_zha_gateway_hass(
    hass: HomeAssistant,
) -> ZHAGateway | zha_helpers.ZHAGatewayProxy:
    """
    Get the ZHA gateway proxy object.

    Fallback to the gateway object prior to 2024.8 which still has an attached
    HASS object.
    """
    if parse_version(HA_VERSION) >= parse_version("2024.8"):
        return zha_helpers.get_zha_gateway_proxy(hass)
    return get_zha_gateway(hass)


def getHaVersion() -> str:
    """Get HA Version"""
    return HA_VERSION


def getZigpyVersion() -> str:
    """Get zigpy Version"""
    return ZIGPY_VERSION


async def getVersion() -> str:
    # pylint: disable=global-variable-undefined,used-before-assignment
    # pylint: disable=global-statement
    global VERSION_TIME
    global VERSION
    global MANIFEST

    try:
        VERSION
    except NameError:
        VERSION_TIME = 0.0
        VERSION = "Unknown"
        MANIFEST = {}

    fname = os.path.dirname(__file__) + "/manifest.json"

    ftime: float = VERSION_TIME

    try:
        ntime = os.path.getmtime(fname)
        if ftime != ntime:
            ftime = ntime
            VERSION = "Unknown"
            MANIFEST = {}
    except Exception:
        MANIFEST = {}

    if (VERSION is None and ftime != 0) or (ftime != VERSION_TIME):
        # No version, or file change -> get version again
        LOGGER.debug(f"Read version from {fname} {ftime}<>{VERSION_TIME}")

        async with aiofiles.open(fname, mode="r", encoding="utf_8") as infile:
            json_raw = await infile.read()
            MANIFEST = json.loads(json_raw)

        if MANIFEST is not None:
            if "version" in MANIFEST.keys():
                v = MANIFEST["version"]
                VERSION = v if isinstance(v, str) else "Invalid manifest"
                if VERSION == "0.0.0":
                    VERSION = "dev"

    return VERSION


# Convert string to int if possible or return original string
#  (Returning the original string is useful for named attributes)
def str2int(s):  # pylint: disable=too-many-return-statements
    if not isinstance(s, str):
        return s
    if s.lower() == "false":
        return 0
    if s.lower() == "true":
        return 1
    if s.startswith("0x") or s.startswith("0X"):
        return int(s, 16)
    if s.startswith("0") and s.isnumeric():
        return int(s, 8)
    if s.startswith("b") and s[1:].isnumeric():
        return int(s[1:], 2)
    if s.isnumeric():
        return int(s)
    # By default, return the same value
    return s


# Convert string to best boolean representation
def str2bool(s):
    if s is None or s == "":
        return False
    if s is True or s is False:
        return s
    return str2int(s) != 0


def normalize_filename(filename: str) -> str:
    """
    Normalize filename so that slashes and other problematic
    characters are replaced with hyphen
    """
    result = "".join([c if re.match(r"[\w.]", c) else "-" for c in filename])
    LOGGER.debug(f"Normalize {filename}->{result}")
    return "".join([c if re.match(r"[\w.]", c) else "-" for c in filename])


class RadioType(Enum):
    UNKNOWN = 0
    ZNP = 1
    EZSP = 2
    BELLOWS = 2
    DECONZ = 3
    ZIGPY_CC = 4
    XBEE = 5
    ZIGATE = 6


def isJsonable(x):
    try:
        json.dumps(x)
        return True
    except (TypeError, OverflowError):
        return False


def get_radiotype(app):
    if hasattr(app, "_znp"):
        return RadioType.ZNP
    if hasattr(app, "_ezsp"):
        return RadioType.EZSP
    if hasattr(app, "_api"):
        try:
            from zigpy_deconz.api import Deconz

            if isinstance(app._api, Deconz):
                return RadioType.DECONZ
        except Exception:  # nosec
            pass

        try:
            from zigpy_zigate.api import ZiGate

            if isinstance(app._api, ZiGate):
                return RadioType.ZIGATE
        except Exception:  # nosec
            pass

        try:
            import zigpy_xbee

            if isinstance(app._api, zigpy_xbee.api.XBee):
                return RadioType.XBEE
        except Exception:  # nosec
            pass

        LOGGER.debug("Did not recognize _api '%s'", type(app._api))
        # try:
        #    from zigpy_cc.api import API
        #    if isinstance(app._api, API):
        #        return RadioType.ZIGPY_CC
        # except Exception:  # nosec
        #    pass

    LOGGER.debug("Type recognition for '%s' not implemented", type(app))
    return RadioType.UNKNOWN


def get_radio(app):
    if hasattr(app, "_znp"):
        return app._znp
    if hasattr(app, "_ezsp"):
        return app._ezsp
    if hasattr(app, "_api"):
        return app._api
    LOGGER.debug("Type recognition for '%s' not implemented", type(app))
    return None


def get_radio_version(app):
    # pylint: disable=R0911
    if hasattr(app, "_znp"):
        import zigpy_znp

        if hasattr(zigpy_znp, "__version__"):
            return zigpy_znp.__version__

        return get_distribution("zigpy_znp").version
    if hasattr(app, "_ezsp"):
        import bellows

        if hasattr(bellows, "__version__"):
            return bellows.__version__

        return get_distribution("bellows").version
    if hasattr(app, "_api"):
        rt = get_radiotype(app)
        if rt == RadioType.DECONZ:
            import zigpy_deconz

            if hasattr(zigpy_deconz, "__version__"):
                return zigpy_deconz.__version__

            return get_distribution("zigpy_deconz").version
        if rt == RadioType.ZIGATE:
            import zigpy_zigate

            if hasattr(zigpy_zigate, "__version__"):
                return zigpy_zigate.__version__

            return get_distribution("zigpy_zigate").version
        if rt == RadioType.XBEE:
            import zigpy_xbee

            if hasattr(zigpy_xbee, "__version__"):
                return zigpy_xbee.__version__

            return get_distribution("zigpy_xbee").version

        # if rt == RadioType.ZIGPY_CC:
        #     import zigpy_cc
        #     return zigpy_cc.__version__

    LOGGER.debug("Type recognition for '%s' not implemented", type(app))
    return None


# Get zigbee IEEE address (EUI64) for the reference.
#  Reference can be entity, device, or IEEE address
async def get_ieee(app, listener, ref):
    # pylint: disable=too-many-return-statements
    # LOGGER.error("######### Get IEEE: %s %r", type(ref), ref)
    if isinstance(ref, str):
        # Check if valid ref address
        if ref.count(":") == 7:
            return t.EUI64.convert(ref)

        # Check if network address
        nwk = str2int(ref)
        if isinstance(nwk, int) and 0x0000 <= nwk <= 0xFFF7:
            device = app.get_device(nwk=nwk)
            if device is None:
                return None

            # Device is found
            LOGGER.debug("NWK addr 0x%04x -> %s", nwk, device.ieee)
            return device.ieee

        # Todo: check if NWK address
        entity_registry = (
            # Deprecated >= 2022.6.0
            await get_hass(
                listener
            ).helpers.entity_registry.async_get_registry()
            if not is_ha_ge("2022.6")
            else get_hass(listener).helpers.entity_registry.async_get(
                get_hass(listener)
            )
            if not is_ha_ge("2024.6")
            else er.async_get(get_hass(listener))
        )

        device_registry = (
            # Deprecated >= 2022.6.0
            await get_hass(
                listener
            ).helpers.device_registry.async_get_registry()
            if not is_ha_ge("2022.6")
            else get_hass(listener).helpers.device_registry.async_get(
                get_hass(listener)
            )
            if not is_ha_ge("2024.6")
            else dr.async_get(get_hass(listener))
        )
        registry_device = device_registry.async_get(ref)

        if registry_device is None:
            # LOGGER.debug("registry %s",entity_registry)
            registry_entity = entity_registry.async_get(ref)
            if registry_entity is None:
                LOGGER.error("No device found for '%s'", ref)
                return None
            if registry_entity.platform != "zha":
                LOGGER.error("Not a ZHA device : '%s'", ref)
                return None

            LOGGER.debug("Found registry_entity %r", registry_entity)
            registry_device = device_registry.async_get(
                registry_entity.device_id
            )

        LOGGER.debug("Found registry_device %r", registry_device)
        for identifier in registry_device.identifiers:
            if identifier[0] == "zha":
                return t.EUI64.convert(identifier[1])

        LOGGER.error("Not a ZHA device : '%s'", ref)
        return None

    # Other type, suppose it's already an EUI64
    return ref


async def get_device(app, listener, reference):
    """
    Get a zigbee device instance for the reference.
    Reference can be entity, device, or IEEE address
    """
    ieee = await get_ieee(app, listener, reference)
    LOGGER.debug("IEEE for get_device: %s %s", reference, ieee)
    return app.get_device(ieee)


# Save state to db
def set_state(
    hass, entity_id, value, key=None, allow_create=False, force_update=False
):
    stateObj = hass.states.get(entity_id)
    if stateObj is None and allow_create is not True:
        LOGGER.warning("Entity_id '%s' not found", entity_id)
        return

    if stateObj is not None:
        # Copy existing attributes, to update selected item
        stateAttrs = stateObj.attributes.copy()
    else:
        stateAttrs = {}

    # LOGGER.debug("Before: entity:%s key:%s value:%s attrs:%s",
    #              entity_id, key, value, stateAttrs)
    if key is not None:
        stateAttrs[key] = value
        if stateObj is not None:
            # Copy existing state, to update selected item
            value = stateObj.state
        else:
            value = None

    # LOGGER.debug("entity:%s key:%s value:%s attrs:%s",
    #              entity_id, key, value, stateAttrs)

    # Store to DB_state
    hass.states.async_set(
        entity_id=entity_id,
        new_state=value,
        attributes=stateAttrs,
        force_update=force_update,
        context=None,
    )


# Find endpoint matching in_cluster
def find_endpoint(dev, cluster_id):
    cnt = 0
    endpoint_id = None

    for key, value in dev.endpoints.items():
        if key == 0:
            continue
        if cluster_id in value.in_clusters:
            endpoint_id = key
            cnt = cnt + 1

    if cnt == 0:
        for key, value in dev.endpoints.items():
            if key == 0:
                continue
            if cluster_id in value.in_clusters:
                endpoint_id = key
                cnt = cnt + 1

        if cnt == 0:
            LOGGER.error("No Endpoint found for cluster '%s'", cluster_id)
        else:
            LOGGER.error(
                "No Endpoint found for in_cluster, found out_cluster '%s'",
                cluster_id,
            )

    if cnt > 1:
        endpoint_id = None
        LOGGER.error(
            "More than one Endpoint found for cluster '%s'", cluster_id
        )
    if cnt == 1:
        LOGGER.debug(
            "Endpoint %s found for cluster '%s'", endpoint_id, cluster_id
        )

    return endpoint_id


def get_cluster_from_params(
    dev, params: dict[str, int | str | list[int | str]], event_data: dict
):
    """
    Get in or outcluster (and endpoint) with best
    correspondence to values provided in params
    """

    cluster_id = params[p.CLUSTER_ID]
    if not isinstance(cluster_id, int):
        attr_id = params[p.ATTR_ID]
        if isinstance(attr_id, str):
            for _epid, ep in dev.endpoints.items():
                if _epid == 0:
                    continue
                for _cid, cluster in ep.in_clusters.items():
                    if attr_id in cluster.attributes_by_name:
                        cluster_id = _cid
                        LOGGER.debug("Found Cluster:0x%04X", cluster_id)
                        break

        if not isinstance(cluster_id, int):
            msg = f"Cluster must be numeric {cluster_id}"
            raise ValueError(msg)

    # Get best endpoint
    if params[p.EP_ID] is None or params[p.EP_ID] == "":
        params[p.EP_ID] = find_endpoint(dev, cluster_id)

    if params[p.EP_ID] not in dev.endpoints:
        msg = (
            f"No endpoint {params[p.EP_ID]}"
            f" and no cluster 0x{cluster_id:04X}"
            f" for '{dev.ieee!r}'"
        )
        LOGGER.error(msg)
        raise ValueError(msg)

    cluster = None
    if cluster_id not in dev.endpoints[params[p.EP_ID]].in_clusters:
        msg = "InCluster 0x{:04X} not found for '{}', endpoint {}".format(
            cluster_id, repr(dev.ieee), params[p.EP_ID]
        )
        if cluster_id in dev.endpoints[params[p.EP_ID]].out_clusters:
            msg = f'"Using" OutCluster. {msg}'
            LOGGER.warning(msg)
            if "warnings" not in event_data:
                event_data["warnings"] = []
            event_data["warnings"].append(msg)
            cluster = dev.endpoints[params[p.EP_ID]].out_clusters[cluster_id]
        else:
            LOGGER.error(msg)
            raise ValueError(msg)
    else:
        cluster = dev.endpoints[params[p.EP_ID]].in_clusters[cluster_id]

    return cluster


def value_to_jsonable(value):
    if not isJsonable(value):
        LOGGER.debug(
            "Can't convert %r to JSON, serializing if possible.", value
        )
        if callable(getattr(value, "serialize", None)):
            # Serialization results in "bytes"
            value = value.serialize()
        if isinstance(value, bytes):
            # "bytes" is not compatible with json, convert
            # try:
            #    value = value.split(b"\x00")[0].decode().strip()
            # except:
            #    value = value.hex()

            try:
                value = str(value, encoding="ascii")
            except Exception:
                value = "0x" + value.hex()
        else:
            # Anything else: get a textual representation
            value = repr(value)
    return value


def dict_to_jsonable(src_dict):
    result = {}
    if isJsonable(src_dict):
        return src_dict
    for key, value in src_dict.items():
        result[key] = value_to_jsonable(value)

    return result


def write_json_to_file(
    data, subdir, fname, desc, listener=None, normalize_name=False
):
    if listener is None or subdir == "local":
        base_dir = os.path.dirname(__file__)
    else:
        base_dir = get_hass(listener).config.config_dir

    out_dir = os.path.join(base_dir, subdir)
    if not os.path.isdir(out_dir):
        os.mkdir(out_dir)

    if normalize_name:
        file_name = os.path.join(out_dir, normalize_filename(fname))
    else:
        file_name = os.path.join(out_dir, fname)

    save_json(file_name, data)
    LOGGER.debug(f"Finished writing {desc} in '{file_name}'")


def helper_save_json(file_name: str, data: typing.Any):
    """Helper because the actual method depends on the HA version"""
    save_json(file_name, data)


def append_to_csvfile(
    fields,
    subdir,
    fname,
    desc,
    listener=None,
    overwrite=False,
    normalize_name=False,
):
    if listener is None or subdir == "local":
        base_dir = os.path.dirname(__file__)
    else:
        base_dir = get_hass(listener).config.config_dir

    out_dir = os.path.join(base_dir, subdir)
    if not os.path.isdir(out_dir):
        os.mkdir(out_dir)

    if normalize_name:
        file_name = os.path.join(out_dir, normalize_filename(fname))
    else:
        file_name = os.path.join(out_dir, fname)

    import csv

    with open(file_name, "w" if overwrite else "a", encoding="utf_8") as out:
        writer = csv.writer(out)
        writer.writerow(fields)

    if overwrite:
        LOGGER.debug(f"Wrote {desc} to '{file_name}'")
    else:
        LOGGER.debug(f"Appended {desc} to '{file_name}'")


def record_read_data(
    read_resp, cluster: zigpy.zcl.Cluster, params, listener=None
):
    """Record result from attr_write to CSV file if configured"""
    if params[p.CSV_FILE] is None:
        return

    date_str = dt_util.utcnow().isoformat()

    for attr_id, read_val in read_resp[0].items():
        fields = []
        if params[p.CSV_LABEL] is not None:
            attr_name = params[p.CSV_LABEL]
        else:
            python_type = type(read_resp[0][attr_id])
            attr_type = f.DATA_TYPES.pytype_to_datatype_id(python_type)

            try:
                attr_def = cluster.attributes.get(
                    attr_id, (str(attr_id), None)
                )
                if is_zigpy_ge("0.50.0") and isinstance(
                    attr_def, f.ZCLAttributeDef
                ):
                    attr_name = attr_def.name
                else:
                    attr_name = attr_def[0]
            except Exception:
                attr_name = attr_id

        fields.append(date_str)
        fields.append(cluster.name)
        fields.append(attr_name)
        fields.append(read_val)
        fields.append(f"0x{attr_id:04X}")
        fields.append(f"0x{cluster.cluster_id:04X}")
        fields.append(cluster.endpoint.endpoint_id)
        fields.append(str(cluster.endpoint.device.ieee))
        fields.append(
            f"0x{params[p.MANF]:04X}" if params[p.MANF] is not None else ""
        )
        fields.append(f"0x{attr_type:02X}" if attr_type is not None else "")

        append_to_csvfile(
            fields,
            "csv",
            params[p.CSV_FILE],
            f"{attr_name}={read_val}",
            listener=listener,
        )


def get_attr_id(cluster, attribute):
    # Try to get attribute id from cluster
    try:
        if attribute in cluster.attributes_by_name:
            # return cluster.attributes_by_name(attribute)
            return cluster.attributes_by_name[attribute].id
    except Exception:
        return None

    # By default, just try to convert it to an int
    return str2int(attribute)


def get_attr_type(cluster, attr_id):
    """Get type for attribute in cluster, or None if not found"""
    try:
        attr_def = cluster.attributes.get(attr_id, (None, f.Unknown))
        if is_zigpy_ge("0.50.0") and isinstance(attr_def, f.ZCLAttributeDef):
            attr_type = attr_def.type
        else:
            attr_type = attr_def[1]

        return f.DATA_TYPES.pytype_to_datatype_id(attr_type)
    except Exception:  # nosec
        LOGGER.debug("Could not find type for %s in %r", attr_id, cluster)

    return None


def attr_encode(attr_val_in, attr_type):  # noqa C901
    # Convert attribute value (provided as a string)
    # to appropriate attribute value.
    # If the attr_type is not set, only read the attribute.
    attr_obj = None
    if attr_type == 0x10:
        compare_val = str2int(attr_val_in)
        attr_obj = f.TypeValue(attr_type, t.Bool(compare_val))
    elif attr_type == 0x20:
        compare_val = str2int(attr_val_in)
        attr_obj = f.TypeValue(attr_type, t.uint8_t(compare_val))
    elif attr_type == 0x21:
        compare_val = str2int(attr_val_in)
        attr_obj = f.TypeValue(attr_type, t.uint16_t(compare_val))
    elif attr_type == 0x22:
        compare_val = str2int(attr_val_in)
        attr_obj = f.TypeValue(attr_type, t.uint24_t(compare_val))
    elif attr_type == 0x23:
        compare_val = str2int(attr_val_in)
        attr_obj = f.TypeValue(attr_type, t.uint32_t(compare_val))
    elif attr_type == 0x24:
        compare_val = str2int(attr_val_in)
        attr_obj = f.TypeValue(attr_type, t.uint32_t(compare_val))
    elif attr_type == 0x25:
        compare_val = str2int(attr_val_in)
        attr_obj = f.TypeValue(attr_type, t.uint48_t(compare_val))
    elif attr_type == 0x26:
        compare_val = str2int(attr_val_in)
        attr_obj = f.TypeValue(attr_type, t.uint56_t(compare_val))
    elif attr_type == 0x27:
        compare_val = str2int(attr_val_in)
        attr_obj = f.TypeValue(attr_type, t.uint64_t(compare_val))
    elif attr_type == 0x28:
        compare_val = str2int(attr_val_in)
        attr_obj = f.TypeValue(attr_type, t.int8s(compare_val))
    elif attr_type == 0x29:
        compare_val = str2int(attr_val_in)
        attr_obj = f.TypeValue(attr_type, t.int16s(compare_val))
    elif attr_type == 0x2A:
        compare_val = str2int(attr_val_in)
        attr_obj = f.TypeValue(attr_type, t.int24s(compare_val))
    elif attr_type == 0x2B:
        compare_val = str2int(attr_val_in)
        attr_obj = f.TypeValue(attr_type, t.int32s(compare_val))
    elif attr_type == 0x2C:
        compare_val = str2int(attr_val_in)
        attr_obj = f.TypeValue(attr_type, t.int32s(compare_val))
    elif attr_type == 0x2D:
        compare_val = str2int(attr_val_in)
        attr_obj = f.TypeValue(attr_type, t.int48s(compare_val))
    elif attr_type == 0x2E:
        compare_val = str2int(attr_val_in)
        attr_obj = f.TypeValue(attr_type, t.int56s(compare_val))
    elif attr_type == 0x2F:
        compare_val = str2int(attr_val_in)
        attr_obj = f.TypeValue(attr_type, t.int64s(compare_val))
    elif attr_type in [0x41, 0x42]:  # Octet string
        # Octet string requires length -> LVBytes
        compare_val = t.LVBytes(attr_val_in)

        if isinstance(attr_val_in, str):
            attr_val_in = bytes(attr_val_in, "utf_8")

        if isinstance(attr_val_in, list):
            # Convert list to List of uint8_t
            attr_val_in = t.List[t.uint8_t](
                [t.uint8_t(i) for i in attr_val_in]
            )

        attr_obj = f.TypeValue(attr_type, t.LVBytes(attr_val_in))
    elif attr_type == 0x48:  # Array, (+Bag?, Set?)
        # TODO: apply to Bag and Set ?
        #
        # Array List of bytes currently is:
        #  First byte: type of array items
        #  Next bytes: bytes for array items
        #
        # Maybe in future accept:
        #  Specifying array item type in 'attr_items_type:'
        #      (/detect items type from read).

        if isinstance(attr_val_in, str):
            attr_val_in = str.encode(attr_val_in[1:])

        # Determine value to compare read values
        #       with the value (to be) written [see attr_write].
        compare_val = t.List[t.uint8_t](attr_val_in)

        # Get type of array items
        array_item_type = attr_val_in[0]

        # Get body / array items.
        array_body = t.SerializableBytes(bytes(attr_val_in[1:]))

        # Construct value to write as specific zigpy object
        attr_obj = f.TypeValue(attr_type, f.Array(array_item_type, array_body))
    elif attr_type == 0xFF or attr_type is None:
        compare_val = str2int(attr_val_in)
        # This should not happen ideally
        attr_obj = f.TypeValue(attr_type, t.LVBytes(compare_val))
    else:
        # Try to apply conversion using foundation DATA_TYPES table
        # Note: this is not perfect and specific conversions may be needed.
        data_type = f.DATA_TYPES[attr_type][1]
        LOGGER.debug(f"Data type '{data_type}' for attr type {attr_type}")
        if isinstance(attr_val_in, list):
            # Without length byte after serialisation:
            compare_val = t.List[t.uint8_t](attr_val_in)
            # With length byte after serialisation:
            # compare_val = t.LVBytes(attr_val_in)

            attr_obj = f.TypeValue(attr_type, data_type(compare_val))
            # Not using : attr_obj = data_type(attr_type, compare_val)
        #             which may add extra bytes
        else:
            compare_val = data_type(str2int(attr_val_in))
            attr_obj = f.TypeValue(attr_type, compare_val)
        LOGGER.debug(
            "Converted %s to %s - will compare to %s - Type: 0x%02X",
            attr_val_in,
            attr_obj,
            compare_val,
            attr_type,
        )

    if attr_obj is None:
        msg = (
            "attr_type {} not supported, "
            "or incorrect parameters (attr_val={})"
        ).format(attr_type, attr_val_in)
        LOGGER.error(msg)
    else:
        msg = None

    return attr_obj, msg, compare_val


def isManf(manf, includeNone=False):
    if manf is None:
        return includeNone
    return not (isinstance(manf, str) and manf == "") or (
        isinstance(manf, int) and (manf == 0 or manf < 0)
    )


# Common method to extract and convert parameters.
#
# Most parameters are similar, this avoids repeating
# code.
#
def extractParams(  # noqa: C901
    service,
) -> dict[str, None | int | str | list[int | str] | bytes]:
    rawParams = service.data

    LOGGER.debug("Parameters '%s'", rawParams)

    # Potential parameters, initialized to None
    # TODO: Not all parameters are decoded in this function yet
    params: dict[str, None | int | str | list[int | str] | bytes] = {
        p.CMD_ID: None,
        p.EP_ID: None,
        p.DST_EP_ID: None,
        p.CLUSTER_ID: None,
        p.ATTR_ID: None,
        p.ATTR_TYPE: None,
        p.ATTR_VAL: None,
        p.CODE: None,  # Install code (join with code)
        p.MIN_INTERVAL: None,
        p.MAX_INTERVAL: None,
        p.REPORTABLE_CHANGE: None,
        p.DIR: 0,
        p.MANF: None,
        p.TRIES: 1,
        p.EXPECT_REPLY: True,
        p.ARGS: [],
        p.STATE_ID: None,
        p.STATE_ATTR: None,
        p.STATE_VALUE_TEMPLATE: None,
        p.FORCE_UPDATE: False,
        p.ALLOW_CREATE: False,
        p.EVT_SUCCESS: None,
        p.EVT_FAIL: None,
        p.EVT_DONE: None,
        p.FAIL_EXCEPTION: False,
        p.READ_BEFORE_WRITE: True,
        p.READ_AFTER_WRITE: True,
        p.WRITE_IF_EQUAL: False,
        p.CSV_FILE: None,
        p.CSV_LABEL: None,
        p.DOWNLOAD: None,
        p.PATH: None,
        p.USE_CACHE: False,
    }

    # Endpoint to send command to
    if P.ENDPOINT in rawParams:
        params[p.EP_ID] = str2int(rawParams[P.ENDPOINT])

    # Destination endpoint (e.g., target of data/cmds in bind_ieee)
    if P.DST_ENDPOINT in rawParams:
        params[p.DST_EP_ID] = str2int(rawParams[P.DST_ENDPOINT])

    # Cluster to send command to
    if P.CLUSTER in rawParams:
        params[p.CLUSTER_ID] = str2int(rawParams[P.CLUSTER])

    # Attribute to send command to
    if P.ATTRIBUTE in rawParams:
        params[p.ATTR_ID] = str2int(rawParams[P.ATTRIBUTE])

    # Attribute to send command to
    if P.ATTR_TYPE in rawParams:
        params[p.ATTR_TYPE] = str2int(rawParams[P.ATTR_TYPE])

    # Attribute to send command to
    if P.ATTR_VAL in rawParams:
        params[p.ATTR_VAL] = str2int(rawParams[P.ATTR_VAL])

    # Install code
    if P.CODE in rawParams:
        params[p.CODE] = str2int(rawParams[P.CODE])

    # The command to send
    if P.CMD in rawParams:
        params[p.CMD_ID] = str2int(rawParams[P.CMD])

    # The direction (to in or out cluster)
    if P.DIR in rawParams:
        params[p.DIR] = str2int(rawParams[P.DIR])

    # Get manufacturer
    if P.MANF in rawParams:
        params[p.MANF] = str2int(rawParams[P.MANF])

    manf = params[p.MANF]
    if not isManf(manf, True):
        LOGGER.debug("Got manf '%s'", manf)
        if hasattr(f.ZCLHeader, "NO_MANUFACTURER_ID"):
            params[p.MANF] = f.ZCLHeader.NO_MANUFACTURER_ID
        else:
            # Forcing b"" not ok in call cases # Not None, force empty manf
            params[p.MANF] = b""

    LOGGER.debug("Final manf '%r'", params[p.MANF])

    # Get tries
    if P.TRIES in rawParams:
        params[p.TRIES] = str2int(rawParams[P.TRIES])

    # Get expect_reply
    if P.EXPECT_REPLY in rawParams:
        params[p.EXPECT_REPLY] = str2int(rawParams[P.EXPECT_REPLY]) == 0

    if P.DOWNLOAD in rawParams:
        params[p.DOWNLOAD] = str2int(rawParams[P.DOWNLOAD]) != 0

    if P.FAIL_EXCEPTION in rawParams:
        params[p.FAIL_EXCEPTION] = str2int(rawParams[P.FAIL_EXCEPTION]) == 0

    if P.ARGS in rawParams:
        cmd_args = []
        rawArgs = rawParams[P.ARGS]
        if rawArgs is not None:
            try:
                iter(rawParams)
            except ValueError:
                rawArgs = [rawArgs]

            for val in rawParams[P.ARGS]:
                LOGGER.debug("cmd arg %s", val)
                lval = str2int(val)
                if isinstance(lval, list):
                    # Convert list to List of uint8_t
                    lval = t.List[t.uint8_t]([t.uint8_t(i) for i in lval])
                    # Convert list to LVList structure
                    # lval = t.LVList(lval)
                cmd_args.append(lval)
                LOGGER.debug("cmd converted arg %s", lval)
        params[p.ARGS] = cmd_args

    if P.MIN_INTRVL in rawParams:
        params[p.MIN_INTERVAL] = str2int(rawParams[P.MIN_INTRVL])
    if P.MAX_INTRVL in rawParams:
        params[p.MAX_INTERVAL] = str2int(rawParams[P.MAX_INTRVL])
    if P.REPTBLE_CHG in rawParams:
        params[p.REPORTABLE_CHANGE] = str2int(rawParams[P.REPTBLE_CHG])

    if P.STATE_ID in rawParams:
        params[p.STATE_ID] = rawParams[P.STATE_ID]

    if P.STATE_ATTR in rawParams:
        params[p.STATE_ATTR] = rawParams[P.STATE_ATTR]

    if P.READ_BEFORE_WRITE in rawParams:
        params[p.READ_BEFORE_WRITE] = str2bool(rawParams[P.READ_BEFORE_WRITE])

    if P.READ_AFTER_WRITE in rawParams:
        params[p.READ_AFTER_WRITE] = str2bool(rawParams[P.READ_AFTER_WRITE])

    if P.WRITE_IF_EQUAL in rawParams:
        params[p.WRITE_IF_EQUAL] = str2bool(rawParams[P.WRITE_IF_EQUAL])

    if P.STATE_ATTR in rawParams:
        params[p.STATE_ATTR] = rawParams[P.STATE_ATTR]

    if P.STATE_VALUE_TEMPLATE in rawParams:
        params[p.STATE_VALUE_TEMPLATE] = rawParams[P.STATE_VALUE_TEMPLATE]

    if P.ALLOW_CREATE in rawParams:
        allow = str2int(rawParams[P.ALLOW_CREATE])
        params[p.ALLOW_CREATE] = (allow is not None) and (
            (allow is True) or (allow == 1)
        )

    if P.FORCE_UPDATE in rawParams:
        force_update = str2int(rawParams[P.FORCE_UPDATE])
        params[p.FORCE_UPDATE] = (force_update is not None) and (
            (force_update is True) or (force_update == 1)
        )

    if P.USE_CACHE in rawParams:
        params[p.USE_CACHE] = str2int(rawParams[P.USE_CACHE])

    if P.EVENT_DONE in rawParams:
        params[p.EVT_DONE] = rawParams[P.EVENT_DONE]

    if P.EVENT_FAIL in rawParams:
        params[p.EVT_FAIL] = rawParams[P.EVENT_FAIL]

    if P.EVENT_SUCCESS in rawParams:
        params[p.EVT_SUCCESS] = rawParams[P.EVENT_SUCCESS]

    if P.OUTCSV in rawParams:
        params[p.CSV_FILE] = rawParams[P.OUTCSV]

    if P.PATH in rawParams:
        params[p.PATH] = rawParams[P.PATH]

    if P.CSVLABEL in rawParams:
        params[p.CSV_LABEL] = rawParams[P.CSVLABEL]

    return params


#
# Copied retry and retryable from zigpy < 0.56.0
#   where "tries" and "delay" were removed
#  from the wrapper function and hence propagated to the decorated function.
#
async def retry(
    func: typing.Callable[[], typing.Awaitable[typing.Any]],
    retry_exceptions: typing.Iterable[typing.Any]
    | None = None,  # typing.Iterable[BaseException],
    tries: int = 3,
    delay: int | float = 0.1,
) -> typing.Any:
    """Retry a function in case of exception

    Only exceptions in `retry_exceptions` will be retried.
    """
    if retry_exceptions is None:
        # Default list
        retry_exceptions = (
            DeliveryError,
            ControllerException,
            asyncio.CancelledError,
            asyncio.TimeoutError,
        )

    while True:
        LOGGER.debug("Tries remaining: %s", tries)
        try:
            return await func()
            # pylint: disable-next=catching-non-exception
        except retry_exceptions:  # type:ignore[misc]
            if tries <= 1:
                raise
            tries -= 1
            await asyncio.sleep(delay)


async def retry_wrapper(
    func: typing.Callable,
    *args,
    retry_exceptions: typing.Iterable[typing.Any]
    | None = None,  # typing.Iterable[BaseException],
    tries: int = 3,
    delay: int | float = 0.1,
    **kwargs,
) -> typing.Any:
    """Inline callable wrapper for retry"""
    return await retry(
        functools.partial(func, *args, **kwargs),
        retry_exceptions,
        tries=tries,
        delay=delay,
    )


def retryable(
    retry_exceptions: None
    | typing.Iterable[typing.Any] = None,  # typing.Iterable[BaseException]
    tries: int = 1,
    delay: float = 0.1,
) -> typing.Callable:
    """Return a decorator which makes a function able to be retried

    This adds "tries" and "delay" keyword arguments to the function. Only
    exceptions in `retry_exceptions` will be retried.
    """

    def decorator(func: typing.Callable) -> typing.Callable:
        nonlocal tries, delay

        @functools.wraps(func)
        def wrapper(*args, tries=tries, delay=delay, **kwargs):
            if tries <= 1:
                return func(*args, **kwargs)
            return retry(
                functools.partial(func, *args, **kwargs),
                retry_exceptions,
                tries=tries,
                delay=delay,
            )

        return wrapper

    return decorator


# zigpy wrappers


# The zigpy library does not offer retryable on read_attributes.
# Add it ourselves
@retryable(
    (
        DeliveryError,
        ControllerException,
        asyncio.CancelledError,
        asyncio.TimeoutError,
    ),
    tries=1,
)
async def cluster_read_attributes(
    cluster, attrs, manufacturer=None
) -> tuple[list, list]:
    """Read attributes from cluster, retryable"""
    return await cluster.read_attributes(attrs, manufacturer=manufacturer)


# The zigpy library does not offer retryable on read_attributes.
# Add it ourselves
@retryable(
    (DeliveryError, asyncio.CancelledError, asyncio.TimeoutError), tries=1
)
async def cluster__write_attributes(cluster, attrs, manufacturer=None):
    """Write cluster attributes from cluster, retryable"""
    return await cluster._write_attributes(attrs, manufacturer=manufacturer)


def get_local_dir() -> str:
    """Provide directory for local files that survive updates"""
    local_dir = os.path.dirname(__file__) + "/local/"
    if not os.path.isdir(local_dir):
        os.mkdir(local_dir)
    return local_dir


def is_zigpy_ge(version: str) -> bool:
    """Test if zigpy library is newer than version"""
    # Example version value: "0.45.0"
    return parse_version(getZigpyVersion()) >= parse_version(version)


def is_ha_ge(version: str) -> bool:
    """Test if zigpy library is newer than version"""
    return parse_version(getHaVersion()) >= parse_version(version)


def get_hass(gateway: ZHAGateway):
    """HA Version independent way of getting hass from gateway"""
    hass = getattr(gateway, "_hass", None)
    if hass is None:
        hass = getattr(gateway, "hass", None)
    return hass
