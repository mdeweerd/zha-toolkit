import asyncio
import logging

import zigpy.types as t
from zigpy.exceptions import ControllerException, DeliveryError

from . import utils as u
from .params import INTERNAL_PARAMS as p

LOGGER = logging.getLogger(__name__)


async def get_routes(
    app, listener, ieee, cmd, data, service, params, event_data
):
    LOGGER.debug("getting routes command: %s", service)

    for dev in app.devices.values():
        if hasattr(dev, "relays"):
            status = f"has routes: {dev.relays}"
        else:
            status = "doesn't have routes"
        LOGGER.debug("Device %s/%s %s", dev.nwk, dev.model, status)

    LOGGER.debug("finished device get_routes")


async def backup(app, listener, ieee, cmd, data, service, params, event_data):
    """Backup Coordinator Configuration."""

    radio_type = u.get_radiotype(app)

    if radio_type == u.RadioType.ZNP:
        from . import znp

        await znp.znp_backup(
            app,
            listener,
            ieee,
            cmd,
            data,
            service,
            event_data=event_data,
            params=params,
        )
        await znp.znp_nvram_backup(
            app,
            listener,
            ieee,
            cmd,
            data,
            service,
            event_data=event_data,
            params=params,
        )
    elif radio_type == u.RadioType.EZSP:
        from . import ezsp

        await ezsp.ezsp_backup(
            app,
            listener,
            ieee,
            cmd,
            data,
            service,
            event_data=event_data,
            params=params,
        )
    else:
        raise ValueError(f"Radio type {radio_type} not supported for backup")


async def handle_join(
    app, listener, ieee, cmd, data, service, params, event_data
):
    """Rediscover a device.
    ieee -- ieee of the device
    data -- nwk of the device in decimal format
    """
    LOGGER.debug("running 'handle_join' command: %s", service)
    if ieee is None:
        LOGGER.debug("Provide 'ieee' parameter for %s", cmd)
        raise ValueError("ieee parameter missing")

    dev = await u.get_device(app, listener, ieee)

    if data is None:
        if dev is None:
            LOGGER.debug(
                f"Device {ieee!r} missing in device table, provide NWK address"
            )
            raise ValueError(f"Missing NWK for unknown device '{ieee}'")

        data = dev.nwk

    # Handle join will initialize the device if it isn't yet, otherwise
    # only scan groups
    # misc_reinitialise is more complete

    event_data["result"] = app.handle_join(u.str2int(data), ieee, None)


async def misc_reinitialize(
    app, listener, ieee, cmd, data, service, params, event_data
):
    """Reinitialize a device, rediscover endpoints
    ieee -- ieee of the device
    """
    if ieee is None:
        msg = f"Provide 'ieee' parameter for {cmd}"
        LOGGER.debug(msg)
        raise ValueError(ieee)

    dev = await u.get_device(app, listener, ieee)
    LOGGER.debug(f"{ieee!r} - Set initialisations=False, call handle_join")
    # dev.has_non_zdo_endpoints = False  # Force rescan
    # Can't set: dev.non_zdo_endpoints = False  # Force rescan
    dev.endpoints = {0: dev.zdo}  # Force rescan

    # dev._znp = u.get_radio(app)
    # dev.node_desc = None  # Force rescan

    dev.all_endpoint_init = False  # Force rescan
    dev.model = None  # Force rescan
    dev.manufacturer = None  # Force rescan
    # event_data["result"] = await dev.schedule_initialize()
    event_data["result"] = await dev.initialize()


async def rejoin(app, listener, ieee, cmd, data, service, params, event_data):
    """Leave and rejoin command.
    data -- device ieee to allow joining through
    ieee -- ieee of the device to leave and rejoin
    """
    if ieee is None:
        LOGGER.error("missing ieee")
        return
    LOGGER.debug("running 'rejoin' command: %s", service)
    src = await u.get_device(app, listener, ieee)

    if data is None:
        await app.permit()
    else:
        await app.permit(node=t.EUI64.convert_ieee(data))

    method = 1
    res = None

    if method == 0:
        # Works on HA 2021.12.10 & ZNP - rejoin is 1:
        res = await u.retry_wrapper(
            src.zdo.request, 0x0034, src.ieee, 0x01, params[p.TRIES]
        )
    elif method == 1:
        # Works on ZNP but apparently not on bellows:
        triesToGo = params[p.TRIES]
        tryIdx = 0
        event_data["success"] = False
        while triesToGo >= 1:
            triesToGo = triesToGo - 1
            tryIdx += 1
            try:
                LOGGER.debug(f"Leave with rejoin - try {tryIdx}")
                res = await src.zdo.leave(remove_children=False, rejoin=True)
                event_data["success"] = True
                triesToGo = 0  # Stop loop
                # event_data["success"] = (
                #     resf[0][0].status == f.Status.SUCCESS
                # )
            except (
                DeliveryError,
                ControllerException,
                asyncio.TimeoutError,
            ) as d:
                event_data["errors"].append(repr(d))
                continue
            except Exception as e:  # Catch all others
                triesToGo = 0  # Stop loop
                LOGGER.debug("Leave with rejoin exception %s", e)
                event_data["errors"].append(repr(e))

    elif method == 2:
        # Results in rejoin bit 0 on ZNP
        LOGGER.debug("Using Method 2 for Leave")
        res = await u.retry_wrapper(
            src.zdo.request, 0x0034, src.ieee, 0x80, params[p.TRIES]
        )
    elif method == 3:
        # Results in rejoin and leave children bit set on ZNP
        LOGGER.debug("Using Method 3 for Leave")
        res = await u.retry_wrapper(
            src.zdo.request, 0x0034, src.ieee, 0xFF, params[p.TRIES]
        )
    elif method == 4:
        # Results in rejoin and leave children bit set on ZNP
        LOGGER.debug("Using Method 4 for Leave")
        res = await u.retry_wrapper(
            src.zdo.request, 0x0034, src.ieee, 0x83, params[p.TRIES]
        )
    else:
        res = "Not executed, no valid 'method' defined in code"

    event_data["result"] = res
    LOGGER.debug("%s -> %s: leave and rejoin result: %s", src, ieee, res)


