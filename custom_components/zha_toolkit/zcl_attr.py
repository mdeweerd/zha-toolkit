from __future__ import annotations

import asyncio
import logging

from homeassistant.helpers.template import Template
from homeassistant.util import dt as dt_util
from zigpy import types as t
from zigpy.exceptions import ControllerException, DeliveryError
from zigpy.zcl import Cluster
from zigpy.zcl import foundation as f

from . import utils as u
from .params import INTERNAL_PARAMS as p
from .params import SERVICES as S

LOGGER = logging.getLogger(__name__)

if not hasattr(Cluster, "_read_reporting_configuration"):
    if hasattr(f, "GeneralCommand"):
        GeneralCommand = f.GeneralCommand
    else:
        GeneralCommand = f.Command

    def read_reporting_configuration(
        self, cfg: t.List[f.ReadReportingConfigRecord], **kwargs
    ):
        command = f.COMMANDS[0x08]
        if isinstance(command, f.ZCLCommandDef):
            # Since zigpy 0.44.0
            schema = command.schema
        else:
            # Before zigpy 0.44.0
            schema = command[0]

        # LOGGER.error(f"SELF:{self!r}")
        # LOGGER.error(f"COMMAND:{command!r}")
        # LOGGER.error(f"SCHEMA:{schema!r}")
        # data = t.serialize([cfg], schema)
        # LOGGER.error(f"SERIALIZED:{data!r}")

        return self.request(
            True,  # General, bool
            0x08,  # Command id
            schema,  # Schema
            cfg,  # args
            **kwargs,
        )

    Cluster._read_reporting_configuration = read_reporting_configuration

    # Cluster._read_reporting_configuration = (
    #     functools.partial(
    #         Cluster.general_command,
    #         GeneralCommand.Read_Reporting_Configuration,
    #     ),
    # )


async def my_read_reporting_configuration_multiple(
    self, attributes: list[int | str], direction: int = 0, **kwargs
) -> list[f.AttributeReportingConfig]:
    """
    Read Report Configuration for multiple attributes in the same request.
    :param attributes: list of attributes to read read report conf from
    """

    cfg: list[f.ReadReportingConfigRecord] = []

    for attribute in attributes:
        if isinstance(attribute, str):
            attrid = self.attributes_by_name[attribute].id
        else:
            # Allow reading attributes that aren't defined
            attrid = attribute
        record = f.ReadReportingConfigRecord()
        record.attrid = attrid
        record.direction = direction
        # LOGGER.warning(f"Record {record.direction} {record.attrid}")
        cfg.append(record)
    LOGGER.debug("Read reporting with %s %r", cfg, kwargs)
    param = t.List[f.ReadReportingConfigRecord](cfg)
    LOGGER.debug("Resolves to %s", param)

    # Exception is propagated to caller if any
    res = await self._read_reporting_configuration(
        t.List[f.ReadReportingConfigRecord](cfg), **kwargs
    )

    try:
        LOGGER.debug("Read reporting with %s result %s", cfg, res)
    except Exception as e:
        LOGGER.warning("Error when reporting result of Read Report %r", e)

    # Parse configure reporting result for unsupported attributes
    records = res[0]
    if (
        isinstance(records, list)
        and not (len(records) == 1 and records[0].status == f.Status.SUCCESS)
        and len(records) >= 0
    ):
        try:
            failed = [
                r.attrid
                for r in records
                if r.status == f.Status.UNSUPPORTED_ATTRIBUTE
            ]
            for attr in failed:
                self.add_unsupported_attribute(attr)
        except Exception as e:
            LOGGER.error(
                "Issue when reading ReadReportingConfig result %r : %r",
                records,
                e,
            )
    return res


Cluster.my_read_reporting_configuration_multiple = (
    my_read_reporting_configuration_multiple
)


