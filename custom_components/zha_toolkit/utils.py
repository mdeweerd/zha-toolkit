import logging
import os

from enum import Enum
from zigpy import types as t
from homeassistant.util.json import save_json

from .params import (
    ALLOW_CREATE,
    ARGS,
    ATTR_ID,
    ATTR_TYPE,
    ATTR_VAL,
    CLUSTER_ID,
    CMD_ID,
    CODE,
    DIR,
    EP_ID,
    EVT_DONE,
    EVT_FAIL,
    EVT_SUCCESS,
    EXPECT_REPLY,
    MANF,
    MAX_INTERVAL,
    MIN_INTERVAL,
    P_ALLOW_CREATE,
    P_ARGS,
    P_ATTRIBUTE,
    P_ATTR_TYPE,
    P_ATTR_VAL,
    P_CLUSTER,
    P_CMD,
    P_CODE,
    P_DIR,
    P_ENDPOINT,
    P_EVENT_DONE,
    P_EVENT_FAIL,
    P_EVENT_SUCCESS,
    P_EXPECT_REPLY,
    P_MANF,
    P_MAX_INTRVL,
    P_MIN_INTRVL,
    P_READ_AFTER_WRITE,
    P_READ_BEFORE_WRITE,
    P_REPTBLE_CHG,
    P_STATE_ATTR,
    P_STATE_ID,
    P_TRIES,
    P_WRITE_IF_EQUAL,
    READ_AFTER_WRITE,
    READ_BEFORE_WRITE,
    REPORTABLE_CHANGE,
    STATE_ATTR,
    STATE_ID,
    TRIES,
    WRITE_IF_EQUAL,
)

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


# Common method to extract and convert parameters.
#
# Most parameters are similar, this avoids repeating
# code.
#
def extractParams(service):

    # Get best parameter set, 'extra' is legacy.
    rawParams = service.data.get("extra")

    if not isinstance(rawParams, dict):
        # Fall back to parameters in 'data:' key
        rawParams = service.data

    LOGGER.debug("Parameters '%s'", rawParams)

    # Potential parameters, initialized to None
    # TODO: Not all parameters are decoded in this function yet
    params = {
        CMD_ID: None,
        EP_ID: None,
        CLUSTER_ID: None,
        ATTR_ID: None,
        ATTR_TYPE: None,
        ATTR_VAL: None,
        CODE: None,  # Install code (join with code)
        MIN_INTERVAL: None,
        MAX_INTERVAL: None,
        REPORTABLE_CHANGE: None,
        DIR: 0,
        MANF: None,
        TRIES: 1,
        EXPECT_REPLY: True,
        ARGS: [],
        STATE_ID: None,
        STATE_ATTR: None,
        ALLOW_CREATE: False,
        EVT_SUCCESS: None,
        EVT_FAIL: None,
        EVT_DONE: None,
        READ_BEFORE_WRITE: True,
        READ_AFTER_WRITE: True,
        WRITE_IF_EQUAL: False,
    }

    # Extract parameters

    # Endpoint to send command to
    if P_ENDPOINT in rawParams:
        params[EP_ID] = str2int(rawParams[P_ENDPOINT])

    # Cluster to send command to
    if P_CLUSTER in rawParams:
        params[CLUSTER_ID] = str2int(rawParams[P_CLUSTER])

    # Attribute to send command to
    if P_ATTRIBUTE in rawParams:
        params[ATTR_ID] = str2int(rawParams[P_ATTRIBUTE])

    # Attribute to send command to
    if P_ATTR_TYPE in rawParams:
        params[ATTR_TYPE] = str2int(rawParams[P_ATTR_TYPE])

    # Attribute to send command to
    if P_ATTR_VAL in rawParams:
        params[ATTR_VAL] = str2int(rawParams[P_ATTR_VAL])

    # Install code
    if P_CODE in rawParams:
        params[CODE] = str2int(rawParams[P_CODE])

    # The command to send
    if P_CMD in rawParams:
        params[CMD_ID] = str2int(rawParams[P_CMD])

    # The direction (to in or out cluster)
    if P_DIR in rawParams:
        params[DIR] = str2int(rawParams[P_DIR])

    # Get manufacturer
    if P_MANF in rawParams:
        params[MANF] = str2int(rawParams[P_MANF])

    # Get tries
    if P_TRIES in rawParams:
        params[TRIES] = str2int(rawParams[P_TRIES])

    # Get expect_reply
    if P_EXPECT_REPLY in rawParams:
        params[EXPECT_REPLY] = str2int(rawParams[P_EXPECT_REPLY]) == 0

    if P_ARGS in rawParams:
        cmd_args = []
        for val in rawParams[P_ARGS]:
            LOGGER.debug("cmd arg %s", val)
            lval = str2int(val)
            if isinstance(lval, list):
                # Convert list to List of uint8_t
                lval = t.List[t.uint8_t]([t.uint8_t(i) for i in lval])
                # Convert list to LVList structure
                # lval = t.LVList(lval)
            cmd_args.append(lval)
            LOGGER.debug("cmd converted arg %s", lval)
        params[ARGS] = cmd_args

    if P_MIN_INTRVL in rawParams:
        params[MIN_INTERVAL] = str2int(rawParams[P_MIN_INTRVL])
    if P_MAX_INTRVL in rawParams:
        params[MAX_INTERVAL] = str2int(rawParams[P_MAX_INTRVL])
    if P_REPTBLE_CHG in rawParams:
        params[REPORTABLE_CHANGE] = str2int(rawParams[P_REPTBLE_CHG])

    if P_STATE_ID in rawParams:
        params[STATE_ID] = rawParams[P_STATE_ID]

    if P_STATE_ATTR in rawParams:
        params[STATE_ATTR] = rawParams[P_STATE_ATTR]

    if P_READ_BEFORE_WRITE in rawParams:
        params[READ_BEFORE_WRITE] = str2bool(rawParams[P_READ_BEFORE_WRITE])

    if P_READ_AFTER_WRITE in rawParams:
        params[READ_AFTER_WRITE] = str2bool(rawParams[P_READ_AFTER_WRITE])

    if P_WRITE_IF_EQUAL in rawParams:
        params[WRITE_IF_EQUAL] = str2bool(rawParams[P_WRITE_IF_EQUAL])

    if P_STATE_ATTR in rawParams:
        params[STATE_ATTR] = rawParams[P_STATE_ATTR]

    if P_ALLOW_CREATE in rawParams:
        allow = str2int(rawParams[P_ALLOW_CREATE])
        params[ALLOW_CREATE] = (allow is not None) and (
            (allow is True) or (allow == 1)
        )

    if P_EVENT_DONE in rawParams:
        params[EVT_DONE] = rawParams[P_EVENT_DONE]

    if P_EVENT_FAIL in rawParams:
        params[EVT_FAIL] = rawParams[P_EVENT_FAIL]

    if P_EVENT_SUCCESS in rawParams:
        params[EVT_SUCCESS] = rawParams[P_EVENT_SUCCESS]

    return params
