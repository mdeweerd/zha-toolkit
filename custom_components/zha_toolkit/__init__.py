import importlib
import logging

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.util import dt as dt_util


from . import utils as u
from .params import INTERNAL_PARAMS as p
from .params import USER_PARAMS as P
from .params import SERVICES as S

DEPENDENCIES = ["zha"]

DOMAIN = "zha_toolkit"


# Legacy parameters
ATTR_COMMAND = "command"
ATTR_COMMAND_DATA = "command_data"
ATTR_IEEE = "ieee"

DATA_ZHATK = "zha_toolkit"


LOGGER = logging.getLogger(__name__)

SERVICE_SCHEMAS = {
    # This service provides access to all other services
    S.EXECUTE: vol.Schema(
        {
            vol.Optional(ATTR_IEEE): cv.string,
            vol.Optional(ATTR_COMMAND): cv.string,
            vol.Optional(ATTR_COMMAND_DATA): cv.string,
            vol.Optional(P.CMD) : cv.int,
            vol.Optional(P.ENDPOINT) : cv.int,
            vol.Optional(P.CLUSTER) : cv.int,
            vol.Optional(P.ATTRIBUTE) : cv.int,
            vol.Optional(P.ATTR_TYPE) : cv.int,
            vol.Optional(P.ATTR_VAL) : cv.int,
            vol.Optional(P.CODE) : cv.int,
            vol.Optional(P.MIN_INTRVL) : cv.int,
            vol.Optional(P.MAX_INTRVL) : cv.int,
            vol.Optional(P.REPTBLE_CHG) : cv.int,
            vol.Optional(P.DIR) : cv.int,
            vol.Optional(P.MANF) : cv.int,
            vol.Optional(P.TRIES) : cv.int,
            vol.Optional(P.EXPECT_REPLY) : cv.int,
            vol.Optional(P.ARGS) : cv.int,
            vol.Optional(P.STATE_ID) : cv.int,
            vol.Optional(P.STATE_ATTR) : cv.int,
            vol.Optional(P.ALLOW_CREATE) : cv.int,
            vol.Optional(P.EVENT_SUCCESS) : cv.int,
            vol.Optional(P.EVENT_FAIL) : cv.int,
            vol.Optional(P.EVENT_DONE) : cv.int,
            vol.Optional(P.READ_BEFORE_WRITE) : cv.int,
            vol.Optional(P.READ_AFTER_WRITE) : cv.int,
            vol.Optional(P.WRITE_IF_EQUAL) : cv.int,
            vol.Optional(P.OUTCSV) : cv.int,
            vol.Optional(P.CSVLABEL) : cv.int,
        },
    S.ADD_GROUP: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.ADD_TO_GROUP: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.ALL_ROUTES_AND_NEIGHBOURS: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.ATTR_READ: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.ATTR_WRITE: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.BACKUP: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.BIND_GROUP: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.BIND_IEEE: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.CONF_REPORT: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.EZSP_ADD_KEY: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.EZSP_BACKUP: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.EZSP_CLEAR_KEYS: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.EZSP_GET_CONFIG_VALUE: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.EZSP_GET_IEEE_BY_NWK: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.EZSP_GET_KEYS: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.EZSP_GET_POLICY: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.EZSP_GET_TOKEN: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.EZSP_GET_VALUE: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.EZSP_SET_CHANNEL: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.EZSP_START_MFG: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.GET_GROUPS: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.GET_ROUTES_AND_NEIGHBOURS: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.GET_ZLL_GROUPS: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.HANDLE_JOIN: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.IEEE_PING: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.LEAVE: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.OTA_NOTIFY: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.REJOIN: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.REMOVE_ALL_GROUPS: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.REMOVE_FROM_GROUP: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.REMOVE_GROUP: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.SCAN_DEVICE: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.SINOPE: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.UNBIND_COORDINATOR: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.UNBIND_GROUP: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.ZCL_CMD: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.ZDO_FLOOD_PARENT_ANNCE: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.ZDO_JOIN_WITH_CODE: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.ZDO_SCAN_NOW: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.ZDO_UPDATE_NWK_ID: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.ZIGPY_DECONZ: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.ZNP_BACKUP: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.ZNP_NVRAM_BACKUP: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.ZNP_NVRAM_RESET: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.ZNP_NVRAM_RESTORE: vol.Schema(
            {
            },
            extra=vol.ALLOW_EXTRA,
        ),
    S.ZNP_RESTORE: vol.Schema(
        {
        },
        extra=vol.ALLOW_EXTRA,
    ),
}

# Constants representing internal parameters keys
class INTERNAL_PARAMS_consts:
    __slots__ = ()
    ALLOW_CREATE = "allow_create"
    ARGS = "args"
    ATTR_ID = "attr_id"
    ATTR_TYPE = "attr_type"
    ATTR_VAL = "attr_val"
    CLUSTER_ID = "cluster_id"
    CMD_ID = "cmd_id"
    CODE = "code"
    DIR = "dir"
    EP_ID = "endpoint_id"
    EVT_DONE = "event_done"
    EVT_FAIL = "event_fail"
    EVT_SUCCESS = "event_success"
    EXPECT_REPLY = "expect_reply"
    MANF = "manf"
    MAX_INTERVAL = "max_interval"
    MIN_INTERVAL = "min_interval"
    READ_AFTER_WRITE = "read_after_write"
    READ_BEFORE_WRITE = "read_before_write"
    REPORTABLE_CHANGE = "reportable_change"
    STATE_ATTR = "state_attr"
    STATE_ID = "state_id"
    TRIES = "tries"
    WRITE_IF_EQUAL = "write_if_equal"
    CSV_FILE = "csvfile"
    CSV_LABEL = "csvlabel"


INTERNAL_PARAMS = INTERNAL_PARAMS_consts()
USER_PARAMS = USER_PARAMS_consts()
SERVICES = SERVICE_consts()
        },
        extra=ALLOW_EXTRA
    ),
    # All services with their specific parameters (List being extended)
}