async def conf_report_read(
    app, listener, ieee, cmd, data, service, params, event_data
):
    dev = await u.get_device(app, listener, ieee)
    cluster = u.get_cluster_from_params(dev, params, event_data)

    if False:  # pylint: disable=using-constant-test
        schema = f.COMMANDS[0x08][0]
        LOGGER.error(f"SCHEMA:{schema!r}")

        record = f.ReadReportingConfigRecord()
        record.attrid = 0
        record.direction = 0

        cfg: list[f.ReadReportingConfigRecord] = []
        cfg.append(record)

        param = t.List[f.ReadReportingConfigRecord](cfg)
        LOGGER.warning("Read reporting with %s", param)

        # data = t.serialize([param,], schema)
        # LOGGER.error(f"SERIALIZED:{data!r}")

        event_data["result"] = await cluster.request(
            True,  # General, bool
            0x08,  # Command id
            schema,  # Schema
            param,
            manufacturer=params[p.MANF],  # Added, not tested
            expect_reply=True,
        )

        return

    triesToGo = params[p.TRIES]
    event_data["success"] = True
    result_conf = None
    event_data["result_conf"] = []

    if not isinstance(params[p.ATTR_ID], list):
        params[p.ATTR_ID] = [params[p.ATTR_ID]]

    while triesToGo >= 1:  # pylint: disable=too-many-nested-blocks
        triesToGo = triesToGo - 1
        try:
            LOGGER.debug(
                "Try %s/%s: read report configuration (%s,%s)",
                params[p.TRIES] - triesToGo,
                params[p.TRIES],
                params[p.ATTR_ID],
                params[p.MANF],
            )
            result_conf = (
                await cluster.my_read_reporting_configuration_multiple(
                    params[p.ATTR_ID],
                    manufacturer=params[p.MANF],
                )
            )
            LOGGER.debug("Got result %s", result_conf)
            triesToGo = 0  # Stop loop

            LOGGER.info("Read Report Configuration result: %s", result_conf)
            if result_conf is None:
                event_data["success"] = False
            else:
                for cfg_with_status in result_conf.attribute_configs:
                    rcfg: f.AttributeReportingConfig = cfg_with_status.config
                    attr_id = rcfg.attrid
                    r_conf = {
                        "cluster": cluster.name,
                        "cluster_id": f"0x{cluster.cluster_id:04X}",
                        "ep": cluster.endpoint.endpoint_id,
                        "attr_id": f"0x{attr_id:04X}",
                        "direction": rcfg.direction,
                        "status": cfg_with_status.status,
                    }
                    try:
                        r_conf["type"] = f"0x{rcfg.datatype:02X}"
                        r_conf["min_interval"] = (rcfg.min_interval,)
                        r_conf["max_interval"] = (rcfg.max_interval,)
                        r_conf["reportable_change"] = (
                            getattr(rcfg, "reportable_change", None),
                        )
                    except Exception as e:  # nosec
                        LOGGER.error(
                            "Issue when reading AttributesReportingConfig"
                            " result %r %r",
                            rcfg,
                            e,
                        )
                    try:
                        # Try to add name of the attribute
                        attr_def = cluster.attributes.get(
                            attr_id, (str(attr_id), None)
                        )
                        if u.is_zigpy_ge("0.50.0") and isinstance(
                            attr_def, f.ZCLAttributeDef
                        ):
                            attr_name = attr_def.name
                        else:
                            attr_name = attr_def[0]

                        if attr_name is not None and attr_name != "":
                            r_conf["attr"] = attr_name
                    except Exception:  # nosec
                        pass

                    event_data["result_conf"].append(r_conf)
        except (
            DeliveryError,
            ControllerException,
            asyncio.CancelledError,
            asyncio.TimeoutError,
        ):
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
    dev = await u.get_device(app, listener, ieee)

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
            event_data["result_conf"] = result_conf
            triesToGo = 0  # Stop loop
            LOGGER.info("Configure report result: %s", result_conf)
            event_data["success"] = (
                result_conf[0][0].status == f.Status.SUCCESS
            )
        except (
            DeliveryError,
            ControllerException,
            asyncio.CancelledError,
            asyncio.TimeoutError,
        ):
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


async def attr_read(*args, **kwargs):
    # Delegate to attr_write which also handles the read command.
    await attr_write(*args, **kwargs)


