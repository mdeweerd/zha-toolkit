import asyncio
import logging
import os
from collections import OrderedDict

from zigpy.exceptions import DeliveryError
from zigpy.util import retryable

from homeassistant.util.json import save_json

LOGGER = logging.getLogger(__name__)


async def get_routes(app, listener, ieee, cmd, data, service):
    LOGGER.debug("getting routes command: %s", service)

    for dev in app.devices.values():
        if hasattr(dev, "relays"):
            status = f"has routes: {dev.relays}"
        else:
            status = "doesn't have routes"
        LOGGER.debug("Device %s/%s %s", dev.nwk, dev.model, status)

    LOGGER.debug("finished device get_routes")