#:Any(xx,yy)
#SCHEMA.extend

COMMON_SCHEMA = vol.Schema(
    manf:
      description: Manufacturer id
      selector:
        number:
          min: 1
          max: 0xFFFF
    cmd:
      description: Command Id (zcl_cmd)
      selector:
        number:
          min: 0
          max: 255 
    endpoint:
      description: target endpoint
      selector:
        number:
          min: 1
          max: 255 
    cluster:
      description: target cluster
      selector:
        number:
          min: 0
          max: 0xFFFF
    attribute:
      description: target attribute id (or name, accepted in most cases)
      selector:
        number:
          min: 0
          max: 0xFFFF
    attr_type:
      description: Attribute type (to write, ...)
      selector:
        number:
          min: 0
          max: 0xFFFF
    attr_val:
      description: Attribute value to write
      selector:
        text:
    min_interval:
      description: Minimum report interval (seconds)
      selector:
        number:
          min: 0
          max: 0xFFFF
    max_interval:
      description: Maximum report interval (seconds)
      selector:
        number:
          min: 0
          max: 0xFFFF
    reportable_change:
      description: Minimum change before reporting
      selector:
        number:
          min: 0
          max: 65535
    dir:
      description: Direction indicator, according to command
      selector:
        number:
          min: 0
          max: 1  
    tries:
      description: Number of times the zigbee packet should be attempted
      selector:
        number:
          min: 0 
          max: 255
    state_id:
      description: When defined, name of state to write the read attribute value to
      example: sensor.example
      selector:
        text:
    state_attr:
      description: When defined, attribute in state_id to write the read attribute value to.  Write to state value when missing (and state_id is defined)
      example: other_attr 
      selector:
        text:
    event_success:
      description: Event name in case of success (currently for attr_read, attr_write).  Has event data with relevant attributes.
      example: my_read_success_trigger_event
      selector:
        text:
    event_fail:
      description: Event name in case of failure (currently for attr_read, attr_write).  Has event data with relevant attributes.
      example: my_read_fail_trigger_event
      selector:
        text:
    event_done:
      description: Event name when the service call did all its work (either success or failure).  Has event data with relevant attributes.
      example: my_read_done_trigger_event
      selector:
        text:
    allow_create:
       description: Allow state creation (given by state_id) if it does not exist
       selector:
         boolean:
    read_before_write:
       description: "Read attribute before writing it (used with attr_write).  When the read value matches the value to write, no write is done  Defaults to True."
       selector:
         boolean:
    read_after_write:
       description: "Read attribute after writing.  Can be used to ensure the values match.  Defaults to True"
       selector:
         boolean:
    write_if_equal:
       description: "Force writing the attribute even if the read attribute already matches.  Defaults to False"
       selector:
         boolean:
    expect_reply:
       description: "Wait for/expect a reply (not used yet)"
       selector:
         boolean:

write_attr:
  description: Write Attribute (ZHA-Toolkit)
  fields:
    ieee:
      description: "Entity name,\ndevice name, or\nIEEE address of the node to execute command"
      example: "00:0d:6f:00:05:7d:2d:34"
      selector:
        entity:
          integration: zha
    manf:
      description: Manufacturer id
      selector:
        number:
          min: 1
          max: 0xFFFF
    endpoint:
      description: target endpoint
      selector:
        number:
          min: 1
          max: 255 
    cluster:
      description: target cluster
      selector:
        number:
          min: 0
          max: 0xFFFF
    attribute:
      description: target attribute id (or name, accepted in most cases)
      selector:
        number:
          min: 0
          max: 0xFFFF
    attr_type:
      description: Attribute type (to write, ...)
      selector:
        number:
          min: 0
          max: 0xFFFF
    attr_val:
      description: Attribute value to write
      selector:
        text:
    tries:
      description: Number of times the zigbee packet should be attempted
      selector:
        number:
          min: 0 
          max: 255
    state_id:
      description: When defined, name of state to write the read attribute value to
      example: sensor.example
      selector:
        text:
    state_attr:
      description: When defined, attribute in state_id to write the read attribute value to.  Write to state value when missing (and state_id is defined)
      example: other_attr 
      selector:
        text:
    event_success:
      description: Event name in case of success (currently for attr_read, attr_write).  Has event data with relevant attributes.
      example: my_read_success_trigger_event
      selector:
        text:
    event_fail:
      description: Event name in case of failure (currently for attr_read, attr_write).  Has event data with relevant attributes.
      example: my_read_fail_trigger_event
      selector:
        text:
    event_done:
      description: Event name when the service call did all its work (either success or failure).  Has event data with relevant attributes.
      example: my_read_done_trigger_event
      selector:
        text:
    allow_create:
       description: Allow state creation (given by state_id) if it does not exist
       selector:
         boolean:
    read_before_write:
       description: "Read attribute before writing it (used with attr_write).  When the read value matches the value to write, no write is done  Defaults to True."
       selector:
         boolean:
    read_after_write:
       description: "Read attribute after writing.  Can be used to ensure the values match.  Defaults to True"
       selector:
         boolean:
    write_if_equal:
       description: "Force writing the attribute even if the read attribute already matches.  Defaults to False"
       selector:
         boolean:
    expect_reply:
       description: "Wait for/expect a reply (not used yet)"
       selector:
         boolean:
        }
);




