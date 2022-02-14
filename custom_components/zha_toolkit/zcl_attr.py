from __future__ import annotations

import asyncio
import functools
import importlib
import logging

from homeassistant.util import dt as dt_util
from zigpy.exceptions import DeliveryError
from zigpy.util import retryable
from zigpy.zcl import Cluster
from zigpy.zcl import foundation as f

from . import utils as u
from .params import INTERNAL_PARAMS as p
from .params import SERVICES as S

LOGGER = logging.getLogger(__name__)

if True or not hasattr(Cluster, "_read_reporting_configuration"):
    if hasattr(f, "GeneralCommand"):
        GeneralCommand = f.GeneralCommand
    else:
        GeneralCommand = f.Command

    Cluster._read_reporting_configuration = (
        functools.partial(
            Cluster.general_command,
            GeneralCommand.Read_Reporting_Configuration,
        ),
    )


async def my_read_reporting_configuration_multiple(
    self,
    attributes: list[int | str],
    manufacturer: int | None = None,
    direction: int = 0,
) -> list[f.AttributeReportingConfig]:
    """Read Report Configuration for multiple attributes in the same request.
    :param attributes: list of attributes to read read report conf from
    :param manufacturer: optional manufacturer id to use with the command
    """

    cfg = []

    for attribute in attributes:
        if isinstance(attribute, str):
            attrid = self.attributes_by_name[attribute].id
        else:
            # Allow reading attributes that aren't defined
            attrid = attribute
        record = f.ReadReportingConfigRecord
        record.direction = direction
        record.attrid = attrid
        cfg.append(record)
    LOGGER.warn("Read reporting with %s", cfg)
    try:
        res = await self._read_reporting_configuration(
            cfg, manufacturer=manufacturer
        )
    except Exception as e:
        LOGGER.warn(f"Exception {e!r}")
        return []

    LOGGER.warn("Read reporting with %s result %s", cfg, res)

    # Parse configure reporting result for unsupported attributes
    records = res[0]
    if (
        isinstance(records, list)
        and not (len(records) == 1 and records[0].status == f.Status.SUCCESS)
        and len(records) >= 0
    ):
        failed = [
            r.attrid
            for r in records
            if r.status == f.Status.UNSUPPORTED_ATTRIBUTE
        ]
        for attr in failed:
            self.add_unsupported_attribute(attr)
    return res


Cluster.my_read_reporting_configuration_multiple = (
    my_read_reporting_configuration_multiple
)


async def conf_report_read(
    app, listener, ieee, cmd, data, service, params, event_data
):
    dev = app.get_device(ieee=ieee)
    cluster = u.get_cluster_from_params(dev, params, event_data)

    triesToGo = params[p.TRIES]
    event_data["success"] = False
    result_conf = None

    if not isinstance(params[p.ATTR_ID], list):
        params[p.ATTR_ID] = [params[p.ATTR_ID]]

    while triesToGo >= 1:
        triesToGo = triesToGo - 1
        try:
            LOGGER.debug(
                "Try %s/%s: read report configuration (%s,%s)",
                params[p.TRIES] - triesToGo,
                params[p.TRIES],
                params[p.ATTR_ID],
                params[p.MANF],
            )
            LOGGER.debug("Before call")
            result_conf = (
                await cluster.my_read_reporting_configuration_multiple(
                    params[p.ATTR_ID],
                    manufacturer=params[p.MANF],
                )
            )
            LOGGER.debug("Got result %s", result_conf)
            event_data["result_conf"] = result_conf
            triesToGo = 0  # Stop loop
            LOGGER.info("Read Report Configuration result: %s", result_conf)
            if result_conf is None:
                event_data["success"] = False
            else:
                event_data["success"] = (
                    result_conf[0][0].status == f.Status.SUCCESS
                )
        except (DeliveryError, asyncio.CancelledError, asyncio.TimeoutError):
            continue
        except Exception as e:
            triesToGo = 0  # Stop loop
            LOGGER.debug(
                "Read report configuration exception %s,%s,%s",
                e,
                params[p.ATTR_ID],
                params[p.MANF],
            )
            raise e


