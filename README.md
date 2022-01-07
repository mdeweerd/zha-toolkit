[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration).
<!-- [![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)
![Version](https://img.shields.io/github/v/release/mdeweerd/zha_custom)
![Downloads](https://img.shields.io/github/downloads/release/mdeweerd/zha_custom/total)
-->
# Purpose

Using the Home Assistant 'Services' feature, provide direct control over
low level zigbee commands provided in ZHA or Zigpy
that are not otherwise available or too limited for some use cases.

Can also serve as a framework to do local low level coding (the modules are
reloaded on each call).

Provide access to some higher level commands such as ZNP backup (and restore).

Make it easier to perform one-time operations where (some) Zigbee
knowledge is sufficient and avoiding the need to understand the inner
workings of ZHA or Zigpy (methods, quirks, etc).


# Setup

The component files needs to be added to your `custom_components` directory
either manually or using [HACS](https://hacs.xyz/docs/setup/prerequisites)
([Tutorial](https://codingcyclist.medium.com/how-to-install-any-custom-component-from-github-in-less-than-5-minutes-ad84e6dc56ff)).

Then, the integration is only available in Home Assistant after adding 
the next line to `configuration.yaml`, and restarting Home Assistant.
```yaml
zha_custom:
```

Before restarting, you may also want to enable debug verbosity.  `zha_custom`
isn't verbose when you use it occasionnaly.  As it's a service, there is
no really good way to inform the user about errors other than the log.

Logging will help verify that the commands you send have the desired effect.

Add/update the logger configuration (in the `configuration.yaml` file):
```yaml
logger:
  log:
    custom_components.zha_custom: debug
```


You can also change the log configuration dynamically by calling the
`logger.setlevel` service.
Example that sets the debug level for this `zha_custom` component and for
zigpy.zcl` (which helps to see some information about actual ZCL frames sent).
This method allows you to enable debug logging only for a limited duration :

```yaml
service: logger.set_level
data: 
    custom_components.zha_custom: debug
    zigpy.zcl: debug
```

# Using `zha_custom`

This components provides a single service (`zha_custom.execute`) that
provides several commands (`command` parameter) providing access
to ZHA/Zigbee actions that are not otherwise available.


You can use a service as an action in automations.  So you can send the
commands according to a schedule or other triggers.  For instance, you
could plan a daily backup of your TI-ZNP USB Key configuration.

It will be more common to send a Zigbee command only once: for instance
bind one device to another, set a manufacturer attribute, ... .  
You can perform them using the developer tools.  
The developer tools are handy to test the service first before adding
them to an automation.

Go to Developer Tools > Services in your instance : 
[![Open your Home Assistant instance and show your service developer tools.](https://my.home-assistant.io/badges/developer_services.svg)](https://my.home-assistant.io/redirect/developer_services/).

Choose `zha_custom.execute` as the service.  
Enable Yaml entry.  

There are several examples below for different commands.  You can
copy/paste them to start from.

Not all available commands are documented.  The undocumented ones
were in the original repository.  
Some of these undocumented commands seem to be very specific trials
from the original authors.  
Feel free to propose documentation updates.


# Examples

Examples are work in progress and may not be functionnal.

For sleepy devices (on a battery) you may need to wake them up
just after sending the command so that they can receive it.

The 'ieee' address can be the IEEE address, the short network address
(0x1203 for instance), or the entity name (example: "light.tz3000_odygigth_ts0505a_12c90efe_level_light_color_on_off").  Be aware that the network address can change over
time but it is shorter to enter if you know it.


## `scan_device`: Scan a device/Read all attribute values

This operation will get all values for the attributes discovered
on the device.

The result of the scan is written to the `scan` directory located
in the configuration directory of Home Assistant (`config/scan/*_result.txt`).


```yaml
service: zha_custom.execute
data:
  ieee: 00:12:4b:00:22:08:ed:1a
  command: scan_device
```

Scan using the entity name:

```yaml
service: zha_custom.execute
data:
  command: scan_device
  ieee: light.tz3000_odygigth_ts0505a_12c90efe_level_light_color_on_off
```

## `zdo_scan_now`: Do a topology scan

Runs `topology.scan()`. 

```yaml
service: zha_custom.execute
data:
  command: zdo_scan_now
```yaml

## `bind_ieee`: Bind matching cluster to another device

Binds all matching clusters (within the scope of the integrated list)

```yaml
service: zha_custom.execute
data:
  ieee: 00:15:8d:00:04:7b:83:69
  command: bind_ieee
  command_data: 00:12:4b:00:22:08:ed:1a

```

## `handle_join`: Handle join - interrogate device

```yaml
service: zha_custom.execute
data:
  ieee: 00:12:4b:00:22:08:ed:1a
  command: handle_join
  command_data: 0x604e

```

## `attr_write`: Write(/Read) an attribute value

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


## `conf_report`: Configure reporting

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

## `zcl_cmd`: Send a Cluster command

Allows you to send a cluster command.
Also accepts command arguments.


```yaml
service: zha_custom.execute
data:
  # Device IEEE address - mandatory
  ieee: 5c:02:72:ff:fe:92:c2:5d
  # Serivce command - mandatory
  command: zcl_cmd
  extra:
    # Command id - mandatory
    cmd: 0
    # Cluster id - mandatory
    cluster: 1006
    # Endpoitn - mandatory
    endpoint: 111
    # Optional: direction (0=to in_cluster (default), 1=to out_cluster),
    dir: 0
    # Optional: expect_reply  (default=true - false when 0 or 'false')
    expect_reply: true 
    # Optional: manf - manufacturer - default : None
    manf: 0x0000
    # Optional: tries - default : 1
    tries: 1
    # Optional (only add when the command requires it): arguments (default=empty)
    args: [ 1, 3, [ 1, 2, 3] ] 

```


### `zcl_cmd` Example: Send `on` command to an OnOff Cluster.

```yaml
service: zha_custom.execute
data:
  ieee: 5c:02:72:ff:fe:92:c2:5d
  command: zcl_cmd
  extra:
    cmd: 1
    cluster: 6
    endpoint: 11
    # Optional: direction (0=to in_cluster)
```


### `zcl_cmd` Example: Send `off` command to an OnOff Cluster:

```yaml
service: zha_custom.execute
data:
  ieee: 5c:02:72:ff:fe:92:c2:5d
  command: zcl_cmd
  extra:
    cmd: 0
    cluster: 6
    endpoint: 11
```

### `zcl_cmd` Example: "Store Scene"

```yaml
service: zha_custom.execute
data:
  ieee: 5c:02:72:ff:fe:92:c2:5d
  command: zcl_cmd
  extra:
    cmd: 4
    cluster: 5
    endpoint: 11
    args: [ 2, 5 ]
```

### `zcl_cmd` Example: "Recall Scene"
```yaml
service: zha_custom.execute
data:
  ieee: 5c:02:72:ff:fe:92:c2:5d
  command: zcl_cmd
  extra:
    cmd: 5
    cluster: 5
    endpoint: 11
    args: [ 2, 5 ]
```

Results in (sniffed):
```raw
ZigBee Cluster Library Frame
    Frame Control Field: Cluster-specific (0x01)
        .... ..01 = Frame Type: Cluster-specific (0x1)
        .... .0.. = Manufacturer Specific: False
        .... 0... = Direction: Client to Server
        ...0 .... = Disable Default Response: False
    Sequence Number: 94
    Command: Recall Scene (0x05)
    Payload
        Group ID: 0x0002
        Scene ID: 0x05
```

### `zcl_cmd` Example: "Add Scene"

This example shows that you can provide a list of bytes for an argument:

```yaml
service: zha_custom.execute
data:
  ieee: 5c:02:72:ff:fe:92:c2:5d
  command: zcl_cmd
  extra:
    cmd: 0
    cluster: 5
    endpoint: 11
    args:
      - 2
      - 5
      - 2
      - "Final Example"
      # Two bytes of cluster Id (LSB first), length, attribute value bytes
      #   repeat as needed (inside the list!)
      - [ 0x06, 0x00, 1, 1 ]
```

sniffed as:
```raw
ZigBee Cluster Library Frame
    Frame Control Field: Cluster-specific (0x01)
        .... ..01 = Frame Type: Cluster-specific (0x1)
        .... .0.. = Manufacturer Specific: False
        .... 0... = Direction: Client to Server
        ...0 .... = Disable Default Response: False
    Sequence Number: 76
    Command: Add Scene (0x00)
    Payload, String: Final Example
        Group ID: 0x0002
        Scene ID: 0x05
        Transition Time: 2 seconds
        Length: 13
        String: Final Example
        Extension Set: 06000101
```


## `znp_nvram_backup`: Backup ZNP NVRAM data

The output is written to the customisation directory as `local/nvram_backup.json`
when `command_data` is empty or not provided.  When `command_data` is provided,
it is added just after nvram_backup.

Note: currently under test.


```yaml
service: zha_custom.execute
data:
  command: znp_nvram_backup
  # Optional command_data, string added to the basename.
  # With this example the backup is written to `nwk_backup_20220105.json`
  command_data: _20220105
```

## `znp_nvram_restore`: Restore ZNP NVRAM data

Will restore ZNP NVRAM data from `local/nvram_backup.json` where `local`
is a directory in the `zha_custom` directory.

Note: currently under test.

For safety, a backup is made of the current network before restoring
`local/nvram_backup.json`.  The name of that backup is according to the format
`local/nvram_backup_YYmmDD_HHMMSS.json`.

```yaml
service: zha_custom.execute
data:
  command: znp_nvram_restore
```


## `znp_nvram_reset`: Reset ZNP NVRAM data

Will reset ZNP NVRAM data from `local/nvram_backup.json` where `local`
is a directory in the `zha_custom` directory.

Note: currently under test.

For safety, a backup is made of the current network before restoring
`local/nvram_backup.json`.  The name of that backup is according to the format
`local/nvram_backup_YYmmDD_HHMMSS.json`.


```yaml
service: zha_custom.execute
data:
  command: znp_nvram_reset
```


## `znp_backup`: Backup ZNP network data 

Used to transfer to another ZNP key later, backup or simply get network key
and other info.

The output is written to the customisation directory as `local/nwk_backup.json`
when `command_data` is empty or not provided.  When `command_data` is provided,
it is added just after nwk_backup.


The name of that backup is according to the format

```yaml
service: zha_custom.execute
data:
  command: znp_backup
  # Optional command_data, string added to the basename.
  # With this example the backup is written to `nwk_backup_20220105.json`
  command_data: _20220105
```

## `znp_restore`: Restore ZNP network data

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

This project was forked from [Adminiguaga/zha_custom](https://github.com/Adminiuga/zha_custom)
where the "hard tricks" for providing services and accessing ZHA functions were
implemented/demonstrated.  The original codeowners were "[dmulcahey](https://github.com/dmulcahey)"
and "[Adminiuga](https://github.com/adminiuga)".

The initial purpose of this fork was mainly to add custom attribute writes,
custom reporting and more binding possibilities.

The structure was then updated to be compliant with HACS integration so that
the component can be easily added to a Home Assistant setup.

# License

I set the License the same as Home Assistant that has the ZHA component.
The original zha_custom repository does not mention a license.

# Contributing 

## Adding commands/documentation

Feel free to propose documentation of the available commands (not all are documented
above) or propose new commands.

To add a new command, one has to add the `command_handler` to the `__init__.py`
file and the actual command itself to an existing module or a new module if that
is appropriate.
Also add a short description of the command in this `README.md` .


Example of addition to `__init__.py`:

```python
def command_handler_znp_backup(*args, **kwargs):
    """ Backup ZNP network information. """
    from . import znp

    importlib.reload(znp)

    return znp.znp_backup(*args, **kwargs)
```

Anything after `command_handler_` is used to match the `command` parameter
to the service - simply adding a function with such a name "adds" the
 corresponding command.

The `reload` in the code above allows you to change the contents of the
module and test it without having to restart Home Assistant.

The code above imports and reloads `znp.py` and then calls `znp_backup`
in that module.

All methods take the same parameters.  'args' and 'kwargs` do some python
magic to ppropagate a variable number of fixed and named parameters.  But 
in the end the method signature has to look like this:

```python
async def znp_backup(app, listener, ieee, cmd, data, service):
    """ Backup ZNP network information. """

```

Where `app` is the `zigpy` instance and `listener` is the gateway instance.
`ieee`, `cmd` and `data` correspond to the parameters provided to the service.  
You can examine some of the existing code how you can use them.  
Possibly `data` could be more than a string, but that has not been validated for now.

Then you have to import the modules you require in the function - or
add/enable them as imports at the module level.

You can also run `flake8` on your files to find some common basic errors
and provide some code styling consistency.

As far as ZHA and zigpy are concerned, you can find the code for the
ZHA integration at
https://github.com/home-assistant/core/tree/dev/homeassistant/components/zha ,
and the `zigpy` repositories are under https://github.com/zigpy .