async def async_setup(hass, config):
    """Set up ZHA from config."""

    if DOMAIN not in config:
        return True

    try:
        zha_gw = hass.data["zha"]["zha_gateway"]
    except KeyError:
        return True

    async def toolkit_service(service):
        """Run command from toolkit module."""
        LOGGER.info("Running ZHA Toolkit service: %s", service)

        ieee_str = service.data.get(ATTR_IEEE)
        cmd = service.data.get(ATTR_COMMAND)
        cmd_data = service.data.get(ATTR_COMMAND_DATA)

        importlib.reload(u)
        # Decode parameters
        params = u.extractParams(service)

        app = zha_gw.application_controller

        ieee = await u.get_ieee(app, zha_gw, ieee_str)


        # Preload event_data
        event_data = {
            "ieee_org": ieee_str,
            "ieee": str(ieee),
            "command": cmd,
            "start_time": dt_util.utcnow().isoformat(),
            "errors": [],
            "params": params,
        }

        if ieee is not None:
            LOGGER.debug(
                "'ieee' parameter: '%s' -> IEEE Addr: '%s'", ieee_str, ieee
            )

        mod_path = f"custom_components.{DOMAIN}"
        try:
            module = importlib.import_module(mod_path)
        except ImportError as err:
            LOGGER.error("Couldn't load %s module: %s", DOMAIN, err)
            return

        importlib.reload(module)
        LOGGER.debug("module is %s", module)

        service_cmd = service.service  # Lower case service name in domain

        # This method can be called as the 'execute' service or
        # with the specific service
        if cmd is None:
            cmd = service_cmd
        try:
            handler = getattr(module, f"command_handler_{cmd}") 
        except AttributeError:
            if service_cmd != "execute":
                cmd = service_cmd  # Actual service name
            

        handler_exception = None
        try:
            if cmd:
                handler = getattr(module, f"command_handler_{cmd}")
                await handler(
                    zha_gw.application_controller,
                    zha_gw,
                    ieee,
                    cmd,
                    cmd_data,
                    service,
                    params=params,
                    event_data=event_data,
                )
            else:
                await module.default_command(
                    zha_gw.application_controller,
                    zha_gw,
                    ieee,
                    cmd,
                    cmd_data,
                    service,
                    params=params,
                    event_data=event_data,
                )
        except Exception as e:
            handler_exception = e
            event_data["errors"].append(repr(e))
            event_data["success"] = False

        if "success" not in event_data:
            event_data["success"] = True

        LOGGER.debug("event_data %s", event_data)
        # Fire events
        if event_data["success"]:
            if params[p.EVT_SUCCESS] is not None:
                LOGGER.debug(
                    "Fire %s -> %s", params[p.EVT_SUCCESS], event_data
                )
                zha_gw._hass.bus.fire(params[p.EVT_SUCCESS], event_data)
        else:
            if params[p.EVT_FAIL] is not None:
                LOGGER.debug("Fire %s -> %s", params[p.EVT_FAIL], event_data)
                zha_gw._hass.bus.fire(params[p.EVT_FAIL], event_data)

        if params[p.EVT_DONE] is not None:
            LOGGER.debug("Fire %s -> %s", params[p.EVT_DONE], event_data)
            zha_gw._hass.bus.fire(params[p.EVT_DONE], event_data)

        if handler_exception is not None:
            raise handler_exception

    hass.services.async_register(
        DOMAIN,
        SERVICE_EXECUTE,
        toolkit_service,
        schema=SERVICE_SCHEMAS[SERVICE_EXECUTE],
    )
    return True


