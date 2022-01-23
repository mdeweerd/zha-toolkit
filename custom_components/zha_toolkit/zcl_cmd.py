import logging

from . import utils as u

LOGGER = logging.getLogger(__name__)


ERR001_PARAMETERS = "Expecting parameters for 'extra'"
ERR002_DATA_MISSING = "Expecting parameter '{}'"
ERR003_PARAMETER_MISSING = "Expecting parameter '{}'"
ERR004_NOT_IN_CLUSTER = "In cluster 0x%04X not found for '%s', endpoint %s"
ERR005_NOT_OUT_CLUSTER = "Out cluster 0x%04X not found for '%s', endpoint %s"


async def zcl_cmd(app, listener, ieee, cmd, data, service, event_data={}, params={}):
    from zigpy import types as t

    # Verify parameter presence

    if ieee is None:
        msg = ERR003_PARAMETER_MISSING.format("ieee")
        LOGGER.error(msg)
        raise Exception(msg)

    dev = app.get_device(ieee=ieee)

    # Decode endpoint
    if params["endpoint_id"] is None or params["endpoint_id"] == "":
        params["endpoint_id"] = u.find_endpoint(dev, params["cluster_id"])

    if params["endpoint_id"] not in dev.endpoints:
        LOGGER.error(
            "Endpoint %s not found for '%s'", params["endpoint_id"], repr(ieee)
        )

    if params["cluster_id"] not in dev.endpoints[params["endpoint_id"]].in_clusters:
        LOGGER.error(
            "Cluster 0x%04X not found for '%s', endpoint %s",
            params["cluster_id"],
            repr(ieee),
            params["endpoint_id"],
        )

    # Extract parameters

    # Endpoint to send command to
    ep_id = params["endpoint_id"]
    # Cluster to send command to
    cluster_id = params["cluster_id"]
    # The command to send
    cmd_id = params["cmd_id"]
    if cmd_id is None:
        raise Exception(ERR003_PARAMETER_MISSING, "cmd")

    # The direction (to in or out cluster)
    dir_int = params["dir"]

    # Get manufacturer
    manf = params["manf"]

    # Get tries
    tries = params["tries"]

    # Get expect_reply
    expect_reply = params["expect_reply"]

    cmd_args = params["args"]

    # Direction 0 = Client to Server, as in protocol bit
    is_in_cluster = dir_int == 0

    if ep_id not in dev.endpoints:
        msg = f"Endpoint {ep_id} not found for '{repr(ieee)}'"
        LOGGER.error(msg)
        raise Exception(msg)

    endpoint = dev.endpoints[ep_id]

    org_cluster_cmd_defs = {}

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
                tries=tries,
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
        for key, _value in org_cluster_cmd_defs.items():
            if is_in_cluster:
                cluster.server_commands[key] = org_cluster_cmd_defs[key]
            else:
                cluster.client_commands[key] = org_cluster_cmd_defs[key]
        if caught_e is not None:
            raise caught_e

    # Could check cluster.client_command, cluster_server commands
