import binascii
import logging

from zigpy import types as t
import zigpy.zdo.types
import bellows
import bellows.types

from . import utils as u

LOGGER = logging.getLogger(__name__)


async def set_channel(app, listener, ieee, cmd, data, service, params={}, event_data={}):
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
        msg = ("Couldn't get network parameters, abort channel change: %s" % (status))
        event_data['errors'].append(msg)
        LOGGER.error(msg)
        return

    payload = b"\xDE" + ch_mask.serialize() + b"\xFE"
    payload += network_params.nwkUpdateId.serialize()

    status, _ = await app._ezsp.sendBroadcast(
        zigpy.types.BroadcastAddress.ALL_DEVICES, aps_frame, 0x00, 0x01, payload,
    )
    assert status == bellows.types.EmberStatus.SUCCESS

    res = await app._ezsp.setRadioChannel(ch)
    LOGGER.info("Set channel status: %s", res)


async def get_token(app, listener, ieee, cmd, data, service, params={}, event_data={}):
    token = t.uint8_t(data)
    event_data['tokens_info'] = {}
    for token in range(0, 31):
        LOGGER.info(f"Getting {token} token...")
        res = await app._ezsp.getToken(token)
        tkInfo = {"status": res[0], "data": binascii.hexlify(res[1].serialize())}
        event_data['tokens_info'][token] = tkInfo
        LOGGER.info(f"Getting token {token} status: {res[0]}")
        LOGGER.info(f"Getting token {token} data: {res[1]}")
        LOGGER.info(
            (f"Getting token {token} data: " "{binascii.hexlify(res[1].serialize())}")
        )


async def start_mfg(app, listener, ieee, cmd, data, service, params={}, event_data={}):
    LOGGER.info("Starting mfg lib")
    res = await app._ezsp.mfglibStart(True)
    LOGGER.info("starting mfg lib result: %s", res)

    channel = 11
    res = await app._ezsp.mfglibSetChannel(channel)
    LOGGER.info("mfg lib change channel: %s", res)

    res = await app._ezsp.mfglibEnd()
    LOGGER.info("mfg lib change channel: %s", res)


async def get_keys(app, listener, ieee, cmd, data, service, params={}, event_data={}):
    LOGGER.info("getting all keys")
    result = {}
    erase = True if data is not None and data else False
    warnings = []

    for idx in range(0, 192):
        LOGGER.debug("Getting key index %s", idx)
        (status, key_struct) = await app._ezsp.getKeyTableEntry(idx)
        if status == app._ezsp.types.EmberStatus.SUCCESS:
            result[idx] = key_struct
            if key_struct.partnerEUI64 not in app.devices:
                warn = ("Partner %s for key %s is not present" % (key_struct.partnerEUI64, idx))
                warnings.append(warn)
                LOGGER.warning(warn)
                if erase:
                    await app._ezsp.eraseKeyTableEntry(idx)
        elif status == app._ezsp.types.EmberStatus.INDEX_OUT_OF_RANGE:
            break
        else:
            warn = ("No key at %s idx: %s" % (idx, status))
            warnings.append(warn)
            LOGGER.warning(warn)

    event_data['warnings'] = warnings
    event_data['result'] = result
    for idx in result:
        LOGGER.info("EZSP %s key: %s", idx, result[idx])
    _, _, params = await app._ezsp.getNetworkParameters()
    LOGGER.info("Current network: %s", params)
    event_data['network'] = params


async def add_transient_key(app, listener, ieee, cmd, data, service, params={}, event_data={}):
    LOGGER.info("adding well known link key as transient key")
    if ieee is None:
        msg = "No ieee to install transient key for"
        event_data['errors'].append(msg)
        LOGGER.error(msg)

    (status,) = await app._ezsp.addTransientLinkKey(ieee, b"ZigbeeAlliance09")
    LOGGER.debug("Installed key for %s: %s", ieee, status)


async def get_ieee_by_nwk(app, listener, ieee, cmd, data, service, params={}, event_data={}):
    LOGGER.info("Lookup IEEE by nwk")
    nwk = u.str2int(data)
    status, eui64 = await app._ezsp.lookupEui64ByNodeId(nwk)
    LOGGER.debug("nwk: 0x%04x, ieee: %s, status: %s", nwk, eui64, status)
    event_data['nwk'] = nwk
    event_data['ieee'] = repr(eui64)
    event_data['status'] = status


