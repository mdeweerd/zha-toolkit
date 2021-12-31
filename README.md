# Setup

This component needs to be added to your custom_components directory either manually or using [![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration).


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

You can use a service as an action in automations, but most actions are
done only once and you can perform them using the developer tools.

If you use HASS.os the following direct link may work.  Otherwise, find
the developer tools in the menu and go to Services.  Direct link:
https://homeassistant.local:8123/developer-tools/service .
Choose `zha_custom.execute`


# Examples

Examples are work in progress and may not be functionnal.

For sleepy devices (on a battery) you may need to wake them up
just after sending the command so that they can receive it.


## Scan a device

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

You can write an attribute value to any endpoint/cluster/attribute.
You can provide the numerical value of the attribute, or the zigpy internal name.

```yaml
service: zha_custom.execute
data:
  ieee: 5c:02:72:ff:fe:92:c2:5d
  command: attr_write
  # Data: Endpoint, Cluster ID, Attribute Id, Attribute Type, Attribute Value
  command_data: 11,0x0006,0x0000,0x10,1
```


## Configure reporting

You can set the minimum and maximum delay between two reports and
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


# Backup ZNP network data 

Used to transfer to another ZNP key later, backup or simply get network key and other info.

The output is written to the customisation directory as 'nwk_backup.json'

```yaml
service: zha_custom.execute
data:
  command: znp_backup
```
