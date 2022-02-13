# 
# Sample 'user.py' script 
# 
# 'user.py' should be located in the 'local' directory of the 
# zha_toolkit custom component.
#
import logging

from zigpy import types as t

LOGGER = logging.getLogger(__name__)


async def user_test(
    app, listener, ieee, cmd, data, service, params, event_data
):
    # To be called as a service:
    #
    # ```yaml
    # service: zha_toolkit.execute
    # data:
    #   command: user_test
    # ```

    # Just a stub, does nothing special
    LOGGER.debug(f"User test called")


async def user_sinope_write_test(
    app, listener, ieee, cmd, data, service, params, event_data
):
    # To be called as a service:
    #
    # ```yaml
    # service: zha_toolkit.execute
    # data:
    #   command: user_sinope_write_test
    # ```

    # User ignores all parameters from service and uses local values
    # This user specific example writes attributes to a precise
    # sinope thermostat.

    ieee = t.EUI64.deserialize(b"\xae\x09\x01\x00\x40\x91\x0b\x50")[0]

    dev = app.get_device(ieee)

    cluster = dev.endpoints[1].thermostat

    res = await cluster.read_attributes([9])
    LOGGER.info("Reading attr status: %s", res)

    attrs = {0x0009: 0b00001000, 0x0012: 1400, 0x001C: 0xFF}
    LOGGER.debug("Writing test attrs to thermostat cluster: %s", attrs)
    res = await cluster.write_attributes(attrs)
    event_data['result'] = res
    LOGGER.info("Writing attrs status: %s", res)


async def user_zigpy_deconz(
    app, listener, ieee, cmd, data, service, params, event_data
):
    # To be called as a service:
    #
    # ```yaml
    # service: zha_toolkit.execute
    # data:
    #   command: user_zigpy_deconz
    # ```

    # User changes channel of EZSP
    LOGGER.debug("Removing EZSP")
    res = await app._ezsp.setRadioChannel(20)
    LOGGER.debug("set channel %s", res)
    return


    # User skipped this previous custom code (due to return above)
    LOGGER.debug("Getting model from iris: %s", service)

    ieee = t.EUI64(b"\x00\x0d\x6f\x00\x0f\x3a\xf6\xa6")
    dev = app.get_device(ieee=ieee)

    cluster = dev.endpoints[2].basic
    res = await cluster.read_attributes(
        ["model", "manufacturer"], allow_cache=False
    )
    LOGGER.info("Iris 2nd ep attr read: %s", res)
