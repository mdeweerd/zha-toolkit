import importlib
import logging

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.util import dt as dt_util


from . import utils as u
from .params import EVT_DONE, EVT_FAIL, EVT_SUCCESS

DEPENDENCIES = ["zha"]

DOMAIN = "zha_toolkit"

ATTR_COMMAND = "command"
ATTR_COMMAND_DATA = "command_data"
ATTR_IEEE = "ieee"
DATA_ZHATK = "zha_toolkit"

SERVICE_TOOLKIT = "execute"

LOGGER = logging.getLogger(__name__)

SERVICE_SCHEMAS = {
    SERVICE_TOOLKIT: vol.Schema(
        {
            vol.Optional(ATTR_IEEE): cv.string,
            vol.Optional(ATTR_COMMAND): cv.string,
            vol.Optional(ATTR_COMMAND_DATA): cv.string,
        },
        extra=vol.ALLOW_EXTRA,
    )
}


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

        app = zha_gw.application_controller

        ieee = await u.get_ieee(app, zha_gw, ieee_str)

        # Decode parameters
        params = u.extractParams(service)

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
            if params[EVT_SUCCESS] is not None:
                LOGGER.debug("Fire %s -> %s", params[EVT_SUCCESS], event_data)
                zha_gw._hass.bus.fire(params[EVT_SUCCESS], event_data)
        else:
            if params[EVT_FAIL] is not None:
                LOGGER.debug("Fire %s -> %s", params[EVT_FAIL], event_data)
                zha_gw._hass.bus.fire(params[EVT_FAIL], event_data)

        if params[EVT_DONE] is not None:
            LOGGER.debug("Fire %s -> %s", params[EVT_DONE], event_data)
            zha_gw._hass.bus.fire(params[EVT_DONE], event_data)

        if handler_exception is not None:
            raise handler_exception

    hass.services.async_register(
        DOMAIN,
        SERVICE_TOOLKIT,
        toolkit_service,
        schema=SERVICE_SCHEMAS[SERVICE_TOOLKIT],
    )
    return True


async def default_command(
    app, listener, ieee, cmd, data, service, params, event_data
):
    LOGGER.debug("running default command: %s", service)


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
