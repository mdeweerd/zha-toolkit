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
            vol.Optional(P.CMD): cv.string,
            vol.Optional(P.ENDPOINT): cv.byte,
            vol.Optional(P.CLUSTER): vol.Range(0, 0xFFFF),
            vol.Optional(P.ATTRIBUTE): vol.Any(cv.string, vol.Range(0, 0xFFFF)),
            vol.Optional(P.ATTR_TYPE): vol.Any(
                cv.string, int
            ),  # String is for later
            vol.Optional(P.ATTR_VAL): vol.Any(cv.string, int, list),
            vol.Optional(P.CODE): vol.Any(
                cv.string, list
            ),  # list is for later
            vol.Optional(P.MIN_INTRVL): int,
            vol.Optional(P.MAX_INTRVL): int,
            vol.Optional(P.REPTBLE_CHG): int,
            vol.Optional(P.DIR): cv.boolean,
            vol.Optional(P.MANF): vol.Range(0, 0xFFFF),
            vol.Optional(P.EXPECT_REPLY): cv.boolean,
            vol.Optional(P.ARGS): vol.Any(
                int, cv.string, list
            ),  # Arguments to command
            vol.Optional(P.STATE_ID): cv.string,
            vol.Optional(P.STATE_ATTR): cv.string,
            vol.Optional(P.ALLOW_CREATE): cv.boolean,
            vol.Optional(P.READ_BEFORE_WRITE): cv.boolean,
            vol.Optional(P.READ_AFTER_WRITE): cv.boolean,
            vol.Optional(P.WRITE_IF_EQUAL): cv.boolean,
            vol.Optional(P.OUTCSV): cv.string,
            vol.Optional(P.CSVLABEL): cv.string,
        },
        extra=vol.ALLOW_EXTRA,
    ),
    # All services with their specific parameters (List being completed)
    S.ADD_GROUP: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.ADD_TO_GROUP: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.ALL_ROUTES_AND_NEIGHBOURS: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.ATTR_READ: vol.Schema(
        {
            vol.Optional(P.ENDPOINT): vol.Range(0, 255),
            vol.Required(P.CLUSTER): vol.Range(0, 0xFFFF),
            vol.Required(P.ATTRIBUTE): vol.Any(cv.string, vol.Range(0, 0xFFFF)),
            vol.Optional(P.MANF): vol.Range(0, 0xFFFF),
            vol.Optional(P.EXPECT_REPLY): cv.boolean,
            vol.Optional(P.STATE_ID): cv.string,
            vol.Optional(P.STATE_ATTR): cv.string,
            vol.Optional(P.ALLOW_CREATE): cv.boolean,
            vol.Optional(P.OUTCSV): cv.string,
            vol.Optional(P.CSVLABEL): cv.string,
        },
        extra=vol.ALLOW_EXTRA,
    ),
    S.ATTR_WRITE: vol.Schema(
        {
            vol.Optional(P.ENDPOINT): vol.Range(0, 255),
            vol.Required(P.CLUSTER): vol.Range(0, 0xFFFF),
            vol.Required(P.ATTRIBUTE): vol.Any(cv.string, vol.Range(0, 0xFFFF)),
            vol.Required(P.ATTR_TYPE): vol.Any(
                cv.string, int
            ),  # String is for later
            vol.Required(P.ATTR_VAL): vol.Any(cv.string, vol.Coerce(int), list),
            vol.Optional(P.MANF): vol.Range(0, 0xFFFF),
            vol.Optional(P.EXPECT_REPLY): cv.boolean,
            vol.Optional(P.STATE_ID): cv.string,
            vol.Optional(P.STATE_ATTR): cv.string,
            vol.Optional(P.ALLOW_CREATE): cv.boolean,
            vol.Optional(P.READ_BEFORE_WRITE): cv.boolean,
            vol.Optional(P.READ_AFTER_WRITE): cv.boolean,
            vol.Optional(P.WRITE_IF_EQUAL): cv.boolean,
            vol.Optional(P.OUTCSV): cv.string,
            vol.Optional(P.CSVLABEL): cv.string,
        },
        extra=vol.ALLOW_EXTRA,
    ),
    S.BACKUP: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.BIND_GROUP: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.BIND_IEEE: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.CONF_REPORT: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.EZSP_ADD_KEY: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.EZSP_BACKUP: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.EZSP_CLEAR_KEYS: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.EZSP_GET_CONFIG_VALUE: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.EZSP_GET_IEEE_BY_NWK: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.EZSP_GET_KEYS: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.EZSP_GET_POLICY: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.EZSP_GET_TOKEN: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.EZSP_GET_VALUE: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.EZSP_SET_CHANNEL: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.EZSP_START_MFG: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.GET_GROUPS: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.GET_ROUTES_AND_NEIGHBOURS: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.GET_ZLL_GROUPS: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.HANDLE_JOIN: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.IEEE_PING: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.LEAVE: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.OTA_NOTIFY: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.REJOIN: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.REMOVE_ALL_GROUPS: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.REMOVE_FROM_GROUP: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.REMOVE_GROUP: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.SCAN_DEVICE: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.SINOPE: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.UNBIND_COORDINATOR: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.UNBIND_GROUP: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.ZCL_CMD: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.ZDO_FLOOD_PARENT_ANNCE: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.ZDO_JOIN_WITH_CODE: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.ZDO_SCAN_NOW: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.ZDO_UPDATE_NWK_ID: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.ZIGPY_DECONZ: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.ZNP_BACKUP: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.ZNP_NVRAM_BACKUP: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.ZNP_NVRAM_RESET: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.ZNP_NVRAM_RESTORE: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.ZNP_RESTORE: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
}


COMMON_SCHEMA = {
    vol.Optional(P.TRIES): cv.positive_int,
    vol.Optional(P.EVENT_SUCCESS): cv.string,
    vol.Optional(P.EVENT_FAIL): cv.string,
    vol.Optional(P.EVENT_DONE): cv.string,
}


async def async_setup(hass, config):  # noqa: C901
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

        handler = None
        try:
            # Check if existing local handler
            handler = getattr(module, f"command_handler_{cmd}")
        except AttributeError:
            # Not an existing local handler, replace with the service command
            if service_cmd != "execute":
                # Actual service name (exists, defined in services.yaml)
                cmd = service_cmd
                handler = getattr(module, f"command_handler_{cmd}")

        if handler is None:
            handler = module.default_command

        handler_exception = None
        try:
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

    # Set up all service schemas
    for key, value in SERVICE_SCHEMAS.items():
        value.extend(COMMON_SCHEMA)
        hass.services.async_register(
            DOMAIN,
            key,
            toolkit_service,
            schema=value,
        )

    return True


async def default_command(
    app, listener, ieee, cmd, data, service, params, event_data
):
    LOGGER.debug("running default command: %s", service)

    if service.service.startswith("user"):
        # User library in 'local' directory

        from .local import user

        importlib.reload(user)

        handler = getattr(user, cmd)
        await handler(
            app, listener, ieee, cmd, data, service, params, event_data
        )
    else:
        from . import default

        importlib.reload(default)

        await default.default(
            app, listener, ieee, cmd, data, service, params, event_data
        )


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
