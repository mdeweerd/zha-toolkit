import logging
from typing import Any

from . import utils as u
from .params import INTERNAL_PARAMS as p
from .params import USER_PARAMS as P

LOGGER = logging.getLogger(__name__)


ERR003_PARAMETER_MISSING = "Expecting parameter '{}'"
ERR004_NOT_IN_CLUSTER = "In cluster 0x%04X not found for '%s', endpoint %s"
ERR005_NOT_OUT_CLUSTER = "Out cluster 0x%04X not found for '%s', endpoint %s"


async def zcl_cmd(app, listener, ieee, cmd, data, service, params, event_data):
    from zigpy import types as t
    from zigpy.zcl import foundation

    # Verify parameter presence

    if ieee is None:
        msg = ERR003_PARAMETER_MISSING.format("ieee")
        LOGGER.error(msg)
        raise ValueError(msg)

    dev = await u.get_device(app, listener, ieee)
    # The next line will also update the endpoint if it is not set
    cluster = u.get_cluster_from_params(dev, params, event_data)

    # Extract parameters

    # Endpoint to send command to
    ep_id = params[p.EP_ID]
    # Cluster to send command to
    cluster_id = params[p.CLUSTER_ID]
    # The command to send
    cmd_id = params[p.CMD_ID]
    if cmd_id is None:
        raise ValueError(ERR003_PARAMETER_MISSING, P.CMD)

    # The direction (to in or out cluster)
    dir_int = params[p.DIR]

    # Get manufacturer
    manf = params[p.MANF]

    # Get tries
    tries = params[p.TRIES]

    # Get expect_reply
    expect_reply = params[p.EXPECT_REPLY]

    cmd_args = params[p.ARGS]
    kw_args = params[p.KWARGS]

    # Direction 0 = Client to Server, as in protocol bit
    is_in_cluster = dir_int == 0

    if ep_id not in dev.endpoints:
        msg = f"Endpoint {ep_id} not found for '{repr(ieee)}'"
        LOGGER.error(msg)
        raise ValueError(msg)

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
                raise ValueError(msg)

            # Cluster is found
            cluster = endpoint.in_clusters[cluster_id]

            # Change command specification ourselves ...

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
            elif cmd_id not in cluster.server_commands:
                cmd_schema: list[Any] = []

                if cmd_args is not None:
                    cmd_schema = [t.uint8_t] * len(cmd_args)

                cmd_def = foundation.ZCLCommandDef(
                    name=f"zha_toolkit_dummy_cmd{cmd_id}",
                    id=cmd_id,
                    schema=cmd_schema,
                    direction=foundation.Direction.Client_to_Server,
                    is_manufacturer_specific=(manf is not None),
                )

                org_cluster_cmd_defs[cmd_id] = None
                cluster.server_commands[cmd_id] = cmd_def

            event_data["cmd_reply"] = await u.retry_wrapper(
                cluster.command,
                cmd_id,
                *cmd_args,
                manufacturer=manf,
                expect_reply=expect_reply,
                tries=tries,
                **kw_args,
            )
        else:
            if cluster_id not in endpoint.out_clusters:
                msg = ERR005_NOT_OUT_CLUSTER.format(
                    cluster_id, repr(ieee), ep_id
                )
                LOGGER.error(msg)
                raise ValueError(msg)

            # Found cluster
            cluster = endpoint.out_clusters[cluster_id]

            # Note: client_command not tested
            event_data["cmd_reply"] = await cluster.client_command(
                cmd_id, *cmd_args, manufacturer=manf, **kw_args
            )
    except Exception as e:
        caught_e = e
    finally:
        # Restore replaced cluster command definitions
        # LOGGER.debug("replaced %s", org_cluster_cmd_defs)
        for key, cmd_def in org_cluster_cmd_defs.items():
            if is_in_cluster:
                if cmd_def is not None:
                    cluster.server_commands[key] = cmd_def
                else:
                    del cluster.server_commands[key]

            else:
                if cmd_def is not None:
                    cluster.client_commands[key] = cmd_def
                else:
                    del cluster.client_commands[key]
        if caught_e is not None:
            raise caught_e

    # Could check cluster.client_command, cluster_server commands
