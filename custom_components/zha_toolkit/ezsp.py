import binascii
import logging

import bellows
import bellows.types as bt
import zigpy.zdo.types
from zigpy import types as t

from . import utils as u

LOGGER = logging.getLogger(__name__)


async def ezsp_set_channel(
    app, listener, ieee, cmd, data, service, params, event_data
):
    ch = t.uint8_t(data)
    assert 11 << ch << 26
    ch_mask = zigpy.types.Channels(1 << ch)

    LOGGER.info("Setting EZSP channel to: %s/%s", ch, ch_mask)

    aps_frame = bellows.types.EmberApsFrame(
        profileId=0x0000,
        clusterId=zigpy.zdo.types.ZDOCmd.Mgmt_NWK_Update_req,
        sourceEndpoint=0x00,
        destinationEndpoint=0x00,
        options=bellows.types.EmberApsOption.APS_OPTION_NONE,
        groupId=0x0000,
        sequence=0xDE,
    )

    status, _, network_params = await app._ezsp.getNetworkParameters()
    if status != bellows.types.EmberStatus.SUCCESS:
        msg = (
            f"Couldn't get network parameters, abort channel change: {status}"
        )
        event_data["errors"].append(msg)
        raise RuntimeError(msg)

    event_data["nwk_params"] = network_params

    payload = b"\xde" + ch_mask.serialize() + b"\xfe"
    payload += network_params.nwkUpdateId.serialize()

    status, _ = await app._ezsp.sendBroadcast(
        zigpy.types.BroadcastAddress.ALL_DEVICES,
        aps_frame,
        0x00,
        0x01,
        payload,
    )
    success = status == bellows.types.EmberStatus.SUCCESS
    event_data["success"] = success

    if not success:
        return

    res = await app._ezsp.setRadioChannel(ch)
    event_data["result"] = res
    LOGGER.info("Set channel status: %s", res)


async def ezsp_get_token(
    app, listener, ieee, cmd, data, service, params, event_data
):
    token = t.uint8_t(data)
    event_data["tokens_info"] = {}
    for token in range(0, 31):
        LOGGER.info(f"Getting {token} token...")
        res = await app._ezsp.getToken(token)
        tkInfo = {
            "status": res[0],
            "data": binascii.hexlify(res[1].serialize()),
        }
        event_data["tokens_info"][token] = tkInfo
        LOGGER.info(f"Getting token {token} status: {res[0]}")
        LOGGER.info(f"Getting token {token} data: {res[1]}")
        LOGGER.info(
            f"Getting token {token} data: "
            "{binascii.hexlify(res[1].serialize())}"
        )


async def ezsp_start_mfg(
    app, listener, ieee, cmd, data, service, params, event_data
):
    event_data["results"] = []
    LOGGER.info("Starting mfg lib")
    res = await app._ezsp.mfglibStart(True)
    event_data["results"].append(res)
    LOGGER.info("starting mfg lib result: %s", res)

    channel = 11
    res = await app._ezsp.mfglibSetChannel(channel)
    event_data["results"].append(res)
    LOGGER.info("mfg lib change channel: %s", res)

    res = await app._ezsp.mfglibEnd()
    event_data["results"].append(res)
    LOGGER.info("mfg lib change channel: %s", res)


async def ezsp_get_keys(
    app, listener, ieee, cmd, data, service, params, event_data
):
    LOGGER.info("getting all keys")
    result = {}
    erase = data is not None and data
    warnings = []
    orphans = []

    # bellows removes getKeyTableEntry from the command table at EZSP v13.
    # read_link_keys() is implemented for every protocol version and reads
    # the key table through whichever command that version provides.
    async for key in app._ezsp.read_link_keys():
        partner = key.partner_ieee
        result[str(partner)] = key
        LOGGER.info("EZSP key for %s: %s", partner, key)
        if partner not in app.devices:
            warn = f"Partner {partner} for key is not present"
            warnings.append(warn)
            LOGGER.warning(warn)
            orphans.append(partner)

    # Erase after reading the table, so the indexes are not looked up
    # while read_link_keys() is still walking it.
    if erase:
        for partner in orphans:
            (index,) = await app._ezsp.findKeyTableEntry(
                address=partner, linkKey=True
            )
            if index == 0xFF:
                warn = f"No key table entry for {partner} to erase"
                warnings.append(warn)
                LOGGER.warning(warn)
                continue
            (status,) = await app._ezsp.eraseKeyTableEntry(index=index)
            LOGGER.info("Erased key %s at %s: %s", partner, index, status)

    event_data["warnings"] = warnings
    event_data["result"] = result
    _, _, nwkParams = await app._ezsp.getNetworkParameters()
    LOGGER.info("Current network: %s", nwkParams)
    event_data["network"] = nwkParams


