import logging

from zigpy import types as t

from . import utils as u

# from zigpy.zcl import foundation
# import zigpy.zcl as zcl

LOGGER = logging.getLogger(__name__)


async def znp_backup(
    app, listener, ieee, cmd, data, service, params, event_data
):
    """Backup ZNP network information."""

    LOGGER.debug("ZNP_BACKUP")

    if u.get_radiotype(app) != u.RadioType.ZNP:
        msg = f"{cmd} is only for ZNP"
        LOGGER.debug(msg)
        raise ValueError(msg)

    # Import stuff we need
    import json

    from zigpy_znp.tools.network_backup import backup_network

    # Get backup information
    backup_obj = await backup_network(app._znp)

    # Store backup information to file

    # Set name with regards to local path
    out_dir = u.get_local_dir()

    # Ensure that data is an empty string when not set
    if data is None:
        data = ""

    fname = out_dir + "nwk_backup" + str(data) + ".json"

    event_data["backup_file"] = fname

    LOGGER.debug("Writing to %s", fname)
    with open(fname, "w", encoding="utf_8") as f:
        f.write(json.dumps(backup_obj, indent=4))


async def znp_restore(
    app, listener, ieee, cmd, data, service, params, event_data
):
    """Restore ZNP network information."""

    if u.get_radiotype(app) != u.RadioType.ZNP:
        msg = f"'{cmd}' is only available for ZNP"
        LOGGER.debug(msg)
        raise ValueError(msg)

    # Get/set parameters

    # command_data (data):
    #    counter_increment (defaults to 2500)

    counter_increment = u.str2int(data)

    if not isinstance(counter_increment, int):
        counter_increment = 2500

    counter_increment = t.uint32_t(counter_increment)

    from datetime import datetime

    current_datetime = datetime.now().strftime("_%Y%m%d_%H%M%S")

    # Safety: backup current configuration
    await znp_backup(
        app, listener, ieee, cmd, current_datetime, service, params, event_data
    )

    # Import stuff we need for restoring
    import json

    from zigpy_znp.tools.common import validate_backup_json
    from zigpy_znp.tools.network_restore import json_backup_to_zigpy_state

    # Set name with regards to local path
    fname = u.get_local_dir() + "nwk_backup.json"
    LOGGER.info("Restore from '%s'", fname)

    event_data["restore_file"] = fname

    # Read backup file
    with open(fname, encoding="utf_8") as f:
        backup = json.load(f)

    # validate the backup file
    LOGGER.info("Validating backup contents")
    validate_backup_json(backup)
    LOGGER.info("Backup contents validated")

    network_info, node_info = json_backup_to_zigpy_state(backup)

    network_info.network_key.tx_counter += counter_increment

    # Network already formed in HA
    # app._znp.startup(force_form=True)

    # Write back information from backup
    LOGGER.info("Writing to device")
    await app._znp.write_network_info(
        network_info=network_info, node_info=node_info
    )

    # LOGGER.debug("List of attributes/methods in app %s", dir(app))
    LOGGER.debug("List of attributes/methods in znp %s", dir(app._znp))

    # Shutdown znp?
    LOGGER.info(
        "Write done, call pre_shutdown().  Restart the device/HA after this."
    )
    await app._znp.pre_shutdown()
    LOGGER.info("pre_shutdown() Done.")

    # TODO: restart znp, HA?


async def znp_nvram_backup(
    app, listener, ieee, cmd, data, service, params, event_data
):
    """Save ZNP NVRAM to file for backup"""

    if u.get_radiotype(app) != u.RadioType.ZNP:
        msg = f"'{cmd}' is only available for ZNP"
        LOGGER.debug(msg)
        raise ValueError(msg)

    # Store backup information to file
    import json

    from zigpy_znp.tools.nvram_read import nvram_read

    # Set name with regards to local path
    out_dir = u.get_local_dir()

    LOGGER.info("Reading NVRAM from device")
    backup_obj = await nvram_read(app._znp)

    # Ensure that data is an empty string when not set
    if data is None:
        data = ""

    fname = out_dir + "nvram_backup" + str(data) + ".json"

    LOGGER.info("Saving NVRAM to '%s'", fname)
    with open(fname, "w", encoding="utf_8") as f:
        f.write(json.dumps(backup_obj, indent=4))
    LOGGER.info("NVRAM backup saved to '%s'", fname)


async def znp_nvram_restore(
    app, listener, ieee, cmd, data, service, params, event_data
):
    """Restore ZNP NVRAM from file"""

    if u.get_radiotype(app) != u.RadioType.ZNP:
        msg = f"'{cmd}' is only available for ZNP"
        LOGGER.debug(msg)
        raise ValueError(msg)

    # Safety: backup current configuration
    from datetime import datetime

    current_datetime = datetime.now().strftime("_%Y%m%d_%H%M%S")
    await znp_nvram_backup(
        app, listener, ieee, cmd, current_datetime, service, params, event_data
    )

    # Restore NVRAM backup from file
    import json

    from zigpy_znp.tools.nvram_write import nvram_write

    # Set name with regards to local path
    out_dir = u.get_local_dir()

    # Ensure that data is an empty string when not set
    if data is None:
        data = ""

    fname = out_dir + "nvram_backup" + str(data) + ".json"

    LOGGER.info("Restoring NVRAM from '%s'", fname)
    with open(fname, "w", encoding="utf_8") as f:
        nvram_obj = json.load(f)

    await nvram_write(app._znp, nvram_obj)
    LOGGER.info("Restored NVRAM from '%s'", fname)

    # TODO: restart znp, HA?


async def znp_nvram_reset(
    app, listener, ieee, cmd, data, service, params, event_data
):
    """Reset ZNP NVRAM"""

    if u.get_radiotype(app) != u.RadioType.ZNP:
        msg = f"'{cmd}' is only available for ZNP"
        LOGGER.debug(msg)
        raise ValueError(msg)

    from datetime import datetime

    current_datetime = datetime.now().strftime("_%Y%m%d_%H%M%S")

    # Safety: backup current configuration
    await znp_nvram_backup(
        app, listener, ieee, cmd, current_datetime, service, params, event_data
    )

    # Import stuff we need for resetting
    from zigpy_znp.tools.nvram_reset import nvram_reset

    # Write back information from backup
    LOGGER.info("Reset NVRAM")
    await nvram_reset(app._znp)

    # Shutdown znp?
    # LOGGER.info("Call pre_shutdown(). Restart the device/HA after this.")
    # await app._znp.pre_shutdown()
    # LOGGER.info("pre_shutdown() Done.")

    # TODO: restart znp, HA?
