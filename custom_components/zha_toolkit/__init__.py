import importlib
import logging
from typing import Any, Optional

import homeassistant.helpers.config_validation as cv
import voluptuous as vol

try:
    from homeassistant.components.zha import Gateway as ZHAGateway
except ImportError:
    from homeassistant.components.zha.core.gateway import ZHAGateway

from homeassistant.util import dt as dt_util
from zigpy import types as t
from zigpy.exceptions import DeliveryError

from . import params as PARDEFS
from . import utils as u

DEPENDENCIES = ["zha"]

DOMAIN = "zha_toolkit"

# Legacy parameters
ATTR_COMMAND = "command"
ATTR_COMMAND_DATA = "command_data"
ATTR_IEEE = "ieee"

DATA_ZHATK = "zha_toolkit"

LOGGER = logging.getLogger(__name__)

try:
    LOADED_VERSION  # type:ignore[used-before-def] # pylint: disable=used-before-assignment
except NameError:
    LOADED_VERSION = ""

try:
    DEFAULT_OTAU  # type:ignore[used-before-def] # pylint: disable=used-before-assignment
except NameError:
    DEFAULT_OTAU = "/config/zigpy_ota"


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
            vol.Optional(P.DST_ENDPOINT): vol.Any(cv.byte, [cv.byte]),
            vol.Optional(P.CLUSTER): vol.Range(0, 0xFFFF),
            vol.Optional(P.ATTRIBUTE): vol.Any(
                vol.Range(0, 0xFFFF), cv.string
            ),
            vol.Optional(P.ATTR_TYPE): vol.Any(
                int, cv.string
            ),  # String is for later
            vol.Optional(P.ATTR_VAL): vol.Any(cv.string, float, int, list),
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
            # Template can't be used for check:
            # vol.Optional(P.STATE_VALUE_TEMPLATE): cv.template,
            vol.Optional(P.STATE_VALUE_TEMPLATE): cv.string,
            vol.Optional(P.FORCE_UPDATE): cv.boolean,
            vol.Optional(P.USE_CACHE): vol.Any(vol.Range(0, 2), cv.boolean),
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
            vol.Optional(P.CLUSTER): vol.Range(0, 0xFFFF),
            vol.Required(P.ATTRIBUTE): vol.Any(
                vol.Range(0, 0xFFFF), cv.string
            ),
            vol.Optional(P.MANF): vol.Range(0, 0xFFFF),
            vol.Optional(P.EXPECT_REPLY): cv.boolean,
            vol.Optional(P.STATE_ID): cv.string,
            vol.Optional(P.STATE_ATTR): cv.string,
            # Template can't be used for check:
            # vol.Optional(P.STATE_VALUE_TEMPLATE): cv.template,
            vol.Optional(P.STATE_VALUE_TEMPLATE): cv.string,
            vol.Optional(P.FORCE_UPDATE): cv.boolean,
            vol.Optional(P.USE_CACHE): vol.Any(vol.Range(0, 2), cv.boolean),
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
            vol.Optional(P.CLUSTER): vol.Range(0, 0xFFFF),
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
            # Template can't be used for check:
            # vol.Optional(P.STATE_VALUE_TEMPLATE): cv.template,
            vol.Optional(P.STATE_VALUE_TEMPLATE): cv.string,
            vol.Optional(P.FORCE_UPDATE): cv.boolean,
            vol.Optional(P.USE_CACHE): vol.Any(vol.Range(0, 2), cv.boolean),
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
            vol.Optional(ATTR_COMMAND_DATA): cv.string,
            vol.Optional(P.CLUSTER): vol.Any(
                vol.Range(0, 0xFFFF), [vol.Range(0, 0xFFFF)]
            ),
            vol.Optional(P.DST_ENDPOINT): vol.Range(0, 255),
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
            vol.Optional(ATTR_COMMAND_DATA): vol.Any(
                cv.entity_id_or_uuid, t.EUI64.convert
            ),
            vol.Optional(P.ENDPOINT): vol.Any(
                vol.Range(0, 255), [vol.Range(0, 255)]
            ),
            vol.Optional(P.CLUSTER): vol.Any(
                vol.Range(0, 0xFFFF), [vol.Range(0, 0xFFFF)]
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
            vol.Optional(P.CLUSTER): vol.Range(0, 0xFFFF),
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
            vol.Optional(P.CLUSTER): vol.Range(0, 0xFFFF),
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
        {
            vol.Required(ATTR_IEEE): vol.Any(
                cv.entity_id_or_uuid, t.EUI64.convert
            ),
        },
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
    S.HA_SET_STATE: vol.Schema(
        {
            vol.Required(P.ATTR_VAL): vol.Any(
                list,
                float,
                int,
                cv.string,
            ),
            vol.Required(P.STATE_ID): cv.string,
            vol.Optional(P.STATE_ATTR): cv.string,
            # Template can't be used for check:
            # vol.Optional(P.STATE_VALUE_TEMPLATE): cv.template,
            vol.Optional(P.STATE_VALUE_TEMPLATE): cv.string,
            vol.Optional(P.FORCE_UPDATE): cv.boolean,
            vol.Optional(P.ALLOW_CREATE): cv.boolean,
            vol.Optional(P.OUTCSV): cv.string,
            vol.Optional(P.CSVLABEL): cv.string,
        },
        extra=vol.ALLOW_EXTRA,
    ),
    S.ZHA_DEVICES: vol.Schema(
        {
            vol.Optional(ATTR_IEEE): vol.Any(
                cv.entity_id_or_uuid, t.EUI64.convert
            ),
        },
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
            vol.Required(ATTR_COMMAND_DATA): vol.Any(
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
    S.MISC_SETTIME: vol.Schema(
        {
            vol.Required(ATTR_IEEE): vol.Any(
                cv.entity_id_or_uuid, t.EUI64.convert
            ),
            vol.Optional(P.ENDPOINT): vol.Range(0, 255),
            vol.Optional(P.READ_BEFORE_WRITE): cv.boolean,
            vol.Optional(P.READ_AFTER_WRITE): cv.boolean,
        },
        extra=vol.ALLOW_EXTRA,
    ),
    S.OTA_NOTIFY: vol.Schema(
        {
            vol.Required(ATTR_IEEE): vol.Any(
                cv.entity_id_or_uuid, t.EUI64.convert
            ),
            vol.Optional(P.PATH): cv.string,
            vol.Optional(P.DOWNLOAD): cv.boolean,
        },
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
    S.TUYA_MAGIC: vol.Schema(
        {
            vol.Required(ATTR_IEEE): vol.Any(
                cv.entity_id_or_uuid, t.EUI64.convert
            ),
        },
        extra=vol.ALLOW_EXTRA,
    ),
    S.UNBIND_COORDINATOR: vol.Schema(
        {
            vol.Required(ATTR_IEEE): vol.Any(
                cv.entity_id_or_uuid, t.EUI64.convert
            ),
            vol.Optional(P.ENDPOINT): vol.Any(
                vol.Range(0, 255), [vol.Range(0, 255)]
            ),
            vol.Optional(P.CLUSTER): vol.Any(
                vol.Range(0, 0xFFFF), [vol.Range(0, 0xFFFF)]
            ),
        },
        extra=vol.ALLOW_EXTRA,
    ),
    S.UNBIND_GROUP: vol.Schema(
        {},
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
    S.ZCL_CMD: ["zcl_cmd", S.ZCL_CMD],
}

ZHA_DOMAIN = "zha"


async def async_setup(hass, config):
    """Set up ZHA from config."""

    if DOMAIN not in config:
        return True

    try:
        global DEFAULT_OTAU  # pylint: disable=global-statement
        DEFAULT_OTAU = config[ZHA_DOMAIN]["zigpy_config"]["ota"][
            "otau_directory"
        ]
        LOGGER.debug("DEFAULT_OTAU = %s", DEFAULT_OTAU)
    except KeyError:
        # Ignore if the value is not set
        pass

    try:
        if hass.data["zha"] is None:
            LOGGER.error(
                "Not initializing zha_toolkit: "
                "hass.data['zha'] is None,"
                " - zha_toolkit needs zha (not deconz, not zigbee2mqtt)."
            )
            return True
    except KeyError:
        LOGGER.error(
            "Not initializing zha_toolkit: "
            "Missing hass.data['zha']"
            " - zha_toolkit needs zha (not deconz, not zigbee2mqtt)."
        )
        return True

    LOGGER.debug("Setup services from async_setup")
    await register_services(hass)

    return True


async def register_services(hass):  # noqa: C901
    global LOADED_VERSION  # pylint: disable=global-statement
    hass_ref = hass

    is_response_data_supported = u.is_ha_ge("2023.7.0")

    if is_response_data_supported:
        from homeassistant.core import SupportsResponse

    async def toolkit_service(service):
        """Run command from toolkit module."""
        LOGGER.info("Running ZHA Toolkit service: %s", service)
        global LOADED_VERSION  # pylint: disable=global-variable-not-assigned

        zha = hass_ref.data["zha"]
        zha_gw: Optional[ZHAGateway] = u.get_zha_gateway(hass)
        zha_gw_hass: Any = u.get_zha_gateway_hass(hass)

        if zha_gw is None:
            LOGGER.error(
                "Missing hass.data['zha']/gateway - not found/running %s - on %r",
                service,
                zha,
            )
        LOGGER.debug(
            "Got hass.data['zha']/gateway %r",
            zha_gw,
        )

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

        currentVersion = await u.getVersion()
        if currentVersion != LOADED_VERSION:
            LOGGER.debug(
                "Reload services because VERSION changed from %s to %s",
                LOADED_VERSION,
                currentVersion,
            )
            await _register_services(hass)

        ieee_str = service.data.get(ATTR_IEEE)
        cmd = service.data.get(ATTR_COMMAND)
        cmd_data = service.data.get(ATTR_COMMAND_DATA)

        # Decode parameters
        params = u.extractParams(service)

        app = zha_gw.application_controller  # type: ignore

        ieee = await u.get_ieee(app, zha_gw_hass, ieee_str)

        slickParams = params.copy()
        for k in params:
            if slickParams[k] is None or slickParams[k] is False:
                del slickParams[k]

        service_cmd = service.service  # Lower case service name in domain

        # This method can be called as the 'execute' service or
        # with the specific service
        if cmd is None:
            cmd = service_cmd

        # Preload event_data
        event_data = {
            "zha_toolkit_version": currentVersion,
            "zigpy_version": u.getZigpyVersion(),
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
        handler_result = None
        try:
            handler_result = await handler(
                zha_gw.application_controller,  # type: ignore
                zha_gw_hass,
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
                u.get_hass(zha_gw).bus.fire(params[p.EVT_SUCCESS], event_data)
        else:
            if params[p.EVT_FAIL] is not None:
                LOGGER.debug("Fire %s -> %s", params[p.EVT_FAIL], event_data)
                u.get_hass(zha_gw).bus.fire(params[p.EVT_FAIL], event_data)

        if params[p.EVT_DONE] is not None:
            LOGGER.debug("Fire %s -> %s", params[p.EVT_DONE], event_data)
            u.get_hass(zha_gw).bus.fire(params[p.EVT_DONE], event_data)

        if handler_exception is not None:
            LOGGER.error(
                "Exception '%s' for service call with data '%r'",
                handler_exception,
                event_data,
            )
            if params[p.FAIL_EXCEPTION] or not isinstance(
                handler_exception, DeliveryError
            ):
                raise handler_exception

        if not event_data["success"] and params[p.FAIL_EXCEPTION]:
            raise RuntimeError("Success expected, but failed")

        if is_response_data_supported:
            if service.return_response:
                if handler_result is None:
                    return event_data

                return handler_result

    # Set up all service schemas
    for key, value in SERVICE_SCHEMAS.items():
        value.extend(COMMON_SCHEMA)
        if key != S.EXECUTE:
            # command key is only for general "execute" - avoid confusion
            # by denying this option
            value.extend(DENY_COMMAND_SCHEMA)
        LOGGER.debug(f"Add service {DOMAIN}.{key}")
        if is_response_data_supported:
            # See https://developers.home-assistant.io/docs/dev_101_services/#response-data
            hass.services.async_register(
                DOMAIN,
                key,
                toolkit_service,
                schema=value,
                supports_response=SupportsResponse.OPTIONAL,  # type:ignore[undefined-variable]
            )
        else:
            hass.services.async_register(
                DOMAIN,
                key,
                toolkit_service,
                schema=value,
            )

    LOADED_VERSION = await u.getVersion()


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
            cmd = CMD_TO_INTERNAL_MAP.get(cmd)

        return await default.default(
            app, listener, ieee, cmd, data, service, params, event_data
        )


def reload_services_yaml(hass):
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


async def _register_services(hass):
    register_services(hass)
    await hass.async_add_executor_job(reload_services_yaml, hass)


#
# To register services when modifying while system is online
#
async def command_handler_register_services(
    app, listener, ieee, cmd, data, service, params, event_data
):
    await _register_services(u.get_hass(listener))
