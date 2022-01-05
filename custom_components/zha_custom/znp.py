import logging

from zigpy import types as t
# from zigpy.zcl import foundation
# import zigpy.zcl as zcl

LOGGER = logging.getLogger(__name__)


# Convert string to int if possible or return original string
#  (Returning the original string is usefull for named attributes)
def str2int(s):
    if not type(s) == str:
        return s
    elif s.startswith("0x") or s.startswith("0X"):
        return int(s, 16)
    elif s.startswith("0") and s.isnumeric():
        return int(s, 8)
    elif s.startswith("b") and s[1:].isnumeric():
        return int(s[1:], 2)
    elif s.isnumeric():
        return int(s)
    else:
        return s




async def znp_backup(app, listener, ieee, cmd, data, service):
    """ Backup ZNP network information. """

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
  
    # Get/set parameters

    # command_data (data):
    #    counter_increment (defaults to 2500)

    counter_increment = str2int(data)

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
    
