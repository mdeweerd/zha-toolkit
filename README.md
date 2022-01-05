[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration).
<!-- [![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)
![Version](https://img.shields.io/github/v/release/mdeweerd/zha_custom)
![Downloads](https://img.shields.io/github/downloads/release/mdeweerd/zha_custom/total)
-->
# Setup

This component needs to be added to your custom_components directory either manually or using HACS.


The component is only available in Home Assistant after adding 
the next line to `configuration.yaml`, and restarting Home Assistant.
```yaml
zha_custom:
```

Before restarting, you may also want to enable debug verbosity.
This will help verify that the commands you send have the desired effect.

Add/update the logger configuration (in the `configuration.yaml` file):
```yaml
logger:
  log:
    custom_components.zha_custom: debug
```

# Use

This components provides a single service (`zha_custom.execute`) that
provides several command (`command` parameter) providing access
to several ZHA/Zigbee actions that are not otherwise available.


You can use a service as an action in automations, but most actions are
done only once and you can perform them using the developer tools.

If you use HASS.os the following direct link may work:
https://homeassistant.local:8123/developer-tools/service .  
If not, find the developer tools in the menu and go to Services.

Choose `zha_custom.execute` as the service.  
Enable Yaml entry.  

There are several examples below for different commands.  

Not all commands are documented, some seem to be very specific trials
from the original authors.  


# Examples

Examples are work in progress and may not be functionnal.

For sleepy devices (on a battery) you may need to wake them up
just after sending the command so that they can receive it.


## Scan a device

The result of the scan is written to the `scan` directory located
in the configuration directory of Home Assistant.

```yaml
service: zha_custom.execute
data:
  ieee: 00:12:4b:00:22:08:ed:1a
  command: scan_device
```

## Bind matching cluster to another device

Binds all matching clusters (within the scope of the integrated list)

```yaml
service: zha_custom.execute
data:
  ieee: 00:15:8d:00:04:7b:83:69
  command: bind_ieee
  command_data: 00:12:4b:00:22:08:ed:1a

```

## Handle join - interrogate device

```yaml
service: zha_custom.execute
data:
  ieee: 00:12:4b:00:22:08:ed:1a
  command: handle_join
  command_data: 0x604e

```

## Write(/Read) an attribute value

Write an attribute value to any endpoint/cluster/attribute.

You can provide the numerical value of the attribute id,
or the internal zigpy name (string).

```yaml
service: zha_custom.execute
data:
  ieee: 5c:02:72:ff:fe:92:c2:5d
  command: attr_write
  # Data: Endpoint, Cluster ID, Attribute Id, Attribute Type, Attribute Value
  command_data: 11,0x0006,0x0000,0x10,1
```


## Configure reporting

Set the minimum and maximum delay between two reports and
set the level of change required to report a value (before the maximum
delay is expired).

This example configures Temperature reporting on a SonOff SNZB-02 (eWeLink/TH01).
Note that you (may) need to press the button on the thermometer just after
requesting the command (it's a sleepy device and does not wake up often).

After succeeding the configuration, the minimum delay was actually 20s
which is likely the measurement period itself.
The changes were reported when they exceeded 0.10 degrees C.

```yaml
service: zha_custom.execute
data:
  ieee: 00:12:4b:00:23:b3:da:a5
  command: conf_report
  command_data: 1,0x0402,0x0000,5,300,10
```


## Backup ZNP network data 

Used to transfer to another ZNP key later, backup or simply get network key and other info.

The output is written to the customisation directory as `local/nwk_backup.json` when `command_data` is empty or not provided.  When `command_data` is provided, it is added just after nwk_backup.


The name of that backup is according to the format

```yaml
service: zha_custom.execute
data:
  command: znp_backup
  # Optional command_data, string added to the basename.
  # With this example the backup is written to `nwk_backup_20220105.json`
  command_data: _20220105
```

## Restore ZNP network data

Will restore network data from `local/nwk_backup.json` where `local`
is a directory in the `zha_custom` directory.

Note: currently under test.

For safety, a backup is made of the current network before restoring
`local/nwk_backup.json`.  The name of that backup is according to the format
`local/nwk_backup_YYmmDD_HHMMSS.json`.


A typical use for this is when you migrate from one key to another.

The procedure should be:
1. Backup using the `znp_backup` command in the `zha_custom` service.
   Verify that the `nwk_backup.json` file is generated in the `local`
   directory.
2. Remove the original key from your system.
   Insert the new key.
3. Restart Home Assistant.
4. Restore using the `znp_restore` command.
5. Check the logs.
6. Restart HA.
7. Check that everything is ok.


```yaml
service: zha_custom.execute
data:
  command: znp_restore
  # Optional:
  #  command_data = Counter_increment (for tx).
  #                 defaults to 2500
  command_data: 2500
```


# Credits/Motivation

This project was forked from [Adminiguaga/zha_custom](https://github.com/Adminiuga/zha_custom) where the "hard tricks" for providing services and accessing ZHA functions were implemented/demonstrated.  The original codeowners were "dmulcahey" and "adminiuga".

The initial purpose of this fork was mainly to add custom attribute writes, custom reporting and more binding possibilities.

The structure was then updated to be compliant with HACS integration so that the component can be easily added to a Home Assistant setup.

# License

I set the License the same as Home Assistant that has the ZHA component.  The original zha_custom repository does not mention a license.

# Contributing 

## Adding commands/documentation

Feel free to propose documentation of the available commands (not all are documented above) or propose new commands.

To add a new command, one has to add the `command_handler` to the `__init__.py` file and the actual command itself to an existing module or a new module if that is appropriate.
Also add a short description of the command in this `README.md` .


Example of addition to `__init__.py`:

```python
def command_handler_znp_backup(*args, **kwargs):
    """ Backup ZNP network information. """
    from . import znp

    importlib.reload(znp)

    return znp.znp_backup(*args, **kwargs)
```

Anything after `command_handler_` is used to match the `command` parameter to the service - simply adding a function with such a name "adds" the corresponding command.

The `reload` in the code above allows you to change the contents of the module and test it without having to restart Home Assistant.

The code above imports and reloads `znp.py` and then calls `znp_backup` in that module.

All methods take the same parameters.  'args' and 'kwargs` do some python magics to ppropagate a variable number of fixed and named parameters.  But in the end the method signature has to look like this:

```python
async def znp_backup(app, listener, ieee, cmd, data, service):
    """ Backup ZNP network information. """

```

Where `app` is the `zigpy` instance and `listener` is the gateway instance.
`ieee`, `cmd` and `data` correspond to the parameters provided to the service.  
You can examine some of the existing code how you can use them.  
Possibly `data` could be more than a string, but that has not been validated for now.

Then you have to import the modules you require in the function - or add/enable them as imports at the module level.

You can also run `flake8` on your files to find some common basic errors and provide some code styling consistency.

As far as ZHA and zigpy are concerned, you can find the code for the ZHA integration at https://github.com/home-assistant/core/tree/dev/homeassistant/components/zha , and the `zigpy` repositories are under https://github.com/zigpy .

