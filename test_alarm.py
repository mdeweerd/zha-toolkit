import asyncio
import binascii
import logging
from collections import namedtuple

from zigpy.util import retryable
from zigpy.exceptions import DeliveryError


_LOGGER = logging.getLogger(__name__)


@retryable((DeliveryError, asyncio.TimeoutError), tries=5)
async def read_attr(cluster, attrs):
    return await cluster.read_attributes(attrs, allow_cache=False)


@retryable((DeliveryError, asyncio.TimeoutError), tries=5)
def wrapper(cmd, *args, **kwargs):
    return cmd(*args, **kwargs)


async def alarm(device):
    cluster = device.endpoints[1].ias_wd
    try:
        res = await wrapper(cluster.start_warning, 0b01001001, 20, 50, 0x02)
        _LOGGER.debug("squawk command result: %s", res)
    except DeliveryError as err:
        _LOGGER.error("Sendind squawk command failed: %s", err)
