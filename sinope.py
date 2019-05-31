import logging

from zigpy import types as t

LOGGER = logging.getLogger(__name__)


async def sinope_write_test(app, listener, ieee, cmd, data, service):
    ieee = t.EUI64.deserialize(b'\xae\x09\x01\x00\x40\x91\x0b\x50')[0]
    dev = app.get_device(ieee)

    cluster = dev.endpoints[1].thermostat

    res = await cluster.read_attributes([9])
    LOGGER.info("Reading attr status: %s", res)

    attrs = {
        0x0009: 0b00001000,
        0x0012: 1400,
        0x001c: 0xff,
    }
    LOGGER.debug("Writing test attrs to thermostat cluster: %s", attrs)
    res = await cluster.write_attributes(attrs)
    LOGGER.info("Writing attrs status: %s", res)
