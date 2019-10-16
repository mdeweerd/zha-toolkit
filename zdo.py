import logging

import zigpy.zdo.types as zdo_t

LOGGER = logging.getLogger(__name__)


async def leave(app, listener, ieee, cmd, data, service):
    if ieee is None or not data:
        LOGGER.warning("Incorrect parameters for 'zdo.leave' command: %s",
                       service)
        return
    LOGGER.debug("running 'leave' command. Telling 0x%s to remove %s: %s",
                 data, ieee, service)
    parent = int(data, base=16)
    parent = app.get_device(nwk=parent)

    res = await parent.zdo.request(zdo_t.ZDOCmd.Mgmt_Leave_req, ieee, 0x02)
    LOGGER.debug("0x%04x: Mgmt_Leave_req: %s", parent.nwk, res)
