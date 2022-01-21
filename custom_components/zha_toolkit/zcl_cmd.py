import logging

from . import utils as u

LOGGER = logging.getLogger(__name__)


ERR001_PARAMETERS = "Expecting parameters for 'extra'"
ERR002_DATA_MISSING = "Expecting 'extra' parameter '{}'"
ERR003_PARAMETER_MISSING = "Expecting parameter '{}'"
ERR004_NOT_IN_CLUSTER = ("In cluster 0x%04X not found for '%s', endpoint %s",)
ERR005_NOT_OUT_CLUSTER = ("Out cluster 0x%04X not found for '%s', endpoint %s",)


async def zcl_cmd(app, listener, ieee, cmd, data, service, event_data={}, params={}):
    from zigpy import types as t

    # Verify parameter presence

    extra = service.data.get("extra")
    # LOGGER.info( "Extra '%s'", extra )
    if not isinstance(extra, dict):
        # Fall back to parameters in 'data:' key
        extra = service.data

    if ieee is None:
        msg = ERR003_PARAMETER_MISSING.format("ieee")
        LOGGER.error(msg)
        raise Exception(msg)

    required_options = ["cmd", "cluster", "endpoint"]
    for key in required_options:
        if key not in extra:
            msg = ERR002_DATA_MISSING.format(key)
            LOGGER.error(msg)
            raise Exception(msg)

    # Extract parameters

    # Endpoint to send command to
    ep_id = u.str2int(extra["endpoint"])
    # Cluster to send command to
    cluster_id = u.str2int(extra["cluster"])
    # The command to send
    cmd_id = u.str2int(extra["cmd"])
    # The direction (to in or out cluster)
    dir_int = 0
    if "dir" in extra:
        dir_int = u.str2int(extra["dir"])

    # Get manufacturer
    manf = None
    if "manf" in extra:
        manf = u.str2int(extra["manf"])

    # Get tries
    tries = 1
    if "tries" in extra:
        tries = u.str2int(extra["tries"])

    # Get expect_reply
    expect_reply = True
    if "expect_reply" in extra:
        expect_reply = u.str2int(extra["expect_reply"]) == 0

    cmd_args = []
    if "args" in extra:
        for val in extra["args"]:
            LOGGER.debug("cmd arg %s", val)
            lval = u.str2int(val)
            if isinstance(lval, list):
                # Convert list to List of uint8_t
                lval = t.List[t.uint8_t]([t.uint8_t(i) for i in lval])
                # Convert list to LVList structure
                # lval = t.LVList(lval)
            cmd_args.append(lval)
            LOGGER.debug("cmd converted arg %s", lval)

    # Direction 0 = Client to Server, as in protocol bit
    is_in_cluster = dir_int == 0

    dev = app.get_device(ieee=ieee)

    if ep_id not in dev.endpoints:
        msg = "Endpoint %s not found for '%s'" % (ep_id, repr(ieee))
        LOGGER.error(msg)
        raise Exception(msg)

    endpoint = dev.endpoints[ep_id]

    org_cluster_cmd_defs = dict()

    # Exception caught in the try/catch below to throw after
    #   restoring cluster definitions
    caught_e = None

    try:
        if is_in_cluster:
            if cluster_id not in endpoint.in_clusters:
                msg = ERR004_NOT_IN_CLUSTER.format(cluster_id, repr(ieee), ep_id)
                LOGGER.error(msg)
                raise Exception(msg)
            else:
                cluster = endpoint.in_clusters[cluster_id]

            if (cluster_id == 5) and (cmd_id == 0):
                org_cluster_cmd_defs[0] = cluster.server_commands[0]
                cluster.server_commands[0] = (
                    "add",
                    (
                        t.uint16_t,
                        t.uint8_t,
                        t.uint16_t,
                        t.CharacterString,
                        t.Optional(t.List[t.uint8_t]),
                    ),
                    False,
                )
            await cluster.command(
                cmd_id,
                *cmd_args,
                manufacturer=manf,
                expect_reply=expect_reply,
                tries=tries
            )
        else:
            if cluster_id not in endpoint.out_clusters:
                msg = ERR005_NOT_OUT_CLUSTER.format(cluster_id, repr(ieee), ep_id)
                LOGGER.error(msg)
                raise Exception(msg)
            else:
                cluster = endpoint.out_clusters[cluster_id]

            # Note: client_command not tested
            await cluster.client_command(cmd_id, *cmd_args, manufacturer=manf)
    except Exception as e:
        caught_e = e
    finally:
        # Restore replaced cluster command definitions
        # LOGGER.debug("replaced %s", org_cluster_cmd_defs)
        for key, value in org_cluster_cmd_defs.items():
            if is_in_cluster:
                cluster.server_commands[key] = org_cluster_cmd_defs[key]
            else:
                cluster.client_commands[key] = org_cluster_cmd_defs[key]
        if caught_e is not None:
            raise caught_e

    # Could check cluster.client_command, cluster_server commands