async def ezsp_add_transient_key(
    app, listener, ieee, cmd, data, service, params, event_data
):
    LOGGER.info("adding well known link key as transient key")
    if ieee is None:
        msg = "No ieee to install transient key for"
        LOGGER.error(msg)
        raise ValueError(msg)

    # addTransientLinkKey is gone from EZSP v13 on; add_transient_link_key
    # is implemented for every protocol version and returns sl_Status.
    status = await app._ezsp.add_transient_link_key(
        ieee, bt.KeyData(b"ZigbeeAlliance09")
    )
    LOGGER.debug("Installed key for %s: %s", ieee, status)
    event_data["result"] = status


async def ezsp_get_ieee_by_nwk(
    app, listener, ieee, cmd, data, service, params, event_data
):
    LOGGER.info("Lookup IEEE by nwk")
    nwk = u.str2int(data)
    status, eui64 = await app._ezsp.lookupEui64ByNodeId(nwk)
    LOGGER.debug("nwk: 0x%04x, ieee: %s, status: %s", nwk, eui64, status)
    event_data["nwk"] = nwk
    event_data["ieee"] = repr(eui64)
    event_data["status"] = status


async def ezsp_get_policy(
    app, listener, ieee, cmd, data, service, params, event_data
):
    policy = int(data)

    LOGGER.info("Getting EZSP %s policy id", policy)
    _status, value = await app._ezsp.getPolicy(policy)
    LOGGER.debug("policy: %s, value: %s", bt.EzspPolicyId(policy), value)
    event_data["policy"] = repr(bt.EzspPolicyId(policy))
    event_data["policy_value"] = repr(value)


async def ezsp_clear_keys(
    app, listener, ieee, cmd, data, service, params, event_data
):
    LOGGER.info("Clear key table")
    (status,) = await app._ezsp.clearKeyTable()
    LOGGER.info("Cleared key table: %s", status)
    event_data["status"] = status


async def ezsp_get_config_value(
    app, listener, ieee, cmd, data, service, params, event_data
):
    if data is None:
        msg = "Need EZSP config value"
        LOGGER.error(msg)
        raise ValueError(msg)

    cfg_id = bt.EzspConfigId(data)
    LOGGER.info("Getting EZSP configuration value: %s", cfg_id)
    status, value = await app._ezsp.getConfigurationValue(cfg_id)
    if status != bt.EzspStatus.SUCCESS:
        msg = f"Couldn't get {status} configuration value: {cfg_id}"
        LOGGER.error(msg)
        raise RuntimeError(msg)

    LOGGER.info("%s = %s", cfg_id.name, value)
    event_data["result"] = value


async def ezsp_get_value(
    app, listener, ieee, cmd, data, service, params, event_data
):
    if data is None:
        msg = "Need EZSP value id"
        LOGGER.error(msg)
        raise ValueError(msg)

    value_id = bt.EzspValueId(data)
    LOGGER.info("Getting EZSP value: %s", value_id)
    status, value = await app._ezsp.getValue(value_id)
    if status != bt.EzspStatus.SUCCESS:
        msg = f"Couldn't get {status} value: {value_id}"
        LOGGER.error(msg)
        raise RuntimeError(msg)

    LOGGER.info("%s = %s", value_id.name, value)
    event_data["ezsp_" + value_id.name] = repr(value)


