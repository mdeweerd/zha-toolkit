#
# Sample 'user.py' script
#
# 'user.py' should be located in the 'local' directory of the
# zha_toolkit custom component.
#
import logging

from zigpy import types as t

from custom_components.zha_toolkit import utils as u
from custom_components.zha_toolkit.params import INTERNAL_PARAMS as p

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
    LOGGER.debug("User test called")


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

    dev = await u.get_device(app, listener, ieee)

    cluster = dev.endpoints[1].thermostat

    res = await cluster.read_attributes([9])
    LOGGER.info("Reading attr status: %s", res)

    attrs = {0x0009: 0b00001000, 0x0012: 1400, 0x001C: 0xFF}
    LOGGER.debug("Writing test attrs to thermostat cluster: %s", attrs)
    res = await cluster.write_attributes(attrs)
    event_data["result"] = res
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
    LOGGER.debug("Set channel %s", res)
    return

    # User skipped this previous custom code (due to return above)
    # pylint: disable=unreachable
    LOGGER.debug("Getting model from iris: %s", service)

    ieee = t.EUI64(b"\x00\x0d\x6f\x00\x0f\x3a\xf6\xa6")
    dev = await u.get_device(app, listener, ieee)

    cluster = dev.endpoints[2].basic
    res = await cluster.read_attributes(
        ["model", "manufacturer"], allow_cache=False
    )
    LOGGER.info("Iris 2nd ep attr read: %s", res)


async def user_tuya_magic(
    app, listener, ieee, cmd, data, service, params, event_data
):
    """
    Send Tuya 'magic spell' sequence to device
    to try to get 'normal' behavior.
    """

    dev = await u.get_device(app, listener, ieee)
    basic_cluster = dev.endpoints[1].in_clusters[0]

    # The magic spell is needed only once.
    # TODO: Improve by doing this only once (successfully).

    # Magic spell - part 1
    attr_to_read = [4, 0, 1, 5, 7, 0xFFFE]
    res = await u.cluster_read_attributes(
        basic_cluster, attr_to_read, tries=params[p.TRIES]
    )

    event_data["result"] = res

    # Magic spell - part 2 (skipped - does not seem to be needed)
    # attr_to_write={0xffde:13}
    # basic_cluster.write_attributes(attr_to_write, tries=3)
