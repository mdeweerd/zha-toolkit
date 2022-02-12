import inspect
import logging

from . import utils as u
from .params import INTERNAL_PARAMS as p
from .params import USER_PARAMS as P

LOGGER = logging.getLogger(__name__)


ERR003_PARAMETER_MISSING = "Expecting parameter '{}'"
ERR004_NOT_IN_CLUSTER = "In cluster 0x%04X not found for '%s', endpoint %s"
ERR005_NOT_OUT_CLUSTER = "Out cluster 0x%04X not found for '%s', endpoint %s"


async def zcl_cmd(app, listener, ieee, cmd, data, service, params, event_data):
    from zigpy import types as t

    # Verify parameter presence

    if ieee is None:
        msg = ERR003_PARAMETER_MISSING.format("ieee")
        LOGGER.error(msg)
        raise Exception(msg)

    dev = app.get_device(ieee=ieee)

    # Decode endpoint
    if params[p.EP_ID] is None or params[p.EP_ID] == "":
        params[p.EP_ID] = u.find_endpoint(dev, params[p.CLUSTER_ID])

    if params[p.EP_ID] not in dev.endpoints:
        LOGGER.error(
            "Endpoint %s not found for '%s'", params[p.EP_ID], repr(ieee)
        )

    if params[p.CLUSTER_ID] not in dev.endpoints[params[p.EP_ID]].in_clusters:
        LOGGER.error(
            "Cluster 0x%04X not found for '%s', endpoint %s",
            params[p.CLUSTER_ID],
            repr(ieee),
            params[p.EP_ID],
        )

    # Extract parameters

    # Endpoint to send command to
    ep_id = params[p.EP_ID]
    # Cluster to send command to
    cluster_id = params[p.CLUSTER_ID]
    # The command to send
    cmd_id = params[p.CMD_ID]
    if cmd_id is None:
        raise Exception(ERR003_PARAMETER_MISSING, P.CMD)

    # The direction (to in or out cluster)
    dir_int = params[p.DIR]

    # Get manufacturer
    manf = params[p.MANF]

    # Get tries
    tries = params[p.TRIES]

    # Get expect_reply
    expect_reply = params[p.EXPECT_REPLY]

    cmd_args = params[p.ARGS]

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
                msg = ERR004_NOT_IN_CLUSTER.format(
                    cluster_id, repr(ieee), ep_id
                )
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
            if "tries" in inspect.getfullargspec(cluster.command)[0]:
                await cluster.command(
                    cmd_id,
                    *cmd_args,
                    manufacturer=manf,
                    expect_reply=expect_reply,
                    tries=tries,
                )
            else:
                await cluster.command(
                    cmd_id,
                    *cmd_args,
                    manufacturer=manf,
                    expect_reply=expect_reply,
                )
        else:
            if cluster_id not in endpoint.out_clusters:
                msg = ERR005_NOT_OUT_CLUSTER.format(
                    cluster_id, repr(ieee), ep_id
                )
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