async def default_command(
    app, listener, ieee, cmd, data, service, params, event_data
):
    LOGGER.debug("running default command: %s", service)

    await user.default(*args, **kwargs)


async def command_handler_handle_join(*args, **kwargs):
    from . import misc

    importlib.reload(misc)

    await misc.handle_join(*args, **kwargs)


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


async def command_handler_unbind_coordinator(*args, **kwargs):
    """IEEE bind device.
    ieee -- ieee of the device to unbind from coordinator
    data -- cluster ID to unbind
    """
    from . import binds

    importlib.reload(binds)

    await binds.unbind_coordinator(*args, **kwargs)


async def command_handler_rejoin(*args, **kwargs):
    from . import misc

    importlib.reload(misc)

    await misc.rejoin(*args, **kwargs)


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


def command_handler_attr_read(*args, **kwargs):
    from . import zcl_attr

    importlib.reload(zcl_attr)

    return zcl_attr.attr_read(*args, **kwargs)


def command_handler_attr_write(*args, **kwargs):
    from . import zcl_attr

    importlib.reload(zcl_attr)

    return zcl_attr.attr_write(*args, **kwargs)


def command_handler_conf_report(*args, **kwargs):
    from . import zcl_attr

    importlib.reload(zcl_attr)

    return zcl_attr.conf_report(*args, **kwargs)


def command_handler_get_routes_and_neighbours(*args, **kwargs):
    """Scan a device for neighbours and routes.
    ieee -- ieee of the device to scan
    """
    from . import neighbours

    importlib.reload(neighbours)

    return neighbours.routes_and_neighbours(*args, **kwargs)


def command_handler_all_routes_and_neighbours(*args, **kwargs):
    """Scan all devices for neighbours and routes."""
    from . import neighbours

    importlib.reload(neighbours)

    return neighbours.all_routes_and_neighbours(*args, **kwargs)


def command_handler_leave(*args, **kwargs):
    from . import zdo

    importlib.reload(zdo)

    return zdo.leave(*args, **kwargs)


def command_handler_ieee_ping(*args, **kwargs):
    from . import zdo

    importlib.reload(zdo)

    return zdo.ieee_ping(*args, **kwargs)


def command_handler_zigpy_deconz(*args, **kwargs):
    """Zigpy deconz test."""
    from . import zigpy_deconz

    importlib.reload(zigpy_deconz)

    return zigpy_deconz.zigpy_deconz(*args, **kwargs)


def command_handler_ezsp_backup(*args, **kwargs):
    """Backup BELLOWS (ezsp) network information."""
    from . import ezsp

    importlib.reload(ezsp)

    return ezsp.ezsp_backup(*args, **kwargs)


