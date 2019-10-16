import binascii
import logging

from zigpy import types as t

LOGGER = logging.getLogger(__name__)


async def set_channel(app, listener, ieee, cmd, data, service):
    ch = t.uint8_t(data)
    LOGGER.info("Setting EZSP channel to: %s", ch)
    res = await app._ezsp.setRadioChannel(ch)
    LOGGER.info("Writing attrs status: %s", res)

async def get_token(app, listener, ieee, cmd, data, service):
    token = t.uint8_t(data)
    for token in range(0, 31):
        LOGGER.info(f"Getting {token} token...")
        res = await app._ezsp.getToken(token)
        LOGGER.info(f"Getting token {token} status: {res[0]}")
        LOGGER.info(f"Getting token {token} data: {res[1]}")
        LOGGER.info((f"Getting token {token} data: "
                      "{binascii.hexlify(res[1].serialize())}"))
