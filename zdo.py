import logging

import zigpy.zdo.types as zdo_t

LOGGER = logging.getLogger(__name__)


async def leave(app, listener, ieee, cmd, data, service):
    if ieee is None or not data:
        LOGGER.warning("Incorrect parameters for 'zdo.leave' command: %s", service)
        return
    LOGGER.debug(
        "running 'leave' command. Telling 0x%s to remove %s: %s", data, ieee, service
    )
    parent = int(data, base=16)
    parent = app.get_device(nwk=parent)

    res = await parent.zdo.request(zdo_t.ZDOCmd.Mgmt_Leave_req, ieee, 0x02)
    LOGGER.debug("0x%04x: Mgmt_Leave_req: %s", parent.nwk, res)


async def ieee_ping(app, listener, ieee, cmd, data, service):
    if ieee is None:
        LOGGER.warning("Incorrect parameters for 'ieee_ping' command: %s", service)
        return
    dev = app.get_device(ieee=ieee)

    LOGGER.debug("running 'ieee_ping' command to 0x%s", dev.nwk)

    res = await dev.zdo.request(zdo_t.ZDOCmd.IEEE_addr_req, dev.nwk, 0x00, 0x00)
    LOGGER.debug("0x%04x: IEEE_addr_req: %s", dev.nwk, res)