async def misc_settime(
    app, listener, ieee, cmd, data, service, params, event_data
):
    from bisect import bisect
    from datetime import datetime

    import pytz
    from homeassistant.util.dt import DEFAULT_TIME_ZONE, utcnow

    LOGGER.debug(f"Default time zone {DEFAULT_TIME_ZONE}")
    tz = pytz.timezone(str(DEFAULT_TIME_ZONE))

    utc_time = utcnow().astimezone(pytz.UTC).replace(tzinfo=None)
    index = bisect(
        tz._utc_transition_times, utc_time  # type:ignore[union-attr]
    )

    if index is None:
        event_data["success"] = False
        event_data[
            "msg"
        ] = "misc_settime expects DST changes, needs update if None"

    try:
        if (
            tz._utc_transition_times[index]  # type:ignore[union-attr]
            .replace(tzinfo=pytz.UTC)
            .astimezone(tz)
            .dst()
            .total_seconds()
            == 0
        ):
            # First date must be start of dst period
            index = index - 1

        dst1_obj = tz._utc_transition_times[index]  # type:ignore[union-attr]
        dst2_obj = tz._utc_transition_times[  # type:ignore[union-attr]
            index + 1
        ]
        epoch2000 = datetime(2000, 1, 1, tzinfo=None)
        dst1 = (dst1_obj - epoch2000).total_seconds()
        dst2 = (dst2_obj - epoch2000).total_seconds()
        dst1_aware = tz._utc_transition_times[  # type:ignore[union-attr]
            index
        ].replace(tzinfo=pytz.UTC)
        dst2_aware = tz._utc_transition_times[  # type:ignore[union-attr]
            index + 1
        ].replace(tzinfo=pytz.UTC)

        dst1_local = dst1_aware.astimezone(tz)
        dst2_local = dst2_aware.astimezone(tz)

        dst_shift = dst1_local.dst().total_seconds()
        utc_offset = dst2_local.utcoffset().total_seconds()

        LOGGER.debug(
            f"Next dst changes {dst1_obj} .. {dst2_obj}"
            f" EPOCH 2000 {dst1} .. {dst2}"
        )
        LOGGER.debug(
            f"Local {dst1_local} {dst2_local} in {tz}"
            f" {dst1_local.dst().total_seconds()}"
            f" {dst2_local.dst().total_seconds()}"
        )
        LOGGER.debug(f"UTC OFFSET: {utc_offset}  DST OFFSET: {dst_shift}")

        dev = await u.get_device(app, listener, ieee)
        params[p.CLUSTER_ID] = 0x000A  # Time Cluster
        cluster = u.get_cluster_from_params(dev, params, event_data)

        # Prepare read and write lists
        attr_read_list = [
            0,
            1,
            2,
            3,
            4,
            5,
        ]  # Time, Timestatus, Timezone, DstStart, DstEnd, DstShift

        if params[p.READ_BEFORE_WRITE]:
            read_resp = await cluster.read_attributes(attr_read_list)
            event_data["read_before"] = (
                u.dict_to_jsonable(read_resp[0]),
                read_resp[1],
            )
            u.record_read_data(read_resp, cluster, params, listener)

        EPOCH2000_TIMESTAMP = 946684800
        utctime_towrite = utcnow().timestamp() - EPOCH2000_TIMESTAMP
        attr_write_list = {
            0x0000: utctime_towrite,  # Time
            0x0002: utc_offset,  # Timezone - int32
            0x0003: dst1,  # DstStart - uint32
            0x0004: dst2,  # DstEnd - uint32
            0x0005: dst_shift,  # DstEnd - uint32
        }

        event_data["result_write"] = await cluster.write_attributes(
            attr_write_list
        )

        if params[p.READ_AFTER_WRITE]:
            read_resp = await cluster.read_attributes(attr_read_list)
            event_data["read_after"] = (
                u.dict_to_jsonable(read_resp[0]),
                read_resp[1],
            )
            u.record_read_data(read_resp, cluster, params, listener)

        event_data["success"] = True
    except DeliveryError as e:
        event_data["success"] = False
        event_data["msg"] = f"{e!r}"