def command_handler_ezsp_set_channel(*args, **kwargs):
    """Set EZSP radio channel."""
    from . import ezsp

    importlib.reload(ezsp)

    return ezsp.set_channel(*args, **kwargs)


def command_handler_ezsp_get_token(*args, **kwargs):
    """Set EZSP radio channel."""
    from . import ezsp

    importlib.reload(ezsp)

    return ezsp.get_token(*args, **kwargs)


def command_handler_ezsp_start_mfg(*args, **kwargs):
    """Set EZSP radio channel."""
    from . import ezsp

    importlib.reload(ezsp)

    return ezsp.start_mfg(*args, **kwargs)


def command_handler_ezsp_get_keys(*args, **kwargs):
    """Get EZSP keys."""
    from . import ezsp

    importlib.reload(ezsp)

    return ezsp.get_keys(*args, **kwargs)


def command_handler_ezsp_add_key(*args, **kwargs):
    """Add transient link key."""
    from . import ezsp

    importlib.reload(ezsp)
    return ezsp.add_transient_key(*args, **kwargs)


def command_handler_ezsp_get_ieee_by_nwk(*args, **kwargs):
    """Get EZSP keys."""
    from . import ezsp

    importlib.reload(ezsp)
    return ezsp.get_ieee_by_nwk(*args, **kwargs)


def command_handler_ezsp_get_policy(*args, **kwargs):
    """Get EZSP keys."""
    from . import ezsp

    importlib.reload(ezsp)
    return ezsp.get_policy(*args, **kwargs)


def command_handler_ezsp_clear_keys(*args, **kwargs):
    """Clear key table."""
    from . import ezsp

    importlib.reload(ezsp)

    return ezsp.clear_keys(*args, **kwargs)


def command_handler_ezsp_get_config_value(*args, **kwargs):
    """Get EZSP config value."""
    from . import ezsp

    importlib.reload(ezsp)

    return ezsp.get_config_value(*args, **kwargs)


def command_handler_ezsp_get_value(*args, **kwargs):
    """Get EZSP value."""
    from . import ezsp

    importlib.reload(ezsp)

    return ezsp.get_value(*args, **kwargs)


def command_handler_ota_notify(*args, **kwargs):
    """Set EZSP radio channel."""
    from . import ota

    importlib.reload(ota)

    return ota.notify(*args, **kwargs)


def command_handler_zdo_join_with_code(*args, **kwargs):
    from . import zdo

    importlib.reload(zdo)

    return zdo.join_with_code(*args, **kwargs)


def command_handler_zdo_update_nwk_id(*args, **kwargs):
    from . import zdo

    importlib.reload(zdo)

    return zdo.update_nwk_id(*args, **kwargs)


def command_handler_zdo_scan_now(*args, **kwargs):
    from . import zdo

    importlib.reload(zdo)

    return zdo.topo_scan_now(*args, **kwargs)


def command_handler_zdo_flood_parent_annce(*args, **kwargs):
    from . import zdo

    importlib.reload(zdo)

    return zdo.flood_parent_annce(*args, **kwargs)


def command_handler_znp_backup(*args, **kwargs):
    """Backup ZNP network information."""
    from . import znp

    importlib.reload(znp)

    return znp.znp_backup(*args, **kwargs)


def command_handler_znp_restore(*args, **kwargs):
    """Restore ZNP network information."""
    from . import znp

    importlib.reload(znp)

    return znp.znp_restore(*args, **kwargs)


def command_handler_zcl_cmd(*args, **kwargs):
    """Perform scene command."""
    from . import zcl_cmd

    importlib.reload(zcl_cmd)

    return zcl_cmd.zcl_cmd(*args, **kwargs)


def command_handler_znp_nvram_backup(*args, **kwargs):
    """Backup ZNP network information."""
    from . import znp

    importlib.reload(znp)

    return znp.znp_nvram_backup(*args, **kwargs)


def command_handler_znp_nvram_restore(*args, **kwargs):
    """Restore ZNP network information."""
    from . import znp

    importlib.reload(znp)

    return znp.znp_nvram_restore(*args, **kwargs)


def command_handler_znp_nvram_reset(*args, **kwargs):
    """Restore ZNP network information."""
    from . import znp

    importlib.reload(znp)

    return znp.znp_nvram_reset(*args, **kwargs)


def command_handler_backup(*args, **kwargs):
    """Backup Coordinator information."""
    from . import misc

    importlib.reload(misc)

    return misc.backup(*args, **kwargs)
