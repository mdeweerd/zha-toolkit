# import asyncio
import logging

import zigpy.types as t

from . import utils as u

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
        raise Exception("ieee parameter missing")
    if data is None:
        dev = None
        try:
            dev = app.get_device(ieee=ieee)
            data = dev.nwk
            if data is None:
                raise Exception(f"Missing NWK for device '{ieee}'")
            LOGGER.debug("Using NWK '%s' for '%s'", data, ieee)
        except Exception as e:
            LOGGER.debug(
                "Device '%s' not found in device table, provide NWK address",
                ieee,
            )
            raise e

    event_data["result"] = app.handle_join(u.str2int(data), ieee, 0)


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

    # Next method is not working - rejoin is 0:
    # res = await src.zdo.request(0x0034, src.ieee, 0x01)
    res = await src.zdo.leave(remove_children=False, rejoin=True)
    event_data["result"] = res
    LOGGER.debug("%s: leave and rejoin result: %s", src, ieee, res)
