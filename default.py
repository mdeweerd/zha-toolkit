import logging

from zigpy import types as t
from zigpy.zcl import foundation
import zigpy.zcl as zcl

LOGGER = logging.getLogger(__name__)


# This file is reimported, so it's easier to add and tweak during development
async def default_handler(app, listener, ieee, cmd, data, service):