async def conf_report(
    app, listener, ieee, cmd, data, service, params, event_data
):
    dev = app.get_device(ieee=ieee)

    cluster = u.get_cluster_from_params(dev, params, event_data)

    # await cluster.bind()  -> commented, not performing bind to coordinator

    triesToGo = params[p.TRIES]
    event_data["success"] = False
    result_conf = None

    while triesToGo >= 1:
        triesToGo = triesToGo - 1
        try:
            LOGGER.debug(
                "Try %s/%s: configure report(%s,%s,%s,%s,%s)",
                params[p.TRIES] - triesToGo,
                params[p.TRIES],
                params[p.ATTR_ID],
                params[p.MIN_INTERVAL],
                params[p.MAX_INTERVAL],
                params[p.REPORTABLE_CHANGE],
                params[p.MANF],
            )
            result_conf = await cluster.configure_reporting(
                params[p.ATTR_ID],
                params[p.MIN_INTERVAL],
                params[p.MAX_INTERVAL],
                params[p.REPORTABLE_CHANGE],
                manufacturer=params[p.MANF],
            )
            event_data["params"] = params
            event_data["result_conf"] = result_conf
            triesToGo = 0  # Stop loop
            LOGGER.info("Configure report result: %s", result_conf)
            event_data["success"] = (
                result_conf[0][0].status == f.Status.SUCCESS
            )
        except (DeliveryError, asyncio.CancelledError, asyncio.TimeoutError):
            continue
        except Exception as e:
            triesToGo = 0  # Stop loop
            LOGGER.debug(
                "Configure report exception %s,%s,%s,%s,%s,%s",
                e,
                params[p.ATTR_ID],
                params[p.MIN_INTERVAL],
                params[p.MAX_INTERVAL],
                params[p.REPORTABLE_CHANGE],
                params[p.MANF],
            )


