import logging
import os
import json

from enum import Enum

from zigpy import types as t
from zigpy.zcl import foundation as f
from homeassistant.util.json import save_json

from .params import USER_PARAMS as P
from .params import INTERNAL_PARAMS as p

LOGGER = logging.getLogger(__name__)


# Convert string to int if possible or return original string
#  (Returning the original string is useful for named attributes)
def str2int(s):
    if not type(s) == str:
        return s
    elif s.lower() == "false":
        return 0
    elif s.lower() == "true":
        return 1
    elif s.startswith("0x") or s.startswith("0X"):
        return int(s, 16)
    elif s.startswith("0") and s.isnumeric():
        return int(s, 8)
    elif s.startswith("b") and s[1:].isnumeric():
        return int(s[1:], 2)
    elif s.isnumeric():
        return int(s)
    else:
        return s


# Convert string to best boolean representation
def str2bool(s):
    if s is None or s == "":
        return False
    if s is True or s is False:
        return s
    return str2int(s) != 0


class RadioType(Enum):
    UNKNOWN = 0
    ZNP = 1
    EZSP = 2
    BELLOWS = 2


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
    LOGGER.debug("Type recognition for '%s' not implemented", type(app))
    return RadioType.UNKNOWN


def get_radio(app):
    if hasattr(app, "_znp"):
        return app._znp
    if hasattr(app, "_ezsp"):
        return app._ezsp
    LOGGER.debug("Type recognition for '%s' not implemented", type(app))
    return RadioType.UNKNOWN


# Get zigbee IEEE address (EUI64) for the reference.
#  Reference can be entity, device, or IEEE address
async def get_ieee(app, listener, ref):
    # LOGGER.debug("Type IEEE: %s", type(ref))
    if type(ref) == str:
        # Check if valid ref address
        if ref.count(":") == 7:
            return t.EUI64.convert(ref)

        # Check if network address
        nwk = str2int(ref)
        if (type(nwk) == int) and nwk >= 0x0000 and nwk <= 0xFFF7:
            device = app.get_device(nwk=nwk)
            if device is None:
                return None
            else:
                LOGGER.debug("NWK addr 0x04x -> %s", nwk, device.ieee)
                return device.ieee

        # Todo: check if NWK address
        entity_registry = (
            await listener._hass.helpers.entity_registry.async_get_registry()
        )
        # LOGGER.debug("registry %s",entity_registry)
        registry_entity = entity_registry.async_get(ref)
        LOGGER.debug("registry_entity %s", registry_entity)
        if registry_entity is None:
            return None
        if registry_entity.platform != "zha":
            LOGGER.error("Not a ZHA device : '%s'", ref)
            return None

        device_registry = (
            await listener._hass.helpers.device_registry.async_get_registry()
        )
        registry_device = device_registry.async_get(registry_entity.device_id)
        LOGGER.debug("registry_device %s", registry_device)
        for identifier in registry_device.identifiers:
            if identifier[0] == "zha":
                return t.EUI64.convert(identifier[1])
        return None

    # Other type, suppose it's already an EUI64
    return ref


# Get a zigbee device instance for the reference.
#  Reference can be entity, device, or IEEE address
async def get_device(app, listener, reference):
    # Method is called get
    ieee = await get_ieee(app, listener, reference)
    LOGGER.debug("IEEE for get_device: %s", ieee)
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
        LOGGER.error("No Endpoint found for cluster '%s'", cluster_id)
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


def write_json_to_file(data, subdir, fname, desc, listener=None):
    if listener is None or subdir == "local":
        base_dir = os.path.dirname(__file__)
    else:
        base_dir = listener._hass.config.config_dir

    out_dir = os.path.join(base_dir, subdir)
    if not os.path.isdir(out_dir):
        os.mkdir(out_dir)

    file_name = os.path.join(out_dir, fname)
    save_json(file_name, data)
    LOGGER.debug(f"Finished writing {desc} in '{file_name}'")


def append_to_csvfile(fields, subdir, fname, desc, listener=None):
    if listener is None or subdir == "local":
        base_dir = os.path.dirname(__file__)
    else:
        base_dir = listener._hass.config.config_dir

    out_dir = os.path.join(base_dir, subdir)
    if not os.path.isdir(out_dir):
        os.mkdir(out_dir)

    file_name = os.path.join(out_dir, fname)

    import csv

    with open(file_name, "a") as f:
        writer = csv.writer(f)
        writer.writerow(fields)

    LOGGER.debug(f"Appended {desc} to '{file_name}'")


def get_attr_id(cluster, attribute):
    # Try to get attribute id from cluster
    try:
        if isinstance(attribute, str):
            return cluster.attridx.get(attribute)
    except Exception:
        return None

    # By default, just try to convert it to an int
    return str2int(attribute)


