# import asyncio
import logging
import asyncio

import zigpy.types as t
from zigpy.exceptions import DeliveryError

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


async def backup(app, listener, ieee, cmd, data, service, event_data, params):
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
        raise Exception(
            "Radio type %s not supported for backup" % (radio_type)
        )


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
    if data is None:
        dev = None
        try:
            dev = app.get_device(ieee=ieee)
            data = dev.nwk
            if data is None:
                raise Exception(f"Missing NWK for device '{ieee}'")
            LOGGER.debug(f"Using NWK '{data}' for '{ieee!r}'")
        except Exception as e:
            LOGGER.debug(
                f"Device {ieee!r} missing in device table, provide NWK address"
            )
            raise e

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

    dev = app.get_device(ieee=ieee)
    LOGGER.debug(f"{ieee!r} - Set initialisations=False, call handle_join")
    dev.node_desc = None  # Force rescan
    dev.has_non_zdo_endpoint = False  # Force rescan
    dev.all_endpoint_init = False  # Force rescan
    dev.model = None  # Force rescan
    dev.manufacturer = None  # Force rescan
    event_data["result"] = dev.schedule_initialize()


async def rejoin(app, listener, ieee, cmd, data, service, params, event_data):
    """Leave and rejoin command.
    data -- device ieee to allow joining through
    ieee -- ieee of the device to leave and rejoin
    """
    if ieee is None:
        LOGGER.error("missing ieee")
        return
    LOGGER.debug("running 'rejoin' command: %s", service)
    src = app.get_device(ieee=ieee)

    if data is None:
        await app.permit()
    else:
        await app.permit(node=t.EUI64.convert_ieee(data))

    method = 1
    res = None

    if method == 0:
        # Works on HA 2021.12.10 & ZNP - rejoin is 1:
        res = await src.zdo.request(0x0034, src.ieee, 0x01, params[p.TRIES])
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
            except (DeliveryError, asyncio.TimeoutError) as d:
                event_data["errors"].append(repr(d))
                continue
            except Exception as e:  # Catch all others
                triesToGo = 0  # Stop loop
                LOGGER.debug("Leave with rejoin exception %s", e)
                event_data["errors"].append(repr(e))

    elif method == 2:
        # Results in rejoin bit 0 on ZNP
        LOGGER.debug("Using Method 2 for Leave")
        res = await src.zdo.request(0x0034, src.ieee, 0x80, params[p.TRIES])
    elif method == 3:
        # Results in rejoin and leave children bit set on ZNP
        LOGGER.debug("Using Method 3 for Leave")
        res = await src.zdo.request(0x0034, src.ieee, 0xFF, params[p.TRIES])
    elif method == 4:
        # Results in rejoin and leave children bit set on ZNP
        LOGGER.debug("Using Method 4 for Leave")
        res = await src.zdo.request(0x0034, src.ieee, 0x83, params[p.TRIES])
    else:
        res = "Not executed, no valid 'method' defined in code"

    event_data["result"] = res
    LOGGER.debug("%s: leave and rejoin result: %s", src, ieee, res)