# Legacy implementation
#
# See https://github.com/zigpy/bellows/tree/dev/bellows/cli
#
# Code essentially from
# https://github.com/zigpy/bellows/blob/dev/bellows/cli/backup.py
#
async def ezsp_backup_legacy(
    app, listener, ieee, cmd, data, service, params, event_data
):
    if u.get_radiotype(app) != u.RadioType.EZSP:
        msg = f"'{cmd}' is only available for BELLOWS/EZSP"
        LOGGER.debug(msg)
        raise ValueError(msg)

    # Import stuff we need
    import json

    from bellows.cli.backup import (  # isort:skip
        ATTR_NODE_TYPE,
        ATTR_NODE_ID,
        ATTR_NODE_EUI64,
        ATTR_PAN_ID,
        ATTR_EXT_PAN_ID,
        ATTR_RADIO_CHANNEL,
        ATTR_RADIO_TX_PWR,
        ATTR_NWK_UPDATE_ID,
        ATTR_CHANNELS,
        ATTR_KEY_GLOBAL,
        ATTR_KEY_NWK,
        ATTR_KEY_PARTNER,
        ATTR_KEY_TABLE,
        _backup_keys,
    )

    status, node_type, network = await app._ezsp.getNetworkParameters()
    assert status == bt.EmberStatus.SUCCESS
    assert node_type == bt.EmberNodeType.COORDINATOR
    LOGGER.debug("Network params: %s", network)

    (node_id,) = await app._ezsp.getNodeId()
    (ieee,) = await app._ezsp.getEui64()

    result = {
        ATTR_NODE_TYPE: node_type.value,
        ATTR_NODE_ID: node_id,
        ATTR_NODE_EUI64: str(ieee),
        ATTR_PAN_ID: network.panId,
        ATTR_EXT_PAN_ID: str(network.extendedPanId),
        ATTR_RADIO_CHANNEL: network.radioChannel,
        ATTR_RADIO_TX_PWR: network.radioTxPower,
        ATTR_NWK_UPDATE_ID: network.nwkUpdateId,
        ATTR_CHANNELS: network.channels,
    }

    for key_name, key_type in (
        (ATTR_KEY_GLOBAL, bt.EmberKeyType.TRUST_CENTER_LINK_KEY),
        (ATTR_KEY_NWK, bt.EmberKeyType.CURRENT_NETWORK_KEY),
    ):
        status, key = await app._ezsp.getKey(key_type)
        assert status == bt.EmberStatus.SUCCESS
        LOGGER.debug("%s key: %s", key_name, key)
        result[key_name] = key.as_dict()
        #
        result[key_name][ATTR_KEY_PARTNER] = str(key.partnerEUI64)

    keys = await _backup_keys(app._ezsp)
    result[ATTR_KEY_TABLE] = keys

    # Store backup information to file

    # Set name with regards to local path
    out_dir = u.get_local_dir()

    # Ensure that data is an empty string when not set
    if data is None:
        data = ""

    fname = out_dir + "nwk_backup" + str(data) + ".json"

    with open(fname, "w", encoding="utf_8") as jsonfile:
        jsonfile.write(json.dumps(result, indent=4))


async def ezsp_dummy_networkInit():
    return (bellows.types.EmberStatus.SUCCESS,)


async def ezsp_click_get_echo(s):
    LOGGER.error(f"GET_ECHO: {s}")
    bellows.cli._result = s


async def ezsp_backup(
    app, listener, ieee, cmd, data, service, params, event_data
):
    if u.get_radiotype(app) != u.RadioType.EZSP:
        msg = f"'{cmd}' is only available for BELLOWS/EZSP"
        LOGGER.debug(msg)
        raise ValueError(msg)

    # Import stuff we need
    import io
    import json
    from contextlib import redirect_stdout

    from bellows.cli import backup as bellows_backup

    try:
        # Network is already initialised, fake result for backup function
        org_network_init = app._ezsp.networkInit
        app._ezsp.networkInit = ezsp_dummy_networkInit
        f = io.StringIO()
        with redirect_stdout(f):
            await bellows_backup._backup(app._ezsp)
        result = f.getvalue()
    finally:
        app._ezsp.networkInit = org_network_init  # pylint: disable=E0601

    # Store backup information to file

    # Set name with regards to local path
    out_dir = u.get_local_dir()

    # Ensure that data is an empty string when not set
    if data is None:
        data = ""

    fname = out_dir + "nwk_backup" + str(data) + ".json"

    with open(fname, "w", encoding="utf_8") as jsonfile:
        jsonfile.write(json.dumps(json.loads(result), indent=4))
