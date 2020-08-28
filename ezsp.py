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
        LOGGER.info(
            (f"Getting token {token} data: " "{binascii.hexlify(res[1].serialize())}")
        )


async def start_mfg(app, listener, ieee, cmd, data, service):
    LOGGER.info("Starting mfg lib")
    res = await app._ezsp.mfglibStart(True)
    LOGGER.info("starting mfg lib result: %s", res)

    channel = 11
    res = await app._ezsp.mfglibSetChannel(channel)
    LOGGER.info("mfg lib change channel: %s", res)

    res = await app._ezsp.mfglibEnd()
    LOGGER.info("mfg lib change channel: %s", res)


async def get_keys(app, listener, ieee, cmd, data, service):
    LOGGER.info("getting all keys")
    result = {}
    erase = True if data is not None and data else False

    for idx in range(0, 192):
        LOGGER.debug("Getting key index %s", idx)
        (status, key_struct) = await app._ezsp.getKeyTableEntry(idx)
        if status == app._ezsp.types.EmberStatus.SUCCESS:
            result[idx] = key_struct
            if key_struct.partnerEUI64 not in app.devices:
                LOGGER.warning("Partner %s for key %s is not present", key_struct.partnerEUI64, idx)
                if erase:
                    await app._ezsp.eraseKeyTableEntry(idx)
        elif status == app._ezsp.types.EmberStatus.INDEX_OUT_OF_RANGE:
            break
        else:
            LOGGER.warning("No key at %s idx: %s", idx, status)

    for idx in result:
        LOGGER.info("EZSP %s key: %s", idx, result[idx])


async def add_transient_key(app, listener, ieee, cmd, data, service):
    LOGGER.info("adding well known link key as transient key")
    if ieee is None:
        LOGGER.error("No ieee to install transient key for")

    (status,) = await app._ezsp.addTransientLinkKey(ieee, b"ZigbeeAlliance09")
    LOGGER.debug("Installed key for %s: %s", ieee, status)


async def clear_keys(app, listener, ieee, cmd, data, service):
    LOGGER.info("Clear key table")
    (status,) = await app._ezsp.clearKeyTable()
    LOGGER.info("Cleared key table: %s", status)


async def get_config_value(app, listener, ieee, cmd, data, service):
    if data is None:
        LOGGER.error("Need EZSP config value")
        return

    cfg_id = app._ezsp.types.EzspConfigId(data)
    LOGGER.info("Getting EZSP configuration value: %s", cfg_id)
    (status, value) = await app._ezsp.getConfigurationValue(cfg_id)
    if status != app._ezsp.types.EzspStatus.SUCCESS:
        LOGGER.error("Couldn't get %s configuration value: %s", status, cfg_id)
        return

    LOGGER.info("%s = %s", cfg_id.name, value)


async def get_value(app, listener, ieee, cmd, data, service):
    if data is None:
        LOGGER.error("Need EZSP value id")
        return

    value_id = app._ezsp.types.EzspValueId(data)
    LOGGER.info("Getting EZSP value: %s", value_id)
    (status, value) = await app._ezsp.getValue(value_id)
    if status != app._ezsp.types.EzspStatus.SUCCESS:
        LOGGER.error("Couldn't get %s value: %s", status, value_id)
        return

    LOGGER.info("%s = %s", value_id.name, value)