# The zigpy library does not offer retryable on read_attributes.
# Add it ourselves
@retryable(
    (DeliveryError, asyncio.CancelledError, asyncio.TimeoutError), tries=1
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


async def attr_read(*args, **kwargs):
    # Delegate to attr_write which also handles the read command.
    await attr_write(*args, **kwargs)


# This code is shared with attr_read.
# Can read and write 1 attribute
async def attr_write(  # noqa: C901
    app, listener, ieee, cmd, data, service, params, event_data
):
    success = True

    dev = app.get_device(ieee=ieee)
    cluster = u.get_cluster_from_params(dev, params, event_data)

    # Prepare read and write lists
    attr_write_list = []
    attr_read_list = []

    # Decode attribute(s)
    #  Currently only one attribute is possible, but the parameter
    #  format could allow for multiple attributes for instance by
    #  adding a split character such as ':' for attr_id, attr_type
    #  and attr_value
    # Then the match should be in a loop

    attr_id = u.get_attr_id(cluster, params[p.ATTR_ID])
    if attr_id is None:
        msg = f"Could not determine attribute id for '{params[p.ATTR_ID]}'"
        event_data["errors"].append(msg)
        raise ValueError(msg)

    attr_read_list.append(attr_id)  # Read before write list

    compare_val = None

    if cmd == "attr_write":
        attr_type = params[p.ATTR_TYPE]
        attr_val_str = params[p.ATTR_VAL]

        if attr_type is None:
            attr_type = u.get_attr_type(cluster, attr_id)

        # Type only needed for write
        if attr_type is None or attr_val_str is None:
            event_data["errors"].append(
                "attr_type and attr_val must be set for attr_write"
            )
        else:
            attr_val, msg, compare_val = u.attr_encode(attr_val_str, attr_type)
            event_data["compare_val"] = compare_val
            if attr_type in [0x41, 0x42]:  # Octet string
                event_data["str"] = attr_val_str

            if msg is not None:
                event_data["errors"].append(msg)

            if attr_val is not None:
                attr = f.Attribute(attr_id, value=attr_val)
                attr_write_list.append(attr)  # Write list

    result_read = None
    if (
        params[p.READ_BEFORE_WRITE]
        or (len(attr_write_list) == 0)
        or (cmd != S.ATTR_WRITE)
    ):
        LOGGER.debug("Re]uest attr read %s", attr_read_list)
        result_read = await cluster_read_attributes(
            cluster,
            attr_read_list,
            manufacturer=params[p.MANF],
            tries=params[p.TRIES],
        )
        LOGGER.debug("Reading attr result (attrs, status): %s", result_read)
        success = (len(result_read[1]) == 0) and (len(result_read[0]) == 1)

    # True if value that should be written is the equal to the read one
    write_is_equal = (
        (params[p.READ_BEFORE_WRITE])
        and (len(attr_write_list) != 0)
        and (
            (attr_id in result_read[0])  # type:ignore[index]
            and (result_read[0][attr_id] == compare_val)  # type:ignore[index]
        )
    )

    event_data["write_is_equal"] = write_is_equal
    if write_is_equal and (cmd == "attr_write"):
        event_data["info"] = "Data read is equal to data to write"

    if (
        len(attr_write_list) != 0
        and (
            not (params[p.READ_BEFORE_WRITE])
            or params[p.WRITE_IF_EQUAL]
            or not (write_is_equal)
        )
        and cmd == "attr_write"
    ):

        if result_read is not None:
            event_data["read_before"] = result_read
            result_read = None

        LOGGER.debug("Request attr write %s", attr_write_list)
        result_write = await cluster__write_attributes(
            cluster,
            attr_write_list,
            manufacturer=params[p.MANF],
            tries=params[p.TRIES],
        )
        LOGGER.debug("Write attr status: %s", result_write)
        event_data["result_write"] = result_write
        success = False
        try:
            # LOGGER.debug("Write attr status: %s", result_write[0][0].status)
            success = result_write[0][0].status == f.Status.SUCCESS
            LOGGER.debug(f"Write success: {success}")
        except Exception as e:
            event_data["errors"].append(repr(e))
            success = False

        # success = (len(result_write[1])==0)

        if params[p.READ_AFTER_WRITE]:
            LOGGER.debug(f"Request attr read {attr_read_list!r}")
            result_read = await cluster_read_attributes(
                cluster,
                attr_read_list,
                manufacturer=params[p.MANF],
                tries=params[p.TRIES],
            )
            LOGGER.debug(
                f"Reading attr result (attrs, status): {result_read!r}"
            )
            # read_is_equal = (result_read[0][attr_id] == compare_val)
            success = (
                success
                and (len(result_read[1]) == 0 and len(result_read[0]) == 1)
                and (result_read[0][attr_id] == compare_val)
            )

    if result_read is not None:
        event_data["result_read"] = result_read
        if len(result_read[1]) == 0:
            read_val = result_read[0][attr_id]
        else:
            msg = (
                f"Result: {result_read[1]}"
                + f" - Attribute {attr_id} not in read {result_read!r}"
            )
            LOGGER.warning(msg)
            if "warnings" not in event_data:
                event_data["warnings"] = []
            event_data["warnings"].append(msg)
            success = False
    else:
        read_val = None

    event_data["success"] = success

    # Write value to provided state or state attribute
    if params[p.STATE_ID] is not None:
        if len(result_read[1]) == 0 and len(result_read[0]) == 1:
            # No error and one result
            for id, val in result_read[0].items():
                if params[p.STATE_ATTR] is not None:
                    LOGGER.debug(
                        "Set state %s[%s] -> %s from attr_id %s",
                        params[p.STATE_ID],
                        params[p.STATE_ATTR],
                        val,
                        id,
                    )
                else:
                    LOGGER.debug(
                        "Set state %s -> %s from attr_id %s",
                        params[p.STATE_ID],
                        val,
                        id,
                    )
                u.set_state(
                    listener._hass,
                    params[p.STATE_ID],
                    val,
                    key=params[p.STATE_ATTR],
                    allow_create=params[p.ALLOW_CREATE],
                )
                LOGGER.debug("STATE is set")

    if success and params[p.CSV_FILE] is not None:
        fields = []
        if params[p.CSV_LABEL] is not None:
            attr_name = params[p.CSV_LABEL]
        else:
            try:
                attr_name = cluster.attributes.get(
                    attr_id, (str(attr_id), None)
                )[0]
            except Exception:
                attr_name = attr_id

        fields.append(dt_util.utcnow().isoformat())
        fields.append(cluster.name)
        fields.append(attr_name)
        fields.append(read_val)
        fields.append(f"0x{attr_id:04X}")
        fields.append(f"0x{cluster.cluster_id:04X}")
        fields.append(cluster.endpoint.endpoint_id)
        fields.append(str(cluster.endpoint.device.ieee))
        fields.append(
            ("0x%04X" % (params[p.MANF])) if params[p.MANF] is not None else ""
        )
        u.append_to_csvfile(
            fields,
            "csv",
            params[p.CSV_FILE],
            f"{attr_name}={read_val}",
            listener=listener,
        )

    importlib.reload(u)
    if "result_read" in event_data and not u.isJsonable(
        event_data["result_read"]
    ):
        event_data["result_read"] = repr(event_data["result_read"])

    # For internal use
    return result_read

    # Example where attributes are not types
    # (supposed typed by the internals):
    #   attrs = {0x0009: 0b00001000, 0x0012: 1400, 0x001C: 0xFF}
    #   result = await cluster'.write_attributes(attrs)
