import logging

from zigpy.zcl import foundation
from . import utils as u

LOGGER = logging.getLogger(__name__)


ERRMSG_PARAMETERS_001 = "Expecting parameters for 'extra'"
ERRMSG_DATA_MISSING_002 = "Expecting 'extra' parameter '{}'"
ERRMSG_PARAMETER_MISSING_003 = "Expecting parameter '{}'"
ERRMSG_NOT_IN_CLUSTER_004 = "In cluster 0x%04X not found for '%s', endpoint %s",
ERRMSG_NOT_OUT_CLUSTER_004 = "Out cluster 0x%04X not found for '%s', endpoint %s",

async def zcl_cmd(app, listener, ieee, cmd, data, service):
    from zigpy import types as t

    # Verify parameter presence

    extra=service.data.get('extra')
    LOGGER.error( "Extra '%s'", extra ) 
    if not isinstance(extra, dict):
        LOGGER.error( "Type '%s'", type(extra) ) 
        raise Exception(ERRMSG_PARAMETERS_001)

    if ieee is None:
        msg=ERRMSG_PARAMETER_MISSING_003.format('ieee')
        LOGGER.error(msg)
        raise Exception(msg)

    required_options=[ 'cmd', 'cluster', 'endpoint' ]
    for key in required_options:
      if not key in extra:
        msg=ERRMSG_DATA_MISSING_002.format(key)
        LOGGER.error(msg)
        raise Exception(msg)

    # Extract parameters

    # Endpoint to send command to
    ep_id = u.str2int(extra['endpoint'])
    # Cluster to send command to
    cluster_id = u.str2int(extra['cluster'])
    # The command to send
    cmd_id     = u.str2int(extra['cmd'])
    # The direction (to in or out cluster)
    dir_int=0
    if 'dir' in extra:
        dir_int = u.str2int(extra['dir'])

    # Get manufacturer
    manf=None
    if 'manf' in extra:
        manf = u.str2int(extra['manf'])

    # Get tries
    tries = 1
    if 'tries' in extra:
        tries = u.str2int(extra['tries'])

    # Get expect_reply
    expect_reply = True
    if 'expect_reply' in extra:
        expect_reply = u.str2int(extra['tries'])==0

    cmd_args=[]
    if 'args' in extra:
        for val in extra['args']:
            LOGGER.debug("cmd arg %s",val)
            cmd_args.append(u.str2int(val))

    # Direction 0 = Client to Server, as in protocol bit
    is_in_cluster = (dir_int == 0)

    dev = app.get_device(ieee=ieee)

    if ep_id not in dev.endpoints:
        msg="Endpoint %s not found for '%s'".format(ep_id, repr(ieee))
        LOGGER.error(msg)
        raise Exception(msg)

    endpoint=dev.endpoints[ep_id]


    if is_in_cluster:
        if not cluster_id in endpoint.in_clusters:
            msg=ERRMSG_NOT_IN_CLUSTER_004.format(
                      cluster_id, repr(ieee), ep_id)
            LOGGER.error(msg)
            raise Exception(msg)
        else:
            cluster = endpoint.in_clusters[cluster_id]
    else:
        if not cluster_id in endpoint.out_clusters:
            msg=ERRMSG_NOT_OUT_CLUSTER_005.format(
                      cluster_id, repr(ieee), ep_id)
            LOGGER.error(msg)
            raise Exception(msg)
        else:
            cluster = endpoint.out_clusters[cluster_id]

    # Could check cluster.client_command, cluster_server commands 

    await cluster.command(
            cmd_id,
            *cmd_args,
            #command_id=cmd_id,
            manufacturer=manf,
            expect_reply=expect_reply,
            tries = tries
    )
 