# This code is shared with attr_read.
# Can read and write 1 attribute
async def attr_write(  # noqa: C901
    app, listener, ieee, cmd, data, service, params, event_data
):
    success = True

    dev = await u.get_device(app, listener, ieee)
    cluster = u.get_cluster_from_params(dev, params, event_data)

    # Prepare read and write lists
    attr_write_list: list[f.Attribute] = []
    attr_read_list = []

    state_template_str = params[p.STATE_VALUE_TEMPLATE]

    use_cache = params[p.USE_CACHE]

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

    attr_type = params[p.ATTR_TYPE]

    result_read = None
    if params[p.READ_BEFORE_WRITE] or (attr_read_list and cmd == S.ATTR_READ):
        if use_cache > 0:
            # Try to get value from cache
            if attr_id in cluster._attr_cache:
                result_read = ({attr_id: cluster._attr_cache[attr_id]}, {})
                LOGGER.debug(
                    f"Got attribute 0x{cluster.cluster_id:04X}/0x{attr_id:04X}"
                    f" from cache: {result_read!r}"
                )
            else:
                LOGGER.debug(
                    f"Attribute 0x{cluster.cluster_id:04X}/0x{attr_id:04X}"
                    " not in cache"
                )
                # Fail if not falling back
                success = use_cache == 1
        if use_cache == 0 or (  # Pure read
            result_read is None and use_cache == 2
        ):  # Not in cache, fall back
            LOGGER.debug("Request attr read %s", attr_read_list)
            # pylint: disable=unexpected-keyword-arg
            result_read = await u.cluster_read_attributes(
                cluster,
                attr_read_list,
                manufacturer=params[p.MANF],
                tries=params[p.TRIES],
            )
            LOGGER.debug(
                "Reading attr result (attrs, status): %s", result_read
            )
            success = (len(result_read[1]) == 0) and (len(result_read[0]) == 1)

            # Try to get attribute type
            if success and (attr_id in result_read[0]):
                python_type = type(result_read[0][attr_id])
                found_attr_type = f.DataType.from_python_type(
                    python_type
                ).type_id
                LOGGER.debug(
                    "Type determined from read: 0x%02x", found_attr_type
                )

                if attr_type is None:
                    attr_type = found_attr_type
                elif attr_type != found_attr_type:
                    LOGGER.warning(
                        "Type determined from read "
                        "different from requested: 0x%02X <> 0x%02X",
                        found_attr_type,
                        attr_id,
                    )

    compare_val = None

    if cmd == "attr_write":
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

    # Use serialize to compare if the compare_val allows it
    use_serialize = callable(getattr(compare_val, "serialize", None))

    if attr_type is not None:
        event_data["attr_type"] = f"0x{attr_type:02X}"

    # True if value that should be written is the equal to the read one
    write_is_equal = (
        (params[p.READ_BEFORE_WRITE])
        and (len(attr_write_list) != 0)
        and compare_val is not None
        and (
            (attr_id in result_read[0])  # type:ignore[index]
            and (
                result_read[0][  # type:ignore[index]
                    attr_id
                ].serialize()  # type:ignore[union-attr]
                == compare_val.serialize()
                if use_serialize
                else result_read[0][  # type:ignore[index]
                    attr_id
                ]  # type:ignore[union-attr]
                == compare_val
            )
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
        # pylint: disable=unexpected-keyword-arg
        result_write = await u.cluster__write_attributes(
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
            # pylint: disable=unexpected-keyword-arg
            result_read = await u.cluster_read_attributes(
                cluster,
                attr_read_list,
                manufacturer=params[p.MANF],
                tries=params[p.TRIES],
            )
            LOGGER.debug(
                f"Reading attr result (attrs, status): {result_read!r}"
            )
            # read_is_equal = (result_read[0][attr_id] == compare_val)
            success = success and (
                len(result_read[1]) == 0 and len(result_read[0]) == 1
            )
            if success and compare_val is not None:
                if (
                    result_read[0][attr_id].serialize()
                    != compare_val.serialize()
                    if use_serialize
                    else result_read[0][attr_id] != compare_val
                ):
                    success = False
                    msg = "Read does not match expected: {!r} <> {!r}".format(
                        result_read[0][attr_id].serialize()
                        if use_serialize
                        else result_read[0][attr_id],
                        compare_val.serialize()
                        if use_serialize
                        else compare_val,
                    )
                    LOGGER.warning(msg)
                    if "warnings" not in event_data:
                        event_data["warnings"] = []
                    event_data["warnings"].append(msg)

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
            for attr_id, val in result_read[0].items():
                if state_template_str is not None:
                    if val is None:
                        LOGGER.debug(
                            "Value is None and template active,"
                            " do not set state %s[%s]",
                            params[p.STATE_ID],
                            params[p.STATE_ATTR],
                        )

                    template = Template(
                        "{{ " + state_template_str + " }}",
                        u.get_hass(listener),
                    )
                    try:
                        val = template.async_render(value=val, attr_val=val)
                    except Exception as e:
                        LOGGER.debug(
                            "Issue when computing template (%r),"
                            " skip setting state",
                            e,
                        )
                        success = False
                        continue

                if params[p.STATE_ATTR] is not None:
                    LOGGER.debug(
                        "Set state %s[%s] -> %s from attr_id %s",
                        params[p.STATE_ID],
                        params[p.STATE_ATTR],
                        val,
                        attr_id,
                    )
                else:
                    LOGGER.debug(
                        "Set state %s -> %s from attr_id %s",
                        params[p.STATE_ID],
                        val,
                        attr_id,
                    )
                u.set_state(
                    u.get_hass(listener),
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
                attr_def = cluster.attributes.get(
                    attr_id, (str(attr_id), None)
                )
                if u.is_zigpy_ge("0.50.0") and isinstance(
                    attr_def, f.ZCLAttributeDef
                ):
                    attr_name = attr_def.name
                else:
                    attr_name = attr_def[0]
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
            f"0x{params[p.MANF]:04X}" if params[p.MANF] is not None else ""
        )
        fields.append(f"0x{attr_type:02X}" if attr_type is not None else "")

        u.append_to_csvfile(
            fields,
            "csv",
            params[p.CSV_FILE],
            f"{attr_name}={read_val}",
            listener=listener,
        )

    for key in ["read_before", "result_read"]:
        if key not in event_data:
            continue
        event_data[key] = (
            u.dict_to_jsonable(event_data[key][0]),
            event_data[key][1],
        )

    # For internal use
    return result_read

    # Example where attributes are not types
    # (supposed typed by the internals):
    #   attrs = {0x0009: 0b00001000, 0x0012: 1400, 0x001C: 0xFF}
    #   result = await cluster'.write_attributes(attrs)