def get_attr_type(cluster, attr_id):
    """Get type for attribute in cluster, or None if not found"""
    try:
        return f.DATA_TYPES.pytype_to_datatype_id(
            cluster.attributes.get(attr_id, (None, f.Unknown))[1]
        )
    except Exception:  # nosec
        pass

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
        attr_obj = f.TypeValue(attr_type, t.int8_t(compare_val))
    elif attr_type == 0x29:
        compare_val = str2int(attr_val_in)
        attr_obj = f.TypeValue(attr_type, t.int16_t(compare_val))
    elif attr_type == 0x2A:
        compare_val = str2int(attr_val_in)
        attr_obj = f.TypeValue(attr_type, t.int24_t(compare_val))
    elif attr_type == 0x2B:
        compare_val = str2int(attr_val_in)
        attr_obj = f.TypeValue(attr_type, t.int32_t(compare_val))
    elif attr_type == 0x2C:
        compare_val = str2int(attr_val_in)
        attr_obj = f.TypeValue(attr_type, t.int32_t(compare_val))
    elif attr_type == 0x2D:
        compare_val = str2int(attr_val_in)
        attr_obj = f.TypeValue(attr_type, t.int48_t(compare_val))
    elif attr_type == 0x2E:
        compare_val = str2int(attr_val_in)
        attr_obj = f.TypeValue(attr_type, t.int56_t(compare_val))
    elif attr_type == 0x2F:
        compare_val = str2int(attr_val_in)
        attr_obj = f.TypeValue(attr_type, t.int64_t(compare_val))
    elif attr_type <= 0x31 and attr_type >= 0x08:
        compare_val = str2int(attr_val_in)
        # uint, int, bool, bitmap and enum
        attr_obj = compare_val
        # attr_obj = f.TypeValue(attr_type, t.FixedIntType(compare_val))
    elif attr_type in [0x41, 0x42]:  # Octet string
        # Octet string requires length -> LVBytes
        compare_val = t.LVBytes(attr_val_in)

        if type(attr_val_in) == str:
            attr_val_in = bytes(attr_val_in, "utf-8")

        if isinstance(attr_val_in, list):
            # Convert list to List of uint8_t
            attr_val_in = t.List[t.uint8_t](
                [t.uint8_t(i) for i in attr_val_in]
            )

        attr_obj = f.TypeValue(attr_type, t.LVBytes(attr_val_in))

    if attr_obj is None:
        msg = (
            "attr_type {} not supported, "
            + "or incorrect parameters (attr_val={})"
        ).format(attr_type, attr_val_in)
        LOGGER.debug(msg)
    else:
        msg = None

    return attr_obj, msg, compare_val


# Common method to extract and convert parameters.
#
# Most parameters are similar, this avoids repeating
# code.
#
def extractParams(service):  # noqa: C901
    rawParams = service.data

    LOGGER.debug("Parameters '%s'", rawParams)

    # Potential parameters, initialized to None
    # TODO: Not all parameters are decoded in this function yet
    params = {
        p.CMD_ID: None,
        p.EP_ID: None,
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
        p.ALLOW_CREATE: False,
        p.EVT_SUCCESS: None,
        p.EVT_FAIL: None,
        p.EVT_DONE: None,
        p.READ_BEFORE_WRITE: True,
        p.READ_AFTER_WRITE: True,
        p.WRITE_IF_EQUAL: False,
        p.CSV_FILE: None,
        p.CSV_LABEL: None,
    }

    # Extract parameters

    # Endpoint to send command to
    if P.ENDPOINT in rawParams:
        params[p.EP_ID] = str2int(rawParams[P.ENDPOINT])

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

    # Get tries
    if P.TRIES in rawParams:
        params[p.TRIES] = str2int(rawParams[P.TRIES])

    # Get expect_reply
    if P.EXPECT_REPLY in rawParams:
        params[p.EXPECT_REPLY] = str2int(rawParams[P.EXPECT_REPLY]) == 0

    if P.ARGS in rawParams:
        cmd_args = []
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

    if P.ALLOW_CREATE in rawParams:
        allow = str2int(rawParams[P.ALLOW_CREATE])
        params[p.ALLOW_CREATE] = (allow is not None) and (
            (allow is True) or (allow == 1)
        )

    if P.EVENT_DONE in rawParams:
        params[p.EVT_DONE] = rawParams[P.EVENT_DONE]

    if P.EVENT_FAIL in rawParams:
        params[p.EVT_FAIL] = rawParams[P.EVENT_FAIL]

    if P.EVENT_SUCCESS in rawParams:
        params[p.EVT_SUCCESS] = rawParams[P.EVENT_SUCCESS]

    if P.OUTCSV in rawParams:
        params[p.CSV_FILE] = rawParams[P.OUTCSV]

    if P.CSVLABEL in rawParams:
        params[p.CSV_LABEL] = rawParams[P.CSVLABEL]

    return params