async def get_policy(app, listener, ieee, cmd, data, service, params={}, event_data={}):
    policy = int(data)

    LOGGER.info("Getting EZSP %s policy id", policy)
    status, value = await app._ezsp.getPolicy(policy)
    LOGGER.debug("policy: %s, value: %s", app._ezsp.types.EzspPolicyId(policy), value)
    event_data['policy'] = repr(app._ezsp.types.EzspPolicyId(policy))
    event_data['policy_value'] = repr(value)


async def clear_keys(app, listener, ieee, cmd, data, service, params={}, event_data={}):
    LOGGER.info("Clear key table")
    (status,) = await app._ezsp.clearKeyTable()
    LOGGER.info("Cleared key table: %s", status)


async def get_config_value(app, listener, ieee, cmd, data, service, params={}, event_data={}):
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


async def get_value(app, listener, ieee, cmd, data, service, params={}, event_data={}):
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
    event_data['ezsp_'+value_id.name] = repr(value)


# Legacy implementation
#
# See https://github.com/zigpy/bellows/tree/dev/bellows/cli
#
# Code essentially from https://github.com/zigpy/bellows/blob/dev/bellows/cli/backup.py
#
async def ezsp_backup_legacy(app, listener, ieee, cmd, data, service, params={}, event_data={}):
    if u.get_radiotype(app) != u.RadioType.EZSP:
        msg = "'{}' is only available for BELLOWS/EZSP".format(cmd)
        LOGGER.debug(msg)
        raise Exception(msg)

    # Import stuff we need
    import bellows.types as bt
    from bellows.cli.backup import ATTR_NODE_TYPE, ATTR_NODE_ID, ATTR_NODE_EUI64, ATTR_PAN_ID, ATTR_EXT_PAN_ID, ATTR_RADIO_CHANNEL, ATTR_RADIO_TX_PWR, ATTR_NWK_UPDATE_ID, ATTR_CHANNELS, ATTR_KEY_GLOBAL, ATTR_KEY_NWK, ATTR_KEY_PARTNER, ATTR_KEY_TABLE, _backup_keys
    import os
    import json

    (status, node_type, network) = await app._ezsp.getNetworkParameters()
    assert status == bt.EmberStatus.SUCCESS
    assert node_type == app._ezsp.types.EmberNodeType.COORDINATOR
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
        (ATTR_KEY_GLOBAL, app._ezsp.types.EmberKeyType.TRUST_CENTER_LINK_KEY),
        (ATTR_KEY_NWK, app._ezsp.types.EmberKeyType.CURRENT_NETWORK_KEY),
    ):
        (status, key) = await app._ezsp.getKey(key_type)
        assert status == bt.EmberStatus.SUCCESS
        LOGGER.debug("%s key: %s", key_name, key)
        result[key_name] = key.as_dict()
#
        result[key_name][ATTR_KEY_PARTNER] = str(key.partnerEUI64)

    keys = await _backup_keys(app._ezsp)
    result[ATTR_KEY_TABLE] = keys

    # Store backup information to file

    # Set name with regards to local path
    out_dir = os.path.dirname(__file__) + '/local/'
    if not os.path.isdir(out_dir):
        os.mkdir(out_dir)

    # Ensure that data is an empty string when not set
    if data is None:
        data = ''

    fname = out_dir + 'nwk_backup' + str(data) + '.json'

    f = open(fname, "w")
    f.write(json.dumps(result, indent=4))
    f.close()


async def ezsp_backup(app, listener, ieee, cmd, data, service, params={}, event_data={}):
    if u.get_radiotype(app) != u.RadioType.EZSP:
        msg = "'{}' is only available for BELLOWS/EZSP".format(cmd)
        LOGGER.debug(msg)
        raise Exception(msg)

    # Import stuff we need
    from . import ezsp_backup
    import os
    import json

    result = await ezsp_backup._backup(app._ezsp)

    # Store backup information to file

    # Set name with regards to local path
    out_dir = os.path.dirname(__file__) + '/local/'
    if not os.path.isdir(out_dir):
        os.mkdir(out_dir)

    # Ensure that data is an empty string when not set
    if data is None:
        data = ''

    fname = out_dir + 'nwk_backup' + str(data) + '.json'

    f = open(fname, "w")
    f.write(json.dumps(result, indent=4))
    f.close()
