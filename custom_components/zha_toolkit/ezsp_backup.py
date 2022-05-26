# Code from
# https://raw.githubusercontent.com/puddly/bellows/puddly/open-coordinator-backup/bellows/cli/backup.py
# slightly adapted
#

import datetime
import logging

import bellows
import bellows.types as t

LOGGER = logging.getLogger(__name__)


EMBER_TABLE_ENTRY_UNUSED_NODE_ID = 0xFFFF
EMBER_UNKNOWN_NODE_ID = 0xFFFD
EMBER_DISCOVERY_ACTIVE_NODE_ID = 0xFFFC


async def _backup(ezsp):
    # (status,) = await ezsp.networkInit()
    # assert status == t.EmberStatus.SUCCESS

    (status, node_type, network) = await ezsp.getNetworkParameters()
    assert status == t.EmberStatus.SUCCESS
    assert node_type == ezsp.types.EmberNodeType.COORDINATOR

    (ieee,) = await ezsp.getEui64()

    (status, nwk_key) = await ezsp.getKey(
        ezsp.types.EmberKeyType.CURRENT_NETWORK_KEY
    )
    assert status == t.EmberStatus.SUCCESS

    (status, security_level) = await ezsp.getConfigurationValue(
        ezsp.types.EzspConfigId.CONFIG_SECURITY_LEVEL
    )
    assert status == t.EmberStatus.SUCCESS

    (status, _tclk) = await ezsp.getKey(
        ezsp.types.EmberKeyType.TRUST_CENTER_LINK_KEY
    )
    assert status == t.EmberStatus.SUCCESS

    addresses = {}

    for idx in range(0, 255 + 1):
        (nwk,) = await ezsp.getAddressTableRemoteNodeId(idx)
        (eui64,) = await ezsp.getAddressTableRemoteEui64(idx)

        if nwk == EMBER_TABLE_ENTRY_UNUSED_NODE_ID:
            continue
        if nwk == EMBER_UNKNOWN_NODE_ID:
            LOGGER.warning("NWK address for %s is unknown!", eui64)
            continue
        if nwk == EMBER_DISCOVERY_ACTIVE_NODE_ID:
            LOGGER.warning(
                "NWK address discovery for %s is currently ongoing", eui64
            )
            continue

        LOGGER.debug("NWK for %s is %s", eui64, nwk)
        addresses[eui64] = nwk

    keys = {}

    for idx in range(0, 192):
        (status, key_struct) = await ezsp.getKeyTableEntry(idx)
        LOGGER.debug(
            "Got key at index %s status: %s key_struct: %s",
            idx,
            status,
            key_struct,
        )

        if status == t.EmberStatus.SUCCESS:
            keys[key_struct.partnerEUI64] = key_struct
        elif status == t.EmberStatus.INDEX_OUT_OF_RANGE:
            break

    now = datetime.datetime.now().astimezone()
    result = {
        "metadata": {
            "version": 1,
            "format": "zigpy/open-coordinator-backup",
            "source": f"bellows@{bellows.__version__}",
            "internal": {
                "creation_time": now.isoformat(timespec="seconds"),
            },
        },
        "coordinator_ieee": ieee.serialize()[::-1].hex(),
        "pan_id": network.panId.serialize()[::-1].hex(),
        "extended_pan_id": network.extendedPanId.serialize()[::-1].hex(),
        "nwk_update_id": network.nwkUpdateId,
        "security_level": security_level,
        "channel": network.radioChannel,
        "channel_mask": list(network.channels),
        "network_key": {
            "key": nwk_key.key.serialize().hex(),
            "sequence_number": nwk_key.sequenceNumber,
            "frame_counter": nwk_key.outgoingFrameCounter,
        },
        "devices": [
            {
                "ieee_address": ieee.serialize()[::-1].hex(),
                "link_key": {
                    "key": key.key.serialize().hex(),
                    "rx_counter": key.incomingFrameCounter,
                    "tx_counter": key.outgoingFrameCounter,
                },
                "nwk_address": addresses[ieee].serialize()[::-1].hex(),
            }
            for ieee, key in keys.items()
            if ieee in addresses
        ],
    }
    return result
