import logging

import zigpy.types as t

LOGGER = logging.getLogger(__name__)


async def zigpy_deconz(
    app, listener, ieee, cmd, data, service, params, event_data
):
    LOGGER.debug("Removing EZSP")
    res = await app._ezsp.setRadioChannel(20)
    LOGGER.debug("set channel %s", res)
    return
    LOGGER.debug("Getting model from iris: %s", service)

    ieee = t.EUI64(b"\x00\x0d\x6f\x00\x0f\x3a\xf6\xa6")
    dev = app.get_device(ieee=ieee)

    cluster = dev.endpoints[2].basic
    res = await cluster.read_attributes(
        ["model", "manufacturer"], allow_cache=False
    )
    LOGGER.info("Iris 2nd ep attr read: %s", res)
