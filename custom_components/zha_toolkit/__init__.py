import importlib
import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
import zigpy
from homeassistant.util import dt as dt_util
from zigpy import types as t

from . import params as PARDEFS
from . import utils as u

DEPENDENCIES = ["zha"]

DOMAIN = "zha_toolkit"
REGISTERED_VERSION = ""

# Legacy parameters
ATTR_COMMAND = "command"
ATTR_COMMAND_DATA = "command_data"
ATTR_IEEE = "ieee"

DATA_ZHATK = "zha_toolkit"


LOGGER = logging.getLogger(__name__)

importlib.reload(PARDEFS)
p = PARDEFS.INTERNAL_PARAMS
P = PARDEFS.USER_PARAMS
S = PARDEFS.SERVICES

SERVICE_SCHEMAS = {
    # This service provides access to all other services
    S.EXECUTE: vol.Schema(
        {
            vol.Optional(ATTR_IEEE): vol.Any(
                cv.entity_id_or_uuid, t.EUI64.convert
            ),
            vol.Optional(ATTR_COMMAND): cv.string,
            vol.Optional(ATTR_COMMAND_DATA): vol.Any(list, cv.string),
            vol.Optional(P.CMD): cv.string,
            vol.Optional(P.ENDPOINT): vol.Any(cv.byte, [cv.byte]),
            vol.Optional(P.CLUSTER): vol.Range(0, 0xFFFF),
            vol.Optional(P.ATTRIBUTE): vol.Any(
                vol.Range(0, 0xFFFF), cv.string
            ),
            vol.Optional(P.ATTR_TYPE): vol.Any(
                int, cv.string
            ),  # String is for later
            vol.Optional(P.ATTR_VAL): vol.Any(cv.string, int, list),
            vol.Optional(P.CODE): vol.Any(
                list, cv.string
            ),  # list is for later
            vol.Optional(P.MIN_INTRVL): int,
            vol.Optional(P.MAX_INTRVL): int,
            vol.Optional(P.REPTBLE_CHG): int,
            vol.Optional(P.DIR): cv.boolean,
            vol.Optional(P.MANF): vol.Range(0, 0xFFFF),
            vol.Optional(P.ARGS): vol.Any(
                int, list, cv.string
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
        {
            vol.Required(ATTR_IEEE): vol.Any(
                cv.entity_id_or_uuid, t.EUI64.convert
            ),
            vol.Required(ATTR_COMMAND_DATA): vol.Range(0, 0xFFFF),
            vol.Optional(P.ENDPOINT): vol.Any(cv.byte, [cv.byte]),
        },
        extra=vol.ALLOW_EXTRA,
    ),
    S.ADD_TO_GROUP: vol.Schema(
        {
            vol.Required(ATTR_IEEE): vol.Any(
                cv.entity_id_or_uuid, t.EUI64.convert
            ),
            vol.Required(ATTR_COMMAND_DATA): vol.Range(0, 0xFFFF),
            vol.Optional(P.ENDPOINT): vol.Any(cv.byte, [cv.byte]),
        },
        extra=vol.ALLOW_EXTRA,
    ),
    S.ALL_ROUTES_AND_NEIGHBOURS: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.ATTR_READ: vol.Schema(
        {
            vol.Required(ATTR_IEEE): vol.Any(
                cv.entity_id_or_uuid, t.EUI64.convert
            ),
            vol.Optional(P.ENDPOINT): vol.Range(0, 255),
            vol.Required(P.CLUSTER): vol.Range(0, 0xFFFF),
            vol.Required(P.ATTRIBUTE): vol.Any(
                vol.Range(0, 0xFFFF), cv.string
            ),
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
            vol.Required(ATTR_IEEE): vol.Any(
                cv.entity_id_or_uuid, t.EUI64.convert
            ),
            vol.Optional(P.ENDPOINT): vol.Range(0, 255),
            vol.Required(P.CLUSTER): vol.Range(0, 0xFFFF),
            vol.Required(P.ATTRIBUTE): vol.Any(
                vol.Range(0, 0xFFFF), cv.string
            ),
            vol.Optional(P.ATTR_TYPE): vol.Any(
                vol.Range(0, 255), cv.string
            ),  # String is for later
            vol.Required(P.ATTR_VAL): vol.Any(
                list,
                vol.Coerce(int),
                cv.string,
            ),
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
        {
            vol.Optional(ATTR_COMMAND_DATA): cv.string,
        },
        extra=vol.ALLOW_EXTRA,
    ),
    S.BIND_GROUP: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.BIND_IEEE: vol.Schema(
        {
            vol.Required(ATTR_IEEE): vol.Any(
                cv.entity_id_or_uuid, t.EUI64.convert
            ),
            vol.Required(ATTR_COMMAND_DATA): cv.string,
            vol.Optional(P.CLUSTER): vol.Any(
                vol.Range(0, 0xFFFF), [vol.Range(0, 0xFFFF)]
            ),
        },
        extra=vol.ALLOW_EXTRA,
    ),
    S.BINDS_GET: vol.Schema(
        {
            vol.Required(ATTR_IEEE): vol.Any(
                cv.entity_id_or_uuid, t.EUI64.convert
            ),
        },
        extra=vol.ALLOW_EXTRA,
    ),
    S.BINDS_REMOVE_ALL: vol.Schema(
        {
            vol.Required(ATTR_IEEE): vol.Any(
                cv.entity_id_or_uuid, t.EUI64.convert
            ),
        },
        extra=vol.ALLOW_EXTRA,
    ),
    S.CONF_REPORT: vol.Schema(
        {
            vol.Required(ATTR_IEEE): vol.Any(
                cv.entity_id_or_uuid, t.EUI64.convert
            ),
            vol.Optional(P.ENDPOINT): vol.Range(0, 255),
            vol.Required(P.CLUSTER): vol.Range(0, 0xFFFF),
            vol.Required(P.ATTRIBUTE): vol.Any(
                vol.Range(0, 0xFFFF), cv.string
            ),
            vol.Optional(P.ATTR_TYPE): vol.Any(
                vol.Range(0, 255), cv.string
            ),  # String is for later
            # vol.Optional(P.ATTR_TYPE): int,  # Optional in ZCL, not used
            vol.Required(P.MIN_INTRVL): int,  # Optional in ZCL
            vol.Required(P.MAX_INTRVL): int,  # Optional in ZCL
            vol.Required(P.REPTBLE_CHG): int,  # Optional in ZCL
            # vol.Optional(P.DIR): cv.boolean,  # ZCL requires it, not used
            vol.Optional(P.MANF): vol.Range(0, 0xFFFF),
        },
        extra=vol.ALLOW_EXTRA,
    ),
    S.CONF_REPORT_READ: vol.Schema(
        {
            vol.Required(ATTR_IEEE): vol.Any(
                cv.entity_id_or_uuid, t.EUI64.convert
            ),
            vol.Optional(P.ENDPOINT): vol.Range(0, 255),
            vol.Required(P.CLUSTER): vol.Range(0, 0xFFFF),
            vol.Required(P.ATTRIBUTE): vol.Any(
                vol.Range(0, 0xFFFF),
                [vol.Any(vol.Range(0, 0xFFFF), cv.string)],
                cv.string,
            ),
            vol.Optional(P.MANF): vol.Range(0, 0xFFFF),
        },
        extra=vol.ALLOW_EXTRA,
    ),
    S.EZSP_ADD_KEY: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.EZSP_BACKUP: vol.Schema(
        {
            vol.Optional(ATTR_COMMAND_DATA): cv.string,
        },
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
        {
            vol.Required(ATTR_IEEE): vol.Any(
                cv.entity_id_or_uuid, t.EUI64.convert
            ),
            vol.Optional(P.ENDPOINT): vol.Any(cv.byte, [cv.byte]),
        },
        extra=vol.ALLOW_EXTRA,
    ),
    S.GET_ROUTES_AND_NEIGHBOURS: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.GET_ZLL_GROUPS: vol.Schema(
        {
            vol.Required(ATTR_IEEE): vol.Any(
                cv.entity_id_or_uuid, t.EUI64.convert
            ),
        },
        extra=vol.ALLOW_EXTRA,
    ),
    S.ZHA_DEVICES: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.HANDLE_JOIN: vol.Schema(
        {
            vol.Optional(ATTR_IEEE): vol.Any(
                cv.entity_id_or_uuid, t.EUI64.convert
            ),
            vol.Optional(ATTR_COMMAND_DATA): vol.Range(0, 0xFFFF),
        },
        extra=vol.ALLOW_EXTRA,
    ),
    S.IEEE_PING: vol.Schema(
        {
            vol.Required(ATTR_IEEE): vol.Any(
                cv.entity_id_or_uuid, t.EUI64.convert
            ),
        },
        extra=vol.ALLOW_EXTRA,
    ),
    S.LEAVE: vol.Schema(
        {
            vol.Required(ATTR_IEEE): vol.Any(
                cv.entity_id_or_uuid, t.EUI64.convert
            ),
        },
        extra=vol.ALLOW_EXTRA,
    ),
    S.MISC_REINITIALIZE: vol.Schema(
        {
            vol.Required(ATTR_IEEE): vol.Any(
                cv.entity_id_or_uuid, t.EUI64.convert
            ),
        },
        extra=vol.ALLOW_EXTRA,
    ),
    S.OTA_NOTIFY: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.REJOIN: vol.Schema(
        {
            vol.Required(ATTR_IEEE): vol.Any(
                cv.entity_id_or_uuid, t.EUI64.convert
            ),
            vol.Optional(ATTR_COMMAND_DATA): vol.Any(
                cv.entity_id_or_uuid, t.EUI64.convert
            ),
        },
        extra=vol.ALLOW_EXTRA,
    ),
    S.REGISTER_SERVICES: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.REMOVE_ALL_GROUPS: vol.Schema(
        {
            vol.Required(ATTR_IEEE): vol.Any(
                cv.entity_id_or_uuid, t.EUI64.convert
            ),
            vol.Optional(P.ENDPOINT): vol.Any(cv.byte, [cv.byte]),
        },
        extra=vol.ALLOW_EXTRA,
    ),
    S.REMOVE_FROM_GROUP: vol.Schema(
        {
            vol.Required(ATTR_IEEE): vol.Any(
                cv.entity_id_or_uuid, t.EUI64.convert
            ),
            vol.Required(ATTR_COMMAND_DATA): vol.Range(0, 0xFFFF),
            vol.Optional(P.ENDPOINT): vol.Any(cv.byte, [cv.byte]),
        },
        extra=vol.ALLOW_EXTRA,
    ),
    S.REMOVE_GROUP: vol.Schema(
        {
            vol.Required(ATTR_IEEE): vol.Any(
                cv.entity_id_or_uuid, t.EUI64.convert
            ),
            vol.Required(ATTR_COMMAND_DATA): vol.Range(0, 0xFFFF),
            vol.Optional(P.ENDPOINT): vol.Any(cv.byte, [cv.byte]),
        },
        extra=vol.ALLOW_EXTRA,
    ),
    S.SCAN_DEVICE: vol.Schema(
        {
            vol.Required(ATTR_IEEE): vol.Any(
                cv.entity_id_or_uuid, t.EUI64.convert
            ),
        },
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
    S.UNBIND_IEEE: vol.Schema(
        {
            vol.Required(ATTR_IEEE): vol.Any(
                cv.entity_id_or_uuid, t.EUI64.convert
            ),
            vol.Required(ATTR_COMMAND_DATA): cv.string,
            vol.Optional(P.CLUSTER): vol.Any(
                vol.Range(0, 0xFFFF), [vol.Range(0, 0xFFFF)]
            ),
        },
        extra=vol.ALLOW_EXTRA,
    ),
    S.ZCL_CMD: vol.Schema(
        {
            vol.Required(ATTR_IEEE): vol.Any(
                cv.entity_id_or_uuid, t.EUI64.convert
            ),
            vol.Optional(P.CMD): cv.string,
            vol.Optional(P.ENDPOINT): vol.Any(cv.byte, [cv.byte]),
            vol.Optional(P.CLUSTER): vol.Range(0, 0xFFFF),
            vol.Optional(P.MANF): vol.Range(0, 0xFFFF),
            vol.Optional(P.ARGS): vol.Any(
                int, list, cv.string
            ),  # Arguments to command
        },
        extra=vol.ALLOW_EXTRA,
    ),
    S.ZDO_FLOOD_PARENT_ANNCE: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.ZDO_JOIN_WITH_CODE: vol.Schema(
        {
            vol.Required(ATTR_IEEE): vol.Any(
                cv.entity_id_or_uuid, t.EUI64.convert
            ),
            vol.Optional(ATTR_COMMAND_DATA): vol.Any(
                cv.entity_id_or_uuid, t.EUI64.convert
            ),
            vol.Required(P.CODE): vol.Any(cv.string),
        },
        extra=vol.ALLOW_EXTRA,
    ),
    S.ZDO_SCAN_NOW: vol.Schema(
        {},  # No parameters
        extra=vol.ALLOW_EXTRA,
    ),
    S.ZDO_UPDATE_NWK_ID: vol.Schema(
        {},
        extra=vol.ALLOW_EXTRA,
    ),
    S.ZNP_BACKUP: vol.Schema(
        {
            vol.Optional(ATTR_COMMAND_DATA): cv.string,
        },
        extra=vol.ALLOW_EXTRA,
    ),
    S.ZNP_NVRAM_BACKUP: vol.Schema(
        {
            vol.Optional(ATTR_COMMAND_DATA): cv.string,
        },
        extra=vol.ALLOW_EXTRA,
    ),
    S.ZNP_NVRAM_RESET: vol.Schema(
        {},  # No specific options
        extra=vol.ALLOW_EXTRA,
    ),
    S.ZNP_NVRAM_RESTORE: vol.Schema(
        {},  # No specific options
        extra=vol.ALLOW_EXTRA,
    ),
    S.ZNP_RESTORE: vol.Schema(
        {
            vol.Optional(ATTR_COMMAND_DATA): int,  # counter_increment
        },
        extra=vol.ALLOW_EXTRA,
    ),
}


COMMON_SCHEMA = {
    vol.Optional(P.TRIES): cv.positive_int,
    vol.Optional(P.EVENT_SUCCESS): cv.string,
    vol.Optional(P.EVENT_FAIL): cv.string,
    vol.Optional(P.EVENT_DONE): cv.string,
    vol.Optional(
        P.FAIL_EXCEPTION
    ): cv.boolean,  # raise exception when success==False
    vol.Optional(
        P.EXPECT_REPLY
    ): cv.boolean,  # To be use where Zigpy uses 'expect_reply'
}


DENY_COMMAND_SCHEMA = {
    vol.Optional(ATTR_COMMAND): None,
}


# Command to internal command mapping for
#
# Exceptions to the ruleset:
# - Service name/cmd =  "MODULE_CMD"
# - Method in MODULE is "MODULE_CMD".
# (i.e., these commands to not have the module name at
#        at the start of the function name)
CMD_TO_INTERNAL_MAP = {
    # "COMMAND or SERVICE": ["MODULE", "modulemethod"],
    S.ADD_GROUP: ["groups", S.ADD_GROUP],
    S.ADD_TO_GROUP: ["groups", S.ADD_TO_GROUP],
    S.ALL_ROUTES_AND_NEIGHBOURS: ["neighbours", S.ALL_ROUTES_AND_NEIGHBOURS],
    S.ATTR_READ: ["zcl_attr", S.ATTR_READ],
    S.ATTR_WRITE: ["zcl_attr", S.ATTR_WRITE],
    S.BACKUP: ["misc", S.BACKUP],
    S.BIND_GROUP: ["binds", S.BIND_GROUP],
    S.BIND_IEEE: ["binds", S.BIND_IEEE],
    S.CONF_REPORT: ["zcl_attr", S.CONF_REPORT],
    S.CONF_REPORT_READ: ["zcl_attr", S.CONF_REPORT_READ],
    S.GET_GROUPS: ["groups", S.GET_GROUPS],
    S.GET_ROUTES_AND_NEIGHBOURS: ["neighbours", S.GET_ROUTES_AND_NEIGHBOURS],
    S.GET_ZLL_GROUPS: ["groups", S.GET_ZLL_GROUPS],
    S.HANDLE_JOIN: ["misc", S.HANDLE_JOIN],
    S.IEEE_PING: ["zdo", S.IEEE_PING],
    S.LEAVE: ["zdo", S.LEAVE],
    S.REJOIN: ["misc", S.REJOIN],
    S.REMOVE_ALL_GROUPS: ["groups", S.REMOVE_ALL_GROUPS],
    S.REMOVE_FROM_GROUP: ["groups", S.REMOVE_FROM_GROUP],
    S.REMOVE_GROUP: ["groups", S.REMOVE_GROUP],
    S.SCAN_DEVICE: ["scan_device", S.SCAN_DEVICE],
    S.UNBIND_COORDINATOR: ["binds", S.UNBIND_COORDINATOR],
    S.UNBIND_GROUP: ["binds", S.UNBIND_GROUP],
    S.UNBIND_IEEE: ["binds", S.UNBIND_IEEE],
    S.ZCL_CMD: ["zcl_cmd", S.ZCL_CMD],
}


async def async_setup(hass, config):
    """Set up ZHA from config."""

    if DOMAIN not in config:
        return True

    try:
        if hass.data["zha"]["zha_gateway"] is None:
            return True
    except KeyError:
        return True

    LOGGER.debug("Setup services from async_setup")
    register_services(hass)

    return True


def register_services(hass):  # noqa: C901
    zha_gw = hass.data["zha"]["zha_gateway"]

    async def toolkit_service(service):
        """Run command from toolkit module."""
        LOGGER.info("Running ZHA Toolkit service: %s", service)

        # importlib.reload(PARDEFS)
        # S = PARDEFS.SERVICES

        # Reload ourselves
        mod_path = f"custom_components.{DOMAIN}"
        try:
            module = importlib.import_module(mod_path)
        except ImportError as err:
            LOGGER.error("Couldn't load %s module: %s", DOMAIN, err)
            return

        importlib.reload(module)

        LOGGER.debug("module is %s", module)
        importlib.reload(u)

        if u.getVersion() != REGISTERED_VERSION:
            LOGGER.debug(
                "Reload services because version changed from %s to %s",
                REGISTERED_VERSION,
                u.getVersion(),
            )
            await command_handler_register_services(
                zha_gw.application_controller,
                zha_gw,
                None,  # ieee,
                None,  # cmd,
                None,  # cmd_data,
                None,  # Not needed
                params={},  # params Not needed
                event_data={},  # event_data Not needed
            )

        ieee_str = service.data.get(ATTR_IEEE)
        cmd = service.data.get(ATTR_COMMAND)
        cmd_data = service.data.get(ATTR_COMMAND_DATA)

        # Decode parameters
        params = u.extractParams(service)

        app = zha_gw.application_controller

        ieee = await u.get_ieee(app, zha_gw, ieee_str)

        slickParams = params.copy()
        for k in params.keys():
            LOGGER.debug(f"Key {p}")
            if slickParams[k] is None or slickParams[k] is False:
                del slickParams[k]

        # Preload event_data
        event_data = {
            "zha_toolkit_version": u.getVersion(),
            "zigpy_version": zigpy.__version__,
            "zigpy_rf_version": u.get_radio_version(app),
            "ieee_org": ieee_str,
            "ieee": str(ieee),
            "command": cmd,
            "command_data": cmd_data,
            "start_time": dt_util.utcnow().isoformat(),
            "errors": [],
            "params": slickParams,  # stripped version of params
        }

        if ieee is not None:
            LOGGER.debug(
                "'ieee' parameter: '%s' -> IEEE Addr: '%s'", ieee_str, ieee
            )

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
                try:
                    handler = getattr(module, f"command_handler_{cmd}")
                except AttributeError:  # nosec
                    pass

        if handler is None:
            LOGGER.debug(f"Default handler for {cmd}")
            handler = module.command_handler_default

        LOGGER.debug("Handler: %s", handler)

        handler_exception = None
        try:
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

        if not event_data["success"] and params[p.FAIL_EXCEPTION]:
            raise Exception("Success expected, but failed")

    # Set up all service schemas
    for key, value in SERVICE_SCHEMAS.items():
        value.extend(COMMON_SCHEMA)
        if key != S.EXECUTE:
            # command key is only for general "execute" - avoid confusion
            # by denying this option
            value.extend(DENY_COMMAND_SCHEMA)
        LOGGER.debug(f"Add service {DOMAIN}.{key}")
        hass.services.async_register(
            DOMAIN,
            key,
            toolkit_service,
            schema=value,
        )

    REGISTERED_VERSION = u.getVersion()


async def command_handler_default(
    app, listener, ieee, cmd, data, service, params, event_data
):
    LOGGER.debug("running default command: %s", service)

    if cmd.startswith("user_"):
        # User library in 'local' directory (user.py)

        LOGGER.debug("Import user path")
        from .local import user

        importlib.reload(user)

        handler = getattr(user, cmd)
        await handler(
            app, listener, ieee, cmd, data, service, params, event_data
        )
    else:
        from . import default

        importlib.reload(default)

        # Use default handler for generic command loading
        if cmd in CMD_TO_INTERNAL_MAP:
            cmd = CMD_TO_INTERNAL_MAP[cmd]

        await default.default(
            app, listener, ieee, cmd, data, service, params, event_data
        )


async def reload_services_yaml(hass):
    import os

    from homeassistant.const import CONF_DESCRIPTION, CONF_NAME
    from homeassistant.helpers.service import async_set_service_schema
    from homeassistant.util.yaml.loader import load_yaml

    CONF_FIELDS = "fields"

    services_yaml = os.path.join(os.path.dirname(__file__), "services.yaml")
    s_defs = load_yaml(services_yaml)

    for s in s_defs:
        # await hass.services.remove(DOMAIN, s)
        s_desc = {
            CONF_NAME: s_defs.get(s, {}).get("name", s),
            CONF_DESCRIPTION: s_defs.get(s, {}).get("description", ""),
            CONF_FIELDS: s_defs.get(s, {}).get("fields", {}),
        }
        async_set_service_schema(hass, DOMAIN, s, s_desc)


#
# To register services when modifying while system is online
#
async def command_handler_register_services(
    app, listener, ieee, cmd, data, service, params, event_data
):
    register_services(listener._hass)
    await reload_services_yaml(listener._hass)
