import logging

# from zigpy import types as t
# from zigpy.zcl import foundation
# import zigpy.zcl as zcl

LOGGER = logging.getLogger(__name__)


async def znp_backup(app, listener, ieee, cmd, data, service):
    """ Backup ZNP network information. """

    # Import stuff we need
    from zigpy_znp.tools.network_backup import backup_network as backup_network
    from os import path
    import json

    # Get backup information
    backup_obj = await backup_network(app._znp)

    # Store backup information to file

    # Set name with regards to local path
    fname = path.dirname(__file__) + '/local/nwk_backup.json'
    f = open(fname, "w")
    f.write(json.dumps(backup_obj, indent=4))
    f.close()
