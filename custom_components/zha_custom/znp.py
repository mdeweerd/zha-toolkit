import logging

from zigpy import types as t

from . import utils as u
# from zigpy.zcl import foundation
# import zigpy.zcl as zcl

LOGGER = logging.getLogger(__name__)


async def znp_backup(app, listener, ieee, cmd, data, service):
    """ Backup ZNP network information. """

    if u.get_radiotype(app) != u.RadioType.ZNP:
        msg = "'%s' is only available for ZNP".format(cmd)
        LOGGER.debug(msg)
        raise Exception(msg) 

    # Import stuff we need
    from zigpy_znp.tools.network_backup import backup_network as backup_network
    import os
    import json

    # Get backup information
    backup_obj = await backup_network(app._znp)

    # Store backup information to file

    # Set name with regards to local path
    out_dir = os.path.dirname(__file__) + '/local/'
    if not os.path.isdir(out_dir):
        os.mkdir(out_dir)


    # Ensure that data is an empty string when not set
    if data is None:
        data=''

    fname = out_dir + 'nwk_backup' + str(data) + '.json'
       
    f = open(fname, "w")
    f.write(json.dumps(backup_obj, indent=4))
    f.close()

async def znp_restore(app, listener, ieee, cmd, data, service):
    """ Restore ZNP network information. """

    if u.get_radiotype(app) != u.RadioType.ZNP:
        msg = "'%s' is only available for ZNP".format(cmd)
        LOGGER.debug(msg)
        raise Exception(msg) 

    # Get/set parameters

    # command_data (data):
    #    counter_increment (defaults to 2500)

    counter_increment = u.str2int(data)

    if type(counter_increment) != int:
        counter_increment = 2500

    counter_increment = t.uint32_t(counter_increment)


    from datetime import datetime
    current_datetime=datetime.now().strftime('_%Y%m%d_%H%M%S')

    # Safety: backup current configuration
    await znp_backup(app, listener, ieee, cmd, current_datetime, service) 

    # Import stuff we need for restoring
    from zigpy_znp.tools.network_restore import restore_network, json_backup_to_zigpy_state
    from zigpy_znp.tools.common import validate_backup_json
    from os import path
    import json


    # Set name with regards to local path
    fname = path.dirname(__file__) + '/local/nwk_backup.json'

    # Read backup file
    f = open(fname, "r")
    backup = json.load(f)
    f.close()

    # validate the backup file
    validate_backup_json(backup)

    network_info, node_info = json_backup_to_zigpy_state(backup)

    network_info.network_key.tx_counter+=counter_increment

    # Network already formed in HA
    # app._znp.startup(force_form=True) 

    # Write back information from backup
    app._znp.write_network_info(network_info=network_info, node_info=node_info) 

    # Shutdown znp?
    await app._znp.pre_shutdown()

    # TODO: restart znp, HA?
    
